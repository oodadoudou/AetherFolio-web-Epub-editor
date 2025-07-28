// Files state slice
// Manages file tree and file operations state

import { StateCreator } from 'zustand';

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: Date;
  children?: FileNode[];
  isExpanded?: boolean;
}

export interface FilesState {
  fileTree: FileNode[];
  selectedFile: string | null;
  openFiles: string[];
  activeFile: string | null;
  isLoading: boolean;
}

export interface FilesActions {
  setFileTree: (tree: FileNode[]) => void;
  setSelectedFile: (path: string | null) => void;
  addOpenFile: (path: string) => void;
  removeOpenFile: (path: string) => void;
  setActiveFile: (path: string | null) => void;
  setLoading: (loading: boolean) => void;
  updateFileNode: (path: string, updates: Partial<FileNode>) => void;
  removeFileNode: (path: string) => void;
}

export type FilesSlice = FilesState & FilesActions;

export const createFilesSlice: StateCreator<FilesSlice> = (set, get) => ({
  // State
  fileTree: [],
  selectedFile: null,
  openFiles: [],
  activeFile: null,
  isLoading: false,

  // Actions
  setFileTree: (tree: FileNode[]) => set({ fileTree: tree }),
  setSelectedFile: (path: string | null) => set({ selectedFile: path }),
  addOpenFile: (path: string) => {
    const { openFiles } = get();
    if (!openFiles.includes(path)) {
      set({ openFiles: [...openFiles, path] });
    }
  },
  removeOpenFile: (path: string) => {
    const { openFiles, activeFile } = get();
    const newOpenFiles = openFiles.filter(f => f !== path);
    const newActiveFile = activeFile === path ? (newOpenFiles[0] || null) : activeFile;
    set({ openFiles: newOpenFiles, activeFile: newActiveFile });
  },
  setActiveFile: (path: string | null) => set({ activeFile: path }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),
  updateFileNode: (path: string, updates: Partial<FileNode>) => {
    // TODO: Implement deep update logic for file tree
    console.log('updateFileNode:', path, updates);
  },
  removeFileNode: (path: string) => {
    // TODO: Implement file node removal logic
    console.log('removeFileNode:', path);
  },
});