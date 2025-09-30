// 会话服务

import { ApiService, apiService } from './api';
import { 
  ExtendSessionRequest, 
  ExtendSessionResponse
} from './types/session';

class SessionService {
  constructor(private apiService: ApiService) {}
    
  async extendSession(sessionId: string, request: ExtendSessionRequest): Promise<ExtendSessionResponse> {
    const response = await this.apiService.put<ExtendSessionResponse>(`/sessions/${sessionId}/extend`, request);
    return response as unknown as ExtendSessionResponse;
  }
  
  async deleteSession(sessionId: string): Promise<void> {
    try {
      // 实际删除逻辑可以在这里实现
      console.log('Session deletion requested for:', sessionId);
    } catch (error) {
      console.error('Failed to delete session:', error);
      throw error;
    }
  }
  
  // 会话验证（简化版本）
  async isSessionValid(sessionId: string): Promise<boolean> {
    // 简化的会话验证，只检查sessionId格式
    return sessionId && sessionId.length > 0;
  }
  
  // 历史会话管理功能已移除
  
  // 自动化功能
  async autoExtendSession(sessionId: string, thresholdMinutes: number, extendMinutes: number): Promise<boolean> {
    const remainingTime = await this.getSessionRemainingTime();
    
    if (remainingTime <= thresholdMinutes) {
      try {
        await this.extendSession(sessionId, { extend_minutes: extendMinutes });
        return true;
      } catch {
        return false;
      }
    }
    
    return false;
  }
  
  async getSessionRemainingTime(): Promise<number> {
    // 历史会话管理功能已移除，返回默认值
    return 9999; // 默认60分钟
  }
}

// 创建服务实例
export const sessionService = new SessionService(apiService);
export default SessionService;