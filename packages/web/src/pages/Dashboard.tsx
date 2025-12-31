import { useState, useMemo, useCallback } from 'react';
import { Link } from 'react-router-dom';
import { FilterBar } from '../components/FilterBar';
import { PhotoGrid } from '../components/PhotoGrid';
import { Lightbox } from '../components/Lightbox';
import { ExportPanel } from '../components/ExportPanel';
import { usePhotos } from '../hooks/usePhotos';
import { useFilters } from '../hooks/useFilters';
import { useCorrections } from '../hooks/useCorrections';

export function Dashboard() {
  const { photos, loading, error } = usePhotos();
  const { sortBy, setSortBy, sortedPhotos, stats } = useFilters(photos);
  const {
    corrections,
    updateCorrection,
    exportCorrections,
    exportCSV,
    correctionsCount,
  } = useCorrections();

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Get current photo for lightbox
  const lightboxPhoto = lightboxIndex !== null ? sortedPhotos[lightboxIndex] : null;

  // Build list of image sources for matching clicked image to index
  const imageSources = useMemo(
    () => sortedPhotos.map((p) => `/photos/${encodeURIComponent(p.image_path)}`),
    [sortedPhotos]
  );

  const openLightbox = useCallback(
    (src: string) => {
      const index = imageSources.indexOf(src);
      if (index !== -1) {
        setLightboxIndex(index);
      }
    },
    [imageSources]
  );

  const closeLightbox = useCallback(() => setLightboxIndex(null), []);

  const goToPrev = useCallback(() => {
    setLightboxIndex((prev) => (prev !== null && prev > 0 ? prev - 1 : prev));
  }, []);

  const goToNext = useCallback(() => {
    setLightboxIndex((prev) =>
      prev !== null && prev < imageSources.length - 1 ? prev + 1 : prev
    );
  }, [imageSources.length]);

  if (loading) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-[var(--text-muted)]">Loading photos...</div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="flex justify-center items-center h-64">
        <div className="text-xl text-red-400">Error: {error}</div>
      </div>
    );
  }

  if (photos.length === 0) {
    return (
      <div className="flex flex-col justify-center items-center h-64 gap-4">
        <div className="text-xl text-[var(--text-muted)]">No photos yet</div>
        <Link
          to="/upload"
          className="px-6 py-3 bg-[#e94560] text-white rounded-lg hover:bg-[#c73e54] transition-colors"
        >
          Upload Your First Photos
        </Link>
      </div>
    );
  }

  return (
    <>
      <div className="flex justify-between items-center mb-4">
        <FilterBar sortBy={sortBy} onSortChange={setSortBy} stats={stats} />
        <Link
          to="/upload"
          className="px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73e54] transition-colors text-sm"
        >
          Upload More
        </Link>
      </div>

      <PhotoGrid
        photos={sortedPhotos}
        corrections={corrections}
        onImageClick={openLightbox}
        onCorrectionUpdate={(imagePath, field, value, photo) =>
          updateCorrection(imagePath, field, value, photo)
        }
      />

      <ExportPanel
        correctionsCount={correctionsCount}
        onExportJSON={exportCorrections}
        onExportCSV={exportCSV}
        photos={photos}
      />

      <Lightbox
        photo={lightboxPhoto}
        onClose={closeLightbox}
        onPrev={goToPrev}
        onNext={goToNext}
        hasPrev={lightboxIndex !== null && lightboxIndex > 0}
        hasNext={lightboxIndex !== null && lightboxIndex < sortedPhotos.length - 1}
      />
    </>
  );
}
