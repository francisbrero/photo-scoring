import { useState, useEffect } from 'react';
import type { Photo } from '../types/photo';
import { apiFetch } from '../lib/api';
import { useAuth } from '../contexts/AuthContext';

interface UsePhotosResult {
  photos: Photo[];
  loading: boolean;
  error: string | null;
  refetch: () => void;
}

export function usePhotos(): UsePhotosResult {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const { session } = useAuth();

  const fetchPhotos = async () => {
    // In production with embedded data, use window.__PHOTOS_DATA__
    const windowWithData = window as Window & { __PHOTOS_DATA__?: Photo[] };
    if (typeof window !== 'undefined' && windowWithData.__PHOTOS_DATA__) {
      setPhotos(windowWithData.__PHOTOS_DATA__);
      setLoading(false);
      return;
    }

    if (!session?.access_token) {
      setLoading(false);
      return;
    }

    try {
      const response = await apiFetch('/api/photos', {
        headers: {
          Authorization: `Bearer ${session.access_token}`,
        },
      });
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
  };

  useEffect(() => {
    fetchPhotos();
  }, [session?.access_token]);

  return { photos, loading, error, refetch: fetchPhotos };
}
