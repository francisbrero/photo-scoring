import { useState, useEffect, useCallback } from 'react';
import { Layout } from './components/Layout';
import { PhotoGrid } from './components/PhotoBrowser';
import { ScoreViewer } from './components/ScoreViewer';
import { FolderLibrary } from './components/FolderLibrary';
import { usePhotos } from './hooks/usePhotos';
import { checkHealth } from './services/sidecar';
import type { PhotoWithScore } from './types/photo';

function App() {
  const [sidecarReady, setSidecarReady] = useState(false);
  const [selectedPhoto, setSelectedPhoto] = useState<PhotoWithScore | null>(null);
  const {
    photos,
    isLoading,
    error,
    currentDirectory,
    loadPhotos,
    scorePhoto,
    scoreAllPhotos,
    getLastDirectory,
    initialized,
    setInitialized,
    folderLibrary,
    removeFromLibrary,
  } = usePhotos();

  // Check sidecar health on mount
  useEffect(() => {
    const checkSidecar = async () => {
      const healthy = await checkHealth();
      setSidecarReady(healthy);
    };

    checkSidecar();
    const interval = setInterval(checkSidecar, 5000);
    return () => clearInterval(interval);
  }, []);

  // Auto-load last directory when sidecar is ready
  useEffect(() => {
    if (sidecarReady && !initialized) {
      setInitialized(true);
      const lastDir = getLastDirectory();
      if (lastDir) {
        loadPhotos(lastDir);
      }
    }
  }, [sidecarReady, initialized, setInitialized, getLastDirectory, loadPhotos]);

  // Listen for menu events
  useEffect(() => {
    const unsubscribe = window.electron.on('menu:open-folder', handleOpenFolder);
    return unsubscribe;
  }, []);

  const handleOpenFolder = useCallback(async () => {
    const directory = await window.electron.dialog.openDirectory();
    if (directory) {
      loadPhotos(directory);
    }
  }, [loadPhotos]);

  const handleScoreAll = useCallback(() => {
    scoreAllPhotos();
  }, [scoreAllPhotos]);

  const unscoredCount = photos.filter((p) => !p.score).length;
  const scoredCount = photos.length - unscoredCount;

  return (
    <Layout>
      {!sidecarReady ? (
        <div className="flex items-center justify-center h-full">
          <div className="text-center">
            <div className="w-12 h-12 border-4 border-blue-500 border-t-transparent rounded-full animate-spin mx-auto mb-4" />
            <p className="text-gray-600 dark:text-gray-400">Starting scoring engine...</p>
          </div>
        </div>
      ) : (
        <div className="flex h-full">
          {/* Folder Library Sidebar */}
          <FolderLibrary
            folders={folderLibrary}
            currentPath={currentDirectory}
            onSelectFolder={loadPhotos}
            onRemoveFolder={removeFromLibrary}
            onAddFolder={handleOpenFolder}
          />

          {/* Main Content */}
          <div className="flex-1 flex flex-col h-full">
            {photos.length === 0 ? (
              <div className="flex items-center justify-center h-full">
                <div className="text-center max-w-md">
                  <svg
                    className="w-16 h-16 mx-auto mb-4 text-gray-400"
                    fill="none"
                    stroke="currentColor"
                    viewBox="0 0 24 24"
                  >
                    <path
                      strokeLinecap="round"
                      strokeLinejoin="round"
                      strokeWidth={1.5}
                      d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z"
                    />
                  </svg>
                  <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100 mb-2">
                    {folderLibrary.length === 0 ? 'Welcome to Photo Scoring' : 'Select a Folder'}
                  </h2>
                  <p className="text-gray-600 dark:text-gray-400 mb-6">
                    {folderLibrary.length === 0
                      ? 'Add a folder to your library to get started with scoring.'
                      : 'Select a folder from the library or add a new one.'}
                  </p>
                  <button
                    onClick={handleOpenFolder}
                    className="bg-blue-500 hover:bg-blue-600 text-white px-6 py-3 rounded-lg font-medium"
                  >
                    Add Folder
                  </button>
                </div>
              </div>
            ) : (
              <>
                {/* Header bar */}
                <div className="flex items-center gap-4 p-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
                  <span className="text-sm text-gray-500 dark:text-gray-400 truncate flex-1">
                    {currentDirectory}
                  </span>
                  <div className="flex items-center gap-2">
                    <span className="text-sm text-gray-600 dark:text-gray-400">
                      {scoredCount}/{photos.length} scored
                    </span>
                    {unscoredCount > 0 && (
                      <button
                        onClick={handleScoreAll}
                        className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-1.5 rounded text-sm font-medium"
                      >
                        Score All ({unscoredCount})
                      </button>
                    )}
                  </div>
                </div>

                {/* Error message */}
                {error && (
                  <div className="bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 px-4 py-2 text-sm">
                    {error}
                  </div>
                )}

                {/* Loading indicator */}
                {isLoading && (
                  <div className="bg-blue-50 dark:bg-blue-900/20 text-blue-600 dark:text-blue-400 px-4 py-2 text-sm flex items-center gap-2">
                    <div className="w-4 h-4 border-2 border-blue-500 border-t-transparent rounded-full animate-spin" />
                    Loading photos...
                  </div>
                )}

                {/* Photo grid */}
                <div className="flex-1 overflow-hidden">
                  <PhotoGrid
                    photos={photos}
                    onScorePhoto={scorePhoto}
                    onSelectPhoto={setSelectedPhoto}
                  />
                </div>
              </>
            )}
          </div>
        </div>
      )}

      {/* Score viewer modal */}
      {selectedPhoto && (
        <ScoreViewer
          photo={selectedPhoto}
          onClose={() => setSelectedPhoto(null)}
          onScore={() => scorePhoto(selectedPhoto.image_id)}
        />
      )}
    </Layout>
  );
}

export default App;
