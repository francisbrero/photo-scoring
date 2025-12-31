import { useState, type FormEvent } from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';

export function ForgotPassword() {
  const [email, setEmail] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [success, setSuccess] = useState(false);

  const { resetPassword } = useAuth();

  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    setError(null);
    setLoading(true);

    const { error } = await resetPassword(email);

    if (error) {
      setError(error.message);
      setLoading(false);
    } else {
      setSuccess(true);
    }
  };

  if (success) {
    return (
      <div className="min-h-[calc(100vh-80px)] flex items-center justify-center px-4">
        <div className="w-full max-w-md">
          <div className="bg-[var(--bg-secondary)] rounded-xl p-8 shadow-lg text-center">
            <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
              <svg className="w-8 h-8 text-green-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z" />
              </svg>
            </div>
            <h1 className="text-2xl font-bold text-[var(--text-primary)] mb-2">Check Your Email</h1>
            <p className="text-[var(--text-secondary)] mb-6">
              We've sent a password reset link to <strong>{email}</strong>.
              Click the link in the email to reset your password.
            </p>
            <Link
              to="/login"
              className="text-[#e94560] hover:underline font-medium"
            >
              Back to Sign In
            </Link>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-[calc(100vh-80px)] flex items-center justify-center px-4">
      <div className="w-full max-w-md">
        <div className="bg-[var(--bg-secondary)] rounded-xl p-8 shadow-lg">
          <h1 className="text-2xl font-bold text-[var(--text-primary)] text-center mb-2">
            Reset Your Password
          </h1>
          <p className="text-[var(--text-muted)] text-center mb-6">
            Enter your email and we'll send you a reset link
          </p>

          {error && (
            <div className="mb-4 p-3 bg-red-500/10 border border-red-500/20 rounded-lg text-red-400 text-sm">
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="email" className="block text-sm font-medium text-[var(--text-secondary)] mb-1">
                Email
              </label>
              <input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
                className="w-full px-4 py-3 bg-[var(--bg-primary)] border border-[var(--border-color)] rounded-lg text-[var(--text-primary)] focus:outline-none focus:border-[#e94560]"
                placeholder="you@example.com"
              />
            </div>

            <button
              type="submit"
              disabled={loading}
              className="w-full py-3 bg-[#e94560] text-white rounded-lg font-semibold hover:bg-[#c73e54] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {loading ? 'Sending...' : 'Send Reset Link'}
            </button>
          </form>

          <p className="mt-6 text-center text-[var(--text-secondary)]">
            Remember your password?{' '}
            <Link to="/login" className="text-[#e94560] hover:underline font-medium">
              Sign in
            </Link>
          </p>
        </div>
      </div>
    </div>
  );
}
