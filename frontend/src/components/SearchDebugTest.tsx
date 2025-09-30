import React, { useState } from 'react';
import { Button, Typography, Modal } from 'antd';
import { fileService } from '../services/file';
import useAppStore from '../store/useAppStore';

interface SearchDebugTestProps {
  visible: boolean;
  onClose: () => void;
  sessionId?: string;
  fileTree?: any[];
  isDarkMode?: boolean;
}

const SearchDebugTest: React.FC<SearchDebugTestProps> = ({
  visible,
  onClose,
  sessionId: propSessionId,
  fileTree,
  isDarkMode = false
}) => {
  const { sessionId: storeSessionId } = useAppStore();
  const sessionId = propSessionId || storeSessionId;
  const [testResults, setTestResults] = useState<string[]>([]);
  const [isLoading, setIsLoading] = useState(false);

  const addLog = (message: string) => {
    console.log(message);
    setTestResults(prev => [...prev, `${new Date().toLocaleTimeString()}: ${message}`]);
  };

  const testFileContentFetch = async () => {
    setIsLoading(true);
    setTestResults([]);
    
    addLog('🧪 Starting file content fetch test...');
    addLog(`🔑 SessionId: ${sessionId}`);
    addLog(`📁 FileTree available: ${!!fileTree}`);
    
    if (!sessionId) {
      addLog('❌ No sessionId available');
      setIsLoading(false);
      return;
    }
    
    if (!fileTree || fileTree.length === 0) {
      addLog('❌ No fileTree available');
      setIsLoading(false);
      return;
    }
    
    // Get all files from fileTree
    const getAllFiles = (items: any[]): any[] => {
      let files: any[] = [];
      items.forEach(item => {
        if (item.type === 'file') {
          files.push(item);
        } else if (item.children) {
          files = files.concat(getAllFiles(item.children));
        }
      });
      return files;
    };
    
    const allFiles = getAllFiles(fileTree);
    addLog(`📄 Total files found: ${allFiles.length}`);
    
    // Filter text files
    const textFiles = allFiles.filter(file => 
      file.name.match(/\.(html|xhtml|xml|txt|md|js|ts|json)$/i)
    );
    addLog(`📝 Text files found: ${textFiles.length}`);
    textFiles.forEach(file => addLog(`  - ${file.name} (${file.path})`));
    
    // Test fetching content for each text file
    for (const file of textFiles.slice(0, 3)) { // Test first 3 files only
      try {
        addLog(`🌐 Fetching content for: ${file.name}`);
        const startTime = Date.now();
        const fileContent = await fileService.getFileContent(sessionId, file.path);
        const endTime = Date.now();
        
        addLog(`✅ Successfully fetched ${file.name}:`);
        addLog(`  - Content length: ${fileContent.content?.length || 0}`);
        addLog(`  - Encoding: ${fileContent.encoding || 'unknown'}`);
        addLog(`  - MIME type: ${fileContent.mime_type || 'unknown'}`);
        addLog(`  - Fetch time: ${endTime - startTime}ms`);
        
        // Test search in content
        if (fileContent.content) {
          const testSearchText = 'the'; // Common word to test
          const matches = (fileContent.content.match(new RegExp(testSearchText, 'gi')) || []).length;
          addLog(`🔍 Test search for '${testSearchText}': ${matches} matches`);
        }
        
      } catch (error) {
        addLog(`❌ Failed to fetch ${file.name}: ${error}`);
        console.error('Fetch error details:', error);
      }
    }
    
    addLog('🏁 Test completed!');
    setIsLoading(false);
  };
  
  const clearLogs = () => {
    setTestResults([]);
  };

  return (
    <Modal
      title="🧪 搜索功能调试测试"
      open={visible}
      onCancel={onClose}
      footer={null}
      width={800}
      className={isDarkMode ? 'dark-modal' : 'light-modal'}
    >
      <div style={{ padding: '16px' }}>
        <div style={{ marginBottom: '16px' }}>
          <Typography.Text strong>会话ID: </Typography.Text>
          <Typography.Text code>{sessionId}</Typography.Text>
        </div>
        
        <div style={{ marginBottom: '16px' }}>
          <Typography.Text strong>文件树状态: </Typography.Text>
          <Typography.Text>{fileTree ? `找到 ${fileTree.length} 个文件` : '未加载'}</Typography.Text>
        </div>
        
        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px' }}>
          <Button
            type="primary"
            onClick={testFileContentFetch}
            loading={isLoading}
          >
            {isLoading ? '⏳ 测试中...' : '🧪 测试文件内容获取'}
          </Button>
          
          <Button
            onClick={clearLogs}
          >
            🗑️ 清除日志
          </Button>
        </div>
        
        <div style={{ 
          backgroundColor: '#000', 
          color: '#00ff00', 
          padding: '16px', 
          borderRadius: '4px', 
          fontFamily: 'monospace', 
          fontSize: '12px', 
          maxHeight: '400px', 
          overflowY: 'auto'
        }}>
          {testResults.length === 0 ? (
            <div style={{ color: '#888' }}>暂无测试结果。点击"测试文件内容获取"开始测试。</div>
          ) : (
            testResults.map((result, index) => (
              <div key={index} style={{ marginBottom: '4px' }}>
                {result}
              </div>
            ))
          )}
        </div>
        
        <div style={{ marginTop: '16px', fontSize: '12px', color: '#666' }}>
          <Typography.Text strong>使用说明:</Typography.Text>
          <ol style={{ paddingLeft: '20px', marginTop: '8px' }}>
            <li>确保已上传文件并有活跃会话</li>
            <li>点击"测试文件内容获取"来测试文件内容检索</li>
            <li>查看上方日志和控制台获取详细调试信息</li>
            <li>打开浏览器开发者工具控制台查看SearchReplaceCard的额外日志</li>
          </ol>
        </div>
      </div>
    </Modal>
  );
};

export default SearchDebugTest;