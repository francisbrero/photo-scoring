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

// Images for the problem section grid (mixed quality travel photos)
const GRID_IMAGES = [
  'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=200&q=60',
  'https://images.unsplash.com/photo-1500530855697-b586d89ba3ee?w=200&q=60',
  'https://images.unsplash.com/photo-1507525428034-b723cf961d3e?w=200&q=60',
  'https://images.unsplash.com/photo-1519681393784-d120267933ba?w=200&q=60',
  'https://images.unsplash.com/photo-1505142468610-359e7d316be0?w=200&q=60',
  'https://images.unsplash.com/photo-1441974231531-c6227db76b6e?w=200&q=60',
  'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=200&q=60',
  'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=200&q=60',
  'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=200&q=60',
  'https://images.unsplash.com/photo-1465056836041-7f43ac27dcb5?w=200&q=60',
  'https://images.unsplash.com/photo-1482938289607-e9573fc25ebb?w=200&q=60',
  'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=200&q=60',
  'https://images.unsplash.com/photo-1472214103451-9374bd1c798e?w=200&q=60',
  'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=200&q=60',
  'https://images.unsplash.com/photo-1464822759023-fed622ff2c3b?w=200&q=60',
  'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=200&q=60',
  'https://images.unsplash.com/photo-1518173946687-a4c036bc3c95?w=200&q=60',
  'https://images.unsplash.com/photo-1490750967868-88aa4486c946?w=200&q=60',
  'https://images.unsplash.com/photo-1504893524553-b855bce32c67?w=200&q=60',
  'https://images.unsplash.com/photo-1439066615861-d1af74d74000?w=200&q=60',
  'https://images.unsplash.com/photo-1497436072909-60f360e1d4b1?w=200&q=60',
  'https://images.unsplash.com/photo-1426604966848-d7adac402bff?w=200&q=60',
  'https://images.unsplash.com/photo-1505765050516-f72dcac9c60e?w=200&q=60',
  'https://images.unsplash.com/photo-1470252649378-9c29740c9fa8?w=200&q=60',
];

// Images for the "Find the Keepers" section with scores
const KEEPER_IMAGES = [
  { url: 'https://images.unsplash.com/photo-1476514525535-07fb3b4ae5f1?w=300&q=70', score: 72 },
  { url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=300&q=70', score: 89 },
  { url: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=300&q=70', score: 94 },
  { url: 'https://images.unsplash.com/photo-1470071459604-3b5ec3a7fe05?w=300&q=70', score: 61 },
  { url: 'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=300&q=70', score: 78 },
];

// Images for the "Learn From Every Shot" rotating showcase
const LEARN_IMAGES = [
  {
    url: 'https://images.unsplash.com/photo-1506905925346-21bda4d32df4?w=800&q=80',
    score: 78,
    composition: { score: 8, tip: 'Strong rule of thirds placement' },
    lighting: { score: 6, tip: 'Slightly overexposed highlights' },
    sharpness: { score: 9, tip: 'Excellent focus throughout' },
    tip: 'Try shooting 30 minutes earlier to capture softer, more even lighting.',
  },
  {
    url: 'https://images.unsplash.com/photo-1469474968028-56623f02e42e?w=800&q=80',
    score: 92,
    composition: { score: 9, tip: 'Beautiful leading lines draw the eye' },
    lighting: { score: 9, tip: 'Perfect golden hour warmth' },
    sharpness: { score: 8, tip: 'Sharp foreground, soft background' },
    tip: 'Consider a polarizing filter to enhance the sky contrast even more.',
  },
  {
    url: 'https://images.unsplash.com/photo-1433086966358-54859d0ed716?w=800&q=80',
    score: 85,
    composition: { score: 7, tip: 'Centered subject works well here' },
    lighting: { score: 9, tip: 'Diffused light creates even exposure' },
    sharpness: { score: 9, tip: 'Tack sharp throughout the frame' },
    tip: 'Try a longer exposure to create silky smooth water effect.',
  },
  {
    url: 'https://images.unsplash.com/photo-1501785888041-af3ef285b470?w=800&q=80',
    score: 88,
    composition: { score: 9, tip: 'Perfect reflection creates symmetry' },
    lighting: { score: 8, tip: 'Blue hour provides calm mood' },
    sharpness: { score: 8, tip: 'Good sharpness across the frame' },
    tip: 'A graduated ND filter would help balance the sky exposure.',
  },
  {
    url: 'https://images.unsplash.com/photo-1447752875215-b2761acb3c5d?w=800&q=80',
    score: 71,
    composition: { score: 6, tip: 'Path creates nice leading line' },
    lighting: { score: 7, tip: 'Dappled light adds interest' },
    sharpness: { score: 8, tip: 'Good focus on the path' },
    tip: 'Lower angle would make the path more prominent and dramatic.',
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

// Score color helper
function getScoreColor(score: number): string {
  if (score >= 90) return '#4ade80';
  if (score >= 75) return '#a3e635';
  if (score >= 60) return '#facc15';
  return '#fb923c';
}

export function Home() {
  const { user } = useAuth();
  const [currentImageIndex, setCurrentImageIndex] = useState(0);
  const [learnImageIndex, setLearnImageIndex] = useState(0);

  // Carousel auto-advance
  useEffect(() => {
    const interval = setInterval(() => {
      setCurrentImageIndex((prev) => (prev + 1) % CAROUSEL_IMAGES.length);
    }, 6000); // 6 seconds per image

    return () => clearInterval(interval);
  }, []);

  // Learn section image rotation
  useEffect(() => {
    const interval = setInterval(() => {
      setLearnImageIndex((prev) => (prev + 1) % LEARN_IMAGES.length);
    }, 5000); // 5 seconds per image

    return () => clearInterval(interval);
  }, []);

  const currentLearnImage = LEARN_IMAGES[learnImageIndex];

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
          {/* Grid of photo thumbnails with question marks overlay */}
          <div className="grid grid-cols-4 sm:grid-cols-6 gap-2 mb-8">
            {GRID_IMAGES.map((url, i) => (
              <div
                key={i}
                className="aspect-square rounded-lg overflow-hidden relative group"
              >
                <img
                  src={url}
                  alt=""
                  className="w-full h-full object-cover opacity-60"
                  loading="lazy"
                />
                <div className="absolute inset-0 bg-black/40 flex items-center justify-center">
                  <span className="text-2xl text-white/70 font-bold">?</span>
                </div>
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
            {KEEPER_IMAGES.map((item, i) => {
              const isHighlight = item.score === Math.max(...KEEPER_IMAGES.map(k => k.score));
              return (
                <div
                  key={i}
                  className={`relative w-20 h-20 sm:w-28 sm:h-28 rounded-lg overflow-hidden transition-all duration-300 ${
                    isHighlight ? 'ring-4 ring-[#4ade80] scale-110 z-10' : 'opacity-70 hover:opacity-90'
                  }`}
                >
                  <img
                    src={item.url}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                  <div
                    className={`absolute bottom-1 right-1 sm:bottom-2 sm:right-2 px-2 py-0.5 rounded text-sm font-bold text-black`}
                    style={{ backgroundColor: getScoreColor(item.score) }}
                  >
                    {item.score}
                  </div>
                </div>
              );
            })}
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
            {/* Rotating photo */}
            <div className="aspect-[4/3] rounded-xl overflow-hidden relative">
              {LEARN_IMAGES.map((image, index) => (
                <div
                  key={image.url}
                  className={`absolute inset-0 transition-opacity duration-1000 ${
                    index === learnImageIndex ? 'opacity-100' : 'opacity-0'
                  }`}
                >
                  <img
                    src={image.url}
                    alt=""
                    className="w-full h-full object-cover"
                    loading="lazy"
                  />
                </div>
              ))}
              <div
                className="absolute bottom-4 left-4 px-3 py-1 rounded font-bold text-lg text-black transition-all duration-500"
                style={{ backgroundColor: getScoreColor(currentLearnImage.score) }}
              >
                {currentLearnImage.score}
              </div>
              {/* Image indicator dots */}
              <div className="absolute bottom-4 right-4 flex gap-1.5">
                {LEARN_IMAGES.map((_, index) => (
                  <button
                    key={index}
                    onClick={() => setLearnImageIndex(index)}
                    className={`w-2 h-2 rounded-full transition-all ${
                      index === learnImageIndex ? 'bg-white w-4' : 'bg-white/50'
                    }`}
                  />
                ))}
              </div>
            </div>

            {/* Score breakdown - updates with image */}
            <div className="space-y-6">
              {[
                { label: 'Composition', data: currentLearnImage.composition },
                { label: 'Lighting', data: currentLearnImage.lighting },
                { label: 'Sharpness', data: currentLearnImage.sharpness },
              ].map((item) => (
                <div key={item.label}>
                  <div className="flex justify-between mb-2">
                    <span className="text-[var(--text-primary)] font-medium">{item.label}</span>
                    <span className="font-bold" style={{ color: getScoreColor(item.data.score * 10) }}>
                      {item.data.score}/10
                    </span>
                  </div>
                  <div className="h-2 bg-[var(--bg-primary)] rounded-full overflow-hidden mb-2">
                    <div
                      className="h-full rounded-full transition-all duration-700"
                      style={{
                        width: `${item.data.score * 10}%`,
                        backgroundColor: getScoreColor(item.data.score * 10)
                      }}
                    />
                  </div>
                  <p className="text-sm text-[var(--text-secondary)] transition-opacity duration-500">
                    {item.data.tip}
                  </p>
                </div>
              ))}

              <div className="mt-6 p-4 bg-[var(--bg-primary)] rounded-lg border-l-4 border-[#e94560]">
                <p className="text-[var(--text-secondary)] transition-opacity duration-500">
                  <span className="text-[#e94560] font-semibold">💡 Tip:</span> {currentLearnImage.tip}
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
              <Link to="/about" className="hover:text-[var(--text-primary)] transition-colors">About</Link>
              <Link to="/pricing" className="hover:text-[var(--text-primary)] transition-colors">Pricing</Link>
              <a href="https://spraiandprai.com" target="_blank" rel="noopener noreferrer" className="hover:text-[var(--text-primary)] transition-colors">Blog</a>
              <a href="mailto:support@photoscorer.com" className="hover:text-[var(--text-primary)] transition-colors">Contact</a>
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
