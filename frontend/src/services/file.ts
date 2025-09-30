// 文件服务

import { ApiService, apiService } from './api';
import { 
  SearchRequest,
  SearchResponse,
  ReplaceResponse,
  ExportResponse,
  FileInfo
} from './types/file';
import { ApiResponse, BookMetadata, FileContentResponse, FileContent } from '../types/api';
// import { FileNode } from '../types/api'; // 暂时注释掉未使用的导入
import { SessionInfo } from '../types/api';

class FileService {
  constructor(private apiService: ApiService) {}
  
  // 上传方法
  async uploadEpub(file: File): Promise<SessionInfo> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.apiService.upload<ApiResponse<SessionInfo>>('/upload', formData);
    return response.data as unknown as SessionInfo;
  }
  
  async uploadText(file: File): Promise<SessionInfo> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.apiService.upload<ApiResponse<SessionInfo>>('/upload', formData);
    return response.data as unknown as SessionInfo;
  }
  
  async uploadFile(file: File): Promise<SessionInfo> {
    const formData = new FormData();
    formData.append('file', file);
    
    const response = await this.apiService.upload<ApiResponse<SessionInfo>>('/upload', formData);
    return response.data as unknown as SessionInfo;
  }
  
  // 文件内容操作
  async getFileContent(
    sessionId: string, 
    filePath: string
  ): Promise<FileContent> {
    console.log('🔍 fileService: getFileContent called with:', { sessionId, filePath });
    
    try {
      console.log('🔍 fileService: Making API request to /files/content');
      const response = await this.apiService.get<FileContentResponse>('/files/content', {
        session_id: sessionId, 
        file_path: filePath 
      });
      
      console.log('✅ fileService: API response received:', response);
      
      return response as unknown as FileContent;
    } catch (error) {
      console.error('❌ fileService: getFileContent failed:', error);
      console.error('❌ fileService: Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText
      });
      throw error;
    }
  }
  
  async saveFileContent(
    sessionId: string,
    filePath: string,
    content: string,
    encoding: string = 'utf-8'
  ): Promise<void> {
    const response = await this.apiService.post<ApiResponse<void>>('/save-file', {
      session_id: sessionId,
      file_path: filePath,
      content,
      encoding
    });
    return response.data as unknown as void;
  }
  
  // 文件树和信息
  async getFileTree(sessionId: string): Promise<unknown> {
    // 后端返回格式: {success, file_tree, total_files, total_size}
    // 不是标准的ApiResponse格式，所以直接返回原始响应
    const response = await this.apiService.get(`/file-tree/${sessionId}`);
    return response;
  }
  
  async getFileInfo(sessionId: string, filePath: string): Promise<FileInfo> {
    const response = await this.apiService.get<FileInfo>('/files/info', {
      session_id: sessionId,
      file_path: filePath
    });
    return response as unknown as FileInfo;
  }
  
  // 搜索和替换
  async searchInFiles(sessionId: string, request: SearchRequest): Promise<SearchResponse> {
    const response = await this.apiService.post<SearchResponse>('/search', {
      session_id: sessionId,
      ...request
    });
    return response as unknown as SearchResponse;
  }
  
  async replaceInFile(sessionId: string, filePath: string, search: string, replace: string): Promise<ReplaceResponse> {
    const response = await this.apiService.post<ReplaceResponse>('/replace', {
      session_id: sessionId,
      file_path: filePath,
      search,
      replace
    });
    return response as unknown as ReplaceResponse;
  }
  
  // 导出功能
  async exportFile(sessionId: string, format: 'epub' | 'zip' | 'html', metadata?: BookMetadata): Promise<ExportResponse> {
    const response = await this.apiService.post<ExportResponse>('/export', {
      session_id: sessionId,
      format,
      metadata
    });
    return response as unknown as ExportResponse;
  }
  
  // 会话管理
  async checkSessionStatus(sessionId: string): Promise<{exists: boolean, status: string, message: string}> {
    try {
      const response = await this.apiService.get(`/sessions/${sessionId}/status`);
      return {
        exists: true,
        status: 'active',
        message: '会话存在'
      };
    } catch (error: unknown) {
      const axiosError = error as { response?: { status?: number } };
      if (axiosError.response?.status === 404) {
        return {
          exists: false,
          status: 'not_found',
          message: '会话不存在或已过期'
        };
      }
      throw error;
    }
  }

  async deleteSession(sessionId: string): Promise<void> {
    await this.apiService.delete(`/sessions/${sessionId}`);
  }
}

// 创建服务实例
export const fileService = new FileService(apiService);
export default FileService;