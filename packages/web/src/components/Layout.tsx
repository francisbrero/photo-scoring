import type { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="min-h-screen bg-ps-bg text-gray-200 p-5">
      <h1 className="text-center text-3xl font-bold text-white mb-2.5">
        Photo Score Viewer
      </h1>
      {children}
    </div>
  );
}
