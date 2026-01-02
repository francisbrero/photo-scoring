import { useState, useMemo, useCallback } from 'react';
import type { Photo, SortOption } from '../types/photo';

interface UseFiltersResult {
  sortBy: SortOption;
  setSortBy: (sort: SortOption) => void;
  sortedPhotos: Photo[];
  stats: {
    count: number;
    avg: number;
    min: number;
    max: number;
  };
}

export function useFilters(photos: Photo[]): UseFiltersResult {
  const [sortBy, setSortBy] = useState<SortOption>('score_desc');

  const sortedPhotos = useMemo(() => {
    if (!photos || !Array.isArray(photos)) {
      return [];
    }
    const sorted = [...photos];

    switch (sortBy) {
      case 'score_desc':
        sorted.sort((a, b) => b.final_score - a.final_score);
        break;
      case 'score_asc':
        sorted.sort((a, b) => a.final_score - b.final_score);
        break;
      case 'name':
        sorted.sort((a, b) => a.image_path.localeCompare(b.image_path));
        break;
      case 'aesthetic':
        sorted.sort((a, b) => b.aesthetic_score - a.aesthetic_score);
        break;
      case 'technical':
        sorted.sort((a, b) => b.technical_score - a.technical_score);
        break;
    }

    return sorted;
  }, [photos, sortBy]);

  const stats = useMemo(() => {
    if (!photos || !Array.isArray(photos) || photos.length === 0) {
      return { count: 0, avg: 0, min: 0, max: 0 };
    }

    const scores = photos.map((p) => p.final_score);
    return {
      count: photos.length,
      avg: scores.reduce((a, b) => a + b, 0) / scores.length,
      min: Math.min(...scores),
      max: Math.max(...scores),
    };
  }, [photos]);

  const handleSetSortBy = useCallback((sort: SortOption) => {
    setSortBy(sort);
  }, []);

  return {
    sortBy,
    setSortBy: handleSetSortBy,
    sortedPhotos,
    stats,
  };
}
