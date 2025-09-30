import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { 
  Users, 
  Shield,
  Plus,
  Key,
  Trash2,
  Copy,
  ArrowLeft
} from 'lucide-react';
import { useAuthStore } from '../store/authStore';
import { authService } from '../services/auth';
import { 
  UserInfo,
  PaginatedResponse,
  InvitationCode,
  CreateInvitationCodeRequest
} from '../types/auth';
import { toast } from 'sonner';

const AdminPanel: React.FC = () => {
  const { user } = useAuthStore();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 用户管理状态
  const [users, setUsers] = useState<PaginatedResponse<UserInfo> | null>(null);
  const [userPage] = useState(1);

  // 邀请码管理状态
  const [invitations, setInvitations] = useState<PaginatedResponse<InvitationCode> | null>(null);
  const [invitationPage] = useState(1);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [createForm, setCreateForm] = useState<CreateInvitationCodeRequest>({
    expiration_days: 30,
    usage_limit: 1
  });





  // 加载用户列表
  const loadUsers = async (page: number = 1) => {
    try {
      setLoading(true);
      console.log('开始加载用户列表, page:', page);
      console.log('当前token:', authService.getAccessToken());
      
      const response = await authService.getUsers(page, 20);
      
      console.log('用户API响应:', response);
      
      if (response.success && response.data) {
        console.log('用户数据:', response.data);
        setUsers(response.data);
        setError(null); // 清除错误
      } else {
        console.error('用户加载失败:', response.error);
        setError(response.error || '加载用户列表失败');
      }
    } catch (err) {
      console.error('用户加载异常:', err);
      setError(err instanceof Error ? err.message : '加载用户列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 加载邀请码列表
  const loadInvitations = async (page: number = 1) => {
    try {
      setLoading(true);
      console.log('开始加载邀请码列表, page:', page);
      console.log('当前token:', authService.getAccessToken());
      
      const response = await authService.getInvitationCodes(page, 20);
      
      console.log('邀请码API响应:', response);
      
      if (response.success && response.data) {
        console.log('邀请码数据:', response.data);
        setInvitations(response.data);
        setError(null); // 清除错误
      } else {
        console.error('邀请码加载失败:', response.error);
        setError(response.error || '加载邀请码列表失败');
      }
    } catch (err) {
      console.error('邀请码加载异常:', err);
      setError(err instanceof Error ? err.message : '加载邀请码列表失败');
    } finally {
      setLoading(false);
    }
  };

  // 创建邀请码
  const handleCreateInvitation = async () => {
    try {
      setLoading(true);
      const response = await authService.createInvitationCode(createForm);
      if (response.success) {
        toast.success('邀请码创建成功');
        setShowCreateForm(false);
        setCreateForm({ expiration_days: 30, usage_limit: 1 });
        await loadInvitations(invitationPage);
      } else {
        toast.error(response.error || '创建邀请码失败');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '创建邀请码失败');
    } finally {
      setLoading(false);
    }
  };

  // 删除邀请码
  const handleDeleteInvitation = async (codeId: number) => {
    try {
      setLoading(true);
      const response = await authService.deleteInvitationCode(codeId);
      if (response.success) {
        toast.success('邀请码删除成功');
        await loadInvitations(invitationPage);
      } else {
        toast.error(response.error || '删除邀请码失败');
      }
    } catch (err) {
      toast.error(err instanceof Error ? err.message : '删除邀请码失败');
    } finally {
      setLoading(false);
    }
  };

  // 复制邀请码
  const handleCopyCode = async (code: string) => {
    try {
      await navigator.clipboard.writeText(code);
      toast.success('邀请码已复制到剪贴板');
    } catch {
      toast.error('复制失败');
    }
  };

  // 删除用户
  const handleDeleteUser = async (userId: number, username: string) => {
    
    try {
      setLoading(true);
      const response = await authService.deleteUser(userId);
      
      if (response.success) {
        toast.success(`用户 "${username}" 删除成功`);
        // 重新加载用户列表
        await loadUsers(userPage);
      } else {
        console.error('Delete user error:', response.error);
        
        let errorMessage = response.error || '删除用户失败';
        
        // 根据错误类型提供更具体的提示
        if (errorMessage.includes('用户不存在') || errorMessage.includes('not found')) {
          errorMessage = '用户不存在或已被删除';
        } else if (errorMessage.includes('不能删除管理员') || errorMessage.includes('admin')) {
          errorMessage = '不能删除管理员账户';
        } else if (errorMessage.includes('不能删除自己') || errorMessage.includes('yourself')) {
          errorMessage = '不能删除自己的账户';
        } else if (errorMessage.includes('权限') || errorMessage.includes('permission')) {
          errorMessage = '没有权限执行此操作';
        } else if (errorMessage.includes('网络') || errorMessage.includes('Failed to fetch')) {
          errorMessage = '网络连接失败，请检查网络后重试';
        }
        
        toast.error(errorMessage);
      }
    } catch (error) {
      console.error('Delete user exception:', error);
      
      let errorMessage = '删除用户失败';
      
      // 处理异常情况
      if (error instanceof Error) {
        errorMessage = error.message;
      } else if (typeof error === 'object' && error !== null) {
        const apiError = error as { response?: { data?: { message?: string; detail?: string } }; message?: string };
        if (apiError.response?.data?.message) {
          errorMessage = apiError.response.data.message;
        } else if (apiError.response?.data?.detail) {
          errorMessage = apiError.response.data.detail;
        }
      }
      
      // 根据错误类型提供友好提示
      if (errorMessage.includes('网络') || errorMessage.includes('Failed to fetch')) {
        toast.error('网络连接失败，请检查网络连接后重试');
      } else if (errorMessage.includes('权限') || errorMessage.includes('403')) {
        toast.error('没有权限执行此操作');
      } else if (errorMessage.includes('服务器') || errorMessage.includes('500')) {
        toast.error('服务器错误，请稍后重试');
      } else {
        toast.error(`删除用户失败：${errorMessage}`);
      }
    } finally {
      setLoading(false);
    }
  };

  // 加载数据
  useEffect(() => {
    console.log('AdminPanel useEffect triggered');
    console.log('User state:', user);
    console.log('User is_admin:', user?.is_admin);
    console.log('Current token:', localStorage.getItem('access_token'));
    console.log('Auth service token:', authService.getAccessToken());
    
    // 检查是否有token
    const token = authService.getAccessToken();
    if (!token) {
      console.log('No token found, user needs to login');
      setError('请先登录');
      return;
    }
    
    // 如果用户信息还在加载中，等待加载完成
    // 注意：ProtectedRoute已经处理了认证检查，这里用户应该已经加载完成
    if (user === null) {
      console.log('User not loaded yet, waiting...');
      return;
    }
    
    // 检查用户是否为管理员
    if (user && !user.is_admin) {
      console.log('User is not admin:', user);
      setError('您没有管理员权限');
      return;
    }
    
    // 用户是管理员，加载数据
    if (user?.is_admin) {
      console.log('Loading data for admin user:', user.username);
      setError(null); // 清除之前的错误
      loadUsers(userPage);
      loadInvitations(invitationPage);
    }
  }, [userPage, invitationPage, user]);

  // 添加一个单独的useEffect来处理初始数据加载
  useEffect(() => {
    // 当组件挂载时，如果用户已经是管理员，立即加载数据
    if (user?.is_admin) {
      console.log('Initial data load for admin user');
      loadUsers(1);
      loadInvitations(1);
    }
  }, [user?.is_admin]); // 只依赖于is_admin状态

  // 检查管理员权限
  if (!user?.is_admin) {
    return (
      <div className="min-h-screen bg-gray-50 dark:bg-gray-900 flex items-center justify-center">
        <div className="text-center">
          <Shield className="w-16 h-16 text-red-500 mx-auto mb-4" />
          <h2 className="text-2xl font-bold text-gray-900 dark:text-white mb-2">
            访问被拒绝
          </h2>
          <p className="text-gray-600 dark:text-gray-400">
            您没有管理员权限
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 dark:bg-gray-900">
      {/* 头部 */}
      <div className="bg-white dark:bg-gray-800 shadow">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
          <div className="flex items-center justify-between h-16">
            <div className="flex items-center space-x-4">
              <button
                onClick={() => navigate('/')}
                className="flex items-center space-x-2 px-3 py-2 text-gray-600 dark:text-gray-300 hover:text-emerald-600 dark:hover:text-emerald-400 hover:bg-gray-100 dark:hover:bg-gray-700 rounded-lg transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
                <span className="text-sm font-medium">返回主页</span>
              </button>
              <div className="h-6 w-px bg-gray-300 dark:bg-gray-600"></div>
              <Shield className="w-8 h-8 text-emerald-500" />
              <h1 className="text-2xl font-bold text-gray-900 dark:text-white">
                管理面板
              </h1>
            </div>
          </div>
        </div>
      </div>

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
        {/* 错误提示 */}
        {error && (
          <div className="mb-6 bg-red-50 dark:bg-red-900/20 border border-red-200 dark:border-red-800 rounded-lg p-4">
            <p className="text-red-600 dark:text-red-400">{error}</p>
            <button
              onClick={() => setError(null)}
              className="mt-2 text-sm text-red-500 hover:text-red-700 underline"
            >
              关闭
            </button>
          </div>
        )}

        {/* 邀请码管理 */}
        <div className="mb-8">
          <div className="flex items-center justify-between mb-6">
            <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2">
              <Key className="w-6 h-6 text-emerald-500" />
              <span>邀请码管理</span>
            </h2>
            <button
              onClick={() => setShowCreateForm(true)}
              className="flex items-center space-x-2 px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors"
              disabled={loading}
            >
              <Plus className="w-4 h-4" />
              <span>生成邀请码</span>
            </button>
          </div>

          {/* 创建邀请码表单 */}
          {showCreateForm && (
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6 mb-6">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white mb-4">
                创建新邀请码
              </h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    有效期（天）
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="365"
                    value={createForm.expiration_days || ''}
                    onChange={(e) => setCreateForm({
                      ...createForm,
                      expiration_days: parseInt(e.target.value) || undefined
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:text-white"
                    placeholder="30"
                  />
                </div>
                <div>
                  <label className="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-2">
                    使用次数限制
                  </label>
                  <input
                    type="number"
                    min="1"
                    max="100"
                    value={createForm.usage_limit || ''}
                    onChange={(e) => setCreateForm({
                      ...createForm,
                      usage_limit: parseInt(e.target.value) || undefined
                    })}
                    className="w-full px-3 py-2 border border-gray-300 dark:border-gray-600 rounded-lg focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 dark:bg-gray-700 dark:text-white"
                    placeholder="1"
                  />
                </div>
              </div>
              <div className="flex items-center space-x-3 mt-6">
                <button
                  onClick={handleCreateInvitation}
                  disabled={loading}
                  className="px-4 py-2 bg-emerald-500 text-white rounded-lg hover:bg-emerald-600 transition-colors disabled:opacity-50"
                >
                  {loading ? '创建中...' : '创建邀请码'}
                </button>
                <button
                  onClick={() => {
                    setShowCreateForm(false);
                    setCreateForm({ expiration_days: 30, usage_limit: 1 });
                  }}
                  className="px-4 py-2 bg-gray-500 text-white rounded-lg hover:bg-gray-600 transition-colors"
                >
                  取消
                </button>
              </div>
            </div>
          )}

          {/* 邀请码列表 */}
          <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
            <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
              <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                邀请码列表
              </h3>
            </div>
            <div className="overflow-x-auto">
              <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                <thead className="bg-gray-50 dark:bg-gray-700">
                  <tr>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      邀请码
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      创建时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      过期时间
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      使用情况
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      状态
                    </th>
                    <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                      操作
                    </th>
                  </tr>
                </thead>
                <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                  {invitations?.items && invitations.items.length > 0 ? (
                    invitations.items.map((invitation) => (
                      <tr key={invitation.id}>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <div className="flex items-center space-x-2">
                            <code className="text-sm font-mono bg-gray-100 dark:bg-gray-700 px-2 py-1 rounded">
                              {invitation.code}
                            </code>
                            <button
                              onClick={() => handleCopyCode(invitation.code)}
                              className="text-gray-400 hover:text-gray-600 dark:hover:text-gray-300"
                              title="复制邀请码"
                            >
                              <Copy className="w-4 h-4" />
                            </button>
                          </div>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {new Date(invitation.created_at).toLocaleDateString()}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {invitation.expires_at 
                            ? new Date(invitation.expires_at).toLocaleDateString()
                            : '永不过期'
                          }
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                          {invitation.used_count} / {invitation.usage_limit || '无限制'}
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap">
                          <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            invitation.is_active
                              ? 'bg-green-100 text-green-800 dark:bg-green-900/20 dark:text-green-400'
                              : 'bg-red-100 text-red-800 dark:bg-red-900/20 dark:text-red-400'
                          }`}>
                            {invitation.is_active ? '有效' : '无效'}
                          </span>
                        </td>
                        <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                          <button
                            onClick={() => handleDeleteInvitation(invitation.id)}
                            className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                            disabled={loading}
                          >
                            <Trash2 className="w-4 h-4" />
                          </button>
                        </td>
                      </tr>
                    ))
                  ) : (
                    <tr>
                      <td colSpan={6} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                        <div className="flex flex-col items-center space-y-2">
                          <Key className="w-8 h-8 text-gray-300 dark:text-gray-600" />
                          <span>暂无邀请码</span>
                          <span className="text-sm">点击上方按钮创建新的邀请码</span>
                        </div>
                      </td>
                    </tr>
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </div>

        {/* 用户管理 */}
        <div className="mb-8">
          <h2 className="text-xl font-semibold text-gray-900 dark:text-white flex items-center space-x-2 mb-6">
            <Users className="w-6 h-6 text-emerald-500" />
            <span>用户管理</span>
          </h2>
        </div>

        {/* 用户管理内容 */}
        <div className="space-y-6">
            {/* 统计卡片 */}
            {users && (
              <div className="grid grid-cols-1 md:grid-cols-1 gap-6">
                <div className="bg-white dark:bg-gray-800 rounded-lg shadow p-6">
                  <div className="flex items-center">
                    <div className="p-2 bg-blue-100 dark:bg-blue-900/20 rounded-lg">
                      <Users className="w-6 h-6 text-blue-600 dark:text-blue-400" />
                    </div>
                    <div className="ml-4">
                      <p className="text-sm font-medium text-gray-500 dark:text-gray-400">总用户数</p>
                      <p className="text-2xl font-bold text-gray-900 dark:text-white">{users.total}</p>
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* 用户列表 */}
            <div className="bg-white dark:bg-gray-800 rounded-lg shadow">
              <div className="px-6 py-4 border-b border-gray-200 dark:border-gray-700">
                <h3 className="text-lg font-medium text-gray-900 dark:text-white">
                  用户列表
                </h3>
              </div>
              <div className="overflow-x-auto">
                <table className="min-w-full divide-y divide-gray-200 dark:divide-gray-700">
                  <thead className="bg-gray-50 dark:bg-gray-700">
                    <tr>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        用户名
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        角色
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        注册时间
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        最后登录
                      </th>
                      <th className="px-6 py-3 text-left text-xs font-medium text-gray-500 dark:text-gray-300 uppercase tracking-wider">
                        操作
                      </th>
                    </tr>
                  </thead>
                  <tbody className="bg-white dark:bg-gray-800 divide-y divide-gray-200 dark:divide-gray-700">
                    {users?.items && users.items.length > 0 ? (
                      users.items.map((userItem) => (
                        <tr key={`user-${userItem.id}`}>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <div className="text-sm font-medium text-gray-900 dark:text-white">
                              {userItem.username}
                            </div>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap">
                            <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                              userItem.is_admin
                                ? 'bg-purple-100 text-purple-800 dark:bg-purple-900/20 dark:text-purple-400'
                                : 'bg-gray-100 text-gray-800 dark:bg-gray-900/20 dark:text-gray-400'
                            }`}>
                              {userItem.is_admin ? '管理员' : '普通用户'}
                            </span>
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {new Date(userItem.created_at).toLocaleDateString()}
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm text-gray-500 dark:text-gray-400">
                            {userItem.last_login 
                              ? new Date(userItem.last_login).toLocaleDateString()
                              : '从未登录'
                            }
                          </td>
                          <td className="px-6 py-4 whitespace-nowrap text-sm font-medium">
                            {userItem.id !== user?.id && !userItem.is_admin && (
                              <button
                                onClick={() => handleDeleteUser(userItem.id, userItem.username)}
                                className="text-red-600 hover:text-red-900 dark:text-red-400 dark:hover:text-red-300"
                                disabled={loading}
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            )}
                          </td>
                        </tr>
                      ))
                    ) : (
                      <tr>
                        <td colSpan={5} className="px-6 py-8 text-center text-gray-500 dark:text-gray-400">
                          <div className="flex flex-col items-center space-y-2">
                            <Users className="w-8 h-8 text-gray-300 dark:text-gray-600" />
                            <span>暂无用户数据</span>
                            <span className="text-sm">系统中还没有注册用户</span>
                          </div>
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>
            </div>
        </div>
      </div>


    </div>
  );
};

export default AdminPanel;