// API related type definitions

// 通用 API 响应
export interface ApiResponse<T = unknown> {
  success: boolean;
  status: 'success' | 'error' | 'warning';
  message: string;
  data: T;
  timestamp: string;
}

// 错误响应
export interface ErrorResponse {
  success: false;
  status: 'error';
  error_code: string;
  message: string;
  details?: Record<string, unknown>;
  timestamp: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  pageSize: number;
  totalPages: number;
}

// 成功响应
export interface SuccessResponse<T = unknown> {
  success: true;
  status: 'success';
  message: string;
  data: T;
  timestamp: string;
}

export type ApiResult<T> = SuccessResponse<T> | ErrorResponse;

// 请求选项
export interface RequestOptions {
  timeout?: number;
  retries?: number;
  headers?: Record<string, string>;
}

// 上传进度
export interface UploadProgress {
  loaded: number;
  total: number;
  percentage: number;
}

// 上传选项
export interface UploadOptions extends RequestOptions {
  onProgress?: (progress: UploadProgress) => void;
}

// 文件类型枚举
export enum FileType {
  FILE = 'file',
  DIRECTORY = 'directory',
  HTML = 'html',
  TEXT = 'text',
  XML = 'xml',
  CSS = 'css',
  JAVASCRIPT = 'javascript',
  IMAGE = 'image',
  FONT = 'font',
  EPUB = 'epub'
}

// 编码类型
export enum EncodingType {
  UTF8 = 'utf-8',
  UTF16 = 'utf-16',
  ASCII = 'ascii',
  LATIN1 = 'latin1'
}

// 会话状态
export enum SessionStatus {
  ACTIVE = 'active',
  EXPIRED = 'expired',
  INVALID = 'invalid'
}

// 行结束类型
export enum LineEndingType {
  LF = 'lf',
  CRLF = 'crlf',
  CR = 'cr'
}

// 任务状态
export enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// 文件节点
export interface FileNode {
  name: string;
  path: string;
  type: FileType;
  size?: number;
  mime_type?: string;
  modified_time?: string;
  children?: FileNode[];
}

// 书籍元数据
export interface BookMetadata {
  title: string;
  author: string;
  language?: string;
  publisher?: string;
  publication_date?: string;
  isbn?: string;
  description?: string;
  cover_image?: string;
  contributor?: string[];
  subject?: string[];
  rights?: string;
}

// 会话信息
export interface SessionInfo {
  session_id: string;
  file_type: FileType;
  created_at: string;
  expires_at: string;
  last_accessed: string;
  file_tree?: FileNode[];
  metadata?: BookMetadata;
  status: SessionStatus;
  file_count?: number;
  total_size?: number;
  original_filename?: string;
}

// 基础请求
export interface BaseRequest {
  session_id: string;
}

// 分页参数
export interface PaginationParams {
  page?: number;
  pageSize?: number;
  limit?: number;
  offset?: number;
}

// 排序参数
export interface SortParams {
  sort_by?: string;
  sort_order?: 'asc' | 'desc';
}

// 进度信息
export interface ProgressInfo {
  total: number;
  completed: number;
  percentage: number;
  current_item?: string;
  estimated_remaining?: number;
}

// 搜索选项
export interface SearchOptions {
  case_sensitive?: boolean;
  regex?: boolean;
  whole_word?: boolean;
  file_types?: string[];
  include_paths?: string[];
  exclude_paths?: string[];
}

// 搜索结果
export interface SearchResult {
  file_path: string;
  line_number: number;
  line_content: string;
  match_start: number;
  match_end: number;
  match_text: string;
}

// 替换规则
export interface ReplaceRule {
  original: string;
  replacement: string;
  is_regex: boolean;
  enabled: boolean;
  description?: string;
  case_sensitive: boolean;
  target_files?: string[];
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
  success: boolean;
  content: string;
  encoding: string;
  mime_type: string;
  size: number;
  last_modified?: string;
  is_binary: boolean;
}