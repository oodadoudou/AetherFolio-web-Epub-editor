import React from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { ConfigProvider, Button, App } from 'antd';
import { ArrowLeftOutlined } from '@ant-design/icons';

import Toolbar from '../components/Toolbar';
import OptimizedEpubEditorV3 from '../components/OptimizedEpubEditorV3';
import BatchReplaceModal from '../components/BatchReplaceModal';
import useAppStore from '../store/useAppStore';
import { fileService } from '../services/file';


interface EditorProps {
  isDarkMode: boolean;
  traeDarkTheme: unknown;
  traeLightTheme: unknown;
  onThemeToggle: () => void;
}

const Editor: React.FC<EditorProps> = ({ isDarkMode, traeDarkTheme, traeLightTheme, onThemeToggle }) => {
  const { sessionId } = useParams<{ sessionId: string }>();
  const navigate = useNavigate();
  const { message } = App.useApp();
  const {
    fileTree,
    metadata,
    isBatchReplaceVisible,
    setBatchReplaceVisible,
    setMetadata,
    renameFile,
    deleteFile,
    reorderFiles,
    clearFileTree,
    setFileTree,
    setSessionId,
  } = useAppStore();

  const [loading, setLoading] = React.useState(true);

  // Load session data on component mount
  React.useEffect(() => {
    const initializeSession = async () => {
      if (!sessionId) {
        message.error('会话ID无效');
        navigate('/');
        return;
      }

      try {
        // 首先检查会话状态
        const sessionStatus = await fileService.checkSessionStatus(sessionId);
        
        if (!sessionStatus.exists) {
          message.error({
            content: '会话已过期或不存在，请重新上传文件',
            duration: 5,
          });
          localStorage.removeItem('currentSessionId');
          setTimeout(() => {
            navigate('/');
          }, 2000);
          return;
        }
        
        // 会话有效，继续初始化
        // 设置会话ID
        setSessionId(sessionId);
        
        // 保存当前会话ID到 localStorage，用于浏览器关闭时清理
        localStorage.setItem('currentSessionId', sessionId);
        
        // 获取文件树数据
        const fileTreeResponse = await fileService.getFileTree(sessionId);
        console.log('File tree response:', fileTreeResponse);
        
        // 处理后端返回的数据格式
        // 后端返回格式: {success, file_tree, total_files, total_size}
        // 前端期望格式: ApiResponse<FileNode[]> 中的 data 字段
        if ((fileTreeResponse as any).file_tree) {
          setFileTree((fileTreeResponse as any).file_tree);
        } else if ((fileTreeResponse as any).data) {
          setFileTree((fileTreeResponse as any).data);
        } else {
          setFileTree([]);
        }
        
        // 设置默认元数据
        setMetadata({ title: '', author: '' });
      } catch (error: unknown) {
        console.error('Failed to load session data:', error);
        
        // 检查是否是会话不存在的错误
        const axiosError = error as { response?: { status?: number }; message?: string };
        if (axiosError?.response?.status === 404 || axiosError?.message?.includes('SESSION_NOT_FOUND')) {
          message.error({
            content: '会话已过期或不存在，请重新上传文件',
            duration: 5,
          });
          // 清理无效的会话ID
          localStorage.removeItem('currentSessionId');
          // 延迟跳转，让用户看到错误信息
          setTimeout(() => {
            navigate('/');
          }, 2000);
        } else {
          message.error('加载会话数据失败，请稍后重试');
        }
        
        setFileTree([]);
        setMetadata({ title: '', author: '' });
      } finally {
        setLoading(false);
      }
    };

    initializeSession();
  }, [sessionId, navigate, setSessionId, setFileTree, setMetadata, message]);

  const handleBatchReplace = () => {
    setBatchReplaceVisible(true);
  };

  const handleExitEditor = () => {
    // 清理会话数据
    clearFileTree();
    localStorage.removeItem('currentSessionId');
    navigate('/');
  };

  // 保存所有修改过的文件到后端
  const handleSave = async () => {
    if (!sessionId) {
      message.error('会话ID无效');
      return;
    }

    try {
      const { getModifiedFiles, clearModifiedFiles } = useAppStore.getState();
      const modifiedFiles = getModifiedFiles();
      
      if (modifiedFiles.size === 0) {
        message.info('没有需要保存的修改');
        return;
      }
      
      message.loading({ content: `正在保存 ${modifiedFiles.size} 个修改的文件...`, key: 'save' });
      
      // 批量保存所有修改过的文件
      const savePromises = Array.from(modifiedFiles.entries()).map(([path, content]) => 
        fileService.saveFileContent(sessionId, path, content)
      );
      
      await Promise.all(savePromises);
      
      // 清除修改记录
      clearModifiedFiles();
      
      message.success({ content: `成功保存 ${modifiedFiles.size} 个文件`, key: 'save' });
    } catch (error) {
      console.error('保存失败:', error);
      
      // 检查是否是会话不存在的错误
      const axiosError = error as { response?: { status?: number }; message?: string };
      if (axiosError?.response?.status === 404 || axiosError?.message?.includes('SESSION_NOT_FOUND')) {
        message.error({
          content: '会话已过期或不存在，请重新上传文件',
          key: 'save',
          duration: 5,
        });
        // 清理无效的会话ID
        localStorage.removeItem('currentSessionId');
        // 延迟跳转，让用户看到错误信息
        setTimeout(() => {
          navigate('/');
        }, 2000);
      } else {
        message.error({ content: '保存失败: ' + (error as Error).message, key: 'save' });
      }
    }
  };

  // 导出EPUB文件
  const handleExport = async () => {
    if (!sessionId) {
      message.error('会话ID无效');
      return;
    }

    try {
      message.loading({ content: '正在导出EPUB文件...', key: 'export' });
      
      // 调用后端导出API
      const response = await fetch(`/api/v1/export/${sessionId}?format=epub`, {
        method: 'GET',
        headers: {
          'Content-Type': 'application/json',
        },
      });
      
      if (response.ok) {
        // 获取文件blob
        const blob = await response.blob();
        
        // 从响应头获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = `${metadata.title || 'exported'}.epub`;
        if (contentDisposition) {
          const filenameMatch = contentDisposition.match(/filename=(.+)/);
          if (filenameMatch) {
            filename = filenameMatch[1].replace(/"/g, '');
          }
        }
        
        // 创建下载链接
        const url = window.URL.createObjectURL(blob);
        const link = document.createElement('a');
        link.href = url;
        link.download = filename;
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
        window.URL.revokeObjectURL(url);
        
        message.success({ content: 'EPUB导出成功', key: 'export' });
      } else {
        const errorText = await response.text();
        console.error('导出失败:', errorText);
        message.error({ content: '导出失败，请重试', key: 'export' });
      }
    } catch (error) {
      console.error('导出失败:', error);
      message.error({ content: '导出失败: ' + (error as Error).message, key: 'export' });
    }
  };



  if (loading) {
    return (
      <ConfigProvider theme={isDarkMode ? traeDarkTheme : traeLightTheme}>
        <div className={`h-screen flex items-center justify-center ${isDarkMode ? 'bg-neutral-900' : 'bg-slate-50'}`}>
          <div className="text-center">
            <div className="text-4xl mb-4">📚</div>
            <p className={`text-lg ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'}`}>
              加载会话中...
            </p>
          </div>
        </div>
      </ConfigProvider>
    );
  }

  return (
    <ConfigProvider theme={isDarkMode ? traeDarkTheme : traeLightTheme}>
      <div className={`h-screen flex flex-col ${isDarkMode ? 'bg-neutral-900' : 'bg-slate-50'}`} style={isDarkMode ? {backgroundColor: '#1a1a1a'} : {}}>
        {/* Toolbar */}
        <Toolbar 
          metadata={metadata}
          onMetadataChange={setMetadata}
          onBatchReplace={handleBatchReplace}
          isDarkMode={isDarkMode}
          onThemeToggle={onThemeToggle}
          onExitEditor={handleExitEditor}
          onSave={handleSave}
          onExport={handleExport}
          sessionId={sessionId}
        />
        
        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden">
          {fileTree.length === 0 ? (
            // No files loaded
            <div className={`h-full flex items-center justify-center ${isDarkMode ? 'bg-neutral-800' : 'bg-white'}`}>
              <div className="text-center space-y-6">
                <div className="text-6xl mb-4">⚠️</div>
                <h2 className={`text-2xl font-bold ${isDarkMode ? 'text-neutral-100' : 'text-slate-800'}`}>
                  会话已加载
                </h2>
                <p className={`text-lg ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'}`}>
                  但没有找到文件数据，可能是会话已过期或文件已被清理
                </p>
                <div className="space-y-3">
                  <p className={`text-sm ${isDarkMode ? 'text-neutral-500' : 'text-slate-500'}`}>
                    建议：返回首页重新上传文件
                  </p>
                  <Button 
                    type="primary" 
                    size="large"
                    icon={<ArrowLeftOutlined />}
                    onClick={handleExitEditor}
                  >
                    返回首页重新上传
                  </Button>
                </div>
              </div>
            </div>
          ) : (
            // Optimized EPUB Editor Interface V3
            <OptimizedEpubEditorV3 
              sessionId={sessionId!}
              onContentChange={(content) => {
                console.log('Content changed:', content.length, 'characters');
              }}
              onSave={async (content) => {
                try {
                  // 这里可以添加保存逻辑
                  console.log('Saving content:', content.length, 'characters');
                  message.success('内容已保存');
                } catch (error) {
                  console.error('Save failed:', error);
                  message.error('保存失败');
                }
              }}
              onExport={async () => {
                try {
                  // 这里可以添加导出逻辑
                  console.log('Exporting EPUB...');
                  message.success('EPUB导出成功');
                } catch (error) {
                  console.error('Export failed:', error);
                  message.error('导出失败');
                }
              }}
              className="h-full"
              isDarkMode={isDarkMode}
            />
          )}
        </div>
        
        {/* Modals */}
        <BatchReplaceModal 
          visible={isBatchReplaceVisible}
          onClose={() => setBatchReplaceVisible(false)}
          isDarkMode={isDarkMode}
        />
      </div>
    </ConfigProvider>
  );
};

export default Editor;