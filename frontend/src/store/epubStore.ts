/**
 * EPUB存储管理器 - 使用Zustand管理EPUB项目状态
 */

import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { fileService } from '../services/file';

interface FileNode {
  id: string;
  name: string;
  type: 'file' | 'folder';
  path: string;
  children?: FileNode[];
  size?: number;
  modified?: Date;
  content?: string;
}

interface EpubProject {
  id: string;
  name: string;
  sessionId: string;
  fileTree: FileNode[];
  metadata: {
    title: string;
    author: string;
    language?: string;
    identifier?: string;
    description?: string;
    publisher?: string;
    date?: string;
  };
  settings: {
    theme: 'light' | 'dark';
    fontSize: number;
    enableSync: boolean;
    enablePreview: boolean;
    autoSave: boolean;
    autoSaveInterval: number;
  };
  lastModified: Date;
  created: Date;
}

interface EpubStoreState {
  // 项目管理
  currentProject: EpubProject | null;
  recentProjects: EpubProject[];
  
  // 文件管理
  openFiles: Map<string, { content: string; modified: boolean; lastAccess: Date }>;
  currentFile: string | null;
  
  // 最近文件
  recentFiles: string[];
  
  // 缓存管理
  fileContentCache: Map<string, { content: string; timestamp: Date }>;
  
  // 操作历史
  operationHistory: Array<{
    type: 'save' | 'load' | 'create' | 'delete' | 'rename';
    file: string;
    timestamp: Date;
    success: boolean;
  }>;
}

interface EpubStoreActions {
  // 项目操作
  setCurrentProject: (project: EpubProject | null) => void;
  createProject: (name: string, sessionId: string) => void;
  updateProject: (updates: Partial<EpubProject>) => void;
  addRecentProject: (project: EpubProject) => void;
  removeRecentProject: (projectId: string) => void;
  
  // 文件操作
  openFile: (path: string, content: string) => void;
  closeFile: (path: string) => void;
  setCurrentFile: (path: string | null) => void;
  updateFileContent: (path: string, content: string) => void;
  markFileModified: (path: string, modified: boolean) => void;
  
  // 最近文件
  addRecentFile: (path: string) => void;
  removeRecentFile: (path: string) => void;
  clearRecentFiles: () => void;
  
  // 文件内容操作
  loadFileContent: (path: string) => Promise<string>;
  saveFileContent: (path: string, content: string) => Promise<void>;
  
  // 缓存管理
  getCachedContent: (path: string) => string | null;
  setCachedContent: (path: string, content: string) => void;
  clearCache: () => void;
  
  // 操作历史
  addOperation: (operation: Omit<EpubStoreState['operationHistory'][0], 'timestamp'>) => void;
  getOperationHistory: () => EpubStoreState['operationHistory'];
  clearOperationHistory: () => void;
  
  // 工具方法
  getOpenFileCount: () => number;
  getModifiedFiles: () => string[];
  hasUnsavedChanges: () => boolean;
  cleanup: () => void;
}

type EpubStore = EpubStoreState & EpubStoreActions;

export const useEpubStore = create<EpubStore>()(
  persist(
    (set, get) => ({
      // 初始状态
      currentProject: null,
      recentProjects: [],
      openFiles: new Map(),
      currentFile: null,
      recentFiles: [],
      fileContentCache: new Map(),
      operationHistory: [],
      
      // 项目操作
      setCurrentProject: (project) => {
        set({ currentProject: project });
        if (project) {
          get().addRecentProject(project);
        }
      },
      
      createProject: (name, sessionId) => {
        const project: EpubProject = {
          id: `project-${Date.now()}`,
          name,
          sessionId,
          fileTree: [],
          metadata: {
            title: name,
            author: '',
            language: 'zh-CN'
          },
          settings: {
            theme: 'light',
            fontSize: 14,
            enableSync: true,
            enablePreview: true,
            autoSave: true,
            autoSaveInterval: 30000
          },
          lastModified: new Date(),
          created: new Date()
        };
        
        set({ currentProject: project });
        get().addRecentProject(project);
        
        console.log('📁 Project created:', project.name);
      },
      
      updateProject: (updates) => {
        const { currentProject } = get();
        if (!currentProject) return;
        
        const updatedProject = {
          ...currentProject,
          ...updates,
          lastModified: new Date()
        };
        
        set({ currentProject: updatedProject });
        get().addRecentProject(updatedProject);
        
        console.log('📝 Project updated:', updatedProject.name);
      },
      
      addRecentProject: (project) => {
        set((state) => {
          const filtered = state.recentProjects.filter(p => p.id !== project.id);
          return {
            recentProjects: [project, ...filtered].slice(0, 10) // 保留最近10个项目
          };
        });
      },
      
      removeRecentProject: (projectId) => {
        set((state) => ({
          recentProjects: state.recentProjects.filter(p => p.id !== projectId)
        }));
      },
      
      // 文件操作
      openFile: (path, content) => {
        set((state) => {
          const newOpenFiles = new Map(state.openFiles);
          newOpenFiles.set(path, {
            content,
            modified: false,
            lastAccess: new Date()
          });
          
          return {
            openFiles: newOpenFiles,
            currentFile: path
          };
        });
        
        get().addRecentFile(path);
        get().setCachedContent(path, content);
        
        console.log('📂 File opened:', path);
      },
      
      closeFile: (path) => {
        set((state) => {
          const newOpenFiles = new Map(state.openFiles);
          newOpenFiles.delete(path);
          
          return {
            openFiles: newOpenFiles,
            currentFile: state.currentFile === path ? null : state.currentFile
          };
        });
        
        console.log('📄 File closed:', path);
      },
      
      setCurrentFile: (path) => {
        set({ currentFile: path });
        if (path) {
          get().addRecentFile(path);
        }
      },
      
      updateFileContent: (path, content) => {
        set((state) => {
          const newOpenFiles = new Map(state.openFiles);
          const existingFile = newOpenFiles.get(path);
          
          if (existingFile) {
            newOpenFiles.set(path, {
              ...existingFile,
              content,
              modified: true,
              lastAccess: new Date()
            });
          }
          
          return { openFiles: newOpenFiles };
        });
        
        get().setCachedContent(path, content);
      },
      
      markFileModified: (path, modified) => {
        set((state) => {
          const newOpenFiles = new Map(state.openFiles);
          const existingFile = newOpenFiles.get(path);
          
          if (existingFile) {
            newOpenFiles.set(path, {
              ...existingFile,
              modified
            });
          }
          
          return { openFiles: newOpenFiles };
        });
      },
      
      // 最近文件
      addRecentFile: (path) => {
        set((state) => {
          const filtered = state.recentFiles.filter(f => f !== path);
          return {
            recentFiles: [path, ...filtered].slice(0, 20) // 保留最近20个文件
          };
        });
      },
      
      removeRecentFile: (path) => {
        set((state) => ({
          recentFiles: state.recentFiles.filter(f => f !== path)
        }));
      },
      
      clearRecentFiles: () => {
        set({ recentFiles: [] });
      },
      
      // 文件内容操作
      loadFileContent: async (path) => {
        const { currentProject, getCachedContent, setCachedContent, addOperation } = get();
        
        if (!currentProject) {
          throw new Error('No current project');
        }
        
        try {
          // 检查缓存
          const cached = getCachedContent(path);
          if (cached) {
            addOperation({ type: 'load', file: path, success: true });
            return cached;
          }
          
          // 从服务器加载
          const response = await fileService.getFileContent(currentProject.sessionId, path);
          const content = response.content || '';
          
          // 缓存内容
          setCachedContent(path, content);
          
          addOperation({ type: 'load', file: path, success: true });
          
          console.log('📥 File content loaded:', path);
          return content;
        } catch (error) {
          addOperation({ type: 'load', file: path, success: false });
          console.error('❌ Failed to load file content:', error);
          throw error;
        }
      },
      
      saveFileContent: async (path, content) => {
        const { currentProject, setCachedContent, markFileModified, addOperation } = get();
        
        if (!currentProject) {
          throw new Error('No current project');
        }
        
        try {
          // 保存到服务器
          await fileService.saveFileContent(currentProject.sessionId, path, content);
          
          // 更新缓存和状态
          setCachedContent(path, content);
          markFileModified(path, false);
          
          addOperation({ type: 'save', file: path, success: true });
          
          console.log('💾 File content saved:', path);
        } catch (error) {
          addOperation({ type: 'save', file: path, success: false });
          console.error('❌ Failed to save file content:', error);
          throw error;
        }
      },
      
      // 缓存管理
      getCachedContent: (path) => {
        const { fileContentCache } = get();
        const cached = fileContentCache.get(path);
        
        if (!cached) return null;
        
        // 检查缓存是否过期（30分钟）
        const now = new Date();
        const age = now.getTime() - cached.timestamp.getTime();
        if (age > 30 * 60 * 1000) {
          fileContentCache.delete(path);
          return null;
        }
        
        return cached.content;
      },
      
      setCachedContent: (path, content) => {
        set((state) => {
          const newCache = new Map(state.fileContentCache);
          newCache.set(path, {
            content,
            timestamp: new Date()
          });
          
          // 限制缓存大小
          if (newCache.size > 100) {
            const oldestKey = newCache.keys().next().value;
            newCache.delete(oldestKey);
          }
          
          return { fileContentCache: newCache };
        });
      },
      
      clearCache: () => {
        set({ fileContentCache: new Map() });
        console.log('🧹 Cache cleared');
      },
      
      // 操作历史
      addOperation: (operation) => {
        set((state) => {
          const newHistory = [
            { ...operation, timestamp: new Date() },
            ...state.operationHistory
          ].slice(0, 100); // 保留最近100个操作
          
          return { operationHistory: newHistory };
        });
      },
      
      getOperationHistory: () => {
        return get().operationHistory;
      },
      
      clearOperationHistory: () => {
        set({ operationHistory: [] });
      },
      
      // 工具方法
      getOpenFileCount: () => {
        return get().openFiles.size;
      },
      
      getModifiedFiles: () => {
        const { openFiles } = get();
        const modifiedFiles: string[] = [];
        
        openFiles.forEach((file, path) => {
          if (file.modified) {
            modifiedFiles.push(path);
          }
        });
        
        return modifiedFiles;
      },
      
      hasUnsavedChanges: () => {
        return get().getModifiedFiles().length > 0;
      },
      
      cleanup: () => {
        set({
          openFiles: new Map(),
          currentFile: null,
          fileContentCache: new Map(),
          operationHistory: []
        });
        
        console.log('🧹 Store cleaned up');
      }
    }),
    {
      name: 'epub-store',
      partialize: (state) => ({
        recentProjects: state.recentProjects,
        recentFiles: state.recentFiles,
        currentProject: state.currentProject
      })
    }
  )
);

// 导出类型
export type { EpubProject, FileNode, EpubStore };

// 工具函数
export const createFileNode = (name: string, type: 'file' | 'folder', path: string): FileNode => ({
  id: `${type}-${Date.now()}-${Math.random().toString(36).substr(2, 9)}`,
  name,
  type,
  path,
  children: type === 'folder' ? [] : undefined,
  modified: new Date()
});

export const findFileNode = (nodes: FileNode[], path: string): FileNode | null => {
  for (const node of nodes) {
    if (node.path === path) {
      return node;
    }
    if (node.children) {
      const found = findFileNode(node.children, path);
      if (found) return found;
    }
  }
  return null;
};

export const getFileExtension = (filename: string): string => {
  const lastDot = filename.lastIndexOf('.');
  return lastDot > 0 ? filename.substring(lastDot + 1).toLowerCase() : '';
};

export const isTextFile = (filename: string): boolean => {
  const textExtensions = ['html', 'xhtml', 'xml', 'css', 'js', 'json', 'txt', 'md', 'opf', 'ncx'];
  return textExtensions.includes(getFileExtension(filename));
};

export const formatFileSize = (bytes: number): string => {
  if (bytes === 0) return '0 B';
  
  const k = 1024;
  const sizes = ['B', 'KB', 'MB', 'GB'];
  const i = Math.floor(Math.log(bytes) / Math.log(k));
  
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
};

export default useEpubStore;