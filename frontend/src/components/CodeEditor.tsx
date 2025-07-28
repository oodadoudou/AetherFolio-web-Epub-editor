import React, { useRef, useEffect } from 'react';
import { Editor } from '@monaco-editor/react';
import { Typography, Empty, Button, Space } from 'antd';
import { FileTextOutlined, SearchOutlined } from '@ant-design/icons';
import * as monaco from 'monaco-editor';

const { Title } = Typography;

interface CurrentFile {
  path: string;
  content: string;
  language: string;
}

interface CodeEditorProps {
  file: CurrentFile | null;
  onChange: (content: string) => void;
  onOpenSearch?: () => void;
  isDarkMode?: boolean;
}

const CodeEditor: React.FC<CodeEditorProps> = ({ file, onChange, onOpenSearch, isDarkMode = false }) => {
  const editorRef = useRef<monaco.editor.IStandaloneCodeEditor | null>(null);
  const decorationsRef = useRef<string[]>([]);

  const handleEditorChange = (value: string | undefined) => {
    if (value !== undefined) {
      onChange(value);
    }
  };

  const handleEditorDidMount = (editor: monaco.editor.IStandaloneCodeEditor) => {
    editorRef.current = editor;
  };

  // Handle jump to position events with improved highlighting
  useEffect(() => {
    const handleJumpToPosition = (event: CustomEvent) => {
      const { line, column, searchText, highlight, searchMode, isCaseSensitive } = event.detail;
      const editor = editorRef.current;
      
      if (!editor) return;

      // Clear previous decorations
      if (decorationsRef.current.length > 0) {
        editor.deltaDecorations(decorationsRef.current, []);
        decorationsRef.current = [];
      }

      // Jump to the position
      const position = { lineNumber: line, column: column };
      editor.setPosition(position);
      editor.revealLineInCenter(line);
      editor.focus();

      // Add highlighting if requested
      if (highlight && searchText) {
        const model = editor.getModel();
        if (model) {
          const decorations: monaco.editor.IModelDeltaDecoration[] = [];
          
          // Find all matches in the document for comprehensive highlighting
          const content = model.getValue();
          let searchPattern: RegExp;
          
          try {
            const flags = isCaseSensitive ? 'g' : 'gi';
            
            if (searchMode === 'regex') {
              searchPattern = new RegExp(searchText, flags);
            } else {
              const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
              searchPattern = new RegExp(escapedText, flags);
            }
            
            const lines = content.split('\n');
            lines.forEach((lineContent, lineIndex) => {
              let match;
              const lineNumber = lineIndex + 1;
              
              // Reset regex lastIndex for each line
              searchPattern.lastIndex = 0;
              
              while ((match = searchPattern.exec(lineContent)) !== null) {
                const startColumn = match.index + 1;
                const endColumn = startColumn + match[0].length;
                
                // Highlight current match differently
                const isCurrentMatch = lineNumber === line && startColumn === column;
                
                decorations.push({
                   range: new monaco.Range(lineNumber, startColumn, lineNumber, endColumn),
                   options: {
                     className: isCurrentMatch ? 'current-search-highlight' : 'search-highlight',
                     inlineClassName: isCurrentMatch ? 'current-search-highlight-inline' : 'search-highlight-inline',
                     overviewRuler: {
                       color: isCurrentMatch ? '#f59e0b' : '#fcd34d',
                       position: monaco.editor.OverviewRulerLane.Right
                     },
                     minimap: {
                       color: isCurrentMatch ? '#f59e0b' : '#fcd34d',
                       position: monaco.editor.MinimapPosition.Inline
                     }
                   }
                 });
                
                // Prevent infinite loop for zero-width matches
                if (match[0].length === 0) {
                  searchPattern.lastIndex++;
                }
              }
            });
            
            if (decorations.length > 0) {
              decorationsRef.current = editor.deltaDecorations([], decorations);
            }
            
          } catch (error) {
            console.error('Highlighting error:', error);
          }
        }
      }
    };

    const handleClearHighlights = () => {
      const editor = editorRef.current;
      if (editor && decorationsRef.current.length > 0) {
        editor.deltaDecorations(decorationsRef.current, []);
        decorationsRef.current = [];
      }
    };

    document.addEventListener('jumpToPosition', handleJumpToPosition as EventListener);
    document.addEventListener('clearSearchHighlights', handleClearHighlights);

    return () => {
      document.removeEventListener('jumpToPosition', handleJumpToPosition as EventListener);
      document.removeEventListener('clearSearchHighlights', handleClearHighlights);
    };
  }, []);

  // Clean up decorations when file changes
  useEffect(() => {
    if (editorRef.current && decorationsRef.current.length > 0) {
      editorRef.current.deltaDecorations(decorationsRef.current, []);
      decorationsRef.current = [];
    }
  }, [file?.path]);

  if (!file) {
    return (
      <div className={`h-full ${isDarkMode ? 'border-neutral-700' : 'bg-white border-gray-200'} border-r flex items-center justify-center`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
        <Empty 
          image={<FileTextOutlined className={`text-4xl ${isDarkMode ? 'text-neutral-500' : 'text-gray-300'}`} />}
          description={<span style={isDarkMode ? {color: '#a3a3a3'} : {}}>Select a file to edit</span>}
        />
      </div>
    );
  }

  return (
    <div className={`h-full ${isDarkMode ? 'border-neutral-700' : 'bg-white border-gray-200'} border-r`} style={isDarkMode ? {backgroundColor: '#2d2d2d'} : {}}>
      <div className={`p-3 border-b ${isDarkMode ? 'border-neutral-700' : 'border-gray-200 bg-gray-50'}`} style={isDarkMode ? {backgroundColor: '#333333'} : {}}>
        <div className="flex items-center justify-between">
          <Title level={5} className={`mb-0 ${isDarkMode ? '' : 'text-gray-700'}`} style={isDarkMode ? {color: '#e5e5e5'} : {}}>
            {file.path.split('/').pop()}
          </Title>
          <Space>
            <Button 
              icon={<SearchOutlined />} 
              size="small" 
              onClick={onOpenSearch}
              title="Search and Replace (Ctrl+F)"
            />
            <span className={`text-xs px-2 py-1 rounded ${isDarkMode ? '' : 'text-gray-500 bg-gray-200'}`} style={isDarkMode ? {color: '#a3a3a3', backgroundColor: '#404040'} : {}}>
              {file.language.toUpperCase()}
            </span>
          </Space>
        </div>
      </div>
      
      <div style={{ height: 'calc(100% - 60px)' }}>
        <Editor
          height="100%"
          language={file.language}
          value={file.content}
          onChange={handleEditorChange}
          onMount={handleEditorDidMount}
          theme={isDarkMode ? "vs-dark" : "vs"}
          options={{
            minimap: { enabled: true },
            fontSize: 14,
            lineNumbers: 'on',
            wordWrap: 'on',
            automaticLayout: true,
            scrollBeyondLastLine: false,
            renderWhitespace: 'selection',
            tabSize: 2,
            insertSpaces: true,
            folding: true,
            lineDecorationsWidth: 10,
            lineNumbersMinChars: 3,
            glyphMargin: false,
            contextmenu: true,
            mouseWheelZoom: true,
            smoothScrolling: true,
            cursorBlinking: 'blink',
            cursorStyle: 'line',
            renderLineHighlight: 'line',
            selectOnLineNumbers: true,
            roundedSelection: false,
            readOnly: false,
            cursorSmoothCaretAnimation: 'on',
          }}
        />
      </div>
    </div>
  );
};

export default CodeEditor;