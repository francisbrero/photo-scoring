import { useState } from 'react';
import type { PhotoWithScore } from '../../types/photo';
import { PhotoCard } from './PhotoCard';

interface PhotoGridProps {
  photos: PhotoWithScore[];
  onScorePhoto: (imageId: string) => void;
  onSelectPhoto: (photo: PhotoWithScore) => void;
}

type SortBy = 'filename' | 'score' | 'score_desc';

export function PhotoGrid({ photos, onScorePhoto, onSelectPhoto }: PhotoGridProps) {
  const [sortBy, setSortBy] = useState<SortBy>('filename');
  const [filterScored, setFilterScored] = useState<'all' | 'scored' | 'unscored'>('all');

  const sortedPhotos = [...photos]
    .filter((photo) => {
      if (filterScored === 'scored') return photo.score !== undefined;
      if (filterScored === 'unscored') return photo.score === undefined;
      return true;
    })
    .sort((a, b) => {
      switch (sortBy) {
        case 'score':
          return (a.score?.final_score ?? -1) - (b.score?.final_score ?? -1);
        case 'score_desc':
          return (b.score?.final_score ?? -1) - (a.score?.final_score ?? -1);
        default:
          return a.filename.localeCompare(b.filename);
      }
    });

  return (
    <div className="h-full flex flex-col">
      {/* Toolbar */}
      <div className="flex items-center gap-4 p-4 border-b border-gray-200 dark:border-gray-700 bg-white dark:bg-gray-800">
        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-300">Sort:</label>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value as SortBy)}
            className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-2 py-1 text-sm"
          >
            <option value="filename">Filename</option>
            <option value="score_desc">Score (High to Low)</option>
            <option value="score">Score (Low to High)</option>
          </select>
        </div>

        <div className="flex items-center gap-2">
          <label className="text-sm text-gray-600 dark:text-gray-300">Filter:</label>
          <select
            value={filterScored}
            onChange={(e) => setFilterScored(e.target.value as typeof filterScored)}
            className="rounded border border-gray-300 dark:border-gray-600 bg-white dark:bg-gray-700 text-gray-800 dark:text-gray-200 px-2 py-1 text-sm"
          >
            <option value="all">All Photos</option>
            <option value="scored">Scored Only</option>
            <option value="unscored">Unscored Only</option>
          </select>
        </div>

        <div className="ml-auto text-sm text-gray-600 dark:text-gray-300">
          {sortedPhotos.length} of {photos.length} photos
        </div>
      </div>

      {/* Grid */}
      <div className="flex-1 overflow-auto p-4">
        {sortedPhotos.length === 0 ? (
          <div className="flex items-center justify-center h-full text-gray-500 dark:text-gray-400">
            No photos to display
          </div>
        ) : (
          <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
            {sortedPhotos.map((photo) => (
              <PhotoCard
                key={photo.image_id}
                photo={photo}
                onScore={() => onScorePhoto(photo.image_id)}
                onSelect={() => onSelectPhoto(photo)}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
