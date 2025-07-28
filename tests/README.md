# AetherFolio E2E 自动化测试

本目录包含 AetherFolio 项目的端到端（E2E）自动化测试套件，使用 Playwright 框架实现。

## 测试覆盖范围

### 首页功能测试 (`e2e/homepage.test.js`)

- ✅ 验证首页正确加载并显示三个功能按钮
- ✅ 验证 "Merge EPUBs" 按钮的灰度状态和提示功能
- ✅ 验证 "Convert Files" 按钮的灰度状态和提示功能  
- ✅ 验证 "Edit EPUB" 按钮的可用状态和功能
- ✅ 验证主题切换功能
- ✅ 验证响应式设计

## 快速开始

### 1. 安装依赖

```bash
cd tests
npm install
```

### 2. 安装浏览器

```bash
npm run install:browsers
```

### 3. 启动前端开发服务器

确保前端开发服务器正在运行：

```bash
cd ../frontend
npm run dev
```

### 4. 运行测试

```bash
# 运行所有测试（无头模式）
npm test

# 运行测试（有头模式，可以看到浏览器）
npm run test:headed

# 调试模式运行测试
npm run test:debug

# 查看测试报告
npm run test:report
```

## 测试配置

- **基础URL**: `http://localhost:5174`
- **支持浏览器**: Chrome, Firefox, Safari, Edge
- **移动端测试**: Pixel 5, iPhone 12
- **失败时**: 自动截图和录制视频
- **重试机制**: CI环境中失败测试重试2次

## 测试结果

测试完成后，结果将保存在：
- HTML报告: `playwright-report/index.html`
- JSON结果: `test-results.json`
- 截图和视频: `test-results/` 目录

## 添加新测试

1. 在 `e2e/` 目录下创建新的 `.test.js` 文件
2. 使用 Playwright 的 `test` 和 `expect` API
3. 参考现有测试文件的结构和模式

## 故障排除

### 常见问题

1. **端口冲突**: 确保端口 5174 可用，或修改配置文件中的端口
2. **服务器未启动**: 确保前端开发服务器正在运行
3. **浏览器未安装**: 运行 `npm run install:browsers`

### 调试技巧

- 使用 `--headed` 参数查看浏览器操作
- 使用 `--debug` 参数进入调试模式
- 检查 `test-results/` 目录中的截图和视频

## 持续集成

测试套件已配置为在CI环境中自动运行，包括：
- 自动启动开发服务器
- 失败时重试机制
- 生成详细的测试报告

---

**注意**: 运行测试前请确保前端应用已正确构建并且开发服务器正在运行。