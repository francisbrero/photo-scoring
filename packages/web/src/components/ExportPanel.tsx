import type { Photo } from '../types/photo';

interface ExportPanelProps {
  correctionsCount: number;
  onExportJSON: () => void;
  onExportCSV: (photos: Photo[]) => void;
  photos: Photo[];
}

export function ExportPanel({
  correctionsCount,
  onExportJSON,
  onExportCSV,
  photos,
}: ExportPanelProps) {
  return (
    <div className="text-center my-8 p-5 bg-ps-card rounded-xl max-w-3xl mx-auto">
      <div className="text-score-excellent text-lg mb-2.5">
        {correctionsCount} correction{correctionsCount !== 1 ? 's' : ''} made
      </div>
      <button
        onClick={onExportJSON}
        className="w-full bg-ps-highlight border-none text-white py-2.5 px-5 rounded-md cursor-pointer text-sm hover:bg-[#c73e54] transition-colors"
      >
        Export Corrections as JSON
      </button>
      <button
        onClick={() => onExportCSV(photos)}
        className="w-full bg-ps-accent border-none text-white py-2.5 px-5 rounded-md cursor-pointer text-sm mt-2.5 hover:bg-ps-card transition-colors"
      >
        Export Updated CSV
      </button>
    </div>
  );
}
