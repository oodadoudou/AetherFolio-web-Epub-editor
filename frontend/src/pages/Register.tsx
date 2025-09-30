import React, { useState, useEffect } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { Eye, EyeOff, UserPlus, LogIn, Key } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { RegisterRequest } from '../types/auth';

const Register: React.FC = () => {
  const navigate = useNavigate();
  const { register, loading, error, clearError, isAuthenticated } = useAuthStore();
  
  const [formData, setFormData] = useState<RegisterRequest>({
    username: '',
    password: '',
    invitation_code: ''
  });
  const [showPassword, setShowPassword] = useState(false);
  const [confirmPassword, setConfirmPassword] = useState('');
  const [formErrors, setFormErrors] = useState<Partial<RegisterRequest & { confirmPassword: string }>>({});

  // 如果已经登录，重定向到首页
  useEffect(() => {
    if (isAuthenticated) {
      navigate('/', { replace: true });
    }
  }, [isAuthenticated, navigate]);

  // 清除错误信息
  useEffect(() => {
    return () => {
      clearError();
    };
  }, [clearError]);

  const validateForm = (): boolean => {
    const errors: Partial<RegisterRequest & { confirmPassword: string }> = {};
    
    // 用户名验证
    if (!formData.username.trim()) {
      errors.username = '请输入用户名';
    } else if (formData.username.length < 3) {
      errors.username = '用户名至少需要3个字符';
    } else if (formData.username.length > 50) {
      errors.username = '用户名不能超过50个字符';
    } else if (!/^[a-zA-Z0-9_-]+$/.test(formData.username)) {
      errors.username = '用户名只能包含字母、数字、下划线和连字符';
    }
    
    // 密码验证
    if (!formData.password) {
      errors.password = '请输入密码';
    } else if (formData.password.length < 8) {
      errors.password = '密码至少需要8个字符';
    }
    
    // 确认密码验证
    if (!confirmPassword) {
      errors.confirmPassword = '请确认密码';
    } else if (confirmPassword !== formData.password) {
      errors.confirmPassword = '两次输入的密码不一致';
    }
    
    // 邀请码验证
    if (!formData.invitation_code.trim()) {
      errors.invitation_code = '请输入邀请码';
    }
    
    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      await register(formData);
      // 注册成功后会通过useEffect重定向
    } catch {
      // 错误已经在store中处理
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const { name, value } = e.target;
    
    if (name === 'confirmPassword') {
      setConfirmPassword(value);
    } else {
      setFormData(prev => ({ ...prev, [name]: value }));
    }
    
    // 清除对应字段的错误
    if (formErrors[name as keyof (RegisterRequest & { confirmPassword: string })]) {
      setFormErrors(prev => ({ ...prev, [name]: undefined }));
    }
    
    // 清除全局错误
    if (error) {
      clearError();
    }
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-emerald-50 to-teal-100 dark:from-gray-900 dark:to-gray-800 flex items-center justify-center p-4">
      <div className="w-full max-w-md">
        {/* Logo和标题 */}
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-emerald-500 rounded-full mb-4">
            <UserPlus className="w-8 h-8 text-white" />
          </div>
          <h1 className="text-3xl font-bold text-gray-900 dark:text-white mb-2">
            AetherFolio
          </h1>
          <p className="text-gray-600 dark:text-gray-400">
            创建您的账户
          </p>
        </div>

        {/* 注册表单 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-xl p-8">
          <form onSubmit={handleSubmit} className="space-y-6">
            {/* 全局错误信息 */}
            {error && (
              <div className="bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
                <p className="text-red-600 dark:text-red-400 text-sm">{error}</p>
              </div>
            )}

            {/* 用户名输入 */}
            <div>
              <label htmlFor="username" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                用户名
              </label>
              <input
                type="text"
                id="username"
                name="username"
                value={formData.username}
                onChange={handleInputChange}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors ${
                  formErrors.username ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="请输入用户名（3-50个字符）"
                disabled={loading}
              />
              {formErrors.username && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{formErrors.username}</p>
              )}
            </div>

            {/* 密码输入 */}
            <div>
              <label htmlFor="password" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                密码
              </label>
              <div className="relative">
                <input
                  type={showPassword ? 'text' : 'password'}
                  id="password"
                  name="password"
                  value={formData.password}
                  onChange={handleInputChange}
                  className={`w-full px-4 py-3 pr-12 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors ${
                    formErrors.password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="请输入密码（至少8个字符）"
                  disabled={loading}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                  disabled={loading}
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
              {formErrors.password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{formErrors.password}</p>
              )}
            </div>

            {/* 确认密码输入 */}
            <div>
              <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                确认密码
              </label>
              <input
                type={showPassword ? 'text' : 'password'}
                id="confirmPassword"
                name="confirmPassword"
                value={confirmPassword}
                onChange={handleInputChange}
                className={`w-full px-4 py-3 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors ${
                  formErrors.confirmPassword ? 'border-red-500' : 'border-gray-300'
                }`}
                placeholder="请再次输入密码"
                disabled={loading}
              />
              {formErrors.confirmPassword && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{formErrors.confirmPassword}</p>
              )}
            </div>

            {/* 邀请码输入 */}
            <div>
              <label htmlFor="invitation_code" className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                邀请码
              </label>
              <div className="relative">
                <input
                  type="text"
                  id="invitation_code"
                  name="invitation_code"
                  value={formData.invitation_code}
                  onChange={handleInputChange}
                  className={`w-full px-4 py-3 pl-12 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white transition-colors ${
                    formErrors.invitation_code ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="请输入邀请码"
                  disabled={loading}
                />
                <Key className="absolute left-3 top-1/2 transform -translate-y-1/2 w-5 h-5 text-gray-400" />
              </div>
              {formErrors.invitation_code && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">{formErrors.invitation_code}</p>
              )}
            </div>

            {/* 注册按钮 */}
            <button
              type="submit"
              disabled={loading}
              className="w-full bg-emerald-500 hover:bg-emerald-600 disabled:bg-emerald-300 text-white font-medium py-3 px-4 rounded-lg transition-colors flex items-center justify-center space-x-2"
            >
              {loading ? (
                <>
                  <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  <span>注册中...</span>
                </>
              ) : (
                <>
                  <UserPlus className="w-5 h-5" />
                  <span>注册</span>
                </>
              )}
            </button>
          </form>

          {/* 登录链接 */}
          <div className="mt-6 text-center">
            <p className="text-gray-600 dark:text-gray-400">
              已有账户？{' '}
              <Link 
                to="/login" 
                className="text-emerald-500 hover:text-emerald-600 font-medium inline-flex items-center space-x-1"
              >
                <LogIn className="w-4 h-4" />
                <span>立即登录</span>
              </Link>
            </p>
          </div>
        </div>

        {/* 底部信息 */}
        <div className="text-center mt-8">
          <p className="text-sm text-gray-500 dark:text-gray-400">
            © 2024 AetherFolio. 专业的EPUB编辑器
          </p>
        </div>
      </div>
    </div>
  );
};

export default Register;