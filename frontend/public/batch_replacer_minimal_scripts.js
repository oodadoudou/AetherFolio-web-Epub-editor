// 现代极简风格 - Batch Replacer 报告交互脚本

// 全局状态管理
const AppState = {
  expandedRules: new Set(),
  animationQueue: [],
  isScrolling: false,
  rulesListExpanded: false
};

// 规则数据 (模拟数据，实际应用中从服务器获取)
const rulesData = [
  {
    id: 0,
    from: '大哥',
    to: '哥',
    count: 19,
    instances: [
      {
        id: 1,
        context: '对话场景',
        original: '「要是有这种疯子存在，我管他叫一辈子<mark class="highlight-original">大哥</mark>!人总得有点盼头吧，您这说的什么话。真是的!」',
        modified: '「要是有这种疯子存在，我管他叫一辈子<mark class="highlight-modified">哥</mark>!人总得有点盼头吧，您这说的什么话。真是的!」'
      },
      {
        id: 2,
        context: '内心独白',
        original: '「就当是<mark class="highlight-original">大哥</mark>说的话吧。很古板的那种<mark class="highlight-original">大哥</mark>。」',
        modified: '「就当是<mark class="highlight-modified">哥</mark>说的话吧。很古板的那种<mark class="highlight-modified">哥</mark>。」'
      }
    ]
  },
  {
    id: 1,
    from: '自渎',
    to: '自慰',
    count: 4,
    instances: [
      {
        id: 1,
        context: '内心描述',
        original: '包含<mark class="highlight-original">自渎</mark>的文本内容...',
        modified: '包含<mark class="highlight-modified">自慰</mark>的文本内容...'
      }
    ]
  },
  {
    id: 2,
    from: '您一定能养好',
    to: '他一定能养好',
    count: 1,
    instances: [
      {
        id: 1,
        context: '对话场景',
        original: '「<mark class="highlight-original">您一定能养好</mark>的，不用担心。」',
        modified: '「<mark class="highlight-modified">他一定能养好</mark>的，不用担心。」'
      }
    ]
  },
  {
    id: 3,
    from: '突然就干架了',
    to: '突然就吵架了',
    count: 1,
    instances: [
      {
        id: 1,
        context: '情节描述',
        original: '两人在餐厅里<mark class="highlight-original">突然就干架了</mark>，引起了其他客人的注意。',
        modified: '两人在餐厅里<mark class="highlight-modified">突然就吵架了</mark>，引起了其他客人的注意。'
      }
    ]
  }
];

// DOM 加载完成后初始化
document.addEventListener('DOMContentLoaded', function() {
  initializeApp();
});

// 应用初始化
function initializeApp() {
  setupScrollProgress();
  setupAnimations();
  setupEventListeners();
  
  // 延迟启动动画
  setTimeout(() => {
    triggerEntryAnimations();
  }, 100);
}

// 设置滚动进度指示器
function setupScrollProgress() {
  const progressLine = document.getElementById('scroll-progress-line');
  
  window.addEventListener('scroll', throttle(() => {
    const scrollTop = window.pageYOffset;
    const docHeight = document.documentElement.scrollHeight - window.innerHeight;
    const scrollPercent = (scrollTop / docHeight) * 100;
    
    progressLine.style.width = `${Math.min(scrollPercent, 100)}%`;
  }, 10));
}

// 设置入场动画
function setupAnimations() {
  const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        const element = entry.target;
        const animationType = element.dataset.animate;
        
        if (animationType && !element.classList.contains('animated')) {
          element.classList.add('animated');
          triggerAnimation(element, animationType);
        }
      }
    });
  }, {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
  });
  
  // 观察所有需要动画的元素
  document.querySelectorAll('[data-animate]').forEach(el => {
    observer.observe(el);
  });
}

// 显示替换规则模态窗口
function showRulesModal() {
  const modalOverlay = document.getElementById('rules-modal-overlay');
  if (modalOverlay) {
    modalOverlay.style.display = 'flex';
    // 添加显示动画
    setTimeout(() => {
      modalOverlay.classList.add('show');
    }, 10);
    
    // 阻止背景滚动
    document.body.style.overflow = 'hidden';
  }
}

// 关闭替换规则模态窗口
function closeRulesModal() {
  const modalOverlay = document.getElementById('rules-modal-overlay');
  if (modalOverlay) {
    modalOverlay.classList.remove('show');
    // 延迟隐藏以完成动画
    setTimeout(() => {
      modalOverlay.style.display = 'none';
      // 恢复背景滚动
      document.body.style.overflow = '';
    }, 300);
  }
}

// 跳转到规则并关闭模态窗口
function jumpToRuleAndClose(ruleId) {
  closeRulesModal();
  // 延迟跳转以确保模态窗口关闭动画完成
  setTimeout(() => {
    jumpToRule(ruleId);
  }, 300);
}

// 设置事件监听器
function setupEventListeners() {
  // 键盘快捷键
  document.addEventListener('keydown', handleKeyboardShortcuts);
  
  // 窗口大小变化
  window.addEventListener('resize', debounce(handleResize, 250));
}

// 触发入场动画
function triggerEntryAnimations() {
  const statCards = document.querySelectorAll('.stat-card[data-animate="slide-up"]');
  
  statCards.forEach((card, index) => {
    setTimeout(() => {
      card.style.animationDelay = `${index * 0.1}s`;
      card.classList.add('animated');
    }, index * 100);
  });
}

// 规则组展开/折叠
function toggleRuleGroup(ruleId) {
  const ruleGroup = document.querySelector(`[data-rule-id="${ruleId}"]`);
  const content = document.getElementById(`content-${ruleId}`);
  const toggleIcon = document.getElementById(`toggle-${ruleId}`);
  
  if (!ruleGroup || !content) return;
  
  const isExpanded = AppState.expandedRules.has(ruleId);
  
  if (isExpanded) {
    // 折叠
    AppState.expandedRules.delete(ruleId);
    ruleGroup.classList.remove('expanded');
    content.style.maxHeight = '0';
  } else {
    // 展开
    AppState.expandedRules.add(ruleId);
    ruleGroup.classList.add('expanded');
    
    // 计算内容高度
    const scrollHeight = content.scrollHeight;
    content.style.maxHeight = `${scrollHeight}px`;
    
    // 触发实例卡片动画
    setTimeout(() => {
      const instanceCards = content.querySelectorAll('.instance-card');
      instanceCards.forEach((card, index) => {
        setTimeout(() => {
          card.style.animationDelay = `${index * 0.1}s`;
          card.classList.add('animated');
        }, index * 50);
      });
    }, 300);
  }
  
  // 平滑滚动到规则组
  if (!isExpanded) {
    setTimeout(() => {
      ruleGroup.scrollIntoView({
        behavior: 'smooth',
        block: 'start'
      });
    }, 100);
  }
}

// 跳转到指定规则
function jumpToRule(ruleId) {
  const ruleGroup = document.querySelector(`[data-rule-id="${ruleId}"]`);
  if (!ruleGroup) return;
  
  // 如果规则组未展开，先展开它
  if (!AppState.expandedRules.has(ruleId)) {
    toggleRuleGroup(ruleId);
  }
  
  // 平滑滚动到规则组
  setTimeout(() => {
    ruleGroup.scrollIntoView({
      behavior: 'smooth',
      block: 'start',
      inline: 'nearest'
    });
    
    // 高亮效果
    ruleGroup.style.transform = 'scale(1.02)';
    ruleGroup.style.boxShadow = '0 8px 25px rgba(16, 185, 129, 0.15)';
    ruleGroup.style.borderColor = 'var(--primary-green)';
    
    setTimeout(() => {
      ruleGroup.style.transform = '';
      ruleGroup.style.boxShadow = '';
      ruleGroup.style.borderColor = '';
    }, 1500);
  }, AppState.expandedRules.has(ruleId) ? 0 : 500);
}

// 回到顶部
function scrollToTop() {
  window.scrollTo({
    top: 0,
    behavior: 'smooth'
  });
}

// 导出报告
function exportReport() {
  // 创建导出动画
  const button = event.target;
  button.style.transform = 'scale(0.9)';
  
  setTimeout(() => {
    button.style.transform = '';
    
    // 生成完整的HTML报告
    const htmlContent = generateCompleteHTMLReport();
    
    // 下载HTML文件
    const blob = new Blob([htmlContent], {
      type: 'text/html;charset=utf-8'
    });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'batch-replacer-report.html';
    a.click();
    URL.revokeObjectURL(url);
    
    // 显示成功提示
    showNotification('HTML报告已导出', 'success');
  }, 150);
}

// 生成完整的HTML报告
function generateCompleteHTMLReport() {
  // 获取CSS样式
  const cssContent = getCSSContent();
  
  // 获取当前页面的主要内容
  const title = document.querySelector('.file-title').textContent;
  const timestamp = new Date().toLocaleString('zh-CN');
  
  // 获取模态窗口HTML
  const modalOverlay = document.getElementById('rules-modal-overlay');
  const modalHTML = modalOverlay ? modalOverlay.outerHTML : '';
  
  // 生成HTML内容
  const htmlTemplate = `<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>${title} - 智能替换报告</title>
    <style>
${cssContent}
    </style>
</head>
<body>
    <div class="container">
        <!-- 顶部导航栏 -->
        <nav class="top-nav">
            <div class="nav-content">
                <div class="logo">
                    <div class="logo-icon"></div>
                    <span>智能替换报告</span>
                </div>
                <div class="nav-actions">
                    <button class="nav-btn" onclick="showOverview()">概览</button>
                    <button class="nav-btn" onclick="showRulesModal()">替换规则</button>
                    <button class="nav-btn active" onclick="showComparisons()">对比详情</button>
                    <span class="export-info">导出时间: ${timestamp}</span>
                </div>
            </div>
        </nav>

        <!-- 文件信息头部 -->
        <header class="file-header">
            <div class="file-info">
                <h1 class="file-title">${title}</h1>
                <div class="file-meta">
                    <span class="meta-item">导出时间: ${timestamp}</span>
                    <span class="meta-divider">|</span>
                    <span class="meta-item">报告类型: 智能替换分析</span>
                </div>
            </div>
        </header>

        ${document.querySelector('.stats-overview').outerHTML}
        ${document.querySelector('.main-content').outerHTML}
    </div>
    
    <!-- 模态窗口 -->
    ${modalHTML}

    <script>
        // 简化的交互脚本（仅用于导出的HTML）
        function showOverview() {
            document.querySelector('.stats-overview').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
        
        function showComparisons() {
            document.querySelector('.main-content').scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
        
        // 显示替换规则模态窗口
        function showRulesModal() {
            const modalOverlay = document.getElementById('rules-modal-overlay');
            if (modalOverlay) {
                modalOverlay.style.display = 'flex';
                setTimeout(() => {
                    modalOverlay.classList.add('show');
                }, 10);
                document.body.style.overflow = 'hidden';
            }
        }
        
        // 关闭替换规则模态窗口
        function closeRulesModal() {
            const modalOverlay = document.getElementById('rules-modal-overlay');
            if (modalOverlay) {
                modalOverlay.classList.remove('show');
                setTimeout(() => {
                    modalOverlay.style.display = 'none';
                    document.body.style.overflow = '';
                }, 300);
            }
        }
        
        // 跳转到规则并关闭模态窗口
        function jumpToRuleAndClose(ruleId) {
            closeRulesModal();
            setTimeout(() => {
                jumpToRule(ruleId);
            }, 300);
        }
        
        // 跳转到指定规则
        function jumpToRule(ruleId) {
            const ruleGroup = document.querySelector('[data-rule-id="' + ruleId + '"]');
            if (ruleGroup) {
                ruleGroup.scrollIntoView({
                    behavior: 'smooth',
                    block: 'start'
                });
                
                // 如果规则组未展开，先展开它
                const content = document.getElementById('content-' + ruleId);
                if (content && (!content.style.maxHeight || content.style.maxHeight === '0px')) {
                    toggleRuleGroup(ruleId);
                }
                
                // 高亮效果
                ruleGroup.style.transform = 'scale(1.02)';
                ruleGroup.style.boxShadow = '0 8px 25px rgba(16, 185, 129, 0.15)';
                ruleGroup.style.borderColor = 'var(--primary-green)';
                
                setTimeout(() => {
                    ruleGroup.style.transform = '';
                    ruleGroup.style.boxShadow = '';
                    ruleGroup.style.borderColor = '';
                }, 1500);
            }
        }
        
        function toggleRuleGroup(ruleId) {
            const content = document.getElementById('content-' + ruleId);
            const toggle = document.getElementById('toggle-' + ruleId);
            
            if (content.style.maxHeight && content.style.maxHeight !== '0px') {
                content.style.maxHeight = '0px';
                toggle.style.transform = 'rotate(0deg)';
            } else {
                content.style.maxHeight = content.scrollHeight + 'px';
                toggle.style.transform = 'rotate(180deg)';
            }
        }
        
        // 键盘快捷键处理
        function handleKeyboardShortcuts(event) {
            if (event.key === 'Escape') {
                const modalOverlay = document.getElementById('rules-modal-overlay');
                if (modalOverlay && modalOverlay.classList.contains('show')) {
                    closeRulesModal();
                }
            }
        }
        
        // 初始化页面
        document.addEventListener('DOMContentLoaded', function() {
            // 展开所有规则组
            const ruleGroups = document.querySelectorAll('.rule-group');
            ruleGroups.forEach((group, index) => {
                const content = document.getElementById('content-' + index);
                const toggle = document.getElementById('toggle-' + index);
                if (content && toggle) {
                    content.style.maxHeight = content.scrollHeight + 'px';
                    toggle.style.transform = 'rotate(180deg)';
                }
            });
            
            // 绑定键盘事件
            document.addEventListener('keydown', handleKeyboardShortcuts);
        });
    </script>
</body>
</html>`;
  
  return htmlTemplate;
}

// 获取CSS内容
function getCSSContent() {
  // 返回内联CSS样式
  return `
/* 现代极简风格 - Batch Replacer 报告样式 */

/* 基础重置和变量 */
:root {
  /* 主色调 - 绿色系 */
  --primary-green: #10b981;
  --light-green: #d1fae5;
  --accent-green: #059669;
  --soft-green: #f0fdf4;
  
  /* 高亮配色 - 现代Web UI设计 */
  /* 原文高亮 - 蓝色系 */
  --highlight-original-bg: #dbeafe;
  --highlight-original-text: #1d4ed8;
  --highlight-original-border: #93c5fd;
  
  /* 修改后高亮 - 琥珀色系 */
  --highlight-modified-bg: #fef3c7;
  --highlight-modified-text: #d97706;
  --highlight-modified-border: #fcd34d;
  
  /* 中性色 */
  --white: #ffffff;
  --gray-50: #f9fafb;
  --gray-100: #f3f4f6;
  --gray-200: #e5e7eb;
  --gray-300: #d1d5db;
  --gray-400: #9ca3af;
  --gray-500: #6b7280;
  --gray-600: #4b5563;
  --gray-700: #374151;
  --gray-800: #1f2937;
  --gray-900: #111827;
  
  /* 阴影 */
  --shadow-sm: 0 1px 2px 0 rgb(0 0 0 / 0.05);
  --shadow-md: 0 4px 6px -1px rgb(0 0 0 / 0.1), 0 2px 4px -2px rgb(0 0 0 / 0.1);
  --shadow-lg: 0 10px 15px -3px rgb(0 0 0 / 0.1), 0 4px 6px -4px rgb(0 0 0 / 0.1);
  
  /* 边框半径 */
  --radius-sm: 0.375rem;
  --radius-md: 0.5rem;
  --radius-lg: 0.75rem;
  --radius-xl: 1rem;
  
  /* 动画 */
  --transition-fast: 0.15s ease-out;
  --transition-normal: 0.3s ease-out;
  --transition-slow: 0.5s ease-out;
}

* {
  margin: 0;
  padding: 0;
  box-sizing: border-box;
}

body {
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Helvetica Neue', Arial, sans-serif;
  background-color: var(--white);
  color: var(--gray-800);
  line-height: 1.6;
  font-size: 14px;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
  position: relative;
}

/* 顶部导航栏 */
.top-nav {
  position: sticky;
  top: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(10px);
  border-bottom: 1px solid var(--gray-200);
  z-index: 100;
  padding: 16px 0;
}

.nav-content {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  color: var(--gray-800);
}

.logo-icon {
  width: 24px;
  height: 24px;
  background: linear-gradient(135deg, var(--primary-green), var(--accent-green));
  border-radius: var(--radius-sm);
  position: relative;
}

.logo-icon::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  width: 12px;
  height: 12px;
  background: var(--white);
  border-radius: 2px;
}

.nav-actions {
  display: flex;
  gap: 8px;
  align-items: center;
}

.nav-btn {
  padding: 8px 16px;
  border: 1px solid var(--gray-200);
  background: var(--white);
  color: var(--gray-600);
  border-radius: var(--radius-md);
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.nav-btn:hover {
  border-color: var(--primary-green);
  color: var(--primary-green);
}

.nav-btn.active {
  background: var(--primary-green);
  border-color: var(--primary-green);
  color: var(--white);
}

.export-info {
  font-size: 12px;
  color: var(--gray-500);
  padding: 8px 12px;
  background: var(--gray-50);
  border-radius: var(--radius-md);
}

/* 文件信息头部 */
.file-header {
  padding: 32px 0;
  border-bottom: 1px solid var(--gray-100);
}

.file-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--gray-900);
  margin-bottom: 8px;
}

.file-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  color: var(--gray-500);
  font-size: 13px;
}

.meta-divider {
  color: var(--gray-300);
}

/* 统计概览 */
.stats-overview {
  padding: 32px 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 24px;
}

.stat-card {
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  padding: 24px;
  display: flex;
  align-items: center;
  gap: 16px;
  transition: all var(--transition-normal);
  position: relative;
}

.stat-card:hover {
  border-color: var(--primary-green);
  box-shadow: var(--shadow-md);
}

.stat-icon {
  width: 48px;
  height: 48px;
  border-radius: var(--radius-lg);
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.rules-icon {
  background: linear-gradient(135deg, var(--primary-green), var(--accent-green));
}

.instances-icon {
  background: linear-gradient(135deg, #3b82f6, #1d4ed8);
}

.success-icon {
  background: linear-gradient(135deg, #10b981, #059669);
}

.stat-content {
  flex: 1;
}

.stat-number {
  font-size: 28px;
  font-weight: 700;
  color: var(--gray-900);
  line-height: 1;
}

.stat-label {
  font-size: 14px;
  color: var(--gray-600);
  margin-top: 4px;
  margin-bottom: 8px;
}

.stat-progress {
  width: 100%;
  height: 4px;
  background: var(--gray-100);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, var(--primary-green), var(--accent-green));
  border-radius: 2px;
  transition: width var(--transition-slow);
}

/* 主要内容区域 */
.main-content {
  padding: 32px 0;
}

.rule-group {
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-lg);
  margin-bottom: 24px;
  overflow: hidden;
  transition: all var(--transition-normal);
}

.rule-group:hover {
  border-color: var(--primary-green);
  box-shadow: var(--shadow-sm);
}

.rule-header {
  padding: 20px 24px;
  background: var(--gray-50);
  border-bottom: 1px solid var(--gray-200);
  display: flex;
  align-items: center;
  justify-content: space-between;
  cursor: pointer;
  transition: all var(--transition-fast);
}

.rule-header:hover {
  background: var(--light-green);
}

.rule-info {
  display: flex;
  align-items: center;
  gap: 16px;
}

.rule-badge {
  background: var(--primary-green);
  color: var(--white);
  padding: 4px 12px;
  border-radius: var(--radius-md);
  font-size: 12px;
  font-weight: 600;
}

.rule-title {
  display: flex;
  align-items: center;
  gap: 12px;
  font-weight: 600;
  color: var(--gray-800);
}

.rule-from {
  color: var(--highlight-original-text);
  background: var(--highlight-original-bg);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--highlight-original-border);
}

.rule-to {
  color: var(--highlight-modified-text);
  background: var(--highlight-modified-bg);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  border: 1px solid var(--highlight-modified-border);
}

.rule-arrow {
  display: flex;
  align-items: center;
  gap: 4px;
  color: var(--gray-400);
}

.arrow-line {
  width: 20px;
  height: 1px;
  background: var(--gray-400);
}

.arrow-head {
  width: 0;
  height: 0;
  border-left: 4px solid var(--gray-400);
  border-top: 3px solid transparent;
  border-bottom: 3px solid transparent;
}

.rule-toggle {
  display: flex;
  align-items: center;
}

.toggle-icon {
  width: 20px;
  height: 20px;
  border: 2px solid var(--gray-400);
  border-radius: 50%;
  position: relative;
  transition: all var(--transition-fast);
}

.toggle-icon::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%) rotate(0deg);
  width: 8px;
  height: 8px;
  border-right: 2px solid var(--gray-400);
  border-bottom: 2px solid var(--gray-400);
  transition: transform var(--transition-fast);
}

.rule-content {
  max-height: 0;
  overflow: hidden;
  transition: max-height var(--transition-normal);
}

.instances-grid {
  padding: 24px;
  display: grid;
  gap: 20px;
}

.instance-card {
  background: var(--white);
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  overflow: hidden;
  transition: all var(--transition-normal);
}

.instance-card:hover {
  border-color: var(--primary-green);
  box-shadow: var(--shadow-sm);
}

.instance-header {
  padding: 12px 16px;
  background: var(--gray-50);
  border-bottom: 1px solid var(--gray-200);
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.instance-number {
  font-weight: 600;
  color: var(--primary-green);
  font-size: 13px;
}

.instance-context {
  font-size: 12px;
  color: var(--gray-500);
}

.comparison-container {
  display: grid;
  grid-template-columns: 1fr auto 1fr;
  gap: 16px;
  padding: 20px;
  align-items: start;
}

.text-section {
  min-height: 60px;
}

.section-label {
  font-size: 12px;
  font-weight: 600;
  color: var(--gray-500);
  margin-bottom: 8px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}

.text-content {
  font-size: 14px;
  line-height: 1.6;
  color: var(--gray-800);
}

.comparison-divider {
  width: 1px;
  background: var(--gray-200);
  align-self: stretch;
  margin: 20px 0;
}

/* 高亮样式 */
.highlight-original {
  background: var(--highlight-original-bg);
  color: var(--highlight-original-text);
  padding: 2px 4px;
  border-radius: 3px;
  border: 1px solid var(--highlight-original-border);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.highlight-original:hover {
  transform: scale(1.05);
}

.highlight-modified {
  background: var(--highlight-modified-bg);
  color: var(--highlight-modified-text);
  padding: 2px 4px;
  border-radius: 3px;
  border: 1px solid var(--highlight-modified-border);
  font-weight: 500;
  transition: all var(--transition-fast);
}

.highlight-modified:hover {
  transform: scale(1.05);
}

/* 响应式设计 */
@media (max-width: 768px) {
  .container {
    padding: 0 16px;
  }
  
  .nav-content {
    flex-direction: column;
    gap: 16px;
  }
  
  .stats-grid {
    grid-template-columns: 1fr;
  }
  
  .comparison-container {
    grid-template-columns: 1fr;
    gap: 12px;
  }
  
  .comparison-divider {
    width: 100%;
    height: 1px;
    margin: 12px 0;
  }
  
  .rule-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}

/* 模态窗口样式 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0, 0, 0, 0.5);
  display: none;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  opacity: 0;
  transition: opacity var(--transition-normal);
}

.modal-overlay.show {
  opacity: 1;
}

.modal-content {
  background: var(--white);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-lg);
  max-width: 600px;
  width: 90%;
  max-height: 80vh;
  overflow: hidden;
  transform: scale(0.9);
  transition: transform var(--transition-normal);
}

.modal-overlay.show .modal-content {
  transform: scale(1);
}

.modal-header {
  padding: 24px 24px 16px;
  border-bottom: 1px solid var(--gray-200);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--gray-900);
  margin: 0;
}

.modal-close {
  background: none;
  border: none;
  cursor: pointer;
  padding: 8px;
  border-radius: var(--radius-md);
  transition: background-color var(--transition-fast);
}

.modal-close:hover {
  background: var(--gray-100);
}

.close-icon {
  font-size: 20px;
  color: var(--gray-500);
  line-height: 1;
}

.modal-body {
  padding: 16px 24px 24px;
  max-height: 60vh;
  overflow-y: auto;
}

.rules-list-modal {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.rule-item-modal {
  padding: 16px;
  border: 1px solid var(--gray-200);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: all var(--transition-fast);
  background: var(--white);
}

.rule-item-modal:hover {
  border-color: var(--primary-green);
  background: var(--soft-green);
  transform: translateX(4px);
}

.rule-summary-modal {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.rule-text-modal {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 500;
}

.rule-count-modal {
  background: var(--primary-green);
  color: var(--white);
  padding: 4px 8px;
  border-radius: var(--radius-sm);
  font-size: 12px;
  font-weight: 600;
}

/* 打印样式 */
@media print {
  .top-nav,
  .modal-overlay {
    display: none;
  }
  
  .rule-content {
    max-height: none !important;
  }
  
  .instance-card {
    break-inside: avoid;
  }
}

}

// 显示通知
function showNotification(message, type = 'info') {
  const notification = document.createElement('div');
  notification.className = `notification notification-${type}`;
  notification.textContent = message;
  
  notification.style.cssText = `
    position: fixed;
    top: 20px;
    right: 20px;
    background: ${type === 'success' ? 'var(--primary-green)' : 'var(--gray-800)'};
    color: white;
    padding: 12px 20px;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-lg);
    z-index: 1000;
    transform: translateX(100%);
    transition: transform 0.3s ease-out;
  `;
  
  document.body.appendChild(notification);
  
  // 滑入动画
  setTimeout(() => {
    notification.style.transform = 'translateX(0)';
  }, 10);
  
  // 自动移除
  setTimeout(() => {
    notification.style.transform = 'translateX(100%)';
    setTimeout(() => {
      document.body.removeChild(notification);
    }, 300);
  }, 3000);
}

// 键盘快捷键处理
function handleKeyboardShortcuts(event) {
  // Esc键关闭模态窗口或所有展开的规则组
  if (event.key === 'Escape') {
    const modalOverlay = document.getElementById('rules-modal-overlay');
    if (modalOverlay && modalOverlay.classList.contains('show')) {
      closeRulesModal();
    } else {
      AppState.expandedRules.forEach(ruleId => {
        toggleRuleGroup(ruleId);
      });
    }
  }
  
  // 数字键快速跳转到对应规则
  if (event.key >= '1' && event.key <= '9') {
    const ruleIndex = parseInt(event.key) - 1;
    if (ruleIndex < rulesData.length) {
      jumpToRule(ruleIndex);
    }
  }
  
  // 空格键回到顶部
  if (event.key === ' ' && event.ctrlKey) {
    event.preventDefault();
    scrollToTop();
  }
}

// 窗口大小变化处理
function handleResize() {
  // 重新计算展开的规则组高度
  AppState.expandedRules.forEach(ruleId => {
    const content = document.getElementById(`content-${ruleId}`);
    if (content) {
      content.style.maxHeight = `${content.scrollHeight}px`;
    }
  });
}

// 触发动画
function triggerAnimation(element, animationType) {
  switch (animationType) {
    case 'slide-up':
      element.style.animation = 'slideUp 0.6s ease-out forwards';
      break;
    case 'fade-in':
      element.style.animation = 'fadeIn 0.4s ease-out forwards';
      break;
    default:
      element.style.opacity = '1';
      element.style.transform = 'translateY(0)';
  }
}

// 工具函数：节流
function throttle(func, limit) {
  let inThrottle;
  return function() {
    const args = arguments;
    const context = this;
    if (!inThrottle) {
      func.apply(context, args);
      inThrottle = true;
      setTimeout(() => inThrottle = false, limit);
    }
  };
}

// 工具函数：防抖
function debounce(func, wait) {
  let timeout;
  return function executedFunction(...args) {
    const later = () => {
      clearTimeout(timeout);
      func(...args);
    };
    clearTimeout(timeout);
    timeout = setTimeout(later, wait);
  };
}

// 导航功能
function showOverview() {
  document.querySelector('.stats-overview').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
  updateActiveNavButton('overview');
}

function showRulesList() {
  document.querySelector('.quick-nav').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
  updateActiveNavButton('rules');
}

function showComparisons() {
  document.querySelector('.main-content').scrollIntoView({
    behavior: 'smooth',
    block: 'start'
  });
  updateActiveNavButton('comparisons');
}

function updateActiveNavButton(activeSection) {
  document.querySelectorAll('.nav-btn').forEach(btn => {
    btn.classList.remove('active');
  });
  
  const buttons = document.querySelectorAll('.nav-btn');
  switch (activeSection) {
    case 'overview':
      buttons[0]?.classList.add('active');
      break;
    case 'rules':
      buttons[1]?.classList.add('active');
      break;
    case 'comparisons':
      buttons[2]?.classList.add('active');
      break;
  }
}

// 性能优化：使用 requestAnimationFrame 进行平滑动画
function smoothScrollTo(element, duration = 800) {
  const start = window.pageYOffset;
  const target = element.offsetTop - 100; // 留出一些顶部空间
  const distance = target - start;
  let startTime = null;
  
  function animation(currentTime) {
    if (startTime === null) startTime = currentTime;
    const timeElapsed = currentTime - startTime;
    const run = easeInOutQuad(timeElapsed, start, distance, duration);
    window.scrollTo(0, run);
    if (timeElapsed < duration) requestAnimationFrame(animation);
  }
  
  requestAnimationFrame(animation);
}

// 缓动函数
function easeInOutQuad(t, b, c, d) {
  t /= d / 2;
  if (t < 1) return c / 2 * t * t + b;
  t--;
  return -c / 2 * (t * (t - 2) - 1) + b;
}

// 暴露全局函数
window.toggleRuleGroup = toggleRuleGroup;
window.jumpToRule = jumpToRule;
window.jumpToRuleAndClose = jumpToRuleAndClose;
window.showRulesModal = showRulesModal;
window.closeRulesModal = closeRulesModal;
window.scrollToTop = scrollToTop;
window.exportReport = exportReport;
window.showOverview = showOverview;
window.showRulesList = showRulesList;
window.showComparisons = showComparisons;

// 开发模式下的调试功能
if (window.location.hostname === 'localhost') {
  window.AppState = AppState;
  window.rulesData = rulesData;
  console.log('🎯 Batch Replacer 报告已加载');
  console.log('📊 统计信息:', {
    规则数量: rulesData.length,
    总实例数: rulesData.reduce((sum, rule) => sum + rule.count, 0)
  });
  console.log('⌨️ 快捷键: 数字键(1-9)跳转规则, Esc关闭所有, Ctrl+Space回顶部');
}