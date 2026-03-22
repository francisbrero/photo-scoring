import { useState, useCallback, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import heic2any from 'heic2any';
import { useTriage } from '../hooks/useTriage';
import { useAuth } from '../contexts/AuthContext';
import { calculateTriageCredits } from '../types/triage';
import type { TriageConfig } from '../types/triage';

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];
const HEIC_TYPES = ['image/heic', 'image/heif'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

function isHeicFile(file: File): boolean {
  if (HEIC_TYPES.includes(file.type)) return true;
  const ext = file.name.toLowerCase().split('.').pop();
  return ext === 'heic' || ext === 'heif';
}

async function convertHeicToJpeg(file: File): Promise<string> {
  try {
    const blob = await heic2any({ blob: file, toType: 'image/jpeg', quality: 0.8 });
    const resultBlob = Array.isArray(blob) ? blob[0] : blob;
    return URL.createObjectURL(resultBlob);
  } catch {
    return '';
  }
}

interface SelectedFile {
  file: File;
  preview: string;
}

export default function Triage() {
  const navigate = useNavigate();
  const { credits } = useAuth();
  const {
    isStarting,
    isUploading,
    uploadProgress,
    isProcessing,
    isDownloading,
    isLoadingActiveJobs,
    activeJobs,
    job,
    status,
    results,
    error,
    startTriage,
    resumeJob,
    downloadSelected,
    cancelTriage,
    proceedToScoring,
    reset,
  } = useTriage();

  // Local state for file selection step
  const [files, setFiles] = useState<SelectedFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({ current: 0, total: 0, fileName: '' });
  const [target, setTarget] = useState('25%');
  const [criteria, setCriteria] = useState('standout');
  const [passes, setPasses] = useState<1 | 2>(2);
  const fileInputRef = useRef<HTMLInputElement>(null);

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type) && !isHeicFile(file)) {
      return 'File type not supported. Use JPEG, PNG, HEIC, or WebP.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds 50MB limit.';
    }
    return null;
  };

  const addFiles = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);
    setIsProcessingFiles(true);
    setProcessingProgress({ current: 0, total: fileArray.length, fileName: '' });

    const selected: SelectedFile[] = [];
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const err = validateFile(file);
      if (err) continue; // skip invalid files

      const isHeic = isHeicFile(file);
      setProcessingProgress({
        current: i,
        total: fileArray.length,
        fileName: isHeic ? `Converting ${file.name}` : `Processing ${file.name}`,
      });

      const preview = isHeic ? await convertHeicToJpeg(file) : URL.createObjectURL(file);
      selected.push({ file, preview });
    }

    setFiles((prev) => [...prev, ...selected]);
    setIsProcessingFiles(false);
    setProcessingProgress({ current: 0, total: 0, fileName: '' });
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(true);
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setIsDragging(false);
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      setIsDragging(false);
      if (e.dataTransfer.files.length > 0) addFiles(e.dataTransfer.files);
    },
    [addFiles]
  );

  const handleFileSelect = useCallback(
    (e: React.ChangeEvent<HTMLInputElement>) => {
      if (e.target.files && e.target.files.length > 0) addFiles(e.target.files);
    },
    [addFiles]
  );

  const removeFile = useCallback((index: number) => {
    setFiles((prev) => {
      const next = [...prev];
      URL.revokeObjectURL(next[index].preview);
      next.splice(index, 1);
      return next;
    });
  }, []);

  const handleStart = async () => {
    if (files.length === 0) return;
    const config: TriageConfig = { target, criteria, passes };
    await startTriage(
      files.map((f) => f.file),
      config
    );
  };

  const handleProceed = async () => {
    if (!results) return;
    const resp = await proceedToScoring(results.job_id);
    if (resp) navigate('/dashboard');
  };

  const estimatedCredits = calculateTriageCredits(files.length);

  // --- Determine which step to render ---

  // Error state
  if (error && !isProcessing && !isUploading && !isStarting) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Triage</h1>
        </div>
        <div className="bg-red-500/10 border border-red-500/30 rounded-xl p-8 text-center">
          <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-red-500/20 flex items-center justify-center">
            <svg className="w-8 h-8 text-red-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L4.082 16.5c-.77.833.192 2.5 1.732 2.5z" />
            </svg>
          </div>
          <p className="text-red-400 text-lg mb-6">{error}</p>
          <button
            onClick={reset}
            className="px-6 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors"
          >
            Try Again
          </button>
        </div>
      </div>
    );
  }

  // Results state
  if (results) {
    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Triage Results</h1>
          <p className="text-[var(--text-secondary)]">
            Your photos have been triaged. Review the selected photos below.
          </p>
        </div>

        {/* Summary Stats */}
        <div className="grid grid-cols-3 gap-4 mb-8">
          <div className="bg-[var(--bg-secondary)] rounded-lg p-4 text-center border border-[var(--border-color)]">
            <p className="text-2xl font-bold text-[var(--text-primary)]">{results.total_input}</p>
            <p className="text-sm text-[var(--text-muted)]">Total Input</p>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-lg p-4 text-center border border-[var(--border-color)]">
            <p className="text-2xl font-bold text-[var(--text-primary)]">{results.pass1_survivors}</p>
            <p className="text-sm text-[var(--text-muted)]">Pass 1 Survivors</p>
          </div>
          <div className="bg-[var(--bg-secondary)] rounded-lg p-4 text-center border border-[var(--border-color)]">
            <p className="text-2xl font-bold text-[#e94560]">{results.final_selected}</p>
            <p className="text-sm text-[var(--text-muted)]">Final Selected</p>
          </div>
        </div>

        {/* Selected Photos Grid */}
        {results.selected_photos.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">
              Selected Photos ({results.selected_photos.length})
            </h2>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              {results.selected_photos.map((photo) => (
                <div
                  key={photo.id}
                  className="bg-[var(--bg-secondary)] rounded-lg overflow-hidden border border-[var(--border-color)]"
                >
                  {photo.thumbnail_url ? (
                    <img
                      src={photo.thumbnail_url}
                      alt={photo.original_filename}
                      className="w-full h-32 object-cover"
                    />
                  ) : (
                    <div className="w-full h-32 bg-[var(--bg-tertiary)] flex items-center justify-center">
                      <svg className="w-8 h-8 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                      </svg>
                    </div>
                  )}
                  <div className="p-2">
                    <p className="text-xs text-[var(--text-muted)] truncate">{photo.original_filename}</p>
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Action Buttons */}
        <div className="flex gap-4">
          <button
            onClick={() => downloadSelected(results.job_id)}
            disabled={isDownloading}
            className="flex-1 py-3 bg-[var(--bg-secondary)] text-[var(--text-primary)] rounded-lg font-semibold border border-[var(--border-color)] hover:border-[#e94560]/50 transition-colors disabled:opacity-50 flex items-center justify-center gap-2"
          >
            {isDownloading ? (
              <>
                <div className="animate-spin w-5 h-5 border-2 border-[var(--text-primary)] border-t-transparent rounded-full" />
                Downloading...
              </>
            ) : (
              <>
                <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                </svg>
                Download Selected
              </>
            )}
          </button>
          <button
            onClick={handleProceed}
            className="flex-1 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors"
          >
            Score Selected
          </button>
          <button
            onClick={reset}
            className="px-6 py-3 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity"
          >
            New Triage
          </button>
        </div>
      </div>
    );
  }

  // Processing state
  if (isProcessing || isUploading || isStarting) {
    const progressPct = status?.progress?.percentage ?? 0;
    const phase = isUploading
      ? 'Uploading photos...'
      : isStarting
        ? 'Starting triage...'
        : status?.progress?.message ?? 'Processing...';

    return (
      <div className="max-w-4xl mx-auto">
        <div className="mb-8">
          <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Triage</h1>
          <p className="text-[var(--text-secondary)]">Processing your photos...</p>
        </div>

        <div className="bg-[var(--bg-secondary)] rounded-xl p-8 border border-[var(--border-color)]">
          {/* Spinner */}
          <div className="w-16 h-16 mx-auto mb-6 flex items-center justify-center">
            <div className="animate-spin w-12 h-12 border-4 border-[#e94560] border-t-transparent rounded-full" />
          </div>

          {/* Phase */}
          <p className="text-lg text-[var(--text-primary)] text-center mb-4">{phase}</p>

          {/* Upload Progress */}
          {isUploading && uploadProgress && (
            <div className="max-w-md mx-auto mb-4">
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                  style={{ width: `${(uploadProgress.uploaded / uploadProgress.total) * 100}%` }}
                />
              </div>
              <p className="text-sm text-[var(--text-muted)] mt-1 text-center">
                Uploading {uploadProgress.uploaded} / {uploadProgress.total}
                {uploadProgress.currentFile && (
                  <span className="block truncate">{uploadProgress.currentFile}</span>
                )}
              </p>
            </div>
          )}

          {/* Processing Progress */}
          {isProcessing && status?.progress && (
            <div className="max-w-md mx-auto mb-4">
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                  style={{ width: `${progressPct}%` }}
                />
              </div>
              <p className="text-sm text-[var(--text-muted)] mt-1 text-center">
                Step {status.progress.current_step} / {status.progress.total_steps} ({Math.round(progressPct)}%)
              </p>
            </div>
          )}

          {/* Cancel Button */}
          {isProcessing && job && (
            <div className="text-center mt-6">
              <button
                onClick={() => cancelTriage(job.job_id)}
                className="px-6 py-2 text-[var(--text-muted)] hover:text-red-400 transition-colors text-sm"
              >
                Cancel
              </button>
            </div>
          )}
        </div>
      </div>
    );
  }

  // Upload / file selection state (default)
  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Triage</h1>
        <p className="text-[var(--text-secondary)]">
          Upload a batch of photos to quickly identify the best ones. Triage uses AI to select standout photos from large sets.
        </p>
      </div>

      {/* Drop Zone */}
      <div
        onDragOver={handleDragOver}
        onDragLeave={handleDragLeave}
        onDrop={handleDrop}
        onClick={() => !isProcessingFiles && fileInputRef.current?.click()}
        className={`
          border-2 border-dashed rounded-xl p-12 text-center transition-colors
          ${isProcessingFiles ? 'cursor-wait' : 'cursor-pointer'}
          ${isDragging ? 'border-[#e94560] bg-[#e94560]/10' : 'border-[var(--border-color)] hover:border-[#e94560]/50'}
        `}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept={ALLOWED_TYPES.join(',')}
          multiple
          onChange={handleFileSelect}
          className="hidden"
          disabled={isProcessingFiles}
        />

        {isProcessingFiles ? (
          <div className="py-4">
            <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <div className="animate-spin w-12 h-12 border-4 border-[#e94560] border-t-transparent rounded-full" />
            </div>
            <p className="text-lg text-[var(--text-primary)] mb-4">
              Processing {processingProgress.total} file{processingProgress.total !== 1 ? 's' : ''}...
            </p>
            <div className="max-w-xs mx-auto mb-3">
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                  style={{ width: `${((processingProgress.current + 1) / processingProgress.total) * 100}%` }}
                />
              </div>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                {processingProgress.current + 1} / {processingProgress.total}
              </p>
            </div>
            <p className="text-sm text-[var(--text-secondary)]">{processingProgress.fileName}</p>
          </div>
        ) : (
          <>
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
              <svg className="w-8 h-8 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
            </div>
            <p className="text-lg text-[var(--text-primary)] mb-2">
              {isDragging ? 'Drop photos here' : 'Drag & drop photos here'}
            </p>
            <p className="text-sm text-[var(--text-muted)]">
              or click to select files (JPEG, PNG, HEIC, WebP up to 50MB)
            </p>
          </>
        )}
      </div>

      {/* Selected Files Preview */}
      {files.length > 0 && (
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Selected Photos ({files.length})
            </h2>
            <button
              onClick={() => {
                files.forEach((f) => URL.revokeObjectURL(f.preview));
                setFiles([]);
              }}
              className="text-sm text-[var(--text-muted)] hover:text-red-400 transition-colors"
            >
              Clear All
            </button>
          </div>

          <div className="grid grid-cols-3 md:grid-cols-6 gap-3">
            {files.map((f, i) => (
              <div key={i} className="relative bg-[var(--bg-secondary)] rounded-lg overflow-hidden">
                <img src={f.preview} alt={f.file.name} className="w-full h-20 object-cover" />
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    removeFile(i);
                  }}
                  className="absolute top-1 right-1 w-5 h-5 bg-red-500 rounded-full flex items-center justify-center text-white hover:bg-red-600 text-xs"
                >
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
                <div className="p-1">
                  <p className="text-[10px] text-[var(--text-muted)] truncate">{f.file.name}</p>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Config Controls */}
      {files.length > 0 && (
        <div className="mt-6 bg-[var(--bg-secondary)] rounded-xl p-6 border border-[var(--border-color)]">
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Triage Settings</h3>
          <div className="grid grid-cols-3 gap-4">
            <div>
              <label className="block text-sm text-[var(--text-secondary)] mb-1">Target Selection</label>
              <select
                value={target}
                onChange={(e) => setTarget(e.target.value)}
                className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg px-3 py-2 border border-[var(--border-color)] focus:border-[#e94560] focus:outline-none"
              >
                <option value="10%">Top 10%</option>
                <option value="25%">Top 25%</option>
                <option value="50%">Top 50%</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--text-secondary)] mb-1">Criteria</label>
              <select
                value={criteria}
                onChange={(e) => setCriteria(e.target.value)}
                className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg px-3 py-2 border border-[var(--border-color)] focus:border-[#e94560] focus:outline-none"
              >
                <option value="standout">Standout</option>
                <option value="quality">Quality</option>
              </select>
            </div>
            <div>
              <label className="block text-sm text-[var(--text-secondary)] mb-1">Passes</label>
              <select
                value={passes}
                onChange={(e) => setPasses(Number(e.target.value) as 1 | 2)}
                className="w-full bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg px-3 py-2 border border-[var(--border-color)] focus:border-[#e94560] focus:outline-none"
              >
                <option value={1}>1 Pass (faster)</option>
                <option value={2}>2 Passes (more accurate)</option>
              </select>
            </div>
          </div>

          {/* Credit Estimate & Start */}
          <div className="mt-6 flex items-center justify-between">
            <div className="text-sm text-[var(--text-secondary)]">
              Estimated cost: <span className="text-[#e94560] font-semibold">{estimatedCredits} credit{estimatedCredits !== 1 ? 's' : ''}</span>
              {credits !== null && (
                <span className="ml-2 text-[var(--text-muted)]">
                  (you have <span className={credits < estimatedCredits ? 'text-red-400' : 'text-green-400'}>{credits}</span>)
                </span>
              )}
            </div>
            <button
              onClick={handleStart}
              disabled={files.length === 0 || (credits !== null && credits < estimatedCredits)}
              className="px-8 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              Start Triage
            </button>
          </div>
          {credits !== null && credits < estimatedCredits && (
            <p className="text-red-400 text-sm mt-2 text-right">Not enough credits.</p>
          )}
        </div>
      )}

      {/* Active Jobs */}
      {(activeJobs.length > 0 || isLoadingActiveJobs) && (
        <div className="mt-8">
          <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">Active Jobs</h2>
          {isLoadingActiveJobs ? (
            <div className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-color)]">
              <p className="text-[var(--text-muted)] text-sm">Loading active jobs...</p>
            </div>
          ) : (
            <div className="space-y-3">
              {activeJobs.map((j) => (
                <div
                  key={j.job_id}
                  className="bg-[var(--bg-secondary)] rounded-lg p-4 border border-[var(--border-color)] flex items-center justify-between"
                >
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <span className="text-sm font-medium text-[var(--text-primary)]">
                        {j.total_input} photos
                      </span>
                      <span className="text-xs px-2 py-0.5 rounded-full bg-amber-500/20 text-amber-400">
                        {j.phase}
                      </span>
                    </div>
                    <div className="h-1.5 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                      <div
                        className="h-full bg-[#e94560] rounded-full transition-all"
                        style={{ width: `${j.progress_percentage}%` }}
                      />
                    </div>
                    <p className="text-xs text-[var(--text-muted)] mt-1">
                      {Math.round(j.progress_percentage)}% complete
                    </p>
                  </div>
                  <button
                    onClick={() => resumeJob(j.job_id)}
                    className="ml-4 px-4 py-2 bg-[#e94560] text-white rounded-lg text-sm font-medium hover:bg-[#c73e54] transition-colors"
                  >
                    Resume
                  </button>
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
