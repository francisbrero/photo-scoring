/**
 * Types for the Triage feature.
 */

export interface TriageConfig {
  target: string;  // e.g., "10%" or "50"
  criteria: string;  // e.g., "standout", "quality", or custom
  passes: 1 | 2;
}

export interface TriageProgress {
  phase: 'uploading' | 'grid_generation' | 'coarse_pass' | 'fine_pass' | 'complete';
  current_step: number;
  total_steps: number;
  percentage: number;
  message: string;
}

export interface TriagePhoto {
  id: string;
  original_filename: string;
  storage_path: string;
  thumbnail_url: string | null;
}

export interface TriageJob {
  job_id: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed' | 'cancelled';
  photo_count: number;
  credits_deducted: number;
  estimated_grids: number;
}

export interface TriageStatus {
  job_id: string;
  status: 'pending' | 'uploading' | 'processing' | 'completed' | 'failed' | 'cancelled';
  progress: TriageProgress | null;
  total_input: number;
  pass1_survivors: number;
  final_selected: number;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface TriageResults {
  job_id: string;
  status: string;
  selected_photos: TriagePhoto[];
  total_input: number;
  pass1_survivors: number;
  final_selected: number;
  target: string;
  criteria: string;
}

export interface ProceedResponse {
  queued_count: number;
  credits_deducted: number;
}

export interface ActiveJobSummary {
  job_id: string;
  status: 'pending' | 'processing';
  total_input: number;
  progress_percentage: number;
  phase: string;
  created_at: string;
}

export interface ActiveJobsResponse {
  jobs: ActiveJobSummary[];
}

/**
 * Calculate credits needed for a triage job.
 */
export function calculateTriageCredits(photoCount: number): number {
  if (photoCount <= 100) return 1;
  if (photoCount <= 500) return 3;
  if (photoCount <= 1000) return 5;
  if (photoCount <= 2000) return 8;
  return 10;
}
