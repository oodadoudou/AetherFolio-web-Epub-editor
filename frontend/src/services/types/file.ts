// 文件操作相关类型定义

import { BaseRequest, FileNode, EncodingType, FileType, SearchOptions, BookMetadata } from './common';

// 文件内容请求
export interface FileContentRequest extends BaseRequest {
  file_path: string;
  encoding?: EncodingType;
}

// 文件内容
export interface FileContent {
  path: string;
  content: string;
  encoding: string;
  mime_type: string;
  size: number;
  is_binary: boolean;
  chunk_info?: Record<string, unknown>;
  checksum?: string;
  last_modified?: string;
}

// 文件内容响应
export interface FileContentResponse {
  content: string;
  file_path: string;
  file_type: string;
  encoding: EncodingType;
  size: number;
  line_count: number;
  last_modified: string;
  mime_type: string;
}

// 保存文件请求
export interface SaveFileRequest extends BaseRequest {
  file_path: string;
  content: string;
  encoding?: EncodingType;
  create_backup?: boolean;
}

// 保存文件响应
export interface SaveFileResponse {
  success: boolean;
  file_path: string;
  size: number;
  checksum: string;
  backup_created?: boolean;
}

// 文件树请求
export interface FileTreeRequest extends BaseRequest {
  include_content?: boolean;
  max_depth?: number;
  file_types?: string[];
}

// 文件信息
export interface FileInfo {
  path: string;
  name: string;
  type: FileType;
  size: number;
  mime_type: string;
  encoding?: EncodingType;
  created_at: string;
  modified_at: string;
  checksum: string;
  is_binary: boolean;
}

// 文件操作类型
export type FileOperation = 'create' | 'update' | 'delete' | 'rename' | 'copy' | 'move';

// 文件操作请求
export interface FileOperationRequest extends BaseRequest {
  operation: FileOperation;
  source_path: string;
  target_path?: string;
  content?: string;
  options?: {
    overwrite?: boolean;
    create_backup?: boolean;
    preserve_permissions?: boolean;
  };
}

// 文件操作响应
export interface FileOperationResponse {
  success: boolean;
  operation: FileOperation;
  source_path: string;
  target_path?: string;
  backup_path?: string;
  timestamp: string;
  file_info?: FileInfo;
}

// 文件搜索请求
export interface FileSearchRequest extends BaseRequest {
  query: string;
  file_types?: string[];
  include_content?: boolean;
  max_results?: number;
}

// 文件搜索结果
export interface FileSearchResult {
  file_path: string;
  file_name: string;
  file_type: string;
  size: number;
  last_modified: string;
  match_type: 'filename' | 'content';
  matches?: {
    line_number: number;
    content: string;
    highlighted: string;
  }[];
}

// 文件搜索响应
export interface FileSearchResponse {
  query: string;
  total_results: number;
  search_time: number;
  results: FileSearchResult[];
  truncated: boolean;
}

// 文件比较请求
export interface FileCompareRequest extends BaseRequest {
  file_path_a: string;
  file_path_b: string;
  options?: {
    ignore_whitespace?: boolean;
    ignore_case?: boolean;
    context_lines?: number;
  };
}

// 文件差异信息
export interface FileDiff {
  type: 'added' | 'removed' | 'modified';
  line_number_a?: number;
  line_number_b?: number;
  content_a?: string;
  content_b?: string;
}

// 文件比较响应
export interface FileCompareResponse {
  file_path_a: string;
  file_path_b: string;
  identical: boolean;
  differences: FileDiff[];
  stats: {
    lines_added: number;
    lines_removed: number;
    lines_modified: number;
  };
}

// 文件历史记录
export interface FileHistory {
  file_path: string;
  operations: {
    operation: FileOperation;
    timestamp: string;
    backup_path?: string;
    user_agent?: string;
  }[];
}

// 搜索请求
export interface SearchRequest {
  query: string;
  options: SearchOptions;
}

// 搜索结果
export interface SearchResult {
  file_path: string;
  line_number: number;
  line_content: string;
  match_start: number;
  match_end: number;
  context_before?: string;
  context_after?: string;
}

// 搜索响应
export interface SearchResponse {
  query: string;
  total_matches: number;
  files_searched: number;
  results: SearchResult[];
  search_time_ms: number;
}

// 替换响应
export interface ReplaceResponse {
  file_path: string;
  replacements_made: number;
  total_matches: number;
  new_content?: string;
}

// 导出响应
export interface ExportResponse {
  download_url: string;
  file_size: number;
  expires_at: string;
}

// 上传响应
export interface UploadResponse {
  sessionId: string;
  fileTree: FileNode[];
  metadata?: BookMetadata;
  fileType: 'epub' | 'text';
}