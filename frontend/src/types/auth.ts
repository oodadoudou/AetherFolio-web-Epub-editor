// 用户相关类型
export interface User {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  last_login?: string;
  failed_login_attempts: number;
  locked_until?: string;
}

// 登录请求
export interface LoginRequest {
  username: string;
  password: string;
}

// 注册请求
export interface RegisterRequest {
  username: string;
  password: string;
  invitation_code: string;
}

// 令牌响应
export interface TokenResponse {
  access_token: string;
  refresh_token: string;
  token_type: string;
  expires_in: number;
  user: User;
}

// 用户信息响应
export interface UserInfo {
  id: number;
  username: string;
  is_admin: boolean;
  created_at: string;
  last_login?: string;
  failed_login_attempts: number;
}

// 邀请码信息
export interface InvitationCode {
  id: number;
  code: string;
  created_by: number;
  created_at: string;
  expires_at?: string;
  usage_limit?: number;
  used_count: number;
  is_active: boolean;
}

// 创建邀请码请求
export interface CreateInvitationCodeRequest {
  expiration_days?: number;
  usage_limit?: number;
}

// 修改密码请求
export interface ChangePasswordRequest {
  current_password: string;
  new_password: string;
}



// 认证状态
export interface AuthState {
  isAuthenticated: boolean;
  user: User | null;
  token: string | null;
  refreshTokenValue: string | null;
  loading: boolean;
  error: string | null;
}

// API响应基础类型
export interface ApiResponse<T = unknown> {
  success: boolean;
  data?: T;
  error?: string;
  message?: string;
}

// 分页响应
export interface PaginatedResponse<T> {
  items: T[];
  total: number;
  page: number;
  size: number;
  pages: number;
}

// 邀请码统计
export interface InvitationCodeStats {
  total_codes: number;
  active_codes: number;
  expired_codes: number;
  used_codes: number;
}