import { useEffect, useCallback, useMemo } from 'react';
import type { Photo, PhotoFeatures } from '../types/photo';
import { getScoreLevel, getScoreLabel } from '../types/photo';

interface LightboxProps {
  photo: Photo | null;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

const scoreColorClasses: Record<string, string> = {
  excellent: 'text-[#4ade80]',
  strong: 'text-[#a3e635]',
  competent: 'text-[#facc15]',
  tourist: 'text-[#fb923c]',
  flawed: 'text-[#f87171]',
};

const scoreLabelClasses: Record<string, string> = {
  excellent: 'bg-green-900',
  strong: 'bg-lime-900',
  competent: 'bg-yellow-900',
  tourist: 'bg-orange-900',
  flawed: 'bg-red-900',
};

export function Lightbox({
  photo,
  onClose,
  onPrev,
  onNext,
  hasPrev = false,
  hasNext = false,
}: LightboxProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      } else if (e.key === 'ArrowLeft' && onPrev && hasPrev) {
        onPrev();
      } else if (e.key === 'ArrowRight' && onNext && hasNext) {
        onNext();
      }
    },
    [onClose, onPrev, onNext, hasPrev, hasNext]
  );

  useEffect(() => {
    if (photo) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [photo, handleKeyDown]);

  const features = useMemo<PhotoFeatures>(() => {
    if (!photo?.features_json) return {};
    try {
      return JSON.parse(photo.features_json);
    } catch {
      return {};
    }
  }, [photo?.features_json]);

  if (!photo) return null;

  const imageSrc = `/photos/${encodeURIComponent(photo.image_path)}`;
  const score = photo.final_score;
  const scoreLevel = getScoreLevel(score);

  return (
    <div
      className="fixed inset-0 bg-black/95 z-50 overflow-y-auto"
      onClick={onClose}
    >
      {/* Close button */}
      <button
        className="fixed top-4 right-6 text-4xl text-white cursor-pointer hover:text-gray-300 transition-colors z-10"
        onClick={onClose}
        aria-label="Close"
      >
        ×
      </button>

      {/* Previous button */}
      {hasPrev && onPrev && (
        <button
          className="fixed left-4 top-1/2 -translate-y-1/2 text-5xl text-white/70 hover:text-white transition-colors p-4 z-10"
          onClick={(e) => {
            e.stopPropagation();
            onPrev();
          }}
          aria-label="Previous photo"
        >
          ‹
        </button>
      )}

      {/* Next button */}
      {hasNext && onNext && (
        <button
          className="fixed right-4 top-1/2 -translate-y-1/2 text-5xl text-white/70 hover:text-white transition-colors p-4 z-10"
          onClick={(e) => {
            e.stopPropagation();
            onNext();
          }}
          aria-label="Next photo"
        >
          ›
        </button>
      )}

      {/* Content container */}
      <div
        className="min-h-full flex flex-col items-center py-8 px-16"
        onClick={(e) => e.stopPropagation()}
      >
        {/* Image */}
        <img
          src={imageSrc}
          alt={photo.image_path}
          className="max-w-full max-h-[70vh] object-contain rounded-lg"
        />

        {/* Photo info */}
        <div className="w-full max-w-3xl mt-6 text-white">
          {/* Filename and Score */}
          <div className="flex items-center justify-between mb-4">
            <div className="text-lg text-gray-400">{photo.image_path}</div>
            <div className="flex items-center gap-4">
              <span className={`text-4xl font-bold ${scoreColorClasses[scoreLevel]}`}>
                {score.toFixed(1)}
              </span>
              <span className={`text-sm px-3 py-1 rounded uppercase ${scoreLabelClasses[scoreLevel]}`}>
                {getScoreLabel(score)}
              </span>
            </div>
          </div>

          {/* Score breakdown */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-white/10 p-4 rounded-lg">
              <div className="text-xs text-gray-400 uppercase mb-1">Aesthetic</div>
              <div className="text-2xl font-bold">{((photo.aesthetic_score || 0) * 100).toFixed(0)}%</div>
              <div className="h-1.5 bg-white/20 rounded mt-2 overflow-hidden">
                <div
                  className="h-full rounded bg-gradient-to-r from-[#e94560] to-[#4ade80]"
                  style={{ width: `${(photo.aesthetic_score || 0) * 100}%` }}
                />
              </div>
            </div>
            <div className="bg-white/10 p-4 rounded-lg">
              <div className="text-xs text-gray-400 uppercase mb-1">Technical</div>
              <div className="text-2xl font-bold">{((photo.technical_score || 0) * 100).toFixed(0)}%</div>
              <div className="h-1.5 bg-white/20 rounded mt-2 overflow-hidden">
                <div
                  className="h-full rounded bg-gradient-to-r from-[#e94560] to-[#4ade80]"
                  style={{ width: `${(photo.technical_score || 0) * 100}%` }}
                />
              </div>
            </div>
          </div>

          {/* Description */}
          {photo.description && (
            <div className="mb-6">
              <div className="text-xs text-gray-400 uppercase mb-2">Description</div>
              <p className="text-gray-200 leading-relaxed">{photo.description}</p>
            </div>
          )}

          {/* Tags */}
          <div className="flex flex-wrap gap-2 mb-6">
            {photo.scene_type && (
              <span className="bg-white/10 px-3 py-1.5 rounded-full text-sm text-gray-300">
                {photo.scene_type}
              </span>
            )}
            {photo.lighting && (
              <span className="bg-white/10 px-3 py-1.5 rounded-full text-sm text-gray-300">
                {photo.lighting}
              </span>
            )}
            {photo.subject_position && (
              <span className="bg-white/10 px-3 py-1.5 rounded-full text-sm text-gray-300">
                {photo.subject_position}
              </span>
            )}
            {features.color_palette && (
              <span className="bg-white/10 px-3 py-1.5 rounded-full text-sm text-gray-300">
                {features.color_palette}
              </span>
            )}
          </div>

          {/* Location */}
          {photo.location_name && (
            <div className="mb-6 text-[#e94560]">
              📍 {photo.location_name}
              {photo.location_country && `, ${photo.location_country}`}
            </div>
          )}

          {/* Critique */}
          {photo.explanation && (
            <div className="mb-6">
              <div className="text-xs text-gray-400 uppercase mb-2">📝 Critique</div>
              <div className="bg-white/5 p-4 rounded-lg text-gray-300 leading-relaxed whitespace-pre-wrap">
                {photo.explanation}
              </div>
            </div>
          )}

          {/* Improvements */}
          {photo.improvements && (
            <div className="mb-6">
              <div className="text-xs text-gray-400 uppercase mb-2">💡 How to Improve</div>
              <div className="space-y-2">
                {photo.improvements.split(' | ').map((imp, i) => (
                  <div key={i} className="bg-white/5 p-3 rounded-lg text-gray-300">
                    {imp}
                  </div>
                ))}
              </div>
            </div>
          )}

          {/* Model scores */}
          <div className="text-xs text-gray-500 mb-8">
            {photo.qwen_aesthetic && <span className="mr-4">Qwen: {photo.qwen_aesthetic}</span>}
            {photo.gpt4o_aesthetic && <span className="mr-4">GPT: {photo.gpt4o_aesthetic}</span>}
            {photo.gemini_aesthetic && <span>Gemini: {photo.gemini_aesthetic}</span>}
          </div>
        </div>

        {/* Keyboard hint */}
        <div className="text-xs text-white/40 mt-4">
          Use ← → arrow keys to navigate • ESC to close • Scroll for details
        </div>
      </div>
    </div>
  );
}
