// 通用类型定义

// 通用 API 响应
export interface ApiResponse<T = unknown> {
  success: boolean;
  status: 'success' | 'error' | 'warning';
  message: string;
  data?: T;
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
  FONT = 'font'
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

// 基础请求参数
export interface BaseRequest {
  session_id: string;
}

// 分页参数
export interface PaginationParams {
  page?: number;
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

// 任务状态
export enum TaskStatus {
  PENDING = 'pending',
  RUNNING = 'running',
  COMPLETED = 'completed',
  FAILED = 'failed',
  CANCELLED = 'cancelled'
}

// 行结束类型
export enum LineEndingType {
  LF = 'lf',
  CRLF = 'crlf',
  CR = 'cr'
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

// 替换规则
export interface ReplaceRule {
  id?: string;
  original: string;
  replacement: string;
  is_regex: boolean;
  enabled: boolean;
  description?: string;
  case_sensitive: boolean;
  target_files?: string[];
}