import { useState } from 'react';
import { Layout } from './components/Layout';
import { FilterBar } from './components/FilterBar';
import { PhotoGrid } from './components/PhotoGrid';
import { Lightbox } from './components/Lightbox';
import { ExportPanel } from './components/ExportPanel';
import { usePhotos } from './hooks/usePhotos';
import { useFilters } from './hooks/useFilters';
import { useCorrections } from './hooks/useCorrections';

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

  const [lightboxSrc, setLightboxSrc] = useState<string | null>(null);

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
    <Layout>
      <FilterBar sortBy={sortBy} onSortChange={setSortBy} stats={stats} />

      <PhotoGrid
        photos={sortedPhotos}
        corrections={corrections}
        onImageClick={setLightboxSrc}
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

      <Lightbox src={lightboxSrc} onClose={() => setLightboxSrc(null)} />
    </Layout>
  );
}

export default App;
