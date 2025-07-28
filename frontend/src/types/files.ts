// Files related type definitions

export interface FileNode {
  id: string;
  name: string;
  path: string;
  type: 'file' | 'directory';
  size?: number;
  modified?: Date;
  children?: FileNode[];
  isExpanded?: boolean;
  isSelected?: boolean;
  isEditable?: boolean;
  icon?: string;
  extension?: string;
}

export interface FileContent {
  content: string;
  encoding: 'utf-8' | 'base64' | 'binary';
  size: number;
  modified: string;
  checksum?: string;
}

export interface FileOperation {
  type: 'create' | 'update' | 'delete' | 'rename' | 'move';
  path: string;
  newPath?: string;
  content?: string;
  timestamp: Date;
}

export interface FileHistory {
  operations: FileOperation[];
  currentIndex: number;
}

export interface FileTreeState {
  tree: FileNode[];
  expandedNodes: Set<string>;
  selectedNodes: Set<string>;
  draggedNode?: FileNode;
  dropTarget?: FileNode;
}

export interface FileFilter {
  extensions?: string[];
  namePattern?: string;
  sizeRange?: {
    min?: number;
    max?: number;
  };
  modifiedRange?: {
    start?: Date;
    end?: Date;
  };
  includeHidden?: boolean;
}

export interface FileSortOptions {
  field: 'name' | 'size' | 'modified' | 'type';
  direction: 'asc' | 'desc';
}

export interface FileStats {
  totalFiles: number;
  totalDirectories: number;
  totalSize: number;
  fileTypes: Record<string, number>;
  largestFile?: {
    path: string;
    size: number;
  };
  oldestFile?: {
    path: string;
    modified: Date;
  };
  newestFile?: {
    path: string;
    modified: Date;
  };
}

export interface DragDropData {
  sourceNode: FileNode;
  targetNode: FileNode;
  position: 'before' | 'after' | 'inside';
  operation: 'move' | 'copy';
}

export type FileExtension = 
  | '.html' 
  | '.xhtml' 
  | '.css' 
  | '.js' 
  | '.json' 
  | '.xml' 
  | '.opf' 
  | '.ncx' 
  | '.txt' 
  | '.md' 
  | '.jpg' 
  | '.jpeg' 
  | '.png' 
  | '.gif' 
  | '.svg' 
  | '.webp' 
  | '.ttf' 
  | '.otf' 
  | '.woff' 
  | '.woff2' 
  | '.eot';

export interface FileTypeInfo {
  extension: FileExtension;
  mimeType: string;
  category: 'text' | 'image' | 'font' | 'style' | 'script' | 'data' | 'other';
  isEditable: boolean;
  icon: string;
  color?: string;
}