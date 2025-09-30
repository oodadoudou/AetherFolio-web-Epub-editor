/**
 * EPUB结构解析工具
 * 用于解析EPUB文件结构，提供章节排序和目录导航功能
 */

export interface EpubChapter {
  id: string;
  title: string;
  href: string;
  order: number;
  level: number;
  parent?: string;
  children?: EpubChapter[];
}

export interface EpubManifest {
  id: string;
  href: string;
  mediaType: string;
}

export interface EpubSpineItem {
  idref: string;
  linear?: boolean;
}

export interface EpubMetadata {
  title: string;
  creator: string;
  language: string;
  identifier: string;
  date: string;
}

export interface EpubStructure {
  chapters: EpubChapter[];
  manifest: EpubManifest[];
  spine: EpubSpineItem[];
  tocPath?: string;
  opfPath?: string;
  metadata?: EpubMetadata;
  resources?: EpubManifest[];
  toc?: EpubChapter[];
}

/**
 * 解析OPF文件获取EPUB结构
 */
export function parseOpfContent(opfContent: string): Partial<EpubStructure> {
  try {
    const parser = new DOMParser();
    const opfDoc = parser.parseFromString(opfContent, 'text/xml');
    
    // 检查解析错误
    const parseError = opfDoc.querySelector('parsererror');
    if (parseError) {
      throw new Error('OPF文件解析错误');
    }

    // 解析manifest
    const manifestItems = opfDoc.querySelectorAll('manifest item');
    const manifest: EpubManifest[] = Array.from(manifestItems).map(item => ({
      id: item.getAttribute('id') || '',
      href: item.getAttribute('href') || '',
      mediaType: item.getAttribute('media-type') || ''
    }));

    // 解析spine
    const spineItems = opfDoc.querySelectorAll('spine itemref');
    const spine: EpubSpineItem[] = Array.from(spineItems).map(item => ({
      idref: item.getAttribute('idref') || '',
      linear: item.getAttribute('linear') !== 'no'
    }));

    // 查找TOC文件
    const tocItem = Array.from(manifestItems).find(item => 
      item.getAttribute('properties')?.includes('nav') ||
      item.getAttribute('media-type') === 'application/x-dtbncx+xml'
    );
    const tocPath = tocItem?.getAttribute('href');

    return {
      manifest,
      spine,
      tocPath
    };
  } catch (error) {
    console.error('解析OPF文件失败:', error);
    return {};
  }
}

/**
 * 解析NCX文件获取章节结构
 */
export function parseNcxContent(ncxContent: string): EpubChapter[] {
  try {
    const parser = new DOMParser();
    const ncxDoc = parser.parseFromString(ncxContent, 'text/xml');
    
    const parseError = ncxDoc.querySelector('parsererror');
    if (parseError) {
      throw new Error('NCX文件解析错误');
    }

    const navPoints = ncxDoc.querySelectorAll('navMap > navPoint');
    const chapters: EpubChapter[] = [];

    const parseNavPoint = (navPoint: Element, level: number = 1, parentId?: string): EpubChapter => {
      const id = navPoint.getAttribute('id') || `chapter-${Date.now()}-${Math.random()}`;
      const playOrder = navPoint.getAttribute('playOrder');
      
      const navLabel = navPoint.querySelector('navLabel > text');
      const title = navLabel?.textContent?.trim() || '未命名章节';
      
      const content = navPoint.querySelector('content');
      const href = content?.getAttribute('src') || '';
      
      const chapter: EpubChapter = {
        id,
        title,
        href,
        order: playOrder ? parseInt(playOrder) : chapters.length + 1,
        level,
        parent: parentId
      };

      // 递归处理子章节
      const childNavPoints = navPoint.querySelectorAll(':scope > navPoint');
      if (childNavPoints.length > 0) {
        chapter.children = Array.from(childNavPoints).map(child => 
          parseNavPoint(child, level + 1, id)
        );
      }

      return chapter;
    };

    Array.from(navPoints).forEach(navPoint => {
      chapters.push(parseNavPoint(navPoint));
    });

    return chapters;
  } catch (error) {
    console.error('解析NCX文件失败:', error);
    return [];
  }
}

/**
 * 解析HTML导航文件获取章节结构（EPUB3）
 */
export function parseHtmlNavContent(htmlContent: string): EpubChapter[] {
  try {
    const parser = new DOMParser();
    const htmlDoc = parser.parseFromString(htmlContent, 'text/html');
    
    // 查找导航元素
    const navElement = htmlDoc.querySelector('nav[epub\\:type="toc"], nav[role="doc-toc"]') ||
                      htmlDoc.querySelector('nav');
    
    if (!navElement) {
      return [];
    }

    const chapters: EpubChapter[] = [];
    let orderCounter = 1;

    const parseNavList = (list: Element, level: number = 1, parentId?: string): EpubChapter[] => {
      const items = list.querySelectorAll(':scope > li');
      const result: EpubChapter[] = [];

      Array.from(items).forEach(item => {
        const link = item.querySelector('a');
        if (!link) return;

        const href = link.getAttribute('href') || '';
        const title = link.textContent?.trim() || '未命名章节';
        const id = `chapter-${orderCounter++}`;

        const chapter: EpubChapter = {
          id,
          title,
          href,
          order: orderCounter - 1,
          level,
          parent: parentId
        };

        // 查找嵌套列表
        const nestedList = item.querySelector('ol, ul');
        if (nestedList) {
          chapter.children = parseNavList(nestedList, level + 1, id);
        }

        result.push(chapter);
      });

      return result;
    };

    const tocList = navElement.querySelector('ol, ul');
    if (tocList) {
      chapters.push(...parseNavList(tocList));
    }

    return chapters;
  } catch (error) {
    console.error('解析HTML导航文件失败:', error);
    return [];
  }
}

/**
 * 根据spine顺序重新排序章节
 */
export function reorderChaptersBySpine(
  chapters: EpubChapter[], 
  spine: EpubSpineItem[], 
  manifest: EpubManifest[]
): EpubChapter[] {
  // 创建manifest映射
  const manifestMap = new Map(manifest.map(item => [item.id, item]));
  
  // 创建章节映射
  const chapterMap = new Map<string, EpubChapter>();
  const flattenChapters = (chaps: EpubChapter[]) => {
    chaps.forEach(chapter => {
      // 移除锚点，只保留文件路径
      const filePath = chapter.href.split('#')[0];
      chapterMap.set(filePath, chapter);
      if (chapter.children) {
        flattenChapters(chapter.children);
      }
    });
  };
  flattenChapters(chapters);

  // 按spine顺序重新排序
  const orderedChapters: EpubChapter[] = [];
  
  spine.forEach((spineItem, index) => {
    const manifestItem = manifestMap.get(spineItem.idref);
    if (manifestItem && manifestItem.mediaType.includes('html')) {
      const chapter = chapterMap.get(manifestItem.href);
      if (chapter) {
        orderedChapters.push({
          ...chapter,
          order: index + 1
        });
      }
    }
  });

  return orderedChapters;
}

/**
 * 扁平化章节结构为文件列表
 */
export function flattenChapters(chapters: EpubChapter[]): EpubChapter[] {
  const result: EpubChapter[] = [];
  
  const flatten = (chaps: EpubChapter[]) => {
    chaps.forEach(chapter => {
      result.push(chapter);
      if (chapter.children) {
        flatten(chapter.children);
      }
    });
  };
  
  flatten(chapters);
  return result;
}

/**
 * 构建章节树形结构
 */
export function buildChapterTree(chapters: EpubChapter[]): EpubChapter[] {
  const chapterMap = new Map(chapters.map(ch => [ch.id, { ...ch, children: [] }]));
  const rootChapters: EpubChapter[] = [];

  chapters.forEach(chapter => {
    const chapterNode = chapterMap.get(chapter.id);
    if (!chapterNode) return;

    if (chapter.parent) {
      const parent = chapterMap.get(chapter.parent);
      if (parent) {
        if (!parent.children) parent.children = [];
        parent.children.push(chapterNode);
      } else {
        rootChapters.push(chapterNode);
      }
    } else {
      rootChapters.push(chapterNode);
    }
  });

  return rootChapters;
}

/**
 * 获取章节的完整路径
 */
export function getChapterPath(chapter: EpubChapter, chapters: EpubChapter[]): string[] {
  const path: string[] = [chapter.title];
  let current = chapter;
  
  while (current.parent) {
    const parent = chapters.find(ch => ch.id === current.parent);
    if (parent) {
      path.unshift(parent.title);
      current = parent;
    } else {
      break;
    }
  }
  
  return path;
}

/**
 * 查找下一个/上一个章节
 */
export function findAdjacentChapter(
  currentChapter: EpubChapter, 
  chapters: EpubChapter[], 
  direction: 'next' | 'prev'
): EpubChapter | null {
  const flatChapters = flattenChapters(chapters).sort((a, b) => a.order - b.order);
  const currentIndex = flatChapters.findIndex(ch => ch.id === currentChapter.id);
  
  if (currentIndex === -1) return null;
  
  const targetIndex = direction === 'next' ? currentIndex + 1 : currentIndex - 1;
  return flatChapters[targetIndex] || null;
}

/**
 * 文件节点接口
 */
interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

/**
 * 创建基本的EPUB结构（当找不到OPF文件时）
 */
function createBasicEpubStructure(fileTree: FileNode[]): EpubStructure {
  const chapters: EpubChapter[] = [];
  let chapterOrder = 1;
  
  const processFiles = (nodes: FileNode[]) => {
    nodes.forEach(node => {
      if (node.type === 'file') {
        const fileName = node.name.toLowerCase();
        // 识别可能的章节文件
        if (fileName.endsWith('.html') || fileName.endsWith('.xhtml') || fileName.endsWith('.htm')) {
          chapters.push({
            id: `chapter_${chapterOrder}`,
            title: node.name.replace(/\.(html|xhtml|htm)$/i, ''),
            href: node.path,
            order: chapterOrder++,
            level: 1,
            parent: null
          });
        }
      } else if (node.children) {
        processFiles(node.children);
      }
    });
  };
  
  processFiles(fileTree);
  
  // 如果没有找到HTML文件，创建一个默认章节
  if (chapters.length === 0) {
    chapters.push({
      id: 'default_chapter',
      title: '默认章节',
      href: 'chapter1.html',
      order: 1,
      level: 1,
      parent: null
    });
  }
  
  return {
    metadata: {
      title: '未知标题',
      creator: '未知作者',
      language: 'zh-CN',
      identifier: 'unknown-epub',
      date: new Date().toISOString().split('T')[0]
    },
    chapters: chapters,
    manifest: [],
    resources: [],
    spine: chapters.map(ch => ({ idref: ch.id, linear: true })),
    toc: chapters
  };
}

/**
 * 解析EPUB结构
 */
export async function parseEpubStructure(
  fileTree: FileNode[],
  sessionId: string
): Promise<EpubStructure | null> {
  try {
    console.log('开始解析EPUB结构，文件树:', fileTree);
    
    // 查找OPF文件 - 增强查找逻辑
    let opfFile = findFileInTree(fileTree, (file) => file.name.endsWith('.opf'));
    console.log('按.opf后缀查找结果:', opfFile);
    
    // 如果没找到，尝试查找content.opf或package.opf等常见名称
    if (!opfFile) {
      const commonOpfNames = ['content.opf', 'package.opf', 'book.opf', 'main.opf', 'metadata.opf', 'toc.opf', 'spine.opf'];
      console.log('尝试常见OPF文件名:', commonOpfNames);
      for (const name of commonOpfNames) {
        opfFile = findFileInTree(fileTree, (file) => file.name.toLowerCase() === name.toLowerCase());
        if (opfFile) {
          console.log('找到常见名称OPF文件:', name, opfFile);
          break;
        }
      }
    }
    
    // 如果还是没找到，尝试在常见目录中查找
    if (!opfFile) {
      const commonDirs = ['OEBPS', 'META-INF', 'EPUB', 'content', 'src', 'text', 'OPS', 'book'];
      console.log('在常见目录中查找OPF文件:', commonDirs);
      for (const dir of commonDirs) {
        opfFile = findFileInTree(fileTree, (file) => {
          const pathLower = file.path.toLowerCase();
          const dirLower = dir.toLowerCase();
          return (pathLower.includes(`/${dirLower}/`) || pathLower.includes(`\\${dirLower}\\`) || 
                  pathLower.startsWith(`${dirLower}/`) || pathLower.startsWith(`${dirLower}\\`)) && 
                 file.name.toLowerCase().endsWith('.opf');
        });
        if (opfFile) {
          console.log('在目录', dir, '中找到OPF文件:', opfFile);
          break;
        }
      }
    }
    
    // 尝试查找任何包含'opf'的文件
    if (!opfFile) {
      console.log('尝试查找任何包含opf的文件');
      opfFile = findFileInTree(fileTree, (file) => {
        const nameLower = file.name.toLowerCase();
        const pathLower = file.path.toLowerCase();
        return nameLower.includes('opf') || pathLower.includes('.opf') || 
               nameLower.includes('package') || nameLower.includes('content');
      });
      if (opfFile) {
        console.log('找到包含opf的文件:', opfFile);
      }
    }
    
    // 最后尝试查找XML文件作为备选
    if (!opfFile) {
      console.log('尝试查找XML文件作为OPF备选');
      const xmlFiles = [];
      const collectXmlFiles = (nodes: FileNode[]) => {
        nodes.forEach(node => {
          if (node.type === 'file' && node.name.toLowerCase().endsWith('.xml')) {
            xmlFiles.push(node);
          }
          if (node.children) {
            collectXmlFiles(node.children);
          }
        });
      };
      collectXmlFiles(fileTree);
      
      // 优先选择可能是OPF的XML文件
      opfFile = xmlFiles.find(file => {
        const nameLower = file.name.toLowerCase();
        return nameLower.includes('content') || nameLower.includes('package') || 
               nameLower.includes('book') || nameLower.includes('metadata');
      }) || xmlFiles[0]; // 如果没有匹配的，选择第一个XML文件
      
      if (opfFile) {
        console.log('使用XML文件作为OPF备选:', opfFile);
      }
    }
    
    if (!opfFile) {
      console.warn('未找到OPF文件，将尝试创建基本结构');
      console.log('完整文件树结构:');
      const logFileTree = (nodes: FileNode[], indent = '') => {
        nodes.forEach(node => {
          console.log(`${indent}${node.type === 'directory' ? '📁' : '📄'} ${node.name} (${node.path})`);
          if (node.children) {
            logFileTree(node.children, indent + '  ');
          }
        });
      };
      logFileTree(fileTree);
      
      // 尝试创建基本的EPUB结构而不是返回null
      return createBasicEpubStructure(fileTree);
    }
    
    console.log('成功找到OPF文件:', opfFile.path);

    // 获取OPF文件内容
    const opfResponse = await fetch(`/api/sessions/${sessionId}/files/content?path=${encodeURIComponent(opfFile.path)}`);
    if (!opfResponse.ok) {
      throw new Error('获取OPF文件失败');
    }
    const opfContent = await opfResponse.text();

    // 解析OPF内容
    const opfStructure = parseOpfContent(opfContent);
    if (!opfStructure.manifest || !opfStructure.spine) {
      throw new Error('OPF文件解析失败');
    }

    let chapters: EpubChapter[] = [];

    // 查找TOC文件
    if (opfStructure.tocPath) {
      const tocFile = findFileInTree(fileTree, (file) => 
        file.path.endsWith(opfStructure.tocPath!) || file.name === opfStructure.tocPath
      );
      
      if (tocFile) {
        try {
          const tocResponse = await fetch(`/api/sessions/${sessionId}/files/content?path=${encodeURIComponent(tocFile.path)}`);
          if (tocResponse.ok) {
            const tocContent = await tocResponse.text();
            
            if (tocFile.name.endsWith('.ncx')) {
              chapters = parseNcxContent(tocContent);
            } else if (tocFile.name.endsWith('.html') || tocFile.name.endsWith('.xhtml')) {
              chapters = parseHtmlNavContent(tocContent);
            }
          }
        } catch (error) {
          console.warn('解析TOC文件失败:', error);
        }
      }
    }

    // 如果没有找到TOC文件或解析失败，从spine生成基本章节结构
    if (chapters.length === 0 && opfStructure.spine && opfStructure.manifest) {
      chapters = generateChaptersFromSpine(opfStructure.spine, opfStructure.manifest);
    }

    // 根据spine顺序重新排序章节
    if (chapters.length > 0 && opfStructure.spine && opfStructure.manifest) {
      chapters = reorderChaptersBySpine(chapters, opfStructure.spine, opfStructure.manifest);
    }

    return {
      chapters,
      manifest: opfStructure.manifest,
      spine: opfStructure.spine,
      tocPath: opfStructure.tocPath,
      opfPath: opfFile.path
    };
  } catch (error) {
    console.error('解析EPUB结构失败:', error);
    return null;
  }
}

/**
 * 在文件树中查找文件
 */
function findFileInTree(
  nodes: FileNode[],
  predicate: (file: FileNode) => boolean
): FileNode | null {
  for (const node of nodes) {
    if (node.type === 'file' && predicate(node)) {
      return node;
    }
    if (node.children) {
      const found = findFileInTree(node.children, predicate);
      if (found) return found;
    }
  }
  return null;
}

/**
 * 从spine生成基本章节结构
 */
function generateChaptersFromSpine(
  spine: EpubSpineItem[],
  manifest: EpubManifest[]
): EpubChapter[] {
  const manifestMap = new Map(manifest.map(item => [item.id, item]));
  const chapters: EpubChapter[] = [];

  spine.forEach((spineItem, index) => {
    const manifestItem = manifestMap.get(spineItem.idref);
    if (manifestItem && manifestItem.mediaType.includes('html')) {
      const fileName = manifestItem.href.split('/').pop() || manifestItem.href;
      const title = fileName.replace(/\.(x?html?)$/i, '').replace(/[_-]/g, ' ');
      
      chapters.push({
        id: `chapter-${index + 1}`,
        title: title || `第${index + 1}章`,
        href: manifestItem.href,
        order: index + 1,
        level: 1
      });
    }
  });

  return chapters;
}