import { useState, useEffect, useCallback, useRef } from 'react';
import {
  startTriage,
  getTriageStatus,
  getTriageResults,
  cancelTriage,
  copySelectedPhotos,
  type TriageConfig,
  type TriageJob,
  type TriageStatus,
  type TriageResults,
  type TriagePhoto,
} from '../../services/sidecar';

interface TriageViewProps {
  onClose: () => void;
}

const POLL_INTERVAL = 2000;

// Credit tiers
function calculateCredits(photoCount: number): number {
  if (photoCount <= 100) return 1;
  if (photoCount <= 500) return 3;
  if (photoCount <= 1000) return 5;
  if (photoCount <= 2000) return 8;
  return 10;
}

// Target options
const TARGET_OPTIONS = [
  { value: '5%', label: 'Top 5%' },
  { value: '10%', label: 'Top 10%' },
  { value: '20%', label: 'Top 20%' },
  { value: '25%', label: 'Top 25%' },
];

// Criteria options
const CRITERIA_OPTIONS = [
  { value: 'standout', label: 'Standout Photos', description: 'Visually compelling' },
  { value: 'quality', label: 'Technical Quality', description: 'Sharp, well-exposed' },
  { value: 'portfolio', label: 'Portfolio Worthy', description: 'Best overall' },
];

type ViewState = 'config' | 'processing' | 'results';

export function TriageView({ onClose }: TriageViewProps) {
  // View state
  const [viewState, setViewState] = useState<ViewState>('config');

  // Config state
  const [directory, setDirectory] = useState<string | null>(null);
  const [photoCount, setPhotoCount] = useState(0);
  const [target, setTarget] = useState('10%');
  const [criteria, setCriteria] = useState('standout');
  const [passes, setPasses] = useState<1 | 2>(2);

  // Processing state
  const [job, setJob] = useState<TriageJob | null>(null);
  const [status, setStatus] = useState<TriageStatus | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isStarting, setIsStarting] = useState(false);

  // Results state
  const [results, setResults] = useState<TriageResults | null>(null);
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());

  const pollRef = useRef<NodeJS.Timeout | null>(null);

  // Clean up on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) {
        clearInterval(pollRef.current);
      }
    };
  }, []);

  const handleSelectFolder = useCallback(async () => {
    const selected = await window.electron.dialog.openDirectory();
    if (selected) {
      setDirectory(selected);
      // Get photo count
      try {
        const response = await fetch(
          `http://127.0.0.1:${await window.electron.sidecar.getPort()}/api/photos/discover?directory=${encodeURIComponent(selected)}`
        );
        if (response.ok) {
          const data = await response.json();
          setPhotoCount(data.total);
        }
      } catch {
        setPhotoCount(0);
      }
    }
  }, []);

  const handleStart = useCallback(async () => {
    if (!directory) return;

    setIsStarting(true);
    setError(null);

    try {
      const config: TriageConfig = {
        directory,
        target,
        criteria,
        passes,
      };

      const jobData = await startTriage(config);
      setJob(jobData);
      setViewState('processing');

      // Start polling
      pollRef.current = setInterval(async () => {
        try {
          const statusData = await getTriageStatus(jobData.job_id);
          setStatus(statusData);

          if (statusData.status === 'completed') {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            const resultsData = await getTriageResults(jobData.job_id);
            setResults(resultsData);
            setSelectedPhotos(new Set(resultsData.selected_photos.map((p) => p.image_id)));
            setViewState('results');
          } else if (statusData.status === 'failed') {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            setError(statusData.error_message || 'Triage failed');
            setViewState('config');
          }
        } catch {
          // Ignore polling errors
        }
      }, POLL_INTERVAL);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start triage');
      setViewState('config');
    } finally {
      setIsStarting(false);
    }
  }, [directory, target, criteria, passes]);

  const handleCancel = useCallback(async () => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    if (job) {
      try {
        await cancelTriage(job.job_id);
      } catch {
        // Ignore
      }
    }
    setViewState('config');
  }, [job]);

  const togglePhotoSelection = useCallback((imageId: string) => {
    setSelectedPhotos((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(imageId)) {
        newSet.delete(imageId);
      } else {
        newSet.add(imageId);
      }
      return newSet;
    });
  }, []);

  const handleCopyToFolder = useCallback(async () => {
    if (!results) return;

    const destination = await window.electron.dialog.openDirectory();
    if (!destination) return;

    try {
      const result = await copySelectedPhotos(results.job_id, destination);
      alert(`Copied ${result.copied} photos to ${result.destination}`);
    } catch (err) {
      alert(err instanceof Error ? err.message : 'Failed to copy photos');
    }
  }, [results]);

  const handleRevealInFinder = useCallback(async (filePath: string) => {
    await window.electron.shell.showItemInFolder(filePath);
  }, []);

  const handleNewTriage = useCallback(() => {
    setJob(null);
    setStatus(null);
    setResults(null);
    setSelectedPhotos(new Set());
    setViewState('config');
  }, []);

  const creditsNeeded = calculateCredits(photoCount);

  // Config View
  if (viewState === 'config') {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-2xl w-full max-h-[90vh] overflow-y-auto m-4">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white">Photo Triage</h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Content */}
          <div className="p-6">
            <p className="text-gray-600 dark:text-gray-400 mb-6">
              Select a folder with up to 2,000 photos. AI will identify the best ones for you.
            </p>

            {error && (
              <div className="mb-6 p-4 bg-red-50 dark:bg-red-900/20 text-red-600 dark:text-red-400 rounded-lg">
                {error}
              </div>
            )}

            {/* Folder Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Folder
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={directory || ''}
                  readOnly
                  placeholder="Select a folder..."
                  className="flex-1 px-4 py-2 border border-gray-300 dark:border-gray-600 rounded-lg bg-gray-50 dark:bg-gray-700 text-gray-900 dark:text-white"
                />
                <button
                  onClick={handleSelectFolder}
                  className="px-4 py-2 bg-blue-500 hover:bg-blue-600 text-white rounded-lg font-medium"
                >
                  Browse
                </button>
              </div>
              {photoCount > 0 && (
                <p className="mt-2 text-sm text-gray-500 dark:text-gray-400">
                  {photoCount.toLocaleString()} photos found
                </p>
              )}
            </div>

            {/* Target Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Selection Target
              </label>
              <div className="grid grid-cols-4 gap-2">
                {TARGET_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setTarget(option.value)}
                    className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                      target === option.value
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    {option.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Criteria Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Selection Criteria
              </label>
              <div className="space-y-2">
                {CRITERIA_OPTIONS.map((option) => (
                  <button
                    key={option.value}
                    onClick={() => setCriteria(option.value)}
                    className={`w-full text-left px-4 py-3 rounded-lg text-sm transition-colors ${
                      criteria === option.value
                        ? 'bg-blue-500 text-white'
                        : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                    }`}
                  >
                    <div className="font-medium">{option.label}</div>
                    <div className={`text-xs ${criteria === option.value ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'}`}>
                      {option.description}
                    </div>
                  </button>
                ))}
              </div>
            </div>

            {/* Passes Selection */}
            <div className="mb-6">
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                Analysis Depth
              </label>
              <div className="grid grid-cols-2 gap-4">
                <button
                  onClick={() => setPasses(1)}
                  className={`px-4 py-3 rounded-lg text-sm transition-colors ${
                    passes === 1
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <div className="font-medium">Quick (1 pass)</div>
                  <div className={`text-xs ${passes === 1 ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'}`}>
                    Faster, slightly less accurate
                  </div>
                </button>
                <button
                  onClick={() => setPasses(2)}
                  className={`px-4 py-3 rounded-lg text-sm transition-colors ${
                    passes === 2
                      ? 'bg-blue-500 text-white'
                      : 'bg-gray-100 dark:bg-gray-700 text-gray-700 dark:text-gray-300 hover:bg-gray-200 dark:hover:bg-gray-600'
                  }`}
                >
                  <div className="font-medium">Thorough (2 passes)</div>
                  <div className={`text-xs ${passes === 2 ? 'text-white/70' : 'text-gray-500 dark:text-gray-400'}`}>
                    Recommended for best results
                  </div>
                </button>
              </div>
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {photoCount > 0 && (
                <>
                  Cost: <span className="font-medium text-gray-900 dark:text-white">{creditsNeeded}</span> credit{creditsNeeded !== 1 ? 's' : ''}
                  <span className="text-gray-400 ml-2">(vs {photoCount} for full scoring)</span>
                </>
              )}
            </div>
            <button
              onClick={handleStart}
              disabled={!directory || photoCount === 0 || isStarting}
              className="px-6 py-2 bg-blue-500 hover:bg-blue-600 disabled:bg-gray-300 dark:disabled:bg-gray-600 text-white rounded-lg font-medium disabled:cursor-not-allowed"
            >
              {isStarting ? 'Starting...' : 'Start Triage'}
            </button>
          </div>
        </div>
      </div>
    );
  }

  // Processing View
  if (viewState === 'processing' && status) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-md w-full m-4 p-8 text-center">
          {/* Spinner */}
          <div className="w-20 h-20 mx-auto mb-6">
            <div className="animate-spin w-full h-full border-4 border-blue-500 border-t-transparent rounded-full" />
          </div>

          <h2 className="text-xl font-semibold text-gray-900 dark:text-white mb-2">
            Analyzing Photos
          </h2>

          <p className="text-gray-600 dark:text-gray-400 mb-6">
            {status.progress?.message || 'Processing...'}
          </p>

          {/* Progress Bar */}
          <div className="mb-4">
            <div className="h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-blue-500 rounded-full transition-all duration-300"
                style={{ width: `${status.progress?.percentage || 0}%` }}
              />
            </div>
            <p className="text-sm text-gray-500 dark:text-gray-400 mt-2">
              {Math.round(status.progress?.percentage || 0)}% complete
            </p>
          </div>

          {/* Stats */}
          <div className="flex justify-center gap-8 text-sm mb-6">
            <div>
              <span className="text-gray-500 dark:text-gray-400">Total:</span>{' '}
              <span className="text-gray-900 dark:text-white">{status.total_input}</span>
            </div>
            {status.pass1_survivors > 0 && (
              <div>
                <span className="text-gray-500 dark:text-gray-400">Pass 1:</span>{' '}
                <span className="text-green-500">{status.pass1_survivors}</span>
              </div>
            )}
          </div>

          <button
            onClick={handleCancel}
            className="text-gray-500 hover:text-red-500 dark:text-gray-400 dark:hover:text-red-400"
          >
            Cancel
          </button>
        </div>
      </div>
    );
  }

  // Results View
  if (viewState === 'results' && results) {
    return (
      <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl max-w-6xl w-full max-h-[90vh] m-4 flex flex-col">
          {/* Header */}
          <div className="flex items-center justify-between p-4 border-b border-gray-200 dark:border-gray-700">
            <div>
              <h2 className="text-xl font-semibold text-gray-900 dark:text-white">
                Triage Complete
              </h2>
              <p className="text-sm text-gray-500 dark:text-gray-400">
                Found {results.final_selected} standout photos from {results.total_input}
              </p>
            </div>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          {/* Photo Grid */}
          <div className="flex-1 overflow-y-auto p-4">
            <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-5 lg:grid-cols-6 gap-3">
              {results.selected_photos.map((photo: TriagePhoto) => (
                <div
                  key={photo.image_id}
                  onClick={() => togglePhotoSelection(photo.image_id)}
                  className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all aspect-square ${
                    selectedPhotos.has(photo.image_id)
                      ? 'border-blue-500 ring-2 ring-blue-500/50'
                      : 'border-transparent hover:border-gray-300 dark:hover:border-gray-600'
                  }`}
                >
                  {photo.thumbnail ? (
                    <img
                      src={`data:image/jpeg;base64,${photo.thumbnail}`}
                      alt={photo.filename}
                      className="w-full h-full object-cover"
                    />
                  ) : (
                    <div className="w-full h-full bg-gray-200 dark:bg-gray-700 flex items-center justify-center">
                      <svg className="w-8 h-8 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}

                  {/* Selection indicator */}
                  <div className="absolute top-2 right-2">
                    <div
                      className={`w-6 h-6 rounded-full flex items-center justify-center ${
                        selectedPhotos.has(photo.image_id)
                          ? 'bg-blue-500'
                          : 'bg-black/50 border border-white/50'
                      }`}
                    >
                      {selectedPhotos.has(photo.image_id) && (
                        <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                        </svg>
                      )}
                    </div>
                  </div>

                  {/* Filename tooltip */}
                  <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1">
                    <p className="text-xs text-white truncate">{photo.filename}</p>
                  </div>

                  {/* Double-click to reveal */}
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      handleRevealInFinder(photo.file_path);
                    }}
                    className="absolute top-2 left-2 w-6 h-6 rounded-full bg-black/50 flex items-center justify-center text-white opacity-0 hover:opacity-100 transition-opacity"
                    title="Reveal in Finder"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
                    </svg>
                  </button>
                </div>
              ))}
            </div>
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between p-4 border-t border-gray-200 dark:border-gray-700 bg-gray-50 dark:bg-gray-800/50">
            <div className="text-sm text-gray-500 dark:text-gray-400">
              {selectedPhotos.size} of {results.selected_photos.length} selected
            </div>
            <div className="flex gap-3">
              <button
                onClick={handleNewTriage}
                className="px-4 py-2 text-gray-600 dark:text-gray-300 hover:text-gray-900 dark:hover:text-white"
              >
                New Triage
              </button>
              <button
                onClick={handleCopyToFolder}
                disabled={selectedPhotos.size === 0}
                className="px-4 py-2 bg-gray-100 dark:bg-gray-700 hover:bg-gray-200 dark:hover:bg-gray-600 text-gray-700 dark:text-gray-300 rounded-lg font-medium disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Copy to Folder
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return null;
}
