import { useState, useCallback, useRef, useEffect } from 'react';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';
import { uploadFilesToStorage, deleteUploadedFiles, type UploadProgress } from '../lib/storage';
import type {
  TriageConfig,
  TriageJob,
  TriageStatus,
  TriageResults,
  ProceedResponse,
  ActiveJobSummary,
  ActiveJobsResponse,
} from '../types/triage';

const POLL_INTERVAL = 2000; // Poll every 2 seconds

interface UseTriageReturn {
  // State
  isStarting: boolean;
  isUploading: boolean;
  uploadProgress: UploadProgress | null;
  isProcessing: boolean;
  isLoadingActiveJobs: boolean;
  activeJobs: ActiveJobSummary[];
  job: TriageJob | null;
  status: TriageStatus | null;
  results: TriageResults | null;
  error: string | null;

  // Actions
  startTriage: (files: File[], config: TriageConfig) => Promise<string | null>;
  resumeJob: (jobId: string) => Promise<void>;
  refreshActiveJobs: () => Promise<void>;
  pollStatus: (jobId: string) => Promise<TriageStatus | null>;
  getResults: (jobId: string) => Promise<TriageResults | null>;
  proceedToScoring: (jobId: string, photoIds?: string[]) => Promise<ProceedResponse | null>;
  downloadSelected: (jobId: string) => void;
  cancelTriage: (jobId: string) => Promise<void>;
  reset: () => void;
}

export function useTriage(): UseTriageReturn {
  const { session, user, refreshCredits } = useAuth();
  const [isStarting, setIsStarting] = useState(false);
  const [isUploading, setIsUploading] = useState(false);
  const [uploadProgress, setUploadProgress] = useState<UploadProgress | null>(null);
  const [isProcessing, setIsProcessing] = useState(false);
  const [isLoadingActiveJobs, setIsLoadingActiveJobs] = useState(false);
  const [activeJobs, setActiveJobs] = useState<ActiveJobSummary[]>([]);
  const [job, setJob] = useState<TriageJob | null>(null);
  const [status, setStatus] = useState<TriageStatus | null>(null);
  const [results, setResults] = useState<TriageResults | null>(null);
  const [error, setError] = useState<string | null>(null);
  const pollIntervalRef = useRef<ReturnType<typeof setInterval> | null>(null);
  const hasCheckedActiveJobs = useRef(false);

  // Fetch active jobs from server
  const refreshActiveJobs = useCallback(async () => {
    if (!session?.access_token) return;

    setIsLoadingActiveJobs(true);
    try {
      const response = await apiFetch('/api/triage/active', {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });

      if (response.ok) {
        const data: ActiveJobsResponse = await response.json();
        setActiveJobs(data.jobs);
      }
    } catch {
      // Silently fail - user can still start new jobs
    } finally {
      setIsLoadingActiveJobs(false);
    }
  }, [session?.access_token]);

  // Check for active jobs on mount
  useEffect(() => {
    if (!session?.access_token || hasCheckedActiveJobs.current) return;
    hasCheckedActiveJobs.current = true;

    refreshActiveJobs();
  }, [session?.access_token, refreshActiveJobs]);

  // Clean up polling on unmount
  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }
    };
  }, []);

  const startTriage = useCallback(
    async (files: File[], config: TriageConfig): Promise<string | null> => {
      if (!session?.access_token || !user?.id) {
        setError('Not authenticated');
        return null;
      }

      setIsStarting(true);
      setError(null);

      // Generate a job ID upfront for organizing uploads
      const jobId = crypto.randomUUID();
      let uploadedPaths: string[] = [];

      try {
        // Step 1: Upload files directly to Supabase Storage
        setIsUploading(true);
        setUploadProgress({ uploaded: 0, total: files.length, currentFile: '' });

        const uploadedFiles = await uploadFilesToStorage(
          files,
          user.id,
          jobId,
          (progress) => setUploadProgress(progress)
        );

        uploadedPaths = uploadedFiles.map((f) => f.storagePath);
        setIsUploading(false);
        setUploadProgress(null);

        // Step 2: Call API with storage paths (small JSON payload)
        const response = await apiFetch('/api/triage/start-from-storage', {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            job_id: jobId,
            files: uploadedFiles.map((f) => ({
              original_name: f.originalName,
              storage_path: f.storagePath,
              size: f.size,
            })),
            target: config.target,
            criteria: config.criteria,
            passes: config.passes,
          }),
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to start triage');
        }

        const jobData: TriageJob = await response.json();
        setJob(jobData);
        setIsProcessing(true);
        await refreshCredits();

        // Start polling for status
        startPolling(jobData.job_id);

        return jobData.job_id;
      } catch (err) {
        // Clean up uploaded files on error
        if (uploadedPaths.length > 0) {
          await deleteUploadedFiles(uploadedPaths);
        }
        setError(err instanceof Error ? err.message : 'Unknown error');
        return null;
      } finally {
        setIsStarting(false);
        setIsUploading(false);
        setUploadProgress(null);
      }
    },
    [session?.access_token, user?.id, refreshCredits]
  );

  const startPolling = useCallback(
    (jobId: string) => {
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
      }

      const poll = async () => {
        const statusData = await pollStatus(jobId);
        if (statusData) {
          if (statusData.status === 'completed') {
            // Stop polling and fetch results
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsProcessing(false);
            // Remove from active jobs list
            setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
            await getResults(jobId);
          } else if (statusData.status === 'failed' || statusData.status === 'cancelled') {
            // Stop polling on failure
            if (pollIntervalRef.current) {
              clearInterval(pollIntervalRef.current);
              pollIntervalRef.current = null;
            }
            setIsProcessing(false);
            // Remove from active jobs list
            setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
            setError(statusData.error_message || 'Triage failed');
          }
        }
      };

      // Initial poll
      poll();

      // Start interval
      pollIntervalRef.current = setInterval(poll, POLL_INTERVAL);
    },
    [session?.access_token]
  );

  const resumeJob = useCallback(
    async (jobId: string): Promise<void> => {
      if (!session?.access_token) return;

      setError(null);

      try {
        // Check job status
        const response = await apiFetch(`/api/triage/${jobId}/status`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!response.ok) {
          // Job not found or error - refresh active jobs
          await refreshActiveJobs();
          return;
        }

        const statusData: TriageStatus = await response.json();
        setStatus(statusData);

        if (statusData.status === 'completed') {
          // Job completed - fetch results
          await getResults(jobId);
          // Remove from active jobs list
          setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
        } else if (statusData.status === 'failed' || statusData.status === 'cancelled') {
          // Job failed - show error and refresh list
          setError(statusData.error_message || 'Triage failed');
          setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
        } else {
          // Job still processing - resume polling
          setIsProcessing(true);
          startPolling(jobId);
        }
      } catch {
        await refreshActiveJobs();
      }
    },
    [session?.access_token, refreshActiveJobs]
  );

  const pollStatus = useCallback(
    async (jobId: string): Promise<TriageStatus | null> => {
      if (!session?.access_token) return null;

      try {
        const response = await apiFetch(`/api/triage/${jobId}/status`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!response.ok) return null;

        const statusData: TriageStatus = await response.json();
        setStatus(statusData);
        return statusData;
      } catch {
        return null;
      }
    },
    [session?.access_token]
  );

  const getResults = useCallback(
    async (jobId: string): Promise<TriageResults | null> => {
      if (!session?.access_token) return null;

      try {
        const response = await apiFetch(`/api/triage/${jobId}/results`, {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to get results');
        }

        const resultsData: TriageResults = await response.json();
        setResults(resultsData);
        return resultsData;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        return null;
      }
    },
    [session?.access_token]
  );

  const proceedToScoring = useCallback(
    async (jobId: string, photoIds?: string[]): Promise<ProceedResponse | null> => {
      if (!session?.access_token) return null;

      try {
        const response = await apiFetch(`/api/triage/${jobId}/proceed`, {
          method: 'POST',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
            'Content-Type': 'application/json',
          },
          body: photoIds ? JSON.stringify({ photo_ids: photoIds }) : undefined,
        });

        if (!response.ok) {
          const errorData = await response.json();
          throw new Error(errorData.detail || 'Failed to proceed to scoring');
        }

        const proceedData: ProceedResponse = await response.json();
        await refreshCredits();
        return proceedData;
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
        return null;
      }
    },
    [session?.access_token, refreshCredits]
  );

  const downloadSelected = useCallback(
    (jobId: string) => {
      if (!session?.access_token) return;

      // Open download in new window/tab
      const url = `/api/triage/${jobId}/download`;
      window.open(url, '_blank');
    },
    [session?.access_token]
  );

  const cancelTriage = useCallback(
    async (jobId: string) => {
      if (!session?.access_token) return;

      // Stop polling
      if (pollIntervalRef.current) {
        clearInterval(pollIntervalRef.current);
        pollIntervalRef.current = null;
      }

      try {
        await apiFetch(`/api/triage/${jobId}`, {
          method: 'DELETE',
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });

        setIsProcessing(false);
        setJob(null);
        setStatus(null);
        // Remove from active jobs list
        setActiveJobs((prev) => prev.filter((j) => j.job_id !== jobId));
      } catch {
        // Ignore errors on cancel
      }
    },
    [session?.access_token]
  );

  const reset = useCallback(() => {
    if (pollIntervalRef.current) {
      clearInterval(pollIntervalRef.current);
      pollIntervalRef.current = null;
    }
    setIsStarting(false);
    setIsUploading(false);
    setUploadProgress(null);
    setIsProcessing(false);
    setJob(null);
    setStatus(null);
    setResults(null);
    setError(null);
  }, []);

  return {
    isStarting,
    isUploading,
    uploadProgress,
    isProcessing,
    isLoadingActiveJobs,
    activeJobs,
    job,
    status,
    results,
    error,
    startTriage,
    resumeJob,
    refreshActiveJobs,
    pollStatus,
    getResults,
    proceedToScoring,
    downloadSelected,
    cancelTriage,
    reset,
  };
}
