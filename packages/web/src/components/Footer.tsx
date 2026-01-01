import { Link } from 'react-router-dom';

export function Footer() {
  return (
    <footer className="py-12 px-4 bg-[var(--bg-primary)] border-t border-[var(--border-color)]">
      <div className="max-w-5xl mx-auto">
        <div className="flex flex-col md:flex-row justify-between items-center gap-6">
          {/* Logo */}
          <Link to="/" className="text-2xl font-bold text-[var(--text-primary)]">
            Photo<span className="text-[#e94560]">Scorer</span>
          </Link>

          {/* Links */}
          <nav className="flex flex-wrap justify-center gap-6 text-[var(--text-secondary)]">
            <Link to="/about" className="hover:text-[var(--text-primary)] transition-colors">About</Link>
            <Link to="/pricing" className="hover:text-[var(--text-primary)] transition-colors">Pricing</Link>
            <a href="https://spraiandprai.com" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text-primary)] transition-colors">Blog</a>
            <Link to="/contact" className="hover:text-[var(--text-primary)] transition-colors">Contact</Link>
          </nav>

          {/* Copyright */}
          <p className="text-sm text-[var(--text-muted)]">
            © 2025 PhotoScorer. Made for photographers who care.
          </p>
        </div>
      </div>
    </footer>
  );
}
