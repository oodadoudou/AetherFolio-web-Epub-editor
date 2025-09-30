// Custom hook for EPUB editor functionality

import { useState, useCallback, useEffect, useRef } from 'react';
import { useAppStore } from '../store';
import { EpubService } from '../services/epub';
import { FilesService } from '../services/files';
import type { EpubMetadata, FileNode } from '../types';
import { FileType } from '../types/api';

export interface EpubEditorState {
  isLoading: boolean;
  error: string | null;
  hasUnsavedChanges: boolean;
  lastSaved: Date | null;
}

export interface UseEpubEditorReturn {
  state: EpubEditorState;
  actions: {
    loadEpub: (file: File) => Promise<void>;
    saveEpub: () => Promise<void>;
    exportEpub: () => Promise<void>;
    createNewEpub: () => Promise<void>;
    updateMetadata: (metadata: Partial<EpubMetadata>) => Promise<void>;
    saveFile: (filePath: string, content: string) => Promise<void>;
    autoSave: () => Promise<void>;
    markAsChanged: () => void;
    markAsSaved: () => void;
  };
}

/**
 * Custom hook for managing EPUB editor functionality
 * @returns EPUB editor state and actions
 */
export function useEpubEditor(): UseEpubEditorReturn {
  const [state, setState] = useState<EpubEditorState>({
    isLoading: false,
    error: null,
    hasUnsavedChanges: false,
    lastSaved: null,
  });

  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  // 使用导入的服务实例
  // const epubService = useRef(new EpubService());
  // const filesService = useRef(new FilesService());

  // Get store actions
  const {
    setMetadata,
    setFileTree,
    setLoading: setFilesLoading,
    metadata,
    fileTree,
  } = useAppStore();

  // Update loading state
  const setLoading = useCallback((loading: boolean) => {
    setState(prev => ({ ...prev, isLoading: loading }));
    setFilesLoading(loading);
  }, [setFilesLoading]);

  // Update error state
  const setError = useCallback((error: string | null) => {
    setState(prev => ({ ...prev, error }));
  }, []);

  // Mark as changed
  const markAsChanged = useCallback(() => {
    setState(prev => ({ ...prev, hasUnsavedChanges: true }));
    
    // Schedule auto-save
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
    }
    autoSaveTimeoutRef.current = setTimeout(() => {
      autoSave();
    }, 30000); // Auto-save after 30 seconds
  }, []);

  // Mark as saved
  const markAsSaved = useCallback(() => {
    setState(prev => ({
      ...prev,
      hasUnsavedChanges: false,
      lastSaved: new Date(),
    }));
    
    if (autoSaveTimeoutRef.current) {
      clearTimeout(autoSaveTimeoutRef.current);
      autoSaveTimeoutRef.current = null;
    }
  }, []);

  // Load EPUB file
  const loadEpub = useCallback(async (file: File) => {
    try {
      setLoading(true);
      setError(null);

      // TODO: Implement actual EPUB loading
      // const result = await epubService.current.uploadEpub(file);
      // setMetadata(result.metadata);
      // setFileTree(result.fileTree);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const mockMetadata: EpubMetadata = {
        title: 'Sample EPUB',
        author: 'Unknown Author',
        language: 'en',
        identifier: 'sample-epub-id',
        publisher: '',
        description: '',
        subject: [],
        contributor: [],
        date: new Date().toISOString(),
        rights: '',
      };
      
      const mockFileTree: FileNode[] = [{
        name: 'EPUB Root',
        type: FileType.DIRECTORY,
        path: '/',
        children: [
          {
            name: 'META-INF',
            type: FileType.DIRECTORY,
            path: '/META-INF',
            children: [],
          },
          {
            name: 'OEBPS',
            type: FileType.DIRECTORY,
            path: '/OEBPS',
            children: [],
          },
        ],
      }];
      
      setMetadata(mockMetadata);
      setFileTree(mockFileTree as any);
      markAsSaved();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to load EPUB';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setMetadata, setFileTree, markAsSaved]);

  // Save EPUB
  const saveEpub = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // TODO: Implement actual EPUB saving
      // await epubService.current.updateMetadata(metadata);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      markAsSaved();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save EPUB';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, markAsSaved, metadata]);

  // Export EPUB
  const exportEpub = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // TODO: Implement actual EPUB export
      // const blob = await epubService.current.exportEpub();
      // downloadFile(blob, `${metadata?.title || 'epub'}.epub`, 'application/epub+zip');
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 2000));
      
      console.log('EPUB exported successfully');
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to export EPUB';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, metadata]);

  // Create new EPUB
  const createNewEpub = useCallback(async () => {
    try {
      setLoading(true);
      setError(null);

      // TODO: Implement new EPUB creation
      // const result = await epubService.current.createNew();
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const newMetadata: EpubMetadata = {
        title: 'New EPUB',
        author: '',
        language: 'en',
        identifier: `epub-${Date.now()}`,
        publisher: '',
        description: '',
        subject: [],
        contributor: [],
        date: new Date().toISOString(),
        rights: '',
      };
      
      const newFileTree: FileNode[] = [{
        name: 'New EPUB',
        type: FileType.DIRECTORY,
        path: '/',
        children: [],
      }];
      
      setMetadata(newMetadata);
      setFileTree(newFileTree as any);
      markAsSaved();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to create new EPUB';
      setError(errorMessage);
    } finally {
      setLoading(false);
    }
  }, [setLoading, setError, setMetadata, setFileTree, markAsSaved]);

  // Update metadata
  const updateMetadata = useCallback(async (updates: Partial<EpubMetadata>) => {
    try {
      if (!metadata) return;
      
      const updatedMetadata = { ...metadata, ...updates };
      setMetadata(updatedMetadata);
      markAsChanged();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to update metadata';
      setError(errorMessage);
    }
  }, [metadata, setMetadata, markAsChanged, setError]);

  // Save individual file
  const saveFile = useCallback(async (filePath: string, content: string) => {
    try {
      // TODO: Implement actual file saving
      // await filesService.current.updateFileContent(filePath, content);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 200));
      
      markAsChanged();
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Failed to save file';
      setError(errorMessage);
    }
  }, [markAsChanged, setError]);

  // Auto-save
  const autoSave = useCallback(async () => {
    if (!state.hasUnsavedChanges) return;
    
    try {
      // TODO: Implement auto-save logic
      // await epubService.current.autoSave();
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 500));
      
      markAsSaved();
    } catch (error) {
      console.warn('Auto-save failed:', error);
      // Don't show error for auto-save failures
    }
  }, [state.hasUnsavedChanges, markAsSaved]);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, []);

  // Handle beforeunload event for unsaved changes
  useEffect(() => {
    const handleBeforeUnload = (e: BeforeUnloadEvent) => {
      if (state.hasUnsavedChanges) {
        e.preventDefault();
        e.returnValue = 'You have unsaved changes. Are you sure you want to leave?';
        return e.returnValue;
      }
    };

    window.addEventListener('beforeunload', handleBeforeUnload);
    return () => window.removeEventListener('beforeunload', handleBeforeUnload);
  }, [state.hasUnsavedChanges]);

  return {
    state,
    actions: {
      loadEpub,
      saveEpub,
      exportEpub,
      createNewEpub,
      updateMetadata,
      saveFile,
      autoSave,
      markAsChanged,
      markAsSaved,
    },
  };
}