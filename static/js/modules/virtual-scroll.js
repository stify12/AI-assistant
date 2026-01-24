/**
 * 虚拟滚动模块 (US-31)
 * 用于大数据量列表的性能优化
 */
class VirtualScroll {
    constructor(container, options = {}) {
        this.container = typeof container === 'string' 
            ? document.querySelector(container) 
            : container;
        
        if (!this.container) {
            console.error('[VirtualScroll] 容器不存在');
            return;
        }
        
        // 配置
        this.itemHeight = options.itemHeight || 60;
        this.bufferSize = options.bufferSize || 5;
        this.renderItem = options.renderItem || this.defaultRenderItem;
        this.onItemClick = options.onItemClick || null;
        
        // 状态
        this.items = [];
        this.scrollTop = 0;
        this.containerHeight = 0;
        
        // 创建DOM结构
        this.setup();
        this.bindEvents();
    }
    
    setup() {
        this.container.style.overflow = 'auto';
        this.container.style.position = 'relative';
        
        // 内容容器（撑开滚动高度）
        this.content = document.createElement('div');
        this.content.className = 'virtual-scroll-content';
        this.content.style.position = 'relative';
        
        // 可视区域容器
        this.viewport = document.createElement('div');
        this.viewport.className = 'virtual-scroll-viewport';
        this.viewport.style.position = 'absolute';
        this.viewport.style.left = '0';
        this.viewport.style.right = '0';
        
        this.content.appendChild(this.viewport);
        this.container.appendChild(this.content);
        
        this.containerHeight = this.container.clientHeight;
    }
    
    bindEvents() {
        this.container.addEventListener('scroll', () => {
            this.scrollTop = this.container.scrollTop;
            this.render();
        });
        
        // 点击事件委托
        this.viewport.addEventListener('click', (e) => {
            const item = e.target.closest('.virtual-scroll-item');
            if (item && this.onItemClick) {
                const index = parseInt(item.dataset.index);
                this.onItemClick(this.items[index], index, e);
            }
        });
        
        // 监听容器大小变化
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                this.containerHeight = this.container.clientHeight;
                this.render();
            });
            this.resizeObserver.observe(this.container);
        }
    }
    
    setData(items) {
        this.items = items || [];
        this.content.style.height = `${this.items.length * this.itemHeight}px`;
        this.render();
    }
    
    render() {
        if (!this.items.length) {
            this.viewport.innerHTML = '<div class="empty-state">暂无数据</div>';
            return;
        }
        
        // 计算可视范围
        const startIndex = Math.max(0, Math.floor(this.scrollTop / this.itemHeight) - this.bufferSize);
        const visibleCount = Math.ceil(this.containerHeight / this.itemHeight);
        const endIndex = Math.min(this.items.length, startIndex + visibleCount + this.bufferSize * 2);
        
        // 定位viewport
        this.viewport.style.top = `${startIndex * this.itemHeight}px`;
        
        // 渲染可视项
        let html = '';
        for (let i = startIndex; i < endIndex; i++) {
            html += this.renderItem(this.items[i], i);
        }
        
        this.viewport.innerHTML = html;
    }
    
    defaultRenderItem(item, index) {
        return `
            <div class="virtual-scroll-item" data-index="${index}" style="height: ${this.itemHeight}px;">
                ${JSON.stringify(item)}
            </div>
        `;
    }
    
    scrollToIndex(index) {
        const top = index * this.itemHeight;
        this.container.scrollTop = top;
    }
    
    refresh() {
        this.containerHeight = this.container.clientHeight;
        this.render();
    }
    
    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
        this.container.innerHTML = '';
    }
}

/**
 * 任务列表虚拟滚动
 */
const VirtualTaskList = {
    instance: null,
    
    init(containerId, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        this.instance = new VirtualScroll(container, {
            itemHeight: options.itemHeight || 72,
            bufferSize: 5,
            renderItem: this.renderTaskItem.bind(this),
            onItemClick: options.onItemClick
        });
    },
    
    setData(tasks) {
        if (this.instance) {
            this.instance.setData(tasks);
        }
    },
    
    renderTaskItem(task, index) {
        const statusClass = task.status || 'pending';
        const statusText = {
            'completed': '已完成',
            'running': '运行中',
            'failed': '失败',
            'pending': '待执行'
        }[task.status] || '未知';
        
        const accuracy = task.accuracy != null 
            ? `${(task.accuracy * 100).toFixed(1)}%` 
            : '--';
        
        return `
            <div class="virtual-scroll-item task-item" data-index="${index}" data-id="${task.task_id || task.id}">
                <div class="task-item-main">
                    <div class="task-item-name">${this.escapeHtml(task.name || task.task_id || '未命名')}</div>
                    <div class="task-item-meta">
                        <span>${task.question_count || 0} 题</span>
                        <span>${this.formatTime(task.created_at)}</span>
                    </div>
                </div>
                <div class="task-item-stats">
                    <span class="task-accuracy">${accuracy}</span>
                    <span class="status-tag ${statusClass}">${statusText}</span>
                </div>
            </div>
        `;
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    },
    
    formatTime(dateStr) {
        if (!dateStr) return '--';
        try {
            const d = new Date(dateStr);
            return `${d.getMonth()+1}/${d.getDate()} ${d.getHours()}:${String(d.getMinutes()).padStart(2,'0')}`;
        } catch {
            return '--';
        }
    }
};

/**
 * 错误样本虚拟滚动
 */
const VirtualErrorList = {
    instance: null,
    
    init(containerId, options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        this.instance = new VirtualScroll(container, {
            itemHeight: options.itemHeight || 80,
            bufferSize: 5,
            renderItem: this.renderErrorItem.bind(this),
            onItemClick: options.onItemClick
        });
    },
    
    setData(errors) {
        if (this.instance) {
            this.instance.setData(errors);
        }
    },
    
    renderErrorItem(error, index) {
        const typeClass = {
            'recognition': 'tag-warning',
            'calculation': 'tag-error',
            'format': 'tag-info'
        }[error.error_type] || 'tag-default';
        
        return `
            <div class="virtual-scroll-item error-item" data-index="${index}" data-id="${error.id}">
                <div class="error-item-header">
                    <span class="error-item-question">${this.escapeHtml(error.question_number || '题目')}</span>
                    <span class="tag ${typeClass}">${this.escapeHtml(error.error_type || '未知')}</span>
                </div>
                <div class="error-item-content">
                    <div class="error-answer">
                        <span class="label">AI:</span> ${this.escapeHtml(error.ai_answer || '-')}
                    </div>
                    <div class="error-answer">
                        <span class="label">预期:</span> ${this.escapeHtml(error.expected_answer || '-')}
                    </div>
                </div>
            </div>
        `;
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }
};

// 导出
window.VirtualScroll = VirtualScroll;
window.VirtualTaskList = VirtualTaskList;
window.VirtualErrorList = VirtualErrorList;
