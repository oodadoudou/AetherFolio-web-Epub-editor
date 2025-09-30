import React, { useState, useEffect, useRef } from 'react';
import { Input, Button, Select, Checkbox, Typography, App } from 'antd';
import { CloseOutlined, DownOutlined, UpOutlined } from '@ant-design/icons';
import useAppStore from '../store/useAppStore';

const { Text } = Typography;
const { Option } = Select;

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

interface SearchReplacePanelProps {
  visible: boolean;
  onClose: () => void;
  currentFilePath?: string;
  isDarkMode?: boolean;
}

interface SearchResult {
  filePath: string;
  fileName: string;
  line: number;
  column: number;
  match: string;
  context: string;
  index: number;
}

const SearchReplacePanel: React.FC<SearchReplacePanelProps> = ({
  visible,
  onClose,
  currentFilePath,
  isDarkMode = false
}) => {
  const { message } = App.useApp();
  const { fileTree, currentFile, updateFileContent } = useAppStore();
  
  // Search state
  const [searchText, setSearchText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [searchMode, setSearchMode] = useState<'normal' | 'fuzzy' | 'regex' | 'regex-function'>('normal');
  const [searchScope, setSearchScope] = useState<'current' | 'text' | 'style' | 'selected' | 'open' | 'marked'>('current');
  const [searchDirection, setSearchDirection] = useState<'up' | 'down'>('down');
  const [isCaseSensitive, setIsCaseSensitive] = useState(false);
  const [isWrap, setIsWrap] = useState(true);
  
  // Results state
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);
  const [isSearching, setIsSearching] = useState(false);
  
  // Refs
  const searchInputRef = useRef<any>(null);
  
  // Focus search input when panel opens and clear highlights when closed
  useEffect(() => {
    if (visible && searchInputRef.current) {
      setTimeout(() => {
        searchInputRef.current.focus();
      }, 100);
    } else if (!visible) {
      // Clear highlights when panel is closed
      clearHighlights();
      setSearchResults([]);
    }
  }, [visible]);

  // Auto-search when search text changes (debounced)
  useEffect(() => {
    const timeoutId = setTimeout(() => {
      if (searchText.trim()) {
        performSearch();
      } else {
        setSearchResults([]);
        clearHighlights();
      }
    }, 300);

    return () => clearTimeout(timeoutId);
  }, [searchText, searchMode, searchScope, isCaseSensitive]);
  
  // Get files based on search scope
  const getFilesInScope = () => {
    const files: { path: string; name: string; content: string }[] = [];
    
    const traverseTree = (nodes: FileNode[]) => {
      nodes.forEach(node => {
        if (node.type === 'file') {
          const shouldInclude = (() => {
            switch (searchScope) {
              case 'current':
                return currentFilePath && node.path === currentFilePath;
              case 'text':
                return node.path.includes('Text/') && (node.name.endsWith('.html') || node.name.endsWith('.xhtml'));
              case 'style':
                return node.path.includes('Styles/') && node.name.endsWith('.css');
              case 'selected':
                return currentFilePath && node.path === currentFilePath;
              case 'open':
                return currentFilePath && node.path === currentFilePath;
              case 'marked':
                return currentFilePath && node.path === currentFilePath;
              default:
                return false;
            }
          })();
          
          if (shouldInclude) {
            const content = node.path === currentFile?.path ? currentFile.content : getMockContent(node.name);
            files.push({
              path: node.path,
              name: node.name,
              content
            });
          }
        }
        
        if (node.children) {
          traverseTree(node.children);
        }
      });
    };
    
    traverseTree(fileTree);
    return files;
  };
  
  // Mock content getter
  const getMockContent = (fileName: string): string => {
    if (fileName.endsWith('.html') || fileName.endsWith('.xhtml')) {
      return `<!DOCTYPE html>
<html xmlns="http://www.w3.org/1999/xhtml">
<head>
    <title>${fileName}</title>
    <link rel="stylesheet" type="text/css" href="../styles/style.css"/>
</head>
<body>
    <div class="chapter">
        <h1>Chapter Title</h1>
        <p>This is a sample paragraph in the EPUB file. You can edit this content using the AetherFolio editor.</p>
        <p>Lorem ipsum dolor sit amet, consectetur adipiscing elit. Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.</p>
        <p>"Hello world" said the character. "This is a test."</p>
    </div>
</body>
</html>`;
    } else if (fileName.endsWith('.css')) {
      return `/* EPUB Stylesheet */
body {
    font-family: "Times New Roman", serif;
    font-size: 1em;
    line-height: 1.6;
    margin: 0;
    padding: 1em;
}

.chapter {
    max-width: 600px;
    margin: 0 auto;
}

h1 {
    color: #333;
    font-size: 1.8em;
    margin-bottom: 1em;
    text-align: center;
}`;
    }
    return `Sample content for ${fileName}`;
  };
  
  // Perform search
  const performSearch = () => {
    if (!searchText.trim()) {
      setSearchResults([]);
      clearHighlights();
      return;
    }
    
    setIsSearching(true);
    const files = getFilesInScope();
    const results: SearchResult[] = [];
    
    files.forEach(file => {
      const lines = file.content.split('\n');
      
      lines.forEach((line, lineIndex) => {
        let searchPattern: RegExp;
        
        try {
          const flags = isCaseSensitive ? 'g' : 'gi';
          
          switch (searchMode) {
            case 'regex':
            case 'regex-function':
              searchPattern = new RegExp(searchText, flags);
              break;
            case 'fuzzy':
              const fuzzyPattern = searchText.split('').map(char => 
                char.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
              ).join('.*');
              searchPattern = new RegExp(fuzzyPattern, flags);
              break;
            case 'normal':
            default:
              const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              searchPattern = new RegExp(escapedText, flags);
              break;
          }
          
          let match;
          while ((match = searchPattern.exec(line)) !== null) {
            const contextStart = Math.max(0, match.index - 20);
            const contextEnd = Math.min(line.length, match.index + match[0].length + 20);
            const context = line.substring(contextStart, contextEnd);
            
            results.push({
              filePath: file.path,
              fileName: file.name,
              line: lineIndex + 1,
              column: match.index + 1,
              match: match[0],
              context,
              index: results.length
            });
            
            if (match[0].length === 0) {
              searchPattern.lastIndex++;
            }
          }
        } catch (error) {
          console.error('Search error:', error);
        }
      });
    });
    
    setSearchResults(results);
    setCurrentResultIndex(0);
    setIsSearching(false);
    
    // Auto jump to first result if found
    if (results.length > 0) {
      setTimeout(() => {
        highlightAndJumpToResult(0);
      }, 100);
    } else {
      clearHighlights();
    }
  };
  
  // Navigate results
  // Clear highlights function
  const clearHighlights = () => {
    document.dispatchEvent(new CustomEvent('clearSearchHighlights'));
  };

  // Highlight and jump to result function
  const highlightAndJumpToResult = (resultIndex: number) => {
    const results = searchResults.length > 0 ? searchResults : [];
    if (results.length === 0 || resultIndex >= results.length) return;
    
    const result = results[resultIndex];
    
    // If result is in a different file, we need to open that file first
    if (!currentFile || result.filePath !== currentFile.path) {
      // Dispatch event to open the file
      const openFileEvent = new CustomEvent('openFile', {
        detail: {
          filePath: result.filePath,
          fileName: result.fileName
        }
      });
      document.dispatchEvent(openFileEvent);
      
      // Wait for file to open, then jump to position
      setTimeout(() => {
        const jumpEvent = new CustomEvent('jumpToPosition', {
          detail: {
            line: result.line,
            column: result.column,
            searchText: searchText,
            highlight: true,
            searchMode: searchMode === 'normal' ? 'text' : searchMode,
            isCaseSensitive: isCaseSensitive
          }
        });
        document.dispatchEvent(jumpEvent);
      }, 300);
    } else {
      // Same file, jump directly
      console.log('Highlighting result:', result, 'with searchText:', searchText);
      
      const jumpEvent = new CustomEvent('jumpToPosition', {
        detail: {
          line: result.line,
          column: result.column,
          searchText: searchText,
          highlight: true,
          searchMode: searchMode === 'normal' ? 'text' : searchMode,
          isCaseSensitive: isCaseSensitive
        }
      });
      
      document.dispatchEvent(jumpEvent);
      
      // Add a small delay to ensure highlighting works properly
      setTimeout(() => {
        document.dispatchEvent(jumpEvent);
      }, 100);
    }
  };

  const goToNextResult = () => {
    if (searchResults.length > 0) {
      let newIndex;
      if (searchDirection === 'down') {
        newIndex = (currentResultIndex + 1) % searchResults.length;
      } else {
        newIndex = (currentResultIndex - 1 + searchResults.length) % searchResults.length;
      }
      setCurrentResultIndex(newIndex);
      highlightAndJumpToResult(newIndex);
    }
  };
  
  const goToPrevResult = () => {
    if (searchResults.length > 0) {
      let newIndex;
      if (searchDirection === 'down') {
        newIndex = (currentResultIndex - 1 + searchResults.length) % searchResults.length;
      } else {
        newIndex = (currentResultIndex + 1) % searchResults.length;
      }
      setCurrentResultIndex(newIndex);
      highlightAndJumpToResult(newIndex);
    }
  };
  
  // Replace functions
  const replaceCurrentMatch = () => {
    if (searchResults.length === 0 || !currentFile) return;
    
    const currentResult = searchResults[currentResultIndex];
    if (currentResult.filePath !== currentFile.path) {
      message.warning('Can only replace in currently open file');
      return;
    }
    
    const lines = currentFile.content.split('\n');
    const targetLine = lines[currentResult.line - 1];
    
    let newLine: string;
    const flags = isCaseSensitive ? 'g' : 'gi';
    
    switch (searchMode) {
      case 'regex':
      case 'regex-function': {
        const regexPattern = new RegExp(searchText, flags);
        newLine = targetLine.replace(regexPattern, replaceText);
        break;
      }
      case 'fuzzy': {
        const currentResult = searchResults[currentResultIndex];
        newLine = targetLine.replace(currentResult.match, replaceText);
        break;
      }
      case 'normal':
      default: {
        const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const normalPattern = new RegExp(escapedText, flags);
        newLine = targetLine.replace(normalPattern, replaceText);
        break;
      }
    }
    
    lines[currentResult.line - 1] = newLine;
    const newContent = lines.join('\n');
    updateFileContent(currentFile.path, newContent);
    
    setTimeout(performSearch, 100);
    message.success('Replaced 1 occurrence');
  };
  
  const replaceAllMatches = () => {
    if (searchResults.length === 0 || !currentFile) return;
    
    const currentFileResults = searchResults.filter(result => result.filePath === currentFile.path);
    if (currentFileResults.length === 0) {
      message.warning('No matches found in current file');
      return;
    }
    
    let newContent = currentFile.content;
    const flags = isCaseSensitive ? 'g' : 'gi';
    
    switch (searchMode) {
      case 'regex':
      case 'regex-function': {
        const regexPattern = new RegExp(searchText, flags);
        newContent = newContent.replace(regexPattern, replaceText);
        break;
      }
      case 'fuzzy': {
        currentFileResults.forEach(result => {
          newContent = newContent.replace(result.match, replaceText);
        });
        break;
      }
      case 'normal':
      default: {
        const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const normalPattern = new RegExp(escapedText, flags);
        newContent = newContent.replace(normalPattern, replaceText);
        break;
      }
    }
    
    updateFileContent(currentFile.path, newContent);
    setTimeout(performSearch, 100);
    message.success(`Replaced ${currentFileResults.length} occurrences`);
  };
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      performSearch();
    } else if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      goToPrevResult();
    } else if (e.key === 'F3' || (e.key === 'g' && e.ctrlKey)) {
      e.preventDefault();
      goToNextResult();
    } else if (e.key === 'F3' && e.shiftKey || (e.key === 'g' && e.ctrlKey && e.shiftKey)) {
      e.preventDefault();
      goToPrevResult();
    }
  };
  
  if (!visible) {
    return null;
  }
  
  const panelBg = isDarkMode ? '#2d2d2d' : '#ffffff';
  const borderColor = isDarkMode ? '#404040' : '#e5e7eb';
  const textColor = isDarkMode ? '#e5e5e5' : '#374151';
  const secondaryTextColor = isDarkMode ? '#a3a3a3' : '#6b7280';
  const inputBg = isDarkMode ? '#404040' : '#ffffff';
  
  return (
    <div 
      className={`border-b ${isDarkMode ? 'border-neutral-700' : 'border-gray-200'}`}
      style={{ backgroundColor: panelBg, borderColor, maxHeight: '180px', overflow: 'hidden' }}
    >
      <div className="p-2 space-y-2">
        {/* Header with close button */}
        <div className="flex items-center justify-between">
          <Text className="text-sm font-medium" style={{ color: textColor }}>
            Search and Replace
          </Text>
          <Button
            type="text"
            size="small"
            icon={<CloseOutlined />}
            onClick={onClose}
            className={isDarkMode ? 'text-neutral-400 hover:text-neutral-200' : 'text-gray-500 hover:text-gray-700'}
          />
        </div>
        
        {/* Find Row */}
        <div className="flex items-center space-x-2">
          <div className="w-16 text-right text-sm font-medium" style={{ color: textColor }}>Find:</div>
          <Input
            ref={searchInputRef}
            placeholder=""
            value={searchText}
            onChange={(e) => setSearchText(e.target.value)}
            onKeyDown={handleKeyDown}
            className="flex-1"
            style={{ backgroundColor: inputBg, borderColor, color: textColor }}
          />
          <Button
            type="default"
            onClick={() => {
              if (searchText.trim() && searchResults.length === 0) {
                performSearch();
              } else if (searchResults.length > 0) {
                goToNextResult();
              }
            }}
            disabled={!searchText.trim()}
            size="small"
          >
            {searchResults.length > 0 ? 'Next' : 'Find'}
          </Button>
          <Button
            type="default"
            onClick={() => {
              if (searchResults.length > 0) {
                replaceCurrentMatch();
                setTimeout(() => {
                  performSearch();
                  setTimeout(() => {
                    if (searchResults.length > 0) {
                      goToNextResult();
                    }
                  }, 50);
                }, 100);
              }
            }}
            disabled={searchResults.length === 0}
            size="small"
          >
            Replace and Find
          </Button>
        </div>
        
        {/* Replace Row */}
        <div className="flex items-center space-x-2">
          <div className="w-16 text-right text-sm font-medium" style={{ color: textColor }}>Replace:</div>
          <Input
            placeholder=""
            value={replaceText}
            onChange={(e) => setReplaceText(e.target.value)}
            className="flex-1"
            style={{ backgroundColor: inputBg, borderColor, color: textColor }}
          />
          <Button
            type="default"
            onClick={replaceCurrentMatch}
            disabled={searchResults.length === 0}
            size="small"
          >
            Replace
          </Button>
          <Button
            type="default"
            onClick={replaceAllMatches}
            disabled={searchResults.length === 0}
            size="small"
          >
            Replace all
          </Button>
        </div>
        
        {/* Options Row */}
        <div className="flex items-center space-x-2">
          <div className="w-16 text-right text-sm font-medium" style={{ color: textColor }}>Mode:</div>
          <Select
            value={searchMode}
            onChange={setSearchMode}
            className="w-20"
            size="small"
            suffixIcon={<DownOutlined style={{ color: secondaryTextColor }} />}
            style={{ backgroundColor: inputBg }}
          >
            <Option value="normal">Text</Option>
            <Option value="regex">Regex</Option>
          </Select>
          <Select
            value={searchScope}
            onChange={setSearchScope}
            className="w-32"
            size="small"
            suffixIcon={<DownOutlined style={{ color: secondaryTextColor }} />}
            style={{ backgroundColor: inputBg }}
          >
            <Option value="current">Current file</Option>
            <Option value="text">All text files</Option>
            <Option value="style">All style files</Option>
          </Select>
          <Select
            value={searchDirection}
            onChange={setSearchDirection}
            className="w-20"
            size="small"
            suffixIcon={<DownOutlined style={{ color: secondaryTextColor }} />}
            style={{ backgroundColor: inputBg }}
          >
            <Option value="down">Down</Option>
            <Option value="up">Up</Option>
          </Select>
          <Checkbox
            checked={isCaseSensitive}
            onChange={(e) => setIsCaseSensitive(e.target.checked)}
            style={{ color: textColor }}
          >
            Case sensitive
          </Checkbox>
          <Checkbox
            checked={isWrap}
            onChange={(e) => setIsWrap(e.target.checked)}
            style={{ color: textColor }}
          >
            Wrap
          </Checkbox>
        </div>
        
        {/* Results Info */}
        {searchResults.length > 0 && (
          <div className="flex items-center justify-between text-sm pt-2 border-t" style={{ borderColor, color: secondaryTextColor }}>
            <span>
              Found {searchResults.length} results
              {searchResults.length > 0 && ` in ${new Set(searchResults.map(r => r.fileName)).size} files`}
            </span>
            <div className="flex items-center space-x-2">
              <span>
                {searchResults.length > 0 ? `${currentResultIndex + 1}/${searchResults.length}` : '0'}
              </span>
              <Button
                type="text"
                size="small"
                icon={<UpOutlined />}
                onClick={goToPrevResult}
                disabled={searchResults.length === 0}
              />
              <Button
                type="text"
                size="small"
                icon={<DownOutlined />}
                onClick={goToNextResult}
                disabled={searchResults.length === 0}
              />
            </div>
          </div>
        )}
        
        {/* Results Preview */}
        {searchResults.length > 0 && (
          <div 
            className="mt-2 p-2 rounded border max-h-20 overflow-y-auto"
            style={{ 
              backgroundColor: isDarkMode ? '#404040' : '#f9fafb', 
              borderColor 
            }}
          >
            <Text className="text-xs font-medium block mb-2" style={{ color: secondaryTextColor }}>
              Current Result:
            </Text>
            <div className="text-sm">
              <Text className="font-medium" style={{ color: textColor }}>
                {searchResults[currentResultIndex]?.fileName}:{searchResults[currentResultIndex]?.line}:{searchResults[currentResultIndex]?.column}
              </Text>
              <div 
                className="mt-1 font-mono text-xs p-2 rounded border"
                style={{ 
                  backgroundColor: isDarkMode ? '#333333' : '#ffffff', 
                  borderColor,
                  color: textColor 
                }}
              >
                {searchResults[currentResultIndex]?.context}
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchReplacePanel;