import { useEffect, useCallback } from 'react';

interface LightboxProps {
  src: string | null;
  onClose: () => void;
}

export function Lightbox({ src, onClose }: LightboxProps) {
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
      }
    },
    [onClose]
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
      <span
        className="absolute top-5 right-8 text-4xl text-white cursor-pointer hover:text-gray-300 transition-colors"
        onClick={onClose}
      >
        ×
      </span>
      <img
        src={src}
        alt="Full size"
        className="max-w-[95%] max-h-[95%] object-contain"
        onClick={(e) => e.stopPropagation()}
      />
    </div>
  );
}
