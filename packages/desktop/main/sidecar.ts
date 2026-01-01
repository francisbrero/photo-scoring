import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as net from 'net';
import { app } from 'electron';

export class SidecarManager {
  private process: ChildProcess | null = null;
  private port: number | null = null;
  private readonly healthCheckInterval = 5000;
  private healthCheckTimer: NodeJS.Timeout | null = null;

  async start(): Promise<number> {
    this.port = await this.findAvailablePort();

    const sidecarPath = this.getSidecarPath();
    const pythonPath = this.getPythonPath();

    console.log(`Starting sidecar: ${pythonPath} ${sidecarPath} on port ${this.port}`);

    this.process = spawn(pythonPath, ['-m', 'uvicorn', 'server:app', '--port', String(this.port), '--host', '127.0.0.1'], {
      cwd: sidecarPath,
      env: {
        ...process.env,
        PYTHONUNBUFFERED: '1',
      },
      stdio: ['ignore', 'pipe', 'pipe'],
    });

    this.process.stdout?.on('data', (data) => {
      console.log(`[sidecar] ${data.toString().trim()}`);
    });

    this.process.stderr?.on('data', (data) => {
      console.error(`[sidecar] ${data.toString().trim()}`);
    });

    this.process.on('exit', (code) => {
      console.log(`Sidecar process exited with code ${code}`);
      this.process = null;
    });

    await this.waitForHealth();
    this.startHealthCheck();

    return this.port;
  }

  async stop(): Promise<void> {
    if (this.healthCheckTimer) {
      clearInterval(this.healthCheckTimer);
      this.healthCheckTimer = null;
    }

    if (this.process) {
      this.process.kill('SIGTERM');

      await new Promise<void>((resolve) => {
        const timeout = setTimeout(() => {
          if (this.process) {
            this.process.kill('SIGKILL');
          }
          resolve();
        }, 5000);

        this.process?.on('exit', () => {
          clearTimeout(timeout);
          resolve();
        });
      });

      this.process = null;
    }
  }

  getPort(): number | null {
    return this.port;
  }

  isRunning(): boolean {
    return this.process !== null && !this.process.killed;
  }

  private getSidecarPath(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'sidecar');
    }
    return path.join(__dirname, '../../sidecar');
  }

  private getPythonPath(): string {
    if (app.isPackaged) {
      if (process.platform === 'win32') {
        return path.join(process.resourcesPath, 'sidecar', 'python', 'python.exe');
      }
      return path.join(process.resourcesPath, 'sidecar', 'python', 'bin', 'python');
    }
    return 'python';
  }

  private async findAvailablePort(): Promise<number> {
    return new Promise((resolve, reject) => {
      const server = net.createServer();
      server.unref();
      server.on('error', reject);
      server.listen(0, '127.0.0.1', () => {
        const address = server.address();
        if (address && typeof address === 'object') {
          const port = address.port;
          server.close(() => resolve(port));
        } else {
          reject(new Error('Failed to get port'));
        }
      });
    });
  }

  private async waitForHealth(maxAttempts = 30, intervalMs = 500): Promise<void> {
    for (let i = 0; i < maxAttempts; i++) {
      try {
        const response = await fetch(`http://127.0.0.1:${this.port}/health`);
        if (response.ok) {
          console.log('Sidecar health check passed');
          return;
        }
      } catch {
        // Sidecar not ready yet
      }
      await new Promise((resolve) => setTimeout(resolve, intervalMs));
    }
    throw new Error('Sidecar failed to start within timeout');
  }

  private startHealthCheck(): void {
    this.healthCheckTimer = setInterval(async () => {
      if (!this.isRunning()) {
        console.log('Sidecar died, attempting restart...');
        try {
          await this.start();
        } catch (error) {
          console.error('Failed to restart sidecar:', error);
        }
      }
    }, this.healthCheckInterval);
  }
}
