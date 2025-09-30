import axios, { AxiosResponse } from 'axios';
import { debounce } from './debounce';

/**
 * 资源类型枚举
 */
export enum ResourceType {
  IMAGE = 'image',
  CSS = 'css',
  JAVASCRIPT = 'javascript',
  FONT = 'font',
  OTHER = 'other'
}

/**
 * 资源缓存项
 */
interface CacheItem {
  data: string | ArrayBuffer;
  type: ResourceType;
  mimeType: string;
  size: number;
  lastAccessed: number;
  accessCount: number;
  expiresAt: number;
}

/**
 * 资源加载选项
 */
interface LoadOptions {
  useCache?: boolean;
  timeout?: number;
  retryCount?: number;
  retryDelay?: number;
  fallbackUrl?: string;
  enableCompression?: boolean;
}

/**
 * 资源统计信息
 */
export interface ResourceStats {
  loaded: number;
  total: number;
  cached: number;
  failed: number;
  totalSize: number;
  cacheHitRate: number;
}

/**
 * 加载状态
 */
interface LoadingState {
  url: string;
  type: ResourceType;
  startTime: number;
  retryCount: number;
}

const DEFAULT_LOAD_OPTIONS: LoadOptions = {
  useCache: true,
  timeout: 10000,
  retryCount: 3,
  retryDelay: 1000,
  enableCompression: true
};

/**
 * 优化的资源管理器
 * 实现智能缓存、错误重试、资源预加载和性能优化
 */
export class ResourceManager {
  private cache: Map<string, CacheItem> = new Map();
  private loadingStates: Map<string, LoadingState> = new Map();
  private stats: ResourceStats = {
    loaded: 0,
    total: 0,
    cached: 0,
    failed: 0,
    totalSize: 0,
    cacheHitRate: 0
  };
  private maxCacheSize: number = 50 * 1024 * 1024; // 50MB
  private maxCacheAge: number = 24 * 60 * 60 * 1000; // 24小时
  private cleanupInterval: NodeJS.Timeout | null = null;
  private preloadQueue: Set<string> = new Set();
  private isPreloading: boolean = false;

  constructor() {
    // 启动缓存清理定时器
    this.startCacheCleanup();
    
    // 监听页面卸载事件，清理资源
    if (typeof window !== 'undefined') {
      window.addEventListener('beforeunload', () => {
        this.cleanup();
      });
    }
  }

  /**
   * 加载资源
   */
  async loadResource(
    url: string, 
    type: ResourceType = ResourceType.OTHER,
    options: LoadOptions = {}
  ): Promise<string | ArrayBuffer> {
    const opts = { ...DEFAULT_LOAD_OPTIONS, ...options };
    const cacheKey = this.getCacheKey(url, type);
    
    // 检查缓存
    if (opts.useCache) {
      const cached = this.getFromCache(cacheKey);
      if (cached) {
        this.updateStats('cached');
        return cached.data;
      }
    }
    
    // 检查是否正在加载
    if (this.loadingStates.has(url)) {
      return this.waitForLoading(url);
    }
    
    // 开始加载
    return this.performLoad(url, type, opts);
  }

  /**
   * 执行实际的资源加载
   */
  private async performLoad(
    url: string,
    type: ResourceType,
    options: LoadOptions
  ): Promise<string | ArrayBuffer> {
    const loadingState: LoadingState = {
      url,
      type,
      startTime: Date.now(),
      retryCount: 0
    };
    
    this.loadingStates.set(url, loadingState);
    this.updateStats('total');
    
    try {
      const data = await this.loadWithRetry(url, type, options, loadingState);
      
      // 缓存结果
      if (options.useCache) {
        this.addToCache(url, type, data);
      }
      
      this.updateStats('loaded');
      return data;
      
    } catch (error) {
      this.updateStats('failed');
      
      // 尝试使用备用URL
      if (options.fallbackUrl) {
        try {
          const fallbackData = await this.loadWithRetry(
            options.fallbackUrl,
            type,
            { ...options, fallbackUrl: undefined },
            loadingState
          );
          
          if (options.useCache) {
            this.addToCache(url, type, fallbackData);
          }
          
          this.updateStats('loaded');
          return fallbackData;
          
        } catch (fallbackError) {
          console.error(`Failed to load fallback resource: ${options.fallbackUrl}`, fallbackError);
        }
      }
      
      throw error;
      
    } finally {
      this.loadingStates.delete(url);
    }
  }

  /**
   * 带重试的加载
   */
  private async loadWithRetry(
    url: string,
    type: ResourceType,
    options: LoadOptions,
    loadingState: LoadingState
  ): Promise<string | ArrayBuffer> {
    const maxRetries = options.retryCount || 3;
    
    for (let attempt = 0; attempt <= maxRetries; attempt++) {
      try {
        loadingState.retryCount = attempt;
        
        if (attempt > 0) {
          // 等待重试延迟
          await this.delay(options.retryDelay || 1000);
        }
        
        return await this.fetchResource(url, type, options);
        
      } catch (error) {
        console.warn(`Attempt ${attempt + 1} failed for ${url}:`, error);
        
        if (attempt === maxRetries) {
          throw new Error(`Failed to load resource after ${maxRetries + 1} attempts: ${url}`);
        }
      }
    }
    
    throw new Error(`Unexpected error loading resource: ${url}`);
  }

  /**
   * 获取资源
   */
  private async fetchResource(
    url: string,
    type: ResourceType,
    options: LoadOptions
  ): Promise<string | ArrayBuffer> {
    // 处理相对路径
    const resolvedUrl = this.resolveUrl(url);
    
    try {
      let response: AxiosResponse;
      
      if (type === ResourceType.IMAGE) {
        // 图片资源使用二进制端点
        response = await axios.get(`/api/v1/files/binary`, {
          params: { path: resolvedUrl },
          responseType: 'arraybuffer',
          timeout: options.timeout,
          headers: {
            'Accept': 'image/*'
          }
        });
        
        return response.data;
        
      } else {
        // 其他资源使用文本端点
        response = await axios.get(`/api/v1/files/content`, {
          params: { path: resolvedUrl },
          timeout: options.timeout,
          headers: {
            'Accept': this.getAcceptHeader(type)
          }
        });
        
        return response.data;
      }
      
    } catch (error) {
      if (axios.isAxiosError(error)) {
        if (error.response?.status === 404) {
          throw new Error(`Resource not found: ${url}`);
        } else if (error.response?.status === 500) {
          throw new Error(`Server error loading resource: ${url}`);
        } else if (error.code === 'ECONNABORTED') {
          throw new Error(`Timeout loading resource: ${url}`);
        }
      }
      
      throw new Error(`Failed to fetch resource: ${url} - ${error}`);
    }
  }

  /**
   * 解析URL
   */
  private resolveUrl(url: string): string {
    // 如果是绝对URL，直接返回
    if (url.startsWith('http://') || url.startsWith('https://') || url.startsWith('/')) {
      return url;
    }
    
    // 处理相对路径
    return url;
  }

  /**
   * 获取Accept头
   */
  private getAcceptHeader(type: ResourceType): string {
    switch (type) {
      case ResourceType.CSS:
        return 'text/css';
      case ResourceType.JAVASCRIPT:
        return 'application/javascript';
      case ResourceType.IMAGE:
        return 'image/*';
      case ResourceType.FONT:
        return 'font/*';
      default:
        return '*/*';
    }
  }

  /**
   * 等待正在加载的资源
   */
  private async waitForLoading(url: string): Promise<string | ArrayBuffer> {
    return new Promise((resolve, reject) => {
      const checkInterval = setInterval(() => {
        if (!this.loadingStates.has(url)) {
          clearInterval(checkInterval);
          
          // 检查缓存中是否有结果
          const cached = this.getFromCache(this.getCacheKey(url, ResourceType.OTHER));
          if (cached) {
            resolve(cached.data);
          } else {
            reject(new Error(`Resource loading failed: ${url}`));
          }
        }
      }, 100);
      
      // 超时处理
      setTimeout(() => {
        clearInterval(checkInterval);
        reject(new Error(`Timeout waiting for resource: ${url}`));
      }, 30000);
    });
  }

  /**
   * 处理CSS引用
   */
  async processCssReferences(
    html: string,
    filePath: string,
    baseUrl: string
  ): Promise<string> {
    const cssLinkRegex = /<link[^>]+rel=["']stylesheet["'][^>]*href=["']([^"']+)["'][^>]*>/gi;
    const cssImportRegex = /@import\s+["']([^"']+)["'];?/gi;
    
    let processedHtml = html;
    const cssPromises: Promise<void>[] = [];
    
    // 处理<link>标签
    let match;
    while ((match = cssLinkRegex.exec(html)) !== null) {
      const cssUrl = match[1];
      const fullMatch = match[0];
      
      cssPromises.push(
        this.loadResource(cssUrl, ResourceType.CSS)
          .then((cssContent) => {
            const inlineStyle = `<style type="text/css">${cssContent}</style>`;
            processedHtml = processedHtml.replace(fullMatch, inlineStyle);
          })
          .catch((error) => {
            console.warn(`Failed to load CSS: ${cssUrl}`, error);
          })
      );
    }
    
    // 处理@import语句
    cssImportRegex.lastIndex = 0;
    while ((match = cssImportRegex.exec(html)) !== null) {
      const cssUrl = match[1];
      const fullMatch = match[0];
      
      cssPromises.push(
        this.loadResource(cssUrl, ResourceType.CSS)
          .then((cssContent) => {
            processedHtml = processedHtml.replace(fullMatch, cssContent as string);
          })
          .catch((error) => {
            console.warn(`Failed to load imported CSS: ${cssUrl}`, error);
          })
      );
    }
    
    await Promise.all(cssPromises);
    return processedHtml;
  }

  /**
   * 处理图片引用
   */
  async processImageReferences(
    html: string,
    filePath: string,
    baseUrl: string,
    enableImagePreview: boolean = true
  ): Promise<string> {
    if (!enableImagePreview) {
      return html;
    }
    
    const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
    let processedHtml = html;
    const imagePromises: Promise<void>[] = [];
    
    let match;
    while ((match = imgRegex.exec(html)) !== null) {
      const imgUrl = match[1];
      const fullMatch = match[0];
      
      // 跳过已经是data URL的图片
      if (imgUrl.startsWith('data:')) {
        continue;
      }
      
      imagePromises.push(
        this.loadResource(imgUrl, ResourceType.IMAGE)
          .then((imageData) => {
            // 将ArrayBuffer转换为base64
            const base64 = this.arrayBufferToBase64(imageData as ArrayBuffer);
            const mimeType = this.getMimeTypeFromUrl(imgUrl);
            const dataUrl = `data:${mimeType};base64,${base64}`;
            
            const newImgTag = fullMatch.replace(
              /src=["'][^"']+["']/,
              `src="${dataUrl}"`
            );
            
            processedHtml = processedHtml.replace(fullMatch, newImgTag);
          })
          .catch((error) => {
            console.warn(`Failed to load image: ${imgUrl}`, error);
            
            // 添加错误占位符
            const errorPlaceholder = fullMatch.replace(
              /src=["'][^"']+["']/,
              `src="data:image/svg+xml;base64,${btoa('<svg xmlns="http://www.w3.org/2000/svg" width="100" height="100"><rect width="100" height="100" fill="#f0f0f0"/><text x="50" y="50" text-anchor="middle" dy=".3em" fill="#999">加载失败</text></svg>')}"`
            );
            
            processedHtml = processedHtml.replace(fullMatch, errorPlaceholder);
          })
      );
    }
    
    await Promise.all(imagePromises);
    return processedHtml;
  }

  /**
   * 预加载资源
   */
  async preloadResources(urls: string[]): Promise<void> {
    if (this.isPreloading) {
      return;
    }
    
    this.isPreloading = true;
    
    try {
      // 添加到预加载队列
      urls.forEach(url => this.preloadQueue.add(url));
      
      // 并发预加载（限制并发数）
      const concurrency = 3;
      const chunks = this.chunkArray(Array.from(this.preloadQueue), concurrency);
      
      for (const chunk of chunks) {
        await Promise.all(
          chunk.map(async (url) => {
            try {
              const type = this.getResourceTypeFromUrl(url);
              await this.loadResource(url, type);
              this.preloadQueue.delete(url);
            } catch (error) {
              console.warn(`Failed to preload resource: ${url}`, error);
            }
          })
        );
      }
      
    } finally {
      this.isPreloading = false;
    }
  }

  /**
   * 从URL推断资源类型
   */
  private getResourceTypeFromUrl(url: string): ResourceType {
    const extension = url.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'css':
        return ResourceType.CSS;
      case 'js':
      case 'javascript':
        return ResourceType.JAVASCRIPT;
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'svg':
      case 'webp':
        return ResourceType.IMAGE;
      case 'woff':
      case 'woff2':
      case 'ttf':
      case 'otf':
        return ResourceType.FONT;
      default:
        return ResourceType.OTHER;
    }
  }

  /**
   * 从URL获取MIME类型
   */
  private getMimeTypeFromUrl(url: string): string {
    const extension = url.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'jpg':
      case 'jpeg':
        return 'image/jpeg';
      case 'png':
        return 'image/png';
      case 'gif':
        return 'image/gif';
      case 'svg':
        return 'image/svg+xml';
      case 'webp':
        return 'image/webp';
      default:
        return 'image/jpeg';
    }
  }

  /**
   * ArrayBuffer转Base64
   */
  private arrayBufferToBase64(buffer: ArrayBuffer): string {
    const bytes = new Uint8Array(buffer);
    let binary = '';
    
    for (let i = 0; i < bytes.byteLength; i++) {
      binary += String.fromCharCode(bytes[i]);
    }
    
    return btoa(binary);
  }

  /**
   * 数组分块
   */
  private chunkArray<T>(array: T[], size: number): T[][] {
    const chunks: T[][] = [];
    for (let i = 0; i < array.length; i += size) {
      chunks.push(array.slice(i, i + size));
    }
    return chunks;
  }

  /**
   * 获取缓存键
   */
  private getCacheKey(url: string, type: ResourceType): string {
    return `${type}:${url}`;
  }

  /**
   * 从缓存获取
   */
  private getFromCache(key: string): CacheItem | null {
    const item = this.cache.get(key);
    
    if (!item) {
      return null;
    }
    
    // 检查是否过期
    if (Date.now() > item.expiresAt) {
      this.cache.delete(key);
      return null;
    }
    
    // 更新访问信息
    item.lastAccessed = Date.now();
    item.accessCount++;
    
    return item;
  }

  /**
   * 添加到缓存
   */
  private addToCache(url: string, type: ResourceType, data: string | ArrayBuffer): void {
    const key = this.getCacheKey(url, type);
    const size = typeof data === 'string' ? data.length : data.byteLength;
    
    // 检查缓存大小限制
    if (size > this.maxCacheSize / 10) {
      // 单个资源太大，不缓存
      return;
    }
    
    // 清理空间
    this.ensureCacheSpace(size);
    
    const item: CacheItem = {
      data,
      type,
      mimeType: this.getMimeTypeFromUrl(url),
      size,
      lastAccessed: Date.now(),
      accessCount: 1,
      expiresAt: Date.now() + this.maxCacheAge
    };
    
    this.cache.set(key, item);
    this.stats.totalSize += size;
  }

  /**
   * 确保缓存空间
   */
  private ensureCacheSpace(requiredSize: number): void {
    while (this.stats.totalSize + requiredSize > this.maxCacheSize && this.cache.size > 0) {
      // 找到最少使用的项目
      let lruKey: string | null = null;
      let lruScore = Infinity;
      
      for (const [key, item] of this.cache.entries()) {
        const score = item.accessCount / (Date.now() - item.lastAccessed + 1);
        if (score < lruScore) {
          lruScore = score;
          lruKey = key;
        }
      }
      
      if (lruKey) {
        const item = this.cache.get(lruKey)!;
        this.cache.delete(lruKey);
        this.stats.totalSize -= item.size;
      } else {
        break;
      }
    }
  }

  /**
   * 更新统计信息
   */
  private updateStats(type: keyof ResourceStats): void {
    if (type === 'cached') {
      this.stats.cached++;
    } else {
      this.stats[type]++;
    }
    
    // 计算缓存命中率
    const totalRequests = this.stats.loaded + this.stats.cached;
    this.stats.cacheHitRate = totalRequests > 0 ? this.stats.cached / totalRequests : 0;
  }

  /**
   * 获取统计信息
   */
  getStats(): ResourceStats {
    return { ...this.stats };
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.cache.clear();
    this.stats.totalSize = 0;
    this.stats.cached = 0;
    this.stats.cacheHitRate = 0;
  }

  /**
   * 启动缓存清理
   */
  private startCacheCleanup(): void {
    this.cleanupInterval = setInterval(() => {
      const now = Date.now();
      
      for (const [key, item] of this.cache.entries()) {
        if (now > item.expiresAt) {
          this.cache.delete(key);
          this.stats.totalSize -= item.size;
        }
      }
    }, 5 * 60 * 1000); // 每5分钟清理一次
  }

  /**
   * 延迟函数
   */
  private delay(ms: number): Promise<void> {
    return new Promise(resolve => setTimeout(resolve, ms));
  }

  /**
   * 处理HTML内容中的资源引用
   */
  async processHtmlContent(htmlContent: string): Promise<string> {
    let processedContent = htmlContent;
    
    // 处理图片资源
    const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
    const imgMatches = Array.from(htmlContent.matchAll(imgRegex));
    
    for (const match of imgMatches) {
      const [fullMatch, src] = match;
      try {
        const imageData = await this.loadResource(src, ResourceType.IMAGE);
        if (typeof imageData === 'string') {
          // 如果是base64数据，直接替换
          const newImg = fullMatch.replace(src, imageData);
          processedContent = processedContent.replace(fullMatch, newImg);
        }
      } catch (error) {
        console.warn(`Failed to process image: ${src}`, error);
      }
    }
    
    // 处理CSS资源
    const cssRegex = /<link[^>]+href=["']([^"']+\.css)["'][^>]*>/gi;
    const cssMatches = Array.from(htmlContent.matchAll(cssRegex));
    
    for (const match of cssMatches) {
      const [fullMatch, href] = match;
      try {
        const cssData = await this.loadResource(href, ResourceType.CSS);
        if (typeof cssData === 'string') {
          // 将外部CSS转换为内联样式
          const styleTag = `<style>${cssData}</style>`;
          processedContent = processedContent.replace(fullMatch, styleTag);
        }
      } catch (error) {
        console.warn(`Failed to process CSS: ${href}`, error);
      }
    }
    
    return processedContent;
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    if (this.cleanupInterval) {
      clearInterval(this.cleanupInterval);
      this.cleanupInterval = null;
    }
    
    this.clearCache();
    this.loadingStates.clear();
    this.preloadQueue.clear();
  }
}

export default ResourceManager;