import { useState, useCallback } from 'react';
import type { PhotoWithScore } from '../types/photo';
import { discoverPhotos, getThumbnail, scorePhoto } from '../services/sidecar';

export function usePhotos() {
  const [photos, setPhotos] = useState<PhotoWithScore[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [currentDirectory, setCurrentDirectory] = useState<string | null>(null);

  const loadPhotos = useCallback(async (directory: string) => {
    setIsLoading(true);
    setError(null);
    setCurrentDirectory(directory);

    try {
      const images = await discoverPhotos(directory);
      setPhotos(images.map((img) => ({ ...img, thumbnail: undefined, score: undefined })));

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

        setPhotos((prev) =>
          prev.map((photo, idx) => {
            const batchIdx = idx - i;
            if (batchIdx >= 0 && batchIdx < thumbnails.length) {
              return { ...photo, thumbnail: thumbnails[batchIdx] };
            }
            return photo;
          })
        );
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

  return {
    photos,
    isLoading,
    error,
    currentDirectory,
    loadPhotos,
    scorePhoto: scoreSinglePhoto,
    scoreAllPhotos,
    setPhotos,
  };
}
