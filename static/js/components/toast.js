/**
 * Toast 通知组件
 */
class ToastManager {
    constructor() {
        this.container = null;
        this.createContainer();
    }

    createContainer() {
        this.container = document.createElement('div');
        this.container.id = 'toast-container';
        this.container.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            z-index: 10000;
            display: flex;
            flex-direction: column;
            gap: 8px;
        `;
        document.body.appendChild(this.container);
    }

    show(message, type = 'info', duration = 3000) {
        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        
        const colors = {
            success: { bg: '#e3f9e5', text: '#1e7e34', border: '#1e7e34' },
            warning: { bg: '#fff3e0', text: '#e65100', border: '#e65100' },
            error: { bg: '#ffeef0', text: '#d73a49', border: '#d73a49' },
            info: { bg: '#e3f2fd', text: '#1565c0', border: '#1565c0' }
        };
        
        const color = colors[type] || colors.info;
        
        toast.style.cssText = `
            background: ${color.bg};
            color: ${color.text};
            border-left: 3px solid ${color.border};
            padding: 12px 16px;
            border-radius: 6px;
            font-size: 14px;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
            transform: translateX(120%);
            transition: transform 0.3s ease;
            max-width: 350px;
        `;
        
        toast.textContent = message;
        this.container.appendChild(toast);
        
        // 滑入动画
        requestAnimationFrame(() => {
            toast.style.transform = 'translateX(0)';
        });
        
        // 自动移除
        if (duration > 0) {
            setTimeout(() => this.remove(toast), duration);
        }
        
        return toast;
    }

    remove(toast) {
        toast.style.transform = 'translateX(120%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.parentNode.removeChild(toast);
            }
        }, 300);
    }

    success(message, duration) {
        return this.show(message, 'success', duration);
    }

    warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    error(message, duration) {
        return this.show(message, 'error', duration);
    }

    info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// 全局实例
window.toast = new ToastManager();
