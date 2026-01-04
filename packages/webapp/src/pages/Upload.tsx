import { useState, useCallback, useRef, useEffect } from 'react';
import { Link } from 'react-router-dom';
import heic2any from 'heic2any';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch } from '../lib/api';

const POLL_INTERVAL = 2000; // Poll every 2 seconds

interface UploadFile {
  file: File;
  preview: string;
  status: 'pending' | 'uploading' | 'queued' | 'processing' | 'done' | 'error';
  progress: number;
  error?: string;
  photoId?: string;
  queuePosition?: number;
}

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/heic', 'image/heif', 'image/webp'];
const HEIC_TYPES = ['image/heic', 'image/heif'];
const MAX_FILE_SIZE = 50 * 1024 * 1024; // 50MB

/**
 * Check if a file is HEIC/HEIF format (by type or extension)
 */
function isHeicFile(file: File): boolean {
  if (HEIC_TYPES.includes(file.type)) return true;
  const ext = file.name.toLowerCase().split('.').pop();
  return ext === 'heic' || ext === 'heif';
}

/**
 * Convert HEIC file to JPEG blob for preview
 */
async function convertHeicToJpeg(file: File): Promise<string> {
  try {
    const blob = await heic2any({
      blob: file,
      toType: 'image/jpeg',
      quality: 0.8,
    });
    // heic2any can return an array of blobs for multi-image HEIC
    const resultBlob = Array.isArray(blob) ? blob[0] : blob;
    return URL.createObjectURL(resultBlob);
  } catch (error) {
    console.error('Failed to convert HEIC:', error);
    // Return a placeholder or empty string on failure
    return '';
  }
}

export function Upload() {
  const [files, setFiles] = useState<UploadFile[]>([]);
  const [isDragging, setIsDragging] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [isProcessingFiles, setIsProcessingFiles] = useState(false);
  const [processingProgress, setProcessingProgress] = useState({ current: 0, total: 0, fileName: '' });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const { session, credits, refreshCredits } = useAuth();

  const validateFile = (file: File): string | null => {
    if (!ALLOWED_TYPES.includes(file.type)) {
      return 'File type not supported. Use JPEG, PNG, HEIC, or WebP.';
    }
    if (file.size > MAX_FILE_SIZE) {
      return 'File size exceeds 50MB limit.';
    }
    return null;
  };

  const addFiles = useCallback(async (newFiles: FileList | File[]) => {
    const fileArray = Array.from(newFiles);

    // Start processing state
    setIsProcessingFiles(true);
    setProcessingProgress({ current: 0, total: fileArray.length, fileName: '' });

    // Process files one by one to show progress
    const uploadFiles: UploadFile[] = [];
    for (let i = 0; i < fileArray.length; i++) {
      const file = fileArray[i];
      const error = validateFile(file);

      // Update progress with current file
      const isHeic = isHeicFile(file);
      setProcessingProgress({
        current: i,
        total: fileArray.length,
        fileName: isHeic ? `Converting ${file.name}` : `Processing ${file.name}`
      });

      // For HEIC files, convert to JPEG for preview
      let preview: string;
      if (isHeic && !error) {
        preview = await convertHeicToJpeg(file);
      } else {
        preview = URL.createObjectURL(file);
      }

      uploadFiles.push({
        file,
        preview,
        status: error ? 'error' : 'pending',
        progress: 0,
        error: error || undefined,
      } as UploadFile);
    }

    setFiles((prev) => [...prev, ...uploadFiles]);
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
      if (e.dataTransfer.files.length > 0) {
        addFiles(e.dataTransfer.files);
      }
    },
    [addFiles]
  );

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

  // Poll for status of queued files
  useEffect(() => {
    const queuedOrProcessing = files.filter(
      (f) => f.status === 'queued' || f.status === 'processing'
    );

    if (queuedOrProcessing.length === 0 || !session?.access_token) {
      return;
    }

    const pollInterval = setInterval(async () => {
      for (const uploadFile of queuedOrProcessing) {
        if (!uploadFile.photoId) continue;

        try {
          const response = await apiFetch(`/api/photos/${uploadFile.photoId}/status`, {
            headers: {
              Authorization: `Bearer ${session.access_token}`,
            },
          });

          if (!response.ok) continue;

          const status = await response.json();
          const fileIndex = files.findIndex((f) => f.photoId === uploadFile.photoId);

          if (fileIndex === -1) continue;

          if (status.status === 'completed') {
            setFiles((prev) => {
              const newFiles = [...prev];
              newFiles[fileIndex] = {
                ...newFiles[fileIndex],
                status: 'done',
                progress: 100,
              };
              return newFiles;
            });
            // Refresh credits after completion
            await refreshCredits();
          } else if (status.status === 'failed') {
            setFiles((prev) => {
              const newFiles = [...prev];
              newFiles[fileIndex] = {
                ...newFiles[fileIndex],
                status: 'error',
                error: status.error_message || 'Scoring failed',
              };
              return newFiles;
            });
          } else if (status.status === 'processing') {
            setFiles((prev) => {
              const newFiles = [...prev];
              newFiles[fileIndex] = {
                ...newFiles[fileIndex],
                status: 'processing',
                progress: 75,
              };
              return newFiles;
            });
          } else if (status.status === 'pending') {
            setFiles((prev) => {
              const newFiles = [...prev];
              newFiles[fileIndex] = {
                ...newFiles[fileIndex],
                queuePosition: status.position,
              };
              return newFiles;
            });
          }
        } catch {
          // Ignore polling errors
        }
      }
    }, POLL_INTERVAL);

    return () => clearInterval(pollInterval);
  }, [files, session?.access_token, refreshCredits]);

  const uploadAndScoreFiles = async () => {
    if (!session?.access_token) {
      return;
    }

    setIsUploading(true);
    const pendingFiles = files.filter((f) => f.status === 'pending');

    for (let i = 0; i < pendingFiles.length; i++) {
      const uploadFile = pendingFiles[i];
      const fileIndex = files.findIndex((f) => f === uploadFile);

      // Update status to uploading
      setFiles((prev) => {
        const newFiles = [...prev];
        newFiles[fileIndex] = { ...newFiles[fileIndex], status: 'uploading', progress: 0 };
        return newFiles;
      });

      try {
        // Create form data
        const formData = new FormData();
        formData.append('file', uploadFile.file);

        // Upload to backend
        const response = await apiFetch('/api/photos/upload', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
          body: formData,
        });

        if (!response.ok) {
          const error = await response.json();
          throw new Error(error.detail || 'Upload failed');
        }

        const result = await response.json();

        // Queue for scoring (background processing)
        const queueResponse = await apiFetch(`/api/photos/${result.id}/score/queue`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!queueResponse.ok) {
          const error = await queueResponse.json();
          throw new Error(error.detail || 'Failed to queue for scoring');
        }

        const queueResult = await queueResponse.json();

        // Update status to queued - polling will handle the rest
        setFiles((prev) => {
          const newFiles = [...prev];
          newFiles[fileIndex] = {
            ...newFiles[fileIndex],
            status: 'queued',
            progress: 50,
            photoId: result.id,
            queuePosition: queueResult.position,
          };
          return newFiles;
        });

        // Refresh credits after queuing (credit was deducted)
        await refreshCredits();
      } catch (error) {
        setFiles((prev) => {
          const newFiles = [...prev];
          newFiles[fileIndex] = {
            ...newFiles[fileIndex],
            status: 'error',
            error: error instanceof Error ? error.message : 'Unknown error',
          };
          return newFiles;
        });
      }
    }

    setIsUploading(false);
  };

  const completedCount = files.filter((f) => f.status === 'done').length;
  const pendingCount = files.filter((f) => f.status === 'pending').length;

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Upload Photos</h1>
        <p className="text-[var(--text-secondary)]">
          Drop your photos here or click to select. Each photo uses 1 credit.
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
          disabled={isProcessingFiles}
        />

        {isProcessingFiles ? (
          /* Processing State */
          <div className="py-4">
            {/* Spinner */}
            <div className="w-16 h-16 mx-auto mb-4 flex items-center justify-center">
              <div className="animate-spin w-12 h-12 border-4 border-[#e94560] border-t-transparent rounded-full" />
            </div>

            {/* Title */}
            <p className="text-lg text-[var(--text-primary)] mb-4">
              Processing {processingProgress.total} file{processingProgress.total !== 1 ? 's' : ''}...
            </p>

            {/* Progress Bar */}
            <div className="max-w-xs mx-auto mb-3">
              <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                <div
                  className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                  style={{
                    width: `${((processingProgress.current + 1) / processingProgress.total) * 100}%`
                  }}
                />
              </div>
              <p className="text-sm text-[var(--text-muted)] mt-1">
                {processingProgress.current + 1} / {processingProgress.total}
              </p>
            </div>

            {/* Current Step */}
            <p className="text-sm text-[var(--text-secondary)] flex items-center justify-center gap-2">
              <span className="inline-block">🔄</span>
              {processingProgress.fileName}
            </p>
          </div>
        ) : (
          /* Default State */
          <>
            <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-[var(--bg-tertiary)] flex items-center justify-center">
              <svg
                className="w-8 h-8 text-[var(--text-muted)]"
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12"
                />
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

      {/* File List */}
      {files.length > 0 && (
        <div className="mt-8">
          <div className="flex justify-between items-center mb-4">
            <h2 className="text-xl font-semibold text-[var(--text-primary)]">
              Selected Photos ({files.length})
            </h2>
            {completedCount === files.length && files.length > 0 && (
              <Link
                to="/dashboard"
                className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 transition-colors"
              >
                View Results
              </Link>
            )}
          </div>

          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            {files.map((uploadFile, index) => (
              <div
                key={index}
                className="relative bg-[var(--bg-secondary)] rounded-lg overflow-hidden"
              >
                <img
                  src={uploadFile.preview}
                  alt={uploadFile.file.name}
                  className="w-full h-32 object-cover"
                />
                {/* Status Overlay */}
                <div
                  className={`absolute inset-0 flex items-center justify-center ${
                    uploadFile.status === 'pending' ? 'bg-black/0' : 'bg-black/50'
                  }`}
                >
                  {uploadFile.status === 'uploading' && (
                    <div className="text-white text-center">
                      <div className="animate-spin w-8 h-8 border-2 border-white border-t-transparent rounded-full mx-auto mb-2" />
                      <span className="text-sm">Uploading...</span>
                    </div>
                  )}
                  {uploadFile.status === 'queued' && (
                    <div className="text-white text-center">
                      <div className="w-8 h-8 bg-amber-500 rounded-full mx-auto mb-2 flex items-center justify-center">
                        <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
                        </svg>
                      </div>
                      <span className="text-sm">Queued{uploadFile.queuePosition ? ` (#${uploadFile.queuePosition})` : ''}</span>
                    </div>
                  )}
                  {uploadFile.status === 'processing' && (
                    <div className="text-white text-center">
                      <div className="animate-pulse w-8 h-8 bg-[#e94560] rounded-full mx-auto mb-2" />
                      <span className="text-sm">Scoring...</span>
                    </div>
                  )}
                  {uploadFile.status === 'done' && (
                    <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center">
                      <svg className="w-6 h-6 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                      </svg>
                    </div>
                  )}
                  {uploadFile.status === 'error' && (
                    <div className="text-red-400 text-center p-2">
                      <svg className="w-8 h-8 mx-auto mb-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                      </svg>
                      <span className="text-xs">{uploadFile.error}</span>
                    </div>
                  )}
                </div>
                {/* Remove Button */}
                {uploadFile.status === 'pending' && (
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      removeFile(index);
                    }}
                    className="absolute top-2 right-2 w-6 h-6 bg-red-500 rounded-full flex items-center justify-center text-white hover:bg-red-600"
                  >
                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                )}
                {/* File Name */}
                <div className="p-2">
                  <p className="text-xs text-[var(--text-muted)] truncate">
                    {uploadFile.file.name}
                  </p>
                </div>
              </div>
            ))}
          </div>

          {/* Upload Progress Bar (shown during upload/queued/processing) */}
          {(isUploading || files.some(f => f.status === 'queued' || f.status === 'processing')) && (
            <div className="mt-6 p-4 bg-[var(--bg-secondary)] rounded-lg border border-[var(--border-color)]">
              {(() => {
                const uploadingFile = files.find(f => f.status === 'uploading');
                const queuedFile = files.find(f => f.status === 'queued');
                const processingFile = files.find(f => f.status === 'processing');
                const currentFile = uploadingFile || processingFile || queuedFile;
                const doneCount = files.filter(f => f.status === 'done').length;
                const queuedCount = files.filter(f => f.status === 'queued').length;
                const processingCount = files.filter(f => f.status === 'processing').length;
                const totalToProcess = files.filter(f => f.status !== 'error').length;
                const currentStep = uploadingFile ? 'Uploading' : processingFile ? 'Scoring' : queuedFile ? 'Queued' : 'Processing';
                const stepIcon = uploadingFile ? '⬆️' : processingFile ? '⭐' : queuedFile ? '⏳' : '🔄';

                return (
                  <>
                    {/* Progress Bar */}
                    <div className="mb-3">
                      <div className="h-2 bg-[var(--bg-tertiary)] rounded-full overflow-hidden">
                        <div
                          className="h-full bg-[#e94560] rounded-full transition-all duration-300"
                          style={{
                            width: `${(doneCount / totalToProcess) * 100}%`
                          }}
                        />
                      </div>
                      <p className="text-sm text-[var(--text-muted)] mt-1 text-center">
                        {doneCount} / {totalToProcess} completed
                        {(queuedCount > 0 || processingCount > 0) && (
                          <span className="ml-2">
                            ({processingCount > 0 ? `${processingCount} scoring` : ''}{processingCount > 0 && queuedCount > 0 ? ', ' : ''}{queuedCount > 0 ? `${queuedCount} queued` : ''})
                          </span>
                        )}
                      </p>
                    </div>

                    {/* Current Step */}
                    {currentFile && (
                      <p className="text-sm text-[var(--text-secondary)] flex items-center justify-center gap-2">
                        <span>{stepIcon}</span>
                        <span>{currentStep}</span>
                        <span className="text-[var(--text-muted)] truncate max-w-[200px]">
                          {currentFile.file.name}
                        </span>
                      </p>
                    )}

                    {/* Background processing note */}
                    {!isUploading && (queuedCount > 0 || processingCount > 0) && (
                      <p className="text-xs text-[var(--text-muted)] mt-3 text-center">
                        Processing continues in the background. You can navigate away safely.
                      </p>
                    )}
                  </>
                );
              })()}
            </div>
          )}

          {/* Action Buttons */}
          <div className="mt-6 flex gap-4">
            <button
              onClick={uploadAndScoreFiles}
              disabled={isUploading || pendingCount === 0}
              className="flex-1 py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isUploading
                ? 'Processing...'
                : `Upload & Score ${pendingCount} Photo${pendingCount !== 1 ? 's' : ''}`}
            </button>
            <button
              onClick={() => setFiles([])}
              disabled={isUploading}
              className="px-6 py-3 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity disabled:opacity-50"
            >
              Clear All
            </button>
          </div>

          {/* Credits Info */}
          <div className="mt-4 text-sm text-center">
            {credits !== null && (
              <p className="text-[var(--text-secondary)] mb-1">
                Credits available: <span className={credits < pendingCount ? 'text-red-400' : 'text-green-400'}>{credits}</span>
              </p>
            )}
            <p className="text-[var(--text-muted)]">
              This will use {pendingCount} credit{pendingCount !== 1 ? 's' : ''} from your account.
            </p>
            {credits !== null && credits < pendingCount && (
              <p className="text-red-400 mt-2">
                Not enough credits! You need {pendingCount - credits} more credit{pendingCount - credits !== 1 ? 's' : ''}.
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
