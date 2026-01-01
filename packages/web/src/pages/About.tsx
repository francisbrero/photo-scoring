import { useEffect } from 'react';
import { Link } from 'react-router-dom';
import { Footer } from '../components/Footer';

export function About() {
  // Scroll to top on mount
  useEffect(() => {
    window.scrollTo(0, 0);
  }, []);

  return (
    <div className="min-h-[calc(100vh-80px)] flex flex-col">
      <div className="flex-1 py-16 px-4">
        <div className="max-w-4xl mx-auto">
        {/* Header */}
        <div className="text-center mb-16">
          <h1 className="text-4xl md:text-5xl font-bold text-[var(--text-primary)] mb-4">
            About PhotoScorer
          </h1>
          <p className="text-xl text-[var(--text-secondary)]">
            AI-powered photo analysis for photographers who want to improve
          </p>
        </div>

        {/* Mission */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-4">Our Mission</h2>
          <p className="text-[var(--text-secondary)] mb-4">
            PhotoScorer was built for photographers who take thousands of photos but struggle to
            identify their best work. We use advanced AI to analyze your photos and provide
            actionable feedback that helps you grow as a photographer.
          </p>
          <p className="text-[var(--text-secondary)]">
            Whether you're a hobbyist coming back from vacation with 2,000 photos or a professional
            looking for objective feedback, PhotoScorer helps you find your keepers and understand
            what makes them great.
          </p>
        </section>

        {/* How It Works */}
        <section className="mb-16">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-4">How It Works</h2>
          <p className="text-[var(--text-secondary)] mb-4">
            Our AI analyzes multiple aspects of your photos including composition, lighting,
            sharpness, subject strength, and visual appeal. Each photo receives a comprehensive
            score along with detailed feedback on what's working and what could be improved.
          </p>
          <p className="text-[var(--text-secondary)]">
            Unlike simple filters or basic scoring apps, PhotoScorer provides personalized,
            actionable advice that helps you understand the "why" behind each score.
          </p>
        </section>

        {/* Terms of Service */}
        <section className="mb-16 bg-[var(--bg-secondary)] rounded-2xl p-8 border border-[var(--border-color)]">
          <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-6">Terms of Service</h2>

          <div className="space-y-6 text-[var(--text-secondary)]">
            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">1. Acceptance of Terms</h3>
              <p>
                By accessing or using PhotoScorer, you agree to be bound by these Terms of Service.
                If you do not agree to these terms, please do not use our service.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">2. Service Description</h3>
              <p>
                PhotoScorer provides AI-powered photo analysis and scoring services. We analyze
                uploaded photos to provide scores, feedback, and improvement suggestions. The
                service is provided "as is" and we make no guarantees about the accuracy or
                usefulness of the AI-generated feedback.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">3. User Accounts</h3>
              <p>
                You are responsible for maintaining the confidentiality of your account credentials
                and for all activities that occur under your account. You must provide accurate
                information when creating an account.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">4. Photo Uploads</h3>
              <p>
                You retain all rights to the photos you upload. By uploading photos, you grant us a
                limited license to process and analyze them for the purpose of providing our
                service. We do not share your photos with third parties except as necessary to
                provide the service (e.g., AI processing).
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">5. Credits and Payments</h3>
              <p>
                Credits are non-transferable and are used to analyze photos. Each photo analysis
                consumes one credit. Purchased credits do not expire. Refunds for unused credits
                may be requested within 30 days of purchase.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">6. Prohibited Content</h3>
              <p>
                You may not upload photos that contain illegal content, violate others' rights,
                or contain malware. We reserve the right to remove any content that violates
                these terms and to terminate accounts that repeatedly violate our policies.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">7. Privacy</h3>
              <p>
                We collect and process personal data as described in our privacy practices. We use
                industry-standard security measures to protect your data. Your photos are processed
                securely and are not used to train AI models without your explicit consent.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">8. Limitation of Liability</h3>
              <p>
                PhotoScorer is provided "as is" without warranties of any kind. We are not liable
                for any damages arising from your use of the service, including but not limited to
                loss of data, loss of profits, or any indirect damages.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">9. Changes to Terms</h3>
              <p>
                We may update these terms from time to time. Continued use of the service after
                changes constitutes acceptance of the new terms. We will notify users of
                significant changes via email or through the service.
              </p>
            </div>

            <div>
              <h3 className="font-semibold text-[var(--text-primary)] mb-2">10. Contact</h3>
              <p>
                For questions about these terms or our service, please{' '}
                <Link to="/contact" className="text-[#e94560] hover:underline">
                  contact us
                </Link>
                .
              </p>
            </div>
          </div>

          <p className="text-sm text-[var(--text-muted)] mt-6">
            Last updated: January 2025
          </p>
        </section>

        {/* CTA */}
        <div className="text-center">
          <Link
            to="/signup"
            className="inline-block px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
          >
            Get Started Free
          </Link>
          <p className="text-[var(--text-muted)] mt-4">
            Start with 5 free credits. No credit card required.
          </p>
        </div>
        </div>
      </div>

      <Footer />
    </div>
  );
}
