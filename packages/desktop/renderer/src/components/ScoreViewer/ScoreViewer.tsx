import type { PhotoWithScore } from '../../types/photo';

interface ScoreViewerProps {
  photo: PhotoWithScore;
  onClose: () => void;
  onScore: () => void;
}

export function ScoreViewer({ photo, onClose, onScore }: ScoreViewerProps) {
  const score = photo.score;

  const getScoreColor = (value: number) => {
    if (value >= 0.8) return 'text-green-500';
    if (value >= 0.6) return 'text-yellow-500';
    if (value >= 0.4) return 'text-orange-500';
    return 'text-red-500';
  };

  const AttributeBar = ({ label, value }: { label: string; value: number }) => (
    <div className="flex items-center gap-3">
      <span className="text-sm text-gray-600 dark:text-gray-400 w-32">{label}</span>
      <div className="flex-1 h-2 bg-gray-200 dark:bg-gray-700 rounded-full overflow-hidden">
        <div
          className="h-full bg-blue-500 rounded-full transition-all"
          style={{ width: `${value * 100}%` }}
        />
      </div>
      <span className={`text-sm font-medium w-12 text-right ${getScoreColor(value)}`}>
        {Math.round(value * 100)}
      </span>
    </div>
  );

  return (
    <div className="fixed inset-0 z-50 flex">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/80"
        onClick={onClose}
      />

      {/* Content */}
      <div className="relative flex w-full max-w-6xl mx-auto my-8">
        {/* Image */}
        <div className="flex-1 flex items-center justify-center p-4">
          {photo.thumbnail ? (
            <img
              src={photo.thumbnail}
              alt={photo.filename}
              className="max-w-full max-h-full object-contain rounded-lg"
            />
          ) : (
            <div className="text-gray-400">Loading image...</div>
          )}
        </div>

        {/* Sidebar */}
        <div className="w-96 bg-white dark:bg-gray-800 rounded-lg m-4 p-6 overflow-auto">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-800 dark:text-gray-100">
              Score Details
            </h2>
            <button
              onClick={onClose}
              className="text-gray-500 hover:text-gray-700 dark:text-gray-400 dark:hover:text-gray-200"
            >
              <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>

          <p className="text-sm text-gray-600 dark:text-gray-400 mb-4 truncate">
            {photo.filename}
          </p>

          {score ? (
            <>
              {/* Final Score */}
              <div className="text-center py-6 mb-6 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <div className="text-5xl font-bold text-gray-800 dark:text-gray-100">
                  {Math.round(score.final_score)}
                </div>
                <div className="text-sm text-gray-500 dark:text-gray-400 mt-1">
                  Final Score
                </div>
              </div>

              {/* Category Scores */}
              <div className="grid grid-cols-2 gap-4 mb-6">
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
                    {Math.round(score.aesthetic_score * 100)}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Aesthetic</div>
                </div>
                <div className="text-center p-4 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                  <div className="text-2xl font-semibold text-gray-800 dark:text-gray-100">
                    {Math.round(score.technical_score * 100)}
                  </div>
                  <div className="text-xs text-gray-500 dark:text-gray-400">Technical</div>
                </div>
              </div>

              {/* Aesthetic Attributes */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Aesthetic
                </h3>
                <div className="space-y-3">
                  <AttributeBar label="Composition" value={score.attributes.composition} />
                  <AttributeBar label="Subject" value={score.attributes.subject_strength} />
                  <AttributeBar label="Visual Appeal" value={score.attributes.visual_appeal} />
                </div>
              </div>

              {/* Technical Attributes */}
              <div className="mb-6">
                <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-3">
                  Technical
                </h3>
                <div className="space-y-3">
                  <AttributeBar label="Sharpness" value={score.attributes.sharpness} />
                  <AttributeBar label="Exposure" value={score.attributes.exposure_balance} />
                  <AttributeBar label="Noise Level" value={score.attributes.noise_level} />
                </div>
              </div>

              {/* Explanation */}
              {score.explanation && (
                <div>
                  <h3 className="text-sm font-semibold text-gray-700 dark:text-gray-300 mb-2">
                    Analysis
                  </h3>
                  <p className="text-sm text-gray-600 dark:text-gray-400 leading-relaxed">
                    {score.explanation}
                  </p>
                </div>
              )}
            </>
          ) : (
            <div className="text-center py-8">
              <p className="text-gray-500 dark:text-gray-400 mb-4">
                This photo hasn't been scored yet.
              </p>
              <button
                onClick={onScore}
                disabled={photo.isScoring}
                className="bg-blue-500 hover:bg-blue-600 disabled:bg-blue-300 text-white px-6 py-2 rounded-lg font-medium"
              >
                {photo.isScoring ? 'Scoring...' : 'Score Photo'}
              </button>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
