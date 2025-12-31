import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function Home() {
  const { user } = useAuth();

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col">
      {/* Hero Section */}
      <section className="flex-1 flex flex-col items-center justify-center text-center px-4 py-16">
        <h1 className="text-4xl md:text-6xl font-bold text-[var(--text-primary)] mb-6">
          Score Your Photos
          <br />
          <span className="text-[#e94560]">Like a Pro</span>
        </h1>
        <p className="text-xl text-[var(--text-secondary)] max-w-2xl mb-8">
          Get AI-powered feedback on your photography. Understand what makes a great photo
          and learn how to improve your shots with detailed aesthetic and technical analysis.
        </p>
        <div className="flex flex-col sm:flex-row gap-4">
          {user ? (
            <>
              <Link
                to="/upload"
                className="px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
              >
                Upload Photos
              </Link>
              <Link
                to="/dashboard"
                className="px-8 py-4 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg text-lg font-semibold hover:opacity-80 transition-opacity"
              >
                View Dashboard
              </Link>
            </>
          ) : (
            <>
              <Link
                to="/signup"
                className="px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
              >
                Get Started Free
              </Link>
              <Link
                to="/login"
                className="px-8 py-4 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg text-lg font-semibold hover:opacity-80 transition-opacity"
              >
                Sign In
              </Link>
            </>
          )}
        </div>
        {!user && (
          <p className="text-[var(--text-muted)] mt-4">
            Start with 5 free photo credits. No credit card required.
          </p>
        )}
      </section>

      {/* Features Section */}
      <section className="bg-[var(--bg-secondary)] py-16 px-4">
        <div className="max-w-6xl mx-auto">
          <h2 className="text-3xl font-bold text-center text-[var(--text-primary)] mb-12">
            How It Works
          </h2>
          <div className="grid md:grid-cols-3 gap-8">
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">1</span>
              </div>
              <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-2">Upload</h3>
              <p className="text-[var(--text-secondary)]">
                Drag and drop your photos or select them from your device. We support JPEG, PNG, and HEIC.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">2</span>
              </div>
              <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-2">Analyze</h3>
              <p className="text-[var(--text-secondary)]">
                Our AI models evaluate composition, lighting, technical quality, and visual appeal.
              </p>
            </div>
            <div className="text-center p-6">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">3</span>
              </div>
              <h3 className="text-xl font-semibold text-[var(--text-primary)] mb-2">Improve</h3>
              <p className="text-[var(--text-secondary)]">
                Get detailed scores, critiques, and actionable tips to take your photography to the next level.
              </p>
            </div>
          </div>
        </div>
      </section>

      {/* Score Preview Section */}
      <section className="py-16 px-4">
        <div className="max-w-4xl mx-auto text-center">
          <h2 className="text-3xl font-bold text-[var(--text-primary)] mb-8">
            Detailed Scoring System
          </h2>
          <div className="grid grid-cols-2 md:grid-cols-5 gap-4 mb-8">
            {[
              { label: 'Excellent', score: '90+', color: '#4ade80' },
              { label: 'Strong', score: '75-89', color: '#a3e635' },
              { label: 'Competent', score: '60-74', color: '#facc15' },
              { label: 'Tourist', score: '40-59', color: '#fb923c' },
              { label: 'Flawed', score: '<40', color: '#f87171' },
            ].map((tier) => (
              <div
                key={tier.label}
                className="p-4 rounded-lg bg-[var(--bg-secondary)]"
              >
                <div
                  className="text-2xl font-bold mb-1"
                  style={{ color: tier.color }}
                >
                  {tier.score}
                </div>
                <div className="text-sm text-[var(--text-secondary)]">{tier.label}</div>
              </div>
            ))}
          </div>
          <p className="text-[var(--text-secondary)]">
            Each photo receives scores for aesthetic appeal and technical quality,
            combined into an overall score with detailed breakdowns.
          </p>
        </div>
      </section>

      {/* CTA Section */}
      {!user && (
        <section className="bg-[#e94560] py-16 px-4 text-center">
          <h2 className="text-3xl font-bold text-white mb-4">
            Ready to Improve Your Photography?
          </h2>
          <p className="text-white/80 mb-8 max-w-xl mx-auto">
            Join thousands of photographers who use Photo Score to understand and improve their work.
          </p>
          <Link
            to="/signup"
            className="inline-block px-8 py-4 bg-white text-[#e94560] rounded-lg text-lg font-semibold hover:bg-gray-100 transition-colors"
          >
            Start Free Trial
          </Link>
        </section>
      )}
    </div>
  );
}
