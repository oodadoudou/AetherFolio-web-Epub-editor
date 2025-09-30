/**
 * Playwright配置文件
 * 用于端到端自动化测试
 */

const { defineConfig, devices } = require('@playwright/test');

module.exports = defineConfig({
  // 测试目录
  testDir: './tests/e2e',
  
  // 全局超时设置
  timeout: 60000,
  expect: {
    timeout: 10000
  },
  
  // 测试失败时的重试次数
  retries: process.env.CI ? 2 : 1,
  
  // 并行执行的worker数量
  workers: process.env.CI ? 1 : undefined,
  
  // 报告器配置
  reporter: [
    ['html', { outputFolder: 'test-results/html-report' }],
    ['json', { outputFile: 'test-results/results.json' }],
    ['junit', { outputFile: 'test-results/junit.xml' }],
    ['line']
  ],
  
  // 全局设置
  use: {
    // 基础URL
    baseURL: 'http://localhost:5174',
    
    // 浏览器上下文选项
    viewport: { width: 1280, height: 720 },
    
    // 忽略HTTPS错误
    ignoreHTTPSErrors: true,
    
    // 截图设置
    screenshot: 'only-on-failure',
    
    // 视频录制
    video: 'retain-on-failure',
    
    // 追踪设置
    trace: 'retain-on-failure',
    
    // 用户代理
    userAgent: 'AetherFolio-E2E-Test'
  },
  
  // 项目配置（不同浏览器）
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
    {
      name: 'firefox',
      use: { ...devices['Desktop Firefox'] },
    },
    {
      name: 'webkit',
      use: { ...devices['Desktop Safari'] },
    },
    // 移动端测试
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },
  ],
  
  // Web服务器配置
  webServer: {
    command: 'npm run dev',