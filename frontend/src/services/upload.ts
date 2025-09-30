// 上传服务

import { ApiService } from './api';
import { UploadProgress } from '../types/api';
import { ApiResponse, FileType } from '../types/api';
import { EpubUploadResponse } from '../types/epub';

type UploadResponse = EpubUploadResponse;

class UploadService {
  constructor(private apiService: ApiService) {}

  // 上传EPUB文件
  async uploadEpub(file: File, options?: {
    extract_metadata?: boolean;
    validate_structure?: boolean;
    create_backup?: boolean;
  }): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      formData.append('options', JSON.stringify(options));
    }

    const response = await this.apiService.upload<ApiResponse<UploadResponse>>('/upload', formData);
    return response.data as unknown as UploadResponse;
  }

  // 上传文本文件
  async uploadText(file: File, options?: {
    encoding?: string;
    create_backup?: boolean;
  }): Promise<UploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      formData.append('options', JSON.stringify(options));
    }

    const response = await this.apiService.upload<ApiResponse<UploadResponse>>('/upload', formData);
    return response.data as unknown as UploadResponse;
  }

  // 统一上传接口
  async uploadFile(file: File, fileType?: FileType, options?: {
    extract_metadata?: boolean;
    validate_structure?: boolean;
    create_backup?: boolean;
    encoding?: string;
  }): Promise<UploadResponse> {
    // 自动检测文件类型
    const detectedType = fileType || this.detectFileType(file);
    
    if (detectedType === FileType.EPUB) {
      return this.uploadEpub(file, options);
    } else {
      return this.uploadText(file, options);
    }
  }

  // 获取上传进度
  async getUploadProgress(uploadId: string): Promise<UploadProgress> {
    const response = await this.apiService.get<ApiResponse<UploadProgress>>(`/upload/progress/${uploadId}`);
    return response.data as unknown as UploadProgress;
  }

  // 取消上传
  async cancelUpload(uploadId: string): Promise<{ success: boolean }> {
    const response = await this.apiService.delete<ApiResponse<{ success: boolean }>>(`/upload/${uploadId}`);
    return response.data as unknown as { success: boolean };
  }

  // 检测文件类型
  private detectFileType(file: File): FileType {
    const extension = file.name.toLowerCase().split('.').pop();
    
    switch (extension) {
      case 'epub':
        return FileType.EPUB;
      case 'txt':
      case 'text':
        return FileType.TEXT;
      default: {
        // 根据MIME类型判断
        if (file.type === 'application/epub+zip') {
          return FileType.EPUB;
        } else if (file.type.startsWith('text/')) {
          return FileType.TEXT;
        }
        return FileType.TEXT; // 默认为文本类型
      }
    }
  }

  // 验证文件
  async validateFile(file: File): Promise<{ isValid: boolean; errors: string[]; warnings: string[] }> {
    const fileType = this.detectFileType(file);
    const errors: string[] = [];
    const warnings: string[] = [];

    // 文件大小检查
    const maxSize = fileType === FileType.EPUB ? 100 * 1024 * 1024 : 10 * 1024 * 1024; // EPUB: 100MB, Text: 10MB
    if (file.size > maxSize) {
      errors.push(`文件大小超过限制 (${Math.round(maxSize / 1024 / 1024)}MB)`);
    }

    // 文件名检查 - 只检查真正危险的字符
    if (/[<>:"|?*\\]|\.\./.test(file.name)) {
      errors.push('文件名包含不安全字符');
    }
    
    // 检查ASCII控制字符
    if (file.name.split('').some(c => c.charCodeAt(0) < 32)) {
      errors.push('文件名包含控制字符');
    }

    return {
      isValid: errors.length === 0,
      errors,
      warnings
    };
  }
}

import { apiService } from './api';

// 创建服务实例
export const uploadService = new UploadService(apiService);
export default UploadService;