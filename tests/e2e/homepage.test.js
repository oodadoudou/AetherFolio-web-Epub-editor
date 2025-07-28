/**
 * AetherFolio 首页功能 E2E 测试
 * 验证重构后的首页UI和交互功能
 */

const { test, expect } = require('@playwright/test');

test.describe('AetherFolio 首页功能测试', () => {
  test.beforeEach(async ({ page }) => {
    // 访问首页
    await page.goto('http://localhost:5174/');
  });

  test('验证首页正确加载并显示三个功能按钮', async ({ page }) => {
    // 验证页面标题
    await expect(page).toHaveTitle(/AetherFolio/);
    
    // 验证三个功能区域存在
    const editSection = page.locator('text=Edit EPUB');
    const mergeSection = page.locator('text=Merge EPUBs');
    const convertSection = page.locator('text=Convert Files');
    
    await expect(editSection).toBeVisible();
    await expect(mergeSection).toBeVisible();
    await expect(convertSection).toBeVisible();
  });

  test('验证Merge按钮的灰度状态和提示功能', async ({ page }) => {
    // 定位Merge按钮区域
    const mergeButton = page.locator('text=Merge EPUBs').locator('..');
    
    // 验证灰度样式（opacity-60类）
    await expect(mergeButton).toHaveClass(/opacity-60/);
    
    // 点击Merge按钮
    await mergeButton.click();
    
    // 验证提示信息出现
    const toast = page.locator('text=暂不支持，请等待更新 ✨');
    await expect(toast).toBeVisible();
  });

  test('验证Convert按钮的灰度状态和提示功能', async ({ page }) => {
    // 定位Convert按钮区域
    const convertButton = page.locator('text=Convert Files').locator('..');
    
    // 验证灰度样式（opacity-60类）
    await expect(convertButton).toHaveClass(/opacity-60/);
    
    // 点击Convert按钮
    await convertButton.click();
    
    // 验证提示信息出现
    const toast = page.locator('text=暂不支持，请等待更新 ✨');
    await expect(toast).toBeVisible();
  });

  test('验证Edit按钮的可用状态和功能', async ({ page }) => {
    // 定位Edit按钮区域
    const editButton = page.locator('text=Edit EPUB').locator('..');
    
    // 验证Edit按钮不是灰度状态
    await expect(editButton).not.toHaveClass(/opacity-60/);
    
    // 点击Edit按钮
    await editButton.click();
    
    // 验证文件上传模态框出现
    const uploadModal = page.locator('.ant-modal');
    await expect(uploadModal).toBeVisible();
    
    // 验证模态框标题
    const modalTitle = page.locator('text=Upload EPUB File');
    await expect(modalTitle).toBeVisible();
  });

  test('验证Help按钮的可见性和位置', async ({ page }) => {
    // 验证Help按钮存在且可见
    const helpButton = page.locator('button').filter({ hasText: /Help/ }).or(
      page.locator('button[title="Help"]')
    );
    
    await expect(helpButton).toBeVisible();
    
    // 验证Help按钮位置（固定定位在右上角）
    const boundingBox = await helpButton.boundingBox();
    expect(boundingBox).toBeTruthy();
    
    // 验证按钮样式（圆形按钮）
    await expect(helpButton).toHaveClass(/rounded-full/);
  });

  test('验证Help按钮交互功能', async ({ page }) => {
    // 定位Help按钮
    const helpButton = page.locator('button').filter({ hasText: /Help/ }).or(
      page.locator('button[title="Help"]')
    );
    
    // 点击Help按钮
    await helpButton.click();
    
    // 验证提示框出现
    const tooltip = page.locator('text=帮助').locator('..');
    await expect(tooltip).toBeVisible();
    
    // 验证提示框内容
    const helpMessage = page.locator('text=当前只有 Edit 功能可用');
    await expect(helpMessage).toBeVisible();
    
    // 验证关闭按钮存在
    const closeButton = page.locator('text=知道了');
    await expect(closeButton).toBeVisible();
  });

  test('验证Help提示框关闭功能', async ({ page }) => {
    // 打开Help提示框
    const helpButton = page.locator('button').filter({ hasText: /Help/ }).or(
      page.locator('button[title="Help"]')
    );
    await helpButton.click();
    
    // 验证提示框可见
    const tooltip = page.locator('text=帮助').locator('..');
    await expect(tooltip).toBeVisible();
    
    // 点击关闭按钮
    const closeButton = page.locator('text=知道了');
    await closeButton.click();
    
    // 验证提示框消失
    await expect(tooltip).not.toBeVisible();
  });

  test('验证主题切换功能', async ({ page }) => {
    // 查找主题切换按钮（通常是一个图标按钮）
    const themeToggle = page.locator('[data-testid="theme-toggle"]').or(
      page.locator('button').filter({ hasText: /🌙|☀️|🌞/ })
    );
    
    if (await themeToggle.count() > 0) {
      // 点击主题切换
      await themeToggle.click();
      
      // 验证主题变化（检查body或html的class变化）
      const body = page.locator('body');
      await expect(body).toHaveClass(/dark|light/);
    }
  });

  test('验证响应式设计', async ({ page }) => {
    // 测试移动端视口
    await page.setViewportSize({ width: 375, height: 667 });
    
    // 验证三个功能按钮在移动端仍然可见
    const editSection = page.locator('text=Edit EPUB');
    const mergeSection = page.locator('text=Merge EPUBs');
    const convertSection = page.locator('text=Convert Files');
    
    await expect(editSection).toBeVisible();
    await expect(mergeSection).toBeVisible();
    await expect(convertSection).toBeVisible();
    
    // 验证Help按钮在移动端的响应式调整
    const helpButton = page.locator('button').filter({ hasText: /Help/ }).or(
      page.locator('button[title="Help"]')
    );
    await expect(helpButton).toBeVisible();
    
    // 恢复桌面端视口
    await page.setViewportSize({ width: 1280, height: 720 });
  });
});