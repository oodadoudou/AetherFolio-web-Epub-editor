// EPUB API service
// Handles EPUB upload, export and metadata operations

import { ApiService } from './api';
import { ApiResponse, BookMetadata } from './types/common';
import { EpubUploadResponse } from './types/upload';
import { ExportResponse } from './types/file';

export class EpubService {
  constructor(private apiService: ApiService) {}
  
  // 上传EPUB文件
  async uploadEpub(file: File, options?: {
    extract_metadata?: boolean;
    validate_structure?: boolean;
    create_backup?: boolean;
  }): Promise<EpubUploadResponse> {
    const formData = new FormData();
    formData.append('file', file);
    if (options) {
      formData.append('options', JSON.stringify(options));
    }

    const response = await this.apiService.upload<ApiResponse<EpubUploadResponse>>('/upload/epub', formData);
    return response.data as unknown as EpubUploadResponse;
  }

  // 导出EPUB文件
  async exportEpub(sessionId: string, options?: {
    metadata?: Partial<BookMetadata>;
    include_images?: boolean;
    compress_images?: boolean;
    validate_output?: boolean;
  }): Promise<ExportResponse> {
    const response = await this.apiService.post<ApiResponse<ExportResponse>>(
      `/sessions/${sessionId}/export/epub`,
      options || {}
    );
    return response.data as unknown as ExportResponse;
  }

  // 获取EPUB元数据
  async getMetadata(sessionId: string): Promise<BookMetadata> {
    const response = await this.apiService.get<ApiResponse<BookMetadata>>(
      `/sessions/${sessionId}/metadata`
    );
    return response.data as unknown as BookMetadata;
  }

  // 更新EPUB元数据
  async updateMetadata(sessionId: string, metadata: Partial<BookMetadata>): Promise<{ success: boolean }> {
    const response = await this.apiService.put<ApiResponse<{ success: boolean }>>(
      `/sessions/${sessionId}/metadata`,
      metadata
    );
    return response.data as unknown as { success: boolean };
  }

  // 验证EPUB结构
  async validateEpub(sessionId: string): Promise<{ isValid: boolean; errors: string[]; warnings: string[] }> {
    const response = await this.apiService.get<ApiResponse<{ isValid: boolean; errors: string[]; warnings: string[] }>>(
      `/sessions/${sessionId}/validate`
    );
    return response.data as unknown as { isValid: boolean; errors: string[]; warnings: string[] };
  }

  // 获取EPUB章节列表
  async getChapters(sessionId: string): Promise<{
    chapters: {
      id: string;
      title: string;
      file_path: string;
      order: number;
    }[];
  }> {
    const response = await this.apiService.get<ApiResponse<{
      chapters: {
        id: string;
        title: string;
        file_path: string;
        order: number;
      }[];
    }>>(`/sessions/${sessionId}/chapters`);
    return response.data as unknown as {
      chapters: {
        id: string;
        title: string;
        file_path: string;
        order: number;
      }[];
    };
  }

  // 重新排序章节
  async reorderChapters(sessionId: string, chapterOrder: { id: string; order: number }[]): Promise<{ success: boolean }> {
    const response = await this.apiService.put<ApiResponse<{ success: boolean }>>(
      `/sessions/${sessionId}/chapters/reorder`,
      { chapters: chapterOrder }
    );
    return response.data as unknown as { success: boolean };
  }
}

import { apiService } from './api';

// 创建服务实例
export const epubService = new EpubService(apiService);
export default EpubService;