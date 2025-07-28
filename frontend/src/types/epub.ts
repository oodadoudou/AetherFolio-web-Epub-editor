// EPUB related type definitions

export interface EpubMetadata {
  title: string;
  author: string;
  language: string;
  identifier?: string;
  publisher?: string;
  date?: string;
  description?: string;
  cover?: string;
  rights?: string;
  subject?: string[];
  contributor?: string[];
}

export interface EpubManifestItem {
  id: string;
  href: string;
  mediaType: string;
  properties?: string[];
}

export interface EpubSpineItem {
  idref: string;
  linear?: boolean;
  properties?: string[];
}

export interface EpubTocItem {
  id: string;
  title: string;
  href: string;
  children?: EpubTocItem[];
  playOrder?: number;
}

export interface EpubStructure {
  metadata: EpubMetadata;
  manifest: EpubManifestItem[];
  spine: EpubSpineItem[];
  toc: EpubTocItem[];
  guide?: Array<{
    type: string;
    title: string;
    href: string;
  }>;
}

export interface EpubValidationError {
  type: 'error' | 'warning';
  message: string;
  file?: string;
  line?: number;
  column?: number;
}

export interface EpubValidationResult {
  isValid: boolean;
  errors: EpubValidationError[];
  warnings: EpubValidationError[];
}

export interface EpubExportOptions {
  includeImages: boolean;
  includeFonts: boolean;
  includeStyles: boolean;
  compression: 'none' | 'fast' | 'best';
  validateStructure: boolean;
}

export type EpubFileType = 
  | 'html' 
  | 'xhtml' 
  | 'css' 
  | 'image' 
  | 'font' 
  | 'audio' 
  | 'video' 
  | 'javascript' 
  | 'xml' 
  | 'other';

export interface EpubFile {
  path: string;
  name: string;
  type: EpubFileType;
  size: number;
  modified: Date;
  content?: string | ArrayBuffer;
  encoding?: string;
}