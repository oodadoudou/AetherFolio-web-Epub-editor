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
    rulesList.classList.toggle('show');
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
        ruleGroup.style.boxShadow = '0 0 20px rgba(34, 197, 94, 0.3)';
        setTimeout(() => {
            ruleGroup.style.boxShadow = '';
        }, 2000);
    }
}

// 主题切换功能
function toggleTheme() {
    const currentTheme = document.documentElement.getAttribute('data-theme');
    const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
    
    document.documentElement.setAttribute('data-theme', newTheme);
    localStorage.setItem('theme', newTheme);
    
    // 更新按钮文本
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = newTheme === 'dark' ? 
            '🌙 Dark Mode' : 
            '☀️ Light Mode';
    }
}

// 初始化主题
function initTheme() {
    const savedTheme = localStorage.getItem('theme') || 'light';
    document.documentElement.setAttribute('data-theme', savedTheme);
    
    const themeToggle = document.getElementById('theme-toggle');
    if (themeToggle) {
        themeToggle.innerHTML = savedTheme === 'dark' ? 
            '🌙 Dark Mode' : 
            '☀️ Light Mode';
        themeToggle.addEventListener('click', toggleTheme);
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

// 点击模态框背景关闭
document.addEventListener('DOMContentLoaded', function() {
    const rulesListContainer = document.getElementById('rules-list');
    if (rulesListContainer) {
        rulesListContainer.addEventListener('click', function(e) {
            if (e.target === rulesListContainer) {
                toggleRulesList();
            }
        });
    }
    
    // ESC 键关闭模态框
    document.addEventListener('keydown', function(e) {
        if (e.key === 'Escape') {
            const rulesList = document.getElementById('rules-list');
            if (rulesList && rulesList.classList.contains('show')) {
                toggleRulesList();
            }
        }
    });
    
    // 初始化主题
    initTheme();
    
    // 初始化返回顶部按钮
    initBackToTopButton();
});