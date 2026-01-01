import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

const PRICING_TIERS = [
  {
    name: 'Starter',
    credits: 100,
    price: 9,
    pricePerCredit: 0.09,
    popular: false,
    description: 'Perfect for trying out PhotoScorer',
  },
  {
    name: 'Popular',
    credits: 500,
    price: 29,
    pricePerCredit: 0.058,
    popular: true,
    description: 'Best value for regular photographers',
  },
  {
    name: 'Pro',
    credits: 2000,
    price: 79,
    pricePerCredit: 0.0395,
    popular: false,
    description: 'For power users and professionals',
  },
];

export function Pricing() {
  const { user } = useAuth();

  return (
    <div className="min-h-[calc(100vh-80px)] py-16 px-4">
      <div className="max-w-5xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-4">
            Simple, Credit-Based Pricing
          </h1>
          <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
            Pay only for what you use. No subscriptions, no hidden fees.
            <br />
            <span className="text-[#e94560] font-semibold">Start with 5 free credits!</span>
          </p>
        </div>

        {/* How Credits Work */}
        <div className="bg-[var(--bg-secondary)] rounded-2xl p-8 mb-12 border border-[var(--border-color)]">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6 text-center">
            How Credits Work
          </h2>
          <div className="grid md:grid-cols-3 gap-6">
            <div className="text-center">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">📷</span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">1 Credit = 1 Photo</h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Each photo analysis uses exactly one credit
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">🎯</span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">Full Analysis</h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Score, breakdown, critique, and improvement tips included
              </p>
            </div>
            <div className="text-center">
              <div className="w-16 h-16 bg-[#e94560]/20 rounded-full flex items-center justify-center mx-auto mb-4">
                <span className="text-3xl">♾️</span>
              </div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">Never Expire</h3>
              <p className="text-sm text-[var(--text-secondary)]">
                Your credits are yours forever, use them anytime
              </p>
            </div>
          </div>
        </div>

        {/* Pricing Tiers */}
        <div className="grid md:grid-cols-3 gap-6 mb-12">
          {PRICING_TIERS.map((tier) => (
            <div
              key={tier.name}
              className={`relative rounded-2xl p-8 border ${
                tier.popular
                  ? 'bg-[#e94560]/10 border-[#e94560]'
                  : 'bg-[var(--bg-secondary)] border-[var(--border-color)]'
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-3 left-1/2 -translate-x-1/2 px-4 py-1 bg-[#e94560] text-white text-sm font-semibold rounded-full">
                  Most Popular
                </div>
              )}
              <div className="text-center mb-6">
                <h3 className="text-xl font-bold text-[var(--text-primary)] mb-2">{tier.name}</h3>
                <p className="text-sm text-[var(--text-secondary)]">{tier.description}</p>
              </div>
              <div className="text-center mb-6">
                <div className="text-4xl font-bold text-[var(--text-primary)]">
                  ${tier.price}
                </div>
                <div className="text-[var(--text-secondary)]">
                  {tier.credits} credits
                </div>
                <div className="text-sm text-[var(--text-muted)] mt-1">
                  ${tier.pricePerCredit.toFixed(3)} per photo
                </div>
              </div>
              <Link
                to={user ? '/dashboard' : '/signup'}
                className={`block w-full py-3 rounded-lg text-center font-semibold transition-colors ${
                  tier.popular
                    ? 'bg-[#e94560] text-white hover:bg-[#c73e54]'
                    : 'bg-[var(--bg-tertiary)] text-[var(--text-primary)] hover:opacity-80'
                }`}
              >
                {user ? 'Buy Credits' : 'Get Started'}
              </Link>
            </div>
          ))}
        </div>

        {/* FAQ */}
        <div className="bg-[var(--bg-secondary)] rounded-2xl p-8 border border-[var(--border-color)]">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6 text-center">
            Frequently Asked Questions
          </h2>
          <div className="space-y-6 max-w-3xl mx-auto">
            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">
                What happens to my free credits?
              </h3>
              <p className="text-[var(--text-secondary)]">
                Every new account gets 5 free credits to try PhotoScorer. These never expire and are
                added to any credits you purchase.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">
                Can I get a refund?
              </h3>
              <p className="text-[var(--text-secondary)]">
                Unused credits can be refunded within 30 days of purchase. Once credits are used for
                photo analysis, they cannot be refunded.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">
                What payment methods do you accept?
              </h3>
              <p className="text-[var(--text-secondary)]">
                We accept all major credit cards (Visa, Mastercard, American Express) through our
                secure payment processor, Stripe.
              </p>
            </div>
            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">
                Do credits expire?
              </h3>
              <p className="text-[var(--text-secondary)]">
                No! Your credits never expire. Use them whenever you're ready.
              </p>
            </div>
          </div>
        </div>

        {/* CTA */}
        <div className="text-center mt-12">
          <p className="text-[var(--text-secondary)] mb-4">
            Questions? Reach out to us at{' '}
            <a href="mailto:support@photoscorer.com" className="text-[#e94560] hover:underline">
              support@photoscorer.com
            </a>
          </p>
        </div>
      </div>
    </div>
  );
}
