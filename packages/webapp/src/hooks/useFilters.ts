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
        // Put unscored (null) photos at the end
        sorted.sort((a, b) => {
          if (a.final_score === null && b.final_score === null) return 0;
          if (a.final_score === null) return 1;
          if (b.final_score === null) return -1;
          return b.final_score - a.final_score;
        });
        break;
      case 'score_asc':
        // Put unscored (null) photos at the end
        sorted.sort((a, b) => {
          if (a.final_score === null && b.final_score === null) return 0;
          if (a.final_score === null) return 1;
          if (b.final_score === null) return -1;
          return a.final_score - b.final_score;
        });
        break;
      case 'name':
        sorted.sort((a, b) => a.image_path.localeCompare(b.image_path));
        break;
      case 'aesthetic':
        sorted.sort((a, b) => {
          if (a.aesthetic_score === null && b.aesthetic_score === null) return 0;
          if (a.aesthetic_score === null) return 1;
          if (b.aesthetic_score === null) return -1;
          return b.aesthetic_score - a.aesthetic_score;
        });
        break;
      case 'technical':
        sorted.sort((a, b) => {
          if (a.technical_score === null && b.technical_score === null) return 0;
          if (a.technical_score === null) return 1;
          if (b.technical_score === null) return -1;
          return b.technical_score - a.technical_score;
        });
        break;
    }

    return sorted;
  }, [photos, sortBy]);

  const stats = useMemo(() => {
    if (!photos || !Array.isArray(photos) || photos.length === 0) {
      return { count: 0, avg: 0, min: 0, max: 0 };
    }

    // Only include scored photos in stats
    const scoredPhotos = photos.filter((p) => p.final_score !== null);
    if (scoredPhotos.length === 0) {
      return { count: photos.length, avg: 0, min: 0, max: 0 };
    }

    const scores = scoredPhotos.map((p) => p.final_score!);
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
