// Search and replace related type definitions

export interface SearchOptions {
  caseSensitive: boolean;
  wholeWord: boolean;
  regex: boolean;
  fileTypes: string[];
}

export interface SearchResult {
  id: string;
  filePath: string;
  fileName: string;
  line: number;
  column: number;
  match: string;
  context: string;
  startOffset: number;
  endOffset: number;
}

export interface ReplaceRule {
  id: string;
  search: string;
  replace: string;
  options: SearchOptions;
  enabled: boolean;
  description?: string;
}

export interface BatchProgress {
  current: number;
  total: number;
}

export interface SearchContext {
  query: string;
  options: SearchOptions;
  results: SearchResult[];
  currentIndex: number;
  isSearching: boolean;
}

export interface ReplaceContext {
  query: string;
  replacement: string;
  isReplacing: boolean;
  rules: ReplaceRule[];
  progress: BatchProgress | null;
}

export interface SearchReplaceState {
  search: SearchContext;
  replace: ReplaceContext;
}

export interface SearchFilter {
  fileTypes?: string[];
  directories?: string[];
  excludePatterns?: string[];
  includePatterns?: string[];
}

export interface SearchStatistics {
  totalFiles: number;
  searchedFiles: number;
  totalMatches: number;
  filesWithMatches: number;
  searchDuration: number;
}

export interface ReplaceStatistics {
  totalReplacements: number;
  filesModified: number;
  replacementDuration: number;
  errors: string[];
}