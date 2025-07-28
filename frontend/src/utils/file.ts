// File utility functions

import { FileExtension, FileTypeInfo } from '../types/files';

// File type mappings
export const FILE_TYPE_MAP: Record<FileExtension, FileTypeInfo> = {
  '.html': {
    extension: '.html',
    mimeType: 'text/html',
    category: 'text',
    isEditable: true,
    icon: 'FileText',
    color: '#e34c26'
  },
  '.xhtml': {
    extension: '.xhtml',
    mimeType: 'application/xhtml+xml',
    category: 'text',
    isEditable: true,
    icon: 'FileText',
    color: '#e34c26'
  },
  '.css': {
    extension: '.css',
    mimeType: 'text/css',
    category: 'style',
    isEditable: true,
    icon: 'Palette',
    color: '#1572b6'
  },
  '.js': {
    extension: '.js',
    mimeType: 'application/javascript',
    category: 'script',
    isEditable: true,
    icon: 'Code',
    color: '#f7df1e'
  },
  '.json': {
    extension: '.json',
    mimeType: 'application/json',
    category: 'data',
    isEditable: true,
    icon: 'Braces',
    color: '#000000'
  },
  '.xml': {
    extension: '.xml',
    mimeType: 'application/xml',
    category: 'data',
    isEditable: true,
    icon: 'FileCode',
    color: '#ff6600'
  },
  '.opf': {
    extension: '.opf',
    mimeType: 'application/oebps-package+xml',
    category: 'data',
    isEditable: true,
    icon: 'Package',
    color: '#8b4513'
  },
  '.ncx': {
    extension: '.ncx',
    mimeType: 'application/x-dtbncx+xml',
    category: 'data',
    isEditable: true,
    icon: 'List',
    color: '#8b4513'
  },
  '.txt': {
    extension: '.txt',
    mimeType: 'text/plain',
    category: 'text',
    isEditable: true,
    icon: 'FileText',
    color: '#000000'
  },
  '.md': {
    extension: '.md',
    mimeType: 'text/markdown',
    category: 'text',
    isEditable: true,
    icon: 'FileText',
    color: '#083fa1'
  },
  '.jpg': {
    extension: '.jpg',
    mimeType: 'image/jpeg',
    category: 'image',
    isEditable: false,
    icon: 'Image',
    color: '#ff6b6b'
  },
  '.jpeg': {
    extension: '.jpeg',
    mimeType: 'image/jpeg',
    category: 'image',
    isEditable: false,
    icon: 'Image',
    color: '#ff6b6b'
  },
  '.png': {
    extension: '.png',
    mimeType: 'image/png',
    category: 'image',
    isEditable: false,
    icon: 'Image',
    color: '#ff6b6b'
  },
  '.gif': {
    extension: '.gif',
    mimeType: 'image/gif',
    category: 'image',
    isEditable: false,
    icon: 'Image',
    color: '#ff6b6b'
  },
  '.svg': {
    extension: '.svg',
    mimeType: 'image/svg+xml',
    category: 'image',
    isEditable: true,
    icon: 'Image',
    color: '#ff9500'
  },
  '.webp': {
    extension: '.webp',
    mimeType: 'image/webp',
    category: 'image',
    isEditable: false,
    icon: 'Image',
    color: '#ff6b6b'
  },
  '.ttf': {
    extension: '.ttf',
    mimeType: 'font/ttf',
    category: 'font',
    isEditable: false,
    icon: 'Type',
    color: '#4a90e2'
  },
  '.otf': {
    extension: '.otf',
    mimeType: 'font/otf',
    category: 'font',
    isEditable: false,
    icon: 'Type',
    color: '#4a90e2'
  },
  '.woff': {
    extension: '.woff',
    mimeType: 'font/woff',
    category: 'font',
    isEditable: false,
    icon: 'Type',
    color: '#4a90e2'
  },
  '.woff2': {
    extension: '.woff2',
    mimeType: 'font/woff2',
    category: 'font',
    isEditable: false,
    icon: 'Type',
    color: '#4a90e2'
  },
  '.eot': {
    extension: '.eot',
    mimeType: 'application/vnd.ms-fontobject',
    category: 'font',
    isEditable: false,
    icon: 'Type',
    color: '#4a90e2'
  }
};

/**
 * Get file extension from filename
 */
export function getFileExtension(filename: string): FileExtension | null {
  const ext = filename.toLowerCase().match(/\.[^.]+$/);
  return ext ? (ext[0] as FileExtension) : null;
}

/**
 * Get file type information
 */
export function getFileTypeInfo(filename: string): FileTypeInfo | null {
  const extension = getFileExtension(filename);
  return extension ? FILE_TYPE_MAP[extension] || null : null;
}

/**
 * Check if file is editable
 */
export function isFileEditable(filename: string): boolean {
  const typeInfo = getFileTypeInfo(filename);
  return typeInfo?.isEditable || false;
}

/**
 * Check if file is an image
 */
export function isImageFile(filename: string): boolean {
  const typeInfo = getFileTypeInfo(filename);
  return typeInfo?.category === 'image' || false;
}

/**
 * Check if file is a text file
 */
export function isTextFile(filename: string): boolean {
  const typeInfo = getFileTypeInfo(filename);
  return typeInfo?.category === 'text' || typeInfo?.category === 'style' || typeInfo?.category === 'script' || typeInfo?.category === 'data' || false;
}

/**
 * Format file size in human readable format
 */
export function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Validate filename
 */
export function validateFilename(filename: string): { isValid: boolean; error?: string } {
  if (!filename || filename.trim() === '') {
    return { isValid: false, error: 'Filename cannot be empty' };
  }
  
  // Check for invalid characters
  const invalidChars = /[<>:"/\\|?*]/;
  if (invalidChars.test(filename)) {
    return { isValid: false, error: 'Filename contains invalid characters' };
  }
  
  // Check for reserved names (Windows)
  const reservedNames = /^(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])$/i;
  if (reservedNames.test(filename)) {
    return { isValid: false, error: 'Filename is a reserved name' };
  }
  
  // Check length
  if (filename.length > 255) {
    return { isValid: false, error: 'Filename is too long' };
  }
  
  return { isValid: true };
}

/**
 * Generate unique filename
 */
export function generateUniqueFilename(baseName: string, existingNames: string[]): string {
  if (!existingNames.includes(baseName)) {
    return baseName;
  }
  
  const extension = getFileExtension(baseName);
  const nameWithoutExt = extension ? baseName.slice(0, -extension.length) : baseName;
  
  let counter = 1;
  let newName: string;
  
  do {
    newName = extension 
      ? `${nameWithoutExt} (${counter})${extension}`
      : `${nameWithoutExt} (${counter})`;
    counter++;
  } while (existingNames.includes(newName));
  
  return newName;
}

/**
 * Sort files by various criteria
 */
export function sortFiles<T extends { name: string; type: 'file' | 'directory'; size?: number; modified?: Date }>(
  files: T[],
  sortBy: 'name' | 'size' | 'modified' | 'type',
  direction: 'asc' | 'desc' = 'asc'
): T[] {
  const sorted = [...files].sort((a, b) => {
    // Always put directories first
    if (a.type !== b.type) {
      return a.type === 'directory' ? -1 : 1;
    }
    
    let comparison = 0;
    
    switch (sortBy) {
      case 'name':
        comparison = a.name.localeCompare(b.name, undefined, { numeric: true });
        break;
      case 'size':
        comparison = (a.size || 0) - (b.size || 0);
        break;
      case 'modified':
        const aTime = a.modified?.getTime() || 0;
        const bTime = b.modified?.getTime() || 0;
        comparison = aTime - bTime;
        break;
      case 'type':
        const aExt = getFileExtension(a.name) || '';
        const bExt = getFileExtension(b.name) || '';
        comparison = aExt.localeCompare(bExt);
        break;
    }
    
    return direction === 'desc' ? -comparison : comparison;
  });
  
  return sorted;
}