import { 
  LoginRequest, 
  RegisterRequest, 
  TokenResponse, 
  UserInfo, 
  CreateInvitationCodeRequest,
  InvitationCode,
  ChangePasswordRequest,
  ApiResponse,
  PaginatedResponse,
  InvitationCodeStats
} from '../types/auth';

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';

class AuthService {
  private getAuthHeaders(): HeadersInit {
    const token = localStorage.getItem('access_token');
    return {
      'Content-Type': 'application/json',
      ...(token && { 'Authorization': `Bearer ${token}` })
    };
  }

  private async handleResponse<T>(response: Response): Promise<ApiResponse<T>> {
    const data = await response.json();
    
    if (!response.ok) {
      return {
        success: false,
        error: data.error || data.message || data.detail || '请求失败',
        data: undefined as T
      };
    }
    
    return {
      success: true,
      data: data,
      error: undefined
    };
  }

  // 用户注册
  async register(data: RegisterRequest): Promise<ApiResponse<TokenResponse>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/register`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    return this.handleResponse<TokenResponse>(response);
  }

  // 用户登录
  async login(data: LoginRequest): Promise<ApiResponse<TokenResponse>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/login`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(data)
    });
    
    return this.handleResponse<TokenResponse>(response);
  }

  // 用户登出
  async logout(): Promise<ApiResponse<void>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/logout`, {
      method: 'POST',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<void>(response);
  }

  // 获取当前用户信息
  async getCurrentUser(): Promise<ApiResponse<UserInfo>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/me`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<UserInfo>(response);
  }

  // 刷新令牌
  async refreshToken(): Promise<ApiResponse<TokenResponse>> {
    const refreshToken = localStorage.getItem('refresh_token');
    
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${refreshToken}`
      }
    });
    
    return this.handleResponse<TokenResponse>(response);
  }

  // 修改密码
  async changePassword(data: ChangePasswordRequest): Promise<ApiResponse<{ message: string }>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/change-password`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data)
    });
    
    return this.handleResponse<{ message: string }>(response);
  }

  // 管理员功能 - 创建邀请码
  async createInvitationCode(data: CreateInvitationCodeRequest): Promise<ApiResponse<InvitationCode>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/invitation-codes`, {
      method: 'POST',
      headers: this.getAuthHeaders(),
      body: JSON.stringify(data)
    });
    
    return this.handleResponse<InvitationCode>(response);
  }

  // 管理员功能 - 获取邀请码列表
  async getInvitationCodes(page: number = 1, size: number = 20): Promise<ApiResponse<PaginatedResponse<InvitationCode>>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/invitation-codes?page=${page}&size=${size}`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<PaginatedResponse<InvitationCode>>(response);
  }

  // 管理员功能 - 获取邀请码统计
  async getInvitationCodeStats(): Promise<ApiResponse<InvitationCodeStats>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/invitation-codes/stats`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<InvitationCodeStats>(response);
  }

  // 管理员功能 - 删除邀请码
  async deleteInvitationCode(codeId: number): Promise<ApiResponse<{ message: string }>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/invitation-codes/${codeId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<{ message: string }>(response);
  }

  // 管理员功能 - 重新加载数据
  async reloadData(): Promise<ApiResponse<{ message: string }>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/reload-data`, {
      method: 'POST',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<{ message: string }>(response);
  }

  // 管理员功能 - 获取用户列表
  async getUsers(page: number = 1, size: number = 20): Promise<ApiResponse<PaginatedResponse<UserInfo>>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/users?page=${page}&size=${size}`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<PaginatedResponse<UserInfo>>(response);
  }

  // 管理员功能 - 删除用户
  async deleteUser(userId: number): Promise<ApiResponse<{ message: string }>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/users/${userId}`, {
      method: 'DELETE',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<{ message: string }>(response);
  }

  // 管理员功能 - 获取用户统计
  async getUserStats(): Promise<ApiResponse<{ total: number }>> {
    const response = await fetch(`${API_BASE_URL}/api/v1/auth/admin/users/stats`, {
      method: 'GET',
      headers: this.getAuthHeaders()
    });
    
    return this.handleResponse<{ total: number }>(response);
  }



  // 令牌管理
  setTokens(accessToken: string, refreshToken: string): void {
    localStorage.setItem('access_token', accessToken);
    localStorage.setItem('refresh_token', refreshToken);
  }

  clearTokens(): void {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
  }

  getAccessToken(): string | null {
    return localStorage.getItem('access_token');
  }

  getRefreshToken(): string | null {
    return localStorage.getItem('refresh_token');
  }

  // 检查令牌是否存在
  hasValidToken(): boolean {
    return !!this.getAccessToken();
  }
}

export const authService = new AuthService();
export default authService;