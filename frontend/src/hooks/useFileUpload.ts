// Custom hook for file upload functionality

import { useState, useCallback, useRef, useEffect } from 'react';
import { validateFileSize, validateFileType } from '../utils/validation';
import { FILE_CONFIG, ALLOWED_FILE_EXTENSIONS, UPLOAD_ALLOWED_EXTENSIONS } from '../utils/constants';

export interface UploadOptions {
  maxSize?: number;
  allowedTypes?: string[];
  multiple?: boolean;
  onProgress?: (progress: number) => void;
  onSuccess?: (files: File[]) => void;
  onError?: (error: string) => void;
}

export interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  uploadedFiles: File[];
}

export interface UseFileUploadReturn {
  uploadState: UploadState;
  uploadFiles: (files: FileList | File[]) => Promise<void>;
  selectFiles: () => void;
  resetUpload: () => void;
  isDragOver: boolean;
  dragHandlers: {
    onDragEnter: (e: React.DragEvent) => void;
    onDragLeave: (e: React.DragEvent) => void;
    onDragOver: (e: React.DragEvent) => void;
    onDrop: (e: React.DragEvent) => void;
  };
}

/**
 * Custom hook for handling file uploads with drag & drop support
 * @param options - Upload configuration options
 * @returns Upload state and handlers
 */
export function useFileUpload(options: UploadOptions = {}): UseFileUploadReturn {
  const {
    maxSize = FILE_CONFIG.MAX_FILE_SIZE,
    allowedTypes = ALLOWED_FILE_EXTENSIONS,
    multiple = false,
    onProgress,
    onSuccess,
    onError,
  } = options;

  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
    uploadedFiles: [],
  });

  const [isDragOver, setIsDragOver] = useState(false);
  const fileInputRef = useRef<HTMLInputElement | null>(null);
  const dragCounterRef = useRef(0);

  // Validate files before upload
  const validateFiles = useCallback(
    (files: File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        // Validate file size
        const sizeValidation = validateFileSize(file.size, maxSize);
        if (!sizeValidation.isValid) {
          errors.push(`${file.name}: ${sizeValidation.error}`);
          continue;
        }

        // Validate file type
        const typeValidation = validateFileType(file.name, allowedTypes as string[]);
        if (!typeValidation.isValid) {
          errors.push(`${file.name}: ${typeValidation.error}`);
          continue;
        }

        valid.push(file);
      }

      return { valid, errors };
    },
    [maxSize, allowedTypes]
  );

  // Upload files
  const uploadFiles = useCallback(
    async (fileList: FileList | File[]): Promise<void> => {
      const files = Array.from(fileList);
      
      // Limit to single file if multiple is false
      const filesToUpload = multiple ? files : files.slice(0, 1);
      
      // Validate files
      const { valid, errors } = validateFiles(filesToUpload);
      
      if (errors.length > 0) {
        const errorMessage = errors.join('; ');
        setUploadState(prev => ({ ...prev, error: errorMessage }));
        onError?.(errorMessage);
        return;
      }

      if (valid.length === 0) {
        const errorMessage = 'No valid files to upload';
        setUploadState(prev => ({ ...prev, error: errorMessage }));
        onError?.(errorMessage);
        return;
      }

      // Start upload
      setUploadState({
        isUploading: true,
        progress: 0,
        error: null,
        uploadedFiles: [],
      });

      try {
        // Simulate upload progress (replace with actual upload logic)
        for (let i = 0; i <= 100; i += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          const progress = i;
          setUploadState(prev => ({ ...prev, progress }));
          onProgress?.(progress);
        }

        // Upload completed
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          progress: 100,
          uploadedFiles: valid,
        }));
        
        onSuccess?.(valid);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          error: errorMessage,
        }));
        onError?.(errorMessage);
      }
    },
    [multiple, validateFiles, onProgress, onSuccess, onError]
  );

  // Select files using file input
  const selectFiles = useCallback(() => {
    if (!fileInputRef.current) {
      // Create hidden file input if it doesn't exist
      const input = document.createElement('input');
      input.type = 'file';
      input.multiple = multiple;
      input.accept = allowedTypes.map(ext => `.${ext}`).join(',');
      input.style.display = 'none';
      
      input.onchange = (e) => {
        const target = e.target as HTMLInputElement;
        if (target.files && target.files.length > 0) {
          uploadFiles(target.files);
        }
      };
      
      document.body.appendChild(input);
      fileInputRef.current = input;
    }
    
    fileInputRef.current.click();
  }, [multiple, allowedTypes, uploadFiles]);

  // Reset upload state
  const resetUpload = useCallback(() => {
    setUploadState({
      isUploading: false,
      progress: 0,
      error: null,
      uploadedFiles: [],
    });
    setIsDragOver(false);
    dragCounterRef.current = 0;
  }, []);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current++;
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    dragCounterRef.current--;
    if (dragCounterRef.current === 0) {
      setIsDragOver(false);
    }
  }, []);

  const handleDragOver = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
  }, []);

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      e.stopPropagation();
      setIsDragOver(false);
      dragCounterRef.current = 0;

      if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
        uploadFiles(e.dataTransfer.files);
      }
    },
    [uploadFiles]
  );

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (fileInputRef.current) {
        document.body.removeChild(fileInputRef.current);
      }
    };
  }, []);

  return {
    uploadState,
    uploadFiles,
    selectFiles,
    resetUpload,
    isDragOver,
    dragHandlers: {
      onDragEnter: handleDragEnter,
      onDragLeave: handleDragLeave,
      onDragOver: handleDragOver,
      onDrop: handleDrop,
    },
  };
}

/**
 * Custom hook for handling EPUB file uploads specifically
 * @param onSuccess - Callback when EPUB upload succeeds
 * @param onError - Callback when upload fails
 * @returns Upload state and handlers for EPUB files
 */
export function useEpubUpload(
  onSuccess?: (file: File) => void,
  onError?: (error: string) => void
): UseFileUploadReturn {
  return useFileUpload({
    maxSize: FILE_CONFIG.MAX_FILE_SIZE,
    allowedTypes: ['epub'],
    multiple: false,
    onSuccess: (files) => {
      if (files.length > 0) {
        onSuccess?.(files[0]);
      }
    },
    onError,
  });
}

/**
 * Custom hook for handling TEXT file uploads specifically
 * @param onSuccess - Callback when TEXT upload succeeds
 * @param onError - Callback when upload fails
 * @returns Upload state and handlers for TEXT files
 */
export function useTextUpload(
  onSuccess?: (file: File) => void,
  onError?: (error: string) => void
): UseFileUploadReturn {
  return useFileUpload({
    maxSize: FILE_CONFIG.MAX_FILE_SIZE,
    allowedTypes: ['txt'],
    multiple: false,
    onSuccess: (files) => {
      if (files.length > 0) {
        onSuccess?.(files[0]);
      }
    },
    onError,
  });
}

/**
 * Custom hook for handling both EPUB and TEXT file uploads
 * @param onSuccess - Callback when upload succeeds
 * @param onError - Callback when upload fails
 * @returns Upload state and handlers for both file types
 */
export function useMultiFileUpload(
  onSuccess?: (file: File) => void,
  onError?: (error: string) => void
): UseFileUploadReturn {
  return useFileUpload({
    maxSize: FILE_CONFIG.MAX_FILE_SIZE,
    allowedTypes: [...UPLOAD_ALLOWED_EXTENSIONS],
    multiple: false,
    onSuccess: (files) => {
      if (files.length > 0) {
        onSuccess?.(files[0]);
      }
    },
    onError,
  });
}