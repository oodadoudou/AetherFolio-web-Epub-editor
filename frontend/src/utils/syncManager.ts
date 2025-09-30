/**
 * 双向同步管理器
 * 负责编辑器和预览面板之间的精确同步
 */

export interface SyncPosition {
  lineNumber: number;
  column: number;
  scrollPercentage: number;
  elementId?: string;
  textContent?: string;
}

export interface SyncMapping {
  editorLine: number;
  previewElementId: string;
  textContent: string;
  confidence: number; // 匹配置信度 0-1
}

export class SyncManager {
  private mappings: SyncMapping[] = [];
  private lastSyncTime = 0;
  private syncDelay = 150; // 防抖延迟
  private isScrollingFromEditor = false;
  private isScrollingFromPreview = false;
  private syncEnabled = true;

  /**
   * 构建编辑器行与预览元素的映射关系
   */
  buildMapping(editorContent: string, previewDocument: Document): SyncMapping[] {
    const mappings: SyncMapping[] = [];
    const editorLines = editorContent.split('\n');
    
    // 为预览文档中的元素添加唯一标识
    this.addElementIds(previewDocument);
    
    // 获取所有有文本内容的元素
    const textElements = this.getTextElements(previewDocument);
    
    editorLines.forEach((line, lineIndex) => {
      const trimmedLine = line.trim();
      if (trimmedLine.length < 3) return; // 跳过空行和短行
      
      // 提取行中的文本内容
      const lineText = this.extractTextFromLine(trimmedLine);
      if (!lineText) return;
      
      // 在预览文档中查找匹配的元素
      const matchedElement = this.findMatchingElement(lineText, textElements);
      if (matchedElement) {
        mappings.push({
          editorLine: lineIndex + 1,
          previewElementId: matchedElement.id,
          textContent: lineText,
          confidence: this.calculateConfidence(lineText, matchedElement.textContent || '')
        });
      }
    });
    
    this.mappings = mappings;
    return mappings;
  }
  
  /**
   * 为预览文档中的元素添加唯一ID
   */
  private addElementIds(document: Document): void {
    let idCounter = 0;
    const elements = document.querySelectorAll('p, h1, h2, h3, h4, h5, h6, div, span, li, td, th');
    
    elements.forEach(element => {
      if (!element.id && element.textContent?.trim()) {
        element.id = `sync-element-${idCounter++}`;
        element.setAttribute('data-sync-line', '0'); // 初始化
      }
    });
  }
  
  /**
   * 获取所有包含文本的元素
   */
  private getTextElements(document: Document): Element[] {
    const elements = document.querySelectorAll('[id^="sync-element-"]');
    return Array.from(elements).filter(el => {
      const text = el.textContent?.trim();
      return text && text.length > 2;
    });
  }
  
  /**
   * 从编辑器行中提取文本内容
   */
  private extractTextFromLine(line: string): string {
    // 移除HTML标签
    const withoutTags = line.replace(/<[^>]*>/g, '');
    // 移除多余空格
    const cleaned = withoutTags.replace(/\s+/g, ' ').trim();
    return cleaned;
  }
  
  /**
   * 在预览文档中查找匹配的元素
   */
  private findMatchingElement(text: string, elements: Element[]): Element | null {
    let bestMatch: Element | null = null;
    let bestScore = 0;
    
    elements.forEach(element => {
      const elementText = element.textContent?.trim() || '';
      const score = this.calculateSimilarity(text, elementText);
      
      if (score > bestScore && score > 0.7) { // 相似度阈值
        bestScore = score;
        bestMatch = element;
      }
    });
    
    return bestMatch;
  }
  
  /**
   * 计算文本相似度
   */
  private calculateSimilarity(text1: string, text2: string): number {
    if (text1 === text2) return 1;
    
    const longer = text1.length > text2.length ? text1 : text2;
    const shorter = text1.length > text2.length ? text2 : text1;
    
    if (longer.length === 0) return 1;
    
    // 使用编辑距离算法
    const editDistance = this.levenshteinDistance(longer, shorter);
    return (longer.length - editDistance) / longer.length;
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
   * 计算匹配置信度
   */
  private calculateConfidence(text1: string, text2: string): number {
    const similarity = this.calculateSimilarity(text1, text2);
    const lengthFactor = Math.min(text1.length, text2.length) / Math.max(text1.length, text2.length);
    return similarity * lengthFactor;
  }
  
  /**
   * 从编辑器行号同步到预览位置
   */
  syncFromEditor(lineNumber: number, previewDocument: Document): boolean {
    if (this.isScrollingFromPreview) return false;
    
    this.isScrollingFromEditor = true;
    
    // 查找最接近的映射
    const mapping = this.findClosestMapping(lineNumber);
    if (!mapping) {
      this.isScrollingFromEditor = false;
      return false;
    }
    
    const element = previewDocument.getElementById(mapping.previewElementId);
    if (!element) {
      this.isScrollingFromEditor = false;
      return false;
    }
    
    // 滚动到元素位置
    element.scrollIntoView({ 
      behavior: 'smooth', 
      block: 'center' 
    });
    
    // 高亮元素
    this.highlightElement(element, previewDocument);
    
    // 更新元素的行号标记
    element.setAttribute('data-sync-line', lineNumber.toString());
    
    setTimeout(() => {
      this.isScrollingFromEditor = false;
    }, 500);
    
    return true;
  }
  
  /**
   * 从预览位置同步到编辑器行号
   */
  syncFromPreview(elementId: string, editorApi: unknown): number | null {
    if (this.isScrollingFromEditor) return null;
    
    this.isScrollingFromPreview = true;
    
    const mapping = this.mappings.find(m => m.previewElementId === elementId);
    if (!mapping) {
      this.isScrollingFromPreview = false;
      return null;
    }
    
    // 跳转到编辑器行
    if (editorApi && typeof editorApi === 'object') {
      const api = editorApi as any;
      if (api.setPosition) {
        api.setPosition({ 
          lineNumber: mapping.editorLine, 
          column: 1 
        });
      }
      if (api.revealLineInCenter) {
        api.revealLineInCenter(mapping.editorLine);
      }
      if (api.focus) {
        api.focus();
      }
    }
    
    setTimeout(() => {
      this.isScrollingFromPreview = false;
    }, 500);
    
    return mapping.editorLine;
  }
  
  /**
   * 查找最接近的映射
   */
  private findClosestMapping(lineNumber: number): SyncMapping | null {
    if (this.mappings.length === 0) return null;
    
    // 查找精确匹配
    const exactMatch = this.mappings.find(m => m.editorLine === lineNumber);
    if (exactMatch) return exactMatch;
    
    // 查找最接近的映射
    let closestMapping = this.mappings[0];
    let minDistance = Math.abs(closestMapping.editorLine - lineNumber);
    
    this.mappings.forEach(mapping => {
      const distance = Math.abs(mapping.editorLine - lineNumber);
      if (distance < minDistance) {
        minDistance = distance;
        closestMapping = mapping;
      }
    });
    
    return closestMapping;
  }
  
  /**
   * 高亮预览元素
   */
  private highlightElement(element: Element, document: Document): void {
    // 移除之前的高亮
    const prevHighlighted = document.querySelectorAll('.sync-highlight');
    prevHighlighted.forEach(el => el.classList.remove('sync-highlight'));
    
    // 添加高亮样式
    element.classList.add('sync-highlight');
    
    // 3秒后移除高亮
    setTimeout(() => {
      element.classList.remove('sync-highlight');
    }, 3000);
  }
  
  /**
   * 获取当前映射统计信息
   */
  getMappingStats(): { total: number; highConfidence: number; averageConfidence: number } {
    const total = this.mappings.length;
    const highConfidence = this.mappings.filter(m => m.confidence > 0.8).length;
    const averageConfidence = total > 0 
      ? this.mappings.reduce((sum, m) => sum + m.confidence, 0) / total 
      : 0;
    
    return { total, highConfidence, averageConfidence };
  }
  
  /**
   * 清除映射
   */
  clearMappings(): void {
    this.mappings = [];
  }
  
  /**
   * 防抖处理
   */
  debounce<T extends (...args: unknown[]) => unknown>(func: T, delay: number): T {
    let timeoutId: NodeJS.Timeout;
    return ((...args: unknown[]) => {
      clearTimeout(timeoutId);
      timeoutId = setTimeout(() => func.apply(this, args), delay);
    }) as T;
  }
  
  /**
   * 获取滚动同步的防抖函数
   */
  getDebouncedSyncFromEditor() {
    return this.debounce((lineNumber: number, previewDocument: Document) => {
      this.syncFromEditor(lineNumber, previewDocument);
    }, this.syncDelay);
  }
  
  /**
   * 获取预览滚动的防抖函数
   */
  getDebouncedSyncFromPreview() {
    return this.debounce((elementId: string, editorApi: unknown) => {
      this.syncFromPreview(elementId, editorApi);
    }, this.syncDelay);
  }

  /**
   * 向HTML内容注入行标记
   * @param htmlContent HTML内容
   * @param lines 编辑器行数组
   * @returns 注入行标记后的HTML内容
   */
  injectLineMarkers(htmlContent: string, lines: string[]): string {
    if (!htmlContent || !lines || lines.length === 0) {
      return htmlContent;
    }

    // 解析HTML内容
    const parser = new DOMParser();
    const doc = parser.parseFromString(htmlContent, 'text/html');
    
    // 为元素添加行标记
    let lineCounter = 1;
    const textElements = doc.querySelectorAll('p, h1, h2, h3, h4, h5, h6, div, span, li, td, th, blockquote');
    
    textElements.forEach((element, index) => {
      const textContent = element.textContent?.trim();
      if (textContent && textContent.length > 0) {
        // 添加唯一ID和行号标记
        if (!element.id) {
          element.id = `sync-element-${index}`;
        }
        element.setAttribute('data-sync-line', lineCounter.toString());
        element.setAttribute('data-sync-text', textContent.substring(0, 50)); // 存储文本片段用于匹配
        
        // 查找对应的编辑器行
        const matchingLineIndex = this.findMatchingLineIndex(textContent, lines, lineCounter - 1);
        if (matchingLineIndex !== -1) {
          element.setAttribute('data-editor-line', (matchingLineIndex + 1).toString());
        }
        
        lineCounter++;
      }
    });
    
    // 返回处理后的HTML
    return doc.documentElement.outerHTML;
  }

  /**
   * 查找匹配的编辑器行索引
   */
  private findMatchingLineIndex(elementText: string, lines: string[], startIndex: number): number {
    const cleanElementText = this.extractTextFromLine(elementText);
    
    // 首先在当前位置附近查找
    const searchRange = 5; // 搜索范围
    const start = Math.max(0, startIndex - searchRange);
    const end = Math.min(lines.length, startIndex + searchRange);
    
    let bestMatch = -1;
    let bestScore = 0;
    
    for (let i = start; i < end; i++) {
      const lineText = this.extractTextFromLine(lines[i]);
      if (lineText.length < 3) continue;
      
      const similarity = this.calculateSimilarity(cleanElementText, lineText);
      if (similarity > bestScore && similarity > 0.6) {
        bestScore = similarity;
        bestMatch = i;
      }
    }
    
    // 如果没有找到好的匹配，扩大搜索范围
    if (bestMatch === -1) {
      for (let i = 0; i < lines.length; i++) {
        const lineText = this.extractTextFromLine(lines[i]);
        if (lineText.length < 3) continue;
        
        const similarity = this.calculateSimilarity(cleanElementText, lineText);
        if (similarity > bestScore && similarity > 0.7) {
          bestScore = similarity;
          bestMatch = i;
        }
      }
    }
    
    return bestMatch;
  }

  /**
   * 启用同步
   */
  enableSync(): void {
    this.syncEnabled = true;
  }

  /**
   * 禁用同步
   */
  disableSync(): void {
    this.syncEnabled = false;
  }

  /**
   * 检查同步是否启用
   */
  isSyncEnabled(): boolean {
    return this.syncEnabled;
  }

  /**
   * 清理同步管理器资源
   */
  cleanup(): void {
    // 清除映射
    this.clearMappings();
    
    // 重置状态变量
    this.lastSyncTime = 0;
    this.isScrollingFromEditor = false;
    this.isScrollingFromPreview = false;
    
    // 清理可能存在的定时器（通过重置防抖延迟来清理）
    this.syncDelay = 150;
  }
}

// 全局同步管理器实例
export const globalSyncManager = new SyncManager();