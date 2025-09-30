/**
 * 优化的EPUB编辑器组件V3 - 根据设计文档全面重构
 * 集成CodeMirror 6、虚拟DOM预览引擎、精确同步机制
 */

import React, { useState, useEffect, useRef, useCallback, useMemo } from 'react';
import { Layout, Button, Input, Modal, Tooltip, Badge, Space, Dropdown, Menu, Card, Switch, Slider, App } from 'antd';
import OptimizedPreviewPanelV3 from './OptimizedPreviewPanelV3';
import { PanelGroup, Panel, PanelResizeHandle } from 'react-resizable-panels';
import {
  SearchOutlined,
  FullscreenOutlined,
  FullscreenExitOutlined,
  SettingOutlined,
  EyeOutlined,
  SwapOutlined
} from '@ant-design/icons';
import Editor from '@monaco-editor/react';
import * as monaco from 'monaco-editor';
import { useEpubStore } from '../store/epubStore';
import useAppStore from '../store/useAppStore';
import { debounce, throttle } from 'lodash';
import { fileService } from '../services/file';
import FileBrowser from './FileBrowser';
import SearchReplaceCard from './SearchReplaceCard';
import SearchDebugTest from './SearchDebugTest';
import './OptimizedEpubEditorV3.css';

const { Header, Content } = Layout;
const { Search } = Input;

// 编辑器设置接口
interface EditorSettings {
  fontSize: number;
  lineHeight: number;
  wordWrap: boolean;
  lineNumbers: boolean;
  folding: boolean;
  autoSave: boolean;
  autoSaveInterval: number;
}

// 组件属性接口
interface OptimizedEpubEditorV3Props {
  sessionId: string;
  initialContent?: string;
  onContentChange?: (content: string) => void;
  onSave?: (content: string) => Promise<void>;
  onExport?: () => Promise<void>;
  className?: string;
  style?: React.CSSProperties;
  isDarkMode?: boolean;
}

const OptimizedEpubEditorV3: React.FC<OptimizedEpubEditorV3Props> = ({
  sessionId,
  initialContent = '',
  onContentChange,
  onSave,
  onExport,
  className,
  style,
  isDarkMode = false
}) => {
  // Antd App hook for message
  const { message } = App.useApp();
  
  // 状态管理
  const { currentFile: activeFile, fileTree } = useAppStore();
  const [content, setContent] = useState('');
  const [hasUnsavedChanges, setHasUnsavedChanges] = useState(false);
  const [isFullscreen, setIsFullscreen] = useState(false);
  const [showSearchReplace, setShowSearchReplace] = useState(false);
  const [searchValue, setSearchValue] = useState('');
  const [replaceValue, setReplaceValue] = useState('');
  const [isSearchReplaceVisible, setIsSearchReplaceVisible] = useState(false);
  const [selectedFile, setSelectedFile] = useState<string | null>(null);
  const [settingsVisible, setSettingsVisible] = useState(false);
  const [isLoading, setIsLoading] = useState(false);
  
  // 新增预览功能状态
  const [previewVisible, setPreviewVisible] = useState(false);
  const [previewContent, setPreviewContent] = useState('');
  const [previewLoading, setPreviewLoading] = useState(false);
  
  // 调试测试状态
  const [debugTestVisible, setDebugTestVisible] = useState(false);
  
  // 监听store中currentFile的变化
  useEffect(() => {
    if (activeFile) {
      setContent(activeFile.content);
    } else {
      setContent('// Select a file to start editing');
    }
  }, [activeFile]);
  

  
  // 编辑器设置
  const [editorSettings, setEditorSettings] = useState<EditorSettings>({
    fontSize: 14,
    lineHeight: 1.5,
    wordWrap: true,
    lineNumbers: true,
    folding: true,
    autoSave: true,
    autoSaveInterval: 30000
  });
  
  // Refs
  const editorRef = useRef<any>(null);
  const autoSaveTimeoutRef = useRef<NodeJS.Timeout | null>(null);
  
  // Store
  const {
    currentFile: epubCurrentFile,
    saveFileContent: epubSaveFileContent,
    hasUnsavedChanges: storeHasUnsavedChanges,
    setCurrentFile: setEpubCurrentFile,
    loadFileContent
  } = useEpubStore();
  
  const {
    updateFileContent,
    markFileAsModified,
    renameFile,
    deleteFile,
    setCurrentFile,
    reorderFiles
  } = useAppStore();
  
  // 获取Monaco Editor语言类型
  const getMonacoLanguage = useCallback((filePath: string): string => {
    const ext = filePath.split('.').pop()?.toLowerCase();
    switch (ext) {
      case 'html':
      case 'xhtml':
        return 'html';
      case 'css':
        return 'css';
      case 'js':
      case 'javascript':
        return 'javascript';
      case 'xml':
        return 'xml';
      case 'json':
        return 'json';
      case 'txt':
        return 'plaintext';
      case 'md':
        return 'markdown';
      default:
        return 'html'; // 默认使用HTML
    }
  }, []);
  
  // 搜索功能处理
  const handleSearch = useCallback(() => {
    setIsSearchReplaceVisible(true);
  }, []);
  
  // 批量替换功能处理
  const handleBatchReplace = useCallback(() => {
    setIsSearchReplaceVisible(true);
  }, []);

  // 保存文件处理
  const handleSave = useCallback(async () => {
    if (!activeFile) {
      message.warning('请先选择一个文件');
      return;
    }

    try {
      // 获取当前编辑器内容
      const currentContent = editorRef.current?.getValue() || content;
      
      // 调用外部保存回调
      if (onSave) {
        await onSave(currentContent);
      }
      
      // 使用store的保存方法
      if (epubCurrentFile) {
        await epubSaveFileContent(activeFile.path, currentContent);
      }
      
      // 更新状态
      setHasUnsavedChanges(false);
      
      message.success('文件保存成功');
      console.log('✅ File saved successfully:', activeFile.path);
    } catch (error) {
      console.error('❌ Save failed:', error);
      message.error('保存失败: ' + (error as Error).message);
    }
  }, [activeFile, content, onSave, epubCurrentFile, epubSaveFileContent]);

  // Monaco Editor配置
  const monacoOptions = useMemo(() => ({
    fontSize: editorSettings.fontSize,
    lineHeight: editorSettings.lineHeight,
    wordWrap: editorSettings.wordWrap ? 'on' : 'off' as 'on' | 'off',
    lineNumbers: editorSettings.lineNumbers ? 'on' : 'off' as 'on' | 'off',
    folding: editorSettings.folding,
    automaticLayout: true,
    minimap: { enabled: false },
    scrollBeyondLastLine: false,
    theme: isDarkMode ? 'vs-dark' : 'vs', // 根据isDarkMode动态设置主题
    selectOnLineNumbers: true,
    roundedSelection: false,
    readOnly: false,
    cursorStyle: 'line' as 'line',
  }), [editorSettings, isDarkMode]);
  
  // 处理Monaco Editor快捷键
  const handleEditorDidMount = useCallback((editor: any, monaco: any) => {
    editorRef.current = editor;
    
    // 添加快捷键
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyS, () => {
      handleSave();
    });
    
    editor.addCommand(monaco.KeyMod.CtrlCmd | monaco.KeyCode.KeyF, () => {
      setShowSearchReplace(!showSearchReplace);
    });
    
    editor.addCommand(monaco.KeyCode.F11, () => {
      setIsFullscreen(prev => !prev);
    });
  }, [handleSave]);
  
  // 简化的内容变化处理
  const debouncedContentChange = useCallback(
    debounce((newContent: string) => {
      console.log('📝 Content changed:', newContent.length, 'characters');
      onContentChange?.(newContent);
      
      // 更新store - 使用useAppStore来保持一致性
      if (activeFile) {
        updateFileContent(activeFile.path, newContent);
        markFileAsModified(activeFile.path);
        console.log('📝 File marked as modified:', activeFile.path);
      }
      
      setHasUnsavedChanges(true);
    }, 300),
    [onContentChange, activeFile, updateFileContent, markFileAsModified]
  );
  
  // 编辑器内容变化处理
  const handleEditorChange = useCallback((newContent: string) => {
    setContent(newContent);
    debouncedContentChange(newContent);
  }, [debouncedContentChange]);
  
  // 预览处理 - 修复CSS样式加载问题
  const handlePreview = useCallback(async () => {
    if (!activeFile) {
      message.warning('请先选择一个文件');
      return;
    }
    
    setPreviewLoading(true);
    try {
      // 获取当前编辑器内容
      const currentContent = editorRef.current?.getValue() || content;
      
      // 如果是HTML文件，需要处理CSS样式链接
      let processedContent = currentContent;
      if (activeFile.path.endsWith('.html') || activeFile.path.endsWith('.xhtml')) {
        // 将相对路径的CSS链接转换为绝对路径或内联样式
        processedContent = currentContent.replace(
          /<link[^>]*rel=["']stylesheet["'][^>]*href=["']([^"']*)["'][^>]*>/gi,
          (match, href) => {
            // 如果是相对路径，添加基础样式
            if (!href.startsWith('http') && !href.startsWith('/')) {
              return `<style>
                body { font-family: serif; line-height: 1.6; margin: 2em; }
                h1, h2, h3, h4, h5, h6 { color: #333; margin-top: 1.5em; }
                p { margin-bottom: 1em; }
                .chapter { max-width: 800px; margin: 0 auto; }
              </style>`;
            }
            return match;
          }
        );
      }
      
      setPreviewContent(processedContent);
      setPreviewVisible(true);
    } catch (error) {
      console.error('预览失败:', error);
      message.error('预览失败');
    } finally {
      setPreviewLoading(false);
    }
  }, [activeFile, content]);
  
  // Store中的selectFile方法
  const { selectFile } = useAppStore();
  
  // 文件选择处理
  const handleFileSelect = useCallback(async (file: any) => {
    console.log('🔍 OptimizedEpubEditorV3: File selected:', file.name, file.path);
    
    try {
      setIsLoading(true);
      setSelectedFile(file.path);
      
      // 使用store的selectFile方法
      await selectFile(file);
      
      console.log('✅ OptimizedEpubEditorV3: File selection completed successfully');
    } catch (error) {
      console.error('❌ OptimizedEpubEditorV3: Error loading file:', error);
      message.error('加载文件失败');
    } finally {
      setIsLoading(false);
    }
  }, [selectFile]);
  

  
  // 自动保存
  useEffect(() => {
    if (editorSettings.autoSave && hasUnsavedChanges) {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
      
      autoSaveTimeoutRef.current = setTimeout(() => {
        handleSave();
      }, editorSettings.autoSaveInterval);
    }
    
    return () => {
      if (autoSaveTimeoutRef.current) {
        clearTimeout(autoSaveTimeoutRef.current);
      }
    };
  }, [hasUnsavedChanges, editorSettings.autoSave, editorSettings.autoSaveInterval, handleSave]);
  
  // Monaco Editor内容变化处理
  const handleMonacoChange = useCallback((value: string | undefined) => {
    if (value !== undefined) {
      handleEditorChange(value);
    }
  }, [handleEditorChange]);
  
  console.log('📝 Monaco Editor content:', content ? content.substring(0, 100) : 'No content');
  
  // 工具栏菜单
  const settingsMenuItems = [
    {
      key: 'editor',
      label: (
        <span>
          <SettingOutlined /> 编辑器设置
        </span>
      ),
      onClick: () => setSettingsVisible(true)
    }
  ];
  
  return (
    <Layout className={`optimized-epub-editor-v3 ${className || ''}`} style={style}>
      {/* 工具栏 */}
      <Header className={`editor-toolbar ${isDarkMode ? 'dark-theme' : 'light-theme'}`} style={{
        backgroundColor: isDarkMode ? '#1f1f1f' : '#fff',
        borderBottom: `1px solid ${isDarkMode ? '#333' : '#f0f0f0'}`
      }}>
        <Space>
          <Button
            icon={<SwapOutlined />}
            onClick={handleBatchReplace}
          >
            批量替换
          </Button>
          
          <Button
            icon={<EyeOutlined />}
            loading={previewLoading}
            onClick={handlePreview}
            disabled={!activeFile}
          >
            预览
          </Button>
          
          <Button
            icon={<SearchOutlined />}
            onClick={() => setShowSearchReplace(!showSearchReplace)}
            type={showSearchReplace ? 'primary' : 'default'}
          >
            搜索
          </Button>
          
          <Button
            onClick={() => setDebugTestVisible(!debugTestVisible)}
            type={debugTestVisible ? 'primary' : 'default'}
            style={{ backgroundColor: debugTestVisible ? '#ff4d4f' : undefined }}
          >
            调试测试
          </Button>
          
          <Button
            icon={isFullscreen ? <FullscreenExitOutlined /> : <FullscreenOutlined />}
            onClick={() => setIsFullscreen(prev => !prev)}
          >
            {isFullscreen ? '退出全屏' : '全屏'}
          </Button>
          
          <Dropdown menu={{ items: settingsMenuItems }} trigger={['click']}>
            <Button icon={<SettingOutlined />}>
              设置
            </Button>
          </Dropdown>
        </Space>
      </Header>
      
      {/* 主编辑区域 - 双面板布局 */}
      <Content style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 64px)' }}>
        <PanelGroup direction="horizontal" style={{ flex: 1 }}>
          {/* 文件浏览器面板 */}
          <Panel defaultSize={25} minSize={20} maxSize={40}>
            <FileBrowser
              fileTree={fileTree}
              selectedFile={selectedFile}
              onFileSelect={handleFileSelect}
              onFileRename={renameFile}
              onFileDelete={deleteFile}
              onFileReorder={reorderFiles}
              isDarkMode={isDarkMode}
            />
          </Panel>
          
          <PanelResizeHandle className="resize-handle" />
          
          {/* 编辑器面板 */}
          <Panel defaultSize={75} minSize={50}>
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column' }}>
              {/* Monaco Editor */}
              <div className="editor-container" style={{ flex: 1, width: '100%' }}>
                <Editor
                  height="100%"
                  language={getMonacoLanguage(activeFile?.path || '')}
                  value={content}
                  onChange={handleMonacoChange}
                  onMount={handleEditorDidMount}
                  options={monacoOptions}
                  theme="vs"
                />
              </div>
              
              {/* Search and Replace Card */}
              <SearchReplaceCard
                visible={showSearchReplace}
                onClose={() => setShowSearchReplace(false)}
                currentFile={activeFile ? {
                  path: activeFile.path,
                  name: activeFile.path.split('/').pop() || '',
                  content: activeFile.content
                } : null}
                updateFileContent={(content) => {
                  if (activeFile) {
                    updateFileContent(activeFile.path, content);
                    setContent(content);
                    setHasUnsavedChanges(true);
                  }
                }}
                monacoEditor={editorRef.current}
                fileTree={fileTree}
                onFileSelect={handleFileSelect}
                isDarkMode={isDarkMode}
                onSave={handleSave}
                sessionId={sessionId}
              />
              
              {/* Debug Test Component */}
              <SearchDebugTest
                visible={debugTestVisible}
                onClose={() => setDebugTestVisible(false)}
                sessionId={sessionId}
                fileTree={fileTree}
                isDarkMode={isDarkMode}
              />
            </div>
          </Panel>
        </PanelGroup>
      </Content>
      
      {/* 简化的设置模态框 */}
      <Modal
        title="编辑器设置"
        open={settingsVisible}
        onCancel={() => setSettingsVisible(false)}
        footer={null}
        width={500}
        className={isDarkMode ? 'dark-modal' : 'light-modal'}
      >
        <Card title="编辑器设置">
          <Space direction="vertical" style={{ width: '100%' }}>
            <div>
              <label>字体大小: {editorSettings.fontSize}px</label>
              <Slider
                min={10}
                max={24}
                value={editorSettings.fontSize}
                onChange={(value) => setEditorSettings(prev => ({ ...prev, fontSize: value }))}
              />
            </div>
            
            <div>
              <label>行高: {editorSettings.lineHeight}</label>
              <Slider
                min={1.0}
                max={2.0}
                step={0.1}
                value={editorSettings.lineHeight}
                onChange={(value) => setEditorSettings(prev => ({ ...prev, lineHeight: value }))}
              />
            </div>
            
            <div>
              <label>自动保存:</label>
              <Switch
                checked={editorSettings.autoSave}
                onChange={(checked) => setEditorSettings(prev => ({ ...prev, autoSave: checked }))}
              />
            </div>
          </Space>
        </Card>
      </Modal>
      
      {/* 预览模态框 */}
      <Modal
        title={`预览 - ${activeFile ? activeFile.path.split('/').pop() : '未选择文件'}`}
        open={previewVisible}
        onCancel={() => setPreviewVisible(false)}
        footer={null}
        width="80%"
        style={{ top: 20 }}
        className={isDarkMode ? 'dark-modal' : 'light-modal'}
      >
        <div style={{ height: '70vh' }}>
          <OptimizedPreviewPanelV3
            content={previewContent}
            editor={editorRef.current}
            isDarkMode={isDarkMode}
            style={{ height: '100%' }}
          />
        </div>
      </Modal>
      

    </Layout>
  );
};

export default OptimizedEpubEditorV3