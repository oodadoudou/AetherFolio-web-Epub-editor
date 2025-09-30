import React, { useState, useRef, useCallback } from 'react';
import { Typography, Modal, Input, App } from 'antd';
import { 
  FolderOutlined, 
  FileTextOutlined,
  FileImageOutlined,
  FileOutlined,
  EditOutlined,
  DeleteOutlined
} from '@ant-design/icons';
import { DndProvider, useDrag, useDrop } from 'react-dnd';
import { HTML5Backend } from 'react-dnd-html5-backend';
import useAppStore from '../store/useAppStore';

const { Title } = Typography;

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

interface FileBrowserProps {
  fileTree: FileNode[];
  selectedFile: string | null;
  onFileSelect: (file: FileNode) => Promise<void>;
  onFileRename?: (oldPath: string, newName: string) => void;
  onFileDelete?: (path: string) => void;
  onFileReorder?: (dragPath: string, hoverPath: string) => void;
  onOpenSearchReplace?: (filePath: string) => void;
  isDarkMode?: boolean;
}

interface ContextMenuProps {
  visible: boolean;
  x: number;
  y: number;
  file: FileNode | null;
  onRename: () => void;
  onDelete: () => void;
  onClose: () => void;
  isDarkMode?: boolean;
}

const ContextMenu: React.FC<ContextMenuProps> = ({ visible, x, y, file, onRename, onDelete, onClose, isDarkMode = false }) => {
  if (!visible || !file) return null;

  return (
    <>
      <div 
        className="fixed inset-0 z-40" 
        onClick={onClose}
      />
      <div 
        className={`fixed z-50 ${isDarkMode ? 'border-neutral-600' : 'bg-white border-gray-200'} rounded-lg shadow-lg py-2 min-w-[160px]`}
        style={{ 
          left: x, 
          top: y,
          backgroundColor: isDarkMode ? '#2d2d2d' : 'white',
          color: isDarkMode ? '#e5e5e5' : 'inherit'
        }}
      >
        <div 
          className={`px-4 py-2 ${isDarkMode ? 'hover:bg-neutral-600' : 'hover:bg-gray-50 text-gray-700'} cursor-pointer flex items-center space-x-2`}
          style={isDarkMode ? {
            color: '#e5e5e5'
          } : {}}
          onClick={onRename}
        >
          <EditOutlined className="text-green-600" />
          <span>重命名</span>
        </div>
        <div 
          className={`px-4 py-2 ${isDarkMode ? 'hover:bg-neutral-600' : 'hover:bg-gray-50'} cursor-pointer flex items-center space-x-2 text-red-600`}
          onClick={onDelete}
        >
          <DeleteOutlined />
          <span>删除</span>
        </div>
      </div>
    </>
  );
};

interface DraggableFileItemProps {
  file: FileNode;
  isSelected: boolean;
  onSelect: () => Promise<void>;
  onContextMenu: (e: React.MouseEvent, file: FileNode) => void;
  onDrop: (dragPath: string, hoverPath: string) => void;
  onOpenSearchReplace?: (filePath: string) => void;
  level: number;
  isDarkMode?: boolean;
  parentPath?: string;
}

const DraggableFileItem: React.FC<DraggableFileItemProps> = ({ 
  file, 
  isSelected, 
  onSelect, 
  onContextMenu, 
  onDrop, 
  onOpenSearchReplace,
  level,
  isDarkMode = false,
  parentPath
}) => {
  const ref = useRef<HTMLDivElement>(null);

  // 定义固定的主要文件夹名称
  const FIXED_FOLDERS = ['Text', 'Styles', 'Images', 'Fonts', 'Miscellaneous'];
  
  // 检查是否为固定文件夹（不允许拖拽）
  const isFixedFolder = file.type === 'directory' && FIXED_FOLDERS.includes(file.name);
  
  // 获取文件所属的主要文件夹
  const getMainFolder = (path: string) => {
    const pathParts = path.split('/');
    for (const folder of FIXED_FOLDERS) {
      if (pathParts.includes(folder)) {
        return folder;
      }
    }
    return null;
  };

  const [{ isDragging }, drag] = useDrag({
    type: 'file',
    item: { path: file.path, type: file.type, parentPath },
    canDrag: () => !isFixedFolder, // 固定文件夹不能拖拽
    collect: (monitor) => ({
      isDragging: monitor.isDragging(),
    }),
  });

  const [{ isOver }, drop] = useDrop({
    accept: 'file',
    drop: (item: { path: string; type: string; parentPath?: string }) => {
      if (item.path !== file.path) {
        // 检查拖拽限制
        const dragMainFolder = getMainFolder(item.path);
        const dropMainFolder = getMainFolder(file.path);
        
        // 只允许在同一主要文件夹内拖拽
        if (dragMainFolder && dropMainFolder && dragMainFolder === dropMainFolder) {
          onDrop(item.path, file.path);
        }
      }
    },
    canDrop: (item) => {
      // 不能拖拽到固定文件夹上
      if (isFixedFolder) return false;
      
      const dragMainFolder = getMainFolder(item.path);
      const dropMainFolder = getMainFolder(file.path);
      
      // 只允许在同一主要文件夹内拖拽
      return dragMainFolder === dropMainFolder;
    },
    collect: (monitor) => ({
      isOver: monitor.isOver() && monitor.canDrop(),
    }),
  });

  drag(drop(ref));

  const getFileIcon = (fileName: string, isDirectory: boolean) => {
    if (isDirectory) {
      return <FolderOutlined />;
    }
    
    const ext = fileName.toLowerCase().split('.').pop();
    switch (ext) {
      case 'html':
      case 'xhtml':
      case 'xml':
        return <FileTextOutlined />;
      case 'css':
        return <FileTextOutlined />;
      case 'txt':
        return <FileTextOutlined />;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'svg':
        return <FileImageOutlined />;
      default:
        return <FileOutlined />;
    }
  };

  return (
    <div
      ref={ref}
      className={`
        flex items-center space-x-2 px-2 py-1 rounded transition-all duration-200 relative
        ${isFixedFolder 
          ? 'cursor-default'
          : 'cursor-pointer'
        }
        ${isSelected 
          ? (isDarkMode ? 'text-green-400' : 'bg-green-100 text-green-800') 
          : (isDarkMode ? 'hover:bg-neutral-700' : 'hover:bg-gray-100')
        }
        ${isDragging ? 'opacity-50' : ''}
        ${isOver && file.type === 'file' 
          ? (isDarkMode ? 'border-l-4 border-green-400' : 'bg-green-50 border-l-4 border-green-500') 
          : ''
        }
        ${isFixedFolder 
          ? (isDarkMode 
              ? 'bg-gradient-to-r from-neutral-700/50 to-transparent border-b border-neutral-600/30' 
              : 'text-gray-600 bg-gradient-to-r from-gray-100/80 to-transparent border-b border-gray-300/40'
            )
          : ''
        }
      `}
      style={{ 
        paddingLeft: `${level * 16 + 8}px`,
        backgroundColor: isSelected && isDarkMode ? '#404040' : undefined,
        color: isDarkMode ? '#e5e5e5' : undefined,
        ...(isFixedFolder && {
          boxShadow: isDarkMode 
            ? 'inset 0 -1px 0 0 rgba(163, 163, 163, 0.2)' 
            : 'inset 0 -1px 0 0 rgba(156, 163, 175, 0.3)'
        })
      }}
      onClick={async () => {
        console.log('🔍 FileBrowser: File clicked:', file.name, file.path);
        console.log('🔍 FileBrowser: File type:', file.type);
        
        try {
          console.log('🔍 FileBrowser: Calling onSelect...');
          await onSelect();
          console.log('✅ FileBrowser: onSelect completed successfully');
          
          // Auto-open search replace for text files
          if (file.type === 'file' && onOpenSearchReplace && 
              (file.name.endsWith('.html') || file.name.endsWith('.xhtml') || file.name.endsWith('.css') || file.name.endsWith('.txt'))) {
            console.log('🔍 FileBrowser: Auto-opening search replace for:', file.path);
            setTimeout(() => {
              onOpenSearchReplace(file.path);
            }, 100);
          }
        } catch (error) {
          console.error('❌ FileBrowser: Error in onSelect:', error);
        }
      }}
      onContextMenu={(e) => onContextMenu(e, file)}
    >
      <div className={`${isFixedFolder ? (isDarkMode ? 'text-neutral-400' : 'text-gray-500') : (isDarkMode ? 'text-neutral-300' : '')}`}>
        {getFileIcon(file.name, file.type === 'directory')}
      </div>
      <span className={`truncate font-medium ${isFixedFolder ? 'tracking-wide' : ''}`}>
        {file.name}
      </span>
      {isDragging && !isFixedFolder && (
        <div className="absolute inset-0 bg-green-200 opacity-30 rounded pointer-events-none" />
      )}
      {isOver && file.type === 'file' && (
        <div className="absolute right-2 top-1/2 transform -translate-y-1/2 text-green-600 text-xs font-medium">
          Drop here
        </div>
      )}
    </div>
  );
};

const FileBrowser: React.FC<FileBrowserProps> = ({ 
  fileTree, 
  selectedFile, 
  onFileSelect, 
  onFileRename, 
  onFileDelete, 
  onFileReorder,
  onOpenSearchReplace,
  isDarkMode = false
}) => {
  const { message } = App.useApp();
  const [contextMenu, setContextMenu] = useState<{
    visible: boolean;
    x: number;
    y: number;
    file: FileNode | null;
  }>({ visible: false, x: 0, y: 0, file: null });
  
  const [renameModal, setRenameModal] = useState<{
    visible: boolean;
    file: FileNode | null;
    newName: string;
  }>({ visible: false, file: null, newName: '' });

  const handleContextMenu = useCallback((e: React.MouseEvent, file: FileNode) => {
    e.preventDefault();
    setContextMenu({
      visible: true,
      x: e.clientX,
      y: e.clientY,
      file
    });
  }, []);

  const handleCloseContextMenu = useCallback(() => {
    setContextMenu({ visible: false, x: 0, y: 0, file: null });
  }, []);

  const handleRename = useCallback(() => {
    if (contextMenu.file) {
      setRenameModal({
        visible: true,
        file: contextMenu.file,
        newName: contextMenu.file.name
      });
    }
    handleCloseContextMenu();
  }, [contextMenu.file, handleCloseContextMenu]);

  const handleDelete = useCallback(() => {
    if (contextMenu.file) {
      Modal.confirm({
        title: '确认删除',
        content: `确定要删除 "${contextMenu.file.name}" 吗？`,
        okText: '删除',
        cancelText: '取消',
        okType: 'danger',
        onOk: () => {
          if (onFileDelete && contextMenu.file) {
            onFileDelete(contextMenu.file.path);
          }
        }
      });
    }
    handleCloseContextMenu();
  }, [contextMenu.file, onFileDelete, handleCloseContextMenu]);

  const handleRenameConfirm = useCallback(() => {
    if (renameModal.file && renameModal.newName.trim() && onFileRename) {
      onFileRename(renameModal.file.path, renameModal.newName.trim());
      message.success('重命名成功');
    }
    setRenameModal({ visible: false, file: null, newName: '' });
  }, [renameModal, onFileRename]);

  const handleDrop = useCallback((dragPath: string, hoverPath: string) => {
    if (onFileReorder) {
      onFileReorder(dragPath, hoverPath);
      message.success('文件顺序已更新');
    }
  }, [onFileReorder]);

  const renderFileTree = useCallback((nodes: FileNode[], level: number = 0, parentPath?: string): React.ReactNode[] => {
    return nodes.map(node => (
      <div key={node.path}>
        <DraggableFileItem
          file={node}
          isSelected={selectedFile === node.path}
          onSelect={() => onFileSelect(node)}
          onContextMenu={handleContextMenu}
          onDrop={handleDrop}
          onOpenSearchReplace={onOpenSearchReplace}
          level={level}
          isDarkMode={isDarkMode}
          parentPath={parentPath}
        />
        {node.children && node.children.length > 0 && (
          <div>
            {renderFileTree(node.children, level + 1, node.path)}
          </div>
        )}
      </div>
    ));
  }, [selectedFile, onFileSelect, handleContextMenu, handleDrop, isDarkMode]);

  return (
    <DndProvider backend={HTML5Backend}>
      <div className={`h-full ${isDarkMode ? 'border-neutral-700' : 'bg-gray-50 border-gray-200'} border-r`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
        <div className={`p-3 border-b ${isDarkMode ? 'border-neutral-700' : 'border-gray-200 bg-white'}`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
          <Title level={5} className={`mb-0 ${isDarkMode ? '' : 'text-gray-700'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>Files</Title>
        </div>
        
        <div className="p-2 overflow-auto" style={{ height: 'calc(100% - 60px)' }}>
          {fileTree.length > 0 ? (
            <div className="space-y-1">
              {renderFileTree(fileTree)}
            </div>
          ) : (
            <div className={`text-center ${isDarkMode ? '' : 'text-gray-500'} mt-8`} style={isDarkMode ? {color: '#a3a3a3'} : {}}>
              <FileOutlined className="text-2xl mb-2" />
              <div>No files loaded</div>
            </div>
          )}
        </div>

        <ContextMenu
          visible={contextMenu.visible}
          x={contextMenu.x}
          y={contextMenu.y}
          file={contextMenu.file}
          onRename={handleRename}
          onDelete={handleDelete}
          onClose={handleCloseContextMenu}
          isDarkMode={isDarkMode}
        />

        <Modal
          title="重命名文件"
          open={renameModal.visible}
          onOk={handleRenameConfirm}
          onCancel={() => setRenameModal({ visible: false, file: null, newName: '' })}
          okText="确认"
          cancelText="取消"
        >
          <Input
            value={renameModal.newName}
            onChange={(e) => setRenameModal(prev => ({ ...prev, newName: e.target.value }))}
            onPressEnter={handleRenameConfirm}
            placeholder="请输入新文件名"
            autoFocus
          />
        </Modal>
      </div>
    </DndProvider>
  );
};

export default FileBrowser;