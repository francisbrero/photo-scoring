import { test, expect, _electron as electron, ElectronApplication, Page } from '@playwright/test';
import * as path from 'path';
import * as fs from 'fs';

let electronApp: ElectronApplication;
let window: Page;

// Helper to get the path to the packaged app or dev entry
function getAppPath(): string {
  const platform = process.platform;
  const releaseDir = path.join(__dirname, '..', 'release');

  // Check for packaged app first
  if (platform === 'darwin') {
    const macAppPath = path.join(releaseDir, 'mac-arm64', 'Photo Scorer.app', 'Contents', 'MacOS', 'Photo Scorer');
    if (fs.existsSync(macAppPath)) {
      return macAppPath;
    }
  } else if (platform === 'win32') {
    const winAppPath = path.join(releaseDir, 'win-unpacked', 'Photo Scorer.exe');
    if (fs.existsSync(winAppPath)) {
      return winAppPath;
    }
  } else if (platform === 'linux') {
    const linuxAppPath = path.join(releaseDir, 'linux-unpacked', 'photo-scoring-desktop');
    if (fs.existsSync(linuxAppPath)) {
      return linuxAppPath;
    }
  }

  // Fall back to development mode (requires build first)
  return path.join(__dirname, '..');
}

test.describe('Photo Scorer Desktop App', () => {
  test.beforeAll(async () => {
    const appPath = getAppPath();
    console.log(`Starting app from: ${appPath}`);

    // Check if we're testing a packaged app (executable) or dev mode (directory)
    const isPackaged = !fs.statSync(appPath).isDirectory();

    if (isPackaged) {
      // Launch packaged app
      electronApp = await electron.launch({
        executablePath: appPath,
        args: ['--no-sandbox'], // Required for some CI environments
      });
    } else {
      // Launch in dev mode
      electronApp = await electron.launch({
        args: [appPath],
      });
    }

    // Wait for the first window
    window = await electronApp.firstWindow();

    // Wait for the app to be ready
    await window.waitForLoadState('domcontentloaded');
  });

  test.afterAll(async () => {
    if (electronApp) {
      await electronApp.close();
    }
  });

  test('should launch the app and show main window', async () => {
    const title = await window.title();
    expect(title).toContain('Photo Scorer');
  });

  test('should have sidecar running and healthy', async () => {
    // The app communicates with sidecar - wait for it to be ready
    // We can check by looking for UI elements that only appear when sidecar is connected

    // Wait up to 30 seconds for sidecar to be ready
    await window.waitForTimeout(5000); // Give sidecar time to start

    // Check if we can make a health request through the renderer
    // The app stores sidecar port in window context
    const sidecarHealthy = await window.evaluate(async () => {
      // Try to find the sidecar port from the app's IPC
      const ports = [9000, 9001, 9002, 9003, 9004, 9005];
      for (const port of ports) {
        try {
          const response = await fetch(`http://127.0.0.1:${port}/health`);
          if (response.ok) {
            const data = await response.json();
            return data.status === 'healthy';
          }
        } catch {
          // Try next port
        }
      }
      return false;
    });

    expect(sidecarHealthy).toBe(true);
  });

  test('should show the library view', async () => {
    // Look for library-related elements
    const libraryExists = await window.locator('text=Library').or(window.locator('text=Add Folder')).first().isVisible({ timeout: 10000 }).catch(() => false);
    expect(libraryExists).toBe(true);
  });
});
