/**
 * 优化的同步管理器V2 - 实现编辑器和预览面板之间的精确同步
 */

import { debounce, throttle } from 'lodash';

export interface SyncPosition {
  line: number;
  column?: number;
  offset?: number;
  elementId?: string;
  scrollTop?: number;
  scrollLeft?: number;
  scrollHeight?: number;
  scrollWidth?: number;
  viewportHeight?: number;
  viewportWidth?: number;
  timestamp?: number;
}

export interface SyncEvent {
  type: 'scroll' | 'cursor' | 'selection' | 'content' | 'click' | 'hover' | 'resize' | 'ready' | 'error';
  source: 'editor' | 'preview';
  position?: SyncPosition;
  content?: string;
  diff?: any;
  metadata?: any;
  timestamp: number;
}

export interface SyncOptions {
  // 同步配置
  bidirectional: boolean;
  scrollSyncDelay: number;
  contentSyncDelay: number;
  smartSync: boolean;
  virtualDOM: boolean;
  incrementalUpdates: boolean;
  lineMapping: boolean;
  
  // 性能配置
  throttleScroll: number;
  debounceContent: number;
  maxDiffSize: number;
  
  // 调试配置
  debug: boolean;
  logEvents: boolean;
  performanceMonitoring: boolean;
}

export interface LineMapping {
  editorLine: number;
  previewElement: string;
  previewLine: number;
  confidence: number;
}

export interface SyncMetrics {
  syncTime: number;
  syncLatency: number;
  syncErrors: number;
  lastSyncTimestamp: number;
  totalSyncs: number;
  successfulSyncs: number;
}

export class OptimizedSyncManagerV2 {
  private options: SyncOptions;
  private editor: any;
  private preview: HTMLIFrameElement | null = null;
  private previewDocument: Document | null = null;
  private previewWindow: Window | null = null;
  
  private editorScrollHandler: any;
  private editorCursorHandler: any;
  private editorChangeHandler: any;
  private previewScrollHandler: any;
  private previewClickHandler: any;
  
  private lineMappings: LineMapping[] = [];
  private lastEditorPosition: SyncPosition | null = null;
  private lastPreviewPosition: SyncPosition | null = null;
  private lastContent: string = '';
  private isEditorScrolling: boolean = false;
  private isPreviewScrolling: boolean = false;
  private isInitialized: boolean = false;
  private isEditorReady: boolean = false;
  private isPreviewReady: boolean = false;
  private pendingEditorScroll: SyncPosition | null = null;
  private pendingPreviewScroll: SyncPosition | null = null;
  private intersectionObserver: IntersectionObserver | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private mutationObserver: MutationObserver | null = null;
  
  private metrics: SyncMetrics = {
    syncTime: 0,
    syncLatency: 0,
    syncErrors: 0,
    lastSyncTimestamp: 0,
    totalSyncs: 0,
    successfulSyncs: 0
  };
  
  constructor(options: Partial<SyncOptions> = {}) {
    this.options = {
      bidirectional: true,
      scrollSyncDelay: 50,
      contentSyncDelay: 300,
      smartSync: true,
      virtualDOM: true,
      incrementalUpdates: true,
      lineMapping: true,
      throttleScroll: 50,
      debounceContent: 300,
      maxDiffSize: 5000,
      debug: false,
      logEvents: false,
      performanceMonitoring: false,
      ...options
    };
    
    this.editorScrollHandler = throttle(this.handleEditorScroll.bind(this), this.options.throttleScroll);
    this.editorCursorHandler = throttle(this.handleEditorCursor.bind(this), this.options.throttleScroll);
    this.editorChangeHandler = debounce(this.handleEditorChange.bind(this), this.options.debounceContent);
    this.previewScrollHandler = throttle(this.handlePreviewScroll.bind(this), this.options.throttleScroll);
    this.previewClickHandler = this.handlePreviewClick.bind(this);
    
    this.log('SyncManager initialized with options:', this.options);
  }
  
  /**
   * 初始化编辑器同步
   */
  public initEditor(editor: any): void {
    this.editor = editor;
    
    // 检测编辑器类型并设置相应的事件监听器
    if (editor.getModel && editor.onDidScrollChange) {
      // Monaco Editor
      this.initMonacoEditor(editor);
    } else if (editor.view && editor.state) {
      // CodeMirror 6
      this.initCodeMirror6(editor);
    } else {
      console.error('Unsupported editor type');
      return;
    }
    
    this.isEditorReady = true;
    this.checkInitialization();
    this.log('Editor initialized');
  }
  
  /**
   * 初始化预览面板同步
   */
  public initPreview(previewFrame: HTMLIFrameElement): void {
    this.preview = previewFrame;
    
    // 等待iframe加载完成
    previewFrame.addEventListener('load', () => {
      this.previewWindow = previewFrame.contentWindow;
      this.previewDocument = previewFrame.contentDocument;
      
      if (!this.previewWindow || !this.previewDocument) {
        console.error('Failed to access preview iframe content');
        return;
      }
      
      // 设置预览面板事件监听器
      this.previewWindow.addEventListener('scroll', this.previewScrollHandler);
      this.previewDocument.addEventListener('click', this.previewClickHandler);
      
      // 设置消息监听器（用于iframe通信）
      window.addEventListener('message', this.handlePreviewMessage.bind(this));
      
      // 设置交叉观察器（用于检测可见元素）
      this.setupIntersectionObserver();
      
      // 设置调整大小观察器（用于处理预览面板大小变化）
      this.setupResizeObserver(previewFrame);
      
      // 设置变异观察器（用于检测DOM变化）
      this.setupMutationObserver();
      
      // 注入辅助脚本到预览iframe
      this.injectHelperScript();
      
      this.isPreviewReady = true;
      this.checkInitialization();
      this.log('Preview initialized');
    });
  }
  
  /**
   * 检查初始化状态
   */
  private checkInitialization(): void {
    if (this.isEditorReady && this.isPreviewReady && !this.isInitialized) {
      this.isInitialized = true;
      this.generateInitialLineMapping();
      this.log('Sync manager fully initialized');
      
      // 发送就绪事件
      this.dispatchSyncEvent({
        type: 'ready',
        source: 'editor',
        timestamp: Date.now()
      });
    }
  }
  
  /**
   * 初始化Monaco编辑器
   */
  private initMonacoEditor(editor: any): void {
    // 滚动事件
    editor.onDidScrollChange((e: any) => {
      this.editorScrollHandler({
        line: editor.getVisibleRanges()[0]?.startLineNumber || 1,
        scrollTop: e.scrollTop,
        scrollLeft: e.scrollLeft,
        scrollHeight: e.scrollHeight,
        viewportHeight: e.viewportHeight
      });
    });
    
    // 光标位置变化事件
    editor.onDidChangeCursorPosition((e: any) => {
      const position = editor.getPosition();
      this.editorCursorHandler({
        line: position.lineNumber,
        column: position.column,
        offset: editor.getModel().getOffsetAt(position)
      });
    });
    
    // 内容变化事件
    editor.onDidChangeModelContent(() => {
      this.editorChangeHandler(editor.getValue());
    });
  }
  
  /**
   * 初始化CodeMirror 6编辑器
   */
  private initCodeMirror6(editor: any): void {
    // 获取视图和状态
    const view = editor.view || editor;
    const state = view.state;
    
    // 滚动事件
    view.scrollDOM.addEventListener('scroll', () => {
      const scrollInfo = {
        scrollTop: view.scrollDOM.scrollTop,
        scrollLeft: view.scrollDOM.scrollLeft,
        scrollHeight: view.scrollDOM.scrollHeight,
        viewportHeight: view.scrollDOM.clientHeight
      };
      
      // 获取可见范围的第一行
      const visibleRange = view.visibleRanges[0];
      const firstVisiblePos = visibleRange ? visibleRange.from : 0;
      const line = state.doc.lineAt(firstVisiblePos).number;
      
      this.editorScrollHandler({
        line,
        ...scrollInfo
      });
    });
    
    // 光标位置变化事件
    view.dom.addEventListener('keyup', () => {
      const selection = view.state.selection.main;
      const pos = selection.head;
      const line = state.doc.lineAt(pos).number;
      const column = pos - state.doc.lineAt(pos).from + 1;
      
      this.editorCursorHandler({
        line,
        column,
        offset: pos
      });
    });
    
    // 内容变化事件
    view.dom.addEventListener('input', () => {
      this.editorChangeHandler(view.state.doc.toString());
    });
  }
  
  /**
   * 处理编辑器滚动事件
   */
  private handleEditorScroll(position: SyncPosition): void {
    if (this.isPreviewScrolling) return;
    
    this.isEditorScrolling = true;
    this.lastEditorPosition = position;
    
    // 记录性能指标开始时间
    const startTime = this.options.performanceMonitoring ? performance.now() : 0;
    
    // 查找对应的预览位置
    const previewPosition = this.findPreviewPositionForEditorLine(position.line);
    
    if (previewPosition) {
      // 发送同步事件
      this.dispatchSyncEvent({
        type: 'scroll',
        source: 'editor',
        position: {
          ...position,
          ...previewPosition,
          timestamp: Date.now()
        },
        timestamp: Date.now()
      });
      
      // 滚动预览面板
      this.scrollPreviewToPosition(previewPosition);
    }
    
    // 更新性能指标
    if (this.options.performanceMonitoring && startTime) {
      this.metrics.syncTime = performance.now() - startTime;
      this.metrics.totalSyncs++;
      this.metrics.successfulSyncs += previewPosition ? 1 : 0;
      this.metrics.lastSyncTimestamp = Date.now();
    }
    
    // 重置滚动状态
    setTimeout(() => {
      this.isEditorScrolling = false;
      
      // 处理待处理的预览滚动
      if (this.pendingPreviewScroll) {
        this.scrollEditorToPosition(this.pendingPreviewScroll);
        this.pendingPreviewScroll = null;
      }
    }, this.options.scrollSyncDelay);
  }
  
  /**
   * 处理编辑器光标位置变化事件
   */
  private handleEditorCursor(position: SyncPosition): void {
    this.lastEditorPosition = position;
    
    // 查找对应的预览位置
    const previewPosition = this.findPreviewPositionForEditorLine(position.line);
    
    if (previewPosition) {
      // 发送同步事件
      this.dispatchSyncEvent({
        type: 'cursor',
        source: 'editor',
        position: {
          ...position,
          ...previewPosition,
          timestamp: Date.now()
        },
        timestamp: Date.now()
      });
      
      // 高亮预览面板中的对应元素
      this.highlightPreviewElement(previewPosition.elementId);
    }
  }
  
  /**
   * 处理编辑器内容变化事件
   */
  private handleEditorChange(content: string): void {
    // 如果内容没有变化，则不处理
    if (content === this.lastContent) return;
    
    // 记录性能指标开始时间
    const startTime = this.options.performanceMonitoring ? performance.now() : 0;
    
    // 计算差异（如果启用了增量更新）
    let diff = null;
    if (this.options.incrementalUpdates && this.lastContent) {
      try {
        // 这里可以使用差异库计算差异，如jsondiffpatch或diff-match-patch
        // 简化实现，实际项目中应使用成熟的差异库
        diff = this.simpleDiff(this.lastContent, content);
        
        // 如果差异太大，则发送完整内容
        if (JSON.stringify(diff).length > this.options.maxDiffSize) {
          diff = null;
        }
      } catch (error) {
        console.error('Error calculating diff:', error);
        diff = null;
      }
    }
    
    this.lastContent = content;
    
    // 发送同步事件
    this.dispatchSyncEvent({
      type: 'content',
      source: 'editor',
      content: diff ? undefined : content,
      diff: diff,
      timestamp: Date.now()
    });
    
    // 更新行映射
    setTimeout(() => {
      this.updateLineMapping();
    }, 100);
    
    // 更新性能指标
    if (this.options.performanceMonitoring && startTime) {
      this.metrics.syncTime = performance.now() - startTime;
      this.metrics.totalSyncs++;
      this.metrics.successfulSyncs++;
      this.metrics.lastSyncTimestamp = Date.now();
    }
  }
  
  /**
   * 处理预览面板滚动事件
   */
  private handlePreviewScroll(event: Event): void {
    if (!this.options.bidirectional || this.isEditorScrolling) return;
    
    this.isPreviewScrolling = true;
    
    const target = event.target as Element;
    const scrollTop = target.scrollTop || window.scrollY;
    const scrollLeft = target.scrollLeft || window.scrollX;
    
    // 查找当前可见的预览元素
    const visibleElement = this.findVisiblePreviewElement();
    
    if (visibleElement) {
      const previewPosition: SyncPosition = {
        elementId: visibleElement.id,
        scrollTop,
        scrollLeft,
        line: 0, // 默认行号，将在后续更新
        timestamp: Date.now()
      };
      
      this.lastPreviewPosition = previewPosition;
      
      // 查找对应的编辑器行
      const editorLine = this.findEditorLineForPreviewElement(visibleElement.id);
      
      if (editorLine) {
        // 发送同步事件
        this.dispatchSyncEvent({
          type: 'scroll',
          source: 'preview',
          position: {
            ...previewPosition,
            line: editorLine,
            timestamp: Date.now()
          },
          timestamp: Date.now()
        });
        
        // 滚动编辑器
        const editorPosition: SyncPosition = {
          line: editorLine,
          timestamp: Date.now()
        };
        
        if (this.isEditorScrolling) {
          this.pendingEditorScroll = editorPosition;
        } else {
          this.scrollEditorToPosition(editorPosition);
        }
      }
    }
    
    // 重置滚动状态
    setTimeout(() => {
      this.isPreviewScrolling = false;
      
      // 处理待处理的编辑器滚动
      if (this.pendingEditorScroll) {
        this.scrollEditorToPosition(this.pendingEditorScroll);
        this.pendingEditorScroll = null;
      }
    }, this.options.scrollSyncDelay);
  }
  
  /**
   * 处理预览面板点击事件
   */
  private handlePreviewClick(event: MouseEvent): void {
    if (!this.options.bidirectional) return;
    
    // 查找被点击的元素
    let target = event.target as HTMLElement;
    let elementId = '';
    
    // 向上查找最近的有ID的元素
    while (target && !elementId) {
      elementId = target.id;
      if (!elementId && target.parentElement) {
        target = target.parentElement;
      } else {
        break;
      }
    }
    
    if (elementId) {
      // 查找对应的编辑器行
      const editorLine = this.findEditorLineForPreviewElement(elementId);
      
      if (editorLine) {
        // 发送同步事件
        this.dispatchSyncEvent({
          type: 'click',
          source: 'preview',
          position: {
            line: editorLine,
            elementId,
            timestamp: Date.now()
          },
          timestamp: Date.now()
        });
        
        // 滚动编辑器并设置光标
        this.scrollEditorToPosition({ line: editorLine });
        this.setEditorCursor(editorLine);
      }
    }
  }
  
  /**
   * 处理预览面板发送的消息
   */
  private handlePreviewMessage(event: MessageEvent): void {
    // 确保消息来自预览iframe
    if (event.source !== this.previewWindow) return;
    
    const data = event.data;
    
    if (data && data.type === 'sync') {
      const syncEvent = data.event as SyncEvent;
      
      switch (syncEvent.type) {
        case 'ready':
          this.log('Preview reported ready');
          this.updateLineMapping();
          break;
          
        case 'click':
          if (syncEvent.position && syncEvent.position.elementId) {
            const editorLine = this.findEditorLineForPreviewElement(syncEvent.position.elementId);
            if (editorLine) {
              this.scrollEditorToPosition({ line: editorLine });
              this.setEditorCursor(editorLine);
            }
          }
          break;
          
        case 'error':
          console.error('Preview error:', syncEvent.metadata);
          this.metrics.syncErrors++;
          break;
      }
    }
  }
  
  /**
   * 滚动预览面板到指定位置
   */
  private scrollPreviewToPosition(position: SyncPosition): void {
    if (!this.previewWindow || !this.previewDocument) return;
    
    // 如果有元素ID，则滚动到该元素
    if (position.elementId) {
      const element = this.previewDocument.getElementById(position.elementId);
      if (element) {
        // 使用平滑滚动
        element.scrollIntoView({
          behavior: 'smooth',
          block: 'start'
        });
        return;
      }
    }
    
    // 如果有滚动位置，则直接滚动
    if (position.scrollTop !== undefined) {
      this.previewWindow.scrollTo({
        top: position.scrollTop,
        left: position.scrollLeft || 0,
        behavior: 'smooth'
      });
    }
  }
  
  /**
   * 滚动编辑器到指定位置
   */
  private scrollEditorToPosition(position: SyncPosition): void {
    if (!this.editor || position.line === undefined) return;
    
    // Monaco Editor
    if (this.editor.revealLine) {
      this.editor.revealLine(position.line, 1); // 1 = 居中
      return;
    }
    
    // CodeMirror 6
    if (this.editor.view) {
      const view = this.editor.view;
      const state = view.state;
      const line = state.doc.line(position.line);
      const pos = line.from;
      
      view.dispatch({
        effects: view.scrollIntoView(pos, { y: 'center' })
      });
    }
  }
  
  /**
   * 设置编辑器光标位置
   */
  private setEditorCursor(line: number, column: number = 1): void {
    if (!this.editor) return;
    
    // Monaco Editor
    if (this.editor.setPosition) {
      this.editor.setPosition({ lineNumber: line, column });
      this.editor.focus();
      return;
    }
    
    // CodeMirror 6
    if (this.editor.view) {
      const view = this.editor.view;
      const state = view.state;
      const lineObj = state.doc.line(line);
      const pos = lineObj.from + Math.min(column - 1, lineObj.length);
      
      view.dispatch({
        selection: { anchor: pos },
        scrollIntoView: true
      });
      view.focus();
    }
  }
  
  /**
   * 高亮预览面板中的元素
   */
  private highlightPreviewElement(elementId?: string): void {
    if (!this.previewDocument || !elementId) return;
    
    // 移除之前的高亮
    const previousHighlight = this.previewDocument.querySelector('.sync-highlight');
    if (previousHighlight) {
      previousHighlight.classList.remove('sync-highlight');
    }
    
    // 添加新的高亮
    const element = this.previewDocument.getElementById(elementId);
    if (element) {
      element.classList.add('sync-highlight');
      
      // 5秒后移除高亮
      setTimeout(() => {
        element.classList.remove('sync-highlight');
      }, 5000);
    }
  }
  
  /**
   * 查找编辑器行对应的预览元素位置
   */
  private findPreviewPositionForEditorLine(line: number): SyncPosition | null {
    if (!this.options.lineMapping || this.lineMappings.length === 0) return null;
    
    // 查找最匹配的映射
    let bestMatch: LineMapping | null = null;
    let bestConfidence = 0;
    
    for (const mapping of this.lineMappings) {
      if (mapping.editorLine === line && mapping.confidence > bestConfidence) {
        bestMatch = mapping;
        bestConfidence = mapping.confidence;
      }
    }
    
    // 如果没有精确匹配，则查找最近的映射
    if (!bestMatch) {
      let minDistance = Number.MAX_VALUE;
      
      for (const mapping of this.lineMappings) {
        const distance = Math.abs(mapping.editorLine - line);
        if (distance < minDistance) {
          minDistance = distance;
          bestMatch = mapping;
          bestConfidence = mapping.confidence * (1 - Math.min(distance / 10, 0.9));
        }
      }
    }
    
    if (bestMatch && bestConfidence > 0.3) {
      return {
        elementId: bestMatch.previewElement,
        line: bestMatch.previewLine
      };
    }
    
    return null;
  }
  
  /**
   * 查找预览元素对应的编辑器行
   */
  private findEditorLineForPreviewElement(elementId: string): number | null {
    if (!this.options.lineMapping || this.lineMappings.length === 0) return null;
    
    // 查找最匹配的映射
    let bestMatch: LineMapping | null = null;
    let bestConfidence = 0;
    
    for (const mapping of this.lineMappings) {
      if (mapping.previewElement === elementId && mapping.confidence > bestConfidence) {
        bestMatch = mapping;
        bestConfidence = mapping.confidence;
      }
    }
    
    if (bestMatch && bestConfidence > 0.3) {
      return bestMatch.editorLine;
    }
    
    return null;
  }
  
  /**
   * 查找当前可见的预览元素
   */
  private findVisiblePreviewElement(): HTMLElement | null {
    if (!this.previewDocument) return null;
    
    // 获取所有有ID的元素
    const elements = this.previewDocument.querySelectorAll('[id]');
    if (elements.length === 0) return null;
    
    // 获取视口信息
    const viewportHeight = this.previewWindow?.innerHeight || 0;
    const scrollTop = this.previewWindow?.scrollY || 0;
    const viewportMiddle = scrollTop + viewportHeight / 2;
    
    // 查找最接近视口中心的元素
    let closestElement: HTMLElement | null = null;
    let minDistance = Number.MAX_VALUE;
    
    elements.forEach((element) => {
      const rect = element.getBoundingClientRect();
      const elementMiddle = rect.top + rect.height / 2;
      const distance = Math.abs(elementMiddle - viewportHeight / 2);
      
      if (distance < minDistance) {
        minDistance = distance;
        closestElement = element as HTMLElement;
      }
    });
    
    return closestElement;
  }
  
  /**
   * 生成初始行映射
   */
  private generateInitialLineMapping(): void {
    if (!this.options.lineMapping) return;
    
    // 请求预览面板生成行映射
    this.sendMessageToPreview({
      type: 'command',
      command: 'generateLineMapping',
      timestamp: Date.now()
    });
  }
  
  /**
   * 更新行映射
   */
  private updateLineMapping(): void {
    if (!this.options.lineMapping) return;
    
    // 请求预览面板更新行映射
    this.sendMessageToPreview({
      type: 'command',
      command: 'updateLineMapping',
      timestamp: Date.now()
    });
  }
  
  /**
   * 设置行映射
   */
  public setLineMapping(mappings: LineMapping[]): void {
    this.lineMappings = mappings;
    this.log(`Line mapping updated with ${mappings.length} entries`);
  }
  
  /**
   * 设置交叉观察器
   */
  private setupIntersectionObserver(): void {
    if (!this.previewDocument || !('IntersectionObserver' in window)) return;
    
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          if (entry.isIntersecting) {
            const element = entry.target as HTMLElement;
            if (element.id) {
              this.log(`Element visible: ${element.id}`);
            }
          }
        });
      },
      {
        root: this.previewDocument.documentElement,
        threshold: 0.5
      }
    );
    
    // 观察所有有ID的元素
    this.previewDocument.querySelectorAll('[id]').forEach(element => {
      this.intersectionObserver?.observe(element);
    });
  }
  
  /**
   * 设置调整大小观察器
   */
  private setupResizeObserver(element: HTMLElement): void {
    if (!('ResizeObserver' in window)) return;
    
    this.resizeObserver = new ResizeObserver(entries => {
      for (const entry of entries) {
        this.log(`Element resized: ${entry.target.id || 'preview'}`);
        
        // 更新行映射
        this.updateLineMapping();
      }
    });
    
    this.resizeObserver.observe(element);
  }
  
  /**
   * 设置变异观察器
   */
  private setupMutationObserver(): void {
    if (!this.previewDocument || !('MutationObserver' in window)) return;
    
    this.mutationObserver = new MutationObserver(mutations => {
      let shouldUpdateMapping = false;
      
      for (const mutation of mutations) {
        if (mutation.type === 'childList' || 
            (mutation.type === 'attributes' && mutation.attributeName === 'id')) {
          shouldUpdateMapping = true;
          break;
        }
      }
      
      if (shouldUpdateMapping) {
        this.log('DOM mutations detected, updating line mapping');
        this.updateLineMapping();
      }
    });
    
    this.mutationObserver.observe(this.previewDocument.body, {
      childList: true,
      subtree: true,
      attributes: true,
      attributeFilter: ['id']
    });
  }
  
  /**
   * 注入辅助脚本到预览iframe
   */
  private injectHelperScript(): void {
    if (!this.previewDocument) return;
    
    const script = this.previewDocument.createElement('script');
    script.textContent = `
      (function() {
        // 设置样式
        const style = document.createElement('style');
        style.textContent = \`
          .sync-highlight {
            background-color: rgba(255, 255, 0, 0.3);
            outline: 2px solid rgba(255, 165, 0, 0.5);
            transition: background-color 0.3s, outline 0.3s;
          }
        \`;
        document.head.appendChild(style);
        
        // 设置消息处理器
        window.addEventListener('message', function(event) {
          if (event.data && event.data.type === 'command') {
            const command = event.data.command;
            
            switch (command) {
              case 'generateLineMapping':
              case 'updateLineMapping':
                generateLineMapping();
                break;
            }
          }
        });
        
        // 生成行映射
        function generateLineMapping() {
          const mappings = [];
          const elements = document.querySelectorAll('[id]');
          
          elements.forEach((element, index) => {
            // 提取元素内容的前几个单词作为特征
            const text = element.textContent || '';
            const words = text.trim().split(/\s+/).slice(0, 5).join(' ');
            
            // 估算行号（这里简化处理，实际应该基于HTML源码分析）
            const previewLine = estimateLineNumber(element);
            
            mappings.push({
              editorLine: index + 1, // 临时占位，后续会更新
              previewElement: element.id,
              previewLine,
              confidence: 0.5, // 初始置信度
              text: words
            });
          });
          
          // 发送映射回主窗口
          window.parent.postMessage({
            type: 'sync',
            event: {
              type: 'ready',
              source: 'preview',
              metadata: {
                mappings
              },
              timestamp: Date.now()
            }
          }, '*');
        }
        
        // 估算元素在源码中的行号
        function estimateLineNumber(element) {
          let line = 1;
          let current = element;
          
          while (current && current !== document.body) {
            line += 2; // 每个父元素估计占用2行
            current = current.parentElement;
          }
          
          return line;
        }
        
        // 点击处理
        document.addEventListener('click', function(event) {
          let target = event.target;
          let elementId = '';
          
          // 向上查找最近的有ID的元素
          while (target && !elementId) {
            elementId = target.id;
            if (!elementId && target.parentElement) {
              target = target.parentElement;
            } else {
              break;
            }
          }
          
          if (elementId) {
            window.parent.postMessage({
              type: 'sync',
              event: {
                type: 'click',
                source: 'preview',
                position: {
                  elementId,
                  timestamp: Date.now()
                },
                timestamp: Date.now()
              }
            }, '*');
          }
        });
        
        // 通知就绪
        window.parent.postMessage({
          type: 'sync',
          event: {
            type: 'ready',
            source: 'preview',
            timestamp: Date.now()
          }
        }, '*');
      })();
    `;
    
    this.previewDocument.head.appendChild(script);
  }
  
  /**
   * 发送消息到预览iframe
   */
  private sendMessageToPreview(message: any): void {
    if (!this.previewWindow) return;
    
    try {
      this.previewWindow.postMessage(message, '*');
    } catch (error) {
      console.error('Error sending message to preview:', error);
    }
  }
  
  /**
   * 发送同步事件
   */
  private dispatchSyncEvent(event: SyncEvent): void {
    // 记录事件
    if (this.options.logEvents) {
      this.log('Sync event:', event);
    }
    
    // 发送到预览iframe
    if (event.source === 'editor') {
      this.sendMessageToPreview({
        type: 'sync',
        event
      });
    }
    
    // 触发自定义事件
    const customEvent = new CustomEvent('sync', { detail: event });
    window.dispatchEvent(customEvent);
  }
  
  /**
   * 简单的差异计算（仅用于演示）
   */
  private simpleDiff(oldText: string, newText: string): any {
    // 这是一个非常简化的差异计算
    // 实际项目中应使用成熟的差异库，如jsondiffpatch或diff-match-patch
    
    if (oldText === newText) return null;
    
    // 查找不同的起始位置
    let start = 0;
    const minLength = Math.min(oldText.length, newText.length);
    
    while (start < minLength && oldText[start] === newText[start]) {
      start++;
    }
    
    // 查找不同的结束位置（从后向前）
    let oldEnd = oldText.length - 1;
    let newEnd = newText.length - 1;
    
    while (oldEnd >= start && newEnd >= start && oldText[oldEnd] === newText[newEnd]) {
      oldEnd--;
      newEnd--;
    }
    
    // 提取差异部分
    const removed = oldText.slice(start, oldEnd + 1);
    const added = newText.slice(start, newEnd + 1);
    
    return {
      start,
      removed,
      added
    };
  }
  
  /**
   * 获取性能指标
   */
  public getMetrics(): SyncMetrics {
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
      lastSyncTimestamp: 0,
      totalSyncs: 0,
      successfulSyncs: 0
    };
  }
  
  /**
   * 销毁同步管理器
   */
  public destroy(): void {
    // 移除编辑器事件监听器
    if (this.editor) {
      // Monaco Editor
      if (this.editor.onDidScrollChange) {
        // 注意：这里应该使用dispose方法，但简化处理
      }
      
      // CodeMirror 6
      if (this.editor.view) {
        const view = this.editor.view;
        view.scrollDOM.removeEventListener('scroll', this.editorScrollHandler);
        view.dom.removeEventListener('keyup', this.editorCursorHandler);
        view.dom.removeEventListener('input', this.editorChangeHandler);
      }
    }
    
    // 移除预览事件监听器
    if (this.previewWindow) {
      this.previewWindow.removeEventListener('scroll', this.previewScrollHandler);
    }
    
    if (this.previewDocument) {
      this.previewDocument.removeEventListener('click', this.previewClickHandler);
    }
    
    // 移除消息监听器
    window.removeEventListener('message', this.handlePreviewMessage);
    
    // 断开观察器
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
      this.intersectionObserver = null;
    }
    
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
      this.resizeObserver = null;
    }
    
    if (this.mutationObserver) {
      this.mutationObserver.disconnect();
      this.mutationObserver = null;
    }
    
    this.log('Sync manager destroyed');
  }
  
  /**
   * 日志输出
   */
  private log(...args: any[]): void {
    if (this.options.debug) {
      console.log('[SyncManager]', ...args);
    }
  }
}

export default OptimizedSyncManagerV2;