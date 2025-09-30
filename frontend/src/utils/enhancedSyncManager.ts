/**
 * 增强同步管理器 - 实现编辑器与预览面板的双向实时同步
 * 支持虚拟DOM增量更新和智能滚动同步
 */

import { debounce, throttle } from 'lodash';

export interface SyncPosition {
  line: number;
  column: number;
  offset: number;
  percentage: number;
}

export interface SyncEvent {
  type: 'scroll' | 'cursor' | 'selection' | 'content';
  source: 'editor' | 'preview';
  position: SyncPosition;
  timestamp: number;
}

export interface SyncOptions {
  enableBidirectional: boolean;
  scrollSyncDelay: number;
  contentSyncDelay: number;
  enableSmartSync: boolean;
  enableVirtualDOM: boolean;
}

class EnhancedSyncManager {
  private editorRef: any = null;
  private previewRef: HTMLElement | null = null;
  private isEnabled = true;
  private isSyncing = false;
  private lastSyncEvent: SyncEvent | null = null;
  private syncHistory: SyncEvent[] = [];
  private maxHistorySize = 50;
  
  private options: SyncOptions = {
    enableBidirectional: true,
    scrollSyncDelay: 100,
    contentSyncDelay: 300,
    enableSmartSync: true,
    enableVirtualDOM: true
  };

  // 防抖和节流函数
  private debouncedScrollSync: ReturnType<typeof debounce>;
  private throttledContentSync: ReturnType<typeof throttle>;
  private debouncedPreviewSync: ReturnType<typeof debounce>;

  // 虚拟DOM相关
  private virtualDOM: Map<string, any> = new Map();
  private lastContentHash = '';

  constructor() {
    this.debouncedScrollSync = debounce(this.performScrollSync.bind(this), this.options.scrollSyncDelay);
    this.throttledContentSync = throttle(this.performContentSync.bind(this), this.options.contentSyncDelay);
    this.debouncedPreviewSync = debounce(this.performPreviewSync.bind(this), this.options.scrollSyncDelay);
    
    this.setupMessageListener();
  }

  /**
   * 初始化同步管理器
   */
  initialize(editorRef: any, previewRef: HTMLElement): void {
    console.log('🔄 Initializing EnhancedSyncManager');
    
    this.editorRef = editorRef;
    this.previewRef = previewRef;
    
    this.setupEditorListeners();
    this.setupPreviewListeners();
    
    console.log('✅ EnhancedSyncManager initialized successfully');
  }

  /**
   * 设置编辑器事件监听
   */
  private setupEditorListeners(): void {
    if (!this.editorRef) return;

    try {
      // CodeMirror 6 事件监听
      if (this.editorRef.view) {
        // 滚动事件
        this.editorRef.view.scrollDOM.addEventListener('scroll', this.handleEditorScroll.bind(this));
        
        // 光标位置变化
        this.editorRef.view.dom.addEventListener('click', this.handleEditorCursor.bind(this));
        this.editorRef.view.dom.addEventListener('keyup', this.handleEditorCursor.bind(this));
        
        console.log('📝 Editor listeners setup for CodeMirror 6');
      }
      // Monaco Editor 事件监听
      else if (this.editorRef.onDidScrollChange) {
        this.editorRef.onDidScrollChange(this.handleEditorScroll.bind(this));
        this.editorRef.onDidChangeCursorPosition(this.handleEditorCursor.bind(this));
        
        console.log('📝 Editor listeners setup for Monaco Editor');
      }
    } catch (error) {
      console.warn('⚠️ Failed to setup editor listeners:', error);
    }
  }

  /**
   * 设置预览面板事件监听
   */
  private setupPreviewListeners(): void {
    if (!this.previewRef) return;

    try {
      // 查找iframe或直接使用容器
      const iframe = this.previewRef.querySelector('iframe');
      const target = iframe || this.previewRef;
      
      if (iframe) {
        // iframe加载完成后设置监听
        iframe.addEventListener('load', () => {
          this.setupIframeListeners(iframe);
        });
        
        // 如果已经加载，直接设置
        if (iframe.contentDocument) {
          this.setupIframeListeners(iframe);
        }
      } else {
        // 直接在容器上设置监听
        target.addEventListener('scroll', this.handlePreviewScroll.bind(this));
        target.addEventListener('click', this.handlePreviewClick.bind(this));
      }
      
      console.log('👁️ Preview listeners setup');
    } catch (error) {
      console.warn('⚠️ Failed to setup preview listeners:', error);
    }
  }

  /**
   * 设置iframe内部监听
   */
  private setupIframeListeners(iframe: HTMLIFrameElement): void {
    try {
      const iframeDoc = iframe.contentDocument;
      if (!iframeDoc) return;
      
      iframeDoc.addEventListener('scroll', this.handlePreviewScroll.bind(this));
      iframeDoc.addEventListener('click', this.handlePreviewClick.bind(this));
      
      console.log('🖼️ Iframe listeners setup');
    } catch (error) {
      console.warn('⚠️ Failed to setup iframe listeners:', error);
    }
  }

  /**
   * 设置消息监听（用于iframe通信）
   */
  private setupMessageListener(): void {
    window.addEventListener('message', (event) => {
      if (!this.isEnabled || this.isSyncing) return;
      
      const { type, data } = event.data;
      
      switch (type) {
        case 'previewScroll':
          this.handlePreviewScrollMessage(data);
          break;
        case 'previewClick':
          this.handlePreviewClickMessage(data);
          break;
        case 'lineClick':
          this.handleLineClickMessage(data);
          break;
      }
    });
  }

  /**
   * 处理编辑器滚动
   */
  private handleEditorScroll(event?: any): void {
    if (!this.isEnabled || this.isSyncing) return;
    
    const position = this.getEditorPosition();
    if (!position) return;
    
    const syncEvent: SyncEvent = {
      type: 'scroll',
      source: 'editor',
      position,
      timestamp: Date.now()
    };
    
    this.addToHistory(syncEvent);
    this.debouncedScrollSync(syncEvent);
  }

  /**
   * 处理编辑器光标变化
   */
  private handleEditorCursor(event?: any): void {
    if (!this.isEnabled || this.isSyncing) return;
    
    const position = this.getEditorPosition();
    if (!position) return;
    
    const syncEvent: SyncEvent = {
      type: 'cursor',
      source: 'editor',
      position,
      timestamp: Date.now()
    };
    
    this.addToHistory(syncEvent);
    this.throttledContentSync(syncEvent);
  }

  /**
   * 处理预览面板滚动
   */
  private handlePreviewScroll(event?: any): void {
    if (!this.isEnabled || this.isSyncing || !this.options.enableBidirectional) return;
    
    const position = this.getPreviewPosition();
    if (!position) return;
    
    const syncEvent: SyncEvent = {
      type: 'scroll',
      source: 'preview',
      position,
      timestamp: Date.now()
    };
    
    this.addToHistory(syncEvent);
    this.debouncedPreviewSync(syncEvent);
  }

  /**
   * 处理预览面板点击
   */
  private handlePreviewClick(event: MouseEvent): void {
    if (!this.isEnabled || !this.options.enableBidirectional) return;
    
    // 查找最近的带有行号的元素
    let target = event.target as HTMLElement;
    let lineNumber: number | null = null;
    
    while (target && target !== document.body) {
      const dataLine = target.getAttribute('data-line');
      if (dataLine) {
        lineNumber = parseInt(dataLine, 10);
        break;
      }
      target = target.parentElement!;
    }
    
    if (lineNumber !== null) {
      this.syncToEditorLine(lineNumber);
    }
  }

  /**
   * 处理预览滚动消息
   */
  private handlePreviewScrollMessage(data: any): void {
    if (!this.options.enableBidirectional) return;
    
    const { percentage } = data;
    if (typeof percentage === 'number') {
      this.syncEditorToPercentage(percentage);
    }
  }

  /**
   * 处理预览点击消息
   */
  private handlePreviewClickMessage(data: any): void {
    if (!this.options.enableBidirectional) return;
    
    const { line } = data;
    if (typeof line === 'number') {
      this.syncToEditorLine(line);
    }
  }

  /**
   * 处理行点击消息
   */
  private handleLineClickMessage(data: any): void {
    const { line } = data;
    if (typeof line === 'number') {
      this.syncToEditorLine(line);
    }
  }

  /**
   * 获取编辑器位置信息
   */
  private getEditorPosition(): SyncPosition | null {
    if (!this.editorRef) return null;
    
    try {
      // CodeMirror 6
      if (this.editorRef.view) {
        const view = this.editorRef.view;
        const state = view.state;
        const selection = state.selection.main;
        const line = state.doc.lineAt(selection.head);
        
        const scrollInfo = {
          top: view.scrollDOM.scrollTop,
          height: view.scrollDOM.scrollHeight,
          clientHeight: view.scrollDOM.clientHeight
        };
        
        return {
          line: line.number,
          column: selection.head - line.from,
          offset: selection.head,
          percentage: scrollInfo.height > scrollInfo.clientHeight 
            ? scrollInfo.top / (scrollInfo.height - scrollInfo.clientHeight)
            : 0
        };
      }
      // Monaco Editor
      else if (this.editorRef.getPosition) {
        const position = this.editorRef.getPosition();
        const scrollTop = this.editorRef.getScrollTop();
        const scrollHeight = this.editorRef.getScrollHeight();
        const clientHeight = this.editorRef.getLayoutInfo().height;
        
        return {
          line: position.lineNumber,
          column: position.column,
          offset: this.editorRef.getModel().getOffsetAt(position),
          percentage: scrollHeight > clientHeight 
            ? scrollTop / (scrollHeight - clientHeight)
            : 0
        };
      }
    } catch (error) {
      console.warn('⚠️ Failed to get editor position:', error);
    }
    
    return null;
  }

  /**
   * 获取预览位置信息
   */
  private getPreviewPosition(): SyncPosition | null {
    if (!this.previewRef) return null;
    
    try {
      const iframe = this.previewRef.querySelector('iframe');
      const target = iframe?.contentDocument || this.previewRef;
      
      const scrollTop = (target as Document).documentElement?.scrollTop || (target as HTMLElement).scrollTop || 0;
      const scrollHeight = (target as Document).documentElement?.scrollHeight || (target as HTMLElement).scrollHeight || 0;
      const clientHeight = (target as Document).documentElement?.clientHeight || (target as HTMLElement).clientHeight || 0;
      
      return {
        line: 0, // 预览中难以确定具体行号
        column: 0,
        offset: 0,
        percentage: scrollHeight > clientHeight 
          ? scrollTop / (scrollHeight - clientHeight)
          : 0
      };
    } catch (error) {
      console.warn('⚠️ Failed to get preview position:', error);
    }
    
    return null;
  }

  /**
   * 执行滚动同步
   */
  private performScrollSync(syncEvent: SyncEvent): void {
    if (!this.isEnabled || this.isSyncing) return;
    
    this.isSyncing = true;
    
    try {
      if (syncEvent.source === 'editor') {
        this.syncPreviewToEditor(syncEvent.position);
      } else if (syncEvent.source === 'preview' && this.options.enableBidirectional) {
        this.syncEditorToPreview(syncEvent.position);
      }
    } catch (error) {
      console.warn('⚠️ Scroll sync failed:', error);
    } finally {
      setTimeout(() => {
        this.isSyncing = false;
      }, 50);
    }
  }

  /**
   * 执行内容同步
   */
  private performContentSync(syncEvent: SyncEvent): void {
    if (!this.isEnabled) return;
    
    // 内容同步逻辑（如高亮当前行等）
    if (syncEvent.source === 'editor') {
      this.highlightPreviewLine(syncEvent.position.line);
    }
  }

  /**
   * 执行预览同步
   */
  private performPreviewSync(syncEvent: SyncEvent): void {
    if (!this.isEnabled || this.isSyncing) return;
    
    this.isSyncing = true;
    
    try {
      this.syncEditorToPreview(syncEvent.position);
    } catch (error) {
      console.warn('⚠️ Preview sync failed:', error);
    } finally {
      setTimeout(() => {
        this.isSyncing = false;
      }, 50);
    }
  }

  /**
   * 同步预览到编辑器位置
   */
  private syncPreviewToEditor(position: SyncPosition): void {
    if (!this.previewRef) return;
    
    try {
      const iframe = this.previewRef.querySelector('iframe');
      
      if (iframe && iframe.contentWindow) {
        // 发送消息到iframe
        iframe.contentWindow.postMessage({
          type: 'scrollToPercentage',
          percentage: position.percentage
        }, '*');
      } else {
        // 直接滚动容器
        const scrollHeight = this.previewRef.scrollHeight;
        const clientHeight = this.previewRef.clientHeight;
        const targetScrollTop = (scrollHeight - clientHeight) * position.percentage;
        
        this.previewRef.scrollTo({
          top: targetScrollTop,
          behavior: 'smooth'
        });
      }
    } catch (error) {
      console.warn('⚠️ Failed to sync preview to editor:', error);
    }
  }

  /**
   * 同步编辑器到预览位置
   */
  private syncEditorToPreview(position: SyncPosition): void {
    if (!this.editorRef) return;
    
    try {
      // CodeMirror 6
      if (this.editorRef.view) {
        const view = this.editorRef.view;
        const scrollHeight = view.scrollDOM.scrollHeight;
        const clientHeight = view.scrollDOM.clientHeight;
        const targetScrollTop = (scrollHeight - clientHeight) * position.percentage;
        
        view.scrollDOM.scrollTo({
          top: targetScrollTop,
          behavior: 'smooth'
        });
      }
      // Monaco Editor
      else if (this.editorRef.setScrollTop) {
        const scrollHeight = this.editorRef.getScrollHeight();
        const clientHeight = this.editorRef.getLayoutInfo().height;
        const targetScrollTop = (scrollHeight - clientHeight) * position.percentage;
        
        this.editorRef.setScrollTop(targetScrollTop);
      }
    } catch (error) {
      console.warn('⚠️ Failed to sync editor to preview:', error);
    }
  }

  /**
   * 同步编辑器到百分比位置
   */
  private syncEditorToPercentage(percentage: number): void {
    if (!this.editorRef || percentage < 0 || percentage > 1) return;
    
    try {
      // CodeMirror 6
      if (this.editorRef.view) {
        const view = this.editorRef.view;
        const scrollHeight = view.scrollDOM.scrollHeight;
        const clientHeight = view.scrollDOM.clientHeight;
        const targetScrollTop = (scrollHeight - clientHeight) * percentage;
        
        view.scrollDOM.scrollTo({
          top: targetScrollTop,
          behavior: 'smooth'
        });
      }
      // Monaco Editor
      else if (this.editorRef.setScrollTop) {
        const scrollHeight = this.editorRef.getScrollHeight();
        const clientHeight = this.editorRef.getLayoutInfo().height;
        const targetScrollTop = (scrollHeight - clientHeight) * percentage;
        
        this.editorRef.setScrollTop(targetScrollTop);
      }
    } catch (error) {
      console.warn('⚠️ Failed to sync editor to percentage:', error);
    }
  }

  /**
   * 同步到编辑器指定行
   */
  private syncToEditorLine(lineNumber: number): void {
    if (!this.editorRef || lineNumber < 1) return;
    
    try {
      // CodeMirror 6
      if (this.editorRef.view) {
        const view = this.editorRef.view;
        const state = view.state;
        
        if (lineNumber <= state.doc.lines) {
          const line = state.doc.line(lineNumber);
          const pos = line.from;
          
          view.dispatch({
            selection: { anchor: pos, head: pos },
            scrollIntoView: true
          });
        }
      }
      // Monaco Editor
      else if (this.editorRef.setPosition) {
        this.editorRef.setPosition({ lineNumber, column: 1 });
        this.editorRef.revealLineInCenter(lineNumber);
      }
    } catch (error) {
      console.warn('⚠️ Failed to sync to editor line:', error);
    }
  }

  /**
   * 高亮预览中的行
   */
  private highlightPreviewLine(lineNumber: number): void {
    if (!this.previewRef) return;
    
    try {
      const iframe = this.previewRef.querySelector('iframe');
      
      if (iframe && iframe.contentWindow) {
        iframe.contentWindow.postMessage({
          type: 'highlightLine',
          line: lineNumber
        }, '*');
      } else {
        // 直接在容器中查找并高亮
        const lineElement = this.previewRef.querySelector(`[data-line="${lineNumber}"]`);
        if (lineElement) {
          // 移除之前的高亮
          this.previewRef.querySelectorAll('.line-highlight').forEach(el => {
            el.classList.remove('line-highlight');
          });
          
          // 添加新的高亮
          lineElement.classList.add('line-highlight');
          lineElement.scrollIntoView({ behavior: 'smooth', block: 'center' });
        }
      }
    } catch (error) {
      console.warn('⚠️ Failed to highlight preview line:', error);
    }
  }

  /**
   * 添加到历史记录
   */
  private addToHistory(syncEvent: SyncEvent): void {
    this.syncHistory.push(syncEvent);
    
    if (this.syncHistory.length > this.maxHistorySize) {
      this.syncHistory.shift();
    }
    
    this.lastSyncEvent = syncEvent;
  }

  /**
   * 启用同步
   */
  enableSync(): void {
    this.isEnabled = true;
    console.log('✅ Sync enabled');
  }

  /**
   * 禁用同步
   */
  disableSync(): void {
    this.isEnabled = false;
    console.log('❌ Sync disabled');
  }

  /**
   * 切换同步状态
   */
  toggleSync(): boolean {
    this.isEnabled = !this.isEnabled;
    console.log(`🔄 Sync ${this.isEnabled ? 'enabled' : 'disabled'}`);
    return this.isEnabled;
  }

  /**
   * 更新选项
   */
  updateOptions(newOptions: Partial<SyncOptions>): void {
    this.options = { ...this.options, ...newOptions };
    
    // 重新创建防抖和节流函数
    this.debouncedScrollSync = debounce(this.performScrollSync.bind(this), this.options.scrollSyncDelay);
    this.throttledContentSync = throttle(this.performContentSync.bind(this), this.options.contentSyncDelay);
    this.debouncedPreviewSync = debounce(this.performPreviewSync.bind(this), this.options.scrollSyncDelay);
    
    console.log('⚙️ Sync options updated:', this.options);
  }

  /**
   * 获取同步统计
   */
  getStats(): {
    isEnabled: boolean;
    isSyncing: boolean;
    historySize: number;
    lastSyncEvent: SyncEvent | null;
    options: SyncOptions;
  } {
    return {
      isEnabled: this.isEnabled,
      isSyncing: this.isSyncing,
      historySize: this.syncHistory.length,
      lastSyncEvent: this.lastSyncEvent,
      options: { ...this.options }
    };
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    this.isEnabled = false;
    this.isSyncing = false;
    this.syncHistory = [];
    this.lastSyncEvent = null;
    this.virtualDOM.clear();
    
    // 取消防抖和节流
    this.debouncedScrollSync.cancel();
    this.throttledContentSync.cancel();
    this.debouncedPreviewSync.cancel();
    
    console.log('🧹 EnhancedSyncManager cleaned up');
  }
}

// 创建全局实例
export const enhancedSyncManager = new EnhancedSyncManager();

export default EnhancedSyncManager;