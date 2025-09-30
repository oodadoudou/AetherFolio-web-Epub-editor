// Validation utility functions

/**
 * Validation result interface
 */
export interface ValidationResult {
  isValid: boolean;
  error?: string;
  warnings?: string[];
}



/**
 * Validate URL
 */
export function validateUrl(url: string): ValidationResult {
  if (!url || url.trim() === '') {
    return { isValid: false, error: 'URL is required' };
  }
  
  try {
    new URL(url);
    return { isValid: true };
  } catch {
    return { isValid: false, error: 'Invalid URL format' };
  }
}

/**
 * Validate regex pattern
 */
export function validateRegex(pattern: string): ValidationResult {
  if (!pattern || pattern.trim() === '') {
    return { isValid: false, error: 'Pattern is required' };
  }
  
  try {
    new RegExp(pattern);
    return { isValid: true };
  } catch (error) {
    return { 
      isValid: false, 
      error: `Invalid regex pattern: ${error instanceof Error ? error.message : 'Unknown error'}` 
    };
  }
}

/**
 * Validate file size
 */
export function validateFileSize(size: number, maxSize: number): ValidationResult {
  if (size <= 0) {
    return { isValid: false, error: 'File size must be greater than 0' };
  }
  
  if (size > maxSize) {
    return { 
      isValid: false, 
      error: `File size exceeds maximum allowed size of ${formatFileSize(maxSize)}` 
    };
  }
  
  return { isValid: true };
}

/**
 * Validate file type
 */
export function validateFileType(filename: string, allowedTypes: string[]): ValidationResult {
  if (!filename) {
    return { isValid: false, error: 'Filename is required' };
  }
  
  const extension = filename.toLowerCase().match(/\.[^.]+$/);
  if (!extension) {
    return { isValid: false, error: 'File must have an extension' };
  }
  
  if (allowedTypes.length > 0 && !allowedTypes.includes(extension[0])) {
    return { 
      isValid: false, 
      error: `File type ${extension[0]} is not allowed. Allowed types: ${allowedTypes.join(', ')}` 
    };
  }
  
  return { isValid: true };
}

/**
 * Validate EPUB metadata
 */
export function validateEpubMetadata(metadata: {
  title?: string;
  author?: string;
  language?: string;
  identifier?: string;
}): ValidationResult {
  const warnings: string[] = [];
  
  if (!metadata.title || metadata.title.trim() === '') {
    return { isValid: false, error: 'Title is required' };
  }
  
  if (!metadata.author || metadata.author.trim() === '') {
    warnings.push('Author is recommended for EPUB files');
  }
  
  if (!metadata.language || metadata.language.trim() === '') {
    warnings.push('Language is recommended for EPUB files');
  }
  
  if (metadata.identifier && metadata.identifier.trim() !== '') {
    // Basic ISBN validation
    const isbn = metadata.identifier.replace(/[^0-9X]/gi, '');
    if (isbn.length !== 10 && isbn.length !== 13) {
      warnings.push('Identifier should be a valid ISBN (10 or 13 digits)');
    }
  }
  
  return { isValid: true, warnings: warnings.length > 0 ? warnings : undefined };
}

/**
 * Validate search options
 */
export function validateSearchOptions(options: {
  query?: string;
  caseSensitive?: boolean;
  wholeWord?: boolean;
  regex?: boolean;
}): ValidationResult {
  if (!options.query || options.query.trim() === '') {
    return { isValid: false, error: 'Search query is required' };
  }
  
  if (options.regex) {
    return validateRegex(options.query);
  }
  
  return { isValid: true };
}

/**
 * Validate replace options
 */
export function validateReplaceOptions(options: {
  search?: string;
  replace?: string;
  caseSensitive?: boolean;
  wholeWord?: boolean;
  regex?: boolean;
}): ValidationResult {
  if (!options.search || options.search.trim() === '') {
    return { isValid: false, error: 'Search text is required' };
  }
  
  if (options.replace === undefined || options.replace === null) {
    return { isValid: false, error: 'Replace text is required (can be empty)' };
  }
  
  if (options.regex) {
    const searchValidation = validateRegex(options.search);
    if (!searchValidation.isValid) {
      return searchValidation;
    }
  }
  
  return { isValid: true };
}

/**
 * Validate session ID
 */
export function validateSessionId(sessionId: string): ValidationResult {
  if (!sessionId || sessionId.trim() === '') {
    return { isValid: false, error: 'Session ID is required' };
  }
  
  // UUID v4 format validation
  const uuidRegex = /^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i;
  if (!uuidRegex.test(sessionId)) {
    return { isValid: false, error: 'Invalid session ID format' };
  }
  
  return { isValid: true };
}

/**
 * Validate file path
 */
export function validateFilePath(path: string): ValidationResult {
  if (!path || path.trim() === '') {
    return { isValid: false, error: 'File path is required' };
  }
  
  // Check for invalid characters
  const invalidChars = /[<>:"|?*]/;
  if (invalidChars.test(path)) {
    return { isValid: false, error: 'File path contains invalid characters' };
  }
  
  // Check for path traversal attempts
  if (path.includes('..') || path.includes('//')) {
    return { isValid: false, error: 'Invalid file path' };
  }
  
  return { isValid: true };
}

/**
 * Helper function to format file size (imported from file utils)
 */
function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return `${parseFloat((bytes / Math.pow(k, i)).toFixed(1))} ${sizes[i]}`;
}

/**
 * Validate multiple values with different validators
 */
export function validateMultiple(
  validations: Array<() => ValidationResult>
): ValidationResult {
  const errors: string[] = [];
  const warnings: string[] = [];
  
  for (const validate of validations) {
    const result = validate();
    if (!result.isValid && result.error) {
      errors.push(result.error);
    }
    if (result.warnings) {
      warnings.push(...result.warnings);
    }
  }
  
  if (errors.length > 0) {
    return { isValid: false, error: errors.join('; ') };
  }
  
  return { 
    isValid: true, 
    warnings: warnings.length > 0 ? warnings : undefined 
  };
}