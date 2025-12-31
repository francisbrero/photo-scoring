import { useState, useMemo, useCallback } from 'react';
import { Layout } from './components/Layout';
import { FilterBar } from './components/FilterBar';
import { PhotoGrid } from './components/PhotoGrid';
import { Lightbox } from './components/Lightbox';
import { ExportPanel } from './components/ExportPanel';
import { usePhotos } from './hooks/usePhotos';
import { useFilters } from './hooks/useFilters';
import { useCorrections } from './hooks/useCorrections';
import { useTheme } from './hooks/useTheme';

function App() {
  const { photos, loading, error } = usePhotos();
  const { sortBy, setSortBy, sortedPhotos, stats } = useFilters(photos);
  const {
    corrections,
    updateCorrection,
    exportCorrections,
    exportCSV,
    correctionsCount,
  } = useCorrections();
  const { theme, toggleTheme } = useTheme();

  const [lightboxIndex, setLightboxIndex] = useState<number | null>(null);

  // Build list of image sources for lightbox navigation
  const imageSources = useMemo(
    () => sortedPhotos.map((p) => `/photos/${encodeURIComponent(p.image_path)}`),
    [sortedPhotos]
  );

  const lightboxSrc = lightboxIndex !== null ? imageSources[lightboxIndex] : null;

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
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-400">Loading photos...</div>
        </div>
      </Layout>
    );
  }

  if (error) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-red-400">Error: {error}</div>
        </div>
      </Layout>
    );
  }

  if (photos.length === 0) {
    return (
      <Layout>
        <div className="flex justify-center items-center h-64">
          <div className="text-xl text-gray-400">No photos found</div>
        </div>
      </Layout>
    );
  }

  return (
    <Layout photoCount={photos.length} avgScore={stats.avg} theme={theme} onThemeToggle={toggleTheme}>
      <FilterBar sortBy={sortBy} onSortChange={setSortBy} stats={stats} />

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
        src={lightboxSrc}
        onClose={closeLightbox}
        onPrev={goToPrev}
        onNext={goToNext}
        hasPrev={lightboxIndex !== null && lightboxIndex > 0}
        hasNext={lightboxIndex !== null && lightboxIndex < imageSources.length - 1}
      />
    </Layout>
  );
}

export default App;
