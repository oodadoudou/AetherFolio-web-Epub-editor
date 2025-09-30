import React, { useState, useRef, useEffect } from 'react';
import { X, ChevronUp, ChevronDown, FileText, File } from 'lucide-react';
import { toast } from 'sonner';
import { fileService } from '../services/file';
import useAppStore from '../store/useAppStore';

interface SearchResult {
  line: number;
  column: number;
  text: string;
  context: string;
  filePath: string;
  fileName: string;
  matchText: string;
}

type SearchScope = 'current' | 'allText' | 'allStyle';

interface SearchReplaceCardProps {
  visible: boolean;
  onClose: () => void;
  currentFile: {
    path: string;
    name: string;
    content: string;
  } | null;
  updateFileContent: (content: string) => void;
  monacoEditor: any;
  fileTree: any[];
  onFileSelect: (file: any) => void;
  isDarkMode?: boolean;
  onSave?: () => Promise<void>;
  sessionId?: string;
}

const SearchReplaceCard: React.FC<SearchReplaceCardProps> = ({
  visible,
  onClose,
  currentFile,
  updateFileContent,
  monacoEditor,
  fileTree,
  onFileSelect,
  isDarkMode = false,
  onSave,
  sessionId: propSessionId
}) => {
  const { sessionId: storeSessionId } = useAppStore();
  const sessionId = propSessionId || storeSessionId;
  const [searchText, setSearchText] = useState('');
  const [replaceText, setReplaceText] = useState('');
  const [isCaseSensitive, setIsCaseSensitive] = useState(false);
  const [isWholeWord, setIsWholeWord] = useState(false);
  const [isRegex, setIsRegex] = useState(false);
  const [matches, setMatches] = useState<any[]>([]);
  const [totalMatches, setTotalMatches] = useState(0);
  const [currentMatchIndex, setCurrentMatchIndex] = useState(0);
  const [searchScope, setSearchScope] = useState<SearchScope>('current');
  const [crossFileResults, setCrossFileResults] = useState<SearchResult[]>([]);
  const [searchDirection, setSearchDirection] = useState<'up' | 'down'>('down');
  const [isWrap, setIsWrap] = useState(true);
  const searchInputRef = useRef<HTMLInputElement>(null);

  // Focus search input when component becomes visible
  useEffect(() => {
    if (visible && searchInputRef.current) {
      searchInputRef.current.focus();
    }
  }, [visible]);

  // Get files based on search scope
  const getFilesInScope = (): any[] => {
    console.log('🔍 getFilesInScope called with scope:', searchScope);
    console.log('📁 fileTree:', fileTree);
    console.log('📁 fileTree structure (detailed):');
    fileTree?.forEach((item, index) => {
      console.log(`  [${index}] name: "${item.name}", path: "${item.path}", type: "${item.type}"`);
      if (item.children && item.children.length > 0) {
        console.log(`    children (${item.children.length}):`);
        item.children.forEach((child, childIndex) => {
          console.log(`      [${childIndex}] name: "${child.name}", path: "${child.path}", type: "${child.type}"`);
          if (child.children && child.children.length > 0) {
            console.log(`        grandchildren (${child.children.length}):`);
            child.children.forEach((grandchild, grandIndex) => {
              console.log(`          [${grandIndex}] name: "${grandchild.name}", path: "${grandchild.path}", type: "${grandchild.type}"`);
            });
          }
        });
      }
    });
    
    if (!fileTree) {
      console.warn('❌ No fileTree available');
      return [];
    }
    
    const getAllFiles = (items: any[]): any[] => {
      let files: any[] = [];
      items.forEach(item => {
        console.log(`🔍 Processing item: name="${item.name}", type="${item.type}", hasChildren=${!!item.children}`);
        // A file is anything that's not a directory and doesn't have children
        if (item.type !== 'directory' && (!item.children || item.children.length === 0)) {
          files.push(item);
          console.log(`  ✅ Added file: ${item.name} (type: ${item.type})`);
        } else if (item.children && item.children.length > 0) {
          console.log(`  📁 Recursing into directory: ${item.name} with ${item.children.length} children`);
          files = files.concat(getAllFiles(item.children));
        }
      });
      return files;
    };

    const allFiles = getAllFiles(fileTree);
    console.log('📄 All files found:', allFiles.length);
    allFiles.forEach((file, index) => {
      console.log(`  File [${index}]: name="${file.name}", path="${file.path}", type="${file.type}"`);
    });
    
    let scopedFiles: any[] = [];
    switch (searchScope) {
      case 'current':
        scopedFiles = currentFile ? [{ path: currentFile.path, name: currentFile.name, content: currentFile.content }] : [];
        break;
      case 'allText':
        scopedFiles = allFiles.filter(file => 
          file.name.match(/\.(html|xhtml|xml|txt|md|js|ts|json)$/i)
        );
        console.log('📝 Text files filtered:', scopedFiles.length, scopedFiles.map(f => f.name));
        break;
      case 'allStyle':
        console.log('🎨 Filtering style files...');
        console.log('🎨 Style file pattern: /\\.(css|scss|sass|less)$/i');
        scopedFiles = allFiles.filter(file => {
          const isStyleFile = file.name.match(/\.(css|scss|sass|less)$/i);
          console.log(`  Checking "${file.name}": ${isStyleFile ? '✅ MATCH' : '❌ NO MATCH'}`);
          return isStyleFile;
        });
        console.log('🎨 Style files filtered:', scopedFiles.length, scopedFiles.map(f => f.name));
        break;
      default:
        scopedFiles = [];
    }
    
    console.log('✅ Final scoped files:', scopedFiles.length, scopedFiles);
    return scopedFiles;
  };

  // Search across multiple files
  const searchInFiles = async (files: any[]): Promise<SearchResult[]> => {
    console.log('🔎 searchInFiles called with files:', files.length);
    console.log('🔑 sessionId:', sessionId);
    console.log('🔤 searchText:', searchText);
    
    const results: SearchResult[] = [];
    
    for (const file of files) {
      console.log(`📂 Processing file: ${file.name} (${file.path})`);
      let content = file.content;
      
      // If file content is not available, try to get it
      if (!content) {
        console.log(`📄 No content available for ${file.name}, attempting to fetch...`);
        
        if (file.path === currentFile?.path) {
          console.log(`📝 Using current file content for ${file.name}`);
          content = currentFile.content;
        } else {
          // For other files, fetch content from the server
          try {
            if (sessionId) {
              console.log(`🌐 Fetching content from server for file: ${file.path}`);
              const fileContent = await fileService.getFileContent(sessionId, file.path);
              content = fileContent.content;
              console.log(`✅ Successfully fetched content for ${file.name}, length: ${content?.length || 0}`);
            } else {
              console.warn(`❌ No sessionId available, skipping file ${file.path}`);
              continue;
            }
          } catch (error) {
            console.error(`❌ Failed to fetch content for ${file.path}:`, error);
            continue;
          }
        }
      } else {
        console.log(`✅ Content already available for ${file.name}, length: ${content.length}`);
      }
      
      if (!content) {
        console.warn(`⚠️ No content available for ${file.name}, skipping`);
        continue;
      }
      
      const lines = content.split('\n');
      console.log(`📋 File ${file.name} has ${lines.length} lines`);
      
      let fileMatches = 0;
      lines.forEach((line, lineIndex) => {
        let searchPattern: RegExp;
        
        try {
          if (isRegex) {
            searchPattern = new RegExp(searchText, isCaseSensitive ? 'g' : 'gi');
          } else {
            const escapedText = searchText.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
            const pattern = isWholeWord ? `\\b${escapedText}\\b` : escapedText;
            searchPattern = new RegExp(pattern, isCaseSensitive ? 'g' : 'gi');
          }
        } catch (e) {
          console.error(`❌ Invalid regex pattern for ${file.name}:`, e);
          return; // Skip invalid regex
        }
        
        let match;
        while ((match = searchPattern.exec(line)) !== null) {
          fileMatches++;
          results.push({
            line: lineIndex + 1,
            column: match.index + 1,
            text: line,
            context: line.trim(),
            filePath: file.path,
            fileName: file.name,
            matchText: match[0]
          });
          
          // Prevent infinite loop for zero-length matches
          if (match.index === searchPattern.lastIndex) {
            searchPattern.lastIndex++;
          }
        }
      });
      
      console.log(`🎯 Found ${fileMatches} matches in ${file.name}`);
    }
    
    console.log('📈 Search summary:');
    console.log(`  - Files processed: ${files.length}`);
    console.log(`  - Total matches found: ${results.length}`);
    console.log(`  - Files with matches: ${results.reduce((acc, curr, index, arr) => {
      const fileName = curr.fileName;
      return acc.includes(fileName) ? acc : [...acc, fileName];
    }, [] as string[]).length}`);
    
    return results;
  };

  // Perform search using Monaco Editor's find functionality or cross-file search
  const performSearch = async () => {
    if (!searchText.trim()) {
      setMatches([]);
      setTotalMatches(0);
      setCurrentMatchIndex(0);
      setCrossFileResults([]);
      return;
    }

    if (searchScope === 'current' && monacoEditor) {
      // Use Monaco Editor's built-in find functionality for current file
      try {
        const findMatches = monacoEditor.getModel()?.findMatches(
          searchText,
          true, // searchOnlyEditableRange
          isRegex,
          isCaseSensitive,
          isWholeWord ? '\\b' : null,
          true // captureMatches
        ) || [];

        setMatches(findMatches);
        setTotalMatches(findMatches.length);
        setCurrentMatchIndex(findMatches.length > 0 ? 0 : -1);
        setCrossFileResults([]);

        if (findMatches.length > 0) {
          // Jump to first match
          jumpToMatch(0, findMatches);
        } else {
          toast.info('No matches found');
        }
      } catch (error) {
        console.error('Search error:', error);
        toast.error('Search error: Invalid pattern');
      }
    } else {
      // Cross-file search
      console.log('🌐 Starting cross-file search...');
      try {
        const files = getFilesInScope();
        console.log('📁 Files in scope for search:', files.length);
        
        if (files.length === 0) {
          console.warn('⚠️ No files found in scope');
          toast.info('No files found in the selected scope');
          setCrossFileResults([]);
          setMatches([]);
          setTotalMatches(0);
          setCurrentMatchIndex(0);
          return;
        }
        
        const results = await searchInFiles(files);
        console.log('🎯 Search completed. Total results:', results.length);
        console.log('📊 Results breakdown:', results);
        
        setCrossFileResults(results);
        setMatches([]);
        setTotalMatches(results.length);
        setCurrentMatchIndex(0);
        
        if (results.length > 0) {
          console.log('✅ Search successful!');
          toast.success(`Found ${results.length} matches across ${files.length} files`);
        } else {
          console.log('ℹ️ No matches found');
          toast.info('No matches found');
        }
      } catch (error) {
        console.error('❌ Cross-file search error:', error);
        toast.error('Search failed. Please check your search pattern.');
      }
    }
  };

  // Jump to specific match and highlight it
  const jumpToMatch = (index: number, matchList = matches) => {
    if (!monacoEditor || matchList.length === 0 || index < 0 || index >= matchList.length) {
      return;
    }

    const match = matchList[index];
    const range = match.range;

    // Set selection and reveal the match
    monacoEditor.setSelection(range);
    monacoEditor.revealRangeInCenter(range);
    
    // Focus the editor
    monacoEditor.focus();
    
    setCurrentMatchIndex(index);
  };

  // Navigate to next match
  const goToNext = () => {
    if (searchScope === 'current') {
      if (matches.length === 0) return;
      const nextIndex = (currentMatchIndex + 1) % matches.length;
      jumpToMatch(nextIndex);
    } else {
      if (crossFileResults.length === 0) return;
      const nextIndex = (currentMatchIndex + 1) % crossFileResults.length;
      setCurrentMatchIndex(nextIndex);
      jumpToCrossFileResult(nextIndex);
    }
  };

  // Navigate to previous match
  const goToPrevious = () => {
    if (searchScope === 'current') {
      if (matches.length === 0) return;
      const prevIndex = currentMatchIndex === 0 ? matches.length - 1 : currentMatchIndex - 1;
      jumpToMatch(prevIndex);
    } else {
      if (crossFileResults.length === 0) return;
      const prevIndex = currentMatchIndex === 0 ? crossFileResults.length - 1 : currentMatchIndex - 1;
      setCurrentMatchIndex(prevIndex);
      jumpToCrossFileResult(prevIndex);
    }
  };

  // Jump to cross-file search result
  const jumpToCrossFileResult = async (index: number) => {
    const result = crossFileResults[index];
    if (!result) return;
    
    // If it's a different file, switch to it
    if (result.filePath !== currentFile?.path) {
      const targetFile = {
        path: result.filePath,
        name: result.fileName,
        content: '' // Will be loaded by the parent component
      };
      onFileSelect(targetFile);
      
      // Wait a bit for the file to load, then jump to the line
      setTimeout(() => {
        if (monacoEditor) {
          monacoEditor.revealLineInCenter(result.line);
          monacoEditor.setPosition({ lineNumber: result.line, column: result.column });
        }
      }, 300);
    } else {
      // Same file, just jump to the position
      if (monacoEditor) {
        monacoEditor.revealLineInCenter(result.line);
        monacoEditor.setPosition({ lineNumber: result.line, column: result.column });
      }
    }
  };

  // Replace current match
  const replaceCurrent = async () => {
    if (searchScope === 'current') {
      if (!monacoEditor || matches.length === 0 || currentMatchIndex < 0) {
        return;
      }

      const match = matches[currentMatchIndex];
      const range = match.range;

      // Perform the replacement
      monacoEditor.executeEdits('replace', [{
        range: range,
        text: replaceText
      }]);

      // Update file content
      const newContent = monacoEditor.getValue();
      updateFileContent(newContent);

      // Save file to server with retry mechanism
      let saveSuccess = false;
      let retryCount = 0;
      const maxRetries = 3;
      
      while (!saveSuccess && retryCount < maxRetries) {
        try {
          await onSave?.();
          toast.success('Replaced 1 occurrence and saved');
          saveSuccess = true;
        } catch (error) {
          retryCount++;
          console.error(`Save failed after replacement (attempt ${retryCount}):`, error);
          
          if (retryCount >= maxRetries) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            toast.success('Replaced 1 occurrence');
            toast.error(`Failed to save file after ${maxRetries} attempts: ${errorMessage}`);
            
            // Offer manual save option
            const shouldRetry = window.confirm(
              `File save failed: ${errorMessage}\n\nThe replacement was applied but not saved to server.\nWould you like to try saving again?`
            );
            
            if (shouldRetry) {
              try {
                await onSave?.();
                toast.success('File saved successfully');
                saveSuccess = true;
              } catch (retryError) {
                const retryErrorMessage = retryError instanceof Error ? retryError.message : 'Unknown error';
                toast.error(`Manual save also failed: ${retryErrorMessage}`);
              }
            }
          } else {
            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
          }
        }
      }

      // Re-perform search to update matches
      setTimeout(() => {
        performSearch();
      }, 100);
    } else {
      // Cross-file replacement
      if (crossFileResults.length === 0 || currentMatchIndex < 0) {
        return;
      }

      const result = crossFileResults[currentMatchIndex];
      
      // For cross-file replacement, we need to switch to the target file first
      if (result.filePath !== currentFile?.path) {
        toast.info('Please switch to the target file to perform replacement');
        jumpToCrossFileResult(currentMatchIndex);
        return;
      }

      // If we're already on the target file, perform replacement
      if (monacoEditor) {
        const model = monacoEditor.getModel();
        if (model) {
          const range = {
            startLineNumber: result.line,
            startColumn: result.column,
            endLineNumber: result.line,
            endColumn: result.column + result.matchText.length
          };

          monacoEditor.executeEdits('replace', [{
            range: range,
            text: replaceText
          }]);

          const newContent = monacoEditor.getValue();
          updateFileContent(newContent);

          // Save file to server with retry mechanism
          let saveSuccess = false;
          let retryCount = 0;
          const maxRetries = 3;
          
          while (!saveSuccess && retryCount < maxRetries) {
            try {
              await onSave?.();
              toast.success('Replaced 1 occurrence and saved');
              saveSuccess = true;
            } catch (error) {
              retryCount++;
              console.error(`Save failed after replacement (attempt ${retryCount}):`, error);
              
              if (retryCount >= maxRetries) {
                const errorMessage = error instanceof Error ? error.message : 'Unknown error';
                toast.success('Replaced 1 occurrence');
                toast.error(`Failed to save file after ${maxRetries} attempts: ${errorMessage}`);
                
                // Offer manual save option
                const shouldRetry = window.confirm(
                  `File save failed: ${errorMessage}\n\nThe replacement was applied but not saved to server.\nWould you like to try saving again?`
                );
                
                if (shouldRetry) {
                  try {
                    await onSave?.();
                    toast.success('File saved successfully');
                    saveSuccess = true;
                  } catch (retryError) {
                    const retryErrorMessage = retryError instanceof Error ? retryError.message : 'Unknown error';
                    toast.error(`Manual save also failed: ${retryErrorMessage}`);
                  }
                }
              } else {
                // Wait before retry
                await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
              }
            }
          }

          // Re-perform search to update matches
          setTimeout(() => {
            performSearch();
          }, 100);
        }
      }
    }
  };

  // Replace all matches
  const replaceAll = async () => {
    if (searchScope === 'current') {
      if (!monacoEditor || matches.length === 0) {
        return;
      }

      // Sort matches by position (descending) to avoid position shifts
      const sortedMatches = [...matches].sort((a, b) => {
        const aStart = a.range.startLineNumber * 1000000 + a.range.startColumn;
        const bStart = b.range.startLineNumber * 1000000 + b.range.startColumn;
        return bStart - aStart;
      });

      // Perform all replacements
      const edits = sortedMatches.map(match => ({
        range: match.range,
        text: replaceText
      }));

      monacoEditor.executeEdits('replace-all', edits);

      // Update file content
      const newContent = monacoEditor.getValue();
      updateFileContent(newContent);

      // Save file to server with retry mechanism
      let saveSuccess = false;
      let retryCount = 0;
      const maxRetries = 3;
      
      while (!saveSuccess && retryCount < maxRetries) {
        try {
          await onSave?.();
          toast.success(`Replaced ${matches.length} occurrences and saved`);
          saveSuccess = true;
        } catch (error) {
          retryCount++;
          console.error(`Save failed after replacement (attempt ${retryCount}):`, error);
          
          if (retryCount >= maxRetries) {
            const errorMessage = error instanceof Error ? error.message : 'Unknown error';
            toast.success(`Replaced ${matches.length} occurrences`);
            toast.error(`Failed to save file after ${maxRetries} attempts: ${errorMessage}`);
            
            // Offer manual save option
            const shouldRetry = window.confirm(
              `File save failed: ${errorMessage}\n\nThe replacement was applied but not saved to server.\nWould you like to try saving again?`
            );
            
            if (shouldRetry) {
              try {
                await onSave?.();
                toast.success('File saved successfully');
                saveSuccess = true;
              } catch (retryError) {
                const retryErrorMessage = retryError instanceof Error ? retryError.message : 'Unknown error';
                toast.error(`Manual save also failed: ${retryErrorMessage}`);
              }
            }
          } else {
            // Wait before retry
            await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
          }
        }
      }

      // Clear search results
      setMatches([]);
      setTotalMatches(0);
      setCurrentMatchIndex(0);
    } else {
      // Cross-file replace all
      if (crossFileResults.length === 0) {
        return;
      }

      // Group results by file path
      const fileGroups = crossFileResults.reduce((groups, result) => {
        if (!groups[result.filePath]) {
          groups[result.filePath] = [];
        }
        groups[result.filePath].push(result);
        return groups;
      }, {} as Record<string, typeof crossFileResults>);

      const filePaths = Object.keys(fileGroups);
      let totalReplacements = 0;
      let successfulSaves = 0;
      let failedSaves: string[] = [];

      // Show progress toast
      const progressToast = toast.loading(`Processing ${filePaths.length} files...`);

      try {
        // Process each file
        for (let i = 0; i < filePaths.length; i++) {
          const filePath = filePaths[i];
          const fileResults = fileGroups[filePath];
          
          // Update progress
          toast.loading(`Processing file ${i + 1}/${filePaths.length}: ${filePath.split('/').pop()}`, {
            id: progressToast
          });

          try {
            // Get file content
            const fileContent = await fileService.getFileContent(sessionId!, filePath);
            let content = fileContent.content;

            // Sort matches by position (descending) to avoid position shifts
            const sortedResults = [...fileResults].sort((a, b) => {
              const aStart = a.line * 1000000 + a.column;
              const bStart = b.line * 1000000 + b.column;
              return bStart - aStart;
            });

            // Apply replacements
            const lines = content.split('\n');
            for (const result of sortedResults) {
              const lineIndex = result.line - 1;
              if (lineIndex >= 0 && lineIndex < lines.length) {
                const line = lines[lineIndex];
                const beforeMatch = line.substring(0, result.column - 1);
                const afterMatch = line.substring(result.column - 1 + result.matchText.length);
                lines[lineIndex] = beforeMatch + replaceText + afterMatch;
              }
            }
            const newContent = lines.join('\n');

            // Save file with retry mechanism
            let saveSuccess = false;
            let retryCount = 0;
            const maxRetries = 3;
            
            while (!saveSuccess && retryCount < maxRetries) {
              try {
                await fileService.saveFileContent(sessionId!, filePath, newContent);
                saveSuccess = true;
                successfulSaves++;
                totalReplacements += fileResults.length;
                
                // If this is the current file, update the editor
                if (filePath === currentFile?.path && monacoEditor) {
                  monacoEditor.setValue(newContent);
                  updateFileContent(newContent);
                }
              } catch (error) {
                retryCount++;
                console.error(`Save failed for ${filePath} (attempt ${retryCount}):`, error);
                
                if (retryCount >= maxRetries) {
                  failedSaves.push(filePath);
                  console.error(`Failed to save ${filePath} after ${maxRetries} attempts`);
                } else {
                  // Wait before retry
                  await new Promise(resolve => setTimeout(resolve, 1000 * retryCount));
                }
              }
            }
          } catch (error) {
            console.error(`Error processing file ${filePath}:`, error);
            failedSaves.push(filePath);
          }
        }

        // Dismiss progress toast
        toast.dismiss(progressToast);

        // Show results
        if (successfulSaves > 0) {
          toast.success(`Successfully replaced ${totalReplacements} occurrences in ${successfulSaves} files`);
        }
        
        if (failedSaves.length > 0) {
          toast.error(`Failed to save ${failedSaves.length} files: ${failedSaves.map(f => f.split('/').pop()).join(', ')}`);
          
          // Offer retry for failed files
          const shouldRetry = window.confirm(
            `Some files failed to save:\n${failedSaves.join('\n')}\n\nWould you like to retry saving these files?`
          );
          
          if (shouldRetry) {
            // Retry failed saves
            for (const filePath of failedSaves) {
              try {
                const fileContent = await fileService.getFileContent(sessionId!, filePath);
                const fileResults = fileGroups[filePath];
                
                // Re-apply replacements
                let content = fileContent.content;
                const lines = content.split('\n');
                const sortedResults = [...fileResults].sort((a, b) => {
                  const aStart = a.line * 1000000 + a.column;
                  const bStart = b.line * 1000000 + b.column;
                  return bStart - aStart;
                });
                
                for (const result of sortedResults) {
                  const lineIndex = result.line - 1;
                  if (lineIndex >= 0 && lineIndex < lines.length) {
                    const line = lines[lineIndex];
                    const beforeMatch = line.substring(0, result.column - 1);
                    const afterMatch = line.substring(result.column - 1 + result.matchText.length);
                    lines[lineIndex] = beforeMatch + replaceText + afterMatch;
                  }
                }
                const newContent = lines.join('\n');
                
                await fileService.saveFileContent(sessionId!, filePath, newContent);
                toast.success(`Successfully saved ${filePath.split('/').pop()}`);
              } catch (retryError) {
                toast.error(`Retry failed for ${filePath.split('/').pop()}`);
              }
            }
          }
        }

        // Re-perform search to update matches
        setTimeout(() => {
          performSearch();
        }, 100);
        
      } catch (error) {
        toast.dismiss(progressToast);
        console.error('Cross-file replacement failed:', error);
        toast.error('Cross-file replacement failed');
      }
    }
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      if (matches.length > 0) {
        goToNext();
      } else {
        performSearch();
      }
    } else if (e.key === 'Enter' && e.shiftKey) {
      e.preventDefault();
      goToPrevious();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      onClose();
    }
  };

  // Auto-search when search text or scope changes
  useEffect(() => {
    if (searchText.trim()) {
      const timeoutId = setTimeout(() => {
        performSearch();
      }, 300);
      return () => clearTimeout(timeoutId);
    } else {
      setMatches([]);
      setTotalMatches(0);
      setCurrentMatchIndex(0);
      setCrossFileResults([]);
    }
  }, [searchText, isCaseSensitive, isWholeWord, isRegex, searchScope, monacoEditor]);

  if (!visible) return null;

  // Theme styles
  const cardBg = isDarkMode ? 'bg-gray-800' : 'bg-white';
  const borderColor = isDarkMode ? 'border-gray-600' : 'border-gray-200';
  const textColor = isDarkMode ? 'text-gray-200' : 'text-gray-900';
  const inputBg = isDarkMode ? 'bg-gray-700' : 'bg-white';
  const inputBorder = isDarkMode ? 'border-gray-600' : 'border-gray-300';
  const inputFocus = isDarkMode ? 'focus:border-blue-400' : 'focus:border-blue-500';
  const buttonBg = isDarkMode ? 'bg-blue-600' : 'bg-blue-500';
  const buttonHover = isDarkMode ? 'hover:bg-blue-500' : 'hover:bg-blue-600';
  const closeBtnHover = isDarkMode ? 'hover:bg-gray-700' : 'hover:bg-gray-100';
  const selectBg = isDarkMode ? 'bg-gray-700' : 'bg-white';
  const resultsBg = isDarkMode ? 'bg-gray-700' : 'bg-gray-50';
  const resultsHover = isDarkMode ? 'hover:bg-gray-600' : 'hover:bg-gray-100';
  const resultsActive = isDarkMode ? 'bg-blue-700 border-blue-500' : 'bg-blue-100 border-blue-300';
  const secondaryText = isDarkMode ? 'text-gray-400' : 'text-gray-500';

  return (
    <div className={`${cardBg} border-t ${borderColor} shadow-lg`}>
      <div className="px-4 py-3">
        {/* Header */}
        <div className="flex items-center justify-between mb-3">
          <h3 className={`text-sm font-medium ${textColor}`}>Find and Replace</h3>
          <button
            onClick={onClose}
            className={`p-1 ${closeBtnHover} rounded transition-colors`}
            title="Close (Esc)"
          >
            <X className={`w-4 h-4 ${secondaryText}`} />
          </button>
        </div>



        {/* Search and Replace Inputs */}
        <div className="space-y-3">
          {/* First Row: Search input + Find button + Replace and Find button */}
          <div className="flex items-center gap-2">
            <input
              ref={searchInputRef}
              type="text"
              value={searchText}
              onChange={(e) => setSearchText(e.target.value)}
              onKeyDown={handleKeyDown}
              className={`flex-1 px-2 py-1 text-sm border ${inputBorder} ${inputBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
              placeholder="Enter search text..."
            />
            <button
              onClick={() => {
                if (searchScope === 'current' && matches.length > 0) {
                  // Navigate based on search direction
                  if (searchDirection === 'down') {
                    goToNext();
                  } else {
                    goToPrevious();
                  }
                } else if (searchScope !== 'current' && crossFileResults.length > 0) {
                  // Navigate cross-file results based on direction
                  if (searchDirection === 'down') {
                    goToNext();
                  } else {
                    goToPrevious();
                  }
                } else {
                  // No results yet, perform new search
                  performSearch();
                }
              }}
              className={`px-4 py-1 text-sm ${buttonBg} text-white rounded ${buttonHover}`}
            >
              Find
            </button>
            <button
              onClick={replaceCurrent}
              disabled={(searchScope === 'current' && matches.length === 0) || (searchScope !== 'current' && crossFileResults.length === 0)}
              className={`px-3 py-1 text-sm ${isDarkMode ? 'bg-green-600 hover:bg-green-500' : 'bg-green-500 hover:bg-green-600'} text-white rounded disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              Replace and Find
            </button>
          </div>

          {/* Second Row: Replace input + Replace button + Replace all button */}
          <div className="flex items-center gap-2">
            <input
              type="text"
              value={replaceText}
              onChange={(e) => setReplaceText(e.target.value)}
              className={`flex-1 px-2 py-1 text-sm border ${inputBorder} ${inputBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
              placeholder="Enter replacement text..."
            />
            <button
              onClick={replaceCurrent}
              disabled={(searchScope === 'current' && matches.length === 0) || (searchScope !== 'current' && crossFileResults.length === 0)}
              className={`px-4 py-1 text-sm ${buttonBg} text-white rounded ${buttonHover} disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              Replace
            </button>
            <button
              onClick={replaceAll}
              disabled={(searchScope === 'current' && matches.length === 0) || (searchScope !== 'current' && crossFileResults.length === 0)}
              className={`px-4 py-1 text-sm ${isDarkMode ? 'bg-red-600 hover:bg-red-500' : 'bg-red-500 hover:bg-red-600'} text-white rounded disabled:opacity-50 disabled:cursor-not-allowed`}
            >
              Replace all
            </button>
          </div>

          {/* Third Row: Search scope select + Search mode select + Case sensitive span + Case sensitive input + Wrap label */}
          <div className="flex items-center gap-2">
            <select
              value={searchScope}
              onChange={(e) => setSearchScope(e.target.value as SearchScope)}
              className={`px-2 py-1 text-sm border ${inputBorder} ${selectBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
            >
              <option value="current">Current file</option>
              <option value="allText">All text files</option>
              <option value="allStyle">All style files</option>
            </select>
            <select
              value={isRegex ? 'regex' : isWholeWord ? 'fuzzy' : 'normal'}
              onChange={(e) => {
                const value = e.target.value;
                setIsRegex(value === 'regex');
                setIsWholeWord(value === 'fuzzy');
              }}
              className={`px-2 py-1 text-sm border ${inputBorder} ${selectBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
            >
              <option value="normal">Normal</option>
              <option value="fuzzy">Fuzzy</option>
              <option value="regex">Regex</option>
            </select>
            <select
              value={searchDirection}
              onChange={(e) => setSearchDirection(e.target.value as 'up' | 'down')}
              className={`px-2 py-1 text-sm border ${inputBorder} ${selectBg} ${textColor} rounded focus:outline-none ${inputFocus}`}
            >
              <option value="down">Down</option>
              <option value="up">Up</option>
            </select>
            <span className={textColor}>Case sensitive</span>
            <input
              type="checkbox"
              checked={isCaseSensitive}
              onChange={(e) => setIsCaseSensitive(e.target.checked)}
              className="rounded"
            />
            <label className={`flex items-center gap-1 cursor-pointer text-xs ${textColor}`}>
              <input
                type="checkbox"
                checked={isWrap}
                onChange={(e) => setIsWrap(e.target.checked)}
                className="rounded"
              />
              <span>Wrap</span>
            </label>
          </div>
        </div>

        {/* Cross-file search results */}
        {searchScope !== 'current' && crossFileResults.length > 0 && (
          <div className="mt-4 border-t border-gray-200 pt-3">
            <h4 className={`text-xs font-medium ${textColor} mb-2`}>
              Search Results ({crossFileResults.length} matches)
            </h4>
            <div className="max-h-48 overflow-y-auto space-y-1">
              {crossFileResults.map((result, index) => (
                <div
                  key={`${result.filePath}-${result.line}-${result.column}`}
                  className={`p-2 rounded text-xs cursor-pointer transition-colors ${
                    index === currentMatchIndex
                      ? `${resultsActive}`
                      : `${resultsBg} ${resultsHover} border border-transparent`
                  }`}
                  onClick={() => {
                    setCurrentMatchIndex(index);
                    jumpToCrossFileResult(index);
                  }}
                >
                  <div className="flex items-center gap-2 mb-1">
                    {result.fileName.match(/\.(css|scss|sass|less)$/i) ? (
                      <File className="w-3 h-3 text-purple-500" />
                    ) : (
                      <FileText className="w-3 h-3 text-blue-500" />
                    )}
                    <span className={`font-medium ${textColor}`}>{result.fileName}</span>
                    <span className={secondaryText}>Line {result.line}</span>
                  </div>
                  <div className={`${secondaryText} font-mono text-xs truncate`}>
                    {result.context}
                  </div>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
};

export default SearchReplaceCard;