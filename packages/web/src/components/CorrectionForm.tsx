import type { Photo, Correction } from '../types/photo';

interface SliderRowProps {
  label: string;
  value: number;
  onChange: (value: number) => void;
}

function SliderRow({ label, value, onChange }: SliderRowProps) {
  return (
    <div className="flex gap-2.5 items-center mb-2.5">
      <label className="text-xs text-gray-400 w-24">{label}</label>
      <input
        type="range"
        min="0"
        max="100"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10))}
        className="flex-1 accent-ps-highlight"
      />
      <input
        type="number"
        min="0"
        max="100"
        value={value}
        onChange={(e) => onChange(parseInt(e.target.value, 10) || 0)}
        className="w-14 bg-ps-bg border border-ps-card text-gray-200 p-1.5 rounded text-center text-sm"
      />
    </div>
  );
}

interface CorrectionFormProps {
  photo: Photo;
  correction?: Correction;
  onUpdate: (
    field: keyof Correction,
    value: string | number,
    photo: Photo
  ) => void;
}

export function CorrectionForm({
  photo,
  correction,
  onUpdate,
}: CorrectionFormProps) {
  const scoreValue = correction?.score ?? Math.round(photo.final_score);
  const compositionValue =
    correction?.composition ?? Math.round((photo.composition || 0) * 100);
  const subjectValue =
    correction?.subject ?? Math.round((photo.subject_strength || 0) * 100);
  const appealValue =
    correction?.appeal ?? Math.round((photo.visual_appeal || 0) * 100);

  return (
    <div className="bg-ps-accent p-4 rounded-lg mt-4">
      <h4 className="text-xs text-gray-500 uppercase mb-2.5 font-semibold">
        Your Assessment
      </h4>

      <SliderRow
        label="Score (0-100)"
        value={scoreValue}
        onChange={(v) => onUpdate('score', v, photo)}
      />

      <SliderRow
        label="Composition"
        value={compositionValue}
        onChange={(v) => onUpdate('composition', v, photo)}
      />

      <SliderRow
        label="Subject"
        value={subjectValue}
        onChange={(v) => onUpdate('subject', v, photo)}
      />

      <SliderRow
        label="Appeal"
        value={appealValue}
        onChange={(v) => onUpdate('appeal', v, photo)}
      />

      <div className="flex gap-2.5 items-start">
        <label className="text-xs text-gray-400 w-24 pt-2">Notes</label>
        <textarea
          placeholder="Why did you adjust the score?"
          value={correction?.notes || ''}
          onChange={(e) => onUpdate('notes', e.target.value, photo)}
          className="flex-1 bg-ps-bg border border-ps-card text-gray-200 p-2 rounded resize-y min-h-[60px] text-sm"
        />
      </div>
    </div>
  );
}
