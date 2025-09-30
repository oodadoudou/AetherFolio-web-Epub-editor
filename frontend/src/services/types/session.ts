// 会话相关类型定义（简化版本）

import { SessionStatus } from './common';

// 基本会话信息（历史会话管理功能已移除）
export interface SessionInfo {
  session_id: string;
  status: SessionStatus;
}

// 会话扩展请求
export interface ExtendSessionRequest {
  extend_minutes?: number;
}

// 会话扩展响应
export interface ExtendSessionResponse {
  session_id: string;
  new_expires_at: string;
  extended_minutes: number;
}

// 历史会话管理相关类型已移除