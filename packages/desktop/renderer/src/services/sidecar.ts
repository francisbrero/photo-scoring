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
