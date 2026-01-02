/**
 * @type {import('electron-builder').Configuration}
 */
module.exports = {
  appId: 'com.photoscoring.desktop',
  productName: 'Photo Scoring',
  directories: {
    output: 'release',
    buildResources: 'resources',
  },
  files: [
    'dist/**/*',
    'package.json',
  ],
  extraResources: [
    {
      from: 'sidecar-dist/',
      to: 'sidecar',
      filter: ['**/*'],
    },
  ],
  mac: {
    target: [
      {
        target: 'dmg',
        arch: ['universal'],
      },
    ],
    category: 'public.app-category.photography',
    icon: 'resources/icon.icns',
    hardenedRuntime: true,
    gatekeeperAssess: false,
  },
  win: {
    target: [
      {
        target: 'nsis',
        arch: ['x64'],
      },
    ],
    icon: 'resources/icon.ico',
  },
  nsis: {
    oneClick: false,
    allowToChangeInstallationDirectory: true,
    installerIcon: 'resources/icon.ico',
    uninstallerIcon: 'resources/icon.ico',
  },
  linux: {
    target: [
      {
        target: 'AppImage',
        arch: ['x64'],
      },
    ],
    category: 'Graphics',
    icon: 'resources/icons',
  },
};
