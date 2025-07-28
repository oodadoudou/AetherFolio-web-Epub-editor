// @ts-check
const { defineConfig, devices } = require('@playwright/test');

/**
 * AetherFolio E2E 测试配置
 * @see https://playwright.dev/docs/test-configuration
 */
module.exports = defineConfig({
  testDir: './e2e',
  /* 并行运行测试 */
  fullyParallel: true,
  /* 在CI环境中失败时不重试 */
  forbidOnly: !!process.env.CI,
  /* 在CI环境中重试失败的测试 */
  retries: process.env.CI ? 2 : 0,
  /* 并行工作进程数量 */
  workers: process.env.CI ? 1 : undefined,
  /* 测试报告配置 */
  reporter: [
    ['html'],
    ['json', { outputFile: 'test-results.json' }]
  ],
  /* 全局测试配置 */
  use: {
    /* 基础URL */
    baseURL: 'http://localhost:5174',
    
    /* 在失败时收集追踪信息 */
    trace: 'on-first-retry',
    
    /* 截图配置 */
    screenshot: 'only-on-failure',
    
    /* 视频录制 */
    video: 'retain-on-failure',
    
    /* 等待网络空闲 */
    waitForLoadState: 'networkidle',
  },

  /* 配置不同浏览器的测试项目 */
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

    /* 移动端测试 */
    {
      name: 'Mobile Chrome',
      use: { ...devices['Pixel 5'] },
    },
    {
      name: 'Mobile Safari',
      use: { ...devices['iPhone 12'] },
    },

    /* 品牌浏览器测试 */
    {
      name: 'Microsoft Edge',
      use: { ...devices['Desktop Edge'], channel: 'msedge' },
    },
    {
      name: 'Google Chrome',
      use: { ...devices['Desktop Chrome'], channel: 'chrome' },
    },
  ],

  /* 在测试开始前启动本地开发服务器 */
  webServer: {
    command: 'cd ../frontend && npm run dev',
    url: 'http://localhost:5174',
    reuseExistingServer: !process.env.CI,
    timeout: 120 * 1000,
  },
});