import { useMemo } from 'react';
import type { Photo, Correction, PhotoFeatures } from '../types/photo';
import { getScoreLevel, getScoreLabel } from '../types/photo';
import { ScoreBreakdown } from './ScoreBreakdown';
import { CorrectionForm } from './CorrectionForm';
import { Expandable } from './Expandable';

interface PhotoCardProps {
  photo: Photo;
  correction?: Correction;
  onImageClick: (src: string) => void;
  onCorrectionUpdate: (
    field: keyof Correction,
    value: string | number,
    photo: Photo
  ) => void;
}

function formatExplanation(text: string): string {
  if (!text) return '';
  return text
    .replace(/\*\*([^*]+)\*\*/g, '<strong style="color: #e94560">$1</strong>')
    .split('\n\n')
    .map((p) => p.trim())
    .filter((p) => p)
    .map((p) => `<p class="mb-3">${p}</p>`)
    .join('');
}

function formatImprovement(text: string): string {
  if (!text) return '';
  return text.replace(
    /\*\*([^*]+)\*\*/g,
    '<strong style="color: #4ade80">$1</strong>'
  );
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

export function PhotoCard({
  photo,
  correction,
  onImageClick,
  onCorrectionUpdate,
}: PhotoCardProps) {
  const score = photo.final_score ?? 0;
  const scoreLevel = getScoreLevel(score);

  const features = useMemo<PhotoFeatures>(() => {
    if (!photo.features_json) return {};
    try {
      return JSON.parse(photo.features_json);
    } catch {
      return {};
    }
  }, [photo.features_json]);

  const imageSrc = `/photos/${encodeURIComponent(photo.image_path)}`;

  return (
    <div className="bg-[var(--bg-secondary)] rounded-xl overflow-hidden shadow-lg hover:-translate-y-1 transition-transform duration-200">
      {/* Image */}
      <img
        src={imageSrc}
        alt={photo.image_path}
        onClick={() => onImageClick(imageSrc)}
        loading="lazy"
        className="w-full h-[300px] object-cover cursor-pointer bg-[var(--bg-tertiary)]"
      />

      <div className="p-4">
        {/* Filename */}
        <div className="font-bold text-sm text-[var(--text-secondary)] mb-2 break-all">
          {photo.image_path}
        </div>

        {/* Score Row */}
        <div className="flex items-center justify-between mb-3">
          <div className={`text-4xl font-bold ${scoreColorClasses[scoreLevel]}`}>
            {score.toFixed(1)}
          </div>
          <span
            className={`text-xs px-2 py-1 rounded uppercase ${scoreLabelClasses[scoreLevel]}`}
          >
            {getScoreLabel(score)}
          </span>
        </div>

        {/* Metrics */}
        <ScoreBreakdown
          aesthetic={photo.aesthetic_score || 0}
          technical={photo.technical_score || 0}
        />

        {/* Description */}
        {photo.description && (
          <div className="text-sm text-[var(--text-secondary)] mb-3 leading-relaxed">
            {photo.description}
          </div>
        )}

        {/* Tags */}
        <div className="flex flex-wrap gap-2 mb-4">
          {photo.scene_type && (
            <span className="bg-[var(--bg-tertiary)] px-2.5 py-1 rounded-full text-xs text-[var(--text-secondary)]">
              {photo.scene_type}
            </span>
          )}
          {photo.lighting && (
            <span className="bg-[var(--bg-tertiary)] px-2.5 py-1 rounded-full text-xs text-[var(--text-secondary)]">
              {photo.lighting}
            </span>
          )}
          {photo.subject_position && (
            <span className="bg-[var(--bg-tertiary)] px-2.5 py-1 rounded-full text-xs text-[var(--text-secondary)]">
              {photo.subject_position}
            </span>
          )}
          {features.color_palette && (
            <span className="bg-[var(--bg-tertiary)] px-2.5 py-1 rounded-full text-xs text-[var(--text-secondary)]">
              {features.color_palette}
            </span>
          )}
        </div>

        {/* Location */}
        {photo.location_name && (
          <div className="text-sm text-[#e94560] mb-3">
            📍 {photo.location_name}
            {photo.location_country && `, ${photo.location_country}`}
          </div>
        )}

        {/* Credit Badge */}
        <div className="mb-3">
          <span className="inline-block bg-[var(--bg-tertiary)] px-2.5 py-1 rounded-full text-[11px] text-[#4ade80]">
            1 credit
          </span>
        </div>

        {/* Explanation */}
        {photo.explanation && (
          <Expandable title="Critique" icon="📝">
            <div
              className="px-3 pb-3 text-sm leading-relaxed text-gray-300"
              dangerouslySetInnerHTML={{
                __html: formatExplanation(photo.explanation),
              }}
            />
          </Expandable>
        )}

        {/* Improvements */}
        {photo.improvements && (
          <Expandable title="How to Improve" icon="💡">
            <div className="px-3 pb-3">
              {photo.improvements.split(' | ').map((imp, i) => (
                <div
                  key={i}
                  className="text-sm text-gray-400 p-2.5 bg-[#0f3460] rounded-md mb-2 last:mb-0 leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: formatImprovement(imp) }}
                />
              ))}
            </div>
          </Expandable>
        )}

        {/* Model Scores */}
        <div className="text-[11px] text-[var(--text-muted)] mt-2 mb-3">
          {photo.qwen_aesthetic && <span className="mr-3">Qwen: {photo.qwen_aesthetic}</span>}
          {photo.gpt4o_aesthetic && <span className="mr-3">GPT: {photo.gpt4o_aesthetic}</span>}
          {photo.gemini_aesthetic && <span>Gemini: {photo.gemini_aesthetic}</span>}
        </div>

        {/* Correction Form */}
        <CorrectionForm
          photo={photo}
          correction={correction}
          onUpdate={onCorrectionUpdate}
        />
      </div>
    </div>
  );
}
