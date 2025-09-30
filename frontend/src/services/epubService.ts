/**
 * EPUB服务 - 处理EPUB文件的保存、导出、验证等功能
 * 支持实时自动保存、版本控制、批量操作等
 */

// Removed static message import - notifications should be handled by components

export interface EpubMetadata {
  title: string;
  author: string;
  language: string;
  identifier: string;
  publisher?: string;
  date?: string;
  description?: string;
  subject?: string;
  rights?: string;
  contributor?: string;
}

export interface EpubChapter {
  id: string;
  title: string;
  fileName: string;
  content: string;
  order: number;
  wordCount: number;
  lastModified: Date;
}

export interface EpubStructure {
  metadata: EpubMetadata;
  chapters: EpubChapter[];
  resources: EpubResource[];
  toc: TocEntry[];
  spine: SpineEntry[];
}

export interface EpubResource {
  id: string;
  href: string;
  mediaType: string;
  size: number;
  lastModified: Date;
}

export interface TocEntry {
  id: string;
  title: string;
  href: string;
  level: number;
  children: TocEntry[];
}

export interface SpineEntry {
  idref: string;
  linear: boolean;
}

export interface SaveOptions {
  autoSave: boolean;
  createBackup: boolean;
  validateStructure: boolean;
  updateToc: boolean;
  compressImages: boolean;
}

export interface ExportOptions {
  format: 'epub' | 'html' | 'pdf';
  includeImages: boolean;
  includeStyles: boolean;
  validateOutput: boolean;
  compressionLevel: number;
}

export interface ValidationResult {
  isValid: boolean;
  errors: ValidationError[];
  warnings: ValidationWarning[];
  suggestions: string[];
}

export interface ValidationError {
  type: 'structure' | 'content' | 'metadata' | 'resource';
  message: string;
  file?: string;
  line?: number;
  severity: 'error' | 'warning';
}

export interface ValidationWarning {
  type: string;
  message: string;
  file?: string;
  suggestion?: string;
}

export interface BackupInfo {
  id: string;
  timestamp: Date;
  description: string;
  size: number;
  fileCount: number;
}

export interface BatchOperation {
  type: 'save' | 'export' | 'validate' | 'backup';
  files: string[];
  options: any;
  progress: number;
  status: 'pending' | 'running' | 'completed' | 'failed';
  result?: any;
  error?: string;
}

class EpubService {
  private baseUrl = '/api/v1';
  private autoSaveInterval: NodeJS.Timeout | null = null;
  private autoSaveDelay = 30000; // 30秒
  private pendingChanges = new Set<string>();
  private batchOperations = new Map<string, BatchOperation>();

  /**
   * 获取EPUB结构
   */
  async getEpubStructure(sessionId: string): Promise<EpubStructure> {
    try {
      const response = await fetch(`${this.baseUrl}/epub/structure?session_id=${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get EPUB structure: ${response.status}`);
      }
      
      const data = await response.json();
      return data.structure;
    } catch (error) {
      console.error('Failed to get EPUB structure:', error);
      throw error;
    }
  }

  /**
   * 保存单个文件
   */
  async saveFile(
    sessionId: string, 
    filePath: string, 
    content: string, 
    options: Partial<SaveOptions> = {}
  ): Promise<boolean> {
    try {
      const saveOptions: SaveOptions = {
        autoSave: false,
        createBackup: true,
        validateStructure: true,
        updateToc: true,
        compressImages: false,
        ...options
      };

      console.log(`💾 Saving file: ${filePath}`);
      
      const response = await fetch(`${this.baseUrl}/files/save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          file_path: filePath,
          content,
          options: saveOptions
        })
      });
      
      if (!response.ok) {
        throw new Error(`Failed to save file: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        console.log(`✅ File saved successfully: ${filePath}`);
        this.pendingChanges.delete(filePath);
        
        // Success notification should be handled by the calling component
        
        return true;
      } else {
        throw new Error(result.error || 'Save failed');
      }
    } catch (error) {
      console.error('Failed to save file:', error);
      // Error notification should be handled by the calling component
      throw error;
    }
  }

  /**
   * 批量保存文件
   */
  async saveFiles(
    sessionId: string, 
    files: Array<{ path: string; content: string }>, 
    options: Partial<SaveOptions> = {}
  ): Promise<{ success: string[]; failed: string[] }> {
    const operationId = this.generateOperationId();
    const operation: BatchOperation = {
      type: 'save',
      files: files.map(f => f.path),
      options,
      progress: 0,
      status: 'running'
    };
    
    this.batchOperations.set(operationId, operation);
    
    try {
      console.log(`📦 Batch saving ${files.length} files`);
      
      const response = await fetch(`${this.baseUrl}/files/batch-save`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          files,
          options
        })
      });
      
      if (!response.ok) {
        throw new Error(`Batch save failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      operation.status = 'completed';
      operation.progress = 100;
      operation.result = result;
      
      console.log(`✅ Batch save completed: ${result.success.length} success, ${result.failed.length} failed`);
      
      // Batch save notifications should be handled by the calling component
      
      return result;
    } catch (error) {
      operation.status = 'failed';
      operation.error = error instanceof Error ? error.message : 'Unknown error';
      
      console.error('Batch save failed:', error);
      // Error notification should be handled by the calling component
      
      return { success: [], failed: files.map(f => f.path) };
    }
  }

  /**
   * 导出EPUB
   */
  async exportEpub(
    sessionId: string, 
    options: Partial<ExportOptions> = {}
  ): Promise<{ success: boolean; downloadUrl?: string; error?: string }> {
    try {
      const exportOptions: ExportOptions = {
        format: 'epub',
        includeImages: true,
        includeStyles: true,
        validateOutput: true,
        compressionLevel: 6,
        ...options
      };

      console.log(`📤 Exporting EPUB with format: ${exportOptions.format}`);
      
      const response = await fetch(`${this.baseUrl}/epub/export`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          options: exportOptions
        })
      });
      
      if (!response.ok) {
        throw new Error(`Export failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        console.log(`✅ Export completed: ${result.downloadUrl}`);
        
        return {
          success: true,
          downloadUrl: result.downloadUrl
        };
      } else {
        throw new Error(result.error || 'Export failed');
      }
    } catch (error) {
      console.error('Export failed:', error);
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * 验证EPUB结构
   */
  async validateEpub(sessionId: string): Promise<ValidationResult> {
    try {
      console.log('🔍 Validating EPUB structure');
      
      const response = await fetch(`${this.baseUrl}/epub/validate?session_id=${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Validation failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      console.log(`✅ Validation completed: ${result.errors.length} errors, ${result.warnings.length} warnings`);
      
      // Validation notifications should be handled by the calling component
      
      return result;
    } catch (error) {
      console.error('Validation failed:', error);
      // Error notification should be handled by the calling component
      
      return {
        isValid: false,
        errors: [{
          type: 'structure',
          message: error instanceof Error ? error.message : 'Validation failed',
          severity: 'error'
        }],
        warnings: [],
        suggestions: []
      };
    }
  }

  /**
   * 创建备份
   */
  async createBackup(
    sessionId: string, 
    description: string = ''
  ): Promise<{ success: boolean; backupId?: string; error?: string }> {
    try {
      console.log('💾 Creating backup');
      
      const response = await fetch(`${this.baseUrl}/epub/backup`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          description: description || `Backup created at ${new Date().toLocaleString()}`
        })
      });
      
      if (!response.ok) {
        throw new Error(`Backup failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        console.log(`✅ Backup created: ${result.backupId}`);
        
        return {
          success: true,
          backupId: result.backupId
        };
      } else {
        throw new Error(result.error || 'Backup failed');
      }
    } catch (error) {
      console.error('Backup failed:', error);
      // Error notification should be handled by the calling component
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * 获取备份列表
   */
  async getBackups(sessionId: string): Promise<BackupInfo[]> {
    try {
      const response = await fetch(`${this.baseUrl}/epub/backups?session_id=${sessionId}`);
      
      if (!response.ok) {
        throw new Error(`Failed to get backups: ${response.status}`);
      }
      
      const result = await response.json();
      return result.backups || [];
    } catch (error) {
      console.error('Failed to get backups:', error);
      return [];
    }
  }

  /**
   * 恢复备份
   */
  async restoreBackup(
    sessionId: string, 
    backupId: string
  ): Promise<{ success: boolean; error?: string }> {
    try {
      console.log(`🔄 Restoring backup: ${backupId}`);
      
      const response = await fetch(`${this.baseUrl}/epub/restore`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        },
        body: JSON.stringify({
          session_id: sessionId,
          backup_id: backupId
        })
      });
      
      if (!response.ok) {
        throw new Error(`Restore failed: ${response.status}`);
      }
      
      const result = await response.json();
      
      if (result.success) {
        console.log('✅ Backup restored successfully');
        
        return { success: true };
      } else {
        throw new Error(result.error || 'Restore failed');
      }
    } catch (error) {
      console.error('Restore failed:', error);
      // Error notification should be handled by the calling component
      
      return {
        success: false,
        error: error instanceof Error ? error.message : 'Unknown error'
      };
    }
  }

  /**
   * 启用自动保存
   */
  enableAutoSave(sessionId: string, filePath: string, getContent: () => string): void {
    this.pendingChanges.add(filePath);
    
    if (this.autoSaveInterval) {
      return; // 已经启用
    }
    
    console.log('🔄 Auto-save enabled');
    
    this.autoSaveInterval = setInterval(async () => {
      if (this.pendingChanges.size === 0) {
        return;
      }
      
      try {
        const content = getContent();
        await this.saveFile(sessionId, filePath, content, { autoSave: true });
        console.log('💾 Auto-save completed');
      } catch (error) {
        console.warn('Auto-save failed:', error);
      }
    }, this.autoSaveDelay);
  }

  /**
   * 禁用自动保存
   */
  disableAutoSave(): void {
    if (this.autoSaveInterval) {
      clearInterval(this.autoSaveInterval);
      this.autoSaveInterval = null;
      this.pendingChanges.clear();
      console.log('❌ Auto-save disabled');
    }
  }

  /**
   * 标记文件有变更
   */
  markFileChanged(filePath: string): void {
    this.pendingChanges.add(filePath);
  }

  /**
   * 获取批量操作状态
   */
  getBatchOperationStatus(operationId: string): BatchOperation | null {
    return this.batchOperations.get(operationId) || null;
  }

  /**
   * 取消批量操作
   */
  cancelBatchOperation(operationId: string): boolean {
    const operation = this.batchOperations.get(operationId);
    if (operation && operation.status === 'running') {
      operation.status = 'failed';
      operation.error = 'Cancelled by user';
      return true;
    }
    return false;
  }

  /**
   * 清理完成的操作
   */
  cleanupCompletedOperations(): void {
    const toDelete: string[] = [];
    
    this.batchOperations.forEach((operation, id) => {
      if (operation.status === 'completed' || operation.status === 'failed') {
        toDelete.push(id);
      }
    });
    
    toDelete.forEach(id => {
      this.batchOperations.delete(id);
    });
    
    console.log(`🧹 Cleaned up ${toDelete.length} completed operations`);
  }

  /**
   * 生成操作ID
   */
  private generateOperationId(): string {
    return `op_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
  }

  /**
   * 获取统计信息
   */
  getStats(): {
    pendingChanges: number;
    autoSaveEnabled: boolean;
    activeOperations: number;
  } {
    return {
      pendingChanges: this.pendingChanges.size,
      autoSaveEnabled: this.autoSaveInterval !== null,
      activeOperations: Array.from(this.batchOperations.values())
        .filter(op => op.status === 'running').length
    };
  }

  /**
   * 销毁服务
   */
  destroy(): void {
    this.disableAutoSave();
    this.batchOperations.clear();
    this.pendingChanges.clear();
    console.log('💥 EpubService destroyed');
  }
}

// 创建全局实例
export const epubService = new EpubService();

export default EpubService;