import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { 
  LoginRequest, 
  RegisterRequest, 
  ChangePasswordRequest,
  AuthState 
} from '../types/auth';
import { authService } from '../services/auth';

interface AuthStore extends AuthState {
  // Actions
  login: (credentials: LoginRequest) => Promise<void>;
  register: (data: RegisterRequest) => Promise<void>;
  logout: () => Promise<void>;
  refreshToken: () => Promise<void>;
  getCurrentUser: () => Promise<void>;
  changePassword: (data: ChangePasswordRequest) => Promise<void>;
  clearError: () => void;
  setLoading: (loading: boolean) => void;
  checkAuth: () => Promise<void>;
}

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      // Initial state
      isAuthenticated: false,
      user: null,
      token: null,
      refreshTokenValue: null,
      loading: false,
      error: null,

      // Actions
      login: async (credentials: LoginRequest) => {
        try {
          set({ loading: true, error: null });
          
          const response = await authService.login(credentials);
          
          // 后端直接返回 { access_token, token_type } 格式
          if (response.success && response.data) {
            const { access_token, refresh_token, user } = response.data;
            
            // 保存令牌
            authService.setTokens(access_token, refresh_token || '');
            
            set({
              isAuthenticated: true,
              user,
              token: access_token,
              refreshTokenValue: refresh_token || null,
              loading: false,
              error: null
            });
          } else {
            throw new Error(response.error || '登录失败');
          }
        } catch (error) {
          set({ 
            loading: false, 
            error: error instanceof Error ? error.message : '登录失败' 
          });
          throw error;
        }
      },

      register: async (data: RegisterRequest) => {
        try {
          set({ loading: true, error: null });
          
          const response = await authService.register(data);
          
          if (response.success && response.data) {
            const { access_token } = response.data;
            
            // 保存令牌
            authService.setTokens(access_token, '');
            
            // 获取用户信息
            try {
              const userResponse = await authService.getCurrentUser();
              if (userResponse.success && userResponse.data) {
                set({
                  isAuthenticated: true,
                  user: userResponse.data,
                  token: access_token,
                  refreshTokenValue: null,
                  loading: false,
                  error: null
                });
              } else {
                throw new Error(userResponse.error || '获取用户信息失败');
              }
            } catch (error) {
              // 即使获取用户信息失败，也认为注册成功
              console.warn('Failed to get user info after registration:', error);
              set({
                isAuthenticated: true,
                user: null,
                token: access_token,
                refreshTokenValue: null,
                loading: false,
                error: null
              });
            }
          } else {
            throw new Error(response.error || '注册失败');
          }
        } catch (error) {
          set({ 
            loading: false, 
            error: error instanceof Error ? error.message : '注册失败' 
          });
          throw error;
        }
      },

      logout: async () => {
        try {
          set({ loading: true });
          
          // 调用后端登出接口
          await authService.logout();
        } catch (error) {
          // 即使后端登出失败，也要清除本地状态
          console.error('Logout error:', error);
        } finally {
          // 清除令牌和状态
          authService.clearTokens();
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            refreshTokenValue: null,
            loading: false,
            error: null
          });
        }
      },

      refreshToken: async () => {
        try {
          const response = await authService.refreshToken();
          
          if (response.success && response.data) {
            const { access_token } = response.data;
            
            // 更新令牌
            authService.setTokens(access_token, '');
            
            // 获取用户信息
            try {
              const userResponse = await authService.getCurrentUser();
              
              if (userResponse.success && userResponse.data) {
                set({
                  isAuthenticated: true,
                  user: userResponse.data,
                  token: access_token,
                  refreshTokenValue: null,
                  error: null
                });
              } else {
                set({
                  isAuthenticated: true,
                  user: null,
                  token: access_token,
                  refreshTokenValue: null,
                  error: null
                });
              }
            } catch (error) {
              console.warn('Failed to get user info after token refresh:', error);
              set({
                isAuthenticated: true,
                user: null,
                token: access_token,
                refreshTokenValue: null,
                error: null
              });
            }
          } else {
            throw new Error(response.error || '令牌刷新失败');
          }
        } catch (error) {
          // 刷新失败，清除认证状态
          authService.clearTokens();
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            refreshTokenValue: null,
            error: error instanceof Error ? error.message : '令牌刷新失败'
          });
          throw error;
        }
      },

      getCurrentUser: async () => {
        try {
          set({ loading: true, error: null });
          
          const response = await authService.getCurrentUser();
          
          if (response.success && response.data) {
            set({
              user: response.data,
              loading: false
            });
          } else {
            throw new Error(response.error || '获取用户信息失败');
          }
        } catch (error) {
          set({ 
            loading: false, 
            error: error instanceof Error ? error.message : '获取用户信息失败' 
          });
          throw error;
        }
      },

      changePassword: async (data: ChangePasswordRequest) => {
        try {
          set({ loading: true, error: null });
          
          await authService.changePassword(data);
          set({ loading: false });
        } catch (error) {
          set({ 
            loading: false, 
            error: error instanceof Error ? error.message : '密码修改失败' 
          });
          throw error;
        }
      },

      clearError: () => {
        set({ error: null });
      },

      setLoading: (loading: boolean) => {
        set({ loading });
      },

      checkAuth: async () => {
        const token = authService.getAccessToken();
        
        if (!token) {
          set({
            isAuthenticated: false,
            user: null,
            token: null,
            refreshTokenValue: null
          });
          return;
        }

        try {
          // 尝试获取当前用户信息来验证令牌
          await get().getCurrentUser();
          
          set({
            isAuthenticated: true,
            token,
            refreshTokenValue: authService.getRefreshToken()
          });
        } catch (error) {
          // 令牌无效，尝试刷新
          console.warn('Token validation failed:', error);
          try {
            await get().refreshToken();
          } catch (refreshError) {
            // 刷新也失败，清除认证状态
            console.warn('Token refresh failed:', refreshError);
            authService.clearTokens();
            set({
              isAuthenticated: false,
              user: null,
              token: null,
              refreshTokenValue: null
            });
          }
        }
      }
    }),
    {
      name: 'auth-storage',
      partialize: (state) => ({
        isAuthenticated: state.isAuthenticated,
        user: state.user,
        token: state.token,
        refreshTokenValue: state.refreshTokenValue
      })
    }
  )
);

export default useAuthStore;