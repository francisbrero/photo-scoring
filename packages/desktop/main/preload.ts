import { contextBridge, ipcRenderer } from 'electron';

export interface ElectronAPI {
  sidecar: {
    getPort: () => Promise<number | null>;
    isRunning: () => Promise<boolean>;
  };
  dialog: {
    openDirectory: () => Promise<string | null>;
    openFile: (filters?: { name: string; extensions: string[] }[]) => Promise<string | null>;
    saveFile: (defaultPath?: string, filters?: { name: string; extensions: string[] }[]) => Promise<string | null>;
    showMessage: (options: {
      type?: 'none' | 'info' | 'error' | 'question' | 'warning';
      title?: string;
      message: string;
      detail?: string;
      buttons?: string[];
    }) => Promise<{ response: number }>;
  };
  on: (channel: string, callback: (...args: unknown[]) => void) => () => void;
}

const electronAPI: ElectronAPI = {
  sidecar: {
    getPort: () => ipcRenderer.invoke('sidecar:getPort'),
    isRunning: () => ipcRenderer.invoke('sidecar:isRunning'),
  },
  dialog: {
    openDirectory: () => ipcRenderer.invoke('dialog:openDirectory'),
    openFile: (filters) => ipcRenderer.invoke('dialog:openFile', filters),
    saveFile: (defaultPath, filters) => ipcRenderer.invoke('dialog:saveFile', defaultPath, filters),
    showMessage: (options) => ipcRenderer.invoke('dialog:showMessage', options),
  },
  on: (channel: string, callback: (...args: unknown[]) => void) => {
    const subscription = (_event: Electron.IpcRendererEvent, ...args: unknown[]) => callback(...args);
    ipcRenderer.on(channel, subscription);
    return () => {
      ipcRenderer.removeListener(channel, subscription);
    };
  },
};

contextBridge.exposeInMainWorld('electron', electronAPI);
