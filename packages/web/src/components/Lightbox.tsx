import { useEffect, useCallback } from 'react';

interface LightboxProps {
  src: string | null;
  onClose: () => void;
  onPrev?: () => void;
  onNext?: () => void;
  hasPrev?: boolean;
  hasNext?: boolean;
}

export function Lightbox({
  src,
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
    if (src) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    }

    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [src, handleKeyDown]);

  if (!src) return null;

  return (
    <div
      className="fixed inset-0 bg-black/95 z-50 flex justify-center items-center"
      onClick={onClose}
    >
      {/* Close button */}
      <button
        className="absolute top-5 right-8 text-4xl text-white cursor-pointer hover:text-gray-300 transition-colors"
        onClick={onClose}
        aria-label="Close"
      >
        ×
      </button>

      {/* Previous button */}
      {hasPrev && onPrev && (
        <button
          className="absolute left-4 top-1/2 -translate-y-1/2 text-5xl text-white/70 hover:text-white transition-colors p-4"
          onClick={(e) => {
            e.stopPropagation();
            onPrev();
          }}
          aria-label="Previous photo"
        >
          ‹
        </button>
      )}

      {/* Image */}
      <img
        src={src}
        alt="Full size"
        className="max-w-[90%] max-h-[90%] object-contain"
        onClick={(e) => e.stopPropagation()}
      />

      {/* Next button */}
      {hasNext && onNext && (
        <button
          className="absolute right-4 top-1/2 -translate-y-1/2 text-5xl text-white/70 hover:text-white transition-colors p-4"
          onClick={(e) => {
            e.stopPropagation();
            onNext();
          }}
          aria-label="Next photo"
        >
          ›
        </button>
      )}

      {/* Keyboard hint */}
      <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-white/50">
        Use ← → arrow keys to navigate • ESC to close
      </div>
    </div>
  );
}
