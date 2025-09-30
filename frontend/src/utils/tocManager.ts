/**
 * TOC管理器
 * 负责TOC文件的解析、编辑、同步和管理
 * 支持toc.ncx和nav.xhtml格式
 */

export interface TocItem {
  id: string;
  title: string;
  href: string;
  level: number;
  playOrder?: number;
  children?: TocItem[];
  parent?: string;
}

export interface TocStructure {
  format: 'ncx' | 'nav';
  items: TocItem[];
  metadata?: {
    title?: string;
    author?: string;
    uid?: string;
    depth?: number;
    totalPageCount?: number;
    maxPageNumber?: number;
  };
}

export interface TocEditOperation {
  type: 'add' | 'remove' | 'move' | 'edit' | 'reorder';
  itemId?: string;
  newItem?: Partial<TocItem>;
  targetPosition?: number;
  parentId?: string;
}

export interface TocValidationResult {
  isValid: boolean;
  errors: string[];
  warnings: string[];
}

export class TocManager {
  private tocStructure: TocStructure | null = null;
  private originalContent: string = '';
  private isDirty: boolean = false;
  private changeListeners: Array<(structure: TocStructure) => void> = [];
  private validationListeners: Array<(result: TocValidationResult) => void> = [];

  /**
   * 解析TOC文件内容
   */
  parseTocContent(content: string, filename: string): TocStructure {
    this.originalContent = content;
    
    if (filename.endsWith('.ncx') || content.includes('ncx')) {
      this.tocStructure = this.parseNcxContent(content);
    } else if (filename.endsWith('.xhtml') || filename.endsWith('.html')) {
      this.tocStructure = this.parseNavContent(content);
    } else {
      throw new Error('不支持的TOC文件格式');
    }
    
    this.isDirty = false;
    this.notifyChangeListeners();
    return this.tocStructure;
  }

  /**
   * 解析NCX格式的TOC
   */
  private parseNcxContent(content: string): TocStructure {
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/xml');
    
    if (doc.querySelector('parsererror')) {
      throw new Error('NCX文件格式错误');
    }

    const metadata = this.extractNcxMetadata(doc);
    const navMap = doc.querySelector('navMap');
    const items: TocItem[] = [];

    if (navMap) {
      const navPoints = navMap.querySelectorAll('navPoint');
      navPoints.forEach(navPoint => {
        const item = this.parseNcxNavPoint(navPoint);
        if (item) {
          items.push(item);
        }
      });
    }

    return {
      format: 'ncx',
      items: this.buildHierarchy(items),
      metadata
    };
  }

  /**
   * 解析NCX元数据
   */
  private extractNcxMetadata(doc: Document): TocStructure['metadata'] {
    const head = doc.querySelector('head');
    if (!head) return {};

    const metadata: TocStructure['metadata'] = {};
    
    const metas = head.querySelectorAll('meta');
    metas.forEach(meta => {
      const name = meta.getAttribute('name');
      const content = meta.getAttribute('content');
      
      if (name && content) {
        switch (name) {
          case 'dtb:uid':
            metadata.uid = content;
            break;
          case 'dtb:depth':
            metadata.depth = parseInt(content, 10);
            break;
          case 'dtb:totalPageCount':
            metadata.totalPageCount = parseInt(content, 10);
            break;
          case 'dtb:maxPageNumber':
            metadata.maxPageNumber = parseInt(content, 10);
            break;
        }
      }
    });

    const docTitle = doc.querySelector('docTitle text');
    if (docTitle) {
      metadata.title = docTitle.textContent || '';
    }

    const docAuthor = doc.querySelector('docAuthor text');
    if (docAuthor) {
      metadata.author = docAuthor.textContent || '';
    }

    return metadata;
  }

  /**
   * 解析NCX导航点
   */
  private parseNcxNavPoint(navPoint: Element, level: number = 1): TocItem | null {
    const id = navPoint.getAttribute('id');
    const playOrder = navPoint.getAttribute('playOrder');
    
    const navLabel = navPoint.querySelector('navLabel text');
    const content = navPoint.querySelector('content');
    
    if (!id || !navLabel || !content) {
      return null;
    }

    const title = navLabel.textContent || '';
    const href = content.getAttribute('src') || '';

    const item: TocItem = {
      id,
      title,
      href,
      level,
      playOrder: playOrder ? parseInt(playOrder, 10) : undefined
    };

    // 解析子导航点
    const childNavPoints = navPoint.querySelectorAll(':scope > navPoint');
    if (childNavPoints.length > 0) {
      item.children = [];
      childNavPoints.forEach(childNavPoint => {
        const childItem = this.parseNcxNavPoint(childNavPoint, level + 1);
        if (childItem) {
          childItem.parent = id;
          item.children!.push(childItem);
        }
      });
    }

    return item;
  }

  /**
   * 解析Nav格式的TOC
   */
  private parseNavContent(content: string): TocStructure {
    const parser = new DOMParser();
    const doc = parser.parseFromString(content, 'text/html');
    
    const nav = doc.querySelector('nav[epub\\:type="toc"], nav.toc');
    if (!nav) {
      throw new Error('未找到TOC导航元素');
    }

    const items: TocItem[] = [];
    const ol = nav.querySelector('ol');
    
    if (ol) {
      const listItems = ol.querySelectorAll(':scope > li');
      listItems.forEach((li, index) => {
        const item = this.parseNavListItem(li, 1, `nav-item-${index}`);
        if (item) {
          items.push(item);
        }
      });
    }

    return {
      format: 'nav',
      items,
      metadata: this.extractNavMetadata(doc)
    };
  }

  /**
   * 解析Nav列表项
   */
  private parseNavListItem(li: Element, level: number, baseId: string): TocItem | null {
    const link = li.querySelector('a');
    if (!link) return null;

    const title = link.textContent?.trim() || '';
    const href = link.getAttribute('href') || '';
    const id = link.getAttribute('id') || baseId;

    const item: TocItem = {
      id,
      title,
      href,
      level
    };

    // 解析子列表
    const childOl = li.querySelector('ol');
    if (childOl) {
      item.children = [];
      const childItems = childOl.querySelectorAll(':scope > li');
      childItems.forEach((childLi, index) => {
        const childItem = this.parseNavListItem(childLi, level + 1, `${baseId}-${index}`);
        if (childItem) {
          childItem.parent = id;
          item.children!.push(childItem);
        }
      });
    }

    return item;
  }

  /**
   * 提取Nav元数据
   */
  private extractNavMetadata(doc: Document): TocStructure['metadata'] {
    const metadata: TocStructure['metadata'] = {};
    
    const title = doc.querySelector('title');
    if (title) {
      metadata.title = title.textContent || '';
    }

    return metadata;
  }

  /**
   * 构建层级结构
   */
  private buildHierarchy(items: TocItem[]): TocItem[] {
    const rootItems: TocItem[] = [];
    const itemMap = new Map<string, TocItem>();

    // 创建映射
    items.forEach(item => {
      itemMap.set(item.id, item);
    });

    // 构建层级关系
    items.forEach(item => {
      if (item.parent && itemMap.has(item.parent)) {
        const parent = itemMap.get(item.parent)!;
        if (!parent.children) {
          parent.children = [];
        }
        parent.children.push(item);
      } else {
        rootItems.push(item);
      }
    });

    return rootItems;
  }

  /**
   * 添加TOC项
   */
  addTocItem(newItem: Omit<TocItem, 'id'>, parentId?: string, position?: number): string {
    if (!this.tocStructure) {
      throw new Error('TOC结构未初始化');
    }

    const id = this.generateUniqueId(newItem.title);
    const item: TocItem = {
      ...newItem,
      id,
      parent: parentId
    };

    if (parentId) {
      const parent = this.findItemById(parentId);
      if (!parent) {
        throw new Error(`未找到父项: ${parentId}`);
      }
      
      if (!parent.children) {
        parent.children = [];
      }
      
      if (position !== undefined && position >= 0 && position <= parent.children.length) {
        parent.children.splice(position, 0, item);
      } else {
        parent.children.push(item);
      }
    } else {
      if (position !== undefined && position >= 0 && position <= this.tocStructure.items.length) {
        this.tocStructure.items.splice(position, 0, item);
      } else {
        this.tocStructure.items.push(item);
      }
    }

    this.markDirty();
    return id;
  }

  /**
   * 删除TOC项
   */
  removeTocItem(itemId: string): boolean {
    if (!this.tocStructure) return false;

    const removeFromArray = (items: TocItem[]): boolean => {
      const index = items.findIndex(item => item.id === itemId);
      if (index !== -1) {
        items.splice(index, 1);
        return true;
      }
      
      for (const item of items) {
        if (item.children && removeFromArray(item.children)) {
          return true;
        }
      }
      
      return false;
    };

    const removed = removeFromArray(this.tocStructure.items);
    if (removed) {
      this.markDirty();
    }
    
    return removed;
  }

  /**
   * 编辑TOC项
   */
  editTocItem(itemId: string, updates: Partial<TocItem>): boolean {
    const item = this.findItemById(itemId);
    if (!item) return false;

    Object.assign(item, updates);
    this.markDirty();
    return true;
  }

  /**
   * 移动TOC项
   */
  moveTocItem(itemId: string, newParentId?: string, newPosition?: number): boolean {
    if (!this.tocStructure) return false;

    const item = this.findItemById(itemId);
    if (!item) return false;

    // 从原位置移除
    this.removeTocItem(itemId);
    
    // 添加到新位置
    try {
      this.addTocItem(item, newParentId, newPosition);
      return true;
    } catch (error) {
      console.error('移动TOC项失败:', error);
      return false;
    }
  }

  /**
   * 重新排序TOC项
   */
  reorderTocItems(parentId: string | null, newOrder: string[]): boolean {
    if (!this.tocStructure) return false;

    const items = parentId 
      ? this.findItemById(parentId)?.children 
      : this.tocStructure.items;
    
    if (!items) return false;

    const reorderedItems: TocItem[] = [];
    
    newOrder.forEach(id => {
      const item = items.find(item => item.id === id);
      if (item) {
        reorderedItems.push(item);
      }
    });

    // 添加未在新顺序中的项目
    items.forEach(item => {
      if (!newOrder.includes(item.id)) {
        reorderedItems.push(item);
      }
    });

    if (parentId) {
      const parent = this.findItemById(parentId);
      if (parent) {
        parent.children = reorderedItems;
      }
    } else {
      this.tocStructure.items = reorderedItems;
    }

    this.markDirty();
    return true;
  }

  /**
   * 根据ID查找TOC项
   */
  findItemById(id: string): TocItem | null {
    if (!this.tocStructure) return null;

    const findInItems = (items: TocItem[]): TocItem | null => {
      for (const item of items) {
        if (item.id === id) {
          return item;
        }
        if (item.children) {
          const found = findInItems(item.children);
          if (found) return found;
        }
      }
      return null;
    };

    return findInItems(this.tocStructure.items);
  }

  /**
   * 验证TOC结构
   */
  validateTocStructure(): TocValidationResult {
    const result: TocValidationResult = {
      isValid: true,
      errors: [],
      warnings: []
    };

    if (!this.tocStructure) {
      result.isValid = false;
      result.errors.push('TOC结构未初始化');
      return result;
    }

    const validateItems = (items: TocItem[], level: number = 1) => {
      items.forEach((item, index) => {
        // 检查必需字段
        if (!item.id) {
          result.errors.push(`第${level}级第${index + 1}项缺少ID`);
          result.isValid = false;
        }
        
        if (!item.title.trim()) {
          result.errors.push(`项目"${item.id}"缺少标题`);
          result.isValid = false;
        }
        
        if (!item.href.trim()) {
          result.warnings.push(`项目"${item.id}"缺少链接`);
        }

        // 检查层级
        if (item.level !== level) {
          result.warnings.push(`项目"${item.id}"的层级不匹配`);
        }

        // 递归检查子项
        if (item.children && item.children.length > 0) {
          validateItems(item.children, level + 1);
        }
      });
    };

    validateItems(this.tocStructure.items);
    this.notifyValidationListeners(result);
    return result;
  }

  /**
   * 生成TOC内容
   */
  generateTocContent(): string {
    if (!this.tocStructure) {
      throw new Error('TOC结构未初始化');
    }

    if (this.tocStructure.format === 'ncx') {
      return this.generateNcxContent();
    } else {
      return this.generateNavContent();
    }
  }

  /**
   * 生成NCX格式内容
   */
  private generateNcxContent(): string {
    if (!this.tocStructure) throw new Error('TOC结构未初始化');

    const { items, metadata } = this.tocStructure;
    
    let ncxContent = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    ncxContent += `<!DOCTYPE ncx PUBLIC "-//NISO//DTD ncx 2005-1//EN" "http://www.daisy.org/z3986/2005/ncx-2005-1.dtd">\n`;
    ncxContent += `<ncx xmlns="http://www.daisy.org/z3986/2005/ncx/" version="2005-1">\n`;
    
    // 头部信息
    ncxContent += `  <head>\n`;
    if (metadata?.uid) {
      ncxContent += `    <meta name="dtb:uid" content="${this.escapeXml(metadata.uid)}"/>\n`;
    }
    if (metadata?.depth) {
      ncxContent += `    <meta name="dtb:depth" content="${metadata.depth}"/>\n`;
    }
    if (metadata?.totalPageCount) {
      ncxContent += `    <meta name="dtb:totalPageCount" content="${metadata.totalPageCount}"/>\n`;
    }
    if (metadata?.maxPageNumber) {
      ncxContent += `    <meta name="dtb:maxPageNumber" content="${metadata.maxPageNumber}"/>\n`;
    }
    ncxContent += `  </head>\n`;
    
    // 文档标题
    if (metadata?.title) {
      ncxContent += `  <docTitle>\n`;
      ncxContent += `    <text>${this.escapeXml(metadata.title)}</text>\n`;
      ncxContent += `  </docTitle>\n`;
    }
    
    // 文档作者
    if (metadata?.author) {
      ncxContent += `  <docAuthor>\n`;
      ncxContent += `    <text>${this.escapeXml(metadata.author)}</text>\n`;
      ncxContent += `  </docAuthor>\n`;
    }
    
    // 导航映射
    ncxContent += `  <navMap>\n`;
    
    let playOrder = 1;
    const generateNavPoints = (items: TocItem[], indent: string = '    ') => {
      items.forEach(item => {
        ncxContent += `${indent}<navPoint id="${this.escapeXml(item.id)}" playOrder="${item.playOrder || playOrder++}">\n`;
        ncxContent += `${indent}  <navLabel>\n`;
        ncxContent += `${indent}    <text>${this.escapeXml(item.title)}</text>\n`;
        ncxContent += `${indent}  </navLabel>\n`;
        ncxContent += `${indent}  <content src="${this.escapeXml(item.href)}"/>\n`;
        
        if (item.children && item.children.length > 0) {
          generateNavPoints(item.children, indent + '  ');
        }
        
        ncxContent += `${indent}</navPoint>\n`;
      });
    };
    
    generateNavPoints(items);
    ncxContent += `  </navMap>\n`;
    ncxContent += `</ncx>`;
    
    return ncxContent;
  }

  /**
   * 生成Nav格式内容
   */
  private generateNavContent(): string {
    if (!this.tocStructure) throw new Error('TOC结构未初始化');

    const { items, metadata } = this.tocStructure;
    
    let navContent = `<?xml version="1.0" encoding="UTF-8"?>\n`;
    navContent += `<!DOCTYPE html>\n`;
    navContent += `<html xmlns="http://www.w3.org/1999/xhtml" xmlns:epub="http://www.idpf.org/2007/ops">\n`;
    navContent += `<head>\n`;
    
    if (metadata?.title) {
      navContent += `  <title>${this.escapeHtml(metadata.title)}</title>\n`;
    }
    
    navContent += `</head>\n`;
    navContent += `<body>\n`;
    navContent += `  <nav epub:type="toc">\n`;
    
    if (metadata?.title) {
      navContent += `    <h1>${this.escapeHtml(metadata.title)}</h1>\n`;
    }
    
    navContent += `    <ol>\n`;
    
    const generateListItems = (items: TocItem[], indent: string = '      ') => {
      items.forEach(item => {
        navContent += `${indent}<li>\n`;
        navContent += `${indent}  <a href="${this.escapeHtml(item.href)}">${this.escapeHtml(item.title)}</a>\n`;
        
        if (item.children && item.children.length > 0) {
          navContent += `${indent}  <ol>\n`;
          generateListItems(item.children, indent + '    ');
          navContent += `${indent}  </ol>\n`;
        }
        
        navContent += `${indent}</li>\n`;
      });
    };
    
    generateListItems(items);
    navContent += `    </ol>\n`;
    navContent += `  </nav>\n`;
    navContent += `</body>\n`;
    navContent += `</html>`;
    
    return navContent;
  }

  /**
   * 生成唯一ID
   */
  private generateUniqueId(title: string): string {
    const baseId = title
      .toLowerCase()
      .replace(/[^a-z0-9\u4e00-\u9fff]/g, '-')
      .replace(/-+/g, '-')
      .replace(/^-|-$/g, '')
      .substring(0, 20);
    
    let counter = 1;
    let id = baseId || 'item';
    
    while (this.findItemById(id)) {
      id = `${baseId}-${counter++}`;
    }
    
    return id;
  }

  /**
   * XML转义
   */
  private escapeXml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&apos;');
  }

  /**
   * HTML转义
   */
  private escapeHtml(text: string): string {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;');
  }

  /**
   * 标记为已修改
   */
  private markDirty(): void {
    this.isDirty = true;
    this.notifyChangeListeners();
  }

  /**
   * 通知变更监听器
   */
  private notifyChangeListeners(): void {
    if (this.tocStructure) {
      this.changeListeners.forEach(listener => {
        try {
          listener(this.tocStructure!);
        } catch (error) {
          console.error('TOC变更监听器错误:', error);
        }
      });
    }
  }

  /**
   * 通知验证监听器
   */
  private notifyValidationListeners(result: TocValidationResult): void {
    this.validationListeners.forEach(listener => {
      try {
        listener(result);
      } catch (error) {
        console.error('TOC验证监听器错误:', error);
      }
    });
  }

  /**
   * 添加变更监听器
   */
  addChangeListener(listener: (structure: TocStructure) => void): void {
    this.changeListeners.push(listener);
  }

  /**
   * 移除变更监听器
   */
  removeChangeListener(listener: (structure: TocStructure) => void): void {
    const index = this.changeListeners.indexOf(listener);
    if (index !== -1) {
      this.changeListeners.splice(index, 1);
    }
  }

  /**
   * 添加验证监听器
   */
  addValidationListener(listener: (result: TocValidationResult) => void): void {
    this.validationListeners.push(listener);
  }

  /**
   * 移除验证监听器
   */
  removeValidationListener(listener: (result: TocValidationResult) => void): void {
    const index = this.validationListeners.indexOf(listener);
    if (index !== -1) {
      this.validationListeners.splice(index, 1);
    }
  }

  /**
   * 获取TOC结构
   */
  getTocStructure(): TocStructure | null {
    return this.tocStructure;
  }

  /**
   * 检查是否有未保存的更改
   */
  isDirtyState(): boolean {
    return this.isDirty;
  }

  /**
   * 重置脏状态
   */
  resetDirtyState(): void {
    this.isDirty = false;
  }

  /**
   * 获取扁平化的TOC项列表
   */
  getFlattenedItems(): TocItem[] {
    if (!this.tocStructure) return [];

    const flattened: TocItem[] = [];
    
    const flatten = (items: TocItem[]) => {
      items.forEach(item => {
        flattened.push(item);
        if (item.children) {
          flatten(item.children);
        }
      });
    };
    
    flatten(this.tocStructure.items);
    return flattened;
  }

  /**
   * 清理资源
   */
  cleanup(): void {
    this.tocStructure = null;
    this.originalContent = '';
    this.isDirty = false;
    this.changeListeners = [];
    this.validationListeners = [];
  }
}

// 导出全局实例
export const globalTocManager = new TocManager();