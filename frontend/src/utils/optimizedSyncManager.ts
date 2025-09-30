import { debounce } from './debounce';

/**
 * 编辑器行与预览元素的映射关系
 */
interface LineMapping {
  editorLine: number;
  previewElement: HTMLElement;
  elementId: string;
  textContent: string;
  confidence: number;
}

/**
 * 同步配置选项
 */
interface SyncOptions {
  enableSmoothScrolling: boolean;
  scrollDuration: number;
  debounceDelay: number;
  confidenceThreshold: number;
  maxMappingDistance: number;
  enableVirtualScrolling: boolean;
}

/**
 * 滚动状态
 */
interface ScrollState {
  isScrolling: boolean;
  lastScrollTime: number;
  scrollDirection: 'up' | 'down' | null;
  targetElement: HTMLElement | null;
}

const DEFAULT_SYNC_OPTIONS: SyncOptions = {
  enableSmoothScrolling: true,
  scrollDuration: 300,
  debounceDelay: 100,
  confidenceThreshold: 0.7,
  maxMappingDistance: 50,
  enableVirtualScrolling: true
};

/**
 * 优化的同步管理器
 * 实现编辑器与预览面板之间的精确行级同步和平滑滚动
 */
export class OptimizedSyncManager {
  private isEnabled: boolean = true;
  private lineMappings: Map<number, LineMapping> = new Map();
  private reverseMapping: Map<string, number> = new Map();
  private previewDocument: Document | null = null;
  private editorContent: string = '';
  private options: SyncOptions = { ...DEFAULT_SYNC_OPTIONS };
  private scrollState: ScrollState = {
    isScrolling: false,
    lastScrollTime: 0,
    scrollDirection: null,
    targetElement: null
  };
  private animationFrameId: number | null = null;
  private intersectionObserver: IntersectionObserver | null = null;
  private visibleElements: Set<string> = new Set();

  constructor(options?: Partial<SyncOptions>) {
    if (options) {
      this.options = { ...DEFAULT_SYNC_OPTIONS, ...options };
    }
    
    // 创建防抖的同步函数
    this.debouncedSyncToPreview = debounce(
      this.syncToPreview.bind(this),
      this.options.debounceDelay
    );
    
    this.debouncedSyncToEditor = debounce(
      this.syncToEditor.bind(this),
      this.options.debounceDelay
    );
  }

  /**
   * 启用同步
   */
  enableSync(): void {
    this.isEnabled = true;
  }

  /**
   * 禁用同步
   */
  disableSync(): void {
    this.isEnabled = false;
    this.cleanup();
  }

  /**
   * 切换同步状态
   */
  toggleSync(): void {
    if (this.isEnabled) {
      this.disableSync();
    } else {
      this.enableSync();
    }
  }

  /**
   * 初始化同步
   */
  initializeSync(previewDoc: Document, editorContent: string): void {
    this.previewDocument = previewDoc;
    this.editorContent = editorContent;
    
    // 构建行映射
    this.buildLineMappings();
    
    // 设置交叉观察器（用于虚拟滚动优化）
    if (this.options.enableVirtualScrolling) {
      this.setupIntersectionObserver();
    }
  }

  /**
   * 更新预览内容（支持增量更新和虚拟DOM）
   */
  updatePreviewContent(previewDoc: Document, newHtml: string, useVirtualDOM: boolean = false): void {
    if (!this.isEnabled || !previewDoc) return;
    
    try {
      if (useVirtualDOM) {
        // 使用虚拟DOM进行增量更新
        this.updateWithVirtualDOM(previewDoc, newHtml);
      } else {
        // 直接更新DOM
        previewDoc.body.innerHTML = newHtml;
      }
      
      // 重新构建映射
      this.editorContent = newHtml;
      this.buildLineMappings();
      
    } catch (error) {
      console.error('Error updating preview content:', error);
    }
  }

  /**
   * 使用虚拟DOM进行增量更新
   */
  private updateWithVirtualDOM(previewDoc: Document, newHtml: string): void {
    // 创建临时容器来解析新HTML
    const tempDiv = previewDoc.createElement('div');
    tempDiv.innerHTML = newHtml;
    
    // 比较并更新差异
    this.diffAndPatch(previewDoc.body, tempDiv);
  }

  /**
   * DOM差异比较和补丁应用
   */
  private diffAndPatch(oldNode: Node, newNode: Node): void {
    // 简化的DOM diff算法
    if (oldNode.nodeType !== newNode.nodeType) {
      oldNode.parentNode?.replaceChild(newNode.cloneNode(true), oldNode);
      return;
    }
    
    if (oldNode.nodeType === Node.TEXT_NODE) {
      if (oldNode.textContent !== newNode.textContent) {
        oldNode.textContent = newNode.textContent;
      }
      return;
    }
    
    if (oldNode.nodeType === Node.ELEMENT_NODE) {
      const oldElement = oldNode as Element;
      const newElement = newNode as Element;
      
      // 更新属性
      this.updateAttributes(oldElement, newElement);
      
      // 递归更新子节点
      const oldChildren = Array.from(oldElement.childNodes);
      const newChildren = Array.from(newElement.childNodes);
      
      const maxLength = Math.max(oldChildren.length, newChildren.length);
      
      for (let i = 0; i < maxLength; i++) {
        if (i >= oldChildren.length) {
          // 添加新节点
          oldElement.appendChild(newChildren[i].cloneNode(true));
        } else if (i >= newChildren.length) {
          // 删除旧节点
          oldElement.removeChild(oldChildren[i]);
        } else {
          // 递归比较
          this.diffAndPatch(oldChildren[i], newChildren[i]);
        }
      }
    }
  }

  /**
   * 更新元素属性
   */
  private updateAttributes(oldElement: Element, newElement: Element): void {
    // 移除旧属性
    Array.from(oldElement.attributes).forEach(attr => {
      if (!newElement.hasAttribute(attr.name)) {
        oldElement.removeAttribute(attr.name);
      }
    });
    
    // 添加或更新新属性
    Array.from(newElement.attributes).forEach(attr => {
      if (oldElement.getAttribute(attr.name) !== attr.value) {
        oldElement.setAttribute(attr.name, attr.value);
      }
    });
  }

  /**
   * 构建行映射关系
   */
  private buildLineMappings(): void {
    if (!this.previewDocument || !this.editorContent) return;
    
    this.lineMappings.clear();
    this.reverseMapping.clear();
    
    const editorLines = this.editorContent.split('\n');
    const previewElements = this.getAllTextElements(this.previewDocument.body);
    
    // 为每个预览元素添加唯一ID
    previewElements.forEach((element, index) => {
      if (!element.id) {
        element.id = `preview-element-${index}`;
      }
    });
    
    // 构建映射关系
    editorLines.forEach((line, lineNumber) => {
      const trimmedLine = line.trim();
      if (trimmedLine.length === 0) return;
      
      // 查找最匹配的预览元素
      const bestMatch = this.findBestMatchingElement(trimmedLine, previewElements);
      
      if (bestMatch && bestMatch.confidence >= this.options.confidenceThreshold) {
        const mapping: LineMapping = {
          editorLine: lineNumber + 1,
          previewElement: bestMatch.element,
          elementId: bestMatch.element.id,
          textContent: trimmedLine,
          confidence: bestMatch.confidence
        };
        
        this.lineMappings.set(lineNumber + 1, mapping);
        this.reverseMapping.set(bestMatch.element.id, lineNumber + 1);
      }
    });
  }

  /**
   * 获取所有文本元素
   */
  private getAllTextElements(container: Element): HTMLElement[] {
    const elements: HTMLElement[] = [];
    const walker = document.createTreeWalker(
      container,
      NodeFilter.SHOW_ELEMENT,
      {
        acceptNode: (node: Node) => {
          const element = node as HTMLElement;
          // 只包含有文本内容的元素
          if (element.textContent && element.textContent.trim().length > 0) {
            return NodeFilter.FILTER_ACCEPT;
          }
          return NodeFilter.FILTER_SKIP;
        }
      }
    );
    
    let node: Node | null;
    while (node = walker.nextNode()) {
      elements.push(node as HTMLElement);
    }
    
    return elements;
  }

  /**
   * 查找最匹配的预览元素
   */
  private findBestMatchingElement(
    editorText: string, 
    previewElements: HTMLElement[]
  ): { element: HTMLElement; confidence: number } | null {
    let bestMatch: { element: HTMLElement; confidence: number } | null = null;
    
    for (const element of previewElements) {
      const elementText = element.textContent?.trim() || '';
      const confidence = this.calculateTextSimilarity(editorText, elementText);
      
      if (!bestMatch || confidence > bestMatch.confidence) {
        bestMatch = { element, confidence };
      }
    }
    
    return bestMatch;
  }

  /**
   * 计算文本相似度
   */
  private calculateTextSimilarity(text1: string, text2: string): number {
    if (text1 === text2) return 1.0;
    if (text1.length === 0 || text2.length === 0) return 0.0;
    
    // 使用编辑距离算法计算相似度
    const maxLength = Math.max(text1.length, text2.length);
    const distance = this.levenshteinDistance(text1, text2);
    
    return 1 - (distance / maxLength);
  }

  /**
   * 计算编辑距离
   */
  private levenshteinDistance(str1: string, str2: string): number {
    const matrix: number[][] = [];
    
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
   * 设置交叉观察器（用于虚拟滚动优化）
   */
  private setupIntersectionObserver(): void {
    if (!this.previewDocument) return;
    
    this.intersectionObserver = new IntersectionObserver(
      (entries) => {
        entries.forEach(entry => {
          const elementId = (entry.target as HTMLElement).id;
          if (entry.isIntersecting) {
            this.visibleElements.add(elementId);
          } else {
            this.visibleElements.delete(elementId);
          }
        });
      },
      {
        root: null,
        rootMargin: '50px',
        threshold: 0.1
      }
    );
    
    // 观察所有映射的元素
    this.lineMappings.forEach(mapping => {
      this.intersectionObserver?.observe(mapping.previewElement);
    });
  }

  /**
   * 防抖的同步到预览函数
   */
  private debouncedSyncToPreview: (line: number, percentage?: number) => void;

  /**
   * 防抖的同步到编辑器函数
   */
  private debouncedSyncToEditor: (element: HTMLElement) => void;

  /**
   * 同步编辑器行到预览
   */
  syncEditorToPreview(line: number, percentage?: number): void {
    if (!this.isEnabled) return;
    this.debouncedSyncToPreview(line, percentage);
  }

  /**
   * 实际的同步到预览实现
   */
  private syncToPreview(line: number, percentage?: number): void {
    if (!this.previewDocument || this.scrollState.isScrolling) return;
    
    const mapping = this.lineMappings.get(line);
    if (mapping) {
      this.scrollToElement(mapping.previewElement, percentage);
    } else {
      // 如果没有直接映射，尝试找到最近的映射
      const nearestMapping = this.findNearestMapping(line);
      if (nearestMapping) {
        this.scrollToElement(nearestMapping.previewElement, percentage);
      }
    }
  }

  /**
   * 同步预览元素到编辑器
   */
  syncPreviewToEditor(element: HTMLElement): void {
    if (!this.isEnabled) return;
    this.debouncedSyncToEditor(element);
  }

  /**
   * 实际的同步到编辑器实现
   */
  private syncToEditor(element: HTMLElement): void {
    const line = this.reverseMapping.get(element.id);
    if (line) {
      // 这里需要通过回调通知编辑器滚动到指定行
      // 具体实现依赖于编辑器组件的接口
      this.notifyEditorScroll(line);
    }
  }

  /**
   * 查找最近的映射
   */
  private findNearestMapping(targetLine: number): LineMapping | null {
    let nearestMapping: LineMapping | null = null;
    let minDistance = Infinity;
    
    this.lineMappings.forEach(mapping => {
      const distance = Math.abs(mapping.editorLine - targetLine);
      if (distance < minDistance && distance <= this.options.maxMappingDistance) {
        minDistance = distance;
        nearestMapping = mapping;
      }
    });
    
    return nearestMapping;
  }

  /**
   * 滚动到指定元素
   */
  private scrollToElement(element: HTMLElement, percentage?: number): void {
    if (!this.previewDocument) return;
    
    this.scrollState.isScrolling = true;
    this.scrollState.lastScrollTime = Date.now();
    this.scrollState.targetElement = element;
    
    if (this.options.enableSmoothScrolling) {
      this.smoothScrollToElement(element, percentage);
    } else {
      element.scrollIntoView({ block: 'center' });
      this.scrollState.isScrolling = false;
    }
  }

  /**
   * 平滑滚动到元素
   */
  private smoothScrollToElement(element: HTMLElement, percentage?: number): void {
    const container = this.previewDocument?.defaultView || window;
    const targetRect = element.getBoundingClientRect();
    const containerHeight = container.innerHeight;
    
    // 计算目标滚动位置
    let targetY = targetRect.top + container.scrollY;
    
    if (percentage !== undefined) {
      // 根据百分比调整位置
      targetY -= containerHeight * (0.5 - percentage);
    } else {
      // 默认居中显示
      targetY -= containerHeight / 2;
    }
    
    const startY = container.scrollY;
    const distance = targetY - startY;
    const startTime = Date.now();
    
    const animateScroll = () => {
      const elapsed = Date.now() - startTime;
      const progress = Math.min(elapsed / this.options.scrollDuration, 1);
      
      // 使用缓动函数
      const easeProgress = this.easeInOutCubic(progress);
      const currentY = startY + distance * easeProgress;
      
      container.scrollTo(0, currentY);
      
      if (progress < 1) {
        this.animationFrameId = requestAnimationFrame(animateScroll);
      } else {
        this.scrollState.isScrolling = false;
        this.animationFrameId = null;
        
        // 高亮目标元素
        this.highlightElement(element);
      }
    };
    
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
    }
    
    this.animationFrameId = requestAnimationFrame(animateScroll);
  }

  /**
   * 缓动函数
   */
  private easeInOutCubic(t: number): number {
    return t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2;
  }

  /**
   * 高亮元素
   */
  private highlightElement(element: HTMLElement): void {
    element.classList.add('preview-highlight');
    
    setTimeout(() => {
      element.classList.remove('preview-highlight');
    }, 2000);
  }

  /**
   * 通知编辑器滚动（需要外部实现）
   */
  private notifyEditorScroll(line: number): void {
    // 这里需要通过事件或回调通知编辑器组件
    // 具体实现依赖于编辑器组件的接口
    const event = new CustomEvent('syncToEditor', {
      detail: { line }
    });
    document.dispatchEvent(event);
  }

  /**
   * 根据预览元素查找对应的编辑器行
   */
  findEditorLineFromPreviewElement(element: HTMLElement): number {
    // 向上遍历DOM树，查找有映射的元素
    let currentElement: HTMLElement | null = element;
    
    while (currentElement) {
      const line = this.reverseMapping.get(currentElement.id);
      if (line) {
        return line;
      }
      currentElement = currentElement.parentElement;
    }
    
    return 0;
  }

  /**
   * 获取同步统计信息
   */
  getStats(): {
    totalMappings: number;
    averageConfidence: number;
    visibleElements: number;
    isEnabled: boolean;
  } {
    const mappings = Array.from(this.lineMappings.values());
    const averageConfidence = mappings.length > 0 
      ? mappings.reduce((sum, mapping) => sum + mapping.confidence, 0) / mappings.length 
      : 0;
    
    return {
      totalMappings: mappings.length,
      averageConfidence,
      visibleElements: this.visibleElements.size,
      isEnabled: this.isEnabled
    };
  }

  /**
   * 更新同步选项
   */
  updateOptions(newOptions: Partial<SyncOptions>): void {
    this.options = { ...this.options, ...newOptions };
    
    // 重新创建防抖函数
    this.debouncedSyncToPreview = debounce(
      this.syncToPreview.bind(this),
      this.options.debounceDelay
    );
    
    this.debouncedSyncToEditor = debounce(
      this.syncToEditor.bind(this),
      this.options.debounceDelay
    );
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    // 取消动画帧
    if (this.animationFrameId) {
      cancelAnimationFrame(this.animationFrameId);
      this.animationFrameId = null;
    }
    
    // 清理交叉观察器
    if (this.intersectionObserver) {
      this.intersectionObserver.disconnect();
      this.intersectionObserver = null;
    }
    
    // 清理映射
    this.lineMappings.clear();
    this.reverseMapping.clear();
    this.visibleElements.clear();
    
    // 重置状态
    this.scrollState = {
      isScrolling: false,
      lastScrollTime: 0,
      scrollDirection: null,
      targetElement: null
    };
  }
}

export default OptimizedSyncManager;