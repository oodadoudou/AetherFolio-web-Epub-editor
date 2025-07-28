// Main Zustand store combining all slices

import { create } from 'zustand';
import { devtools } from 'zustand/middleware';
import {
  createSessionSlice,
  createFilesSlice,
  createMetadataSlice,
  createUiSlice,
  createSearchReplaceSlice,
  type SessionSlice,
  type FilesSlice,
  type MetadataSlice,
  type UiSlice,
  type SearchReplaceSlice,
} from './slices';

// Combined store type
export type AppStore = SessionSlice & FilesSlice & MetadataSlice & UiSlice & SearchReplaceSlice;

// Create the main store
export const useAppStore = create<AppStore>()((
  devtools(
    (...a) => ({
      ...createSessionSlice(...a),
      ...createFilesSlice(...a),
      ...createMetadataSlice(...a),
      ...createUiSlice(...a),
      ...createSearchReplaceSlice(...a),
    }),
    {
      name: 'aether-folio-store',
    }
  )
));

// Export individual slice selectors for better performance
export const useSessionStore = () => useAppStore((state) => ({
  sessionId: state.sessionId,
  isConnected: state.isConnected,
  lastActivity: state.lastActivity,
  setSessionId: state.setSessionId,
  setConnected: state.setConnected,
  updateLastActivity: state.updateLastActivity,
  clearSession: state.clearSession,
}));

export const useFilesStore = () => useAppStore((state) => ({
  fileTree: state.fileTree,
  selectedFile: state.selectedFile,
  openFiles: state.openFiles,
  activeFile: state.activeFile,
  isLoading: state.isLoading,
  setFileTree: state.setFileTree,
  setSelectedFile: state.setSelectedFile,
  addOpenFile: state.addOpenFile,
  removeOpenFile: state.removeOpenFile,
  setActiveFile: state.setActiveFile,
  setLoading: state.setLoading,
  updateFileNode: state.updateFileNode,
  removeFileNode: state.removeFileNode,
}));

export const useMetadataStore = () => useAppStore((state) => ({
  metadata: state.metadata,
  isDirty: state.isDirty,
  isLoading: state.isLoading,
  setMetadata: state.setMetadata,
  updateMetadata: state.updateMetadata,
  resetMetadata: state.resetMetadata,
  setDirty: state.setDirty,
  setLoading: state.setLoading,
}));

export const useUiStore = () => useAppStore((state) => ({
  theme: state.theme,
  sidebarCollapsed: state.sidebarCollapsed,
  searchPanelVisible: state.searchPanelVisible,
  previewPanelVisible: state.previewPanelVisible,
  uploadModalVisible: state.uploadModalVisible,
  batchReplaceModalVisible: state.batchReplaceModalVisible,
  searchReplaceModalVisible: state.searchReplaceModalVisible,
  isFullscreen: state.isFullscreen,
  setTheme: state.setTheme,
  toggleTheme: state.toggleTheme,
  setSidebarCollapsed: state.setSidebarCollapsed,
  toggleSidebar: state.toggleSidebar,
  setSearchPanelVisible: state.setSearchPanelVisible,
  toggleSearchPanel: state.toggleSearchPanel,
  setPreviewPanelVisible: state.setPreviewPanelVisible,
  togglePreviewPanel: state.togglePreviewPanel,
  setUploadModalVisible: state.setUploadModalVisible,
  setBatchReplaceModalVisible: state.setBatchReplaceModalVisible,
  setSearchReplaceModalVisible: state.setSearchReplaceModalVisible,
  setFullscreen: state.setFullscreen,
  toggleFullscreen: state.toggleFullscreen,
}));

export const useSearchReplaceStore = () => useAppStore((state) => ({
  searchQuery: state.searchQuery,
  replaceQuery: state.replaceQuery,
  searchOptions: state.searchOptions,
  searchResults: state.searchResults,
  currentResultIndex: state.currentResultIndex,
  isSearching: state.isSearching,
  isReplacing: state.isReplacing,
  replaceRules: state.replaceRules,
  batchProgress: state.batchProgress,
  setSearchQuery: state.setSearchQuery,
  setReplaceQuery: state.setReplaceQuery,
  setSearchOptions: state.setSearchOptions,
  setSearchResults: state.setSearchResults,
  setCurrentResultIndex: state.setCurrentResultIndex,
  setSearching: state.setSearching,
  setReplacing: state.setReplacing,
  addReplaceRule: state.addReplaceRule,
  updateReplaceRule: state.updateReplaceRule,
  removeReplaceRule: state.removeReplaceRule,
  clearReplaceRules: state.clearReplaceRules,
  setBatchProgress: state.setBatchProgress,
  clearSearch: state.clearSearch,
}));

// Export store types
export type {
  SessionSlice,
  FilesSlice,
  MetadataSlice,
  UiSlice,
  SearchReplaceSlice,
};