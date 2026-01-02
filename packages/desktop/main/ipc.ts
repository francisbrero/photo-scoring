import { ipcMain, dialog, BrowserWindow } from 'electron';
import { SidecarManager } from './sidecar';

export function setupIpcHandlers(sidecarManager: SidecarManager): void {
  // Get sidecar port for renderer to connect directly
  ipcMain.handle('sidecar:getPort', () => {
    return sidecarManager.getPort();
  });

  // Check if sidecar is running
  ipcMain.handle('sidecar:isRunning', () => {
    return sidecarManager.isRunning();
  });

  // Open directory picker dialog
  ipcMain.handle('dialog:openDirectory', async () => {
    const window = BrowserWindow.getFocusedWindow();
    if (!window) return null;

    const result = await dialog.showOpenDialog(window, {
      properties: ['openDirectory'],
      title: 'Select Photo Folder',
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  // Open file picker dialog (for single images)
  ipcMain.handle('dialog:openFile', async (_event, filters?: { name: string; extensions: string[] }[]) => {
    const window = BrowserWindow.getFocusedWindow();
    if (!window) return null;

    const result = await dialog.showOpenDialog(window, {
      properties: ['openFile'],
      title: 'Select Photo',
      filters: filters || [
        { name: 'Images', extensions: ['jpg', 'jpeg', 'png', 'heic', 'heif', 'webp'] },
      ],
    });

    if (result.canceled || result.filePaths.length === 0) {
      return null;
    }

    return result.filePaths[0];
  });

  // Save file dialog
  ipcMain.handle('dialog:saveFile', async (_event, defaultPath?: string, filters?: { name: string; extensions: string[] }[]) => {
    const window = BrowserWindow.getFocusedWindow();
    if (!window) return null;

    const result = await dialog.showSaveDialog(window, {
      title: 'Save File',
      defaultPath,
      filters: filters || [
        { name: 'CSV', extensions: ['csv'] },
        { name: 'JSON', extensions: ['json'] },
      ],
    });

    if (result.canceled || !result.filePath) {
      return null;
    }

    return result.filePath;
  });

  // Show message dialog
  ipcMain.handle('dialog:showMessage', async (_event, options: {
    type?: 'none' | 'info' | 'error' | 'question' | 'warning';
    title?: string;
    message: string;
    detail?: string;
    buttons?: string[];
  }) => {
    const window = BrowserWindow.getFocusedWindow();
    if (!window) return { response: 0 };

    const result = await dialog.showMessageBox(window, {
      type: options.type || 'info',
      title: options.title,
      message: options.message,
      detail: options.detail,
      buttons: options.buttons || ['OK'],
    });

    return { response: result.response };
  });
}
