import React from 'react';
import { Button, Input, Space, Divider, Tooltip } from 'antd';
import { 
  SaveOutlined, 
  ExportOutlined, 
  UndoOutlined, 
  RedoOutlined,
  SwapOutlined,
  HistoryOutlined,
  BulbOutlined,
  BulbFilled,
  HomeOutlined
} from '@ant-design/icons';

interface ToolbarProps {
  metadata: { title: string; author: string };
  onMetadataChange: (metadata: { title: string; author: string }) => void;
  onBatchReplace: () => void;
  isDarkMode: boolean;
  onThemeToggle: () => void;
  onExitEditor?: () => void;
  onSave?: () => void;
  onExport?: () => void;
  sessionId?: string;
}

const Toolbar: React.FC<ToolbarProps> = ({ metadata, onMetadataChange, onBatchReplace, isDarkMode, onThemeToggle, onExitEditor, onSave, onExport, sessionId }) => {
  const handleTitleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onMetadataChange({ ...metadata, title: e.target.value });
  };

  const handleAuthorChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    onMetadataChange({ ...metadata, author: e.target.value });
  };

  return (
    <div className={`${isDarkMode ? 'border-neutral-700' : 'bg-white border-gray-200'} border-b px-4 py-2`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
      <div className="flex items-center justify-between">
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className={`text-lg font-semibold ${isDarkMode ? '' : 'text-gray-800'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>AetherFolio</span>
            <span className={`text-sm ${isDarkMode ? '' : 'text-gray-500'}`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>EPUB Editor</span>
          </div>
          
          <Divider type="vertical" className="h-6" />
          
          <Space>
            {onExitEditor && (
              <>
                <Tooltip title="Exit Editor">
                  <Button 
                    icon={<HomeOutlined />} 
                    type="text" 
                    onClick={onExitEditor}
                    className="text-red-500 hover:text-red-600"
                  />
                </Tooltip>
                <Divider type="vertical" className="h-4" />
              </>
            )}
            <Tooltip title="Save">
              <Button 
                icon={<SaveOutlined />} 
                type="text" 
                onClick={onSave}
                disabled={!sessionId}
              />
            </Tooltip>
            <Tooltip title="Export">
              <Button 
                icon={<ExportOutlined />} 
                type="text" 
                onClick={onExport}
                disabled={!sessionId}
              />
            </Tooltip>
            <Tooltip title="Undo">
              <Button icon={<UndoOutlined />} type="text" />
            </Tooltip>
            <Tooltip title="Redo">
              <Button icon={<RedoOutlined />} type="text" />
            </Tooltip>
            <Tooltip title="Batch Replace">
              <Button 
                icon={<SwapOutlined />} 
                type="text" 
                onClick={onBatchReplace}
              />
            </Tooltip>
            <Tooltip title="History">
              <Button icon={<HistoryOutlined />} type="text" />
            </Tooltip>
            <Tooltip title={isDarkMode ? "Switch to Light Mode" : "Switch to Dark Mode"}>
              <Button 
                icon={isDarkMode ? <BulbFilled /> : <BulbOutlined />} 
                type="text" 
                onClick={onThemeToggle}
                className={isDarkMode ? 'text-yellow-500' : 'text-gray-600'}
              />
            </Tooltip>
          </Space>
        </div>
        
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className={`text-sm ${isDarkMode ? '' : 'text-gray-600'}`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>Title:</span>
            <Input 
              value={metadata.title}
              onChange={handleTitleChange}
              placeholder="Book Title"
              className="w-48"
              size="small"
            />
          </div>
          
          <div className="flex items-center space-x-2">
            <span className={`text-sm ${isDarkMode ? '' : 'text-gray-600'}`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>Author:</span>
            <Input 
              value={metadata.author}
              onChange={handleAuthorChange}
              placeholder="Author Name"
              className="w-48"
              size="small"
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default Toolbar;