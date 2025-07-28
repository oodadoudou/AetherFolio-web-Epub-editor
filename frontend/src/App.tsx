import React from 'react';
import { ConfigProvider, Button, FloatButton, theme, message } from 'antd';
import { PlusOutlined, EditOutlined, MergeOutlined, SwapOutlined, HomeOutlined, QuestionCircleOutlined } from '@ant-design/icons';
import { Panel, PanelGroup, PanelResizeHandle } from 'react-resizable-panels';

import UploadModal from './components/UploadModal';
import Toolbar from './components/Toolbar';
import FileBrowser from './components/FileBrowser';
import CodeEditor from './components/CodeEditor';
import PreviewPanel from './components/PreviewPanel';
import SearchReplacePanel from './components/SearchReplacePanel';
import BatchReplaceModal from './components/BatchReplaceModal';
import useAppStore from './store/useAppStore';

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
    isUploadModalVisible,
    setUploadModalVisible,
    fileTree,
    currentFile,
    selectedFilePath,
    metadata,
    isBatchReplaceVisible,
    setBatchReplaceVisible,
    isDarkMode,
    toggleTheme,
    selectFile,
    updateFileContent,
    setMetadata,
    renameFile,
    deleteFile,
    reorderFiles,
    clearFileTree,
  } = useAppStore();

  const [searchReplaceVisible, setSearchReplaceVisible] = React.useState(false);
  const [searchReplaceFilePath, setSearchReplaceFilePath] = React.useState<string | null>(null);
  const [helpTooltipVisible, setHelpTooltipVisible] = React.useState(false);

  const handleOpenUpload = () => {
    setUploadModalVisible(true);
  };

  const handleBatchReplace = () => {
    setBatchReplaceVisible(true);
  };

  const handleOpenSearchReplace = (filePath: string) => {
    setSearchReplaceFilePath(filePath);
    setSearchReplaceVisible(true);
  };

  const handleMergeClick = () => {
    message.info({
      content: '暂不支持，请等待更新 ✨',
      duration: 3,
    });
  };

  const handleConvertClick = () => {
    message.info({
      content: '暂不支持，请等待更新 ✨',
      duration: 3,
    });
  };

  const handleHelpClick = () => {
    setHelpTooltipVisible(true);
  };

  const handleCloseTooltip = () => {
    setHelpTooltipVisible(false);
  };

  // Handle file opening from search results
  React.useEffect(() => {
    const handleOpenFile = (event: CustomEvent) => {
      const { filePath, fileName } = event.detail;
      
      // Find the file in the file tree
      const findFileInTree = (nodes: any[]): any => {
        for (const node of nodes) {
          if (node.type === 'file' && node.path === filePath) {
            return node;
          }
          if (node.children) {
            const found = findFileInTree(node.children);
            if (found) return found;
          }
        }
        return null;
      };
      
      const fileNode = findFileInTree(fileTree);
      if (fileNode) {
        selectFile(fileNode);
      }
    };
    
    document.addEventListener('openFile', handleOpenFile as EventListener);
    
    return () => {
      document.removeEventListener('openFile', handleOpenFile as EventListener);
    };
  }, [fileTree, selectFile]);

  return (
    <ConfigProvider theme={isDarkMode ? traeDarkTheme : traeLightTheme}>
      <div className={`h-screen flex flex-col ${isDarkMode ? 'bg-neutral-900' : 'bg-slate-50'}`} style={isDarkMode ? {backgroundColor: '#1a1a1a'} : {}}>
        {/* Toolbar */}
        <Toolbar 
          metadata={metadata}
          onMetadataChange={setMetadata}
          onBatchReplace={handleBatchReplace}
          isDarkMode={isDarkMode}
          onThemeToggle={toggleTheme}
          onExitEditor={fileTree.length > 0 ? clearFileTree : undefined}
        />
        
        {/* Main Content Area */}
        <div className="flex-1 overflow-hidden">
          {fileTree.length === 0 ? (
            // Main Interface
            <div className={`h-full flex items-center justify-center ${isDarkMode ? 'bg-neutral-800' : 'bg-white'}`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
              <div className="text-center space-y-8">
                <div className="text-6xl text-slate-300 mb-4">📚</div>
                <h1 className={`text-4xl font-bold ${isDarkMode ? 'text-neutral-100' : 'text-slate-800'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>AetherFolio</h1>
                <p className={`text-lg ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'} max-w-lg`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>
                  A modern EPUB editor with powerful editing, merging, and conversion capabilities.
                </p>
                
                {/* Main Action Buttons */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mt-12">
                  {/* Edit EPUB */}
                  <div className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer ${isDarkMode ? 'border-neutral-600 hover:border-green-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-green-500 bg-slate-50 hover:bg-slate-100'}`} onClick={handleOpenUpload}>
                    <div className="text-center space-y-4">
                      <EditOutlined className={`text-4xl ${isDarkMode ? 'text-green-400' : 'text-green-600'}`} />
                      <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-100' : 'text-slate-800'}`}>Edit EPUB</h3>
                      <p className={`text-sm ${isDarkMode ? 'text-neutral-400' : 'text-slate-600'}`}>
                        Upload and edit EPUB files with advanced text processing capabilities
                      </p>
                    </div>
                  </div>
                  
                  {/* Merge EPUBs */}
                  <div 
                    className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer opacity-60 ${isDarkMode ? 'border-neutral-600 hover:border-gray-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-gray-400 bg-slate-50 hover:bg-slate-100'}`}
                    onClick={handleMergeClick}
                  >
                    <div className="text-center space-y-4">
                      <MergeOutlined className={`text-4xl ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                      <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-300' : 'text-slate-600'}`}>Merge EPUBs</h3>
                      <p className={`text-sm ${isDarkMode ? 'text-neutral-500' : 'text-slate-500'}`}>
                        Combine multiple EPUB files into a single publication
                      </p>
                    </div>
                  </div>
                  
                  {/* Convert Files */}
                  <div 
                    className={`p-6 rounded-lg border-2 border-dashed transition-all hover:border-solid cursor-pointer opacity-60 ${isDarkMode ? 'border-neutral-600 hover:border-gray-500 bg-neutral-700 hover:bg-neutral-600' : 'border-slate-300 hover:border-gray-400 bg-slate-50 hover:bg-slate-100'}`}
                    onClick={handleConvertClick}
                  >
                    <div className="text-center space-y-4">
                      <SwapOutlined className={`text-4xl ${isDarkMode ? 'text-gray-400' : 'text-gray-500'}`} />
                      <h3 className={`text-xl font-semibold ${isDarkMode ? 'text-neutral-300' : 'text-slate-600'}`}>Convert Files</h3>
                      <p className={`text-sm ${isDarkMode ? 'text-neutral-500' : 'text-slate-500'}`}>
                        Convert between different e-book formats and document types
                      </p>
                    </div>
                  </div>
                </div>
                
                {/* Help Button */}
                <Button 
                  className="fixed top-6 right-6 w-14 h-14 rounded-full flex items-center justify-center shadow-lg hover:scale-110 transition-all z-50"
                  style={{
                    backgroundColor: '#22c55e',
                    borderColor: '#22c55e',
                    color: 'white'
                  }}
                  onClick={handleHelpClick}
                  icon={<QuestionCircleOutlined style={{ fontSize: '24px' }} />}
                  title="Help"
                />
                
                {/* Help Tooltip */}
                {helpTooltipVisible && (
                  <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50" onClick={handleCloseTooltip}>
                    <div className="bg-white rounded-lg p-6 max-w-sm mx-4 text-center shadow-xl" onClick={(e) => e.stopPropagation()}>
                      <div className="text-4xl mb-4 text-yellow-500">
                        <QuestionCircleOutlined />
                      </div>
                      <h3 className="text-xl font-bold mb-2 text-gray-800">帮助</h3>
                      <p className="text-gray-600 mb-6">
                        当前只有 Edit 功能可用，Merge 和 Convert 功能正在开发中。
                      </p>
                      <Button 
                        type="primary" 
                        onClick={handleCloseTooltip}
                        className="px-6"
                      >
                        知道了
                      </Button>
                    </div>
                  </div>
                )}
              </div>
            </div>
          ) : (
            // Editor Interface
            <PanelGroup direction="horizontal" className="h-full">
              {/* File Browser */}
              <Panel defaultSize={20} minSize={15} maxSize={35}>
                <FileBrowser 
                  fileTree={fileTree}
                  selectedFile={selectedFilePath}
                  onFileSelect={selectFile}
                  onFileRename={renameFile}
                  onFileDelete={deleteFile}
                  onFileReorder={reorderFiles}
                  onOpenSearchReplace={handleOpenSearchReplace}
                  isDarkMode={isDarkMode}
                />
              </Panel>
              
              <PanelResizeHandle className={`w-1 ${isDarkMode ? 'bg-neutral-700 hover:bg-neutral-600' : 'bg-slate-200 hover:bg-slate-300'} transition-colors`} style={isDarkMode ? {backgroundColor: '#404040'} : {}} />
              
              {/* Middle Panel - Code Editor + Search */}
              <Panel defaultSize={50} minSize={30}>
                <PanelGroup direction="vertical">
                  {/* Code Editor */}
                  <Panel defaultSize={searchReplaceVisible ? 70 : 100} minSize={50}>
                    <CodeEditor 
                       file={currentFile}
                       onChange={updateFileContent}
                       onOpenSearch={() => setSearchReplaceVisible(true)}
                       isDarkMode={isDarkMode}
                     />
                  </Panel>
                  
                  {/* Search Replace Panel */}
                  {searchReplaceVisible && (
                    <>
                      <PanelResizeHandle className={`h-1 ${isDarkMode ? 'bg-neutral-700 hover:bg-neutral-600' : 'bg-slate-200 hover:bg-slate-300'} transition-colors`} style={isDarkMode ? {backgroundColor: '#404040'} : {}} />
                      <Panel defaultSize={30} minSize={20} maxSize={50}>
                        <div className={`h-full ${isDarkMode ? 'bg-neutral-800' : 'bg-white'}`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
                          <SearchReplacePanel
                            visible={searchReplaceVisible}
                            onClose={() => setSearchReplaceVisible(false)}
                            currentFilePath={searchReplaceFilePath || currentFile?.path}
                            isDarkMode={isDarkMode}
                          />
                        </div>
                      </Panel>
                    </>
                  )}
                </PanelGroup>
              </Panel>
              
              <PanelResizeHandle className={`w-1 ${isDarkMode ? 'bg-neutral-700 hover:bg-neutral-600' : 'bg-slate-200 hover:bg-slate-300'} transition-colors`} style={isDarkMode ? {backgroundColor: '#404040'} : {}} />
              
              {/* Preview Panel */}
              <Panel defaultSize={30} minSize={20} maxSize={50}>
                <PreviewPanel 
                  content={currentFile?.content || ''}
                  fileName={currentFile?.path.split('/').pop() || null}
                  filePath={currentFile?.path}
                  isDarkMode={isDarkMode}
                />
              </Panel>
            </PanelGroup>
          )}
        </div>
        
        {/* Floating Action Button */}
        {fileTree.length === 0 && (
          <FloatButton 
            icon={<PlusOutlined />}
            type="primary"
            style={{ right: 24, bottom: 24 }}
            onClick={handleOpenUpload}
            tooltip="Upload EPUB File"
          />
        )}
        
        {/* Modals */}
        <UploadModal 
          visible={isUploadModalVisible}
          onClose={() => setUploadModalVisible(false)}
        />
        
        <BatchReplaceModal 
          visible={isBatchReplaceVisible}
          onClose={() => setBatchReplaceVisible(false)}
        />
      </div>
    </ConfigProvider>
  );
}

export default App;