import { useState, useCallback, useRef } from 'react';
import { Link } from 'react-router-dom';
import heic2any from 'heic2any';
import { useAuth } from '../contexts/AuthContext';
import { useTriage } from '../hooks/useTriage';
import { calculateTriageCredits, type TriageConfig, type TriagePhoto } from '../types/triage';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];
const HEIC_TYPES = ['image/heic', 'image/heif'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB
const MAX_PHOTOS = 2000;

interface PreviewFile {
  file: File;
  preview: string;
}

function isHeicFile(file: File): boolean {
  if (HEIC_TYPES.includes(file.type)) return true;
  const ext = file.name.toLowerCase().split('.').pop();
  return ext === 'heic' || ext === 'heif';
}

async function convertHeicToJpeg(file: File): Promise<string> {
  try {
    const blob = await heic2any({
      blob: file,
      toType: 'image/jpeg',
      quality: 0.8,
    });
    const resultBlob = Array.isArray(blob) ? blob[0] : blob;
    return URL.createObjectURL(resultBlob);
  } catch {
    return '';
  }
}

// Criteria options
const CRITERIA_OPTIONS = [
  { value: 'standout', label: 'Standout Photos', description: 'Visually compelling, likely to grab attention' },
  { value: 'quality', label: 'Technical Quality', description: 'Sharp, well-exposed, properly composed' },
  { value: 'portfolio', label: 'Portfolio Worthy', description: 'Professional quality, best overall' },
];

// Target options
const TARGET_OPTIONS = [
  { value: '5%', label: 'Top 5%' },
  { value: '10%', label: 'Top 10%' },
  { value: '20%', label: 'Top 20%' },
  { value: '25%', label: 'Top 25%' },
];

export function Triage() {
  const { credits } = useAuth();
  const {
    isStarting,
    isProcessing,
    isLoadingActiveJobs,
    activeJobs,
    status,
    results,
    error,
    startTriage,
    resumeJob,
    proceedToScoring,
    cancelTriage,
    reset,
  } = useTriage();

  // File state
  const [files, setFiles] = useState<PreviewFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({ current: 0, total: 0 });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);

  // Config state
  const [target, setTarget] = useState('10%');
  const [criteria, setCriteria] = useState('standout');
  const [passes, setPasses] = useState<1 | 2>(2);

  // Results modal state
  const [showResults, setShowResults] = useState(false);
  const [selectedPhotos, setSelectedPhotos] = useState<Set<string>>(new Set());

  const creditsNeeded = calculateTriageCredits(files.length);

  const validateFile = (file: File): boolean => {
    if (!ALLOWED_TYPES.includes(file.type) && !isHeicFile(file)) {
      return false;
    }
    if (file.size > MAX_FILE_SIZE) {
      return false;
    }
    return true;
  };

  const addFiles = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles).filter(validateFile);

    // Check max photos limit
    const totalFiles = files.length + fileArray.length;
    if (totalFiles > MAX_PHOTOS) {
      alert(`Maximum ${MAX_PHOTOS} photos allowed. ${fileArray.length - (MAX_PHOTOS - files.length)} files were not added.`);
      fileArray.splice(MAX_PHOTOS - files.length);
    }

    if (fileArray.length === 0) return;

    setIsProcessingFiles(true);
    setProcessingProgress({ current: 0, total: fileArray.length });

    const previewFiles: PreviewFile[] = [];
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      setProcessingProgress({ current: i + 1, total: fileArray.length });

      let preview: string;
      if (isHeicFile(file)) {
        preview = await convertHeicToJpeg(file);
      } else {
        preview = URL.createObjectURL(file);
      }

      previewFiles.push({ file, preview });
    }

    setFiles((prev) => [...prev, ...previewFiles]);
    setIsProcessingFiles(false);
  }, [files.length]);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    async (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);

      const items = e.dataTransfer.items;
      const fileList: File[] = [];

      // Handle folder drops
      for (let i = 0; i < items.length; i++) {
        const item = items[i].webkitGetAsEntry?.();
        if (item) {
          await traverseFileTree(item, fileList);
        }
      }

      if (fileList.length > 0) {
        addFiles(fileList);
      } else if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

  // Recursively traverse folder structure
  async function traverseFileTree(item: FileSystemEntry, files: File[]): Promise<void> {
    if (item.isFile) {
      const fileEntry = item as FileSystemFileEntry;
      return new Promise((resolve) => {
        fileEntry.file((file) => {
          if (validateFile(file)) {
            files.push(file);
          }
          resolve();
        });
      });
    } else if (item.isDirectory) {
      const dirEntry = item as FileSystemDirectoryEntry;
      const reader = dirEntry.createReader();
      return new Promise((resolve) => {
        reader.readEntries(async (entries) => {
          for (const entry of entries) {
            await traverseFileTree(entry, files);
          }
          resolve();
        });
      });
    }
  }

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) {
        addFiles(e.target.files);
      }
    },
    [addFiles]
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const newFiles = [...prev];
      URL.revokeObjectURL(newFiles[index].preview);
      newFiles.splice(index, 1);
      return newFiles;
    });
  }, []);

  const clearFiles = useCallback(() => {
    files.forEach((f) => URL.revokeObjectURL(f.preview));
    setFiles([]);
  }, [files]);

  const handleStartTriage = async () => {
    const config: TriageConfig = { target, criteria, passes };
    const jobId = await startTriage(files.map((f) => f.file), config);
    if (jobId) {
      // Clear file previews to free memory
      files.forEach((f) => URL.revokeObjectURL(f.preview));
      setFiles([]);
    }
  };

  const handleCancel = async () => {
    if (status?.job_id) {
      await cancelTriage(status.job_id);
    }
    reset();
  };

  const handleViewResults = () => {
    setShowResults(true);
    // Select all photos by default
    if (results) {
      setSelectedPhotos(new Set(results.selected_photos.map((p) => p.id)));
    }
  };

  const togglePhotoSelection = (photoId: string) => {
    setSelectedPhotos((prev) => {
      const newSet = new Set(prev);
      if (newSet.has(photoId)) {
        newSet.delete(photoId);
      } else {
        newSet.add(photoId);
      }
      return newSet;
    });
  };

  const handleProceedToScoring = async () => {
    if (!results) return;
    const photoIds = Array.from(selectedPhotos);
    const result = await proceedToScoring(results.job_id, photoIds);
    if (result) {
      setShowResults(false);
      reset();
      // Redirect to dashboard
      window.location.href = '/dashboard';
    }
  };

  const handleDownload = () => {
    if (!results) return;
    window.open(`/api/triage/${results.job_id}/download`, '_blank');
  };

  const handleNewTriage = () => {
    setShowResults(false);
    reset();
  };

  // Show loading view (when fetching active jobs on mount)
  if (isLoadingActiveJobs) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-8">Photo Triage</h1>

        {/* Animated Spinner */}
        <div className="w-16 h-16 mx-auto mb-6">
          <div className="animate-spin w-full h-full border-4 border-[#e94560] border-t-transparent rounded-full" />
        </div>

        {/* Message */}
        <p className="text-[var(--text-muted)]">
          Checking for active jobs...
        </p>
      </div>
    );
  }

  // Show upload progress view (while uploading files to server)
  if (isStarting) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-8">Uploading Photos</h1>

        {/* Animated Spinner */}
        <div className="w-24 h-24 mx-auto mb-8">
          <div className="animate-spin w-full h-full border-4 border-[#e94560] border-t-transparent rounded-full" />
        </div>

        {/* Phase */}
        <p className="text-xl text-[var(--text-primary)] mb-4">
          Uploading {files.length} photos to server...
        </p>

        {/* Info */}
        <p className="text-sm text-[var(--text-muted)]">
          This may take a moment depending on file sizes and connection speed.
        </p>
      </div>
    );
  }

  // Show processing view (while AI is analyzing)
  if (isProcessing && status) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-8">Analyzing Photos</h1>

        {/* Animated Spinner */}
        <div className="w-24 h-24 mx-auto mb-8">
          <div className="animate-spin w-full h-full border-4 border-[#e94560] border-t-transparent rounded-full" />
        </div>

        {/* Phase */}
        <p className="text-xl text-[var(--text-primary)] mb-4">
          {status.progress?.message || 'Processing...'}
        </p>

        {/* Progress Bar */}
        <div className="max-w-md mx-auto mb-4">
          <div className="h-3 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
            <div
              className="h-full bg-[#e94560] rounded-full transition-all duration-300"
              style={{ width: `${status.progress?.percentage || 0}%` }}
            />
          </div>
          <p className="text-sm text-[var(--text-muted)] mt-2">
            {Math.round(status.progress?.percentage || 0)}% complete
          </p>
        </div>

        {/* Stats */}
        <div className="flex justify-center gap-8 mt-8 text-sm">
          <div>
            <span className="text-[var(--text-muted)]">Total Photos:</span>{' '}
            <span className="text-[var(--text-primary)]">{status.total_input}</span>
          </div>
          {status.pass1_survivors > 0 && (
            <div>
              <span className="text-[var(--text-muted)]">Pass 1 Survivors:</span>{' '}
              <span className="text-green-400">{status.pass1_survivors}</span>
            </div>
          )}
        </div>

        {/* Cancel Button */}
        <button
          onClick={handleCancel}
          className="mt-8 px-6 py-2 text-[var(--text-muted)] hover:text-red-400 transition-colors"
        >
          Cancel
        </button>
      </div>
    );
  }

  // Show completion view
  if (results && !showResults) {
    return (
      <div className="max-w-2xl mx-auto text-center py-12">
        <div className="w-20 h-20 mx-auto mb-6 bg-green-500 rounded-full flex items-center justify-center">
          <svg className="w-10 h-10 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-4">Triage Complete!</h1>

        <p className="text-[var(--text-secondary)] mb-8">
          Found <span className="text-green-400 font-semibold">{results.final_selected}</span> standout photos
          from {results.total_input} analyzed.
        </p>

        {/* Stats */}
        <div className="flex justify-center gap-8 mb-8">
          <div className="text-center">
            <div className="text-2xl font-bold text-[var(--text-primary)]">{results.total_input}</div>
            <div className="text-sm text-[var(--text-muted)]">Total Input</div>
          </div>
          {results.pass1_survivors > 0 && results.pass1_survivors !== results.final_selected && (
            <div className="text-center">
              <div className="text-2xl font-bold text-amber-400">{results.pass1_survivors}</div>
              <div className="text-sm text-[var(--text-muted)]">Pass 1</div>
            </div>
          )}
          <div className="text-center">
            <div className="text-2xl font-bold text-green-400">{results.final_selected}</div>
            <div className="text-sm text-[var(--text-muted)]">Selected</div>
          </div>
        </div>

        {/* Actions */}
        <div className="flex flex-col sm:flex-row gap-4 justify-center">
          <button
            onClick={handleViewResults}
            className="px-6 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors"
          >
            View Selected Photos
          </button>
          <button
            onClick={handleDownload}
            className="px-6 py-3 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity"
          >
            Download ZIP
          </button>
          <button
            onClick={handleNewTriage}
            className="px-6 py-3 text-[var(--text-secondary)] hover:text-[var(--text-primary)] transition-colors"
          >
            New Triage
          </button>
        </div>
      </div>
    );
  }

  // Results Modal
  if (showResults && results) {
    return (
      <div className="max-w-7xl mx-auto">
        <div className="flex justify-between items-center mb-6">
          <div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)]">Selected Photos</h1>
            <p className="text-[var(--text-muted)]">
              {selectedPhotos.size} of {results.selected_photos.length} selected for scoring
            </p>
          </div>
          <button
            onClick={() => setShowResults(false)}
            className="text-[var(--text-muted)] hover:text-[var(--text-primary)]"
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        {/* Photo Grid */}
        <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-6 gap-4 mb-8">
          {results.selected_photos.map((photo: TriagePhoto) => (
            <div
              key={photo.id}
              onClick={() => togglePhotoSelection(photo.id)}
              className={`relative cursor-pointer rounded-lg overflow-hidden border-2 transition-all ${
                selectedPhotos.has(photo.id)
                  ? 'border-[#e94560] ring-2 ring-[#e94560]/50'
                  : 'border-transparent hover:border-[var(--border-color)]'
              }`}
            >
              <img
                src={photo.thumbnail_url || ''}
                alt={photo.original_filename}
                className="w-full aspect-square object-cover"
              />
              {/* Checkbox Overlay */}
              <div className="absolute top-2 right-2">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center ${
                    selectedPhotos.has(photo.id)
                      ? 'bg-[#e94560]'
                      : 'bg-black/50 border border-white/50'
                  }`}
                >
                  {selectedPhotos.has(photo.id) && (
                    <svg className="w-4 h-4 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                  )}
                </div>
              </div>
              {/* Filename */}
              <div className="absolute bottom-0 left-0 right-0 bg-black/60 px-2 py-1">
                <p className="text-xs text-white truncate">{photo.original_filename}</p>
              </div>
            </div>
          ))}
        </div>

        {/* Action Bar */}
        <div className="sticky bottom-0 bg-[var(--bg-secondary)] border-t border-[var(--border-color)] p-4 -mx-4">
          <div className="max-w-7xl mx-auto flex flex-col sm:flex-row gap-4 justify-between items-center">
            <div className="text-sm text-[var(--text-muted)]">
              {selectedPhotos.size > 0 ? (
                <>
                  Scoring {selectedPhotos.size} photo{selectedPhotos.size !== 1 ? 's' : ''} will use{' '}
                  <span className="text-[var(--text-primary)]">{selectedPhotos.size}</span> credit
                  {selectedPhotos.size !== 1 ? 's' : ''}
                </>
              ) : (
                'Select photos to proceed with full scoring'
              )}
            </div>
            <div className="flex gap-4">
              <button
                onClick={handleDownload}
                className="px-4 py-2 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity"
              >
                Download ZIP
              </button>
              <button
                onClick={handleProceedToScoring}
                disabled={selectedPhotos.size === 0}
                className="px-6 py-2 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Score Selected Photos
              </button>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // Default upload view
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Photo Triage</h1>
        <p className="text-[var(--text-secondary)]">
          Upload up to {MAX_PHOTOS.toLocaleString()} photos. AI will identify the best ones to score in detail.
        </p>
      </div>

      {/* Error Display */}
      {error && (
        <div className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Active Jobs Banner */}
      {activeJobs.length > 0 && (
        <div className="mb-6 p-4 bg-amber-500/10 border border-amber-500/30 rounded-lg">
          <h3 className="font-semibold text-amber-400 mb-3">
            {activeJobs.length === 1 ? 'You have an active triage job' : `You have ${activeJobs.length} active triage jobs`}
          </h3>
          <div className="space-y-3">
            {activeJobs.map((activeJob) => (
              <div
                key={activeJob.job_id}
                className="flex items-center justify-between bg-[var(--bg-tertiary)] rounded-lg p-3"
              >
                <div className="flex-1">
                  <div className="flex items-center gap-2">
                    <span className="text-[var(--text-primary)]">
                      {activeJob.total_input} photos
                    </span>
                    <span className="text-[var(--text-muted)]">•</span>
                    <span className="text-[var(--text-muted)] text-sm">
                      {activeJob.phase === 'coarse_pass' ? 'Coarse pass' :
                       activeJob.phase === 'fine_pass' ? 'Fine pass' :
                       activeJob.phase === 'grid_generation' ? 'Generating grids' :
                       activeJob.status === 'pending' ? 'Pending' : 'Processing'}
                    </span>
                  </div>
                  <div className="mt-1 h-1.5 bg-[var(--bg-secondary)] rounded-full overflow-hidden max-w-xs">
                    <div
                      className="h-full bg-amber-500 rounded-full transition-all duration-300"
                      style={{ width: `${activeJob.progress_percentage}%` }}
                    />
                  </div>
                </div>
                <button
                  onClick={() => resumeJob(activeJob.job_id)}
                  className="ml-4 px-4 py-2 bg-amber-500 text-black rounded-lg font-medium hover:bg-amber-400 transition-colors"
                >
                  Resume
                </button>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center transition-colors
          ${isProcessingFiles ? 'cursor-wait' : 'cursor-pointer'}
          ${
            isDragging
              ? 'border-[#e94560] bg-[#e94560]/10'
              : 'border-[var(--border-color)] hover:border-[#e94560]/50'
          }
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          multiple
          onChange={handleFileSelect}
          className="hidden"
        />
        <input
          ref={folderInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          multiple
          {...{ webkitdirectory: '', directory: '' } as React.InputHTMLAttributes<HTMLInputElement>}
          onChange={handleFileSelect}
          className="hidden"
        />

        {isProcessingFiles ? (
          <div className="py-4">
            <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <div className="animate-spin w-12 h-12 border-4 border-[#e94560] border-t-transparent rounded-full" />
            </div>
            <p className="text-lg text-[var(--text-primary)] mb-4">
              Processing {processingProgress.total} files...
            </p>
            <div className="max-w-xs mx-auto">
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                  style={{ width: `${(processingProgress.current / processingProgress.total) * 100}%` }}
                />
              </div>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                {processingProgress.current} / {processingProgress.total}
              </p>
            </div>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M3 7v10a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-6l-2-2H5a2 2 0 00-2 2z"
                />
              </svg>
            </div>
            <p className="text-lg text-[var(--text-primary)] mb-2">
              {isDragging ? 'Drop your photos or folder here' : 'Drag & drop photos or folders here'}
            </p>
            <p className="text-sm text-[var(--text-muted)] mb-4">
              JPEG, PNG, HEIC, WebP up to 50MB each
            </p>
            <div className="flex gap-4 justify-center">
              <button
                onClick={() => fileInputRef.current?.click()}
                className="px-4 py-2 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity"
              >
                Select Files
              </button>
              <button
                onClick={() => folderInputRef.current?.click()}
                className="px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73e54] transition-colors"
              >
                Select Folder
              </button>
            </div>
          </>
        )}
      </div>

      {/* Configuration */}
      {files.length > 0 && (
        <div className="mt-8 grid md:grid-cols-2 gap-6">
          {/* Target Selection */}
          <div className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-color)]">
            <h3 className="font-semibold text-[var(--text-primary)] mb-3">Selection Target</h3>
            <div className="grid grid-cols-2 gap-2">
              {TARGET_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setTarget(option.value)}
                  className={`px-4 py-2 rounded-lg text-sm transition-colors ${
                    target === option.value
                      ? 'bg-[#e94560] text-white'
                      : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/80'
                  }`}
                >
                  {option.label}
                </button>
              ))}
            </div>
          </div>

          {/* Criteria Selection */}
          <div className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-color)]">
            <h3 className="font-semibold text-[var(--text-primary)] mb-3">Selection Criteria</h3>
            <div className="space-y-2">
              {CRITERIA_OPTIONS.map((option) => (
                <button
                  key={option.value}
                  onClick={() => setCriteria(option.value)}
                  className={`w-full text-left px-4 py-2 rounded-lg text-sm transition-colors ${
                    criteria === option.value
                      ? 'bg-[#e94560] text-white'
                      : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/80'
                  }`}
                >
                  <div className="font-medium">{option.label}</div>
                  <div className={`text-xs ${criteria === option.value ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>
                    {option.description}
                  </div>
                </button>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Passes Selection */}
      {files.length > 0 && (
        <div className="mt-4 bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-color)]">
          <h3 className="font-semibold text-[var(--text-primary)] mb-3">Analysis Depth</h3>
          <div className="flex gap-4">
            <button
              onClick={() => setPasses(1)}
              className={`flex-1 px-4 py-3 rounded-lg text-sm transition-colors ${
                passes === 1
                  ? 'bg-[#e94560] text-white'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/80'
              }`}
            >
              <div className="font-medium">Quick (1 pass)</div>
              <div className={`text-xs ${passes === 1 ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>
                Faster, slightly less accurate
              </div>
            </button>
            <button
              onClick={() => setPasses(2)}
              className={`flex-1 px-4 py-3 rounded-lg text-sm transition-colors ${
                passes === 2
                  ? 'bg-[#e94560] text-white'
                  : 'bg-[var(--bg-tertiary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]/80'
              }`}
            >
              <div className="font-medium">Thorough (2 passes)</div>
              <div className={`text-xs ${passes === 2 ? 'text-white/70' : 'text-[var(--text-muted)]'}`}>
                Recommended for best results
              </div>
            </button>
          </div>
        </div>
      )}

      {/* File Preview Grid */}
      {files.length > 0 && (
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Selected Photos ({files.length.toLocaleString()})
            </h2>
            <button
              onClick={clearFiles}
              className="text-sm text-[var(--text-muted)] hover:text-red-400 transition-colors"
            >
              Clear All
            </button>
          </div>

          <div className="grid grid-cols-4 sm:grid-cols-6 md:grid-cols-8 gap-2 max-h-64 overflow-y-auto p-2 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)]">
            {files.slice(0, 100).map((f, index) => (
              <div key={index} className="relative group aspect-square">
                <img
                  src={f.preview}
                  alt={f.file.name}
                  className="w-full h-full object-cover rounded"
                />
                <button
                  onClick={() => removeFile(index)}
                  className="absolute top-1 right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white opacity-0 group-hover:opacity-100 transition-opacity"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
            ))}
            {files.length > 100 && (
              <div className="aspect-square bg-[var(--bg-tertiary)] rounded flex items-center justify-center">
                <span className="text-[var(--text-muted)] text-sm">+{files.length - 100} more</span>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Action Bar */}
      {files.length > 0 && (
        <div className="mt-8 flex flex-col sm:flex-row gap-4 justify-between items-center p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)]">
          <div className="text-center sm:text-left">
            <p className="text-[var(--text-primary)]">
              {files.length.toLocaleString()} photo{files.length !== 1 ? 's' : ''} selected
            </p>
            <p className="text-sm text-[var(--text-muted)]">
              This will use <span className="text-[var(--text-primary)]">{creditsNeeded}</span> credit
              {creditsNeeded !== 1 ? 's' : ''} (vs {files.length} for full scoring)
            </p>
            {credits !== null && credits < creditsNeeded && (
              <p className="text-sm text-red-400 mt-1">
                Not enough credits! You have {credits}, need {creditsNeeded}.{' '}
                <Link to="/settings" className="underline">Buy more</Link>
              </p>
            )}
          </div>
          <button
            onClick={handleStartTriage}
            disabled={isStarting || (credits !== null && credits < creditsNeeded)}
            className="px-8 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
          >
            {isStarting ? 'Starting...' : 'Start Triage'}
          </button>
        </div>
      )}

      {/* How It Works */}
      <div className="mt-12 bg-[var(--bg-secondary)] rounded-lg p-6 border border-[var(--border-color)]">
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">How Triage Works</h3>
        <div className="grid md:grid-cols-3 gap-6">
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-[#e94560] flex items-center justify-center text-white font-bold shrink-0">
              1
            </div>
            <div>
              <h4 className="font-medium text-[var(--text-primary)]">Upload Photos</h4>
              <p className="text-sm text-[var(--text-muted)]">
                Drop a folder with up to 2,000 photos
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-[#e94560] flex items-center justify-center text-white font-bold shrink-0">
              2
            </div>
            <div>
              <h4 className="font-medium text-[var(--text-primary)]">AI Analysis</h4>
              <p className="text-sm text-[var(--text-muted)]">
                Grid-based visual analysis identifies standouts
              </p>
            </div>
          </div>
          <div className="flex gap-3">
            <div className="w-8 h-8 rounded-full bg-[#e94560] flex items-center justify-center text-white font-bold shrink-0">
              3
            </div>
            <div>
              <h4 className="font-medium text-[var(--text-primary)]">Review & Score</h4>
              <p className="text-sm text-[var(--text-muted)]">
                Download selected or proceed to detailed scoring
              </p>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
