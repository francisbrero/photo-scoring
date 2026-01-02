import { useState, useCallback, useEffect } from 'react';
import type { PhotoWithScore } from '../types/photo';
import { discoverPhotos, getThumbnail, scorePhoto, getCachedScores } from '../services/sidecar';

const LAST_DIRECTORY_KEY = 'photo-scoring-last-directory';
const FOLDER_LIBRARY_KEY = 'photo-scoring-folder-library';

export interface FolderInfo {
  path: string;
  name: string;
  addedAt: string;
  lastOpenedAt: string;
}

function loadFolderLibrary(): FolderInfo[] {
  try {
    const stored = localStorage.getItem(FOLDER_LIBRARY_KEY);
    return stored ? JSON.parse(stored) : [];
  } catch {
    return [];
  }
}

function saveFolderLibrary(folders: FolderInfo[]): void {
  localStorage.setItem(FOLDER_LIBRARY_KEY, JSON.stringify(folders));
}

function addToFolderLibrary(directory: string): FolderInfo[] {
  const folders = loadFolderLibrary();
  const now = new Date().toISOString();
  const name = directory.split('/').pop() || directory;

  const existingIndex = folders.findIndex((f) => f.path === directory);
  if (existingIndex >= 0) {
    // Update lastOpenedAt
    folders[existingIndex].lastOpenedAt = now;
  } else {
    // Add new folder
    folders.push({
      path: directory,
      name,
      addedAt: now,
      lastOpenedAt: now,
    });
  }

  // Sort by lastOpenedAt (most recent first)
  folders.sort((a, b) => new Date(b.lastOpenedAt).getTime() - new Date(a.lastOpenedAt).getTime());

  saveFolderLibrary(folders);
  return folders;
}

export function usePhotos() {
  const [photos, setPhotos] = useState<PhotoWithScore[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDirectory, setCurrentDirectory] = useState<string | null>(null);
  const [initialized, setInitialized] = useState(false);
  const [folderLibrary, setFolderLibrary] = useState<FolderInfo[]>(loadFolderLibrary);

  const loadPhotos = useCallback(async (directory: string) => {
    setIsLoading(true);
    setError(null);

    // Clear existing photos immediately when switching folders
    setPhotos([]);
    setCurrentDirectory(directory);

    // Save to localStorage for next app launch
    localStorage.setItem(LAST_DIRECTORY_KEY, directory);

    // Add to folder library
    const updatedLibrary = addToFolderLibrary(directory);
    setFolderLibrary(updatedLibrary);

    try {
      const images = await discoverPhotos(directory);

      // Create a Set of image_ids for this directory to validate updates
      const imageIds = new Set(images.map((img) => img.image_id));

      // Initialize photos
      const initialPhotos = images.map((img) => ({ ...img, thumbnail: undefined, score: undefined }));
      setPhotos(initialPhotos);

      // Load cached scores for all images (non-blocking)
      const imagePaths = images.map((img) => img.file_path);
      getCachedScores(imagePaths)
        .then((cachedScores) => {
          setPhotos((prev) => {
            // Only update if we're still showing photos from the same directory
            // by checking if any of the current photos match the cached score keys
            const currentPaths = new Set(prev.map((p) => p.file_path));
            const hasMatchingPaths = Object.keys(cachedScores).some((path) => currentPaths.has(path));

            if (!hasMatchingPaths && prev.length > 0) {
              // Directory changed, don't apply these scores
              return prev;
            }

            return prev.map((photo) => {
              const cachedScore = cachedScores[photo.file_path];
              if (cachedScore) {
                return { ...photo, score: cachedScore };
              }
              return photo;
            });
          });
        })
        .catch((err) => {
          console.error('Failed to load cached scores:', err);
        });

      // Load thumbnails in batches
      const batchSize = 10;
      for (let i = 0; i < images.length; i += batchSize) {
        const batch = images.slice(i, i + batchSize);
        const thumbnails = await Promise.all(
          batch.map(async (img) => {
            try {
              return await getThumbnail(img.file_path);
            } catch {
              return undefined;
            }
          })
        );

        setPhotos((prev) => {
          // Only update thumbnails for photos that are still in our current set
          return prev.map((photo) => {
            // Find the matching image in the batch by file_path
            const batchIndex = batch.findIndex((b) => b.file_path === photo.file_path);
            if (batchIndex >= 0 && thumbnails[batchIndex]) {
              return { ...photo, thumbnail: thumbnails[batchIndex] };
            }
            return photo;
          });
        });
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load photos');
    } finally {
      setIsLoading(false);
    }
  }, []);

  const scoreSinglePhoto = useCallback(async (imageId: string) => {
    const photo = photos.find((p) => p.image_id === imageId);
    if (!photo) return;

    setPhotos((prev) =>
      prev.map((p) => (p.image_id === imageId ? { ...p, isScoring: true } : p))
    );

    try {
      const result = await scorePhoto(photo.file_path);
      setPhotos((prev) =>
        prev.map((p) =>
          p.image_id === imageId ? { ...p, score: result, isScoring: false } : p
        )
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to score photo');
      setPhotos((prev) =>
        prev.map((p) => (p.image_id === imageId ? { ...p, isScoring: false } : p))
      );
    }
  }, [photos]);

  const scoreAllPhotos = useCallback(async () => {
    const unscored = photos.filter((p) => !p.score);
    for (const photo of unscored) {
      await scoreSinglePhoto(photo.image_id);
    }
  }, [photos, scoreSinglePhoto]);

  // Get the last opened directory (for auto-loading on startup)
  const getLastDirectory = useCallback(() => {
    return localStorage.getItem(LAST_DIRECTORY_KEY);
  }, []);

  // Remove a folder from the library
  const removeFromLibrary = useCallback((path: string) => {
    const folders = loadFolderLibrary().filter((f) => f.path !== path);
    saveFolderLibrary(folders);
    setFolderLibrary(folders);

    // If we're removing the current directory, clear it
    if (path === currentDirectory) {
      setPhotos([]);
      setCurrentDirectory(null);
      localStorage.removeItem(LAST_DIRECTORY_KEY);
    }
  }, [currentDirectory]);

  return {
    photos,
    isLoading,
    error,
    currentDirectory,
    loadPhotos,
    scorePhoto: scoreSinglePhoto,
    scoreAllPhotos,
    setPhotos,
    getLastDirectory,
    initialized,
    setInitialized,
    folderLibrary,
    removeFromLibrary,
  };
}
