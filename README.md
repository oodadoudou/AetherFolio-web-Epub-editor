# AetherFolio - EPUB Editor

AetherFolio 是一个现代化的 EPUB 编辑器，具有强大的编辑、合并和转换功能。

## 功能特性

### 核心功能
- 📚 **EPUB 编辑**: 上传和编辑 EPUB 文件，支持高级文本处理
- 🔄 **批量替换**: 强大的批量文本替换功能，支持正则表达式
- 📝 **文本编辑**: 支持多种文件格式的编辑（HTML、CSS、XML、TXT等）
- 🔍 **搜索功能**: 全文搜索和替换，支持跨文件操作
- 📊 **预览功能**: 实时预览编辑结果
- 🌓 **主题切换**: 支持明暗主题切换

### 界面特性
- 🎨 **现代化界面**: 基于 Ant Design 的绿色主题设计
- 📱 **响应式设计**: 支持不同屏幕尺寸
- 🚀 **快速操作**: 直观的主界面，包含 Edit、Merge、Convert 三大功能模块
- 🏠 **便捷导航**: 支持退出编辑模式，返回主界面

## 技术栈

### 前端
- React 18 + TypeScript
- Vite (构建工具)
- Ant Design (UI 组件库)
- Tailwind CSS (样式框架)
- Monaco Editor (代码编辑器)
- Zustand (状态管理)

### 后端
- FastAPI (Python Web 框架)
- Pydantic (数据验证)
- Asyncio (异步处理)
- 文件处理和 EPUB 解析

## 快速开始

### 环境要求
- Node.js 18+
- Python 3.8+
- npm 或 pnpm

### 安装和运行

1. **克隆项目**
```bash
git clone <repository-url>
cd AetherFolio-web-Epub-editor
```

2. **安装前端依赖**
```bash
npm install
# 或
pnpm install
```

3. **安装后端依赖**
```bash
cd backend
pip install -r requirements.txt
```

4. **启动开发服务器**

前端开发服务器：
```bash
npm run dev
# 访问 http://localhost:5173
```

后端服务器：
```bash
cd backend
uvicorn main:app --reload --port 8000
# API 访问 http://localhost:8000
```

## 使用指南

### 主界面功能

启动应用后，您将看到包含三个主要功能模块的主界面：

1. **📝 Edit EPUB**: 上传和编辑 EPUB 文件
   - 点击进入文件编辑模式
   - 支持文件树浏览
   - 实时代码编辑和预览

2. **🔄 Merge EPUBs**: 合并多个 EPUB 文件
   - 将多个 EPUB 文件合并为一个
   - 保持文件结构和元数据

3. **🔄 Convert Files**: 文件格式转换
   - 支持多种电子书格式转换
   - 批量处理功能

### 编辑模式功能

- **文件浏览器**: 左侧面板显示 EPUB 文件结构
- **代码编辑器**: 中间面板进行文件内容编辑
- **预览面板**: 右侧面板实时预览效果
- **搜索替换**: 支持单文件和批量搜索替换
- **退出编辑**: 点击工具栏的主页图标返回主界面

## 更新记录

### v1.2.0 (2024-12-19) ✅ 已完成

#### 🎨 界面优化
- **新增主界面设计**: 重新设计启动界面，包含 Edit、Merge、Convert 三大功能模块
- **优化用户体验**: 每次启动都显示主界面，方便用户快速选择功能和测试
- **添加退出编辑功能**: 在编辑模式下可以快速返回主界面
- **改进响应式设计**: 支持不同屏幕尺寸的自适应布局
- **绿色主题优化**: 统一使用绿色主题，提升视觉一致性

#### 🔧 技术改进
- **状态管理优化**: 添加 `clearFileTree` 方法，支持清除编辑状态
- **组件结构优化**: 改进 Toolbar 组件，支持条件显示退出按钮
- **图标库扩展**: 新增 EditOutlined、MergeOutlined、SwapOutlined、HomeOutlined 等功能图标
- **文件树初始化**: 默认为空数组，确保每次启动显示主界面

#### 🐛 问题修复
- **修复文件树初始化问题**: 解决启动时的语法错误
- **优化热更新**: 改进开发环境的实时更新体验
- **修复状态管理**: 确保退出编辑模式时正确清除所有相关状态

### v1.1.0 (2024-12-XX)
- ✅ 完成批量替换功能增强
- ✅ 支持 TEXT 格式文件批量替换
- ✅ 生成详细的 HTML 替换报告
- ✅ 扩展文件类型支持

## 开发配置

### ESLint 配置扩展

If you are developing a production application, we recommend updating the configuration to enable type-aware lint rules:

```js
export default tseslint.config({
  extends: [
    // Remove ...tseslint.configs.recommended and replace with this
    ...tseslint.configs.recommendedTypeChecked,
    // Alternatively, use this for stricter rules
    ...tseslint.configs.strictTypeChecked,
    // Optionally, add this for stylistic rules
    ...tseslint.configs.stylisticTypeChecked,
  ],
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```

You can also install [eslint-plugin-react-x](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-x) and [eslint-plugin-react-dom](https://github.com/Rel1cx/eslint-react/tree/main/packages/plugins/eslint-plugin-react-dom) for React-specific lint rules:

```js
// eslint.config.js
import reactX from 'eslint-plugin-react-x'
import reactDom from 'eslint-plugin-react-dom'

export default tseslint.config({
  extends: [
    // other configs...
    // Enable lint rules for React
    reactX.configs['recommended-typescript'],
    // Enable lint rules for React DOM
    reactDom.configs.recommended,
  ],
  languageOptions: {
    // other options...
    parserOptions: {
      project: ['./tsconfig.node.json', './tsconfig.app.json'],
      tsconfigRootDir: import.meta.dirname,
    },
  },
})
```
