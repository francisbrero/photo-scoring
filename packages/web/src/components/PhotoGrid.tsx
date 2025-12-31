import type { Photo, Correction } from '../types/photo';
import { PhotoCard } from './PhotoCard';

interface PhotoGridProps {
  photos: Photo[];
  corrections: Record<string, Correction>;
  onImageClick: (photo: Photo) => void;
  onCorrectionUpdate: (
    imagePath: string,
    field: keyof Correction,
    value: string | number,
    photo: Photo
  ) => void;
}

export function PhotoGrid({
  photos,
  corrections,
  onImageClick,
  onCorrectionUpdate,
}: PhotoGridProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 2xl:grid-cols-4 gap-5 max-w-[1800px] mx-auto">
      {photos.map((photo) => (
        <PhotoCard
          key={photo.id || photo.image_path}
          photo={photo}
          correction={corrections[photo.image_path]}
          onImageClick={onImageClick}
          onCorrectionUpdate={(field, value, p) =>
            onCorrectionUpdate(photo.image_path, field, value, p)
          }
        />
      ))}
    </div>
  );
}
