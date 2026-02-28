/**
 * 图片灯箱组件 - 点击放大查看细节
 * 支持缩放、拖拽、键盘操作
 */

class ImageLightbox {
    constructor() {
        this.lightbox = null;
        this.img = null;
        this.currentScale = 1;
        this.minScale = 0.5;
        this.maxScale = 5;
        this.isDragging = false;
        this.startX = 0;
        this.startY = 0;
        this.translateX = 0;
        this.translateY = 0;
        
        this.init();
    }
    
    init() {
        // 创建灯箱DOM
        this.createLightbox();
        
        // 绑定事件
        this.bindEvents();
        
        // 自动为所有图片添加点击放大功能
        this.autoBindImages();
    }
    
    createLightbox() {
        const html = `
            <div class="image-lightbox" id="imageLightbox">
                <button class="image-lightbox-close" onclick="imageLightbox.close()">×</button>
                <div class="image-lightbox-content">
                    <img class="image-lightbox-img" id="lightboxImg" src="" alt="预览">
                </div>
                <div class="image-lightbox-controls">
                    <button class="image-lightbox-btn" onclick="imageLightbox.zoomOut()" title="缩小">
                        <svg viewBox="0 0 24 24" width="18" height="18">
                            <path fill="currentColor" d="M19 13H5v-2h14v2z"/>
                        </svg>
                    </button>
                    <div class="image-lightbox-zoom-level" id="zoomLevel">100%</div>
                    <button class="image-lightbox-btn" onclick="imageLightbox.zoomIn()" title="放大">
                        <svg viewBox="0 0 24 24" width="18" height="18">
                            <path fill="currentColor" d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                        </svg>
                    </button>
                    <button class="image-lightbox-btn" onclick="imageLightbox.reset()" title="重置">
                        <svg viewBox="0 0 24 24" width="18" height="18">
                            <path fill="currentColor" d="M12 5V1L7 6l5 5V7c3.31 0 6 2.69 6 6s-2.69 6-6 6-6-2.69-6-6H4c0 4.42 3.58 8 8 8s8-3.58 8-8-3.58-8-8-8z"/>
                        </svg>
                    </button>
                    <button class="image-lightbox-btn" onclick="imageLightbox.download()" title="下载">
                        <svg viewBox="0 0 24 24" width="18" height="18">
                            <path fill="currentColor" d="M19 12v7H5v-7H3v7c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2v-7h-2zm-6 .67l2.59-2.58L17 11.5l-5 5-5-5 1.41-1.41L11 12.67V3h2z"/>
                        </svg>
                    </button>
                </div>
            </div>
        `;
        
        document.body.insertAdjacentHTML('beforeend', html);
        this.lightbox = document.getElementById('imageLightbox');
        this.img = document.getElementById('lightboxImg');
    }
    
    bindEvents() {
        // 点击背景关闭
        this.lightbox.addEventListener('click', (e) => {
            if (e.target === this.lightbox) {
                this.close();
            }
        });
        
        // 键盘事件
        document.addEventListener('keydown', (e) => {
            if (!this.lightbox.classList.contains('active')) return;
            
            switch(e.key) {
                case 'Escape':
                    this.close();
                    break;
                case '+':
                case '=':
                    this.zoomIn();
                    break;
                case '-':
                    this.zoomOut();
                    break;
                case '0':
                    this.reset();
                    break;
            }
        });
        
        // 鼠标滚轮缩放 - 监听整个灯箱容器
        this.lightbox.addEventListener('wheel', (e) => {
            if (!this.lightbox.classList.contains('active')) return;
            e.preventDefault();
            e.stopPropagation();
            if (e.deltaY < 0) {
                this.zoomIn();
            } else {
                this.zoomOut();
            }
        }, { passive: false });
        
        // 图片上的滚轮缩放
        this.img.addEventListener('wheel', (e) => {
            e.preventDefault();
            e.stopPropagation();
            if (e.deltaY < 0) {
                this.zoomIn();
            } else {
                this.zoomOut();
            }
        }, { passive: false });
        
        // 拖拽功能
        this.img.addEventListener('mousedown', (e) => {
            if (this.currentScale <= 1) return;
            
            this.isDragging = true;
            this.startX = e.clientX - this.translateX;
            this.startY = e.clientY - this.translateY;
            this.img.style.cursor = 'grabbing';
        });
        
        document.addEventListener('mousemove', (e) => {
            if (!this.isDragging) return;
            
            this.translateX = e.clientX - this.startX;
            this.translateY = e.clientY - this.startY;
            this.updateTransform();
        });
        
        document.addEventListener('mouseup', () => {
            this.isDragging = false;
            if (this.currentScale > 1) {
                this.img.style.cursor = 'grab';
            }
        });
    }
    
    autoBindImages() {
        // 自动为所有img标签添加点击放大功能
        const observer = new MutationObserver(() => {
            this.bindAllImages();
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
        
        // 初始绑定
        this.bindAllImages();
    }
    
    bindAllImages() {
        // 排除已经绑定的和不需要放大的图片
        const images = document.querySelectorAll('img:not(.no-lightbox):not(.lightbox-bound)');
        
        images.forEach(img => {
            // 排除小图标和按钮图片
            if (img.width < 50 || img.height < 50) return;
            
            img.classList.add('zoomable-image', 'lightbox-bound');
            img.style.cursor = 'zoom-in';
            
            img.addEventListener('click', (e) => {
                // 如果图片已经有自定义点击事件，不覆盖
                if (img.hasAttribute('onclick')) return;
                
                e.stopPropagation();
                this.open(img.src, img.alt);
            });
        });
    }
    
    open(src, alt = '预览') {
        this.img.src = src;
        this.img.alt = alt;
        this.lightbox.classList.add('active');
        document.body.style.overflow = 'hidden';
        this.reset();
    }
    
    close() {
        this.lightbox.classList.remove('active');
        document.body.style.overflow = '';
        this.reset();
    }
    
    zoomIn() {
        if (this.currentScale >= this.maxScale) return;
        this.currentScale = Math.min(this.currentScale + 0.25, this.maxScale);
        this.updateTransform();
        this.updateZoomLevel();
    }
    
    zoomOut() {
        if (this.currentScale <= this.minScale) return;
        this.currentScale = Math.max(this.currentScale - 0.25, this.minScale);
        this.updateTransform();
        this.updateZoomLevel();
    }
    
    reset() {
        this.currentScale = 1;
        this.translateX = 0;
        this.translateY = 0;
        this.updateTransform();
        this.updateZoomLevel();
        this.img.style.cursor = 'default';
    }
    
    updateTransform() {
        this.img.style.transform = `scale(${this.currentScale}) translate(${this.translateX / this.currentScale}px, ${this.translateY / this.currentScale}px)`;
        this.img.style.cursor = this.currentScale > 1 ? 'grab' : 'default';
    }
    
    updateZoomLevel() {
        const level = Math.round(this.currentScale * 100);
        document.getElementById('zoomLevel').textContent = `${level}%`;
    }
    
    download() {
        const link = document.createElement('a');
        link.href = this.img.src;
        link.download = `image_${Date.now()}.jpg`;
        link.click();
    }
}

// 全局实例
let imageLightbox;

// 页面加载完成后初始化
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
        imageLightbox = new ImageLightbox();
    });
} else {
    imageLightbox = new ImageLightbox();
}

// 导出供外部使用
window.ImageLightbox = ImageLightbox;
window.imageLightbox = imageLightbox;
