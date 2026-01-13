/**
 * AI学科批改评估 - 工具函数模块
 * 提供通用工具函数，减少代码重复
 */

// ========== Toast 提示 ==========
const Toast = {
    container: null,
    
    init() {
        if (!this.container) {
            this.container = document.createElement('div');
            this.container.className = 'toast-container';
            document.body.appendChild(this.container);
        }
    },
    
    show(message, type = 'info', duration = 3000) {
        this.init();
        
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const icons = {
            success: '✓',
            error: '✗',
            warning: '⚠',
            info: 'ℹ'
        };
        
        toast.innerHTML = `
            <span class="toast-icon">${icons[type] || icons.info}</span>
            <span class="toast-message">${message}</span>
        `;
        
        this.container.appendChild(toast);
        
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
};

// 全局 showToast 函数
function showToast(message, type = 'info', duration = 3000) {
    Toast.show(message, type, duration);
}

// ========== 加载状态管理 ==========
const LoadingManager = {
    show(text = '处理中...') {
        const overlay = document.getElementById('loadingOverlay');
        const textEl = document.getElementById('loadingText');
        if (textEl) textEl.textContent = text;
        if (overlay) overlay.classList.add('show');
    },
    
    hide() {
        const overlay = document.getElementById('loadingOverlay');
        if (overlay) overlay.classList.remove('show');
    },
    
    update(text) {
        const textEl = document.getElementById('loadingText');
        if (textEl) textEl.textContent = text;
    }
};

// 兼容旧函数
function showLoading(text) {
    LoadingManager.show(text);
}

function hideLoading() {
    LoadingManager.hide();
}

// ========== 错误处理 ==========
function showError(msg) {
    showToast(msg, 'error', 5000);
}

// ========== HTML 转义 ==========
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

// ========== 时间格式化 ==========
function formatTime(timeStr) {
    if (!timeStr) return '-';
    try {
        const date = new Date(timeStr);
        if (isNaN(date.getTime())) return timeStr;
        return date.toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    } catch (e) {
        return timeStr;
    }
}

// ========== 生成唯一ID ==========
function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2, 9);
}

// ========== 防抖函数 ==========
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

// ========== 节流函数 ==========
function throttle(func, limit) {
    let inThrottle;
    return function(...args) {
        if (!inThrottle) {
            func.apply(this, args);
            inThrottle = true;
            setTimeout(() => inThrottle = false, limit);
        }
    };
}

// ========== 深拷贝 ==========
function deepClone(obj) {
    if (obj === null || typeof obj !== 'object') return obj;
    try {
        return JSON.parse(JSON.stringify(obj));
    } catch (e) {
        return obj;
    }
}

// ========== 数组分组 ==========
function groupBy(array, key) {
    return array.reduce((result, item) => {
        const groupKey = typeof key === 'function' ? key(item) : item[key];
        (result[groupKey] = result[groupKey] || []).push(item);
        return result;
    }, {});
}

// ========== 数字格式化 ==========
function formatNumber(num, decimals = 1) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return Number(num).toFixed(decimals);
}

function formatPercent(num, decimals = 1) {
    if (num === null || num === undefined || isNaN(num)) return '-';
    return (Number(num) * 100).toFixed(decimals) + '%';
}

// ========== 本地存储封装 ==========
const Storage = {
    get(key, defaultValue = null) {
        try {
            const value = localStorage.getItem(key);
            return value ? JSON.parse(value) : defaultValue;
        } catch (e) {
            return defaultValue;
        }
    },
    
    set(key, value) {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch (e) {
            console.error('Storage set error:', e);
            return false;
        }
    },
    
    remove(key) {
        try {
            localStorage.removeItem(key);
            return true;
        } catch (e) {
            return false;
        }
    }
};

// ========== API 请求封装 ==========
const API = {
    async get(url) {
        try {
            const res = await fetch(url);
            return await res.json();
        } catch (e) {
            return { success: false, error: e.message };
        }
    },
    
    async post(url, data) {
        try {
            const res = await fetch(url, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            return await res.json();
        } catch (e) {
            return { success: false, error: e.message };
        }
    },
    
    async delete(url) {
        try {
            const res = await fetch(url, { method: 'DELETE' });
            return await res.json();
        } catch (e) {
            return { success: false, error: e.message };
        }
    }
};

// ========== 图片弹窗 ==========
function showImageModal(src) {
    if (!src) return;
    const modal = document.getElementById('imageModal');
    const img = document.getElementById('modalImg');
    if (modal && img) {
        img.src = src;
        modal.classList.add('show');
    }
}

function hideImageModal() {
    const modal = document.getElementById('imageModal');
    if (modal) modal.classList.remove('show');
}

// ESC 关闭弹窗
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideImageModal();
        const batchModal = document.getElementById('batchResultModal');
        if (batchModal) batchModal.style.display = 'none';
    }
});

// 导出到全局
window.showToast = showToast;
window.showLoading = showLoading;
window.hideLoading = hideLoading;
window.showError = showError;
window.escapeHtml = escapeHtml;
window.formatTime = formatTime;
window.generateId = generateId;
window.debounce = debounce;
window.throttle = throttle;
window.deepClone = deepClone;
window.groupBy = groupBy;
window.formatNumber = formatNumber;
window.formatPercent = formatPercent;
window.Storage = Storage;
window.API = API;
window.showImageModal = showImageModal;
window.hideImageModal = hideImageModal;
