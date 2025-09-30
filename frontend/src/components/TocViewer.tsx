import React, { useState, useEffect } from 'react';
import { Tree, Typography, Spin, Alert, Empty } from 'antd';
import { BookOutlined, FileTextOutlined } from '@ant-design/icons';
import type { TreeDataNode } from 'antd';

const { Title } = Typography;

interface TocViewerProps {
  fileName: string;
  content: string;
  isDarkMode?: boolean;
  onChapterSelect?: (chapterPath: string) => void;
}

interface TocItem {
  id: string;
  text: string;
  src: string;
  playOrder?: number;
  children?: TocItem[];
}

const TocViewer: React.FC<TocViewerProps> = ({
  fileName,
  content,
  isDarkMode = false,
  onChapterSelect
}) => {
  const [tocData, setTocData] = useState<TreeDataNode[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // 解析TOC.ncx文件
  const parseTocNcx = (xmlContent: string): TocItem[] => {
    try {
      const parser = new DOMParser();
      const xmlDoc = parser.parseFromString(xmlContent, 'text/xml');
      
      // 检查解析错误
      const parseError = xmlDoc.querySelector('parsererror');
      if (parseError) {
        throw new Error('XML解析错误');
      }

      const navPoints = xmlDoc.querySelectorAll('navMap > navPoint');
      const tocItems: TocItem[] = [];

      const parseNavPoint = (navPoint: Element): TocItem => {
        const id = navPoint.getAttribute('id') || '';
        const playOrder = navPoint.getAttribute('playOrder');
        
        const navLabel = navPoint.querySelector('navLabel > text');
        const text = navLabel?.textContent?.trim() || '未命名章节';
        
        const content = navPoint.querySelector('content');
        const src = content?.getAttribute('src') || '';
        
        const item: TocItem = {
          id,
          text,
          src,
          playOrder: playOrder ? parseInt(playOrder) : undefined
        };

        // 递归处理子章节
        const childNavPoints = navPoint.querySelectorAll(':scope > navPoint');
        if (childNavPoints.length > 0) {
          item.children = Array.from(childNavPoints).map(parseNavPoint);
        }

        return item;
      };

      Array.from(navPoints).forEach(navPoint => {
        tocItems.push(parseNavPoint(navPoint));
      });

      return tocItems;
    } catch (error) {
      console.error('解析TOC失败:', error);
      throw error;
    }
  };

  // 将TOC数据转换为Antd Tree组件需要的格式
  const convertToTreeData = (tocItems: TocItem[]): TreeDataNode[] => {
    return tocItems.map((item, index) => {
      const treeNode: TreeDataNode = {
        key: item.id || `item-${index}`,
        title: (
          <span 
            className={`cursor-pointer hover:text-blue-500 ${isDarkMode ? 'text-gray-200' : 'text-gray-800'}`}
            onClick={() => handleChapterClick(item.src)}
          >
            <FileTextOutlined className="mr-2" />
            {item.text}
          </span>
        ),
        icon: <FileTextOutlined />,
        children: item.children ? convertToTreeData(item.children) : undefined
      };
      return treeNode;
    });
  };

  // 处理章节点击
  const handleChapterClick = (src: string) => {
    if (src && onChapterSelect) {
      // 处理相对路径
      let chapterPath = src;
      if (src.includes('#')) {
        chapterPath = src.split('#')[0]; // 移除锚点
      }
      onChapterSelect(chapterPath);
    }
  };

  // 解析TOC内容
  useEffect(() => {
    if (!content || !fileName.toLowerCase().includes('toc')) {
      setTocData([]);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const tocItems = parseTocNcx(content);
      const treeData = convertToTreeData(tocItems);
      setTocData(treeData);
    } catch (err) {
      setError('无法解析TOC文件');
      console.error('TOC解析错误:', err);
    } finally {
      setLoading(false);
    }
  }, [content, fileName, isDarkMode]);

  if (!fileName.toLowerCase().includes('toc')) {
    return (
      <div className={`h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'} flex items-center justify-center`}>
        <Empty 
          image={<BookOutlined className={`text-4xl ${isDarkMode ? 'text-gray-500' : 'text-gray-300'}`} />}
          description={<span style={isDarkMode ? {color: '#a3a3a3'} : {}}>请选择TOC文件查看目录</span>}
        />
      </div>
    );
  }

  if (loading) {
    return (
      <div className={`h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'} flex items-center justify-center`}>
        <Spin size="large" />
      </div>
    );
  }

  if (error) {
    return (
      <div className={`h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'} p-4`}>
        <Alert
          message="解析错误"
          description={error}
          type="error"
          showIcon
        />
      </div>
    );
  }

  return (
    <div className={`h-full ${isDarkMode ? 'bg-gray-800' : 'bg-white'}`}>
      <div className={`p-3 border-b ${isDarkMode ? 'border-gray-700 bg-gray-900' : 'border-gray-200 bg-gray-50'}`}>
        <Title level={5} className={`mb-0 ${isDarkMode ? 'text-gray-200' : 'text-gray-700'}`}>
          <BookOutlined className="mr-2" />
          目录: {fileName}
        </Title>
      </div>
      
      <div className="flex-1 overflow-auto p-4">
        {tocData.length > 0 ? (
          <Tree
            treeData={tocData}
            defaultExpandAll
            showIcon
            className={isDarkMode ? 'dark-tree' : ''}
            style={{
              background: 'transparent',
              color: isDarkMode ? '#e5e5e5' : '#333'
            }}
          />
        ) : (
          <Empty 
            image={<BookOutlined className={`text-4xl ${isDarkMode ? 'text-gray-500' : 'text-gray-300'}`} />}
            description={<span style={isDarkMode ? {color: '#a3a3a3'} : {}}>TOC文件为空或格式不正确</span>}
          />
        )}
      </div>
      
      <style>{`
        .dark-tree .ant-tree-node-content-wrapper {
          color: #e5e5e5 !important;
        }
        .dark-tree .ant-tree-node-content-wrapper:hover {
          background-color: #374151 !important;
        }
        .dark-tree .ant-tree-node-selected .ant-tree-node-content-wrapper {
          background-color: #1f2937 !important;
        }
        .dark-tree .ant-tree-switcher {
          color: #9ca3af !important;
        }
      `}</style>
    </div>
  );
};

export default TocViewer;