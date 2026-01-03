import { useState, useEffect } from 'react';

interface ReleaseAsset {
  name: string;
  browser_download_url: string;
  size: number;
}

interface Release {
  tag_name: string;
  name: string;
  published_at: string;
  body: string;
  assets: ReleaseAsset[];
}

type Platform = 'mac' | 'windows' | 'linux';

function detectPlatform(): Platform {
  const ua = navigator.userAgent.toLowerCase();
  if (ua.includes('mac')) return 'mac';
  if (ua.includes('win')) return 'windows';
  return 'linux';
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return bytes + ' B';
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

function formatDate(dateString: string): string {
  return new Date(dateString).toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric',
  });
}

const PLATFORM_INFO = {
  mac: {
    name: 'macOS',
    icon: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M18.71 19.5c-.83 1.24-1.71 2.45-3.05 2.47-1.34.03-1.77-.79-3.29-.79-1.53 0-2 .77-3.27.82-1.31.05-2.3-1.32-3.14-2.53C4.25 17 2.94 12.45 4.7 9.39c.87-1.52 2.43-2.48 4.12-2.51 1.28-.02 2.5.87 3.29.87.78 0 2.26-1.07 3.81-.91.65.03 2.47.26 3.64 1.98-.09.06-2.17 1.28-2.15 3.81.03 3.02 2.65 4.03 2.68 4.04-.03.07-.42 1.44-1.38 2.83M13 3.5c.73-.83 1.94-1.46 2.94-1.5.13 1.17-.34 2.35-1.04 3.19-.69.85-1.83 1.51-2.95 1.42-.15-1.15.41-2.35 1.05-3.11z" />
      </svg>
    ),
    extension: '.dmg',
    pattern: /\.dmg$/,
  },
  windows: {
    name: 'Windows',
    icon: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M3 12V6.75l6-1.32v6.48L3 12zm17-9v8.75l-10 .15V5.21L20 3zM3 13l6 .09v6.81l-6-1.15V13zm17 .25V22l-10-1.91V13.1l10 .15z" />
      </svg>
    ),
    extension: '.exe',
    pattern: /\.exe$/,
  },
  linux: {
    name: 'Linux',
    icon: (
      <svg className="w-8 h-8" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12.504 0c-.155 0-.315.008-.48.021-4.226.333-3.105 4.807-3.17 6.298-.076 1.092-.3 1.953-1.05 3.02-.885 1.051-2.127 2.75-2.716 4.521-.278.832-.41 1.684-.287 2.489.117.779.392 1.498.845 2.13.566.792 1.347 1.471 2.325 1.953.196.096.394.18.594.252.187.064.348.13.525.177-.08.112-.155.228-.227.348-.392.654-.577 1.472-.542 2.367.028.715.196 1.465.55 2.188a.95.95 0 0 0 .313.322l.074.05c.196.127.385.254.576.378.383.247.798.469 1.247.656.448.187.93.339 1.446.438.477.092.973.134 1.49.134.51 0 1.003-.041 1.474-.13.476-.089.939-.23 1.372-.417.449-.195.863-.433 1.232-.706.168-.124.33-.254.482-.386.068-.06.141-.115.205-.177a.945.945 0 0 0 .268-.3c.297-.687.458-1.401.487-2.082.037-.895-.15-1.72-.546-2.379a3.655 3.655 0 0 0-.207-.317c.157-.044.313-.103.459-.164.195-.081.38-.177.556-.283a5.61 5.61 0 0 0 1.035-.759c.49-.433.85-.929 1.122-1.476.295-.594.488-1.238.573-1.909.078-.623.069-1.264-.038-1.89-.107-.643-.324-1.272-.625-1.86-.61-1.19-1.577-2.146-2.658-2.84-.9-.58-1.874-.96-2.823-1.111a9.04 9.04 0 0 0-1.262-.075c-.178 0-.353.008-.52.021v.001l.002-.001.002-.001zm-.504 2c.043 0 .086.002.127.004.27.007.538.034.798.093 1.012.232 2.105.903 2.843 1.483.738.58 1.176 1.17 1.395 1.687.095.222.155.44.178.652.012.1.014.201.008.301-.003.052-.01.104-.02.154a1.72 1.72 0 0 1-.06.234c-.034.104-.085.208-.154.312-.039.058-.085.117-.138.175-.054.059-.114.117-.183.174-.069.058-.144.115-.228.17-.084.056-.174.111-.274.163a3.49 3.49 0 0 1-.342.148 3.9 3.9 0 0 1-.397.12 4.18 4.18 0 0 1-.452.088 4.23 4.23 0 0 1-.984.028 4.35 4.35 0 0 1-.455-.055 4.113 4.113 0 0 1-.435-.108 3.688 3.688 0 0 1-.404-.151 3.217 3.217 0 0 1-.362-.181 2.76 2.76 0 0 1-.309-.198 2.328 2.328 0 0 1-.247-.205 1.938 1.938 0 0 1-.182-.197 1.62 1.62 0 0 1-.138-.184c-.039-.057-.07-.114-.096-.17a1.09 1.09 0 0 1-.055-.153.852.852 0 0 1-.024-.13.604.604 0 0 1-.003-.102c.003-.063.015-.125.038-.186.023-.062.056-.122.1-.181.045-.06.1-.12.167-.177.067-.058.146-.115.236-.168.09-.054.191-.106.305-.153.114-.048.24-.093.377-.132.137-.04.285-.074.443-.102.16-.028.328-.05.504-.064.088-.007.177-.011.267-.011zm-.248 1.978c-.154 0-.304.013-.45.04a3.4 3.4 0 0 0-.417.103c-.136.043-.265.095-.388.154-.123.06-.238.127-.346.202-.107.075-.206.157-.297.245-.09.09-.172.185-.244.286-.072.102-.133.21-.183.322a1.48 1.48 0 0 0-.107.367 1.38 1.38 0 0 0-.019.389c.02.136.057.268.113.393.056.125.13.244.221.355.092.111.201.215.326.308.124.093.265.177.421.249.155.072.325.133.509.182.183.05.38.088.589.113.418.05.865.05 1.324 0a5.76 5.76 0 0 0 .589-.113c.184-.05.354-.11.509-.182.156-.072.297-.156.421-.249.125-.093.234-.197.326-.308.091-.111.165-.23.221-.355.056-.125.093-.257.113-.393.02-.136.016-.266-.019-.389a1.48 1.48 0 0 0-.107-.367 1.59 1.59 0 0 0-.183-.322 2.062 2.062 0 0 0-.244-.286 2.349 2.349 0 0 0-.297-.245 2.637 2.637 0 0 0-.346-.202 2.916 2.916 0 0 0-.388-.154 3.384 3.384 0 0 0-.417-.103 3.58 3.58 0 0 0-.45-.04zm.508 7.22c.585 0 1.088.199 1.508.597.419.398.629.883.629 1.454 0 .572-.21 1.058-.629 1.456-.42.399-.923.598-1.508.598-.587 0-1.09-.199-1.51-.598-.418-.398-.628-.884-.628-1.456 0-.571.21-1.056.628-1.454.42-.398.923-.597 1.51-.597z" />
      </svg>
    ),
    extension: '.AppImage',
    pattern: /\.AppImage$/,
  },
};

export function Downloads() {
  const [release, setRelease] = useState<Release | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [selectedPlatform, setSelectedPlatform] = useState<Platform>(detectPlatform);

  useEffect(() => {
    async function fetchRelease() {
      try {
        const response = await fetch(
          'https://api.github.com/repos/francisbrero/photo-scoring/releases/latest'
        );
        if (response.status === 404) {
          setRelease(null);
          setLoading(false);
          return;
        }
        if (!response.ok) throw new Error('Failed to fetch release');
        const data = await response.json();
        setRelease(data);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Failed to load release');
      } finally {
        setLoading(false);
      }
    }
    fetchRelease();
  }, []);

  const getAssetForPlatform = (platform: Platform): ReleaseAsset | undefined => {
    if (!release) return undefined;
    return release.assets.find((asset) => PLATFORM_INFO[platform].pattern.test(asset.name));
  };

  const primaryAsset = getAssetForPlatform(selectedPlatform);

  return (
    <div className="min-h-screen bg-[var(--bg-primary)] py-12">
      <div className="max-w-4xl mx-auto px-4">
        {/* Header */}
        <div className="text-center mb-12">
          <h1 className="text-4xl font-bold text-[var(--text-primary)] mb-4">
            Download Photo Scorer
          </h1>
          <p className="text-xl text-[var(--text-secondary)] max-w-2xl mx-auto">
            Score your photos offline with our desktop app. No internet required after installation.
          </p>
        </div>

        {loading ? (
          <div className="flex justify-center py-12">
            <div className="w-8 h-8 border-4 border-[#e94560] border-t-transparent rounded-full animate-spin" />
          </div>
        ) : error ? (
          <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-6 text-center">
            <p className="text-red-400">{error}</p>
          </div>
        ) : !release ? (
          <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-8 text-center">
            <div className="text-6xl mb-4">🚧</div>
            <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-4">
              Coming Soon
            </h2>
            <p className="text-[var(--text-secondary)] max-w-md mx-auto">
              The desktop app is currently in development. Check back soon for downloadable releases,
              or star our GitHub repository to get notified.
            </p>
            <a
              href="https://github.com/francisbrero/photo-scoring"
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 mt-6 px-6 py-3 bg-[var(--bg-tertiary)] text-[var(--text-primary)] rounded-lg hover:opacity-80 transition-opacity"
            >
              <svg className="w-5 h-5" viewBox="0 0 24 24" fill="currentColor">
                <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z" />
              </svg>
              View on GitHub
            </a>
          </div>
        ) : (
          <>
            {/* Platform Selector */}
            <div className="flex justify-center gap-4 mb-8">
              {(Object.keys(PLATFORM_INFO) as Platform[]).map((platform) => (
                <button
                  key={platform}
                  onClick={() => setSelectedPlatform(platform)}
                  className={`flex flex-col items-center gap-2 px-6 py-4 rounded-xl transition-all ${
                    selectedPlatform === platform
                      ? 'bg-[#e94560] text-white'
                      : 'bg-[var(--bg-secondary)] text-[var(--text-secondary)] hover:bg-[var(--bg-tertiary)]'
                  }`}
                >
                  {PLATFORM_INFO[platform].icon}
                  <span className="font-medium">{PLATFORM_INFO[platform].name}</span>
                </button>
              ))}
            </div>

            {/* Primary Download */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-8 mb-8">
              <div className="flex flex-col sm:flex-row items-center gap-6">
                <div className="flex-1 text-center sm:text-left">
                  <h2 className="text-2xl font-bold text-[var(--text-primary)] mb-2">
                    Photo Scorer for {PLATFORM_INFO[selectedPlatform].name}
                  </h2>
                  <p className="text-[var(--text-secondary)] mb-4">
                    Version {release.tag_name.replace('v', '')} &bull; Released {formatDate(release.published_at)}
                  </p>
                  {primaryAsset ? (
                    <a
                      href={primaryAsset.browser_download_url}
                      className="inline-flex items-center gap-2 px-8 py-4 bg-[#e94560] text-white rounded-lg text-lg font-semibold hover:bg-[#c73e54] transition-colors"
                    >
                      <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
                      </svg>
                      Download ({formatBytes(primaryAsset.size)})
                    </a>
                  ) : (
                    <p className="text-[var(--text-muted)]">
                      No download available for {PLATFORM_INFO[selectedPlatform].name} yet.
                    </p>
                  )}
                </div>
                <div className="text-[var(--text-muted)]">
                  {PLATFORM_INFO[selectedPlatform].icon}
                </div>
              </div>
            </div>

            {/* All Downloads */}
            <div className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-6">
              <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">All Downloads</h3>
              <div className="space-y-3">
                {release.assets.map((asset) => (
                  <a
                    key={asset.name}
                    href={asset.browser_download_url}
                    className="flex items-center justify-between p-4 bg-[var(--bg-primary)] rounded-lg hover:bg-[var(--bg-tertiary)] transition-colors"
                  >
                    <div className="flex items-center gap-3">
                      <svg className="w-5 h-5 text-[var(--text-muted)]" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                      </svg>
                      <span className="text-[var(--text-primary)] font-medium">{asset.name}</span>
                    </div>
                    <span className="text-[var(--text-muted)] text-sm">{formatBytes(asset.size)}</span>
                  </a>
                ))}
              </div>
            </div>

            {/* Release Notes */}
            {release.body && (
              <div className="mt-8 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-6">
                <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">Release Notes</h3>
                <div className="prose prose-invert max-w-none text-[var(--text-secondary)]">
                  <pre className="whitespace-pre-wrap font-sans text-sm">{release.body}</pre>
                </div>
              </div>
            )}
          </>
        )}

        {/* Features */}
        <div className="mt-12 grid sm:grid-cols-3 gap-6">
          {[
            {
              icon: '🔒',
              title: 'Privacy First',
              description: 'All scoring happens locally. Your photos never leave your computer.',
            },
            {
              icon: '⚡',
              title: 'Lightning Fast',
              description: 'Score hundreds of photos in minutes with GPU acceleration.',
            },
            {
              icon: '🌐',
              title: 'Works Offline',
              description: 'No internet required after installation. Score anywhere.',
            },
          ].map((feature) => (
            <div
              key={feature.title}
              className="bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-6 text-center"
            >
              <div className="text-4xl mb-4">{feature.icon}</div>
              <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-2">{feature.title}</h3>
              <p className="text-[var(--text-secondary)] text-sm">{feature.description}</p>
            </div>
          ))}
        </div>

        {/* System Requirements */}
        <div className="mt-12 bg-[var(--bg-secondary)] rounded-xl border border-[var(--border-color)] p-6">
          <h3 className="text-lg font-semibold text-[var(--text-primary)] mb-4">System Requirements</h3>
          <div className="grid sm:grid-cols-3 gap-6">
            <div>
              <h4 className="font-medium text-[var(--text-primary)] mb-2 flex items-center gap-2">
                {PLATFORM_INFO.mac.icon}
                <span>macOS</span>
              </h4>
              <ul className="text-sm text-[var(--text-secondary)] space-y-1">
                <li>macOS 11 Big Sur or later</li>
                <li>Apple Silicon or Intel processor</li>
                <li>4 GB RAM minimum</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-[var(--text-primary)] mb-2 flex items-center gap-2">
                {PLATFORM_INFO.windows.icon}
                <span>Windows</span>
              </h4>
              <ul className="text-sm text-[var(--text-secondary)] space-y-1">
                <li>Windows 10 or later</li>
                <li>64-bit processor</li>
                <li>4 GB RAM minimum</li>
              </ul>
            </div>
            <div>
              <h4 className="font-medium text-[var(--text-primary)] mb-2 flex items-center gap-2">
                {PLATFORM_INFO.linux.icon}
                <span>Linux</span>
              </h4>
              <ul className="text-sm text-[var(--text-secondary)] space-y-1">
                <li>Ubuntu 20.04 or equivalent</li>
                <li>64-bit processor</li>
                <li>4 GB RAM minimum</li>
              </ul>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
