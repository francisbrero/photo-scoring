import { ReactNode } from 'react';

interface LayoutProps {
  children: ReactNode;
}

export function Layout({ children }: LayoutProps) {
  return (
    <div className="flex flex-col h-screen bg-gray-50 dark:bg-gray-900">
      {/* Titlebar (draggable on macOS) */}
      <header className="titlebar h-12 flex items-center px-4 bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700">
        <div className="w-20" /> {/* Space for traffic lights on macOS */}
        <h1 className="text-lg font-semibold text-gray-800 dark:text-gray-100">
          Photo Scoring
        </h1>
      </header>

      {/* Main content */}
      <main className="flex-1 overflow-hidden">
        {children}
      </main>
    </div>
  );
}
