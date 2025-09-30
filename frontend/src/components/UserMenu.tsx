import React, { useState, useRef, useEffect } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { 
  User, 
  LogOut, 
  Settings, 
  Shield, 
  ChevronDown,
  Key,
  Users
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';

const UserMenu: React.FC = () => {
  const navigate = useNavigate();
  const { user, logout, loading } = useAuthStore();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  // 点击外部关闭菜单
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    };

    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  const handleLogout = async () => {
    try {
      await logout();
      navigate('/login');
    } catch (error) {
      console.error('Logout failed:', error);
      // 即使登出失败，也重定向到登录页
      navigate('/login');
    }
  };

  if (!user) {
    return null;
  }

  return (
    <div className="relative" ref={menuRef}>
      {/* 用户头像和名称按钮 */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="flex items-center space-x-3 px-3 py-2 rounded-lg hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
        disabled={loading}
      >
        {/* 用户头像 */}
        <div className="w-8 h-8 bg-emerald-500 rounded-full flex items-center justify-center">
          <User className="w-5 h-5 text-white" />
        </div>
        
        {/* 用户信息 */}
        <div className="flex items-center space-x-2">
          <div className="text-left">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user.username}
            </p>
            {user.is_admin && (
              <p className="text-xs text-emerald-600 dark:text-emerald-400 flex items-center space-x-1">
                <Shield className="w-3 h-3" />
                <span>管理员</span>
              </p>
            )}
          </div>
          <ChevronDown className={`w-4 h-4 text-gray-500 transition-transform ${
            isOpen ? 'rotate-180' : ''
          }`} />
        </div>
      </button>

      {/* 下拉菜单 */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white dark:bg-gray-800 rounded-lg shadow-lg border border-gray-200 dark:border-gray-700 py-2 z-50">
          {/* 用户信息头部 */}
          <div className="px-4 py-3 border-b border-gray-200 dark:border-gray-700">
            <p className="text-sm font-medium text-gray-900 dark:text-white">
              {user.username}
            </p>
            <p className="text-xs text-gray-500 dark:text-gray-400">
              {user.is_admin ? '管理员账户' : '普通用户'}
            </p>
            {user.last_login && (
              <p className="text-xs text-gray-500 dark:text-gray-400 mt-1">
                上次登录: {new Date(user.last_login).toLocaleString()}
              </p>
            )}
          </div>

          {/* 菜单项 */}
          <div className="py-1">
            {/* 修改密码 */}
            <Link
              to="/profile/change-password"
              className="flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <Key className="w-4 h-4" />
              <span>修改密码</span>
            </Link>

            {/* 个人设置 */}
            <Link
              to="/profile/settings"
              className="flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
              onClick={() => setIsOpen(false)}
            >
              <Settings className="w-4 h-4" />
              <span>个人设置</span>
            </Link>

            {/* 管理员专用菜单 */}
            {user.is_admin && (
              <Link
                to="/admin/users"
                className="flex items-center space-x-3 px-4 py-2 text-sm text-gray-700 dark:text-gray-300 hover:bg-gray-100 dark:hover:bg-gray-700 transition-colors"
                onClick={() => setIsOpen(false)}
              >
                <Users className="w-4 h-4" />
                <span>用户管理</span>
              </Link>
            )}
          </div>

          {/* 分隔线 */}
          <div className="border-t border-gray-200 dark:border-gray-700 my-1" />

          {/* 登出 */}
          <button
            onClick={handleLogout}
            disabled={loading}
            className="w-full flex items-center space-x-3 px-4 py-2 text-sm text-red-600 dark:text-red-400 hover:bg-red-50 dark:hover:bg-red-900/20 transition-colors disabled:opacity-50"
          >
            {loading ? (
              <div className="w-4 h-4 border-2 border-red-600 border-t-transparent rounded-full animate-spin" />
            ) : (
              <LogOut className="w-4 h-4" />
            )}
            <span>{loading ? '登出中...' : '登出'}</span>
          </button>
        </div>
      )}
    </div>
  );
};

export default UserMenu;