// 预览服务

import { ApiService, apiService } from './api';

interface PreviewResponse {
  success: boolean;
  html: string;
  file_path: string;
}

interface PreviewStatusResponse {
  success: boolean;
  cache_size: number;
  cache_hits: number;
  cache_misses: number;
}

class PreviewService {
  constructor(private apiService: ApiService) {}
  
  /**
   * 获取文件预览HTML
   */
  async getPreview(
    sessionId: string, 
    filePath: string
  ): Promise<PreviewResponse> {
    console.log('🔍 previewService: getPreview called with:', { sessionId, filePath });
    
    try {
      console.log('🔍 previewService: Making API request to /preview');
      const data = await this.apiService.get<PreviewResponse>('/preview', {
        session_id: sessionId, 
        file_path: filePath 
      });
      
      console.log('✅ previewService: API response received:', data);
      
      return data;
    } catch (error) {
      console.error('❌ previewService: getPreview failed:', error);
      console.error('❌ previewService: Error details:', {
        message: error.message,
        response: error.response?.data,
        status: error.response?.status,
        statusText: error.response?.statusText
      });
      throw error;
    }
  }
  
  /**
   * 获取预览服务状态
   */
  async getPreviewStatus(sessionId: string): Promise<PreviewStatusResponse> {
    try {
      const data = await this.apiService.get<PreviewStatusResponse>('/preview/status', {
        session_id: sessionId
      });
      
      return data;
    } catch (error) {
      console.error('❌ previewService: getPreviewStatus failed:', error);
      throw error;
    }
  }
  
  /**
   * 清除预览缓存
   */
  async clearPreviewCache(sessionId: string): Promise<{ success: boolean; message: string }> {
    try {
      const data = await this.apiService.delete(`/preview/cache?session_id=${sessionId}`);
      
      return {
        success: true,
        message: '缓存清除成功'
      };
    } catch (error) {
      console.error('❌ previewService: clearPreviewCache failed:', error);
      throw error;
    }
  }
}

// 创建服务实例
export const previewService = new PreviewService(apiService);
export default PreviewService;