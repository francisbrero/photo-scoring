import type { ImageRecord, ScoreResult } from '../types/photo';

let sidecarPort: number | null = null;

async function getBaseUrl(): Promise<string> {
  if (sidecarPort === null) {
    sidecarPort = await window.electron.sidecar.getPort();
  }
  if (sidecarPort === null) {
    throw new Error('Sidecar not running');
  }
  return `http://127.0.0.1:${sidecarPort}`;
}

export async function checkHealth(): Promise<boolean> {
  try {
    const baseUrl = await getBaseUrl();
    const response = await fetch(`${baseUrl}/health`);
    return response.ok;
  } catch {
    return false;
  }
}

export async function discoverPhotos(directory: string): Promise<ImageRecord[]> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/photos/discover?directory=${encodeURIComponent(directory)}`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to discover photos');
  }

  const data = await response.json();
  return data.images;
}

export async function getThumbnail(imagePath: string, size = 300): Promise<string> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/photos/thumbnail?path=${encodeURIComponent(imagePath)}&size=${size}`
  );

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get thumbnail');
  }

  const data = await response.json();
  return `data:image/jpeg;base64,${data.data}`;
}

export async function scorePhoto(imagePath: string, configPath?: string): Promise<ScoreResult> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/inference/score`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: imagePath,
      config_path: configPath,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to score photo');
  }

  return response.json();
}

export async function rescorePhoto(imagePath: string, configPath?: string): Promise<ScoreResult> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/inference/rescore`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      image_path: imagePath,
      config_path: configPath,
    }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to rescore photo');
  }

  return response.json();
}

export async function getAttributes(imagePath: string): Promise<ScoreResult['attributes'] | null> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(
    `${baseUrl}/api/inference/attributes?path=${encodeURIComponent(imagePath)}`
  );

  if (!response.ok) {
    if (response.status === 404) {
      return null;
    }
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get attributes');
  }

  return response.json();
}

export async function getCacheStats(): Promise<{ total_entries: number; cache_size_bytes: number }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/inference/cache/stats`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get cache stats');
  }

  return response.json();
}

export async function clearCache(): Promise<void> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/inference/cache/clear`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to clear cache');
  }
}

export async function getCachedScores(imagePaths: string[]): Promise<Record<string, ScoreResult | null>> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/inference/cached-scores`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ image_paths: imagePaths }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get cached scores');
  }

  const data = await response.json();
  return data.scores;
}

// Auth API

export interface AuthStatus {
  authenticated: boolean;
  user_email: string | null;
  credits: number | null;
}

export interface AuthResponse {
  authenticated: boolean;
  user_email: string;
  credits: number;
  message: string;
}

export async function getAuthStatus(): Promise<AuthStatus> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/status`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get auth status');
  }

  return response.json();
}

export async function login(email: string, password: string): Promise<AuthResponse> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Login failed');
  }

  return response.json();
}

export async function signup(email: string, password: string): Promise<AuthResponse> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/signup`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Signup failed');
  }

  return response.json();
}

export async function logout(): Promise<void> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/logout`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Logout failed');
  }
}

export async function getCredits(): Promise<{ credits: number; cached?: boolean }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/auth/credits`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get credits');
  }

  return response.json();
}

// Triage API

export interface TriageConfig {
  directory: string;
  target: string;
  criteria: string;
  passes: 1 | 2;
}

export interface TriageJob {
  job_id: string;
  status: string;
}

export interface TriageProgress {
  percentage: number;
  message: string;
}

export interface TriageStatus {
  job_id: string;
  status: string;
  total_input: number;
  pass1_survivors: number;
  final_selected: number;
  error_message?: string;
  progress?: TriageProgress;
}

export interface TriagePhoto {
  image_id: string;
  filename: string;
  file_path: string;
  thumbnail?: string;
}

export interface TriageResults {
  job_id: string;
  total_input: number;
  final_selected: number;
  selected_photos: TriagePhoto[];
}

export async function startTriage(config: TriageConfig): Promise<TriageJob> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/triage/start`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(config),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to start triage');
  }

  return response.json();
}

export async function getTriageStatus(jobId: string): Promise<TriageStatus> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/triage/${jobId}/status`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get triage status');
  }

  return response.json();
}

export async function getTriageResults(jobId: string): Promise<TriageResults> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/triage/${jobId}/results`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get triage results');
  }

  return response.json();
}

export async function cancelTriage(jobId: string): Promise<void> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/triage/${jobId}/cancel`, {
    method: 'POST',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to cancel triage');
  }
}

export async function copySelectedPhotos(
  jobId: string,
  destination: string
): Promise<{ copied: number; destination: string }> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/triage/${jobId}/copy`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ destination }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to copy photos');
  }

  return response.json();
}

// Settings API - OpenRouter API Key

export interface ApiKeyStatus {
  is_set: boolean;
  masked_key?: string;
}

export async function getApiKeyStatus(): Promise<ApiKeyStatus> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/api-key`);

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to get API key status');
  }

  return response.json();
}

export async function setApiKey(apiKey: string): Promise<void> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/api-key`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ api_key: apiKey }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to set API key');
  }
}

export async function deleteApiKey(): Promise<void> {
  const baseUrl = await getBaseUrl();
  const response = await fetch(`${baseUrl}/api/settings/api-key`, {
    method: 'DELETE',
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || 'Failed to delete API key');
  }
}
