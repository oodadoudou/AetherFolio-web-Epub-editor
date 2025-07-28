import React, { useEffect } from 'react';
import { Typography, Empty, Button, Space, Dropdown, MenuProps } from 'antd';
import { EyeOutlined, ReloadOutlined, ExpandOutlined } from '@ant-design/icons';
import { useTheme } from '../hooks/useTheme';

const { Title } = Typography;

interface PreviewPanelProps {
  content: string;
  fileName: string | null;
  filePath?: string;
  isDarkMode?: boolean;
}

const PreviewPanel: React.FC<PreviewPanelProps> = ({ 
  content, 
  fileName, 
  filePath,
  isDarkMode = false
}) => {
  const [refreshKey, setRefreshKey] = React.useState(0);

  const handleRefresh = () => {
    setRefreshKey(prev => prev + 1);
  };

  // Context menu items
  const contextMenuItems: MenuProps['items'] = [
    {
      key: 'refresh',
      label: 'Refresh Preview',
      icon: <ReloadOutlined />,
      onClick: handleRefresh,
    },
  ];

  const isHtmlContent = fileName && (fileName.endsWith('.html') || fileName.endsWith('.xhtml'));

  if (!content || !isHtmlContent) {
    return (
      <div className={`h-full ${isDarkMode ? '' : 'bg-white'} flex items-center justify-center`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
        <Empty 
          image={<EyeOutlined className={`text-4xl ${isDarkMode ? 'text-neutral-500' : 'text-gray-300'}`} />}
          description={<span style={isDarkMode ? {color: '#a3a3a3'} : {}}>Select an HTML file to preview</span>}
        />
      </div>
    );
  }

  return (
    <div className={`h-full ${isDarkMode ? '' : 'bg-white'}`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
      <div className={`p-3 border-b ${isDarkMode ? 'border-neutral-700' : 'border-gray-200 bg-gray-50'}`} style={isDarkMode ? {backgroundColor: '#333333'} : {}}>
        <div className="flex items-center justify-between">
          <Title level={5} className={`mb-0 ${isDarkMode ? '' : 'text-gray-700'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>
            Preview: {fileName}
          </Title>
          <Space>
            <Button 
              icon={<ReloadOutlined />} 
              size="small" 
              onClick={handleRefresh}
              title="Refresh Preview"
            />
            <Button 
              icon={<ExpandOutlined />} 
              size="small" 
              title="Open in New Window"
            />
          </Space>
        </div>
      </div>
      
      <div className="flex-1 overflow-auto" style={{ height: 'calc(100% - 60px)' }}>
        <div className="p-4">
          <Dropdown
            menu={{ items: contextMenuItems }}
            trigger={['contextMenu']}
          >
            <div className={`${isDarkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-white border-gray-200'} border rounded-lg shadow-sm`}>
              <iframe
                key={refreshKey}
                srcDoc={content}
                className="w-full border-0 rounded-lg"
                style={{ 
                  minHeight: '400px', 
                  height: 'calc(100vh - 200px)' 
                }}
                title="HTML Preview"
                sandbox="allow-same-origin allow-scripts"
              />
            </div>
          </Dropdown>
        </div>
      </div>
    </div>
  );
};

export default PreviewPanel;