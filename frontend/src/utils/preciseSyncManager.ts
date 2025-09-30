/**
 * 精确同步管理器 - 实现编辑器与预览面板的精确双向同步
 * 基于AST解析和位置映射的高精度同步机制
 */

import { debounce, throttle } from 'lodash';
import { EditorView } from '@codemirror/view';
import { VirtualDOMPreviewEngine } from './virtualDOMPreviewEngine';

// 同步位置接口
export interface SyncPosition {
  line: number;
  column: number;
  offset: number;
  percentage: number;
  elementId?: string;
  timestamp: number;
}

// 同步事件接口
export interface SyncEvent {
  type: 'scroll' | 'cursor' | 'content' | 'click';
  source: 'editor' | 'preview';
  position: SyncPosition;
  syncTime?: number;
  syncLatency?: number;
  target?: HTMLElement;
}

// 同步设置接口
export interface SyncSettings {
  bidirectional: boolean;
  scrollSyncDelay: number;
  contentSyncDelay: number;
  smartSync: boolean;
  lineMapping: boolean;
  debug: boolean;
}

// 行映射接口
interface LineMapping {
  editorLine: number;
  previewElement: HTMLElement;
  elementId: string;
  confidence: number;
  textContent: string;
}

// 同步选项接口
export interface PreciseSyncOptions {
  editor: EditorView;
  preview: VirtualDOMPreviewEngine;
  settings: SyncSettings;
  onSyncEvent?: (event: SyncEvent) => void;
}

export class PreciseSyncManager {
  private editor: EditorView;
  private preview: VirtualDOMPreviewEngine;
  private settings: SyncSettings;
  private onSyncEvent?: (event: SyncEvent) => void;
  
  private lineMappings: Map<number, LineMapping> = new Map();
  private reverseMapping: Map<string, number> = new Map();
  private isEnabled: boolean = true;
  private isSyncing: boolean = false;
  private lastSyncTime: number = 0;
  
  // 防抖和节流函数
  private debouncedScrollSync: Function;
  private debouncedContentSync: Function;
  private throttledCursorSync: Function;
  
  // 事件监听器
  private editorScrollHandler?: () => void;
  private editorCursorHandler?: () => void;
  private previewScrollHandler?: () => void;
  private previewClickHandler?: (event: MouseEvent) => void;
  
  // 性能指标
  private metrics = {
    syncTime: 0,
    syncLatency: 0,
    syncErrors: 0,
    totalSyncs: 0
  };
  
  constructor(options: PreciseSyncOptions) {
    this.editor = options.editor;
    this.preview = options.preview;
    this.settings = options.settings;
    this.onSyncEvent = options.onSyncEvent;
    
    // 初始化防抖和节流函数
    this.debouncedScrollSync = debounce(this.performScrollSync.bind(this), this.settings.scrollSyncDelay);
    this.debouncedContentSync = debounce(this.performContentSync.bind(this), this.settings.contentSyncDelay);
    this.throttledCursorSync = throttle(this.performCursorSync.bind(this), 100);
    
    this.initialize();
  }
  
  /**
   * 初始化同步管理器
   */
  private initialize(): void {
    try {
      this.setupEditorListeners();
      this.setupPreviewListeners();
      this.buildLineMappings();
      
      if (this.settings.debug) {
        console.log('🔄 Precise sync manager initialized');
      }
    } catch (error) {
      console.error('❌ Failed to initialize sync manager:', error);
      this.metrics.syncErrors++;
    }
  }
  
  /**
   * 设置编辑器事件监听器
   */
  private setupEditorListeners(): void {
    // 滚动同步
    this.editorScrollHandler = () => {
      if (!this.isEnabled || this.isSyncing) return;
      
      const scrollInfo = this.getEditorScrollInfo();
      this.debouncedScrollSync('editor', scrollInfo);
    };
    
    // 光标同步
    this.editorCursorHandler = () => {
      if (!this.isEnabled || this.isSyncing) return;
      
      const cursorInfo = this.getEditorCursorInfo();
      this.throttledCursorSync('editor', cursorInfo);
    };
    
    // 添加事件监听器
    this.editor.scrollDOM.addEventListener('scroll', this.editorScrollHandler);
    this.editor.dom.addEventListener('click', this.editorCursorHandler);
    this.editor.dom.addEventListener('keyup', this.editorCursorHandler);
  }
  
  /**
   * 设置预览面板事件监听器
   */
  private setupPreviewListeners(): void {
    const previewContainer = this.preview.getContainer();
    if (!previewContainer) return;
    
    // 预览滚动同步
    this.previewScrollHandler = () => {
      if (!this.isEnabled || this.isSyncing || !this.settings.bidirectional) return;
      
      const scrollInfo = this.getPreviewScrollInfo();
      this.debouncedScrollSync('preview', scrollInfo);
    };
    
    // 预览点击同步
    this.previewClickHandler = (event: MouseEvent) => {
      if (!this.isEnabled || !this.settings.bidirectional) return;
      
      const clickInfo = this.getPreviewClickInfo(event);
      if (clickInfo) {
        this.syncPreviewToEditor(clickInfo);
      }
    };
    
    previewContainer.addEventListener('scroll', this.previewScrollHandler);
    previewContainer.addEventListener('click', this.previewClickHandler);
  }
  
  /**
   * 构建行映射关系
   */
  private buildLineMappings(): void {
    if (!this.settings.lineMapping) return;
    
    try {
      const content = this.editor.state.doc.toString();
      const lines = content.split('\n');
      const previewElements = this.preview.getAllElements();
      
      this.lineMappings.clear();
      this.reverseMapping.clear();
      
      // 基于内容匹配建立映射
      lines.forEach((line, index) => {
        const trimmedLine = line.trim();
        if (trimmedLine.length === 0) return;
        
        // 查找匹配的预览元素
        const matchedElement = this.findMatchingElement(trimmedLine, previewElements);
        if (matchedElement) {
          const mapping: LineMapping = {
            editorLine: index + 1,
            previewElement: matchedElement.element,
            elementId: matchedElement.id,
            confidence: matchedElement.confidence,
            textContent: trimmedLine
          };
          
          this.lineMappings.set(index + 1, mapping);
          this.reverseMapping.set(matchedElement.id, index + 1);
        }
      });
      
      if (this.settings.debug) {
        console.log(`📍 Built ${this.lineMappings.size} line mappings`);
      }
    } catch (error) {
      console.error('❌ Failed to build line mappings:', error);
      this.metrics.syncErrors++;
    }
  }
  
  /**
   * 查找匹配的预览元素
   */
  private findMatchingElement(content: string, elements: any[]): { element: HTMLElement; id: string; confidence: number } | null {
    let bestMatch = null;
    let bestConfidence = 0;
    
    for (const element of elements) {
      const elementText = element.textContent?.trim() || '';
      const confidence = this.calculateTextSimilarity(content, elementText);
      
      if (confidence > bestConfidence && confidence > 0.7) {
        bestMatch = {
          element: element,
          id: element.id || `element-${Date.now()}-${Math.random()}`,
          confidence
        };
        bestConfidence = confidence;
      }
    }
    
    return bestMatch;
  }
  
  /**
   * 计算文本相似度
   */
  private calculateTextSimilarity(text1: string, text2: string): number {
    if (text1 === text2) return 1;
    if (text1.length === 0 || text2.length === 0) return 0;
    
    // 简单的相似度计算（可以使用更复杂的算法）
    const longer = text1.length > text2.length ? text1 : text2;
    const shorter = text1.length > text2.length ? text2 : text1;
    
    if (longer.length === 0) return 1;
    
    const distance = this.levenshteinDistance(longer, shorter);
    return (longer.length - distance) / longer.length;
  }
  
  /**
   * 计算编辑距离
   */
  private levenshteinDistance(str1: string, str2: string): number {
    const matrix = [];
    
    for (let i = 0; i <= str2.length; i++) {
      matrix[i] = [i];
    }
    
    for (let j = 0; j <= str1.length; j++) {
      matrix[0][j] = j;
    }
    
    for (let i = 1; i <= str2.length; i++) {
      for (let j = 1; j <= str1.length; j++) {
        if (str2.charAt(i - 1) === str1.charAt(j - 1)) {
          matrix[i][j] = matrix[i - 1][j - 1];
        } else {
          matrix[i][j] = Math.min(
            matrix[i - 1][j - 1] + 1,
            matrix[i][j - 1] + 1,
            matrix[i - 1][j] + 1
          );
        }
      }
    }
    
    return matrix[str2.length][str1.length];
  }
  
  /**
   * 获取编辑器滚动信息
   */
  private getEditorScrollInfo(): SyncPosition {
    const scrollTop = this.editor.scrollDOM.scrollTop;
    const scrollHeight = this.editor.scrollDOM.scrollHeight;
    const clientHeight = this.editor.scrollDOM.clientHeight;
    
    const percentage = scrollHeight > clientHeight ? scrollTop / (scrollHeight - clientHeight) : 0;
    const lineInfo = this.editor.lineBlockAtHeight(scrollTop + clientHeight / 2);
    
    return {
      line: this.editor.state.doc.lineAt(lineInfo.from).number,
      column: 0,
      offset: lineInfo.from,
      percentage,
      timestamp: Date.now()
    };
  }
  
  /**
   * 获取编辑器光标信息
   */
  private getEditorCursorInfo(): SyncPosition {
    const selection = this.editor.state.selection.main;
    const line = this.editor.state.doc.lineAt(selection.head);
    
    return {
      line: line.number,
      column: selection.head - line.from,
      offset: selection.head,
      percentage: selection.head / this.editor.state.doc.length,
      timestamp: Date.now()
    };
  }
  
  /**
   * 获取预览滚动信息
   */
  private getPreviewScrollInfo(): SyncPosition {
    const container = this.preview.getContainer();
    if (!container) {
      return { line: 1, column: 0, offset: 0, percentage: 0, timestamp: Date.now() };
    }
    
    const scrollTop = container.scrollTop;
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    
    const percentage = scrollHeight > clientHeight ? scrollTop / (scrollHeight - clientHeight) : 0;
    
    return {
      line: 1, // 需要根据可见元素计算
      column: 0,
      offset: 0,
      percentage,
      timestamp: Date.now()
    };
  }
  
  /**
   * 获取预览点击信息
   */
  private getPreviewClickInfo(event: MouseEvent): SyncPosition | null {
    const target = event.target as HTMLElement;
    if (!target) return null;
    
    const elementId = target.id || target.closest('[id]')?.id;
    if (!elementId) return null;
    
    const editorLine = this.reverseMapping.get(elementId);
    if (!editorLine) return null;
    
    return {
      line: editorLine,
      column: 0,
      offset: 0,
      percentage: 0,
      elementId,
      timestamp: Date.now()
    };
  }
  
  /**
   * 执行滚动同步
   */
  private performScrollSync(source: 'editor' | 'preview', position: SyncPosition): void {
    if (this.isSyncing) return;
    
    const startTime = performance.now();
    this.isSyncing = true;
    
    try {
      if (source === 'editor') {
        this.syncEditorToPreview(position);
      } else {
        this.syncPreviewToEditor(position);
      }
      
      const syncTime = performance.now() - startTime;
      this.metrics.syncTime = syncTime;
      this.metrics.totalSyncs++;
      
      // 触发同步事件
      const syncEvent: SyncEvent = {
        type: 'scroll',
        source,
        position,
        syncTime,
        syncLatency: Date.now() - position.timestamp
      };
      
      this.onSyncEvent?.(syncEvent);
      
      if (this.settings.debug) {
        console.log(`🔄 Scroll sync (${source}):`, syncEvent);
      }
    } catch (error) {
      console.error('❌ Scroll sync failed:', error);
      this.metrics.syncErrors++;
    } finally {
      this.isSyncing = false;
    }
  }
  
  /**
   * 执行光标同步
   */
  private performCursorSync(source: 'editor' | 'preview', position: SyncPosition): void {
    if (this.isSyncing) return;
    
    try {
      if (source === 'editor') {
        this.highlightPreviewLine(position.line);
      }
      
      const syncEvent: SyncEvent = {
        type: 'cursor',
        source,
        position
      };
      
      this.onSyncEvent?.(syncEvent);
    } catch (error) {
      console.error('❌ Cursor sync failed:', error);
      this.metrics.syncErrors++;
    }
  }
  
  /**
   * 执行内容同步
   */
  private performContentSync(content: string): void {
    try {
      this.preview.updateContent(content);
      this.buildLineMappings(); // 重新构建映射
      
      const syncEvent: SyncEvent = {
        type: 'content',
        source: 'editor',
        position: { line: 1, column: 0, offset: 0, percentage: 0, timestamp: Date.now() }
      };
      
      this.onSyncEvent?.(syncEvent);
    } catch (error) {
      console.error('❌ Content sync failed:', error);
      this.metrics.syncErrors++;
    }
  }
  
  /**
   * 同步编辑器到预览
   */
  private syncEditorToPreview(position: SyncPosition): void {
    const container = this.preview.getContainer();
    if (!container) return;
    
    if (this.settings.lineMapping) {
      // 基于行映射的精确同步
      const mapping = this.lineMappings.get(position.line);
      if (mapping) {
        mapping.previewElement.scrollIntoView({
          behavior: 'smooth',
          block: 'center'
        });
        return;
      }
    }
    
    // 基于百分比的同步
    const scrollHeight = container.scrollHeight;
    const clientHeight = container.clientHeight;
    const targetScrollTop = (scrollHeight - clientHeight) * position.percentage;
    
    container.scrollTo({
      top: targetScrollTop,
      behavior: 'smooth'
    });
  }
  
  /**
   * 同步预览到编辑器
   */
  private syncPreviewToEditor(position: SyncPosition): void {
    if (position.elementId) {
      const editorLine = this.reverseMapping.get(position.elementId);
      if (editorLine) {
        this.scrollEditorToLine(editorLine);
        return;
      }
    }
    
    // 基于百分比的同步
    const doc = this.editor.state.doc;
    const targetLine = Math.round(doc.lines * position.percentage);
    this.scrollEditorToLine(Math.max(1, targetLine));
  }
  
  /**
   * 滚动编辑器到指定行
   */
  private scrollEditorToLine(line: number): void {
    const doc = this.editor.state.doc;
    if (line < 1 || line > doc.lines) return;
    
    const lineObj = doc.line(line);
    this.editor.dispatch({
      effects: EditorView.scrollIntoView(lineObj.from, { y: 'center' })
    });
  }
  
  /**
   * 高亮预览行
   */
  private highlightPreviewLine(line: number): void {
    const mapping = this.lineMappings.get(line);
    if (!mapping) return;
    
    // 移除之前的高亮
    const prevHighlighted = this.preview.getContainer()?.querySelector('.sync-highlight');
    if (prevHighlighted) {
      prevHighlighted.classList.remove('sync-highlight');
    }
    
    // 添加新的高亮
    mapping.previewElement.classList.add('sync-highlight');
    
    // 3秒后移除高亮
    setTimeout(() => {
      mapping.previewElement.classList.remove('sync-highlight');
    }, 3000);
  }
  
  /**
   * 启用同步
   */
  public enableSync(): void {
    this.isEnabled = true;
    if (this.settings.debug) {
      console.log('✅ Sync enabled');
    }
  }
  
  /**
   * 禁用同步
   */
  public disableSync(): void {
    this.isEnabled = false;
    if (this.settings.debug) {
      console.log('❌ Sync disabled');
    }
  }
  
  /**
   * 切换同步状态
   */
  public toggleSync(): void {
    this.isEnabled = !this.isEnabled;
    if (this.settings.debug) {
      console.log(`🔄 Sync ${this.isEnabled ? 'enabled' : 'disabled'}`);
    }
  }
  
  /**
   * 更新设置
   */
  public updateSettings(newSettings: Partial<SyncSettings>): void {
    this.settings = { ...this.settings, ...newSettings };
    
    // 重新初始化防抖函数
    this.debouncedScrollSync = debounce(this.performScrollSync.bind(this), this.settings.scrollSyncDelay);
    this.debouncedContentSync = debounce(this.performContentSync.bind(this), this.settings.contentSyncDelay);
  }
  
  /**
   * 获取性能指标
   */
  public getMetrics() {
    return { ...this.metrics };
  }
  
  /**
   * 重置性能指标
   */
  public resetMetrics(): void {
    this.metrics = {
      syncTime: 0,
      syncLatency: 0,
      syncErrors: 0,
      totalSyncs: 0
    };
  }
  
  /**
   * 手动触发内容同步
   */
  public syncContent(content: string): void {
    this.debouncedContentSync(content);
  }
  
  /**
   * 销毁同步管理器
   */
  public destroy(): void {
    // 移除事件监听器
    if (this.editorScrollHandler) {
      this.editor.scrollDOM.removeEventListener('scroll', this.editorScrollHandler);
    }
    if (this.editorCursorHandler) {
      this.editor.dom.removeEventListener('click', this.editorCursorHandler);
      this.editor.dom.removeEventListener('keyup', this.editorCursorHandler);
    }
    
    const previewContainer = this.preview.getContainer();
    if (previewContainer) {
      if (this.previewScrollHandler) {
        previewContainer.removeEventListener('scroll', this.previewScrollHandler);
      }
      if (this.previewClickHandler) {
        previewContainer.removeEventListener('click', this.previewClickHandler);
      }
    }
    
    // 清理数据
    this.lineMappings.clear();
    this.reverseMapping.clear();
    
    if (this.settings.debug) {
      console.log('🗑️ Precise sync manager destroyed');
    }
  }
}

export default PreciseSyncManager;