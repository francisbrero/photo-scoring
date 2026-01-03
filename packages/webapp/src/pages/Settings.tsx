import { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import { apiFetch } from '../lib/api';

interface Transaction {
  id: string;
  amount: number;
  type: string;
  stripe_payment_id: string | null;
  created_at: string;
}

const PRICING_DISPLAY = [
  {
    planId: 'credits_100',
    name: 'Starter',
    credits: 100,
    price: 9,
    pricePerCredit: 0.09,
    popular: false,
    description: 'Perfect for trying out PhotoScorer',
  },
  {
    planId: 'credits_500',
    name: 'Popular',
    credits: 500,
    price: 49,
    pricePerCredit: 0.098,
    popular: true,
    description: 'Best value for regular photographers',
  },
  {
    planId: 'credits_2000',
    name: 'Pro',
    credits: 2000,
    price: 179,
    pricePerCredit: 0.0895,
    popular: false,
    description: 'For power users and professionals',
  },
];

export function Settings() {
  const { user, session, credits, refreshCredits } = useAuth();
  const [searchParams, setSearchParams] = useSearchParams();
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [loadingTransactions, setLoadingTransactions] = useState(true);
  const [purchaseLoading, setPurchaseLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  // Handle success/cancel from Stripe redirect
  useEffect(() => {
    const checkoutStatus = searchParams.get('checkout');
    if (checkoutStatus === 'success') {
      setSuccessMessage('Payment successful! Your credits have been added to your account.');
      refreshCredits();
      // Clear the query param
      setSearchParams({}, { replace: true });
    } else if (checkoutStatus === 'cancel') {
      setError('Payment was cancelled. No charges were made.');
      setSearchParams({}, { replace: true });
    }
  }, [searchParams, setSearchParams, refreshCredits]);

  // Fetch transactions
  useEffect(() => {
    async function fetchTransactions() {
      if (!session?.access_token) return;

      try {
        const response = await apiFetch('/api/billing/transactions?limit=10', {
          headers: {
            Authorization: `Bearer ${session.access_token}`,
          },
        });
        if (response.ok) {
          const data = await response.json();
          setTransactions(data.transactions);
        }
      } catch (err) {
        console.error('Failed to fetch transactions:', err);
      } finally {
        setLoadingTransactions(false);
      }
    }

    fetchTransactions();
  }, [session]);

  const handlePurchase = async (planId: string) => {
    if (!session?.access_token) return;

    setPurchaseLoading(planId);
    setError(null);

    try {
      const response = await apiFetch('/api/billing/checkout', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${session.access_token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          plan_id: planId,
          success_url: `${window.location.origin}/settings?checkout=success`,
          cancel_url: `${window.location.origin}/settings?checkout=cancel`,
        }),
      });

      if (!response.ok) {
        const data = await response.json();
        throw new Error(data.detail || 'Failed to create checkout session');
      }

      const data = await response.json();
      // Redirect to Stripe checkout
      window.location.href = data.checkout_url;
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to start checkout');
      setPurchaseLoading(null);
    }
  };

  const formatDate = (dateString: string) => {
    return new Date(dateString).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="max-w-4xl mx-auto">
      <div className="mb-8">
        <h1 className="text-3xl font-bold text-[var(--text-primary)] mb-2">Settings</h1>
        <p className="text-[var(--text-secondary)]">
          Manage your account and credits
        </p>
      </div>

      {/* Success/Error Messages */}
      {successMessage && (
        <div className="mb-6 p-4 bg-green-500/20 border border-green-500 rounded-lg text-green-400">
          {successMessage}
        </div>
      )}
      {error && (
        <div className="mb-6 p-4 bg-red-500/20 border border-red-500 rounded-lg text-red-400">
          {error}
        </div>
      )}

      {/* Account Section */}
      <div className="bg-[var(--bg-secondary)] rounded-xl p-6 mb-6 border border-[var(--border-color)]">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">Account</h2>
        <div className="flex items-center gap-4">
          <div className="w-12 h-12 rounded-full bg-[#e94560] flex items-center justify-center text-white text-xl font-medium">
            {user?.email?.[0].toUpperCase() || 'U'}
          </div>
          <div>
            <p className="text-[var(--text-primary)] font-medium">{user?.email}</p>
            <p className="text-sm text-[var(--text-muted)]">
              Member since {user?.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
            </p>
          </div>
        </div>
      </div>

      {/* Credits Section */}
      <div className="bg-[var(--bg-secondary)] rounded-xl p-6 mb-6 border border-[var(--border-color)]">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">Credits</h2>

        {/* Current Balance */}
        <div className="flex items-center justify-between p-4 bg-[var(--bg-tertiary)] rounded-lg mb-6">
          <div>
            <p className="text-sm text-[var(--text-muted)] mb-1">Current Balance</p>
            <p className="text-4xl font-bold text-[#4ade80]">
              {credits !== null ? credits : '...'}
            </p>
          </div>
          <div className="text-right">
            <p className="text-sm text-[var(--text-muted)]">credits available</p>
            <p className="text-xs text-[var(--text-muted)] mt-1">1 credit = 1 photo analysis</p>
          </div>
        </div>

        {/* Pricing Tiers */}
        <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Buy More Credits</h3>
        <div className="grid md:grid-cols-3 gap-4">
          {PRICING_DISPLAY.map((tier) => (
            <div
              key={tier.planId}
              className={`relative rounded-xl p-5 border ${
                tier.popular
                  ? 'bg-[#e94560]/10 border-[#e94560]'
                  : 'bg-[var(--bg-tertiary)] border-[var(--border-color)]'
              }`}
            >
              {tier.popular && (
                <div className="absolute -top-2.5 left-1/2 -translate-x-1/2 px-3 py-0.5 bg-[#e94560] text-white text-xs font-semibold rounded-full">
                  Most Popular
                </div>
              )}
              <div className="text-center mb-4">
                <h4 className="font-semibold text-[var(--text-primary)] mb-1">{tier.name}</h4>
                <p className="text-xs text-[var(--text-muted)]">{tier.description}</p>
              </div>
              <div className="text-center mb-4">
                <div className="text-3xl font-bold text-[var(--text-primary)]">
                  ${tier.price}
                </div>
                <div className="text-sm text-[var(--text-secondary)]">
                  {tier.credits} credits
                </div>
                <div className="text-xs text-[var(--text-muted)] mt-1">
                  ${tier.pricePerCredit.toFixed(3)} per photo
                </div>
              </div>
              <button
                onClick={() => handlePurchase(tier.planId)}
                disabled={purchaseLoading !== null}
                className={`w-full py-2.5 rounded-lg font-semibold transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${
                  tier.popular
                    ? 'bg-[#e94560] text-white hover:bg-[#c73e54]'
                    : 'bg-[var(--bg-secondary)] text-[var(--text-primary)] hover:opacity-80 border border-[var(--border-color)]'
                }`}
              >
                {purchaseLoading === tier.planId ? (
                  <span className="flex items-center justify-center gap-2">
                    <div className="w-4 h-4 border-2 border-current border-t-transparent rounded-full animate-spin" />
                    Processing...
                  </span>
                ) : (
                  'Buy Credits'
                )}
              </button>
            </div>
          ))}
        </div>
      </div>

      {/* Transaction History */}
      <div className="bg-[var(--bg-secondary)] rounded-xl p-6 border border-[var(--border-color)]">
        <h2 className="text-xl font-semibold text-[var(--text-primary)] mb-4">Recent Transactions</h2>

        {loadingTransactions ? (
          <div className="text-center py-8 text-[var(--text-muted)]">
            Loading transactions...
          </div>
        ) : transactions.length === 0 ? (
          <div className="text-center py-8 text-[var(--text-muted)]">
            No transactions yet. Purchase credits to see your history here.
          </div>
        ) : (
          <div className="space-y-3">
            {transactions.map((transaction) => (
              <div
                key={transaction.id}
                className="flex items-center justify-between p-3 bg-[var(--bg-tertiary)] rounded-lg"
              >
                <div className="flex items-center gap-3">
                  <div className={`w-8 h-8 rounded-full flex items-center justify-center ${
                    transaction.amount > 0 ? 'bg-green-500/20 text-green-400' : 'bg-red-500/20 text-red-400'
                  }`}>
                    {transaction.amount > 0 ? '+' : '-'}
                  </div>
                  <div>
                    <p className="text-sm text-[var(--text-primary)]">
                      {transaction.type === 'purchase' ? 'Credit Purchase' :
                       transaction.type === 'usage' ? 'Photo Analysis' :
                       transaction.type === 'trial' ? 'Welcome Bonus' : transaction.type}
                    </p>
                    <p className="text-xs text-[var(--text-muted)]">
                      {formatDate(transaction.created_at)}
                    </p>
                  </div>
                </div>
                <div className={`font-semibold ${
                  transaction.amount > 0 ? 'text-green-400' : 'text-red-400'
                }`}>
                  {transaction.amount > 0 ? '+' : ''}{transaction.amount} credits
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
