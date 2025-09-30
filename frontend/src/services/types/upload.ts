// 上传相关类型定义

import { FileNode, FileType, EncodingType, ReplaceRule, BookMetadata } from './common';

// 使用通用的BookMetadata类型
// export { BookMetadata } from './common';

// EPUB上传请求
export interface EpubUploadRequest {
  file: File;
  options?: {
    validateStructure?: boolean;
    extractMetadata?: boolean;
  };
}

// EPUB上传响应
export interface EpubUploadResponse {
  session_id: string;
  file_tree: FileNode[];
  metadata: BookMetadata;
  upload_time: string;
  file_size: number;
  extracted_files_count: number;
}

// 文本文件上传请求
export interface TextUploadRequest {
  file: File;
  encoding?: EncodingType;
}

// 文本文件上传响应
export interface TextUploadResponse {
  session_id: string;
  content: string;
  encoding: EncodingType;
  file_size: number;
  line_count: number;
  upload_time: string;
}

// 通用文件上传请求
export interface GeneralUploadRequest {
  file: File;
  file_type: FileType;
  options?: Record<string, unknown>;
}

// 通用文件上传响应
export type GeneralUploadResponse = EpubUploadResponse | TextUploadResponse;

// 上传进度信息
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
  speed?: number; // bytes per second
  estimated_time_remaining?: number; // seconds
}

// 上传选项
export interface UploadOptions {
  onProgress?: (progress: UploadProgress) => void;
  timeout?: number;
  retries?: number;
}

// 文件验证结果
export interface FileValidationResult {
  valid: boolean;
  file_type: FileType;
  size: number;
  errors: string[];
  warnings: string[];
}

// 批量替换请求
export interface BatchReplaceRequest {
  rules: ReplaceRule[];
  options?: {
    create_backup?: boolean;
    validate_rules?: boolean;
    dry_run?: boolean;
  };
}

// 批量替换进度
export interface ReplaceProgress {
  session_id: string;
  task_id: string;
  status: string;
  total_files: number;
  processed_files: number;
  total_replacements: number;
  current_file: string;
  progress_percentage: number;
  start_time: number;
  estimated_remaining: number;
  error_message?: string;
}

// 批量替换响应
export interface BatchReplaceResponse {
  task_id: string;
  total_files: number;
  estimated_time_ms: number;
}