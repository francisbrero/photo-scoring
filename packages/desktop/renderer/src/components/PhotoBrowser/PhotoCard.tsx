import type { PhotoWithScore } from '../../types/photo';

interface PhotoCardProps {
  photo: PhotoWithScore;
  onScore: () => void;
  onSelect: () => void;
}

export function PhotoCard({ photo, onScore, onSelect }: PhotoCardProps) {
  const score = photo.score?.final_score;
  const hasScore = score !== undefined;

  const getScoreColor = (score: number) => {
    if (score >= 80) return 'bg-green-500';
    if (score >= 60) return 'bg-yellow-500';
    if (score >= 40) return 'bg-orange-500';
    return 'bg-red-500';
  };

  return (
    <div
      className="relative group cursor-pointer rounded-lg overflow-hidden bg-gray-200 dark:bg-gray-700 aspect-square"
      onClick={onSelect}
    >
      {/* Thumbnail */}
      {photo.thumbnail ? (
        <img
          src={photo.thumbnail}
          alt={photo.filename}
          className="w-full h-full object-cover"
        />
      ) : (
        <div className="w-full h-full flex items-center justify-center text-gray-400">
          Loading...
        </div>
      )}

      {/* Score badge */}
      {hasScore && (
        <div
          className={`absolute top-2 right-2 ${getScoreColor(score)} text-white text-sm font-bold px-2 py-1 rounded`}
        >
          {Math.round(score)}
        </div>
      )}

      {/* Scoring indicator */}
      {photo.isScoring && (
        <div className="absolute inset-0 bg-black/50 flex items-center justify-center">
          <div className="w-8 h-8 border-2 border-white border-t-transparent rounded-full animate-spin" />
        </div>
      )}

      {/* Hover overlay */}
      <div className="absolute inset-0 bg-black/0 group-hover:bg-black/30 transition-colors flex items-center justify-center opacity-0 group-hover:opacity-100">
        {!hasScore && !photo.isScoring && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onScore();
            }}
            className="bg-blue-500 hover:bg-blue-600 text-white px-4 py-2 rounded-lg font-medium"
          >
            Score
          </button>
        )}
      </div>

      {/* Filename */}
      <div className="absolute bottom-0 left-0 right-0 bg-gradient-to-t from-black/60 to-transparent p-2">
        <p className="text-white text-xs truncate">{photo.filename}</p>
      </div>
    </div>
  );
}
