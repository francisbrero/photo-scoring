import { useState, useEffect, useCallback } from 'react';
import type { Photo, Correction } from '../types/photo';

const STORAGE_KEY = 'photo_corrections';

interface UseCorrectionsResult {
  corrections: Record<string, Correction>;
  updateCorrection: (
    imagePath: string,
    field: keyof Correction,
    value: string | number,
    photo?: Photo
  ) => void;
  getCorrection: (imagePath: string) => Correction | undefined;
  exportCorrections: () => void;
  exportCSV: (photos: Photo[]) => void;
  correctionsCount: number;
}

function loadCorrectionsFromStorage(): Record<string, Correction> {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (saved) {
      return JSON.parse(saved);
    }
  } catch (e) {
    console.error('Failed to parse saved corrections:', e);
  }
  return {};
}

export function useCorrections(): UseCorrectionsResult {
  const [corrections, setCorrections] = useState<Record<string, Correction>>(
    loadCorrectionsFromStorage
  );

  // Save to localStorage when corrections change
  useEffect(() => {
    if (Object.keys(corrections).length > 0) {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(corrections));
    }
  }, [corrections]);

  const updateCorrection = useCallback(
    (
      imagePath: string,
      field: keyof Correction,
      value: string | number,
      photo?: Photo
    ) => {
      setCorrections((prev) => {
        const existing = prev[imagePath] || {
          image_path: imagePath,
          timestamp: new Date().toISOString(),
        };

        // If this is a new correction and we have photo data, store original values
        if (!prev[imagePath] && photo) {
          existing.original_score = photo.final_score ?? undefined;
          existing.original_aesthetic = photo.aesthetic_score ?? undefined;
          existing.original_technical = photo.technical_score ?? undefined;
        }

        return {
          ...prev,
          [imagePath]: {
            ...existing,
            [field]: field === 'notes' ? value : parseFloat(String(value)),
            timestamp: new Date().toISOString(),
          },
        };
      });
    },
    []
  );

  const getCorrection = useCallback(
    (imagePath: string) => corrections[imagePath],
    [corrections]
  );

  const exportCorrections = useCallback(() => {
    const data = {
      exported_at: new Date().toISOString(),
      corrections_count: Object.keys(corrections).length,
      corrections: Object.values(corrections),
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `photo_corrections_${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  }, [corrections]);

  const exportCSV = useCallback(
    (photos: Photo[]) => {
      const headers = [
        'image_path',
        'final_score',
        'aesthetic_score',
        'technical_score',
        'composition',
        'subject_strength',
        'visual_appeal',
        'sharpness',
        'exposure',
        'noise_level',
        'scene_type',
        'lighting',
        'subject_position',
        'description',
        'location_name',
        'location_country',
        'human_score',
        'human_composition',
        'human_subject',
        'human_appeal',
        'human_notes',
      ];

      let csv = headers.join(',') + '\n';

      for (const photo of photos) {
        const c = corrections[photo.image_path] || {};
        const row = [
          photo.image_path,
          photo.final_score,
          photo.aesthetic_score,
          photo.technical_score,
          photo.composition,
          photo.subject_strength,
          photo.visual_appeal,
          photo.sharpness,
          photo.exposure,
          photo.noise_level,
          photo.scene_type || '',
          photo.lighting || '',
          photo.subject_position || '',
          `"${(photo.description || '').replace(/"/g, '""')}"`,
          photo.location_name || '',
          photo.location_country || '',
          c.score || '',
          c.composition || '',
          c.subject || '',
          c.appeal || '',
          `"${(c.notes || '').replace(/"/g, '""')}"`,
        ];
        csv += row.join(',') + '\n';
      }

      const blob = new Blob([csv], { type: 'text/csv' });
      const a = document.createElement('a');
      a.href = URL.createObjectURL(blob);
      a.download = `photo_scores_corrected_${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
    },
    [corrections]
  );

  return {
    corrections,
    updateCorrection,
    getCorrection,
    exportCorrections,
    exportCSV,
    correctionsCount: Object.keys(corrections).length,
  };
}
