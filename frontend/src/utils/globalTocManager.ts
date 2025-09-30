/**
 * 全局TOC管理器 - 处理目录解析、导航和同步
 * 支持多种文件格式的TOC提取和智能导航
 */

export interface TocItem {
  id: string;
  title: string;
  level: number;
  line: number;
  offset: number;
  children: TocItem[];
  parent?: TocItem;
  href?: string;
  anchor?: string;
}

export interface TocStructure {
  items: TocItem[];
  flatItems: TocItem[];
  maxLevel: number;
  totalItems: number;
}

export interface TocParseOptions {
  maxLevel: number;
  includeNumbering: boolean;
  extractAnchors: boolean;
  parseMarkdown: boolean;
  parseHtml: boolean;
  parseXhtml: boolean;
}

class GlobalTocManager {
  private tocCache = new Map<string, TocStructure>();
  private currentToc: TocStructure | null = null;
  private currentFile: string | null = null;
  private listeners = new Set<(toc: TocStructure | null) => void>();
  
  private defaultOptions: TocParseOptions = {
    maxLevel: 6,
    includeNumbering: true,
    extractAnchors: true,
    parseMarkdown: true,
    parseHtml: true,
    parseXhtml: true
  };

  /**
   * 解析文件内容生成TOC
   */
  parseContent(content: string, fileName: string, options?: Partial<TocParseOptions>): TocStructure {
    const parseOptions = { ...this.defaultOptions, ...options };
    const cacheKey = this.generateCacheKey(content, fileName, parseOptions);
    
    // 检查缓存
    if (this.tocCache.has(cacheKey)) {
      const cached = this.tocCache.get(cacheKey)!;
      console.log(`📦 Using cached TOC for ${fileName}`);
      return cached;
    }
    
    console.log(`🔍 Parsing TOC for ${fileName}`);
    
    let tocStructure: TocStructure;
    
    // 根据文件类型选择解析方法
    const extension = fileName.split('.').pop()?.toLowerCase();
    
    switch (extension) {
      case 'md':
      case 'markdown':
        tocStructure = this.parseMarkdownToc(content, parseOptions);
        break;
      case 'html':
      case 'htm':
        tocStructure = this.parseHtmlToc(content, parseOptions);
        break;
      case 'xhtml':
      case 'xml':
        tocStructure = this.parseXhtmlToc(content, parseOptions);
        break;
      case 'ncx':
        tocStructure = this.parseNcxToc(content, parseOptions);
        break;
      case 'opf':
        tocStructure = this.parseOpfToc(content, parseOptions);
        break;
      default:
        // 尝试通用解析
        tocStructure = this.parseGenericToc(content, parseOptions);
    }
    
    // 缓存结果
    this.tocCache.set(cacheKey, tocStructure);
    
    console.log(`✅ TOC parsed: ${tocStructure.totalItems} items, max level ${tocStructure.maxLevel}`);
    return tocStructure;
  }

  /**
   * 解析Markdown TOC
   */
  private parseMarkdownToc(content: string, options: TocParseOptions): TocStructure {
    const items: TocItem[] = [];
    const lines = content.split('\n');
    const stack: TocItem[] = [];
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      // 匹配标题
      const headingMatch = trimmedLine.match(/^(#{1,6})\s+(.+)$/);
      if (headingMatch) {
        const level = headingMatch[1].length;
        const title = headingMatch[2].trim();
        
        if (level <= options.maxLevel) {
          const item: TocItem = {
            id: this.generateId(title, index),
            title,
            level,
            line: index + 1,
            offset: content.split('\n').slice(0, index).join('\n').length,
            children: [],
            anchor: options.extractAnchors ? this.generateAnchor(title) : undefined
          };
          
          // 建立层级关系
          while (stack.length > 0 && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          
          if (stack.length > 0) {
            const parent = stack[stack.length - 1];
            parent.children.push(item);
            item.parent = parent;
          } else {
            items.push(item);
          }
          
          stack.push(item);
        }
      }
    });
    
    return this.buildTocStructure(items);
  }

  /**
   * 解析HTML TOC
   */
  private parseHtmlToc(content: string, options: TocParseOptions): TocStructure {
    const items: TocItem[] = [];
    const lines = content.split('\n');
    const stack: TocItem[] = [];
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      // 匹配HTML标题标签
      const headingMatch = trimmedLine.match(/<h([1-6])[^>]*>([^<]+)<\/h[1-6]>/i);
      if (headingMatch) {
        const level = parseInt(headingMatch[1]);
        const title = headingMatch[2].trim();
        
        if (level <= options.maxLevel) {
          // 提取id或anchor
          const idMatch = trimmedLine.match(/id=["']([^"']+)["']/i);
          const anchor = idMatch ? idMatch[1] : (options.extractAnchors ? this.generateAnchor(title) : undefined);
          
          const item: TocItem = {
            id: this.generateId(title, index),
            title,
            level,
            line: index + 1,
            offset: content.split('\n').slice(0, index).join('\n').length,
            children: [],
            anchor
          };
          
          // 建立层级关系
          while (stack.length > 0 && stack[stack.length - 1].level >= level) {
            stack.pop();
          }
          
          if (stack.length > 0) {
            const parent = stack[stack.length - 1];
            parent.children.push(item);
            item.parent = parent;
          } else {
            items.push(item);
          }
          
          stack.push(item);
        }
      }
    });
    
    return this.buildTocStructure(items);
  }

  /**
   * 解析XHTML TOC
   */
  private parseXhtmlToc(content: string, options: TocParseOptions): TocStructure {
    // XHTML解析逻辑与HTML类似，但更严格
    return this.parseHtmlToc(content, options);
  }

  /**
   * 解析NCX TOC
   */
  private parseNcxToc(content: string, options: TocParseOptions): TocStructure {
    const items: TocItem[] = [];
    
    try {
      // 简单的XML解析（实际项目中应使用专业的XML解析器）
      const navPointRegex = /<navPoint[^>]*id=["']([^"']+)["'][^>]*>([\s\S]*?)<\/navPoint>/gi;
      let match;
      let index = 0;
      
      while ((match = navPointRegex.exec(content)) !== null) {
        const id = match[1];
        const navPointContent = match[2];
        
        // 提取标题
        const labelMatch = navPointContent.match(/<navLabel>\s*<text>([^<]+)<\/text>\s*<\/navLabel>/i);
        const title = labelMatch ? labelMatch[1].trim() : `Chapter ${index + 1}`;
        
        // 提取链接
        const contentMatch = navPointContent.match(/<content\s+src=["']([^"']+)["'][^>]*\/?>/i);
        const href = contentMatch ? contentMatch[1] : undefined;
        
        const item: TocItem = {
          id,
          title,
          level: 1, // NCX中的层级需要更复杂的解析
          line: index + 1,
          offset: 0,
          children: [],
          href,
          anchor: href?.split('#')[1]
        };
        
        items.push(item);
        index++;
      }
    } catch (error) {
      console.warn('Failed to parse NCX TOC:', error);
    }
    
    return this.buildTocStructure(items);
  }

  /**
   * 解析OPF TOC
   */
  private parseOpfToc(content: string, options: TocParseOptions): TocStructure {
    const items: TocItem[] = [];
    
    try {
      // 解析spine中的项目
      const itemrefRegex = /<itemref\s+idref=["']([^"']+)["'][^>]*\/?>/gi;
      let match;
      let index = 0;
      
      while ((match = itemrefRegex.exec(content)) !== null) {
        const idref = match[1];
        
        // 查找对应的manifest项
        const manifestRegex = new RegExp(`<item\\s+id=["']${idref}["'][^>]*href=["']([^"']+)["'][^>]*\\/?>`,'i');
        const manifestMatch = content.match(manifestRegex);
        
        if (manifestMatch) {
          const href = manifestMatch[1];
          const title = href.split('/').pop()?.replace(/\.[^.]+$/, '') || `Item ${index + 1}`;
          
          const item: TocItem = {
            id: idref,
            title,
            level: 1,
            line: index + 1,
            offset: 0,
            children: [],
            href
          };
          
          items.push(item);
          index++;
        }
      }
    } catch (error) {
      console.warn('Failed to parse OPF TOC:', error);
    }
    
    return this.buildTocStructure(items);
  }

  /**
   * 通用TOC解析
   */
  private parseGenericToc(content: string, options: TocParseOptions): TocStructure {
    const items: TocItem[] = [];
    const lines = content.split('\n');
    
    lines.forEach((line, index) => {
      const trimmedLine = line.trim();
      
      // 尝试匹配各种可能的标题格式
      const patterns = [
        /^(#{1,6})\s+(.+)$/, // Markdown标题
        /^(\d+\.)+\s+(.+)$/, // 数字编号
        /^([A-Z]+\.)+\s+(.+)$/, // 字母编号
        /^\*\s+(.+)$/, // 列表项
        /^-\s+(.+)$/, // 列表项
        /^\d+\)\s+(.+)$/ // 数字加括号
      ];
      
      for (const pattern of patterns) {
        const match = trimmedLine.match(pattern);
        if (match) {
          let level = 1;
          let title = '';
          
          if (pattern === patterns[0]) { // Markdown标题
            level = match[1].length;
            title = match[2];
          } else if (pattern === patterns[1] || pattern === patterns[2]) { // 编号
            level = (match[1].match(/\./g) || []).length;
            title = match[2];
          } else { // 其他格式
            level = 1;
            title = match[1];
          }
          
          if (level <= options.maxLevel && title.length > 0) {
            const item: TocItem = {
              id: this.generateId(title, index),
              title,
              level,
              line: index + 1,
              offset: content.split('\n').slice(0, index).join('\n').length,
              children: [],
              anchor: options.extractAnchors ? this.generateAnchor(title) : undefined
            };
            
            items.push(item);
          }
          break;
        }
      }
    });
    
    return this.buildTocStructure(items);
  }

  /**
   * 构建TOC结构
   */
  private buildTocStructure(items: TocItem[]): TocStructure {
    const flatItems = this.flattenTocItems(items);
    const maxLevel = Math.max(...flatItems.map(item => item.level), 0);
    
    return {
      items,
      flatItems,
      maxLevel,
      totalItems: flatItems.length
    };
  }

  /**
   * 扁平化TOC项目
   */
  private flattenTocItems(items: TocItem[]): TocItem[] {
    const result: TocItem[] = [];
    
    const flatten = (items: TocItem[]) => {
      items.forEach(item => {
        result.push(item);
        if (item.children.length > 0) {
          flatten(item.children);
        }
      });
    };
    
    flatten(items);
    return result;
  }

  /**
   * 生成缓存键
   */
  private generateCacheKey(content: string, fileName: string, options: TocParseOptions): string {
    const contentHash = this.simpleHash(content);
    const optionsHash = this.simpleHash(JSON.stringify(options));
    return `${fileName}_${contentHash}_${optionsHash}`;
  }

  /**
   * 简单哈希函数
   */
  private simpleHash(str: string): string {
    let hash = 0;
    for (let i = 0; i < str.length; i++) {
      const char = str.charCodeAt(i);
      hash = ((hash << 5) - hash) + char;
      hash = hash & hash; // Convert to 32bit integer
    }
    return hash.toString(36);
  }

  /**
   * 生成ID
   */
  private generateId(title: string, index: number): string {
    const cleanTitle = title.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-')
      .substring(0, 50);
    return `toc-${cleanTitle}-${index}`;
  }

  /**
   * 生成锚点
   */
  private generateAnchor(title: string): string {
    return title.toLowerCase()
      .replace(/[^a-z0-9\s-]/g, '')
      .replace(/\s+/g, '-');
  }

  /**
   * 设置当前TOC
   */
  setCurrentToc(toc: TocStructure | null, fileName?: string): void {
    this.currentToc = toc;
    this.currentFile = fileName || null;
    
    // 通知监听器
    this.listeners.forEach(listener => {
      try {
        listener(toc);
      } catch (error) {
        console.warn('TOC listener error:', error);
      }
    });
    
    console.log(`📋 Current TOC updated: ${toc ? `${toc.totalItems} items` : 'null'}`);
  }

  /**
   * 获取当前TOC
   */
  getCurrentToc(): TocStructure | null {
    return this.currentToc;
  }

  /**
   * 根据行号查找TOC项
   */
  findTocItemByLine(lineNumber: number): TocItem | null {
    if (!this.currentToc) return null;
    
    // 找到最接近的TOC项
    let bestMatch: TocItem | null = null;
    let minDistance = Infinity;
    
    this.currentToc.flatItems.forEach(item => {
      const distance = Math.abs(item.line - lineNumber);
      if (distance < minDistance && item.line <= lineNumber) {
        minDistance = distance;
        bestMatch = item;
      }
    });
    
    return bestMatch;
  }

  /**
   * 根据偏移量查找TOC项
   */
  findTocItemByOffset(offset: number): TocItem | null {
    if (!this.currentToc) return null;
    
    let bestMatch: TocItem | null = null;
    let minDistance = Infinity;
    
    this.currentToc.flatItems.forEach(item => {
      const distance = Math.abs(item.offset - offset);
      if (distance < minDistance && item.offset <= offset) {
        minDistance = distance;
        bestMatch = item;
      }
    });
    
    return bestMatch;
  }

  /**
   * 获取下一个TOC项
   */
  getNextTocItem(currentItem: TocItem): TocItem | null {
    if (!this.currentToc) return null;
    
    const currentIndex = this.currentToc.flatItems.indexOf(currentItem);
    if (currentIndex >= 0 && currentIndex < this.currentToc.flatItems.length - 1) {
      return this.currentToc.flatItems[currentIndex + 1];
    }
    
    return null;
  }

  /**
   * 获取上一个TOC项
   */
  getPreviousTocItem(currentItem: TocItem): TocItem | null {
    if (!this.currentToc) return null;
    
    const currentIndex = this.currentToc.flatItems.indexOf(currentItem);
    if (currentIndex > 0) {
      return this.currentToc.flatItems[currentIndex - 1];
    }
    
    return null;
  }

  /**
   * 搜索TOC项
   */
  searchTocItems(query: string): TocItem[] {
    if (!this.currentToc || !query.trim()) return [];
    
    const lowerQuery = query.toLowerCase();
    return this.currentToc.flatItems.filter(item => 
      item.title.toLowerCase().includes(lowerQuery)
    );
  }

  /**
   * 添加TOC变化监听器
   */
  addTocChangeListener(listener: (toc: TocStructure | null) => void): () => void {
    this.listeners.add(listener);
    
    // 返回取消监听的函数
    return () => {
      this.listeners.delete(listener);
    };
  }

  /**
   * 清除缓存
   */
  clearCache(): void {
    this.tocCache.clear();
    console.log('🗑️ TOC cache cleared');
  }

  /**
   * 获取缓存统计
   */
  getCacheStats(): {
    size: number;
    keys: string[];
  } {
    return {
      size: this.tocCache.size,
      keys: Array.from(this.tocCache.keys())
    };
  }

  /**
   * 导出TOC为JSON
   */
  exportTocAsJson(): string | null {
    if (!this.currentToc) return null;
    
    return JSON.stringify(this.currentToc, null, 2);
  }

  /**
   * 导出TOC为Markdown
   */
  exportTocAsMarkdown(): string | null {
    if (!this.currentToc) return null;
    
    const lines: string[] = [];
    
    const processItems = (items: TocItem[], level = 0) => {
      items.forEach(item => {
        const indent = '  '.repeat(level);
        const link = item.anchor ? `#${item.anchor}` : `#line-${item.line}`;
        lines.push(`${indent}- [${item.title}](${link})`);
        
        if (item.children.length > 0) {
          processItems(item.children, level + 1);
        }
      });
    };
    
    lines.push('# Table of Contents\n');
    processItems(this.currentToc.items);
    
    return lines.join('\n');
  }
}

// 创建全局实例
export const globalTocManager = new GlobalTocManager();

export default GlobalTocManager;