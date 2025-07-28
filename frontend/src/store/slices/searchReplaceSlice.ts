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
  addReplaceRule: (rule: Omit<ReplaceRule, 'id'>) => void;
  updateReplaceRule: (id: string, updates: Partial<ReplaceRule>) => void;
  removeReplaceRule: (id: string) => void;
  clearReplaceRules: () => void;
  setBatchProgress: (progress: { current: number; total: number } | null) => void;
  clearSearch: () => void;
}

export type SearchReplaceSlice = SearchReplaceState & SearchReplaceActions;

const defaultSearchOptions: SearchOptions = {
  caseSensitive: false,
  wholeWord: false,
  regex: false,
  fileTypes: [],
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
  addReplaceRule: (rule: Omit<ReplaceRule, 'id'>) => {
    const newRule: ReplaceRule = {
      ...rule,
      id: Date.now().toString() + Math.random().toString(36).substr(2, 9),
    };
    const { replaceRules } = get();
    set({ replaceRules: [...replaceRules, newRule] });
  },
  updateReplaceRule: (id: string, updates: Partial<ReplaceRule>) => {
    const { replaceRules } = get();
    const updatedRules = replaceRules.map(rule => 
      rule.id === id ? { ...rule, ...updates } : rule
    );
    set({ replaceRules: updatedRules });
  },
  removeReplaceRule: (id: string) => {
    const { replaceRules } = get();
    set({ replaceRules: replaceRules.filter(rule => rule.id !== id) });
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