/**
 * 虚拟DOM预览引擎 - 基于设计文档的高性能预览系统
 * 实现增量更新、资源优化、智能缓存等功能
 */

import { debounce, throttle } from 'lodash';

// 虚拟DOM节点接口
interface VirtualNode {
  id: string;
  type: string;
  tag?: string;
  text?: string;
  attributes?: Record<string, string>;
  children?: VirtualNode[];
  parent?: VirtualNode;
  lineNumber?: number;
  columnNumber?: number;
  hash?: string;
}

// 差异类型
type DiffType = 'add' | 'remove' | 'update' | 'move' | 'text';

// 差异对象
interface VirtualDiff {
  type: DiffType;
  node: VirtualNode;
  oldNode?: VirtualNode;
  newNode?: VirtualNode;
  index?: number;
  newIndex?: number;
}

// 预览设置接口
interface PreviewEngineSettings {
  fontSize: number;
  lineHeight: number;
  zoom: number;
  showLineNumbers: boolean;
  enableImagePreview: boolean;
  smoothScroll: boolean;
  virtualDOM: boolean;
  incrementalUpdate: boolean;
  performanceMonitor: boolean;
  syncEnabled: boolean;
  autoRefresh: boolean;
  theme: 'light' | 'dark';
  resourceOptimization: boolean;
  lazyLoading: boolean;
}

// 资源缓存接口
interface ResourceCache {
  url: string;
  data: string | ArrayBuffer;
  type: string;
  size: number;
  lastAccessed: number;
  hitCount: number;
}

// 性能指标接口
interface EngineMetrics {
  renderTime: number;
  diffTime: number;
  updateTime: number;
  cacheHitRate: number;
  memoryUsage: number;
  domNodes: number;
  virtualNodes: number;
  resourcesLoaded: number;
  resourcesCached: number;
  cacheHits: number;
  cacheMisses: number;
}

// 预览引擎选项
interface PreviewEngineOptions {
  container: HTMLElement;
  settings: PreviewEngineSettings;
  onError?: (error: Error) => void;
  onMetricsUpdate?: (metrics: EngineMetrics) => void;
  onResourceLoad?: (resource: ResourceCache) => void;
}

export class VirtualDOMPreviewEngine {
  private container: HTMLElement;
  private settings: PreviewEngineSettings;
  private onError?: (error: Error) => void;
  private onMetricsUpdate?: (metrics: EngineMetrics) => void;
  private onResourceLoad?: (resource: ResourceCache) => void;
  
  private virtualDOM: VirtualNode | null = null;
  private realDOM: HTMLElement | null = null;
  private resourceCache: Map<string, ResourceCache> = new Map();
  private nodeMap: Map<string, HTMLElement | Text> = new Map();
  private lineMap: Map<number, HTMLElement> = new Map();
  
  private parser: DOMParser;
  private observer: IntersectionObserver | null = null;
  private resizeObserver: ResizeObserver | null = null;
  private mutationObserver: MutationObserver | null = null;
  
  private metrics: EngineMetrics = {
    renderTime: 0,
    diffTime: 0,
    updateTime: 0,
    cacheHitRate: 100,
    memoryUsage: 0,
    domNodes: 0,
    virtualNodes: 0,
    resourcesLoaded: 0,
    resourcesCached: 0,
    cacheHits: 0,
    cacheMisses: 0
  };
  
  private lastContent: string = '';
  private updateQueue: VirtualDiff[] = [];
  private isUpdating: boolean = false;
  private frameId: number | null = null;
  
  // 防抖和节流函数
  private debouncedUpdate: Function;
  private throttledMetricsUpdate: Function;
  
  constructor(options: PreviewEngineOptions) {
    this.container = options.container;
    this.settings = options.settings;
    this.onError = options.onError;
    this.onMetricsUpdate = options.onMetricsUpdate;
    this.onResourceLoad = options.onResourceLoad;
    
    this.parser = new DOMParser();
    
    // 初始化防抖和节流函数
    this.debouncedUpdate = debounce(this.performFullUpdate.bind(this), 100);
    this.throttledMetricsUpdate = throttle(this.updateMetrics.bind(this), 1000);
    
    this.initialize();
  }
  
  /**
   * 初始化预览引擎
   */
  private initialize(): void {
    try {
      // 创建预览容器
      this.createPreviewContainer();
      
      // 设置观察器
      this.setupObservers();
      
      // 应用样式
      this.applyStyles();
      
      console.log('🖼️ Virtual DOM preview engine initialized');
    } catch (error) {
      this.handleError(error as Error);
    }
  }
  
  /**
   * 处理错误
   */
  private handleError(error: Error): void {
    console.error('Virtual DOM Preview Engine Error:', error);
    if (this.onError) {
      this.onError(error);
    }
  }
  
  /**
   * 创建预览容器
   */
  private createPreviewContainer(): void {
    this.realDOM = document.createElement('div');
    this.realDOM.className = 'virtual-preview-content';
    this.realDOM.style.cssText = `
      width: 100%;
      height: 100%;
      overflow: auto;
      padding: 16px;
      background: ${this.settings.theme === 'dark' ? '#1e1e1e' : '#ffffff'};
      color: ${this.settings.theme === 'dark' ? '#ffffff' : '#000000'};
      font-size: ${this.settings.fontSize}px;
      line-height: ${this.settings.lineHeight};
      zoom: ${this.settings.zoom / 100};
    `;
    
    this.container.appendChild(this.realDOM);
  }
  
  /**
   * 设置观察器
   */
  private setupObservers(): void {
    // 交叉观察器 - 用于懒加载
    if (this.settings.lazyLoading) {
      this.observer = new IntersectionObserver(
        (entries) => {
          entries.forEach((entry) => {
            if (entry.isIntersecting) {
              this.loadLazyResource(entry.target as HTMLElement);
            }
          });
        },
        { threshold: 0.1 }
      );
    }
    
    // 尺寸观察器 - 用于响应式布局
    this.resizeObserver = new ResizeObserver(
      throttle((entries) => {
        this.handleResize(entries);
      }, 100)
    );
    
    if (this.realDOM) {
      this.resizeObserver.observe(this.realDOM);
    }
    
    // 变异观察器 - 用于监控DOM变化
    if (this.settings.performanceMonitor) {
      this.mutationObserver = new MutationObserver(
        throttle((mutations) => {
          this.handleMutations(mutations);
        }, 100)
      );
      
      if (this.realDOM) {
        this.mutationObserver.observe(this.realDOM, {
          childList: true,
          subtree: true,
          attributes: true,
          characterData: true
        });
      }
    }
  }
  
  /**
   * 应用样式
   */
  private applyStyles(): void {
    const styleId = 'virtual-preview-styles';
    let styleElement = document.getElementById(styleId) as HTMLStyleElement;
    
    if (!styleElement) {
      styleElement = document.createElement('style');
      styleElement.id = styleId;
      document.head.appendChild(styleElement);
    }
    
    styleElement.textContent = `
      .virtual-preview-content {
        font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      }
      
      .virtual-preview-content img {
        max-width: 100%;
        height: auto;
        border-radius: 4px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
      }
      
      .virtual-preview-content pre {
        background: ${this.settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
        padding: 12px;
        border-radius: 4px;
        overflow-x: auto;
      }
      
      .virtual-preview-content code {
        background: ${this.settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
        padding: 2px 4px;
        border-radius: 2px;
        font-family: 'SF Mono', Monaco, 'Cascadia Code', monospace;
      }
      
      .virtual-preview-content blockquote {
        border-left: 4px solid #1890ff;
        padding-left: 16px;
        margin: 16px 0;
        color: ${this.settings.theme === 'dark' ? '#cccccc' : '#666666'};
      }
      
      .line-number {
        display: inline-block;
        width: 40px;
        color: ${this.settings.theme === 'dark' ? '#666666' : '#999999'};
        font-size: 12px;
        text-align: right;
        margin-right: 8px;
        user-select: none;
      }
      
      .sync-highlight {
        background: rgba(24, 144, 255, 0.1);
        border-left: 3px solid #1890ff;
        padding-left: 8px;
        transition: all 0.3s ease;
      }
      
      .lazy-loading {
        background: ${this.settings.theme === 'dark' ? '#2d2d2d' : '#f5f5f5'};
        display: flex;
        align-items: center;
        justify-content: center;
        min-height: 100px;
        border-radius: 4px;
      }
    `;
  }
  
  /**
   * 更新内容
   */
  public updateContent(content: string): void {
    if (content === this.lastContent) {
      return;
    }
    
    this.lastContent = content;
    
    if (this.settings.incrementalUpdate && this.virtualDOM) {
      this.performIncrementalUpdate(content);
    } else {
      this.performFullUpdate(content);
    }
  }
  
  /**
   * 执行增量更新
   */
  private performIncrementalUpdate(content: string): void {
    const startTime = performance.now();
    
    try {
      // 解析新的虚拟DOM
      const newVirtualDOM = this.parseContent(content);
      
      // 计算差异
      const diffs = this.calculateDiff(this.virtualDOM!, newVirtualDOM);
      
      // 应用差异
      this.applyDiffs(diffs);
      
      // 更新虚拟DOM
      this.virtualDOM = newVirtualDOM;
      
      this.metrics.diffTime = performance.now() - startTime;
      this.throttledMetricsUpdate();
      
    } catch (error) {
      console.warn('Incremental update failed, falling back to full update:', error);
      this.performFullUpdate(content);
    }
  }
  
  /**
   * 执行完整更新
   */
  private performFullUpdate(content: string): void {
    const startTime = performance.now();
    
    try {
      // 解析虚拟DOM
      this.virtualDOM = this.parseContent(content);
      
      // 渲染到真实DOM
      this.renderToDOM(this.virtualDOM);
      
      this.metrics.renderTime = performance.now() - startTime;
      this.throttledMetricsUpdate();
      
    } catch (error) {
      this.handleError(error as Error);
    }
  }
  
  /**
   * 解析内容为虚拟DOM
   */
  private parseContent(content: string): VirtualNode {
    const lines = content.split('\n');
    const processedContent = this.preprocessContent(content);
    
    try {
      const doc = this.parser.parseFromString(
        `<div class="preview-root">${processedContent}</div>`,
        'text/html'
      );
      
      const rootElement = doc.querySelector('.preview-root');
      if (!rootElement) {
        throw new Error('Failed to parse content');
      }
      
      return this.createVirtualNode(rootElement, lines);
    } catch (error) {
      // 如果解析失败，创建一个包含错误信息的节点
      return {
        id: 'error-root',
        type: 'element',
        tag: 'div',
        attributes: { class: 'parse-error' },
        children: [{
          id: 'error-text',
          type: 'text',
          text: `解析错误: ${(error as Error).message}`
        }]
      };
    }
  }
  
  /**
   * 预处理内容
   */
  private preprocessContent(content: string): string {
    let processed = content;
    
    // 处理图片
    if (this.settings.enableImagePreview) {
      processed = processed.replace(
        /<img([^>]*)src=["']([^"']+)["']([^>]*)>/gi,
        (match, before, src, after) => {
          const optimizedSrc = this.optimizeImageSrc(src);
          const lazyAttr = this.settings.lazyLoading ? ' loading="lazy"' : '';
          return `<img${before}src="${optimizedSrc}"${after}${lazyAttr}>`;
        }
      );
    }
    
    // 添加行号
    if (this.settings.showLineNumbers) {
      const lines = processed.split('\n');
      processed = lines.map((line, index) => {
        if (line.trim()) {
          return `<div class="line" data-line="${index + 1}">
            <span class="line-number">${index + 1}</span>
            ${line}
          </div>`;
        }
        return line;
      }).join('\n');
    }
    
    // 添加同步标记
    processed = processed.replace(
      /<(h[1-6]|p|div|section|article|blockquote)([^>]*)>/gi,
      (match, tag, attrs) => {
        const id = `sync-${Math.random().toString(36).substr(2, 9)}`;
        return `<${tag}${attrs} data-sync-id="${id}">`;
      }
    );
    
    return processed;
  }
  
  /**
   * 优化图片源地址
   */
  private optimizeImageSrc(src: string): string {
    // 检查缓存
    if (this.resourceCache.has(src)) {
      const cached = this.resourceCache.get(src)!;
      cached.lastAccessed = Date.now();
      cached.hitCount++;
      return src; // 返回原始URL，浏览器会使用缓存
    }
    
    // 如果启用资源优化，可以在这里进行图片压缩、格式转换等
    if (this.settings.resourceOptimization) {
      // 这里可以添加图片优化逻辑
      // 例如：转换为WebP格式、调整尺寸等
    }
    
    return src;
  }
  
  /**
   * 创建虚拟节点
   */
  private createVirtualNode(element: Element, lines: string[], lineNumber?: number): VirtualNode {
    const id = `node-${Math.random().toString(36).substr(2, 9)}`;
    
    if (element.nodeType === Node.TEXT_NODE) {
      return {
        id,
        type: 'text',
        text: element.textContent || '',
        lineNumber
      };
    }
    
    const attributes: Record<string, string> = {};
    for (let i = 0; i < element.attributes.length; i++) {
      const attr = element.attributes[i];
      attributes[attr.name] = attr.value;
    }
    
    const children: VirtualNode[] = [];
    for (let i = 0; i < element.childNodes.length; i++) {
      const child = element.childNodes[i];
      if (child.nodeType === Node.ELEMENT_NODE || child.nodeType === Node.TEXT_NODE) {
        const childNode = this.createVirtualNode(child as Element, lines, lineNumber);
        childNode.parent = { id, type: 'element', tag: element.tagName.toLowerCase() };
        children.push(childNode);
      }
    }
    
    return {
      id,
      type: 'element',
      tag: element.tagName.toLowerCase(),
      attributes,
      children,
      lineNumber
    };
  }
  
  /**
   * 计算虚拟DOM差异
   */
  private calculateDiff(oldNode: VirtualNode, newNode: VirtualNode): VirtualDiff[] {
    const diffs: VirtualDiff[] = [];
    
    // 简化的差异算法
    if (oldNode.type !== newNode.type || oldNode.tag !== newNode.tag) {
      diffs.push({
        type: 'update',
        node: newNode,
        oldNode,
        newNode
      });
      return diffs;
    }
    
    // 检查文本内容
    if (oldNode.type === 'text' && oldNode.text !== newNode.text) {
      diffs.push({
        type: 'text',
        node: newNode,
        oldNode,
        newNode
      });
    }
    
    // 检查属性
    if (oldNode.type === 'element' && newNode.type === 'element') {
      const oldAttrs = oldNode.attributes || {};
      const newAttrs = newNode.attributes || {};
      
      if (JSON.stringify(oldAttrs) !== JSON.stringify(newAttrs)) {
        diffs.push({
          type: 'update',
          node: newNode,
          oldNode,
          newNode
        });
      }
    }
    
    // 递归检查子节点
    if (oldNode.children && newNode.children) {
      const maxLength = Math.max(oldNode.children.length, newNode.children.length);
      
      for (let i = 0; i < maxLength; i++) {
        const oldChild = oldNode.children[i];
        const newChild = newNode.children[i];
        
        if (!oldChild && newChild) {
          diffs.push({ type: 'add', node: newChild, index: i });
        } else if (oldChild && !newChild) {
          diffs.push({ type: 'remove', node: oldChild, index: i });
        } else if (oldChild && newChild) {
          diffs.push(...this.calculateDiff(oldChild, newChild));
        }
      }
    }
    
    return diffs;
  }
  
  /**
   * 应用差异
   */
  private applyDiffs(diffs: VirtualDiff[]): void {
    const startTime = performance.now();
    
    diffs.forEach((diff) => {
      try {
        switch (diff.type) {
          case 'add':
            this.addNode(diff.node, diff.index);
            break;
          case 'remove':
            this.removeNode(diff.node);
            break;
          case 'update':
            this.updateNode(diff.oldNode!, diff.newNode!);
            break;
          case 'text':
            this.updateTextNode(diff.oldNode!, diff.newNode!);
            break;
        }
      } catch (error) {
        console.warn('Failed to apply diff:', diff, error);
      }
    });
    
    this.metrics.updateTime = performance.now() - startTime;
  }
  
  /**
   * 添加节点
   */
  private addNode(node: VirtualNode, index?: number): void {
    const element = this.createDOMElement(node);
    if (element && this.realDOM) {
      if (index !== undefined && index < this.realDOM.children.length) {
        this.realDOM.insertBefore(element, this.realDOM.children[index]);
      } else {
        this.realDOM.appendChild(element);
      }
      this.nodeMap.set(node.id, element);
    }
  }
  
  /**
   * 移除节点
   */
  private removeNode(node: VirtualNode): void {
    const element = this.nodeMap.get(node.id);
    if (element && element.parentNode) {
      element.parentNode.removeChild(element);
      this.nodeMap.delete(node.id);
    }
  }
  
  /**
   * 更新节点
   */
  private updateNode(oldNode: VirtualNode, newNode: VirtualNode): void {
    const element = this.nodeMap.get(oldNode.id);
    if (!element) return;
    
    // 更新属性（只对HTMLElement有效）
    if (newNode.attributes && element instanceof HTMLElement) {
      Object.entries(newNode.attributes).forEach(([key, value]) => {
        element.setAttribute(key, value);
      });
    }
    
    // 更新映射
    this.nodeMap.delete(oldNode.id);
    this.nodeMap.set(newNode.id, element);
  }
  
  /**
   * 更新文本节点
   */
  private updateTextNode(oldNode: VirtualNode, newNode: VirtualNode): void {
    const element = this.nodeMap.get(oldNode.id);
    if (element && newNode.text !== undefined) {
      element.textContent = newNode.text;
    }
  }
  
  /**
   * 渲染虚拟DOM到真实DOM
   */
  private renderToDOM(virtualNode: VirtualNode): void {
    if (!this.realDOM) return;
    
    // 清空容器
    this.realDOM.innerHTML = '';
    this.nodeMap.clear();
    this.lineMap.clear();
    
    // 渲染虚拟DOM
    const element = this.createDOMElement(virtualNode);
    if (element) {
      this.realDOM.appendChild(element);
    }
  }
  
  /**
   * 创建DOM元素
   */
  private createDOMElement(virtualNode: VirtualNode): HTMLElement | Text | null {
    if (virtualNode.type === 'text') {
      const textNode = document.createTextNode(virtualNode.text || '');
      this.nodeMap.set(virtualNode.id, textNode);
      return textNode;
    }
    
    if (virtualNode.type === 'element' && virtualNode.tag) {
      const element = document.createElement(virtualNode.tag);
      
      // 设置属性
      if (virtualNode.attributes) {
        Object.entries(virtualNode.attributes).forEach(([key, value]) => {
          element.setAttribute(key, value);
        });
      }
      
      // 添加子节点
      if (virtualNode.children) {
        virtualNode.children.forEach((child) => {
          const childElement = this.createDOMElement(child);
          if (childElement) {
            element.appendChild(childElement);
          }
        });
      }
      
      // 设置懒加载
      if (this.settings.lazyLoading && virtualNode.tag === 'img') {
        this.setupLazyLoading(element);
      }
      
      // 建立映射
      this.nodeMap.set(virtualNode.id, element);
      
      if (virtualNode.lineNumber) {
        this.lineMap.set(virtualNode.lineNumber, element);
      }
      
      return element;
    }
    
    return null;
  }
  
  /**
   * 设置懒加载
   */
  private setupLazyLoading(element: HTMLElement): void {
    if (this.observer && element.tagName === 'IMG') {
      // 创建占位符
      const placeholder = document.createElement('div');
      placeholder.className = 'lazy-loading';
      placeholder.textContent = '加载中...';
      
      // 替换图片
      element.style.display = 'none';
      element.parentNode?.insertBefore(placeholder, element);
      
      // 观察占位符
      this.observer.observe(placeholder);
      
      // 存储原始图片元素
      (placeholder as any).__originalImage = element;
    }
  }
  
  /**
   * 加载懒加载资源
   */
  private loadLazyResource(placeholder: HTMLElement): void {
    const originalImage = (placeholder as any).__originalImage as HTMLImageElement;
    if (!originalImage) return;
    
    const src = originalImage.src;
    
    // 创建新的图片元素来预加载
    const img = new Image();
    img.onload = () => {
      // 替换占位符
      originalImage.style.display = '';
      placeholder.parentNode?.replaceChild(originalImage, placeholder);
      
      // 缓存资源
      this.cacheResource(src, 'image', img);
      
      // 停止观察
      if (this.observer) {
        this.observer.unobserve(placeholder);
      }
    };
    
    img.onerror = () => {
      placeholder.textContent = '加载失败';
      placeholder.className = 'lazy-error';
    };
    
    img.src = src;
  }
  
  /**
   * 缓存资源
   */
  private cacheResource(url: string, type: string, data: any): void {
    const cache: ResourceCache = {
      url,
      data,
      type,
      size: this.estimateResourceSize(data),
      lastAccessed: Date.now(),
      hitCount: 1
    };
    
    this.resourceCache.set(url, cache);
    this.metrics.resourcesCached++;
    
    if (this.onResourceLoad) {
      this.onResourceLoad(cache);
    }
    
    // 清理过期缓存
    this.cleanupCache();
  }
  
  /**
   * 估算资源大小
   */
  private estimateResourceSize(data: any): number {
    if (typeof data === 'string') {
      return data.length * 2; // UTF-16
    }
    if (data instanceof ArrayBuffer) {
      return data.byteLength;
    }
    if (data instanceof HTMLImageElement) {
      return data.naturalWidth * data.naturalHeight * 4; // RGBA
    }
    return 0;
  }
  
  /**
   * 清理缓存
   */
  private cleanupCache(): void {
    const maxCacheSize = 50 * 1024 * 1024; // 50MB
    const maxAge = 30 * 60 * 1000; // 30分钟
    const now = Date.now();
    
    let totalSize = 0;
    const entries = Array.from(this.resourceCache.entries());
    
    // 计算总大小
    entries.forEach(([, cache]) => {
      totalSize += cache.size;
    });
    
    // 如果超过限制，清理最少使用的资源
    if (totalSize > maxCacheSize) {
      entries
        .sort((a, b) => a[1].hitCount - b[1].hitCount)
        .slice(0, Math.floor(entries.length * 0.3))
        .forEach(([url]) => {
          this.resourceCache.delete(url);
        });
    }
    
    // 清理过期资源
    entries.forEach(([url, cache]) => {
      if (now - cache.lastAccessed > maxAge) {
        this.resourceCache.delete(url);
      }
    });
  }
  
  /**
   * 处理尺寸变化
   */
  private handleResize(entries: ResizeObserverEntry[]): void {
    // 重新计算布局
    if (this.realDOM) {
      this.realDOM.style.zoom = `${this.settings.zoom / 100}`;
    }
  }
  
  /**
   * 处理DOM变化
   */
  private handleMutations(mutations: MutationRecord[]): void {
    this.metrics.domNodes = this.realDOM?.querySelectorAll('*').length || 0;
    this.throttledMetricsUpdate();
  }
  
  /**
   * 更新性能指标
   */
  private updateMetrics(): void {
    this.metrics.virtualNodes = this.countVirtualNodes(this.virtualDOM);
    this.metrics.cacheHitRate = this.calculateCacheHitRate();
    this.metrics.memoryUsage = this.estimateMemoryUsage();
    
    if (this.onMetricsUpdate) {
      this.onMetricsUpdate(this.metrics);
    }
  }
  
  /**
   * 计算虚拟节点数量
   */
  private countVirtualNodes(node: VirtualNode | null): number {
    if (!node) return 0;
    
    let count = 1;
    if (node.children) {
      node.children.forEach(child => {
        count += this.countVirtualNodes(child);
      });
    }
    
    return count;
  }
  
  /**
   * 计算缓存命中率
   */
  private calculateCacheHitRate(): number {
    const total = this.metrics.cacheHits + this.metrics.cacheMisses;
    return total > 0 ? (this.metrics.cacheHits / total) * 100 : 100;
  }
  
  /**
   * 估算内存使用量
   */
  private estimateMemoryUsage(): number {
    let usage = 0;
    
    // 虚拟DOM内存
    usage += this.metrics.virtualNodes * 200; // 估算每个节点200字节
    
    // 缓存内存
    this.resourceCache.forEach(cache => {
      usage += cache.size;
    });
    
    return usage;
  }
  
  /**
   * 获取容器元素
   */
  public getContainer(): HTMLElement | null {
    return this.realDOM;
  }
  
  /**
   * 获取所有元素
   */
  public getAllElements(): HTMLElement[] {
    if (!this.realDOM) return [];
    return Array.from(this.realDOM.querySelectorAll('*'));
  }
  
  /**
   * 销毁引擎
   */
  public destroy(): void {
    // 清理观察器
    if (this.observer) {
      this.observer.disconnect();
    }
    
    if (this.resizeObserver) {
      this.resizeObserver.disconnect();
    }
    
    if (this.mutationObserver) {
      this.mutationObserver.disconnect();
    }
    
    // 清理缓存
    this.resourceCache.clear();
    this.nodeMap.clear();
    this.lineMap.clear();
    
    // 清理DOM
    if (this.realDOM) {
      this.realDOM.innerHTML = '';
    }
    
    console.log('🗑️ Virtual DOM Preview Engine destroyed');
  }
}