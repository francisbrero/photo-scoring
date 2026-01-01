import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { useEffect, useRef, useState } from 'react';

// Curated Unsplash images for the carousel (beautiful world/landscapes)
const CAROUSEL_IMAGES = [
  {
    url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=1920&q=80',
    alt: 'Mountain landscape at golden hour',
  },
  {
    url: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=1920&q=80',
    alt: 'Misty mountains with sun rays',
  },
  {
    url: 'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=1920&q=80',
    alt: 'Forest path with sunlight',
  },
  {
    url: 'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=1920&q=80',
    alt: 'Waterfall in lush green landscape',
  },
  {
    url: 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=1920&q=80',
    alt: 'Lake with mountain reflection',
  },
];

// Hook for scroll-triggered animations
function useScrollAnimation() {
  const ref = useRef<HTMLDivElement>(null);
  const [isVisible, setIsVisible] = useState(false);

  useEffect(() => {
    const observer = new IntersectionObserver(
      ([entry]) => {
        if (entry.isIntersecting) {
          setIsVisible(true);
        }
      },
      { threshold: 0.1, rootMargin: '0px 0px -50px 0px' }
    );

    if (ref.current) {
      observer.observe(ref.current);
    }

    return () => observer.disconnect();
  }, []);

  return { ref, isVisible };
}

// Animated section wrapper
function AnimatedSection({
  children,
  className = ''
}: {
  children: React.ReactNode;
  className?: string;
}) {
  const { ref, isVisible } = useScrollAnimation();

  return (
    <div
      ref={ref}
      className={`transition-all duration-700 ${
        isVisible
          ? 'opacity-100 translate-y-0'
          : 'opacity-0 translate-y-8'
      } ${className}`}
    >
      {children}
    </div>
  );
}

export function Home() {
  const { user } = useAuth();
  const [currentImageIndex, setCurrentImageIndex] = useState(0);

  // Carousel auto-advance
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % CAROUSEL_IMAGES.length);
    }, 6000); // 6 seconds per image

    return () => clearInterval(interval);
  }, []);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)]">
      {/* ============================================ */}
      {/* HERO SECTION - Fullscreen Carousel */}
      {/* ============================================ */}
      <section className="relative h-screen w-full overflow-hidden">
        {/* Carousel Images */}
        {CAROUSEL_IMAGES.map((image, index) => (
          <div
            key={image.url}
            className={`absolute inset-0 transition-opacity duration-[2000ms] ${
              index === currentImageIndex ? 'opacity-100' : 'opacity-0'
            }`}
          >
            <div
              className="absolute inset-0 bg-cover bg-center animate-ken-burns"
              style={{ backgroundImage: `url(${image.url})` }}
            />
          </div>
        ))}

        {/* Dark overlay for text readability */}
        <div className="absolute inset-0 bg-gradient-to-b from-black/60 via-black/40 to-black/70" />

        {/* Hero Content */}
        <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
          <h1 className="text-4xl sm:text-5xl md:text-6xl lg:text-7xl font-bold text-white mb-6 max-w-5xl leading-tight">
            Every trip. Thousands of photos.
            <br />
            <span className="text-[#e94560]">Which ones are actually good?</span>
          </h1>
          <p className="text-lg sm:text-xl text-white/80 max-w-2xl mb-8">
            AI-powered photo scoring that finds your keepers, explains what works,
            and helps you grow as a photographer.
          </p>
          <div className="flex flex-col sm:flex-row gap-4">
            {user ? (
              <Link
                to="/upload"
                className="px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
              >
                Upload Photos
              </Link>
            ) : (
              <Link
                to="/signup"
                className="px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
              >
                GET STARTED FREE
              </Link>
            )}
          </div>
        </div>

        {/* Scroll Indicator */}
        <div className="absolute bottom-8 left-1/2 -translate-x-1/2 animate-bounce">
          <div className="w-8 h-12 border-2 border-white/50 rounded-full flex items-start justify-center p-2">
            <div className="w-1.5 h-3 bg-white/70 rounded-full animate-scroll-down" />
          </div>
        </div>
      </section>

      {/* ============================================ */}
      {/* PROBLEM SECTION */}
      {/* ============================================ */}
      <section className="py-20 px-4 bg-[var(--bg-secondary)]">
        <AnimatedSection className="max-w-4xl mx-auto text-center">
          {/* Grid of photo thumbnails with question marks */}
          <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 mb-8 opacity-60">
            {Array.from({ length: 24 }).map((_, i) => (
              <div
                key={i}
                className="aspect-square bg-[var(--bg-tertiary)] rounded-lg flex items-center justify-center"
              >
                <span className="text-2xl text-[var(--text-muted)]">?</span>
              </div>
            ))}
          </div>
          <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)] mb-4">
            You know great photos when you see them.
          </h2>
          <p className="text-xl text-[var(--text-secondary)]">
            But scrolling through thousands? <span className="text-[#e94560] font-semibold">Exhausting.</span>
          </p>
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* VALUE #1: Find the Keepers */}
      {/* ============================================ */}
      <section className="py-20 px-4">
        <AnimatedSection className="max-w-5xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-6">
            <span className="text-4xl">🎯</span>
            <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)]">
              Find the Keepers
            </h2>
          </div>

          {/* Photo thumbnails with scores */}
          <div className="flex justify-center gap-2 sm:gap-4 mb-8 flex-wrap">
            {[
              { score: 72, highlight: false },
              { score: 89, highlight: false },
              { score: 94, highlight: true },
              { score: 61, highlight: false },
              { score: 78, highlight: false },
            ].map((item, i) => (
              <div
                key={i}
                className={`relative w-20 h-20 sm:w-28 sm:h-28 rounded-lg overflow-hidden transition-transform ${
                  item.highlight ? 'ring-4 ring-[#4ade80] scale-110' : 'opacity-70'
                }`}
              >
                <div className="absolute inset-0 bg-gradient-to-br from-[var(--bg-tertiary)] to-[var(--bg-secondary)]" />
                <div
                  className={`absolute bottom-1 right-1 sm:bottom-2 sm:right-2 px-2 py-0.5 rounded text-sm font-bold ${
                    item.score >= 90
                      ? 'bg-[#4ade80] text-black'
                      : item.score >= 75
                      ? 'bg-[#a3e635] text-black'
                      : item.score >= 60
                      ? 'bg-[#facc15] text-black'
                      : 'bg-[#fb923c] text-black'
                  }`}
                >
                  {item.score}
                </div>
              </div>
            ))}
          </div>

          <p className="text-xl text-center text-[var(--text-secondary)] max-w-2xl mx-auto">
            <span className="text-[var(--text-primary)] font-semibold">500 photos from your trip?</span>
            {' '}AI finds the 20 worth keeping — in minutes.
          </p>
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* VALUE #2: Learn From Every Shot */}
      {/* ============================================ */}
      <section className="py-20 px-4 bg-[var(--bg-secondary)]">
        <AnimatedSection className="max-w-5xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-10">
            <span className="text-4xl">📈</span>
            <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)]">
              Learn From Every Shot
            </h2>
          </div>

          {/* Side-by-side layout */}
          <div className="grid md:grid-cols-2 gap-8 items-center">
            {/* Sample photo placeholder */}
            <div className="aspect-[4/3] bg-gradient-to-br from-[var(--bg-tertiary)] to-[var(--bg-primary)] rounded-xl overflow-hidden relative">
              <div className="absolute inset-0 flex items-center justify-center">
                <div className="text-6xl opacity-30">📷</div>
              </div>
              <div className="absolute bottom-4 left-4 px-3 py-1 bg-[#a3e635] text-black rounded font-bold text-lg">
                78
              </div>
            </div>

            {/* Score breakdown */}
            <div className="space-y-6">
              {[
                { label: 'Composition', score: 8, color: '#4ade80', tip: 'Strong rule of thirds placement' },
                { label: 'Lighting', score: 6, color: '#facc15', tip: 'Slightly overexposed highlights' },
                { label: 'Sharpness', score: 9, color: '#4ade80', tip: 'Excellent focus throughout' },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex justify-between mb-2">
                    <span className="text-[var(--text-primary)] font-medium">{item.label}</span>
                    <span className="font-bold" style={{ color: item.color }}>{item.score}/10</span>
                  </div>
                  <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full rounded-full transition-all duration-1000"
                      style={{ width: `${item.score * 10}%`, backgroundColor: item.color }}
                    />
                  </div>
                  <p className="text-sm text-[var(--text-secondary)]">{item.tip}</p>
                </div>
              ))}

              <div className="mt-6 p-4 bg-[var(--bg-primary)] rounded-lg border-l-4 border-[#e94560]">
                <p className="text-[var(--text-secondary)]">
                  <span className="text-[#e94560] font-semibold">💡 Tip:</span> Try shooting 30 minutes earlier
                  to capture softer, more even lighting.
                </p>
              </div>
            </div>
          </div>

          <p className="text-xl text-center text-[var(--text-secondary)] mt-10 max-w-2xl mx-auto">
            Understand exactly what's working — and what to improve.
          </p>
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* VALUE #3: Match Your Style */}
      {/* ============================================ */}
      <section className="py-20 px-4">
        <AnimatedSection className="max-w-5xl mx-auto">
          <div className="flex items-center justify-center gap-3 mb-10">
            <span className="text-4xl">🎨</span>
            <h2 className="text-3xl md:text-4xl font-bold text-[var(--text-primary)]">
              Match Your Style
            </h2>
          </div>

          {/* Style cards */}
          <div className="grid sm:grid-cols-3 gap-4 mb-8">
            {[
              { name: 'Your Style', icon: '✨', description: 'Train on photos you love' },
              { name: 'Ansel Adams', icon: '🏔️', description: 'Dramatic landscapes' },
              { name: 'Steve McCurry', icon: '👤', description: 'Powerful portraits' },
            ].map((style) => (
              <div
                key={style.name}
                className="p-6 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] hover:border-[#e94560] transition-colors cursor-pointer group"
              >
                <div className="text-4xl mb-3">{style.icon}</div>
                <h3 className="text-lg font-semibold text-[var(--text-primary)] group-hover:text-[#e94560] transition-colors">
                  {style.name}
                </h3>
                <p className="text-sm text-[var(--text-secondary)]">{style.description}</p>
              </div>
            ))}
          </div>

          <p className="text-xl text-center text-[var(--text-secondary)] max-w-2xl mx-auto">
            Train the AI on <span className="text-[var(--text-primary)] font-semibold">YOUR</span> preferences.
            Or score like photographers you admire.
            <br />
            <span className="text-[#e94560]">Your photos, your standards.</span>
          </p>
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* SOCIAL PROOF SECTION */}
      {/* ============================================ */}
      <section className="py-20 px-4 bg-[var(--bg-secondary)]">
        <AnimatedSection className="max-w-5xl mx-auto">
          <h2 className="text-3xl md:text-4xl font-bold text-center text-[var(--text-primary)] mb-12">
            Photographers Love PhotoScorer
          </h2>

          <div className="grid md:grid-cols-3 gap-6">
            {[
              {
                quote: "I came back from Japan with 2,000 photos. PhotoScorer found the 50 I actually wanted to share.",
                author: "@travelphotographer",
                role: "Travel Photographer",
              },
              {
                quote: "Finally understand why some of my shots work and others don't. Like having a mentor in my pocket.",
                author: "Amateur photographer",
                role: "Reddit r/photography",
              },
              {
                quote: "The style matching is incredible. I trained it on my favorite street photographers and now it picks exactly the shots I would have chosen.",
                author: "@urbanshooter",
                role: "Street Photographer",
              },
            ].map((testimonial, i) => (
              <div
                key={i}
                className="p-6 bg-[var(--bg-primary)] rounded-xl border border-[var(--border-color)]"
              >
                <div className="text-[#e94560] text-4xl mb-4">"</div>
                <p className="text-[var(--text-primary)] mb-4 italic">
                  {testimonial.quote}
                </p>
                <div>
                  <p className="text-[var(--text-primary)] font-semibold">{testimonial.author}</p>
                  <p className="text-sm text-[var(--text-muted)]">{testimonial.role}</p>
                </div>
              </div>
            ))}
          </div>
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* FINAL CTA SECTION */}
      {/* ============================================ */}
      <section className="relative py-32 px-4 overflow-hidden">
        {/* Background image with parallax effect */}
        <div
          className="absolute inset-0 bg-cover bg-center bg-fixed"
          style={{ backgroundImage: `url(${CAROUSEL_IMAGES[2].url})` }}
        />
        <div className="absolute inset-0 bg-black/70" />

        <AnimatedSection className="relative z-10 text-center">
          <h2 className="text-4xl md:text-5xl font-bold text-white mb-6">
            Ready to find your best shots?
          </h2>
          <p className="text-xl text-white/80 mb-8 max-w-xl mx-auto">
            Start with 5 free photo credits. No credit card required.
          </p>
          {user ? (
            <Link
              to="/upload"
              className="inline-block px-10 py-5 bg-[#e94560] text-white rounded-lg text-xl font-semibold hover:bg-[#c73e54] transition-colors"
            >
              Upload Photos →
            </Link>
          ) : (
            <Link
              to="/signup"
              className="inline-block px-10 py-5 bg-[#e94560] text-white rounded-lg text-xl font-semibold hover:bg-[#c73e54] transition-colors"
            >
              GET STARTED FREE →
            </Link>
          )}
        </AnimatedSection>
      </section>

      {/* ============================================ */}
      {/* FOOTER */}
      {/* ============================================ */}
      <footer className="py-12 px-4 bg-[var(--bg-primary)] border-t border-[var(--border-color)]">
        <div className="max-w-5xl mx-auto">
          <div className="flex flex-col md:flex-row justify-between items-center gap-6">
            {/* Logo */}
            <div className="text-2xl font-bold text-[var(--text-primary)]">
              Photo<span className="text-[#e94560]">Scorer</span>
            </div>

            {/* Links */}
            <nav className="flex flex-wrap justify-center gap-6 text-[var(--text-secondary)]">
              <a href="#" className="hover:text-[var(--text-primary)] transition-colors">About</a>
              <a href="#" className="hover:text-[var(--text-primary)] transition-colors">Pricing</a>
              <a href="#" className="hover:text-[var(--text-primary)] transition-colors">Blog</a>
              <a href="#" className="hover:text-[var(--text-primary)] transition-colors">Contact</a>
            </nav>

            {/* Copyright */}
            <p className="text-sm text-[var(--text-muted)]">
              © 2025 PhotoScorer. Made for photographers who care.
            </p>
          </div>
        </div>
      </footer>
    </div>
  );
}
