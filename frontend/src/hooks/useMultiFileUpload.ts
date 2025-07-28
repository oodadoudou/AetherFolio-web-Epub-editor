import { useState, useCallback } from 'react';
import { validateFileSize, validateFileType } from '../utils/validation';
import { UPLOAD_ALLOWED_EXTENSIONS, FILE_CONFIG } from '../utils/constants';

export interface UploadState {
  isUploading: boolean;
  progress: number;
  error: string | null;
  uploadedFiles: File[];
}

export interface UseMultiFileUploadReturn {
  uploadState: UploadState;
  uploadFiles: (files: File[]) => Promise<void>;
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
 * Custom hook for handling multi-file uploads with validation
 * @param onSuccess - Callback when upload succeeds
 * @param onError - Callback when upload fails
 * @returns Upload state and handlers
 */
export function useMultiFileUpload(
  onSuccess: (file: File) => void,
  onError: (error: string) => void
): UseMultiFileUploadReturn {
  const [uploadState, setUploadState] = useState<UploadState>({
    isUploading: false,
    progress: 0,
    error: null,
    uploadedFiles: [],
  });

  const [isDragOver, setIsDragOver] = useState(false);

  // Validate files before upload
  const validateFiles = useCallback(
    (files: File[]): { valid: File[]; errors: string[] } => {
      const valid: File[] = [];
      const errors: string[] = [];

      for (const file of files) {
        // Validate file size
        const sizeValidation = validateFileSize(file.size, FILE_CONFIG.MAX_FILE_SIZE);
        if (!sizeValidation.isValid) {
          errors.push(`${file.name}: ${sizeValidation.error}`);
          continue;
        }

        // Validate file type
        const typeValidation = validateFileType(file.name, [...UPLOAD_ALLOWED_EXTENSIONS]);
        if (!typeValidation.isValid) {
          errors.push(`${file.name}: ${typeValidation.error}`);
          continue;
        }

        valid.push(file);
      }

      return { valid, errors };
    },
    []
  );

  // Upload files
  const uploadFiles = useCallback(
    async (files: File[]): Promise<void> => {
      // Only allow single file upload
      const filesToUpload = files.slice(0, 1);
      
      // Validate files
      const { valid, errors } = validateFiles(filesToUpload);
      
      if (errors.length > 0) {
        const errorMessage = errors.join('; ');
        setUploadState(prev => ({ ...prev, error: errorMessage }));
        onError(errorMessage);
        return;
      }

      if (valid.length === 0) {
        const errorMessage = 'No valid files to upload';
        setUploadState(prev => ({ ...prev, error: errorMessage }));
        onError(errorMessage);
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
        // Simulate upload progress
        for (let i = 0; i <= 100; i += 10) {
          await new Promise(resolve => setTimeout(resolve, 100));
          setUploadState(prev => ({ ...prev, progress: i }));
        }

        // Upload completed
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          progress: 100,
          uploadedFiles: valid,
        }));
        
        onSuccess(valid[0]);
      } catch (error) {
        const errorMessage = error instanceof Error ? error.message : 'Upload failed';
        setUploadState(prev => ({
          ...prev,
          isUploading: false,
          error: errorMessage,
        }));
        onError(errorMessage);
      }
    },
    [validateFiles, onSuccess, onError]
  );

  // Reset upload state
  const resetUpload = useCallback(() => {
    setUploadState({
      isUploading: false,
      progress: 0,
      error: null,
      uploadedFiles: [],
    });
    setIsDragOver(false);
  }, []);

  // Drag and drop handlers
  const handleDragEnter = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.dataTransfer.items && e.dataTransfer.items.length > 0) {
      setIsDragOver(true);
    }
  }, []);

  const handleDragLeave = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setIsDragOver(false);
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

      const files = Array.from(e.dataTransfer.files);
      if (files.length > 0) {
        uploadFiles(files);
      }
    },
    [uploadFiles]
  );

  return {
    uploadState,
    uploadFiles,
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

export default useMultiFileUpload;