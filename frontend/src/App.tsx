import React, { useEffect } from 'react';
import { Routes, Route } from 'react-router-dom';
import { theme, App as AntdApp } from 'antd';
import { Toaster } from 'sonner';

import Home from './pages/Home';
import Editor from './pages/Editor';
import Login from './pages/Login';
import Register from './pages/Register';
import Settings from './pages/Settings';
import ChangePassword from './pages/ChangePassword';
import AdminPanel from './pages/AdminPanel';
import ProtectedRoute from './components/ProtectedRoute';
import useAppStore from './store/useAppStore';
import { useAuthStore } from './store/authStore';
// import { fileService } from './services/file';

import './App.css';

// Trae Light theme configuration - Green Theme
const traeLightTheme = {
  token: {
    colorPrimary: '#10b981', // Green-500 (主绿色)
    colorSuccess: '#059669', // Emerald-600
    colorWarning: '#d97706', // Amber-600
    colorError: '#dc2626',   // Red-600
    colorInfo: '#10b981',    // Green-500 (改为绿色)
    colorBgBase: '#ffffff',  // White
    colorBgContainer: '#f8fafc', // Slate-50
    colorBorder: '#e2e8f0',  // Slate-200
    colorText: '#1e293b',    // Slate-800
    colorTextSecondary: '#64748b', // Slate-500
    borderRadius: 8,
    fontSize: 14,
  },
};

// Trae Dark theme configuration - 基于截图配色
const traeDarkTheme = {
  token: {
    colorPrimary: '#22c55e', // 绿色高亮 (Green-500)
    colorSuccess: '#16a34a', // Green-600
    colorWarning: '#f59e0b', // Amber-500
    colorError: '#ef4444',   // Red-500
    colorInfo: '#22c55e',    // Green-500
    colorBgBase: '#1a1a1a',  // 深灰色背景 (类似截图)
    colorBgContainer: '#2d2d2d', // 稍浅的灰色容器
    colorBorder: '#404040',  // 边框颜色
    colorText: '#e5e5e5',    // 浅色文字
    colorTextSecondary: '#a3a3a3', // 次要文字颜色
    colorBgLayout: '#1a1a1a', // 布局背景
    colorBgElevated: '#333333', // 悬浮元素背景
    colorFillSecondary: '#2d2d2d', // 二级填充色
    colorFillTertiary: '#404040', // 三级填充色
    borderRadius: 6,
    fontSize: 14,
  },
  algorithm: theme.darkAlgorithm,
};

function App() {
  const {
    isDarkMode,
    toggleTheme,
  } = useAppStore();
  
  const { checkAuth } = useAuthStore();

  // 应用启动时检查认证状态
  useEffect(() => {
    checkAuth();
  }, [checkAuth]);

  // 会话管理和清理
  useEffect(() => {
    // 页面卸载时的清理逻辑（仅在真正关闭浏览器时执行）
    const handleBeforeUnload = () => {
      // 不在这里删除会话，因为用户可能只是刷新页面或切换标签
      // 会话应该由服务器端的过期机制或用户主动操作来管理
      console.log('Page unloading, but keeping session alive');
    };

    // 监听页面卸载事件
    window.addEventListener('beforeunload', handleBeforeUnload);

    // 清理事件监听器
    return () => {
      window.removeEventListener('beforeunload', handleBeforeUnload);
    };
  }, []);

  return (
    <>
      <Toaster 
        position="top-right" 
        richColors 
        closeButton 
        theme={isDarkMode ? 'dark' : 'light'}
      />
      <AntdApp>
        <Routes>
      {/* 公开路由 */}
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      
      {/* 受保护的路由 */}
      <Route 
        path="/" 
        element={
          <ProtectedRoute>
            <Home 
              isDarkMode={isDarkMode}
              traeDarkTheme={traeDarkTheme}
              traeLightTheme={traeLightTheme}
            />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/editor/:sessionId" 
        element={
          <ProtectedRoute>
            <Editor 
              isDarkMode={isDarkMode}
              traeDarkTheme={traeDarkTheme}
              traeLightTheme={traeLightTheme}
              onThemeToggle={toggleTheme}
            />
          </ProtectedRoute>
        } 
      />
      
      {/* 用户个人页面路由 */}
      <Route 
        path="/profile/settings" 
        element={
          <ProtectedRoute>
            <Settings />
          </ProtectedRoute>
        } 
      />
      <Route 
        path="/profile/change-password" 
        element={
          <ProtectedRoute>
            <ChangePassword />
          </ProtectedRoute>
        } 
      />
      
      {/* 管理员页面路由 */}
      <Route 
        path="/admin/users" 
        element={
          <ProtectedRoute requireAdmin={true}>
            <AdminPanel />
          </ProtectedRoute>
        } 
      />
      

        </Routes>
      </AntdApp>
    </>
  );
}

export default App;