/**
 * EPUB解析Web Worker
 * 在后台线程中处理EPUB文件解析，避免阻塞主线程
 */

// Worker消息类型定义
interface WorkerMessage {
  id: string;
  type: 'parse' | 'validate' | 'extract' | 'optimize';
  data: any;
}

interface WorkerResponse {
  id: string;
  type: 'success' | 'error' | 'progress';
  data: any;
  error?: string;
}

// EPUB文件结构接口
interface EpubStructure {
  metadata: {
    title: string;
    author: string;
    language: string;
    identifier: string;
    publisher?: string;
    date?: string;
    description?: string;
    rights?: string;
  };
  manifest: {
    [id: string]: {
      href: string;
      mediaType: string;
      properties?: string[];
    };
  };
  spine: {
    id: string;
    href: string;
    linear: boolean;
  }[];
  toc: {
    id: string;
    title: string;
    href: string;
    children?: any[];
  }[];
  resources: {
    images: string[];
    styles: string[];
    fonts: string[];
    scripts: string[];
  };
}

// AST节点接口
interface ASTNode {
  type: string;
  tag?: string;
  attributes?: { [key: string]: string };
  children?: ASTNode[];
  text?: string;
  position?: {
    start: { line: number; column: number; offset: number };
    end: { line: number; column: number; offset: number };
  };
}

// 解析选项
interface ParseOptions {
  validateStructure: boolean;
  extractResources: boolean;
  generateAST: boolean;
  optimizeContent: boolean;
  preserveWhitespace: boolean;
}

/**
 * HTML/XML解析器
 */
class HTMLParser {
  private position: { line: number; column: number; offset: number } = {
    line: 1,
    column: 1,
    offset: 0
  };

  /**
   * 解析HTML/XML内容为AST
   */
  public parse(content: string): ASTNode {
    this.position = { line: 1, column: 1, offset: 0 };
    return this.parseNode(content, 0).node;
  }

  private parseNode(content: string, startIndex: number): { node: ASTNode; endIndex: number } {
    const trimmed = content.slice(startIndex).trim();
    
    if (!trimmed) {
      return {
        node: { type: 'text', text: '' },
        endIndex: content.length
      };
    }

    // 处理文本节点
    if (!trimmed.startsWith('<')) {
      const textEnd = trimmed.indexOf('<');
      const text = textEnd === -1 ? trimmed : trimmed.slice(0, textEnd);
      return {
        node: {
          type: 'text',
          text: text.trim(),
          position: this.getCurrentPosition()
        },
        endIndex: startIndex + text.length
      };
    }

    // 处理注释
    if (trimmed.startsWith('<!--')) {
      const commentEnd = trimmed.indexOf('-->');
      if (commentEnd !== -1) {
        const comment = trimmed.slice(4, commentEnd);
        return {
          node: {
            type: 'comment',
            text: comment,
            position: this.getCurrentPosition()
          },
          endIndex: startIndex + commentEnd + 3
        };
      }
    }

    // 处理CDATA
    if (trimmed.startsWith('<![CDATA[')) {
      const cdataEnd = trimmed.indexOf(']]>');
      if (cdataEnd !== -1) {
        const cdata = trimmed.slice(9, cdataEnd);
        return {
          node: {
            type: 'cdata',
            text: cdata,
            position: this.getCurrentPosition()
          },
          endIndex: startIndex + cdataEnd + 3
        };
      }
    }

    // 处理DOCTYPE
    if (trimmed.startsWith('<!DOCTYPE')) {
      const doctypeEnd = trimmed.indexOf('>');
      if (doctypeEnd !== -1) {
        return {
          node: {
            type: 'doctype',
            text: trimmed.slice(0, doctypeEnd + 1),
            position: this.getCurrentPosition()
          },
          endIndex: startIndex + doctypeEnd + 1
        };
      }
    }

    // 处理元素节点
    const tagMatch = trimmed.match(/^<([^\s>]+)/);
    if (!tagMatch) {
      throw new Error('Invalid tag format');
    }

    const tagName = tagMatch[1];
    const isSelfClosing = trimmed.includes('/>');
    const tagEnd = trimmed.indexOf(isSelfClosing ? '/>' : '>');
    
    if (tagEnd === -1) {
      throw new Error('Unclosed tag');
    }

    // 解析属性
    const attributesStr = trimmed.slice(tagName.length + 1, tagEnd).trim();
    const attributes = this.parseAttributes(attributesStr);

    const node: ASTNode = {
      type: 'element',
      tag: tagName,
      attributes,
      children: [],
      position: this.getCurrentPosition()
    };

    let currentIndex = startIndex + tagEnd + (isSelfClosing ? 2 : 1);

    // 如果是自闭合标签，直接返回
    if (isSelfClosing) {
      return { node, endIndex: currentIndex };
    }

    // 解析子节点
    while (currentIndex < content.length) {
      const remaining = content.slice(currentIndex);
      
      // 查找结束标签
      const endTagPattern = new RegExp(`</${tagName}\\s*>`, 'i');
      const endTagMatch = remaining.match(endTagPattern);
      
      if (endTagMatch && endTagMatch.index === 0) {
        // 找到结束标签
        currentIndex += endTagMatch[0].length;
        break;
      }

      // 解析子节点
      try {
        const childResult = this.parseNode(content, currentIndex);
        if (childResult.node.text?.trim() || childResult.node.type !== 'text') {
          node.children!.push(childResult.node);
        }
        currentIndex = childResult.endIndex;
      } catch (error) {
        // 如果解析失败，跳过当前字符
        currentIndex++;
      }
    }

    return { node, endIndex: currentIndex };
  }

  private parseAttributes(attributesStr: string): { [key: string]: string } {
    const attributes: { [key: string]: string } = {};
    
    if (!attributesStr.trim()) {
      return attributes;
    }

    // 简化的属性解析
    const attrPattern = /([^\s=]+)(?:=(["'])((?:(?!\2)[^\\]|\\.)*)\2|=([^\s]+))?/g;
    let match;

    while ((match = attrPattern.exec(attributesStr)) !== null) {
      const name = match[1];
      const value = match[3] || match[4] || '';
      attributes[name] = value;
    }

    return attributes;
  }

  private getCurrentPosition(): { start: { line: number; column: number; offset: number }; end: { line: number; column: number; offset: number } } {
    return {
      start: { ...this.position },
      end: { ...this.position }
    };
  }
}

/**
 * EPUB解析器
 */
class EpubParser {
  private htmlParser: HTMLParser;

  constructor() {
    this.htmlParser = new HTMLParser();
  }

  /**
   * 解析EPUB文件
   */
  public async parseEpub(file: File, options: ParseOptions): Promise<EpubStructure> {
    try {
      // 发送进度更新
      this.sendProgress('开始解析EPUB文件...', 0);

      // 读取ZIP文件内容
      const zipContent = await this.readZipFile(file);
      this.sendProgress('ZIP文件读取完成', 20);

      // 解析container.xml
      const containerXml = zipContent['META-INF/container.xml'];
      if (!containerXml) {
        throw new Error('Missing container.xml');
      }

      const containerAST = this.htmlParser.parse(containerXml);
      const opfPath = this.extractOpfPath(containerAST);
      this.sendProgress('Container解析完成', 40);

      // 解析OPF文件
      const opfContent = zipContent[opfPath];
      if (!opfContent) {
        throw new Error('Missing OPF file');
      }

      const opfAST = this.htmlParser.parse(opfContent);
      const structure = this.parseOpfStructure(opfAST, zipContent, options);
      this.sendProgress('OPF解析完成', 60);

      // 解析TOC
      if (structure.manifest['toc']) {
        const tocPath = structure.manifest['toc'].href;
        const tocContent = zipContent[tocPath];
        if (tocContent) {
          structure.toc = this.parseToc(tocContent);
        }
      }
      this.sendProgress('TOC解析完成', 80);

      // 提取资源
      if (options.extractResources) {
        structure.resources = this.extractResources(zipContent);
      }
      this.sendProgress('资源提取完成', 90);

      // 验证结构
      if (options.validateStructure) {
        this.validateEpubStructure(structure);
      }
      this.sendProgress('解析完成', 100);

      return structure;
    } catch (error) {
      throw new Error(`EPUB解析失败: ${error.message}`);
    }
  }

  /**
   * 读取ZIP文件内容
   */
  private async readZipFile(file: File): Promise<{ [path: string]: string }> {
    // 简化的ZIP读取实现
    // 实际项目中应该使用专门的ZIP库如JSZip
    const arrayBuffer = await file.arrayBuffer();
    const content: { [path: string]: string } = {};
    
    // 这里应该实现真正的ZIP解析
    // 为了演示，返回模拟数据
    content['META-INF/container.xml'] = `<?xml version="1.0"?>
<container version="1.0" xmlns="urn:oasis:names:tc:opendocument:xmlns:container">
  <rootfiles>
    <rootfile full-path="OEBPS/content.opf" media-type="application/oebps-package+xml"/>
  </rootfiles>
</container>`;
    
    return content;
  }

  /**
   * 提取OPF路径
   */
  private extractOpfPath(containerAST: ASTNode): string {
    // 遍历AST查找rootfile元素
    const rootfile = this.findElementByTag(containerAST, 'rootfile');
    if (rootfile && rootfile.attributes && rootfile.attributes['full-path']) {
      return rootfile.attributes['full-path'];
    }
    throw new Error('Cannot find OPF path in container.xml');
  }

  /**
   * 解析OPF结构
   */
  private parseOpfStructure(opfAST: ASTNode, zipContent: { [path: string]: string }, options: ParseOptions): EpubStructure {
    const structure: EpubStructure = {
      metadata: {
        title: '',
        author: '',
        language: '',
        identifier: ''
      },
      manifest: {},
      spine: [],
      toc: [],
      resources: {
        images: [],
        styles: [],
        fonts: [],
        scripts: []
      }
    };

    // 解析metadata
    const metadataElement = this.findElementByTag(opfAST, 'metadata');
    if (metadataElement) {
      structure.metadata = this.parseMetadata(metadataElement);
    }

    // 解析manifest
    const manifestElement = this.findElementByTag(opfAST, 'manifest');
    if (manifestElement) {
      structure.manifest = this.parseManifest(manifestElement);
    }

    // 解析spine
    const spineElement = this.findElementByTag(opfAST, 'spine');
    if (spineElement) {
      structure.spine = this.parseSpine(spineElement, structure.manifest);
    }

    return structure;
  }

  /**
   * 解析元数据
   */
  private parseMetadata(metadataElement: ASTNode): any {
    const metadata: any = {
      title: '',
      author: '',
      language: '',
      identifier: ''
    };

    if (metadataElement.children) {
      for (const child of metadataElement.children) {
        if (child.type === 'element' && child.tag) {
          const tagName = child.tag.toLowerCase();
          const text = this.getElementText(child);
          
          switch (tagName) {
            case 'dc:title':
            case 'title':
              metadata.title = text;
              break;
            case 'dc:creator':
            case 'creator':
              metadata.author = text;
              break;
            case 'dc:language':
            case 'language':
              metadata.language = text;
              break;
            case 'dc:identifier':
            case 'identifier':
              metadata.identifier = text;
              break;
            case 'dc:publisher':
            case 'publisher':
              metadata.publisher = text;
              break;
            case 'dc:date':
            case 'date':
              metadata.date = text;
              break;
            case 'dc:description':
            case 'description':
              metadata.description = text;
              break;
            case 'dc:rights':
            case 'rights':
              metadata.rights = text;
              break;
          }
        }
      }
    }

    return metadata;
  }

  /**
   * 解析manifest
   */
  private parseManifest(manifestElement: ASTNode): any {
    const manifest: any = {};

    if (manifestElement.children) {
      for (const child of manifestElement.children) {
        if (child.type === 'element' && child.tag === 'item' && child.attributes) {
          const id = child.attributes.id;
          const href = child.attributes.href;
          const mediaType = child.attributes['media-type'];
          const properties = child.attributes.properties;

          if (id && href && mediaType) {
            manifest[id] = {
              href,
              mediaType,
              properties: properties ? properties.split(' ') : []
            };
          }
        }
      }
    }

    return manifest;
  }

  /**
   * 解析spine
   */
  private parseSpine(spineElement: ASTNode, manifest: any): any[] {
    const spine: any[] = [];

    if (spineElement.children) {
      for (const child of spineElement.children) {
        if (child.type === 'element' && child.tag === 'itemref' && child.attributes) {
          const idref = child.attributes.idref;
          const linear = child.attributes.linear !== 'no';

          if (idref && manifest[idref]) {
            spine.push({
              id: idref,
              href: manifest[idref].href,
              linear
            });
          }
        }
      }
    }

    return spine;
  }

  /**
   * 解析TOC
   */
  private parseToc(tocContent: string): any[] {
    const tocAST = this.htmlParser.parse(tocContent);
    const navElement = this.findElementByTag(tocAST, 'nav') || this.findElementByTag(tocAST, 'ncx');
    
    if (navElement) {
      return this.parseTocItems(navElement);
    }

    return [];
  }

  /**
   * 解析TOC项目
   */
  private parseTocItems(element: ASTNode): any[] {
    const items: any[] = [];

    if (element.children) {
      for (const child of element.children) {
        if (child.type === 'element') {
          if (child.tag === 'li' || child.tag === 'navPoint') {
            const item = this.parseTocItem(child);
            if (item) {
              items.push(item);
            }
          } else if (child.tag === 'ol' || child.tag === 'ul') {
            items.push(...this.parseTocItems(child));
          }
        }
      }
    }

    return items;
  }

  /**
   * 解析单个TOC项目
   */
  private parseTocItem(element: ASTNode): any | null {
    const aElement = this.findElementByTag(element, 'a');
    if (aElement && aElement.attributes && aElement.attributes.href) {
      return {
        id: aElement.attributes.id || '',
        title: this.getElementText(aElement),
        href: aElement.attributes.href,
        children: this.parseTocItems(element)
      };
    }
    return null;
  }

  /**
   * 提取资源
   */
  private extractResources(zipContent: { [path: string]: string }): any {
    const resources = {
      images: [] as string[],
      styles: [] as string[],
      fonts: [] as string[],
      scripts: [] as string[]
    };

    for (const path in zipContent) {
      const ext = path.split('.').pop()?.toLowerCase();
      
      switch (ext) {
        case 'jpg':
        case 'jpeg':
        case 'png':
        case 'gif':
        case 'svg':
        case 'webp':
          resources.images.push(path);
          break;
        case 'css':
          resources.styles.push(path);
          break;
        case 'ttf':
        case 'otf':
        case 'woff':
        case 'woff2':
          resources.fonts.push(path);
          break;
        case 'js':
          resources.scripts.push(path);
          break;
      }
    }

    return resources;
  }

  /**
   * 验证EPUB结构
   */
  private validateEpubStructure(structure: EpubStructure): void {
    // 验证必需的元数据
    if (!structure.metadata.title) {
      throw new Error('Missing required metadata: title');
    }
    if (!structure.metadata.identifier) {
      throw new Error('Missing required metadata: identifier');
    }
    if (!structure.metadata.language) {
      throw new Error('Missing required metadata: language');
    }

    // 验证manifest
    if (Object.keys(structure.manifest).length === 0) {
      throw new Error('Empty manifest');
    }

    // 验证spine
    if (structure.spine.length === 0) {
      throw new Error('Empty spine');
    }

    // 验证spine引用的文件在manifest中存在
    for (const spineItem of structure.spine) {
      if (!structure.manifest[spineItem.id]) {
        throw new Error(`Spine item ${spineItem.id} not found in manifest`);
      }
    }
  }

  /**
   * 查找指定标签的元素
   */
  private findElementByTag(node: ASTNode, tagName: string): ASTNode | null {
    if (node.type === 'element' && node.tag?.toLowerCase() === tagName.toLowerCase()) {
      return node;
    }

    if (node.children) {
      for (const child of node.children) {
        const found = this.findElementByTag(child, tagName);
        if (found) {
          return found;
        }
      }
    }

    return null;
  }

  /**
   * 获取元素的文本内容
   */
  private getElementText(node: ASTNode): string {
    if (node.type === 'text') {
      return node.text || '';
    }

    if (node.children) {
      return node.children
        .map(child => this.getElementText(child))
        .join('')
        .trim();
    }

    return '';
  }

  /**
   * 发送进度更新
   */
  private sendProgress(message: string, progress: number): void {
    self.postMessage({
      id: 'current',
      type: 'progress',
      data: { message, progress }
    });
  }
}

// Worker实例
const epubParser = new EpubParser();

// 监听主线程消息
self.addEventListener('message', async (event: MessageEvent<WorkerMessage>) => {
  const { id, type, data } = event.data;

  try {
    let result: any;

    switch (type) {
      case 'parse':
        result = await epubParser.parseEpub(data.file, data.options || {
          validateStructure: true,
          extractResources: true,
          generateAST: true,
          optimizeContent: false,
          preserveWhitespace: false
        });
        break;

      case 'validate':
        // 验证EPUB文件
        result = await epubParser.parseEpub(data.file, {
          validateStructure: true,
          extractResources: false,
          generateAST: false,
          optimizeContent: false,
          preserveWhitespace: false
        });
        break;

      case 'extract':
        // 仅提取资源
        result = await epubParser.parseEpub(data.file, {
          validateStructure: false,
          extractResources: true,
          generateAST: false,
          optimizeContent: false,
          preserveWhitespace: false
        });
        break;

      case 'optimize':
        // 优化内容
        result = await epubParser.parseEpub(data.file, {
          validateStructure: false,
          extractResources: false,
          generateAST: true,
          optimizeContent: true,
          preserveWhitespace: false
        });
        break;

      default:
        throw new Error(`Unknown worker task type: ${type}`);
    }

    // 发送成功响应
    const response: WorkerResponse = {
      id,
      type: 'success',
      data: result
    };
    self.postMessage(response);

  } catch (error) {
    // 发送错误响应
    const response: WorkerResponse = {
      id,
      type: 'error',
      data: null,
      error: error.message
    };
    self.postMessage(response);
  }
});

// 导出类型（用于TypeScript类型检查）
export type { WorkerMessage, WorkerResponse, EpubStructure, ASTNode, ParseOptions };