// Search Replace state slice
// Manages search and replace operations state

import { StateCreator } from 'zustand';
import type { SearchOptions, SearchResult, ReplaceRule } from '../../types';

// Re-export types from the main types module
export type { SearchOptions, SearchResult, ReplaceRule } from '../../types';

export interface SearchReplaceState {
  searchQuery: string;
  replaceQuery: string;
  searchOptions: SearchOptions;
  searchResults: SearchResult[];
  currentResultIndex: number;
  isSearching: boolean;
  isReplacing: boolean;
  replaceRules: ReplaceRule[];
  batchProgress: { current: number; total: number } | null;
}

export interface SearchReplaceActions {
  setSearchQuery: (query: string) => void;
  setReplaceQuery: (query: string) => void;
  setSearchOptions: (options: Partial<SearchOptions>) => void;
  setSearchResults: (results: SearchResult[]) => void;
  setCurrentResultIndex: (index: number) => void;
  setSearching: (searching: boolean) => void;
  setReplacing: (replacing: boolean) => void;
  addReplaceRule: (rule: ReplaceRule) => void;
  updateReplaceRule: (index: number, updates: Partial<ReplaceRule>) => void;
  removeReplaceRule: (index: number) => void;
  clearReplaceRules: () => void;
  setBatchProgress: (progress: { current: number; total: number } | null) => void;
  clearSearch: () => void;
}

export type SearchReplaceSlice = SearchReplaceState & SearchReplaceActions;

const defaultSearchOptions: SearchOptions = {
  case_sensitive: false,
  whole_word: false,
  regex: false,
  file_types: [],
};

export const createSearchReplaceSlice: StateCreator<SearchReplaceSlice> = (set, get) => ({
  // State
  searchQuery: '',
  replaceQuery: '',
  searchOptions: { ...defaultSearchOptions },
  searchResults: [],
  currentResultIndex: -1,
  isSearching: false,
  isReplacing: false,
  replaceRules: [],
  batchProgress: null,

  // Actions
  setSearchQuery: (query: string) => set({ searchQuery: query }),
  setReplaceQuery: (query: string) => set({ replaceQuery: query }),
  setSearchOptions: (options: Partial<SearchOptions>) => {
    const currentOptions = get().searchOptions;
    set({ searchOptions: { ...currentOptions, ...options } });
  },
  setSearchResults: (results: SearchResult[]) => set({ 
    searchResults: results,
    currentResultIndex: results.length > 0 ? 0 : -1 
  }),
  setCurrentResultIndex: (index: number) => set({ currentResultIndex: index }),
  setSearching: (searching: boolean) => set({ isSearching: searching }),
  setReplacing: (replacing: boolean) => set({ isReplacing: replacing }),
  addReplaceRule: (rule: ReplaceRule) => {
    const { replaceRules } = get();
    set({ replaceRules: [...replaceRules, rule] });
  },
  updateReplaceRule: (index: number, updates: Partial<ReplaceRule>) => {
    const { replaceRules } = get();
    const updatedRules = replaceRules.map((rule, i) => 
      i === index ? { ...rule, ...updates } : rule
    );
    set({ replaceRules: updatedRules });
  },
  removeReplaceRule: (index: number) => {
    const { replaceRules } = get();
    set({ replaceRules: replaceRules.filter((_, i) => i !== index) });
  },
  clearReplaceRules: () => set({ replaceRules: [] }),
  setBatchProgress: (progress: { current: number; total: number } | null) => set({ batchProgress: progress }),
  clearSearch: () => set({ 
    searchQuery: '',
    replaceQuery: '',
    searchResults: [],
    currentResultIndex: -1,
    batchProgress: null 
  }),
});