import type { SortOption } from '../types/photo';

interface FilterBarProps {
  sortBy: SortOption;
  onSortChange: (sort: SortOption) => void;
  stats: {
    count: number;
    avg: number;
    min: number;
    max: number;
  };
}

export function FilterBar({ sortBy, onSortChange, stats }: FilterBarProps) {
  return (
    <div className="mb-6">
      <div className="flex justify-center mb-4">
        <select
          value={sortBy}
          onChange={(e) => onSortChange(e.target.value as SortOption)}
          className="bg-ps-card border border-ps-accent text-gray-200 px-5 py-2.5 rounded-lg cursor-pointer hover:bg-ps-accent transition-colors"
        >
          <option value="score_desc">Score (High to Low)</option>
          <option value="score_asc">Score (Low to High)</option>
          <option value="name">Filename</option>
          <option value="aesthetic">Aesthetic Score</option>
          <option value="technical">Technical Score</option>
        </select>
      </div>
      <div className="text-center text-gray-500">
        {stats.count} photos | Avg: {stats.avg.toFixed(1)} | Range:{' '}
        {stats.min.toFixed(1)} - {stats.max.toFixed(1)}
      </div>
    </div>
  );
}
