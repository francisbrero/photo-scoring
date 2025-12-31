/**
 * API client with configurable base URL.
 * In development, uses Vite proxy (/api).
 * In production, uses VITE_API_URL environment variable.
 */

const API_BASE_URL = import.meta.env.VITE_API_URL || '';

export function apiUrl(path: string): string {
  // Ensure path starts with /
  const normalizedPath = path.startsWith('/') ? path : `/${path}`;
  return `${API_BASE_URL}${normalizedPath}`;
}

export async function apiFetch(
  path: string,
  options?: RequestInit
): Promise<Response> {
  return fetch(apiUrl(path), options);
}
