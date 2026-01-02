import { spawn, ChildProcess } from 'child_process';
import * as path from 'path';
import * as net from 'net';
import * as fs from 'fs';
import { app } from 'electron';

export class SidecarManager {
  private process: ChildProcess | null = null;
  private port: number | null = null;
  private readonly healthCheckInterval = 5000;
  private healthCheckTimer: NodeJS.Timeout | null = null;
  private isExternalSidecar = false;

  async start(): Promise<number> {
    // In development, check if an external sidecar is already running on port 9000
    if (!app.isPackaged) {
      const externalPort = 9000;
      if (await this.checkExternalSidecar(externalPort)) {
        console.log(`Using external sidecar on port ${externalPort}`);
        this.port = externalPort;
        this.isExternalSidecar = true;
        return this.port;
      }
    }

    this.port = await this.findAvailablePort();

    console.log(`Starting sidecar on port ${this.port}`);
    console.log(`app.isPackaged: ${app.isPackaged}`);
    console.log(`process.resourcesPath: ${process.resourcesPath}`);

    let command: string;
    let args: string[];
    let cwd: string;

    // Check if PyInstaller sidecar executable exists (works for both packaged and local testing)
    const sidecarExecutable = this.getSidecarExecutable();
    const sidecarExists = fs.existsSync(sidecarExecutable);
    console.log(`Sidecar executable path: ${sidecarExecutable}`);
    console.log(`Sidecar executable exists: ${sidecarExists}`);

    if (sidecarExists) {
      // PyInstaller bundle - run the sidecar executable directly
      command = sidecarExecutable;
      args = ['--port', String(this.port), '--host', '127.0.0.1'];
      cwd = path.dirname(sidecarExecutable);
      console.log(`Running packaged sidecar: ${command}`);
    } else if (!app.isPackaged) {
      // Development mode - use uv run
      const sidecarPath = this.getSidecarPath();
      command = 'uv';
      args = ['run', 'uvicorn', 'server:app', '--port', String(this.port), '--host', '127.0.0.1'];
      cwd = sidecarPath;
      console.log(`Running dev sidecar: ${command} ${args.join(' ')} in ${cwd}`);
    } else {
      // Packaged but sidecar not found - this is an error
      const sidecarDir = path.join(process.resourcesPath, 'sidecar');
      let dirContents = 'directory does not exist';
      if (fs.existsSync(sidecarDir)) {
        dirContents = fs.readdirSync(sidecarDir).join(', ');
      }
      throw new Error(
        `Sidecar executable not found at ${sidecarExecutable}. ` +
        `Contents of sidecar dir: ${dirContents}`
      );
    }

    this.process = spawn(command, args, {
      cwd,
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

  private async checkExternalSidecar(port: number): Promise<boolean> {
    try {
      const response = await fetch(`http://127.0.0.1:${port}/health`);
      return response.ok;
    } catch {
      return false;
    }
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
    return this.isExternalSidecar || (this.process !== null && !this.process.killed);
  }

  private getSidecarPath(): string {
    if (app.isPackaged) {
      return path.join(process.resourcesPath, 'sidecar');
    }
    return path.join(__dirname, '../../sidecar');
  }

  private getSidecarExecutable(): string {
    const sidecarDir = path.join(process.resourcesPath, 'sidecar');
    if (process.platform === 'win32') {
      return path.join(sidecarDir, 'sidecar.exe');
    }
    return path.join(sidecarDir, 'sidecar');
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
