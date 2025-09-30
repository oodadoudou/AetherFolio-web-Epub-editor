import React, { useRef, useEffect, useState, useCallback, useMemo } from 'react';
import { EditorView } from '@codemirror/view';
import { basicSetup } from 'codemirror';
import { EditorState, Extension } from '@codemirror/state';
import { html } from '@codemirror/lang-html';
import { css } from '@codemirror/lang-css';
import { javascript } from '@codemirror/lang-javascript';
import { xml } from '@codemirror/lang-xml';
import { json } from '@codemirror/lang-json';
import { oneDark } from '@codemirror/theme-one-dark';
import { search, searchKeymap } from '@codemirror/search';
import { autocompletion } from '@codemirror/autocomplete';
import { linter, lintKeymap } from '@codemirror/lint';
import { keymap } from '@codemirror/view';
import { defaultKeymap, historyKeymap } from '@codemirror/commands';
import { Button, Input, Tooltip, Dropdown, MenuProps, Badge, Alert } from 'antd';
import { 
  SearchOutlined, 
  CloseOutlined, 
  ArrowUpOutlined, 
  ArrowDownOutlined,
  SwapOutlined,
  SettingOutlined,
  BookOutlined,
  SyncOutlined
} from '@ant-design/icons';
import { SyncManager } from '../utils/syncManager';
import { enhancedSyncManager } from '../utils/enhancedSyncManager';
import { globalTocManager, TocStructure } from '../utils/globalTocManager';
import { EpubChapter } from '../utils/epubStructure';
import { isImageFile } from '../utils/file';
// ImagePreview has been removed as part of cleanup

interface CodeMirrorEditorProps {
  content: string;
  language: string;
  onChange: (value: string) => void;
  onSave?: () => Promise<void>;
  onCursorPositionChange?: (line: number, column: number) => void;
  onScrollChange?: (scrollTop: number, scrollPercentage: number) => void;
  isDarkMode?: boolean;
  selectedLine?: number;
  searchQuery?: string;
  onSearchResultsChange?: (results: number) => void;
  showSearchReplace?: boolean;
  onSearchReplaceToggle?: (show: boolean) => void;
  currentChapter?: EpubChapter;
  onChapterNavigation?: (direction: 'prev' | 'next') => void;
  enableSync?: boolean;
  onSyncToggle?: (enabled: boolean) => void;
  previewIframe?: HTMLIFrameElement | null;
  fileName?: string;
  onTocUpdate?: (tocStructure: TocStructure) => void;
  sessionId?: string;
  filePath?: string;
}

interface SearchState {
  query: string;
  replaceText: string;
  caseSensitive: boolean;
  wholeWord: boolean;
  useRegex: boolean;
  currentMatch: number;
  totalMatches: number;
}

interface EditorSettings {
  fontSize: number;
  tabSize: number;
  wordWrap: boolean;
  lineNumbers: boolean;
  folding: boolean;
  autoIndent: boolean;
}

const CodeMirrorEditor = React.forwardRef<any, CodeMirrorEditorProps>((
  {
    content,
    language,
    onChange,
    onCursorPositionChange,
    onScrollChange,
    isDarkMode = false,
    selectedLine,
    searchQuery,
    onSearchResultsChange,
    showSearchReplace = false,
    onSearchReplaceToggle,
    currentChapter,
    onChapterNavigation,
    enableSync = true,
    onSyncToggle,
    previewIframe,
    fileName,
    onTocUpdate,
    sessionId,
    filePath
  },
  ref
) => {
  const editorRef = useRef<HTMLDivElement>(null);
  const viewRef = useRef<EditorView | null>(null);
  const syncManagerRef = useRef<SyncManager | null>(null);
  const [isTocFile, setIsTocFile] = useState(false);
  const [tocStructure, setTocStructure] = useState<TocStructure | null>(null);
  
  const [searchState, setSearchState] = useState<SearchState>({
    query: searchQuery || '',
    replaceText: '',
    caseSensitive: false,
    wholeWord: false,
    useRegex: false,
    currentMatch: 0,
    totalMatches: 0
  });
  
  const [settings, setSettings] = useState<EditorSettings>({
    fontSize: 14,
    tabSize: 2,
    wordWrap: true,
    lineNumbers: true,
    folding: true,
    autoIndent: true
  });

  const [isSearching, setIsSearching] = useState(false);
  const [error, setError] = useState<string | null>(null);
  
  // 检测是否为图片文件
  const isImageFileType = useMemo(() => {
    return fileName ? isImageFile(fileName) : false;
  }, [fileName]);
  
  // 获取语言扩展
  const getLanguageExtension = useCallback((lang: string): Extension => {
    switch (lang.toLowerCase()) {
      case 'html':
      case 'xhtml':
        return html();
      case 'css':
        return css();
      case 'javascript':
      case 'js':
        return javascript();
      case 'xml':
      case 'opf':
      case 'ncx':
        return xml();
      case 'json':
        return json();
      default:
        return [];
    }
  }, []);
  
  // 创建编辑器扩展
  const extensions = useMemo(() => {
    const exts: Extension[] = [
      basicSetup,
      getLanguageExtension(language),
      search(),
      autocompletion(),
      keymap.of([
        ...defaultKeymap,
        ...historyKeymap,
        ...searchKeymap,
        ...lintKeymap
      ]),
      EditorView.updateListener.of((update) => {
        if (update.docChanged) {
          onChange(update.state.doc.toString());
        }
        if (update.selectionSet) {
          const pos = update.state.selection.main.head;
          const line = update.state.doc.lineAt(pos);
          onCursorPositionChange?.(line.number, pos - line.from + 1);
        }
      }),
      EditorView.theme({
        '&': {
          fontSize: `${settings.fontSize}px`,
          height: '100%'
        },
        '.cm-content': {
          padding: '10px',
          minHeight: '100%',
          fontFamily: 'SF Mono, Monaco, Cascadia Code, Roboto Mono, Consolas, Liberation Mono, Menlo, Courier, monospace'
        },
        '.cm-focused': {
          outline: 'none'
        },
        '.cm-editor': {
          height: '100%'
        },
        '.cm-scroller': {
          fontFamily: 'inherit'
        }
      })
    ];
    
    if (isDarkMode) {
      exts.push(oneDark);
    }
    
    return exts;
  }, [language, isDarkMode, settings.fontSize, onChange, onCursorPositionChange, getLanguageExtension]);
  
  // 初始化编辑器
  useEffect(() => {
    if (!editorRef.current) return;
    
    const state = EditorState.create({
      doc: content,
      extensions
    });
    
    const view = new EditorView({
      state,
      parent: editorRef.current
    });
    
    viewRef.current = view;
    
    // 暴露给父组件
    if (ref) {
      if (typeof ref === 'function') {
        ref({ view, scrollToLine: (line: number) => scrollToLine(line) });
      } else {
        ref.current = { view, scrollToLine: (line: number) => scrollToLine(line) };
      }
    }
    
    return () => {
      view.destroy();
    };
  }, [extensions, ref]);
  
  // 更新内容
  useEffect(() => {
    if (viewRef.current && viewRef.current.state.doc.toString() !== content) {
      const transaction = viewRef.current.state.update({
        changes: {
          from: 0,
          to: viewRef.current.state.doc.length,
          insert: content
        }
      });
      viewRef.current.dispatch(transaction);
    }
  }, [content]);
  
  // 滚动到指定行
  const scrollToLine = useCallback((line: number) => {
    if (!viewRef.current) return;
    
    try {
      const lineInfo = viewRef.current.state.doc.line(line);
      viewRef.current.dispatch({
        selection: { anchor: lineInfo.from },
        scrollIntoView: true
      });
    } catch (error) {
      console.warn('滚动到行失败:', error);
    }
  }, []);
  
  // 初始化同步管理器
  useEffect(() => {
    syncManagerRef.current = new SyncManager();
    
    // 初始化增强同步管理器
    if (enableSync && viewRef.current && previewIframe) {
      enhancedSyncManager.initialize(viewRef.current, previewIframe);
    }
    
    return () => {
      syncManagerRef.current?.cleanup();
      enhancedSyncManager.cleanup();
    };
  }, [enableSync, previewIframe]);
  
  // 检测TOC文件
  useEffect(() => {
    const isToc = fileName && (fileName.endsWith('.ncx') || fileName.includes('toc') || fileName.includes('nav'));
    setIsTocFile(!!isToc);
    
    if (isToc && content) {
      try {
        const structure = globalTocManager.parseContent(content, fileName);
        setTocStructure(structure);
        if (onTocUpdate) {
          onTocUpdate(structure);
        }
      } catch (error) {
        console.warn('TOC解析失败:', error);
        setTocStructure(null);
      }
    }
  }, [fileName, content, onTocUpdate]);
  
  // 监听TOC变更
  useEffect(() => {
    const handleTocChange = (structure: TocStructure) => {
      setTocStructure(structure);
      if (onTocUpdate) {
        onTocUpdate(structure);
      }
      
      // 如果是TOC文件，更新编辑器内容
      // TOC文件内容更新处理
      if (isTocFile) {
        console.log('TOC file detected, content updated');
      }
    };
    
    const removeListener = globalTocManager.addTocChangeListener(handleTocChange);
    
    return removeListener;
  }, [isTocFile, content, onTocUpdate]);
  
  // 处理搜索
  const handleSearch = useCallback((query: string) => {
    if (!viewRef.current || !query) return;
    
    setIsSearching(true);
    // CodeMirror 6的搜索功能会自动处理
    setIsSearching(false);
  }, []);
  
  // 设置菜单项
  const settingsMenuItems: MenuProps['items'] = [
    {
      key: 'fontSize',
      label: (
        <div className="flex items-center justify-between w-48">
          <span>字体大小</span>
          <div className="flex items-center gap-1">
            <Button size="small" onClick={() => setSettings(prev => ({ ...prev, fontSize: Math.max(10, prev.fontSize - 1) }))}>
              -
            </Button>
            <span className="w-8 text-center">{settings.fontSize}</span>
            <Button size="small" onClick={() => setSettings(prev => ({ ...prev, fontSize: Math.min(24, prev.fontSize + 1) }))}>
              +
            </Button>
          </div>
        </div>
      )
    },
    {
      key: 'tabSize',
      label: (
        <div className="flex items-center justify-between w-48">
          <span>缩进大小</span>
          <div className="flex items-center gap-1">
            <Button size="small" onClick={() => setSettings(prev => ({ ...prev, tabSize: Math.max(1, prev.tabSize - 1) }))}>
              -
            </Button>
            <span className="w-8 text-center">{settings.tabSize}</span>
            <Button size="small" onClick={() => setSettings(prev => ({ ...prev, tabSize: Math.min(8, prev.tabSize + 1) }))}>
              +
            </Button>
          </div>
        </div>
      )
    }
  ];
  
  // 如果是图片文件，显示图片预览
  if (isImageFileType) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className={`text-center p-8 ${isDarkMode ? 'text-neutral-400' : 'text-gray-600'}`}>
          <div className="text-4xl mb-4">🖼️</div>
          <p>图片预览功能已移除</p>
          <p className="text-sm mt-2">{fileName}</p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="h-full flex flex-col">
      {/* 工具栏 */}
      <div className={`flex items-center justify-between p-2 border-b ${
        isDarkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-gray-50 border-gray-200'
      }`}>
        <div className="flex items-center gap-2">
          {/* 搜索按钮 */}
          <Tooltip title="搜索">
            <Button
              icon={<SearchOutlined />}
              size="small"
              type={showSearchReplace ? 'primary' : 'default'}
              onClick={() => onSearchReplaceToggle?.(!showSearchReplace)}
            />
          </Tooltip>
          
          {/* 章节导航 */}
          {currentChapter && (
            <>
              <Tooltip title="上一章">
                <Button
                  icon={<ArrowUpOutlined />}
                  size="small"
                  onClick={() => onChapterNavigation?.('prev')}
                />
              </Tooltip>
              <Tooltip title="下一章">
                <Button
                  icon={<ArrowDownOutlined />}
                  size="small"
                  onClick={() => onChapterNavigation?.('next')}
                />
              </Tooltip>
              <span className={`text-sm ${
                isDarkMode ? 'text-neutral-400' : 'text-gray-600'
              }`}>
                {currentChapter.title}
              </span>
            </>
          )}
          
          {/* TOC文件标识 */}
          {isTocFile && (
            <Badge count="TOC" size="small">
              <BookOutlined className={isDarkMode ? 'text-neutral-400' : 'text-gray-600'} />
            </Badge>
          )}
        </div>
        
        <div className="flex items-center gap-2">
          {/* 同步开关 */}
          <Tooltip title={enableSync ? '禁用同步' : '启用同步'}>
            <Button
              icon={<SyncOutlined />}
              size="small"
              type={enableSync ? 'primary' : 'default'}
              onClick={() => onSyncToggle?.(!enableSync)}
            />
          </Tooltip>
          
          {/* 设置 */}
          <Dropdown menu={{ items: settingsMenuItems }} trigger={['click']}>
            <Button icon={<SettingOutlined />} size="small" />
          </Dropdown>
        </div>
      </div>
      
      {/* 搜索替换面板 */}
      {showSearchReplace && (
        <div className={`p-3 border-b ${
          isDarkMode ? 'bg-neutral-800 border-neutral-700' : 'bg-gray-50 border-gray-200'
        }`}>
          <div className="flex items-center gap-2 mb-2">
            <Input
              placeholder="搜索..."
              value={searchState.query}
              onChange={(e) => {
                const newQuery = e.target.value;
                setSearchState(prev => ({ ...prev, query: newQuery }));
                handleSearch(newQuery);
              }}
              onPressEnter={() => handleSearch(searchState.query)}
              className="flex-1"
            />
            <Button
              icon={<ArrowUpOutlined />}
              size="small"
              title="上一个"
            />
            <Button
              icon={<ArrowDownOutlined />}
              size="small"
              title="下一个"
            />
            <Button
              icon={<CloseOutlined />}
              size="small"
              onClick={() => onSearchReplaceToggle?.(false)}
            />
          </div>
          
          <div className="flex items-center gap-2">
            <Input
              placeholder="替换为..."
              value={searchState.replaceText}
              onChange={(e) => setSearchState(prev => ({ ...prev, replaceText: e.target.value }))}
              className="flex-1"
            />
            <Button size="small">替换</Button>
            <Button size="small">全部替换</Button>
          </div>
          
          {searchState.totalMatches > 0 && (
            <div className={`text-sm mt-2 ${
              isDarkMode ? 'text-neutral-400' : 'text-gray-600'
            }`}>
              {searchState.currentMatch} / {searchState.totalMatches} 个匹配项
            </div>
          )}
        </div>
      )}
      
      {/* 错误提示 */}
      {error && (
        <Alert
          message={error}
          type="error"
          closable
          onClose={() => setError(null)}
          className="m-2"
        />
      )}
      
      {/* 编辑器 */}
      <div 
        ref={editorRef} 
        className={`flex-1 overflow-hidden ${
          isDarkMode ? 'bg-neutral-900' : 'bg-white'
        }`}
      />
    </div>
  );
});

CodeMirrorEditor.displayName = 'CodeMirrorEditor';

export default CodeMirrorEditor;