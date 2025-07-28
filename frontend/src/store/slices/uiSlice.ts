// UI state slice
// Manages UI-related state (modals, panels, theme, etc.)

import { StateCreator } from 'zustand';
import type { Theme } from '../../types';

export interface UiState {
  theme: Theme;
  sidebarCollapsed: boolean;
  searchPanelVisible: boolean;
  previewPanelVisible: boolean;
  uploadModalVisible: boolean;
  batchReplaceModalVisible: boolean;
  searchReplaceModalVisible: boolean;
  isFullscreen: boolean;
}

export interface UiActions {
  setTheme: (theme: Theme) => void;
  toggleTheme: () => void;
  setSidebarCollapsed: (collapsed: boolean) => void;
  toggleSidebar: () => void;
  setSearchPanelVisible: (visible: boolean) => void;
  toggleSearchPanel: () => void;
  setPreviewPanelVisible: (visible: boolean) => void;
  togglePreviewPanel: () => void;
  setUploadModalVisible: (visible: boolean) => void;
  setBatchReplaceModalVisible: (visible: boolean) => void;
  setSearchReplaceModalVisible: (visible: boolean) => void;
  setFullscreen: (fullscreen: boolean) => void;
  toggleFullscreen: () => void;
}

export type UiSlice = UiState & UiActions;

export const createUiSlice: StateCreator<UiSlice> = (set, get) => ({
  // State
  theme: 'auto',
  sidebarCollapsed: false,
  searchPanelVisible: false,
  previewPanelVisible: true,
  uploadModalVisible: false,
  batchReplaceModalVisible: false,
  searchReplaceModalVisible: false,
  isFullscreen: false,

  // Actions
  setTheme: (theme: Theme) => set({ theme }),
  toggleTheme: () => {
    const currentTheme = get().theme;
    // If auto, toggle to light/dark based on system preference
    if (currentTheme === 'auto') {
      const systemDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
      set({ theme: systemDark ? 'light' : 'dark' });
    } else {
      set({ theme: currentTheme === 'light' ? 'dark' : 'light' });
    }
  },
  setSidebarCollapsed: (collapsed: boolean) => set({ sidebarCollapsed: collapsed }),
  toggleSidebar: () => {
    const { sidebarCollapsed } = get();
    set({ sidebarCollapsed: !sidebarCollapsed });
  },
  setSearchPanelVisible: (visible: boolean) => set({ searchPanelVisible: visible }),
  toggleSearchPanel: () => {
    const { searchPanelVisible } = get();
    set({ searchPanelVisible: !searchPanelVisible });
  },
  setPreviewPanelVisible: (visible: boolean) => set({ previewPanelVisible: visible }),
  togglePreviewPanel: () => {
    const { previewPanelVisible } = get();
    set({ previewPanelVisible: !previewPanelVisible });
  },
  setUploadModalVisible: (visible: boolean) => set({ uploadModalVisible: visible }),
  setBatchReplaceModalVisible: (visible: boolean) => set({ batchReplaceModalVisible: visible }),
  setSearchReplaceModalVisible: (visible: boolean) => set({ searchReplaceModalVisible: visible }),
  setFullscreen: (fullscreen: boolean) => set({ isFullscreen: fullscreen }),
  toggleFullscreen: () => {
    const { isFullscreen } = get();
    set({ isFullscreen: !isFullscreen });
  },
});