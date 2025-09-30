import { create } from 'zustand';
import { fileService } from '../services/file';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

interface CurrentFile {
  path: string;
  content: string;
  language: string;
}

interface AppState {
  // Upload state
  isUploadModalVisible: boolean;
  uploadProgress: number;
  
  // Session management
  sessionId: string | null;
  
  // File management
  fileTree: FileNode[];
  currentFile: CurrentFile | null;
  selectedFilePath: string | null;
  modifiedFiles: Map<string, string>; // path -> content mapping for modified files
  
  // Metadata
  metadata: {
    title: string;
    author: string;
  };
  
  // Batch replace
  isBatchReplaceVisible: boolean;
  
  // Theme
  isDarkMode: boolean;
  
  // Actions
  setUploadModalVisible: (visible: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setSessionId: (sessionId: string | null) => void;
  setFileTree: (tree: FileNode[]) => void;
  setCurrentFile: (file: CurrentFile | null) => void;
  setSelectedFilePath: (path: string | null) => void;
  updateFileContent: (path: string, content: string) => void;
  markFileAsModified: (path: string) => void;
  getModifiedFiles: () => Map<string, string>;
  clearModifiedFiles: () => void;
  setMetadata: (metadata: { title: string; author: string }) => void;
  setBatchReplaceVisible: (visible: boolean) => void;
  toggleTheme: () => void;
  
  // File operations
  selectFile: (file: FileNode) => Promise<void>;
  renameFile: (oldPath: string, newName: string) => void;
  deleteFile: (path: string) => void;
  reorderFiles: (dragPath: string, hoverPath: string) => void;
  clearFileTree: () => void;
}

const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  isUploadModalVisible: false,
  uploadProgress: 0,
  sessionId: null,
  fileTree: [],
  currentFile: null,
  selectedFilePath: null,
  modifiedFiles: new Map(),
  metadata: {
    title: '',
    author: ''
  },
  isBatchReplaceVisible: false,
  isDarkMode: false,
  
  // Actions
  setUploadModalVisible: (visible) => set({ isUploadModalVisible: visible }),
  
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  
  setSessionId: (sessionId) => set({ sessionId }),
  
  setFileTree: (tree) => set({ fileTree: tree }),
  
  setCurrentFile: (file) => set({ currentFile: file }),
  
  setSelectedFilePath: (path) => set({ selectedFilePath: path }),
  

  
  setMetadata: (metadata) => set({ metadata }),
  
  setBatchReplaceVisible: (visible) => set({ isBatchReplaceVisible: visible }),
  
  toggleTheme: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  
  selectFile: async (file) => {
    console.log('🔍 useAppStore: selectFile called with:', file);
    const { sessionId } = get();
    
    console.log('🔍 useAppStore: Current sessionId:', sessionId);
    
    if (!sessionId) {
      console.error('❌ useAppStore: No session ID available');
      return;
    }
    
    if (file.type === 'directory') {
      console.log('🔍 useAppStore: Skipping directory selection:', file.name);
      return; // Don't select directories
    }
    
    console.log('🔍 useAppStore: Processing file selection for:', file.name);
    
    // Determine file language based on extension
    const extension = file.name.split('.').pop()?.toLowerCase();
    let language = 'plaintext';
    
    console.log('🔍 useAppStore: File extension:', extension);
    
    if (extension) {
      switch (extension) {
        case 'html':
        case 'xhtml':
          language = 'html';
          break;
        case 'css':
          language = 'css';
          break;
        case 'js':
          language = 'javascript';
          break;
        case 'xml':
          language = 'xml';
          break;
        case 'json':
          language = 'json';
          break;
        case 'txt':
          language = 'plaintext';
          break;
        default:
          language = 'plaintext';
      }
      
      console.log('🔍 useAppStore: Determined language:', language);
      
      // Set selected file path immediately for UI feedback
      console.log('🔍 useAppStore: Setting selectedFilePath to:', file.path);
      set({ selectedFilePath: file.path });
      
      try {
        console.log('🔍 useAppStore: Fetching file content from server...');
        // Fetch real file content from server
        const fileContent = await fileService.getFileContent(sessionId, file.path);
        
        console.log('✅ useAppStore: File content fetched successfully:', {
          path: file.path,
          contentLength: fileContent.content?.length || 0,
          contentPreview: fileContent.content?.substring(0, 100) || 'No content'
        });
        
        set({
          currentFile: {
            path: file.path,
            content: fileContent.content,
            language
          },
          selectedFilePath: file.path
        });
        
        console.log('✅ useAppStore: File selection completed successfully');
      } catch (error) {
        console.error('❌ useAppStore: Failed to load file content:', error);
        console.error('❌ useAppStore: Error details:', {
          message: error.message,
          stack: error.stack,
          sessionId,
          filePath: file.path
        });
        
        // Show error to user instead of fallback to mock content
        alert(`无法加载文件内容: ${error.message || '未知错误'}\n\n请检查:\n1. 网络连接是否正常\n2. 后端服务是否运行\n3. 会话是否有效`);
        
        // Clear current file on error
        set({
          currentFile: null,
          selectedFilePath: null
        });
      }
    }
  },

  renameFile: (oldPath, newName) => {
    const { fileTree, currentFile, selectedFilePath } = get();
    
    const renameInTree = (nodes: FileNode[]): FileNode[] => {
      return nodes.map(node => {
        if (node.path === oldPath) {
          const pathParts = oldPath.split('/');
          pathParts[pathParts.length - 1] = newName;
          const newPath = pathParts.join('/');
          
          return {
            ...node,
            name: newName,
            path: newPath
          };
        }
        
        if (node.children) {
          return {
            ...node,
            children: renameInTree(node.children)
          };
        }
        
        return node;
      });
    };
    
    const newFileTree = renameInTree(fileTree);
    const updates: Partial<AppState> = { fileTree: newFileTree };
    
    // Update current file path if it matches the renamed file
    if (currentFile && currentFile.path === oldPath) {
      const pathParts = oldPath.split('/');
      pathParts[pathParts.length - 1] = newName;
      const newPath = pathParts.join('/');
      
      updates.currentFile = {
        ...currentFile,
        path: newPath
      };
    }
    
    // Update selected file path if it matches
    if (selectedFilePath === oldPath) {
      const pathParts = oldPath.split('/');
      pathParts[pathParts.length - 1] = newName;
      updates.selectedFilePath = pathParts.join('/');
    }
    
    set(updates);
  },

  deleteFile: (path) => {
    const { fileTree, currentFile, selectedFilePath } = get();
    
    const deleteFromTree = (nodes: FileNode[]): FileNode[] => {
      return nodes.filter(node => {
        if (node.path === path) {
          return false;
        }
        
        if (node.children) {
          node.children = deleteFromTree(node.children);
        }
        
        return true;
      });
    };
    
    const newFileTree = deleteFromTree(fileTree);
    const updates: Partial<AppState> = { fileTree: newFileTree };
    
    // Clear current file if it was deleted
    if (currentFile && currentFile.path === path) {
      updates.currentFile = null;
    }
    
    // Clear selected file if it was deleted
    if (selectedFilePath === path) {
      updates.selectedFilePath = null;
    }
    
    set(updates);
  },

  reorderFiles: (dragPath, hoverPath) => {
    const { fileTree } = get();
    
    // Find the dragged item and its parent
    let draggedItem: FileNode | null = null;
    let draggedParent: FileNode[] | null = null;
    let draggedIndex = -1;
    
    const findDraggedItem = (nodes: FileNode[], parent: FileNode[] | null = null): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].path === dragPath) {
          draggedItem = nodes[i];
          draggedParent = parent || fileTree;
          draggedIndex = i;
          return true;
        }
        
        if (nodes[i].children && findDraggedItem(nodes[i].children, nodes[i].children)) {
          return true;
        }
      }
      return false;
    };
    
    // Find the hover target and its parent
    let hoverParent: FileNode[] | null = null;
    let hoverIndex = -1;
    
    const findHoverTarget = (nodes: FileNode[], parent: FileNode[] | null = null): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].path === hoverPath) {
          hoverParent = parent || fileTree;
          hoverIndex = i;
          return true;
        }
        
        if (nodes[i].children && findHoverTarget(nodes[i].children, nodes[i].children)) {
          return true;
        }
      }
      return false;
    };
    
    findDraggedItem(fileTree);
    findHoverTarget(fileTree);
    
    if (draggedItem && draggedParent && hoverParent && draggedIndex !== -1 && hoverIndex !== -1) {
      // Remove from original position
      draggedParent.splice(draggedIndex, 1);
      
      // Insert at new position
      if (draggedParent === hoverParent && draggedIndex < hoverIndex) {
        hoverIndex--; // Adjust for removal
      }
      hoverParent.splice(hoverIndex, 0, draggedItem);
      
      // Save the new file order to localStorage for persistence
      const newFileTree = [...fileTree];
      localStorage.setItem('aetherfolio_file_order', JSON.stringify(newFileTree));
      
      set({ fileTree: newFileTree });
    }
  },

  clearFileTree: () => {
    set({
      fileTree: [],
      currentFile: null,
      selectedFilePath: null,
      modifiedFiles: new Map(),
      sessionId: null,
      metadata: { title: '', author: '' },
      isUploadModalVisible: false,
      uploadProgress: 0,
      isBatchReplaceVisible: false
    });
    localStorage.removeItem('aetherfolio_file_order');
  },

  // 文件内容更新方法
  updateFileContent: (path, content) => {
    const { currentFile, modifiedFiles } = get();
    
    // 更新当前文件内容
    if (currentFile && currentFile.path === path) {
      set({
        currentFile: {
          ...currentFile,
          content
        }
      });
    }
    
    // 标记文件为已修改
    const newModifiedFiles = new Map(modifiedFiles);
    newModifiedFiles.set(path, content);
    set({ modifiedFiles: newModifiedFiles });
  },

  // 标记文件为已修改
  markFileAsModified: (path) => {
    const { modifiedFiles, currentFile } = get();
    const newModifiedFiles = new Map(modifiedFiles);
    
    // 使用当前文件内容或空字符串
    const content = (currentFile && currentFile.path === path) ? currentFile.content : '';
    newModifiedFiles.set(path, content);
    set({ modifiedFiles: newModifiedFiles });
  },

  // 获取已修改的文件
  getModifiedFiles: () => {
    return get().modifiedFiles;
  },

  // 清除已修改的文件标记
  clearModifiedFiles: () => {
    set({ modifiedFiles: new Map() });
  }
}));

// Mock file content generator function has been removed to fix compilation issues

export default useAppStore;