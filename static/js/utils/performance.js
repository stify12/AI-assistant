/**
 * 性能优化工具
 */

/**
 * 防抖函数
 */
function debounce(fn, delay = 300) {
    let timer = null;
    return function(...args) {
        clearTimeout(timer);
        timer = setTimeout(() => fn.apply(this, args), delay);
    };
}

/**
 * 节流函数
 */
function throttle(fn, interval = 16) {
    let lastTime = 0;
    return function(...args) {
        const now = Date.now();
        if (now - lastTime >= interval) {
            lastTime = now;
            fn.apply(this, args);
        }
    };
}

/**
 * 懒加载类
 */
class LazyLoader {
    constructor(options = {}) {
        this.options = {
            root: options.root || null,
            rootMargin: options.rootMargin || '100px',
            threshold: options.threshold || 0,
            onLoad: options.onLoad || (() => {}),
            ...options
        };
        
        this.observer = new IntersectionObserver(
            this.handleIntersect.bind(this),
            {
                root: this.options.root,
                rootMargin: this.options.rootMargin,
                threshold: this.options.threshold
            }
        );
        
        this.loadedElements = new Set();
    }

    observe(element) {
        if (element && !this.loadedElements.has(element)) {
            this.observer.observe(element);
        }
    }

    unobserve(element) {
        if (element) {
            this.observer.unobserve(element);
        }
    }

    handleIntersect(entries) {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const element = entry.target;
                this.loadedElements.add(element);
                this.observer.unobserve(element);
                this.options.onLoad(element);
            }
        });
    }

    disconnect() {
        this.observer.disconnect();
    }
}

/**
 * 虚拟滚动类
 */
class VirtualScroller {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            itemHeight: options.itemHeight || 60,
            bufferSize: options.bufferSize || 5,
            renderItem: options.renderItem || ((item) => `<div>${item}</div>`),
            onLoadMore: options.onLoadMore || null,
            loadMoreThreshold: options.loadMoreThreshold || 200,
            ...options
        };
        
        this.items = [];
        this.scrollTop = 0;
        this.containerHeight = 0;
        this.totalHeight = 0;
        
        this.init();
    }

    init() {
        if (!this.container) return;
        
        // 创建内部结构
        this.container.style.overflow = 'auto';
        this.container.style.position = 'relative';
        
        this.spacer = document.createElement('div');
        this.spacer.style.position = 'absolute';
        this.spacer.style.top = '0';
        this.spacer.style.left = '0';
        this.spacer.style.right = '0';
        this.spacer.style.pointerEvents = 'none';
        
        this.content = document.createElement('div');
        this.content.style.position = 'absolute';
        this.content.style.top = '0';
        this.content.style.left = '0';
        this.content.style.right = '0';
        
        this.container.appendChild(this.spacer);
        this.container.appendChild(this.content);
        
        // 绑定滚动事件
        this.container.addEventListener('scroll', throttle(() => this.handleScroll(), 16));
        
        // 监听容器大小变化
        if (window.ResizeObserver) {
            this.resizeObserver = new ResizeObserver(() => {
                this.containerHeight = this.container.clientHeight;
                this.render();
            });
            this.resizeObserver.observe(this.container);
        }
        
        this.containerHeight = this.container.clientHeight;
    }

    setItems(items) {
        this.items = items;
        this.totalHeight = items.length * this.options.itemHeight;
        this.spacer.style.height = `${this.totalHeight}px`;
        this.render();
    }

    appendItems(items) {
        this.items = this.items.concat(items);
        this.totalHeight = this.items.length * this.options.itemHeight;
        this.spacer.style.height = `${this.totalHeight}px`;
        this.render();
    }

    handleScroll() {
        this.scrollTop = this.container.scrollTop;
        this.render();
        
        // 检查是否需要加载更多
        if (this.options.onLoadMore) {
            const scrollBottom = this.scrollTop + this.containerHeight;
            if (this.totalHeight - scrollBottom < this.options.loadMoreThreshold) {
                this.options.onLoadMore();
            }
        }
    }

    render() {
        const { itemHeight, bufferSize, renderItem } = this.options;
        
        // 计算可见范围
        const startIndex = Math.max(0, Math.floor(this.scrollTop / itemHeight) - bufferSize);
        const endIndex = Math.min(
            this.items.length,
            Math.ceil((this.scrollTop + this.containerHeight) / itemHeight) + bufferSize
        );
        
        // 渲染可见项
        const visibleItems = this.items.slice(startIndex, endIndex);
        const offsetY = startIndex * itemHeight;
        
        this.content.style.transform = `translateY(${offsetY}px)`;
        this.content.innerHTML = visibleItems.map((item, index) => {
            const html = renderItem(item, startIndex + index);
            return `<div style="height: ${itemHeight}px;">${html}</div>`;
        }).join('');
    }

    scrollToIndex(index) {
        const targetTop = index * this.options.itemHeight;
        this.container.scrollTop = targetTop;
    }

    destroy() {
        if (this.resizeObserver) {
            this.resizeObserver.disconnect();
        }
    }
}

window.debounce = debounce;
window.throttle = throttle;
window.LazyLoader = LazyLoader;
window.VirtualScroller = VirtualScroller;
