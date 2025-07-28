import { create } from 'zustand';

interface FileNode {
  name: string;
  path: string;
  type: 'file' | 'directory';
  children?: FileNode[];
}

interface CurrentFile {
  path: string;
  content: string;
  language: string;
}

interface AppState {
  // Upload state
  isUploadModalVisible: boolean;
  uploadProgress: number;
  
  // File management
  fileTree: FileNode[];
  currentFile: CurrentFile | null;
  selectedFilePath: string | null;
  
  // Metadata
  metadata: {
    title: string;
    author: string;
  };
  
  // Batch replace
  isBatchReplaceVisible: boolean;
  
  // Theme
  isDarkMode: boolean;
  
  // Actions
  setUploadModalVisible: (visible: boolean) => void;
  setUploadProgress: (progress: number) => void;
  setFileTree: (tree: FileNode[]) => void;
  setCurrentFile: (file: CurrentFile | null) => void;
  setSelectedFilePath: (path: string | null) => void;
  updateFileContent: (content: string) => void;
  setMetadata: (metadata: { title: string; author: string }) => void;
  setBatchReplaceVisible: (visible: boolean) => void;
  toggleTheme: () => void;
  
  // File operations
  selectFile: (file: FileNode) => void;
  renameFile: (oldPath: string, newName: string) => void;
  deleteFile: (path: string) => void;
  reorderFiles: (dragPath: string, hoverPath: string) => void;
  clearFileTree: () => void;
}

const useAppStore = create<AppState>((set, get) => ({
  // Initial state
  isUploadModalVisible: false,
  uploadProgress: 0,
  fileTree: [],
  currentFile: null,
  selectedFilePath: null,
  metadata: {
    title: '',
    author: ''
  },
  isBatchReplaceVisible: false,
  isDarkMode: false,
  
  // Actions
  setUploadModalVisible: (visible) => set({ isUploadModalVisible: visible }),
  
  setUploadProgress: (progress) => set({ uploadProgress: progress }),
  
  setFileTree: (tree) => set({ fileTree: tree }),
  
  setCurrentFile: (file) => set({ currentFile: file }),
  
  setSelectedFilePath: (path) => set({ selectedFilePath: path }),
  
  updateFileContent: (content) => {
    const { currentFile } = get();
    if (currentFile) {
      set({ currentFile: { ...currentFile, content } });
    }
  },
  
  setMetadata: (metadata) => set({ metadata }),
  
  setBatchReplaceVisible: (visible) => set({ isBatchReplaceVisible: visible }),
  
  toggleTheme: () => set((state) => ({ isDarkMode: !state.isDarkMode })),
  
  selectFile: (file) => {
    if (file.type === 'file') {
      // Determine language based on file extension
      const ext = file.name.toLowerCase().split('.').pop();
      let language = 'plaintext';
      
      switch (ext) {
        case 'html':
        case 'xhtml':
          language = 'html';
          break;
        case 'css':
          language = 'css';
          break;
        case 'js':
          language = 'javascript';
          break;
        case 'xml':
          language = 'xml';
          break;
        case 'json':
          language = 'json';
          break;
        case 'txt':
          language = 'plaintext';
          break;
        default:
          language = 'plaintext';
      }
      
      // Mock file content - in real app, this would fetch from server
      const mockContent = getMockFileContent(file.name, language);
      
      set({
        currentFile: {
          path: file.path,
          content: mockContent,
          language
        },
        selectedFilePath: file.path
      });
    }
  },

  renameFile: (oldPath, newName) => {
    const { fileTree, currentFile, selectedFilePath } = get();
    
    const renameInTree = (nodes: FileNode[]): FileNode[] => {
      return nodes.map(node => {
        if (node.path === oldPath) {
          const pathParts = oldPath.split('/');
          pathParts[pathParts.length - 1] = newName;
          const newPath = pathParts.join('/');
          
          return {
            ...node,
            name: newName,
            path: newPath
          };
        }
        
        if (node.children) {
          return {
            ...node,
            children: renameInTree(node.children)
          };
        }
        
        return node;
      });
    };
    
    const newFileTree = renameInTree(fileTree);
    const updates: Partial<AppState> = { fileTree: newFileTree };
    
    // Update current file path if it matches the renamed file
    if (currentFile && currentFile.path === oldPath) {
      const pathParts = oldPath.split('/');
      pathParts[pathParts.length - 1] = newName;
      const newPath = pathParts.join('/');
      
      updates.currentFile = {
        ...currentFile,
        path: newPath
      };
    }
    
    // Update selected file path if it matches
    if (selectedFilePath === oldPath) {
      const pathParts = oldPath.split('/');
      pathParts[pathParts.length - 1] = newName;
      updates.selectedFilePath = pathParts.join('/');
    }
    
    set(updates);
  },

  deleteFile: (path) => {
    const { fileTree, currentFile, selectedFilePath } = get();
    
    const deleteFromTree = (nodes: FileNode[]): FileNode[] => {
      return nodes.filter(node => {
        if (node.path === path) {
          return false;
        }
        
        if (node.children) {
          node.children = deleteFromTree(node.children);
        }
        
        return true;
      });
    };
    
    const newFileTree = deleteFromTree(fileTree);
    const updates: Partial<AppState> = { fileTree: newFileTree };
    
    // Clear current file if it was deleted
    if (currentFile && currentFile.path === path) {
      updates.currentFile = null;
    }
    
    // Clear selected file if it was deleted
    if (selectedFilePath === path) {
      updates.selectedFilePath = null;
    }
    
    set(updates);
  },

  reorderFiles: (dragPath, hoverPath) => {
    const { fileTree } = get();
    
    // Find the dragged item and its parent
    let draggedItem: FileNode | null = null;
    let draggedParent: FileNode[] | null = null;
    let draggedIndex = -1;
    
    const findDraggedItem = (nodes: FileNode[], parent: FileNode[] | null = null): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].path === dragPath) {
          draggedItem = nodes[i];
          draggedParent = parent || fileTree;
          draggedIndex = i;
          return true;
        }
        
        if (nodes[i].children && findDraggedItem(nodes[i].children, nodes[i].children)) {
          return true;
        }
      }
      return false;
    };
    
    // Find the hover target and its parent
    let hoverParent: FileNode[] | null = null;
    let hoverIndex = -1;
    
    const findHoverTarget = (nodes: FileNode[], parent: FileNode[] | null = null): boolean => {
      for (let i = 0; i < nodes.length; i++) {
        if (nodes[i].path === hoverPath) {
          hoverParent = parent || fileTree;
          hoverIndex = i;
          return true;
        }
        
        if (nodes[i].children && findHoverTarget(nodes[i].children, nodes[i].children)) {
          return true;
        }
      }
      return false;
    };
    
    findDraggedItem(fileTree);
    findHoverTarget(fileTree);
    
    if (draggedItem && draggedParent && hoverParent && draggedIndex !== -1 && hoverIndex !== -1) {
      // Remove from original position
      draggedParent.splice(draggedIndex, 1);
      
      // Insert at new position
      if (draggedParent === hoverParent && draggedIndex < hoverIndex) {
        hoverIndex--; // Adjust for removal
      }
      hoverParent.splice(hoverIndex, 0, draggedItem);
      
      // Save the new file order to localStorage for persistence
      const newFileTree = [...fileTree];
      localStorage.setItem('aetherfolio_file_order', JSON.stringify(newFileTree));
      
      set({ fileTree: newFileTree });
    }
  },

  clearFileTree: () => {
    set({
      fileTree: [],
      currentFile: null,
      selectedFilePath: null,
      metadata: { title: '', author: '' },
      isUploadModalVisible: false,
      uploadProgress: 0,
      isBatchReplaceVisible: false
    });
    localStorage.removeItem('aetherfolio_file_order');
  }
}));

// Mock file content generator
function getMockFileContent(fileName: string, language: string): string {
  // Special handling for TEXT files
  if (fileName.toLowerCase().endsWith('.txt')) {
    return `This is a sample text file: ${fileName}

You can edit this content using the AetherFolio editor.
This is a plain text file that supports:
- Direct text editing
- Search and replace functionality
- Batch replacement operations
- Export functionality

Lorem ipsum dolor sit amet, consectetur adipiscing elit. 
Sed do eiusmod tempor incididunt ut labore et dolore magna aliqua. 
Ut enim ad minim veniam, quis nostrud exercitation ullamco laboris.

You can add your own content here and use all the editing features available in AetherFolio.`;
  }
  
  switch (language) {
    case 'html':
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
    </div>
</body>
</html>`;
    
    case 'css':
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
}

p {
    text-align: justify;
    margin-bottom: 1em;
    text-indent: 1.5em;
}`;
    
    case 'xml':
      return `<?xml version="1.0" encoding="UTF-8"?>
<package xmlns="http://www.idpf.org/2007/opf" unique-identifier="BookId" version="3.0">
    <metadata xmlns:dc="http://purl.org/dc/elements/1.1/">
        <dc:title>Sample EPUB Book</dc:title>
        <dc:creator>Author Name</dc:creator>
        <dc:language>en</dc:language>
        <dc:identifier id="BookId">urn:uuid:12345</dc:identifier>
        <meta property="dcterms:modified">2024-01-01T00:00:00Z</meta>
    </metadata>
    <manifest>
        <item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
        <item id="chapter1" href="chapter1.xhtml" media-type="application/xhtml+xml"/>
        <item id="style" href="styles/style.css" media-type="text/css"/>
    </manifest>
    <spine>
        <itemref idref="chapter1"/>
    </spine>
</package>`;
    
    case 'plaintext':
      return `Sample content for ${fileName}

This is a plain text file.
You can edit this content using the AetherFolio editor.

Features available:
- Text editing
- Search and replace
- Batch operations
- Export functionality`;
    
    default:
      return `// ${fileName}
// This is a sample file content.
// You can edit this content using the AetherFolio editor.

Sample content for ${fileName}`;
  }
}

export default useAppStore;