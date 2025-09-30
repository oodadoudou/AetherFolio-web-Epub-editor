# AetherFolio - 现代化 EPUB 编辑器

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![React](https://img.shields.io/badge/React-18.3.1-blue.svg)](https://reactjs.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.108.0-green.svg)](https://fastapi.tiangolo.com/)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6.2-blue.svg)](https://www.typescriptlang.org/)

> 中文 | [English](./README.md)

一个现代化、功能强大的 EPUB 编辑器，具有高级编辑功能、批量文本替换和实时预览特性。

## ✨ 功能特性

### 📚 核心功能
- **EPUB 编辑** - 上传和编辑 EPUB 文件，支持高级文本处理
- **批量替换** - 强大的批量文本替换功能，支持正则表达式
- **多格式支持** - 编辑 HTML、CSS、XML、TXT 等多种文件格式
- **搜索替换** - 全文搜索和替换，支持跨文件操作
- **实时预览** - 编辑结果实时预览
- **主题切换** - 支持明暗主题切换

### 🎨 界面特性
- **现代化界面** - 基于 Ant Design 的绿色主题设计
- **响应式设计** - 支持不同屏幕尺寸
- **三面板布局** - 文件浏览器、编辑器和预览面板
- **快速导航** - 编辑模式和主界面之间轻松切换

## 🚀 快速开始

### 环境要求
- Node.js 18+
- Python 3.12+
- npm 或 pnpm

### 安装

1. **克隆仓库**
```bash
git clone <repository-url>
cd AetherFolio-web-Epub-editor
```

2. **安装前端依赖**
```bash
npm install
```

3. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

### 运行应用

1. **启动后端服务器**
```bash
cd backend
uvicorn main:app --reload --port 8000
```

2. **启动前端开发服务器**
```bash
npm run dev
```

3. **打开浏览器**
   - 前端：http://localhost:5173
   - 后端 API：http://localhost:8000

## 📖 使用指南

### 主界面
启动应用后，您将看到三个主要功能模块：

1. **📝 编辑 EPUB** - 上传和编辑 EPUB 文件
   - 点击进入文件编辑模式
   - 浏览文件树结构
   - 实时代码编辑和预览

2. **🔄 合并文件** - 合并多个文件（即将推出）
3. **🔄 转换文件** - 格式转换（即将推出）

### 编辑功能
- **文件浏览器** - 左侧面板显示 EPUB 文件结构
- **代码编辑器** - 中间面板用于编辑文件内容
- **预览面板** - 右侧面板实时预览效果
- **搜索替换** - 支持单文件和批量操作
- **导出功能** - 下载编辑后的 EPUB 文件

## 🛠 技术栈

### 前端
- React 18 + TypeScript
- Vite（构建工具）
- Ant Design（UI 组件库）
- Tailwind CSS（样式框架）
- Monaco Editor（代码编辑器）
- Zustand（状态管理）

### 后端
- FastAPI（Python Web 框架）
- Pydantic（数据验证）
- EbookLib（EPUB 处理）
- BeautifulSoup4（HTML 解析）
- SQLAlchemy（数据库 ORM）

## 📝 许可证

本项目采用 MIT 许可证 - 查看 [LICENSE](LICENSE) 文件了解详情。

## 🤝 贡献

欢迎贡献代码！请先阅读我们的贡献指南。

## 📞 支持

如果您遇到任何问题或有功能建议，请创建一个 issue。