import { useState, useEffect } from 'react';
import type { Photo } from '../types/photo';
import { apiFetch } from '../lib/api';

interface UsePhotosResult {
  photos: Photo[];
  loading: boolean;
  error: string | null;
}

export function usePhotos(): UsePhotosResult {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function fetchPhotos() {
      try {
        // In development, fetch from API
        // In production with embedded data, use window.__PHOTOS_DATA__
        const windowWithData = window as Window & { __PHOTOS_DATA__?: Photo[] };
        if (typeof window !== 'undefined' && windowWithData.__PHOTOS_DATA__) {
          setPhotos(windowWithData.__PHOTOS_DATA__);
          setLoading(false);
          return;
        }

        const response = await apiFetch('/api/photos');
        if (!response.ok) {
          throw new Error(`Failed to fetch photos: ${response.statusText}`);
        }
        const data = await response.json();
        setPhotos(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load photos');
      } finally {
        setLoading(false);
      }
    }

    fetchPhotos();
  }, []);

  return { photos, loading, error };
}
