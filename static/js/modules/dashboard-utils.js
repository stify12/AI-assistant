/**
 * 看板工具函数模块
 * @module dashboard-utils
 */

// ========== 常量定义 ==========

/** @type {Object} 学科ID到名称的映射 */
export const SUBJECT_MAP = {
    '0': '英语',
    '1': '语文',
    '2': '数学',
    '3': '物理',
    '4': '化学',
    '5': '生物',
    '6': '地理'
};

/** @type {Object} 学科颜色映射 - 浅色系柔和色调 */
export const SUBJECT_COLORS = {
    '0': '#93c5fd',  // 英语 - 浅蓝
    '1': '#fda4af',  // 语文 - 浅玫瑰
    '2': '#86efac',  // 数学 - 浅绿
    '3': '#fcd34d',  // 物理 - 浅琥珀
    '4': '#c4b5fd',  // 化学 - 浅紫
    '5': '#67e8f9',  // 生物 - 浅青
    '6': '#a5b4fc'   // 地理 - 浅靛蓝
};

/** @type {Object} 状态文本映射 */
export const STATUS_MAP = {
    'pending': '待处理',
    'processing': '进行中',
    'completed': '已完成',
    'failed': '异常',
    'draft': '草稿',
    'active': '进行中',
    'archived': '已归档'
};

/** @type {Object} 错误类型颜色 - 现代色调 */
export const ERROR_TYPE_COLORS = {
    '识别错误-判断错误': '#ef4444', // 红色
    '识别正确-判断错误': '#f97316', // 橙色
    '识别错误-判断正确': '#eab308', // 黄色
    '缺失题目': '#a855f7', // 紫色
    'AI识别幻觉': '#ec4899', // 粉色
    '其他': '#64748b'  // 灰色
};

// ========== 格式化函数 ==========

/**
 * 格式化日期时间
 * @param {string|Date} dateStr - 日期字符串或Date对象
 * @returns {string} 格式化后的日期时间
 */
export function formatDateTime(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '--';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${year}-${month}-${day} ${hours}:${minutes}`;
}

/**
 * 格式化简短时间（月-日 时:分）
 * @param {string|Date} dateStr - 日期字符串
 * @returns {string} 格式化后的时间
 */
export function formatTime(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '--';
    
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    
    return `${month}-${day} ${hours}:${minutes}`;
}

/**
 * 格式化日期（年-月-日）
 * @param {string|Date} dateStr - 日期字符串
 * @returns {string} 格式化后的日期
 */
export function formatDate(dateStr) {
    if (!dateStr) return '--';
    const date = new Date(dateStr);
    if (isNaN(date.getTime())) return '--';
    
    const year = date.getFullYear();
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    
    return `${year}-${month}-${day}`;
}

/**
 * 格式化百分比
 * @param {number} value - 数值（0-1）
 * @param {number} decimals - 小数位数
 * @returns {string} 百分比字符串
 */
export function formatPercent(value, decimals = 1) {
    if (value === null || value === undefined || isNaN(value)) return '--';
    return (value * 100).toFixed(decimals) + '%';
}

/**
 * 格式化数字（千分位）
 * @param {number} num - 数字
 * @returns {string} 格式化后的数字
 */
export function formatNumber(num) {
    if (num === null || num === undefined || isNaN(num)) return '0';
    return num.toLocaleString('zh-CN');
}

// ========== DOM 工具函数 ==========

/**
 * HTML 转义
 * @param {string} str - 原始字符串
 * @returns {string} 转义后的字符串
 */
export function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

/**
 * 显示 Toast 通知
 * @param {string} message - 消息内容
 * @param {string} type - 类型: success|error|warning|info
 * @param {number} duration - 显示时长(ms)
 */
export function showToast(message, type = 'info', duration = 3000) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `
        <span class="toast-message">${escapeHtml(message)}</span>
        <button class="toast-close" onclick="this.parentElement.remove()">×</button>
    `;
    
    container.appendChild(toast);
    
    // 触发动画
    requestAnimationFrame(() => {
        toast.classList.add('show');
    });
    
    // 自动移除
    setTimeout(() => {
        toast.classList.remove('show');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

/**
 * 显示/隐藏骨架屏
 * @param {string} skeletonId - 骨架屏元素ID
 * @param {string} contentId - 内容元素ID
 * @param {boolean} showSkeleton - 是否显示骨架屏
 */
export function toggleSkeleton(skeletonId, contentId, showSkeleton) {
    const skeleton = document.getElementById(skeletonId);
    const content = document.getElementById(contentId);
    
    if (skeleton) skeleton.style.display = showSkeleton ? '' : 'none';
    if (content) content.style.display = showSkeleton ? 'none' : '';
}

/**
 * 创建元素
 * @param {string} tag - 标签名
 * @param {Object} attrs - 属性对象
 * @param {string|HTMLElement|Array} children - 子元素
 * @returns {HTMLElement}
 */
export function createElement(tag, attrs = {}, children = null) {
    const el = document.createElement(tag);
    
    for (const [key, value] of Object.entries(attrs)) {
        if (key === 'className') {
            el.className = value;
        } else if (key === 'style' && typeof value === 'object') {
            Object.assign(el.style, value);
        } else if (key.startsWith('on') && typeof value === 'function') {
            el.addEventListener(key.slice(2).toLowerCase(), value);
        } else {
            el.setAttribute(key, value);
        }
    }
    
    if (children) {
        if (typeof children === 'string') {
            el.innerHTML = children;
        } else if (Array.isArray(children)) {
            children.forEach(child => {
                if (typeof child === 'string') {
                    el.appendChild(document.createTextNode(child));
                } else if (child instanceof HTMLElement) {
                    el.appendChild(child);
                }
            });
        } else if (children instanceof HTMLElement) {
            el.appendChild(children);
        }
    }
    
    return el;
}

// ========== 数据处理函数 ==========

/**
 * 获取难度等级
 * @param {number} accuracy - 准确率（0-1）
 * @returns {Object} {class, text, color}
 */
export function getDifficultyLevel(accuracy) {
    if (accuracy === null || accuracy === undefined) {
        return { class: '', text: '未知', color: '#86868b' };
    }
    if (accuracy >= 0.9) {
        return { class: 'easy', text: '简单', color: '#10b981' };
    }
    if (accuracy >= 0.7) {
        return { class: 'medium', text: '中等', color: '#f59e0b' };
    }
    return { class: 'hard', text: '困难', color: '#ef4444' };
}

/**
 * 获取趋势方向
 * @param {number} current - 当前值
 * @param {number} previous - 之前值
 * @returns {Object} {direction, diff, class}
 */
export function getTrend(current, previous) {
    if (current === null || previous === null || 
        current === undefined || previous === undefined) {
        return { direction: 'flat', diff: 0, class: '' };
    }
    
    const diff = current - previous;
    if (Math.abs(diff) < 0.001) {
        return { direction: 'flat', diff: 0, class: 'trend-flat' };
    }
    if (diff > 0) {
        return { direction: 'up', diff, class: 'trend-up' };
    }
    return { direction: 'down', diff, class: 'trend-down' };
}

/**
 * 防抖函数
 * @param {Function} fn - 要防抖的函数
 * @param {number} delay - 延迟时间(ms)
 * @returns {Function}
 */
export function debounce(fn, delay = 300) {
    let timer = null;
    return function(...args) {
        if (timer) clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * 节流函数
 * @param {Function} fn - 要节流的函数
 * @param {number} limit - 时间限制(ms)
 * @returns {Function}
 */
export function throttle(fn, limit = 16) {
    let lastTime = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastTime >= limit) {
            lastTime = now;
            fn.apply(this, args);
        }
    };
}

/**
 * requestIdleCallback 兼容处理
 * @param {Function} callback - 回调函数
 * @param {Object} options - 选项
 */
export function requestIdleCallbackPolyfill(callback, options = { timeout: 1000 }) {
    if (typeof requestIdleCallback === 'function') {
        requestIdleCallback(callback, options);
    } else {
        setTimeout(callback, 100);
    }
}

// ========== 导航函数 ==========

/**
 * 页面导航
 * @param {string} url - 目标URL
 */
export function navigateTo(url) {
    window.location.href = url;
}

/**
 * 切换侧边栏
 */
export function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const mainContent = document.querySelector('.main-content');
    
    if (sidebar) {
        sidebar.classList.toggle('collapsed');
        if (mainContent) {
            mainContent.classList.toggle('sidebar-collapsed');
        }
        
        // 保存状态
        const isCollapsed = sidebar.classList.contains('collapsed');
        localStorage.setItem('sidebarCollapsed', isCollapsed);
    }
}

/**
 * 恢复侧边栏状态
 */
export function restoreSidebarState() {
    const isCollapsed = localStorage.getItem('sidebarCollapsed') === 'true';
    if (isCollapsed) {
        const sidebar = document.getElementById('sidebar');
        const mainContent = document.querySelector('.main-content');
        if (sidebar) sidebar.classList.add('collapsed');
        if (mainContent) mainContent.classList.add('sidebar-collapsed');
    }
}
