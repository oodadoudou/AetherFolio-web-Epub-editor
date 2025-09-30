// 导出服务

import { ApiService } from './api';
import { ExportResponse } from './types/file';
import { ApiResponse, BookMetadata } from '../types/api';

class ExportService {
  constructor(private apiService: ApiService) {}

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

  // 导出为ZIP文件
  async exportZip(sessionId: string, options?: {
    include_metadata?: boolean;
    compress_level?: number;
  }): Promise<ExportResponse> {
    const response = await this.apiService.post<ApiResponse<ExportResponse>>(
      `/sessions/${sessionId}/export/zip`,
      options || {}
    );
    return response.data as unknown as ExportResponse;
  }

  // 导出为HTML
  async exportHtml(sessionId: string, options?: {
    single_file?: boolean;
    include_css?: boolean;
    include_images?: boolean;
    template?: string;
  }): Promise<ExportResponse> {
    const response = await this.apiService.post<ApiResponse<ExportResponse>>(
      `/sessions/${sessionId}/export/html`,
      options || {}
    );
    return response.data as unknown as ExportResponse;
  }

  // 导出单个文件
  async exportSingleFile(sessionId: string, filePath: string, format?: 'original' | 'html' | 'text'): Promise<ExportResponse> {
    const response = await this.apiService.post<ApiResponse<ExportResponse>>(
      `/sessions/${sessionId}/export/file`,
      { file_path: filePath, format: format || 'original' }
    );
    return response.data as unknown as ExportResponse;
  }

  // 获取导出进度
  async getExportProgress(sessionId: string, exportId: string): Promise<{
    status: 'pending' | 'processing' | 'completed' | 'failed';
    progress: number;
    message?: string;
    download_url?: string;
  }> {
    const response = await this.apiService.get<ApiResponse<{
      status: 'pending' | 'processing' | 'completed' | 'failed';
      progress: number;
      message?: string;
      download_url?: string;
    }>>(`/sessions/${sessionId}/export/${exportId}/progress`);
    return response.data as unknown as {
      status: 'pending' | 'processing' | 'completed' | 'failed';
      progress: number;
      message?: string;
      download_url?: string;
    };
  }

  // 取消导出
  async cancelExport(sessionId: string, exportId: string): Promise<{ success: boolean }> {
    const response = await this.apiService.delete<ApiResponse<{ success: boolean }>>(
      `/sessions/${sessionId}/export/${exportId}`
    );
    return response.data as unknown as { success: boolean };
  }

  // 下载导出文件
  async downloadExportFile(downloadUrl: string): Promise<Blob> {
    const response = await fetch(downloadUrl);
    if (!response.ok) {
      throw new Error(`下载失败: ${response.statusText}`);
    }
    return response.blob();
  }

  // 获取导出历史
  async getExportHistory(sessionId: string): Promise<{
    exports: {
      export_id: string;
      format: string;
      created_at: string;
      status: string;
      file_size?: number;
      download_url?: string;
      expires_at?: string;
    }[];
  }> {
    const response = await this.apiService.get<ApiResponse<{
      exports: {
        export_id: string;
        format: string;
        created_at: string;
        status: string;
        file_size?: number;
        download_url?: string;
        expires_at?: string;
      }[];
    }>>(`/sessions/${sessionId}/export/history`);
    return response.data as unknown as {
      exports: {
        export_id: string;
        format: string;
        created_at: string;
        status: string;
        file_size?: number;
        download_url?: string;
        expires_at?: string;
      }[];
    };
  }
}

import { apiService } from './api';

// 创建服务实例
export const exportService = new ExportService(apiService);
export default ExportService;