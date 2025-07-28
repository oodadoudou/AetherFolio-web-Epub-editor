// Enhanced JavaScript for Green Theme Batch Replacer Report with Theme Toggle

// Theme management
function initTheme() {
    const savedTheme = localStorage.getItem('batch-replacer-theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    updateThemeToggleText(savedTheme);
}

function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('batch-replacer-theme', newTheme);
    updateThemeToggleText(newTheme);
}

function updateThemeToggleText(theme) {
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = theme === 'dark' 
            ? '☀️ Light Mode' 
            : '🌙 Dark Mode';
    }
}

// Original functionality
function toggleInstances(groupIndex) {
    const container = document.getElementById('instances-' + groupIndex);
    const icon = document.getElementById('toggle-' + groupIndex);
    
    if (container.classList.contains('expanded')) {
        container.classList.remove('expanded');
        icon.classList.remove('expanded');
    } else {
        container.classList.add('expanded');
        icon.classList.add('expanded');
    }
}

function toggleRulesList() {
    const rulesList = document.getElementById('rules-list');
    if (rulesList.style.display === 'flex') {
        rulesList.style.display = 'none';
        rulesList.classList.remove('show');
    } else {
        rulesList.style.display = 'flex';
        rulesList.classList.add('show');
    }
}

function jumpToRule(groupIndex) {
    // 关闭规则列表
    toggleRulesList();
    
    // 滚动到对应的规则组
    const ruleGroup = document.querySelector(`[data-group-index="${groupIndex}"]`);
    if (ruleGroup) {
        ruleGroup.scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // 自动展开该规则组
        const container = document.getElementById('instances-' + groupIndex);
        const icon = document.getElementById('toggle-' + groupIndex);
        if (container && !container.classList.contains('expanded')) {
            container.classList.add('expanded');
            icon.classList.add('expanded');
        }
        
        // 添加高亮效果
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const highlightColor = currentTheme === 'dark' 
            ? 'rgba(34, 197, 94, 0.3)' 
            : 'rgba(34, 197, 94, 0.2)';
        
        ruleGroup.style.boxShadow = `0 0 20px ${highlightColor}`;
        setTimeout(() => {
            ruleGroup.style.boxShadow = '';
        }, 2000);
    }
}

// 返回顶部按钮功能
function initBackToTopButton() {
    const backToTopBtn = document.getElementById('back-to-top');
    if (!backToTopBtn) return;
    
    // 监听滚动事件
    window.addEventListener('scroll', function() {
        if (window.pageYOffset > 300) {
            backToTopBtn.classList.add('show');
        } else {
            backToTopBtn.classList.remove('show');
        }
    });
    
    // 点击返回顶部
    backToTopBtn.addEventListener('click', function() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    });
}

// 键盘快捷键
function initKeyboardShortcuts() {
    document.addEventListener('keydown', function(e) {
        // ESC 键关闭模态框
        if (e.key === 'Escape') {
            const rulesList = document.getElementById('rules-list');
            if (rulesList && rulesList.classList.contains('show')) {
                toggleRulesList();
            }
        }
        
        // Ctrl/Cmd + D 切换主题
        if ((e.ctrlKey || e.metaKey) && e.key === 'd') {
            e.preventDefault();
            toggleTheme();
        }
    });
}

// 点击模态框背景关闭
function initModalBackgroundClose() {
    const rulesListContainer = document.getElementById('rules-list');
    if (rulesListContainer) {
        rulesListContainer.addEventListener('click', function(e) {
            if (e.target === rulesListContainer) {
                toggleRulesList();
            }
        });
    }
}

// 初始化返回顶部按钮的显示逻辑
function initBackToTopVisibility() {
    const backToTopBtn = document.getElementById('back-to-top');
    if (!backToTopBtn) return;
    
    function toggleBackToTopVisibility() {
        if (window.pageYOffset > 300) {
            backToTopBtn.style.display = 'flex';
            backToTopBtn.classList.add('show');
        } else {
            backToTopBtn.style.display = 'none';
            backToTopBtn.classList.remove('show');
        }
    }
    
    // 初始检查
    toggleBackToTopVisibility();
    
    // 监听滚动
    window.addEventListener('scroll', toggleBackToTopVisibility);
}

// 初始化所有功能
document.addEventListener('DOMContentLoaded', function() {
    // 初始化主题
    initTheme();
    
    // 绑定主题切换按钮
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.addEventListener('click', toggleTheme);
    }
    
    // 初始化其他功能
    initModalBackgroundClose();
    initKeyboardShortcuts();
    initBackToTopButton();
    initBackToTopVisibility();
    
    // 添加平滑过渡效果
    document.body.style.transition = 'all 0.3s ease';
});

// 导出函数供全局使用
window.toggleInstances = toggleInstances;
window.toggleRulesList = toggleRulesList;
window.jumpToRule = jumpToRule;
window.toggleTheme = toggleTheme;