import { useState, useEffect, type ReactNode } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import type { Theme } from '../hooks/useTheme';
import { ThemeToggle } from './ThemeToggle';
import { useAuth } from '../contexts/AuthContext';

interface LayoutProps {
  children: ReactNode;
  photoCount?: number;
  avgScore?: number;
  theme?: Theme;
  onThemeToggle?: () => void;
}

export function Layout({
  children,
  photoCount,
  avgScore,
  theme = 'dark',
  onThemeToggle,
}: LayoutProps) {
  const { user, signOut } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();
  const [showUserMenu, setShowUserMenu] = useState(false);
  const [scrolled, setScrolled] = useState(false);

  const isHomePage = location.pathname === '/';

  // Track scroll position for floating header on home page
  useEffect(() => {
    if (!isHomePage) {
      setScrolled(false);
      return;
    }

    const handleScroll = () => {
      setScrolled(window.scrollY > 100);
    };

    window.addEventListener('scroll', handleScroll, { passive: true });
    return () => window.removeEventListener('scroll', handleScroll);
  }, [isHomePage]);

  const handleSignOut = async () => {
    await signOut();
    navigate('/');
  };

  const isActive = (path: string) => location.pathname === path;

  // For home page, show transparent header at top, solid when scrolled
  const headerClasses = isHomePage
    ? `fixed top-0 left-0 right-0 z-50 transition-all duration-300 ${
        scrolled
          ? 'bg-[var(--bg-secondary)]/95 backdrop-blur-sm border-b border-[var(--border-color)]'
          : 'bg-transparent'
      }`
    : 'bg-[var(--bg-secondary)] border-b border-[var(--border-color)] sticky top-0 z-50';

  // On home page when not scrolled, use white text for visibility over hero image
  const homeTransparentText = isHomePage && !scrolled;
  const textPrimaryClass = homeTransparentText ? 'text-white' : 'text-[var(--text-primary)]';
  const textMutedClass = homeTransparentText ? 'text-white/60' : 'text-[var(--text-muted)]';

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] text-[var(--text-primary)]">
      {/* Header */}
      <header className={headerClasses}>
        <div className="max-w-7xl mx-auto px-5 py-4">
          <div className="flex items-center justify-between">
            {/* Logo */}
            <Link to="/" className="flex items-center gap-3 hover:opacity-80 transition-opacity">
              <span className="text-2xl">📸</span>
              <div>
                <h1 className={`text-xl font-bold ${textPrimaryClass} transition-colors`}>Photo Scorer</h1>
                <p className={`text-xs ${textMutedClass} transition-colors`}>AI-powered photo analysis</p>
              </div>
            </Link>

            {/* Navigation & Actions */}
            <div className="flex items-center gap-6">
              {/* Downloads Link */}
              <Link
                to="/downloads"
                className={`px-3 py-2 rounded-lg transition-colors ${
                  isActive('/downloads')
                    ? homeTransparentText
                      ? 'bg-white/20 text-white'
                      : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                    : homeTransparentText
                      ? 'text-white/80 hover:text-white'
                      : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                }`}
              >
                Downloads
              </Link>

              {/* Stats (only show on dashboard) */}
              {photoCount !== undefined && avgScore !== undefined && (
                <>
                  <div className="text-center hidden sm:block">
                    <div className="text-lg font-bold text-[#4ade80]">{photoCount}</div>
                    <div className="text-xs text-[var(--text-muted)]">Photos</div>
                  </div>
                  <div className="text-center hidden sm:block">
                    <div className="text-lg font-bold text-[#e94560]">{avgScore.toFixed(1)}</div>
                    <div className="text-xs text-[var(--text-muted)]">Avg Score</div>
                  </div>
                </>
              )}

              {/* Navigation Links */}
              {user && (
                <nav className="hidden md:flex items-center gap-4">
                  <Link
                    to="/dashboard"
                    className={`px-3 py-2 rounded-lg transition-colors ${
                      isActive('/dashboard')
                        ? homeTransparentText
                          ? 'bg-white/20 text-white'
                          : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                        : homeTransparentText
                          ? 'text-white/80 hover:text-white'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    Dashboard
                  </Link>
                  <Link
                    to="/upload"
                    className={`px-3 py-2 rounded-lg transition-colors ${
                      isActive('/upload')
                        ? homeTransparentText
                          ? 'bg-white/20 text-white'
                          : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)]'
                        : homeTransparentText
                          ? 'text-white/80 hover:text-white'
                          : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    Upload
                  </Link>
                </nav>
              )}

              {/* Theme Toggle */}
              {onThemeToggle && <ThemeToggle theme={theme} onToggle={onThemeToggle} />}

              {/* User Menu */}
              {user ? (
                <div className="relative">
                  <button
                    onClick={() => setShowUserMenu(!showUserMenu)}
                    className={`flex items-center gap-2 px-3 py-2 rounded-lg hover:opacity-80 transition-all ${
                      homeTransparentText
                        ? 'bg-white/20 backdrop-blur-sm'
                        : 'bg-[var(--bg-tertiary)]'
                    }`}
                  >
                    <div className="w-8 h-8 rounded-full bg-[#e94560] flex items-center justify-center text-white font-medium">
                      {user.email?.[0].toUpperCase() || 'U'}
                    </div>
                    <svg
                      className={`w-4 h-4 transition-colors ${textMutedClass}`}
                      fill="none"
                      stroke="currentColor"
                      viewBox="0 0 24 24"
                    >
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                    </svg>
                  </button>

                  {showUserMenu && (
                    <>
                      <div
                        className="fixed inset-0 z-10"
                        onClick={() => setShowUserMenu(false)}
                      />
                      <div className="absolute right-0 mt-2 w-48 bg-[var(--bg-secondary)] border border-[var(--border-color)] rounded-lg shadow-lg z-20">
                        <div className="p-3 border-b border-[var(--border-color)]">
                          <p className="text-sm font-medium text-[var(--text-primary)] truncate">
                            {user.email}
                          </p>
                        </div>
                        <div className="py-1">
                          <Link
                            to="/dashboard"
                            onClick={() => setShowUserMenu(false)}
                            className="block px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] md:hidden"
                          >
                            Dashboard
                          </Link>
                          <Link
                            to="/upload"
                            onClick={() => setShowUserMenu(false)}
                            className="block px-4 py-2 text-sm text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)] md:hidden"
                          >
                            Upload
                          </Link>
                          <button
                            onClick={handleSignOut}
                            className="w-full text-left px-4 py-2 text-sm text-red-400 hover:bg-[var(--bg-tertiary)]"
                          >
                            Sign Out
                          </button>
                        </div>
                      </div>
                    </>
                  )}
                </div>
              ) : (
                <div className="flex items-center gap-3">
                  <Link
                    to="/login"
                    className={`px-4 py-2 transition-colors ${
                      homeTransparentText
                        ? 'text-white/80 hover:text-white'
                        : 'text-[var(--text-secondary)] hover:text-[var(--text-primary)]'
                    }`}
                  >
                    Sign In
                  </Link>
                  <Link
                    to="/signup"
                    className="px-4 py-2 bg-[#e94560] text-white rounded-lg hover:bg-[#c73e54] transition-colors"
                  >
                    Sign Up
                  </Link>
                </div>
              )}
            </div>
          </div>
        </div>
      </header>

      {/* Main Content */}
      {isHomePage ? (
        // Home page renders without wrapper padding for fullscreen sections
        <main>{children}</main>
      ) : (
        <main className="px-4 py-5 max-w-7xl mx-auto">{children}</main>
      )}
    </div>
  );
}
