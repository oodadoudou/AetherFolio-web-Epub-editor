import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Key, ArrowLeft, Eye, EyeOff } from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { toast } from 'sonner';

const ChangePassword: React.FC = () => {
  const navigate = useNavigate();
  const { changePassword, loading } = useAuthStore();
  const [formData, setFormData] = useState({
    current_password: '',
    new_password: '',
    confirm_password: ''
  });
  const [showPasswords, setShowPasswords] = useState({
    current: false,
    new: false,
    confirm: false
  });
  const [errors, setErrors] = useState<Record<string, string>>({});

  const validateForm = () => {
    const newErrors: Record<string, string> = {};

    if (!formData.current_password) {
      newErrors.current_password = '请输入当前密码';
    }

    if (!formData.new_password) {
      newErrors.new_password = '请输入新密码';
    } else if (formData.new_password.length < 6) {
      newErrors.new_password = '新密码至少需要6个字符';
    }

    if (!formData.confirm_password) {
      newErrors.confirm_password = '请确认新密码';
    } else if (formData.new_password !== formData.confirm_password) {
      newErrors.confirm_password = '两次输入的密码不一致';
    }

    if (formData.current_password === formData.new_password) {
      newErrors.new_password = '新密码不能与当前密码相同';
    }

    setErrors(newErrors);
    return Object.keys(newErrors).length === 0;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (!validateForm()) {
      return;
    }

    try {
      await changePassword({
        current_password: formData.current_password,
        new_password: formData.new_password
      });
      
      toast.success('密码修改成功，请重新登录');
      
      // 延迟跳转，让用户看到成功提示
      setTimeout(() => {
        navigate(-1);
      }, 1500);
      
    } catch (error) {
      console.error('Change password error:', error);
      
      let errorMessage = '密码修改失败';
      
      // 处理不同类型的错误
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'object' && error !== null) {
        const apiError = error as { response?: { data?: { message?: string; detail?: string } }; message?: string };
        if (apiError.response?.data?.message) {
          errorMessage = apiError.response.data.message;
        } else if (apiError.response?.data?.detail) {
          errorMessage = apiError.response.data.detail;
        } else if (apiError.message) {
          errorMessage = apiError.message;
        }
      }
      
      // 根据错误类型提供更具体的提示
      if (errorMessage.includes('当前密码错误') || errorMessage.includes('current password')) {
        setErrors({ current_password: '当前密码错误，请重新输入' });
        toast.error('当前密码错误');
      } else if (errorMessage.includes('新密码不能与当前密码相同')) {
        setErrors({ new_password: '新密码不能与当前密码相同' });
        toast.error('新密码不能与当前密码相同');
      } else if (errorMessage.includes('密码至少需要') || errorMessage.includes('password')) {
        setErrors({ new_password: '新密码格式不符合要求' });
        toast.error('新密码格式不符合要求');
      } else if (errorMessage.includes('网络') || errorMessage.includes('Failed to fetch')) {
        toast.error('网络连接失败，请检查网络后重试');
      } else {
        toast.error(errorMessage);
      }
    }
  };

  const handleInputChange = (field: string, value: string) => {
    setFormData(prev => ({ ...prev, [field]: value }));
    // 清除对应字段的错误
    if (errors[field]) {
      setErrors(prev => ({ ...prev, [field]: '' }));
    }
  };

  const togglePasswordVisibility = (field: 'current' | 'new' | 'confirm') => {
    setShowPasswords(prev => ({ ...prev, [field]: !prev[field] }));
  };

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900 py-8">
      <div className="max-w-2xl mx-auto px-4 sm:px-6 lg:px-8">
        {/* 头部 */}
        <div className="mb-8">
          <button
            onClick={() => navigate(-1)}
            className="flex items-center space-x-2 text-gray-600 dark:text-gray-400 hover:text-gray-900 dark:hover:text-white transition-colors mb-4"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>返回</span>
          </button>
          
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 bg-emerald-500 rounded-lg flex items-center justify-center">
              <Key className="w-5 h-5 text-white" />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                修改密码
              </h1>
              <p className="text-gray-600 dark:text-gray-400">
                为了账户安全，请定期更新您的密码
              </p>
            </div>
          </div>
        </div>

        {/* 表单 */}
        <div className="bg-white dark:bg-gray-800 rounded-lg shadow-sm border border-gray-200 dark:border-gray-700">
          <form onSubmit={handleSubmit} className="p-6 space-y-6">
            {/* 当前密码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                当前密码
              </label>
              <div className="relative">
                <input
                  type={showPasswords.current ? 'text' : 'password'}
                  value={formData.current_password}
                  onChange={(e) => handleInputChange('current_password', e.target.value)}
                  className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                    errors.current_password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="请输入当前密码"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('current')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPasswords.current ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.current_password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.current_password}
                </p>
              )}
            </div>

            {/* 新密码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                新密码
              </label>
              <div className="relative">
                <input
                  type={showPasswords.new ? 'text' : 'password'}
                  value={formData.new_password}
                  onChange={(e) => handleInputChange('new_password', e.target.value)}
                  className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                    errors.new_password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="请输入新密码（至少6个字符）"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('new')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPasswords.new ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.new_password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.new_password}
                </p>
              )}
            </div>

            {/* 确认新密码 */}
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                确认新密码
              </label>
              <div className="relative">
                <input
                  type={showPasswords.confirm ? 'text' : 'password'}
                  value={formData.confirm_password}
                  onChange={(e) => handleInputChange('confirm_password', e.target.value)}
                  className={`w-full px-3 py-2 pr-10 border rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:border-gray-600 dark:text-white ${
                    errors.confirm_password ? 'border-red-500' : 'border-gray-300'
                  }`}
                  placeholder="请再次输入新密码"
                />
                <button
                  type="button"
                  onClick={() => togglePasswordVisibility('confirm')}
                  className="absolute right-3 top-1/2 transform -translate-y-1/2 text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                >
                  {showPasswords.confirm ? <EyeOff className="w-4 h-4" /> : <Eye className="w-4 h-4" />}
                </button>
              </div>
              {errors.confirm_password && (
                <p className="mt-1 text-sm text-red-600 dark:text-red-400">
                  {errors.confirm_password}
                </p>
              )}
            </div>

            {/* 安全提示 */}
            <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 rounded-lg p-4">
              <h3 className="text-sm font-medium text-blue-800 dark:text-blue-200 mb-2">
                密码安全建议
              </h3>
              <ul className="text-sm text-blue-700 dark:text-blue-300 space-y-1">
                <li>• 使用至少8个字符的密码</li>
                <li>• 包含大小写字母、数字和特殊字符</li>
                <li>• 避免使用个人信息或常见词汇</li>
                <li>• 定期更换密码以确保账户安全</li>
              </ul>
            </div>

            {/* 按钮 */}
            <div className="flex justify-end space-x-4 pt-4">
              <button
                type="button"
                onClick={() => navigate(-1)}
                className="px-4 py-2 text-gray-700 dark:text-gray-300 bg-gray-100 dark:bg-gray-700 rounded-lg hover:bg-gray-200 dark:hover:bg-gray-600 transition-colors"
              >
                取消
              </button>
              <button
                type="submit"
                disabled={loading}
                className="px-6 py-2 bg-emerald-600 text-white rounded-lg hover:bg-emerald-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center space-x-2"
              >
                {loading && (
                  <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                <span>{loading ? '修改中...' : '修改密码'}</span>
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>
  );
};

export default ChangePassword;