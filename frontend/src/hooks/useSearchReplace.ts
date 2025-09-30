// Custom hook for search and replace functionality

import { useState, useCallback, useRef, useEffect } from 'react';
import { useAppStore } from '../store';
import { searchReplaceService } from '../services/searchReplace';
import { useDebounce } from './useDebounce';
import type { SearchOptions, SearchResult, ReplaceRule } from '../types';

export interface UseSearchReplaceReturn {
  // Search functionality
  search: (query: string, options?: Partial<SearchOptions>) => Promise<void>;
  clearSearch: () => void;
  navigateToResult: (index: number) => void;
  nextResult: () => void;
  previousResult: () => void;
  
  // Replace functionality
  replace: (index: number, replacement: string) => Promise<void>;
  replaceAll: (replacement: string) => Promise<void>;
  replaceInFile: (filePath: string, replacement: string) => Promise<void>;
  
  // Batch replace functionality
  addReplaceRule: (rule: Omit<ReplaceRule, 'id'>) => void;
  updateReplaceRule: (index: number, updates: Partial<ReplaceRule>) => void;
  removeReplaceRule: (index: number) => void;
  executeBatchReplace: () => Promise<void>;
  
  // State
  isSearching: boolean;
  isReplacing: boolean;
  searchResults: SearchResult[];
  currentResultIndex: number;
  totalResults: number;
  hasResults: boolean;
}

/**
 * Custom hook for search and replace functionality
 * @param autoSearch - Whether to automatically search when query changes
 * @param debounceMs - Debounce delay for auto search
 * @returns Search and replace state and actions
 */
export function useSearchReplace(
  autoSearch: boolean = true,
  debounceMs: number = 300
): UseSearchReplaceReturn {
  const searchService = useRef(searchReplaceService);
  
  // Get store state and actions
  const {
    searchQuery,
    replaceQuery,
    searchOptions,
    searchResults,
    currentResultIndex,
    isSearching,
    isReplacing,
    replaceRules,
    batchProgress,
    setSearchQuery,
    setReplaceQuery,
    setSearchOptions,
    setSearchResults,
    setCurrentResultIndex,
    setSearching,
    setReplacing,
    addReplaceRule: addRule,
    updateReplaceRule: updateRule,
    removeReplaceRule: removeRule,
    clearReplaceRules,
    setBatchProgress,
    clearSearch: clearSearchStore,
  } = useAppStore();

  // Debounced search query for auto search
  const debouncedSearchQuery = useDebounce(searchQuery, debounceMs);

  // Perform search
  const search = useCallback(async (
    query: string,
    options: Partial<SearchOptions> = {}
  ) => {
    if (!query.trim()) {
      clearSearchStore();
      return;
    }

    try {
      setSearching(true);
      setSearchQuery(query);
      
      const searchOpts = { ...searchOptions, ...options };
      setSearchOptions(searchOpts);

      // TODO: Implement actual search
      // const results = await searchService.current.searchInFiles(query, searchOpts);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 500));
      
      const mockResults: SearchResult[] = [
        {
          file_path: 'chapter1.html',
          line_number: 10,
          line_content: 'This is a sample text with search term.',
          match_start: 25,
          match_end: 36,
          match_text: 'search term'
        },
        {
          file_path: 'chapter2.html',
          line_number: 5,
          line_content: 'Another line containing the search term here.',
          match_start: 32,
          match_end: 43,
          match_text: 'search term'
        }
      ];
      
      setSearchResults(mockResults);
      setCurrentResultIndex(mockResults.length > 0 ? 0 : -1);
    } catch (error) {
      console.error('Search failed:', error);
      setSearchResults([]);
      setCurrentResultIndex(-1);
    } finally {
      setSearching(false);
    }
  }, [searchOptions, setSearching, setSearchQuery, setSearchOptions, setSearchResults, setCurrentResultIndex, clearSearchStore]);

  // Clear search
  const clearSearch = useCallback(() => {
    clearSearchStore();
  }, [clearSearchStore]);

  // Navigate to specific result
  const navigateToResult = useCallback((index: number) => {
    if (index >= 0 && index < searchResults.length) {
      setCurrentResultIndex(index);
      
      // TODO: Implement navigation to result in editor
      const result = searchResults[index];
      console.log('Navigate to result:', result);
    }
  }, [searchResults, setCurrentResultIndex]);

  // Navigate to next result
  const nextResult = useCallback(() => {
    if (searchResults.length === 0) return;
    
    const nextIndex = currentResultIndex < searchResults.length - 1 
      ? currentResultIndex + 1 
      : 0;
    navigateToResult(nextIndex);
  }, [searchResults.length, currentResultIndex, navigateToResult]);

  // Navigate to previous result
  const previousResult = useCallback(() => {
    if (searchResults.length === 0) return;
    
    const prevIndex = currentResultIndex > 0 
      ? currentResultIndex - 1 
      : searchResults.length - 1;
    navigateToResult(prevIndex);
  }, [searchResults.length, currentResultIndex, navigateToResult]);

  // Replace single occurrence
  const replace = useCallback(async (index: number, replacement: string) => {
    if (index < 0 || index >= searchResults.length) return;
    
    try {
      setReplacing(true);
      const result = searchResults[index];
      
      // TODO: Implement actual replace
      // await searchService.current.replaceInFile(
      //   result.filePath,
      //   result.startOffset,
      //   result.endOffset,
      //   replacement
      // );
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 200));
      
      // Remove the replaced result from search results
      const updatedResults = searchResults.filter((_, i) => i !== index);
      setSearchResults(updatedResults);
      
      // Adjust current index
      if (updatedResults.length === 0) {
        setCurrentResultIndex(-1);
      } else if (index >= updatedResults.length) {
        setCurrentResultIndex(updatedResults.length - 1);
      }
      
      console.log(`Replaced "${result.match_text}" with "${replacement}" in ${result.file_path}`);
    } catch (error) {
      console.error('Replace failed:', error);
    } finally {
      setReplacing(false);
    }
  }, [searchResults, setReplacing, setSearchResults, setCurrentResultIndex]);

  // Replace all occurrences
  const replaceAll = useCallback(async (replacement: string) => {
    if (searchResults.length === 0) return;
    
    try {
      setReplacing(true);
      
      // TODO: Implement actual replace all
      // await searchService.current.replaceInFiles(searchQuery, replacement, searchOptions);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      const replacedCount = searchResults.length;
      setSearchResults([]);
      setCurrentResultIndex(-1);
      
      console.log(`Replaced ${replacedCount} occurrences with "${replacement}"`);
    } catch (error) {
      console.error('Replace all failed:', error);
    } finally {
      setReplacing(false);
    }
  }, [searchResults, searchQuery, searchOptions, setReplacing, setSearchResults, setCurrentResultIndex]);

  // Replace in specific file
  const replaceInFile = useCallback(async (filePath: string, replacement: string) => {
    try {
      setReplacing(true);
      
      // TODO: Implement actual file replace
      // await searchService.current.replaceInFile(filePath, searchQuery, replacement, searchOptions);
      
      // Mock implementation
      await new Promise(resolve => setTimeout(resolve, 300));
      
      // Remove results from this file
      const updatedResults = searchResults.filter(result => result.file_path !== filePath);
      setSearchResults(updatedResults);
      
      if (updatedResults.length === 0) {
        setCurrentResultIndex(-1);
      } else if (currentResultIndex >= updatedResults.length) {
        setCurrentResultIndex(updatedResults.length - 1);
      }
      
      console.log(`Replaced all occurrences in ${filePath}`);
    } catch (error) {
      console.error('Replace in file failed:', error);
    } finally {
      setReplacing(false);
    }
  }, [searchQuery, searchOptions, searchResults, currentResultIndex, setReplacing, setSearchResults, setCurrentResultIndex]);

  // Add replace rule
  const addReplaceRule = useCallback((rule: Omit<ReplaceRule, 'id'>) => {
    const newRule: ReplaceRule = {
      ...rule,
    };
    addRule(newRule);
  }, [addRule]);

  // Update replace rule
  const updateReplaceRule = useCallback((index: number, updates: Partial<ReplaceRule>) => {
    updateRule(index, updates);
  }, [updateRule]);

  // Remove replace rule
  const removeReplaceRule = useCallback((index: number) => {
    removeRule(index);
  }, [removeRule]);

  // Execute batch replace
  const executeBatchReplace = useCallback(async () => {
    if (replaceRules.length === 0) return;
    
    try {
      setReplacing(true);
      setBatchProgress({ current: 0, total: replaceRules.length });
      
      // TODO: Implement actual batch replace
      // await searchService.current.batchReplace(replaceRules);
      
      // Mock implementation
      for (let i = 0; i < replaceRules.length; i++) {
        await new Promise(resolve => setTimeout(resolve, 500));
        setBatchProgress({ current: i + 1, total: replaceRules.length });
      }
      
      clearReplaceRules();
      setBatchProgress(null);
      
      console.log(`Executed ${replaceRules.length} replace rules`);
    } catch (error) {
      console.error('Batch replace failed:', error);
    } finally {
      setReplacing(false);
    }
  }, [replaceRules, setReplacing, setBatchProgress, clearReplaceRules]);

  // Auto search when query changes
  useEffect(() => {
    if (autoSearch && debouncedSearchQuery) {
      search(debouncedSearchQuery);
    }
  }, [autoSearch, debouncedSearchQuery, search]);

  return {
    // Search functionality
    search,
    clearSearch,
    navigateToResult,
    nextResult,
    previousResult,
    
    // Replace functionality
    replace,
    replaceAll,
    replaceInFile,
    
    // Batch replace functionality
    addReplaceRule,
    updateReplaceRule,
    removeReplaceRule,
    executeBatchReplace,
    
    // State
    isSearching,
    isReplacing,
    searchResults,
    currentResultIndex,
    totalResults: searchResults.length,
    hasResults: searchResults.length > 0,
  };
}