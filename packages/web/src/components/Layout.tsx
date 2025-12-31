import type { ReactNode } from 'react';
import type { Theme } from '../hooks/useTheme';
import { ThemeToggle } from './ThemeToggle';

interface LayoutProps {
  children: ReactNode;
  photoCount?: number;
  avgScore?: number;
  theme?: Theme;
  onThemeToggle?: () => void;
}

export function Layout({
  children,
  photoCount = 0,
  avgScore = 0,
  theme = 'dark',
  onThemeToggle,
}: LayoutProps) {
  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Header */}
      <header className="bg-[var(--bg-secondary)] border-b border-[var(--border-color)] sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-5 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <span className="text-2xl">📸</span>
              <div>
                <h1 className="text-xl font-bold">Photo Score</h1>
                <p className="text-xs text-[var(--text-muted)]">AI-powered photo analysis</p>
              </div>
            </div>
            <div className="flex items-center gap-6">
              <div className="text-center">
                <div className="text-lg font-bold text-[#4ade80]">{photoCount}</div>
                <div className="text-xs text-[var(--text-muted)]">Photos</div>
              </div>
              <div className="text-center">
                <div className="text-lg font-bold text-[#e94560]">{avgScore.toFixed(1)}</div>
                <div className="text-xs text-[var(--text-muted)]">Avg Score</div>
              </div>
              {onThemeToggle && (
                <ThemeToggle theme={theme} onToggle={onThemeToggle} />
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="px-4 py-5">
        {children}
      </main>
    </div>
  );
}
