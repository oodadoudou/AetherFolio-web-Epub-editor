import React, { useState, useEffect, useRef } from 'react';
import { X, ChevronDown } from 'lucide-react';
import useAppStore from '../store/useAppStore';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

interface SelectProps {
  value: string;
  onChange: (value: string) => void;
  options: { value: string; label: string }[];
  className?: string;
  isDarkMode?: boolean;
}

const CustomSelect: React.FC<SelectProps> = ({ value, onChange, options, className = '', isDarkMode = false }) => {
  const [isOpen, setIsOpen] = useState(false);
  const selectedOption = options.find(opt => opt.value === value);
  
  const buttonBg = isDarkMode ? 'bg-gray-700' : 'bg-white';
  const buttonBorder = isDarkMode ? 'border-gray-600' : 'border-gray-300';
  const buttonHover = isDarkMode ? 'hover:border-gray-500' : 'hover:border-gray-400';
  const buttonFocus = isDarkMode ? 'focus:border-blue-400' : 'focus:border-blue-500';
  const textColor = isDarkMode ? 'text-gray-200' : 'text-gray-900';
  const iconColor = isDarkMode ? 'text-gray-400' : 'text-gray-500';
  const dropdownBg = isDarkMode ? 'bg-gray-700' : 'bg-white';
  const dropdownBorder = isDarkMode ? 'border-gray-600' : 'border-gray-300';
  const optionHover = isDarkMode ? 'hover:bg-gray-600' : 'hover:bg-gray-100';
  const optionFocus = isDarkMode ? 'focus:bg-gray-600' : 'focus:bg-gray-100';
  
  return (
    <div className={`relative ${className}`}>
      <button
        type="button"
        onClick={() => setIsOpen(!isOpen)}
        className={`w-full px-3 py-1 text-left ${buttonBg} border ${buttonBorder} rounded flex items-center justify-between ${buttonHover} focus:outline-none ${buttonFocus} ${textColor}`}
      >
        <span className="text-sm">{selectedOption?.label || value}</span>
        <ChevronDown className={`w-4 h-4 ${iconColor}`} />
      </button>
      {isOpen && (
        <div className={`absolute top-full left-0 right-0 mt-1 ${dropdownBg} border ${dropdownBorder} rounded shadow-lg z-50`}>
          {options.map((option) => (
            <button
              key={option.value}
              type="button"
              onClick={() => {
                onChange(option.value);
                setIsOpen(false);
              }}
              className={`w-full px-3 py-2 text-left text-sm ${optionHover} focus:outline-none ${optionFocus} ${textColor}`}
            >
              {option.label}
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

interface SearchReplaceModalProps {
  visible: boolean;
  onClose: () => void;
  currentFilePath?: string;
  autoOpen?: boolean;
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

const SearchReplaceModal: React.FC<SearchReplaceModalProps> = ({
  visible,
  onClose,
  isDarkMode = false
}) => {
  const { fileTree, currentFile, updateFileContent } = useAppStore();
  
  // Search state
  const [searchText, setSearchText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [searchMode, setSearchMode] = useState('text');
  const [searchScope, setSearchScope] = useState('current');
  const [searchDirection, setSearchDirection] = useState('down');
  const [isCaseSensitive, setIsCaseSensitive] = useState(false);
  const [isWrap, setIsWrap] = useState(true);
  
  // Results state
  const [searchResults, setSearchResults] = useState<SearchResult[]>([]);
  const [currentResultIndex, setCurrentResultIndex] = useState(0);
  const [, setIsSearching] = useState(false);
  
  // Refs
  const searchInputRef = useRef<HTMLInputElement>(null);
  
  // Toast function
  const showToast = (message: string, type: 'success' | 'warning' | 'error' = 'success') => {
    // Simple toast implementation - in a real app, you might use a toast library
    console.log(`${type.toUpperCase()}: ${message}`);
  };
  
  // Simplified options for VSCode-like experience
  const modeOptions = [
    { value: 'text', label: 'Text' },
    { value: 'regex', label: 'Regex' }
  ];
  
  const scopeOptions = [
    { value: 'current', label: 'Current file' },
    { value: 'all', label: 'All files' },
    { value: 'text', label: 'Text files (HTML/XHTML)' },
    { value: 'style', label: 'Style files (CSS)' },
    { value: 'content', label: 'Content files (HTML/XHTML/CSS)' },
    { value: 'images', label: 'Image files' },
    { value: 'fonts', label: 'Font files' },
    { value: 'misc', label: 'Misc files (TXT/XML)' },
    { value: 'selected', label: 'Selected files' },
    { value: 'open', label: 'Open files' }
  ];
  
  const directionOptions = [
    { value: 'down', label: 'Down ↓' },
    { value: 'up', label: 'Up ↑' }
  ];
  
  // Focus search input when modal opens and clear highlights when closed
  useEffect(() => {
    if (visible && searchInputRef.current) {
      setTimeout(() => {
        searchInputRef.current.focus();
      }, 100);
    } else if (!visible) {
      // Clear highlights when modal is closed
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
                return currentFile && node.path === currentFile.path;
              case 'all':
                return true;
              case 'text':
                return node.name.endsWith('.html') || node.name.endsWith('.xhtml');
              case 'style':
                return node.name.endsWith('.css');
              case 'content':
                return node.name.endsWith('.html') || node.name.endsWith('.xhtml') || node.name.endsWith('.css');
              case 'images':
                return /\.(jpg|jpeg|png|gif|svg|webp|bmp|ico)$/i.test(node.name);
              case 'fonts':
                return /\.(ttf|otf|woff|woff2|eot)$/i.test(node.name);
              case 'misc':
                return node.name.endsWith('.txt') || node.name.endsWith('.xml') || node.name.endsWith('.opf') || node.name.endsWith('.ncx');
              case 'selected':
                // Mock: return currently selected files (in real app, this would be from selection state)
                return currentFile && node.path === currentFile.path;
              case 'open':
                // Mock: return currently open files (in real app, this would be from open tabs state)
                return currentFile && node.path === currentFile.path;
              default:
                return false;
            }
          })();
          
          if (shouldInclude) {
            // Get mock content for the file
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
  
  // Mock content getter (in real app, this would fetch actual file content)
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
    } else if (fileName.endsWith('.txt')) {
      return `This is a sample TEXT file content.

You can edit this content directly in the AetherFolio editor.
The TEXT file supports:
- Direct editing
- Search and replace functionality
- Batch replacement operations
- Export capabilities

Lorem ipsum dolor sit amet, consectetur adipiscing elit.
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua.
Ut enim ad minim veniam, quis nostrud exercitation.

This is another paragraph with some sample text for testing search functionality.
"Hello world" is a common phrase used in programming examples.`;
    }
    return `Sample content for ${fileName}`;
  };
  
  // Clear search highlights
  const clearHighlights = () => {
    document.dispatchEvent(new CustomEvent('clearSearchHighlights'));
  };

  // Perform search and highlight
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
          case 'regex': {
            searchPattern = new RegExp(searchText, flags);
            break;
          }
          case 'text':
          default: {
            const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            searchPattern = new RegExp(escapedText, flags);
            break;
          }
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
            
            // Prevent infinite loop for zero-width matches
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
    
    // Highlight and jump to first result with a small delay to ensure state is updated
    if (results.length > 0) {
      setTimeout(() => {
        highlightAndJumpToResult(0);
      }, 50);
    } else {
      // Clear highlights if no results
      clearHighlights();
    }
  };
  
  // Highlight and jump to search result
  const highlightAndJumpToResult = (resultIndex: number) => {
    if (!currentFile) return;
    
    // Use the current searchResults state or get from parameters
    const results = searchResults.length > 0 ? searchResults : [];
    if (results.length === 0 || resultIndex >= results.length) return;
    
    const result = results[resultIndex];
    if (result.filePath !== currentFile.path) return;
    
    console.log('Highlighting result:', result, 'with searchText:', searchText);
    
    // Use custom event to communicate with Monaco Editor
    const jumpEvent = new CustomEvent('jumpToPosition', {
      detail: {
        line: result.line,
        column: result.column,
        searchText: searchText, // Use the current search text instead of result.match
        highlight: true,
        searchMode: searchMode,
        isCaseSensitive: isCaseSensitive
      }
    });
    
    document.dispatchEvent(jumpEvent);
  };
  
  // Navigate results
  const goToNextResult = () => {
    if (searchResults.length > 0) {
      const newIndex = (currentResultIndex + 1) % searchResults.length;
      setCurrentResultIndex(newIndex);
      highlightAndJumpToResult(newIndex);
    }
  };
  
  const goToPrevResult = () => {
    if (searchResults.length > 0) {
      const newIndex = (currentResultIndex - 1 + searchResults.length) % searchResults.length;
      setCurrentResultIndex(newIndex);
      highlightAndJumpToResult(newIndex);
    }
  };
  
  const handleFindClick = () => {
    if (searchText.trim() && searchResults.length === 0) {
      performSearch();
    } else if (searchResults.length > 0) {
      // Always go to next result when Find button is clicked
      goToNextResult();
    }
  };
  
  // 处理搜索方向变化
  const handleDirectionChange = (direction: string) => {
    setSearchDirection(direction);
    // 如果有搜索结果，立即按新方向跳转
    if (searchResults.length > 0) {
      if (direction === 'down') {
        goToNextResult();
      } else {
        goToPrevResult();
      }
    }
  };
  


  // Replace functions
  const replaceCurrentMatch = () => {
    if (searchResults.length === 0 || !currentFile) return;
    
    const currentResult = searchResults[currentResultIndex];
    if (currentResult.filePath !== currentFile.path) {
      showToast('Can only replace in currently open file', 'warning');
      return;
    }
    
    const lines = currentFile.content.split('\n');
    const targetLine = lines[currentResult.line - 1];
    
    let newLine: string;
    const flags = isCaseSensitive ? 'g' : 'gi';
    
    switch (searchMode) {
      case 'regex':
        const regexPattern = new RegExp(searchText, flags);
        newLine = targetLine.replace(regexPattern, replaceText);
        break;
      case 'text':
      default:
        const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const textPattern = new RegExp(escapedText, flags);
        newLine = targetLine.replace(textPattern, replaceText);
        break;
    }
    
    lines[currentResult.line - 1] = newLine;
    const newContent = lines.join('\n');
    updateFileContent(currentFile.path, newContent);
    
    showToast('Replaced 1 occurrence');
    
    // Re-perform search to update results after replacement
    setTimeout(() => {
      performSearch();
    }, 100);
  };
  
  // Replace current match and find next
  const replaceAndFindNext = () => {
    if (searchResults.length === 0 || !currentFile) return;
    
    const currentResult = searchResults[currentResultIndex];
    if (currentResult.filePath !== currentFile.path) {
      showToast('Can only replace in currently open file', 'warning');
      return;
    }
    
    const lines = currentFile.content.split('\n');
    const targetLine = lines[currentResult.line - 1];
    
    let newLine: string;
    const flags = isCaseSensitive ? 'g' : 'gi';
    
    switch (searchMode) {
      case 'regex':
        const regexPattern = new RegExp(searchText, flags);
        newLine = targetLine.replace(regexPattern, replaceText);
        break;
      case 'text':
      default:
        const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const textPattern = new RegExp(escapedText, flags);
        newLine = targetLine.replace(textPattern, replaceText);
        break;
    }
    
    lines[currentResult.line - 1] = newLine;
    const newContent = lines.join('\n');
    updateFileContent(currentFile.path, newContent);
    
    showToast('Replaced 1 occurrence');
    
    // Re-perform search and go to next result
    setTimeout(() => {
      performSearch();
      setTimeout(() => {
        if (searchResults.length > 0) {
          goToNextResult();
        }
      }, 50);
    }, 100);
  };
  
  const replaceAllMatches = () => {
    if (searchResults.length === 0 || !currentFile) return;
    
    // Only replace in current file for safety
    const currentFileResults = searchResults.filter(result => result.filePath === currentFile.path);
    if (currentFileResults.length === 0) {
      showToast('No matches found in current file', 'warning');
      return;
    }
    
    let newContent = currentFile.content;
    
    const flags = isCaseSensitive ? 'g' : 'gi';
    
    switch (searchMode) {
      case 'regex': {
        const regexPattern = new RegExp(searchText, flags);
        newContent = newContent.replace(regexPattern, replaceText);
        break;
      }
      case 'text':
      default: {
        const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
        const textPattern = new RegExp(escapedText, flags);
        newContent = newContent.replace(textPattern, replaceText);
        break;
      }
    }
    
    updateFileContent(currentFile.path, newContent);
    
    showToast(`Replaced ${currentFileResults.length} occurrences`);
  };
  
  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (searchResults.length > 0) {
        goToNextResult();
      }
    } else if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      if (searchResults.length > 0) {
        goToPrevResult();
      }
    } else if (e.key === 'F3' || (e.key === 'g' && e.ctrlKey)) {
      e.preventDefault();
      goToNextResult();
    } else if (e.key === 'F3' && e.shiftKey || (e.key === 'g' && e.ctrlKey && e.shiftKey)) {
      e.preventDefault();
      goToPrevResult();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };
  
  if (!visible) return null;

  // Theme styles
  const modalBg = isDarkMode ? 'bg-gray-800' : 'bg-white';
  const borderColor = isDarkMode ? 'border-gray-600' : 'border-gray-200';
  const textColor = isDarkMode ? 'text-gray-200' : 'text-gray-900';
  const headerBg = isDarkMode ? 'bg-gray-700' : 'bg-gray-50';
  const closeBtnHover = isDarkMode ? 'hover:bg-gray-600' : 'hover:bg-gray-100';
  const inputBg = isDarkMode ? 'bg-gray-700' : 'bg-white';
  const inputBorder = isDarkMode ? 'border-gray-600' : 'border-gray-300';
  const inputFocus = isDarkMode ? 'focus:border-blue-400' : 'focus:border-blue-500';
  const buttonBg = isDarkMode ? 'bg-gray-600' : 'bg-gray-100';
  const buttonHover = isDarkMode ? 'hover:bg-gray-500' : 'hover:bg-gray-200';
  const buttonBorder = isDarkMode ? 'border-gray-500' : 'border-gray-300';
  const resultsBg = isDarkMode ? 'bg-gray-700' : 'bg-gray-50';
  const resultsTextColor = isDarkMode ? 'text-gray-300' : 'text-gray-700';
  const previewBg = isDarkMode ? 'bg-gray-800' : 'bg-white';

  return (
    <div className="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div className={`${modalBg} rounded-lg shadow-xl w-[600px] max-w-[90vw] max-h-[70vh] overflow-y-auto`}>
        {/* Header with close button */}
        <div className={`flex items-center justify-between p-3 border-b ${borderColor} ${headerBg}`}>
          <h2 className={`text-base font-semibold ${textColor}`}>Find and Replace</h2>
          <button
            onClick={onClose}
            className={`p-1 ${closeBtnHover} rounded`}
          >
            <X className="w-4 h-4 text-red-500" />
          </button>
        </div>
        
        {/* Content */}
        <div className="p-4 space-y-3">
          {/* Find Row */}
          <div className="flex items-center gap-2">
            <label className={`w-12 text-xs font-medium text-right ${textColor}`}>Find:</label>
            <input
              ref={searchInputRef}
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={handleKeyDown}
              className={`flex-1 px-2 py-1 text-sm border ${inputBorder} ${inputBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
              placeholder=""
            />

            <button
              onClick={handleFindClick}
              disabled={!searchText.trim()}
              className={`px-3 py-1 ${buttonBg} ${buttonHover} border ${buttonBorder} ${textColor} rounded text-xs font-medium disabled:opacity-50`}
            >
              Find
            </button>
            <button
              onClick={replaceAndFindNext}
              disabled={searchResults.length === 0}
              className={`px-3 py-1 ${buttonBg} ${buttonHover} border ${buttonBorder} ${textColor} rounded text-xs font-medium disabled:opacity-50`}
            >
              Replace and Find
            </button>
          </div>
          
          {/* Replace Row */}
          <div className="flex items-center gap-2">
            <label className={`w-12 text-xs font-medium text-right ${textColor}`}>Replace:</label>
            <input
              type="text"
              value={replaceText}
              onChange={(e) => setReplaceText(e.target.value)}
              className={`flex-1 px-2 py-1 text-sm border ${inputBorder} ${inputBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
              placeholder=""
            />
            <button
              onClick={replaceCurrentMatch}
              disabled={searchResults.length === 0}
              className={`px-3 py-1 ${buttonBg} ${buttonHover} border ${buttonBorder} ${textColor} rounded text-xs font-medium disabled:opacity-50`}
            >
              Replace
            </button>
            <button
              onClick={replaceAllMatches}
              disabled={searchResults.length === 0}
              className={`px-3 py-1 ${buttonBg} ${buttonHover} border ${buttonBorder} ${textColor} rounded text-xs font-medium disabled:opacity-50`}
            >
              Replace all
            </button>
          </div>
          
          {/* Search Mode and Scope Row */}
          <div className="flex items-center gap-2">
            <label className={`w-12 text-xs font-medium text-right ${textColor}`}>Mode:</label>
            <CustomSelect
              value={searchMode}
              onChange={setSearchMode}
              options={modeOptions}
              className="w-20"
              isDarkMode={isDarkMode}
            />
            <label className={`text-xs font-medium ml-2 ${textColor}`}>Scope:</label>
            <CustomSelect
              value={searchScope}
              onChange={setSearchScope}
              options={scopeOptions}
              className="w-40"
              isDarkMode={isDarkMode}
            />
          </div>
          
          {/* Direction and Options Row */}
          <div className="flex items-center gap-2">
            <label className={`w-12 text-xs font-medium text-right ${textColor}`}>Direction:</label>
            <CustomSelect
              value={searchDirection}
              onChange={handleDirectionChange}
              options={directionOptions}
              className="w-24"
              isDarkMode={isDarkMode}
            />
            <label className={`flex items-center gap-1 text-xs ${textColor} ml-4`}>
              <input
                type="checkbox"
                checked={isCaseSensitive}
                onChange={(e) => setIsCaseSensitive(e.target.checked)}
                className="rounded"
              />
              Case sensitive
            </label>
            <label className={`flex items-center gap-1 text-xs ${textColor}`}>
              <input
                type="checkbox"
                checked={isWrap}
                onChange={(e) => setIsWrap(e.target.checked)}
                className="rounded"
              />
              Wrap
            </label>
          </div>
          
          {/* Results Info */}
          {searchResults.length > 0 && (
            <div className={`flex items-center justify-between text-xs ${resultsTextColor} pt-1 border-t ${borderColor}`}>
              <span>
                Found {searchResults.length} results
                {searchResults.length > 0 && ` in ${new Set(searchResults.map(r => r.fileName)).size} files`}
              </span>
              <div className="flex items-center space-x-1">
                <span>
                  {searchResults.length > 0 ? `${currentResultIndex + 1}/${searchResults.length}` : '0'}
                </span>
                <button
                  onClick={goToPrevResult}
                  disabled={searchResults.length === 0}
                  className={`p-0.5 ${buttonHover} rounded disabled:opacity-50 text-xs ${textColor}`}
                >
                  ↑
                </button>
                <button
                  onClick={goToNextResult}
                  disabled={searchResults.length === 0}
                  className={`p-0.5 ${buttonHover} rounded disabled:opacity-50 text-xs ${textColor}`}
                >
                  ↓
                </button>
              </div>
            </div>
          )}
          
          {/* Results Preview */}
          {searchResults.length > 0 && (
            <div className={`mt-2 p-2 ${resultsBg} rounded border ${borderColor} max-h-24 overflow-y-auto`}>
              <div className={`text-xs font-medium ${resultsTextColor} mb-1`}>
                Current Result:
              </div>
              <div className="text-xs">
                <div className={`font-medium ${textColor}`}>
                  {searchResults[currentResultIndex]?.fileName}:{searchResults[currentResultIndex]?.line}:{searchResults[currentResultIndex]?.column}
                </div>
                <div className={`mt-1 font-mono text-xs ${previewBg} ${textColor} p-1 rounded border ${borderColor}`}>
                  {searchResults[currentResultIndex]?.context}
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default SearchReplaceModal;