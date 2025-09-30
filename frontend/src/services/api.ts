// API base service
// Contains base API configuration and utilities

import axios, { AxiosInstance, AxiosError } from 'axios';

// 基础配置
const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
const API_PREFIX = '/api/v1';

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

export class ApiError extends Error {
  constructor(
    message: string,
    public status?: number,
    public response?: unknown
  ) {
    super(message);
    this.name = 'ApiError';
  }
}

// 生成请求ID的工具函数
function generateRequestId(): string {
  return `req_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
}

export class ApiService {
  private axiosInstance: AxiosInstance;
  
  constructor() {
    this.axiosInstance = axios.create({
      baseURL: `${API_BASE_URL}${API_PREFIX}`,
      timeout: 30000,
      headers: {
        'Content-Type': 'application/json',
      },
    });
    
    this.setupInterceptors();
  }
  
  private setupInterceptors() {
    // 请求拦截器
    this.axiosInstance.interceptors.request.use(
      (config) => {
        // 添加请求 ID
        config.headers['X-Request-ID'] = generateRequestId();
        return config;
      },
      (error) => Promise.reject(error)
    );
    
    // 响应拦截器
    this.axiosInstance.interceptors.response.use(
      (response) => {
        // 直接返回axios response对象，让具体的方法处理data
        return response;
      },
      (error) => {
        const errorResponse = this.handleError(error);
        return Promise.reject(errorResponse);
      }
    );
  }
  
  private handleError(error: AxiosError): ErrorResponse {
    // 统一错误处理逻辑
    if (error.response?.data) {
      return error.response.data as ErrorResponse;
    }
    
    return {
      success: false,
      status: 'error',
      error_code: 'NETWORK_ERROR',
      message: error.message || '网络请求失败',
      timestamp: new Date().toISOString()
    };
  }

  // HTTP 方法封装
  async get<T>(url: string, params?: Record<string, unknown>): Promise<T> {
    const response = await this.axiosInstance.get(url, { params });
    return response.data;
  }
  
  async post<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.axiosInstance.post(url, data);
    return response.data;
  }
  
  async put<T>(url: string, data?: unknown): Promise<T> {
    const response = await this.axiosInstance.put(url, data);
    return response.data;
  }
  
  async delete<T>(url: string): Promise<T> {
    const response = await this.axiosInstance.delete(url);
    return response.data;
  }
  
  async upload<T>(url: string, formData: FormData): Promise<T> {
    const response = await this.axiosInstance.post(url, formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    });
    return response.data;
  }
}

// 错误处理类
class ApiErrorHandler {
  static async withRetry<T>(
    operation: () => Promise<T>,
    maxRetries: number = 3,
    delay: number = 1000
  ): Promise<T> {
    let lastError: Error;
    
    for (let attempt = 1; attempt <= maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error as Error;
        
        if (attempt === maxRetries) {
          break;
        }
        
        // 指数退避
        await new Promise(resolve => setTimeout(resolve, delay * Math.pow(2, attempt - 1)));
      }
    }
    
    throw lastError!;
  }
  
  static handleUploadError(error: ErrorResponse): string {
    switch (error.error_code) {
      case 'FILE_TOO_LARGE':
        return '文件大小超出限制，请选择较小的文件';
      case 'INVALID_FILE_FORMAT':
        return '文件格式不支持，请选择有效的 EPUB 文件';
      case 'FILE_UPLOAD_FAILED':
        return '文件上传失败，请检查网络连接后重试';
      case 'EPUB_PARSE_ERROR':
        return 'EPUB 文件解析失败，请检查文件是否损坏';
      default:
        return error.message || '上传过程中发生未知错误';
    }
  }
}

// 导出错误处理类
export { ApiErrorHandler };

// Default API service instance
export const apiService = new ApiService();