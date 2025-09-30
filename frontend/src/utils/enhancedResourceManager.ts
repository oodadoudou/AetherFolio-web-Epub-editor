/**
 * 增强资源管理器 - 处理EPUB文件中的图片、CSS等资源
 * 解决资源加载500错误和缓存问题
 */

export interface ResourceItem {
  url: string;
  type: 'image' | 'css' | 'font' | 'script';
  data?: string | Blob;
  timestamp: number;
  status: 'pending' | 'loaded' | 'error';
  error?: string;
}

export interface ResourceCache {
  [key: string]: ResourceItem;
}

export class EnhancedResourceManager {
  private cache: ResourceCache = {};
  private sessionId: string;
  private maxCacheSize = 100; // 最大缓存项数
  private cacheTimeout = 300000; // 5分钟缓存超时
  private loadingPromises: Map<string, Promise<ResourceItem>> = new Map();

  constructor(sessionId: string) {
    this.sessionId = sessionId;
    this.startCacheCleanup();
  }

  /**
   * 启动缓存清理定时器
   */
  private startCacheCleanup(): void {
    setInterval(() => {
      this.cleanupExpiredCache();
    }, 60000); // 每分钟清理一次
  }

  /**
   * 清理过期缓存
   */
  private cleanupExpiredCache(): void {
    const now = Date.now();
    const expiredKeys: string[] = [];

    Object.entries(this.cache).forEach(([key, item]) => {
      if (now - item.timestamp > this.cacheTimeout) {
        expiredKeys.push(key);
      }
    });

    expiredKeys.forEach(key => {
      // 释放Blob URL
      const item = this.cache[key];
      if (item.data && typeof item.data === 'string' && item.data.startsWith('blob:')) {
        URL.revokeObjectURL(item.data);
      }
      delete this.cache[key];
    });

    // 如果缓存过大，删除最旧的项
    const cacheKeys = Object.keys(this.cache);
    if (cacheKeys.length > this.maxCacheSize) {
      const sortedKeys = cacheKeys.sort((a, b) => 
        this.cache[a].timestamp - this.cache[b].timestamp
      );
      
      const keysToRemove = sortedKeys.slice(0, cacheKeys.length - this.maxCacheSize);
      keysToRemove.forEach(key => {
        const item = this.cache[key];
        if (item.data && typeof item.data === 'string' && item.data.startsWith('blob:')) {
          URL.revokeObjectURL(item.data);
        }
        delete this.cache[key];
      });
    }

    console.log(`🧹 Cache cleanup completed. Removed ${expiredKeys.length} expired items. Current cache size: ${Object.keys(this.cache).length}`);
  }

  /**
   * 检测资源类型
   */
  private detectResourceType(url: string): ResourceItem['type'] {
    const extension = url.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'jpg':
      case 'jpeg':
      case 'png':
      case 'gif':
      case 'webp':
      case 'svg':
        return 'image';
      case 'css':
        return 'css';
      case 'woff':
      case 'woff2':
      case 'ttf':
      case 'otf':
        return 'font';
      case 'js':
        return 'script';
      default:
        return 'image'; // 默认当作图片处理
    }
  }

  /**
   * 构建资源URL
   */
  private buildResourceUrl(originalUrl: string, type: ResourceItem['type']): string {
    // 如果已经是完整URL，直接返回
    if (originalUrl.startsWith('http') || originalUrl.startsWith('data:') || originalUrl.startsWith('blob:')) {
      return originalUrl;
    }

    // 处理相对路径
    let cleanUrl = originalUrl;
    
    // 移除开头的 ./ 或 /
    if (cleanUrl.startsWith('./')) {
      cleanUrl = cleanUrl.substring(2);
    } else if (cleanUrl.startsWith('/')) {
      cleanUrl = cleanUrl.substring(1);
    }

    // 根据资源类型选择不同的API端点
    if (type === 'image') {
      return `/api/v1/files/binary?session_id=${this.sessionId}&file_path=${encodeURIComponent(cleanUrl)}`;
    } else {
      return `/api/v1/files/content?session_id=${this.sessionId}&file_path=${encodeURIComponent(cleanUrl)}`;
    }
  }

  /**
   * 加载单个资源
   */
  private async loadSingleResource(url: string, type: ResourceItem['type']): Promise<ResourceItem> {
    const resourceUrl = this.buildResourceUrl(url, type);
    
    try {
      console.log(`🔄 Loading ${type} resource:`, url, '→', resourceUrl);
      
      const response = await fetch(resourceUrl, {
        method: 'GET',
        headers: {
          'Accept': type === 'image' ? 'image/*' : 'text/*'
        }
      });

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}: ${response.statusText}`);
      }

      let data: string | Blob;
      
      if (type === 'image') {
        const blob = await response.blob();
        data = URL.createObjectURL(blob);
      } else {
        data = await response.text();
      }

      const item: ResourceItem = {
        url,
        type,
        data,
        timestamp: Date.now(),
        status: 'loaded'
      };

      console.log(`✅ Successfully loaded ${type} resource:`, url);
      return item;
    } catch (error) {
      console.error(`❌ Failed to load ${type} resource:`, url, error);
      
      const item: ResourceItem = {
        url,
        type,
        timestamp: Date.now(),
        status: 'error',
        error: error instanceof Error ? error.message : 'Unknown error'
      };
      
      return item;
    }
  }

  /**
   * 获取资源（带缓存）
   */
  async getResource(url: string, type?: ResourceItem['type']): Promise<ResourceItem> {
    // 检查缓存
    const cached = this.cache[url];
    if (cached && Date.now() - cached.timestamp < this.cacheTimeout) {
      console.log(`📦 Using cached ${cached.type} resource:`, url);
      return cached;
    }

    // 检查是否正在加载
    const existingPromise = this.loadingPromises.get(url);
    if (existingPromise) {
      console.log(`⏳ Waiting for existing ${type || 'unknown'} resource load:`, url);
      return existingPromise;
    }

    // 开始加载
    const resourceType = type || this.detectResourceType(url);
    const loadPromise = this.loadSingleResource(url, resourceType);
    
    this.loadingPromises.set(url, loadPromise);
    
    try {
      const item = await loadPromise;
      this.cache[url] = item;
      return item;
    } finally {
      this.loadingPromises.delete(url);
    }
  }

  /**
   * 批量预加载资源
   */
  async preloadResources(urls: string[]): Promise<ResourceItem[]> {
    console.log(`🚀 Preloading ${urls.length} resources...`);
    
    const promises = urls.map(url => {
      const type = this.detectResourceType(url);
      return this.getResource(url, type).catch(error => {
        console.warn(`Failed to preload resource: ${url}`, error);
        return {
          url,
          type,
          timestamp: Date.now(),
          status: 'error' as const,
          error: error instanceof Error ? error.message : 'Preload failed'
        };
      });
    });

    const results = await Promise.all(promises);
    const successful = results.filter(item => item.status === 'loaded').length;
    
    console.log(`📊 Preload completed: ${successful}/${urls.length} resources loaded successfully`);
    return results;
  }

  /**
   * 从HTML内容中提取资源URL
   */
  extractResourceUrls(html: string): string[] {
    const urls: string[] = [];
    
    // 提取图片
    const imgRegex = /<img[^>]+src=["']([^"']+)["'][^>]*>/gi;
    let match;
    while ((match = imgRegex.exec(html)) !== null) {
      urls.push(match[1]);
    }
    
    // 提取CSS链接
    const linkRegex = /<link[^>]+href=["']([^"']+\.css)["'][^>]*>/gi;
    while ((match = linkRegex.exec(html)) !== null) {
      urls.push(match[1]);
    }
    
    // 提取内联样式中的背景图片
    const bgRegex = /background-image:\s*url\(["']?([^"')]+)["']?\)/gi;
    while ((match = bgRegex.exec(html)) !== null) {
      urls.push(match[1]);
    }
    
    return [...new Set(urls)]; // 去重
  }

  /**
   * 处理HTML内容，替换资源引用
   */
  async processHtmlContent(html: string): Promise<string> {
    if (!html) return html;
    
    let processedHtml = html;
    
    // 提取所有资源URL
    const resourceUrls = this.extractResourceUrls(html);
    
    if (resourceUrls.length === 0) {
      return processedHtml;
    }
    
    console.log(`🔍 Found ${resourceUrls.length} resources to process in HTML`);
    
    // 批量加载资源
    const resources = await this.preloadResources(resourceUrls);
    
    // 替换HTML中的资源引用
    for (const resource of resources) {
      if (resource.status === 'loaded' && resource.data) {
        const originalUrl = resource.url;
        const processedUrl = typeof resource.data === 'string' ? resource.data : URL.createObjectURL(resource.data);
        
        // 替换所有出现的原始URL
        const escapedUrl = originalUrl.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const urlRegex = new RegExp(escapedUrl, 'g');
        processedHtml = processedHtml.replace(urlRegex, processedUrl);
      }
    }
    
    return processedHtml;
  }

  /**
   * 获取缓存统计信息
   */
  getCacheStats(): {
    totalItems: number;
    byType: Record<ResourceItem['type'], number>;
    totalSize: number;
    oldestTimestamp: number;
    newestTimestamp: number;
  } {
    const items = Object.values(this.cache);
    const stats = {
      totalItems: items.length,
      byType: {
        image: 0,
        css: 0,
        font: 0,
        script: 0
      } as Record<ResourceItem['type'], number>,
      totalSize: 0,
      oldestTimestamp: Date.now(),
      newestTimestamp: 0
    };
    
    items.forEach(item => {
      stats.byType[item.type]++;
      if (item.timestamp < stats.oldestTimestamp) {
        stats.oldestTimestamp = item.timestamp;
      }
      if (item.timestamp > stats.newestTimestamp) {
        stats.newestTimestamp = item.timestamp;
      }
    });
    
    return stats;
  }

  /**
   * 清空缓存
   */
  clearCache(): void {
    // 释放所有Blob URL
    Object.values(this.cache).forEach(item => {
      if (item.data && typeof item.data === 'string' && item.data.startsWith('blob:')) {
        URL.revokeObjectURL(item.data);
      }
    });
    
    this.cache = {};
    this.loadingPromises.clear();
    
    console.log('🗑️ Resource cache cleared');
  }

  /**
   * 销毁管理器
   */
  destroy(): void {
    this.clearCache();
    console.log('💥 EnhancedResourceManager destroyed');
  }
}

// 创建全局实例管理器
const resourceManagers = new Map<string, EnhancedResourceManager>();

export function getResourceManager(sessionId: string): EnhancedResourceManager {
  if (!resourceManagers.has(sessionId)) {
    resourceManagers.set(sessionId, new EnhancedResourceManager(sessionId));
  }
  return resourceManagers.get(sessionId)!;
}

export function destroyResourceManager(sessionId: string): void {
  const manager = resourceManagers.get(sessionId);
  if (manager) {
    manager.destroy();
    resourceManagers.delete(sessionId);
  }
}

export default EnhancedResourceManager;