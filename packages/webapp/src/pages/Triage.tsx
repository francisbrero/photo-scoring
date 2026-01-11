import { ExternalLink } from 'lucide-react';

export default function Triage() {
  return (
    <div className="min-h-screen flex items-center justify-center p-6">
      <div className="max-w-2xl w-full bg-gray-800/50 backdrop-blur-sm rounded-2xl p-12 border border-gray-700/50 text-center">
        <div className="mb-8">
          <div className="w-20 h-20 bg-blue-500/10 rounded-full flex items-center justify-center mx-auto mb-6">
            <svg
              className="w-10 h-10 text-blue-400"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 3v2m6-2v2M9 19v2m6-2v2M5 9H3m2 6H3m18-6h-2m2 6h-2M7 19h10a2 2 0 002-2V7a2 2 0 00-2-2H7a2 2 0 00-2 2v10a2 2 0 002 2zM9 9h6v6H9V9z"
              />
            </svg>
          </div>
          <h1 className="text-3xl font-bold text-white mb-4">
            Triage is Available in the Desktop App
          </h1>
          <p className="text-gray-300 text-lg mb-6">
            For the best triage experience with local processing, faster speeds, and no upload limits,
            use our desktop application.
          </p>
        </div>

        <div className="bg-gray-900/50 rounded-xl p-6 mb-8 text-left">
          <h2 className="text-xl font-semibold text-white mb-4">Desktop App Benefits:</h2>
          <ul className="space-y-3 text-gray-300">
            <li className="flex items-start">
              <svg className="w-5 h-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span><strong>No upload time</strong> - photos never leave your computer</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span><strong>Faster processing</strong> - uses your computer's resources</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span><strong>Complete privacy</strong> - all processing happens locally</span>
            </li>
            <li className="flex items-start">
              <svg className="w-5 h-5 text-green-400 mr-3 mt-0.5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20">
                <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
              </svg>
              <span><strong>Works with folders</strong> - select entire photo directories</span>
            </li>
          </ul>
        </div>

        <a
          href="https://github.com/your-repo/releases/latest"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-2 bg-blue-600 hover:bg-blue-700 text-white font-semibold px-8 py-4 rounded-xl transition-colors shadow-lg shadow-blue-500/30"
        >
          Download Desktop App
          <ExternalLink className="w-5 h-5" />
        </a>

        <p className="text-gray-400 text-sm mt-6">
          Available for macOS, Windows, and Linux
        </p>
      </div>
    </div>
  );
}
