// Metadata state slice
// Manages EPUB metadata state

import { StateCreator } from 'zustand';

export interface EpubMetadata {
  title: string;
  author: string;
  language: string;
  identifier?: string;
  publisher?: string;
  date?: string;
  description?: string;
  cover?: string;
}

export interface MetadataState {
  metadata: EpubMetadata;
  isDirty: boolean;
  isLoading: boolean;
}

export interface MetadataActions {
  setMetadata: (metadata: Partial<EpubMetadata>) => void;
  updateMetadata: (field: keyof EpubMetadata, value: string) => void;
  resetMetadata: () => void;
  setDirty: (dirty: boolean) => void;
  setLoading: (loading: boolean) => void;
}

export type MetadataSlice = MetadataState & MetadataActions;

const defaultMetadata: EpubMetadata = {
  title: '',
  author: '',
  language: 'en',
  identifier: '',
  publisher: '',
  date: '',
  description: '',
  cover: '',
};

export const createMetadataSlice: StateCreator<MetadataSlice> = (set, get) => ({
  // State
  metadata: { ...defaultMetadata },
  isDirty: false,
  isLoading: false,

  // Actions
  setMetadata: (metadata: Partial<EpubMetadata>) => {
    const currentMetadata = get().metadata;
    set({ 
      metadata: { ...currentMetadata, ...metadata },
      isDirty: true 
    });
  },
  updateMetadata: (field: keyof EpubMetadata, value: string) => {
    const currentMetadata = get().metadata;
    set({ 
      metadata: { ...currentMetadata, [field]: value },
      isDirty: true 
    });
  },
  resetMetadata: () => set({ 
    metadata: { ...defaultMetadata },
    isDirty: false 
  }),
  setDirty: (dirty: boolean) => set({ isDirty: dirty }),
  setLoading: (loading: boolean) => set({ isLoading: loading }),
});