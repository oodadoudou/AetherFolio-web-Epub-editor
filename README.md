# AetherFolio - Modern EPUB Editor

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/React-18.3.1-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108.0-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6.2-blue.svg)](https://www.typescriptlang.org/)

> 🌏 [中文版本](./README_CN.md) | English

A modern, powerful EPUB editor with advanced editing capabilities, batch text replacement, and real-time preview features.

## ✨ Features

### 📚 Core Functions
- **EPUB Editing** - Upload and edit EPUB files with advanced text processing
- **Batch Replace** - Powerful batch text replacement with regex support
- **Multi-format Support** - Edit HTML, CSS, XML, TXT and other file formats
- **Search & Replace** - Full-text search and replace across multiple files
- **Real-time Preview** - Live preview of editing results
- **Theme Toggle** - Support for light and dark themes

### 🎨 Interface
- **Modern UI** - Clean design based on Ant Design with green theme
- **Responsive** - Works on different screen sizes
- **Three-panel Layout** - File browser, editor, and preview panels
- **Quick Navigation** - Easy switching between editing and home interface

## 🚀 Quick Start

### Prerequisites
- Node.js 18+
- Python 3.12+
- npm or pnpm

### Installation

1. **Clone the repository**
```bash
git clone <repository-url>
cd AetherFolio-web-Epub-editor
```

2. **Install frontend dependencies**
```bash
npm install
```

3. **Install backend dependencies**
```bash
cd backend
pip install -r requirements.txt
```

### Running the Application

1. **Start the backend server**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

2. **Start the frontend development server**
```bash
npm run dev
```

3. **Open your browser**
   - Frontend: http://localhost:5173
   - Backend API: http://localhost:8000

## 📖 How to Use

### Main Interface
After starting the application, you'll see three main function modules:

1. **📝 Edit EPUB** - Upload and edit EPUB files
   - Click to enter file editing mode
   - Browse file tree structure
   - Real-time code editing and preview

2. **🔄 Merge Files** - Combine multiple files (Coming Soon)
3. **🔄 Convert Files** - Format conversion (Coming Soon)

### Editing Features
- **File Browser** - Left panel shows EPUB file structure
- **Code Editor** - Center panel for editing file content
- **Preview Panel** - Right panel for real-time preview
- **Search & Replace** - Support for single file and batch operations
- **Export** - Download edited EPUB files

## 🛠 Tech Stack

### Frontend
- React 18 + TypeScript
- Vite (Build tool)
- Ant Design (UI components)
- Tailwind CSS (Styling)
- Monaco Editor (Code editor)
- Zustand (State management)

### Backend
- FastAPI (Python web framework)
- Pydantic (Data validation)
- EbookLib (EPUB processing)
- BeautifulSoup4 (HTML parsing)
- SQLAlchemy (Database ORM)

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## 📞 Support

If you encounter any issues or have feature suggestions, please create an issue.
