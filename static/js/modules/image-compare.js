/**
 * 图片对比模块 (US-23)
 * @module ImageCompare
 */

/**
 * 图片对比API
 */
export const ImageCompareAPI = {
    /**
     * 获取作业图片信息
     */
    getHomeworkImage: async (homeworkId) => {
        const response = await fetch(`/api/image-compare/${homeworkId}`);
        return response.json();
    },
    
    /**
     * 获取任务下所有图片
     */
    getTaskImages: async (taskId, page = 1, pageSize = 10) => {
        const response = await fetch(
            `/api/image-compare/task/${taskId}?page=${page}&page_size=${pageSize}`
        );
        return response.json();
    }
};

/**
 * 图片对比查看器类
 */
export class ImageCompareViewer {
    constructor(modalId) {
        this.modal = document.getElementById(modalId);
        this.currentIndex = 0;
        this.images = [];
        this.scale = 1;
        this.position = { x: 0, y: 0 };
        this.isDragging = false;
        this.dragStart = { x: 0, y: 0 };
        
        this.initElements();
        this.bindEvents();
    }
    
    /**
     * 初始化元素引用
     */
    initElements() {
        if (!this.modal) return;
        
        this.imageWrapper = this.modal.querySelector('.image-wrapper');
        this.originalImage = this.modal.querySelector('#originalImage');
        this.resultContent = this.modal.querySelector('#recognitionResult');
        this.baseAnswerEl = this.modal.querySelector('#baseAnswer');
        this.aiAnswerEl = this.modal.querySelector('#aiAnswer');
        this.errorTypeEl = this.modal.querySelector('#errorType');
        this.currentIndexEl = this.modal.querySelector('#currentIndex');
        this.totalCountEl = this.modal.querySelector('#totalCount');
        this.zoomLevelEl = this.modal.querySelector('#zoomLevel');
        this.prevBtn = this.modal.querySelector('#prevBtn');
        this.nextBtn = this.modal.querySelector('#nextBtn');
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        if (!this.modal) return;
        
        // 关闭按钮
        const closeBtn = this.modal.querySelector('.close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }
        
        // 点击遮罩关闭
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) this.close();
        });
        
        // 缩放事件
        if (this.imageWrapper) {
            this.imageWrapper.addEventListener('wheel', (e) => {
                e.preventDefault();
                const delta = e.deltaY > 0 ? -0.1 : 0.1;
                this.zoom(delta);
            });
            
            // 拖拽事件
            this.imageWrapper.addEventListener('mousedown', (e) => this.startDrag(e));
            document.addEventListener('mousemove', (e) => this.drag(e));
            document.addEventListener('mouseup', () => this.endDrag());
        }
        
        // 键盘事件
        document.addEventListener('keydown', (e) => {
            if (this.modal.style.display !== 'flex') return;
            
            if (e.key === 'ArrowLeft') this.prev();
            else if (e.key === 'ArrowRight') this.next();
            else if (e.key === 'Escape') this.close();
            else if (e.key === '+' || e.key === '=') this.zoom(0.1);
            else if (e.key === '-') this.zoom(-0.1);
        });
    }

    
    /**
     * 打开查看器
     * @param {Array} images - 图片数据列表
     * @param {number} startIndex - 起始索引
     */
    open(images, startIndex = 0) {
        this.images = images;
        this.currentIndex = startIndex;
        this.scale = 1;
        this.position = { x: 0, y: 0 };
        
        this.showImage(this.currentIndex);
        this.modal.style.display = 'flex';
    }
    
    /**
     * 关闭查看器
     */
    close() {
        this.modal.style.display = 'none';
        this.images = [];
        this.currentIndex = 0;
    }
    
    /**
     * 显示指定索引的图片
     */
    showImage(index) {
        if (index < 0 || index >= this.images.length) return;
        
        const imageData = this.images[index];
        this.currentIndex = index;
        
        // 更新图片
        if (this.originalImage && imageData.pic_url) {
            this.originalImage.src = imageData.pic_url;
            this.resetTransform();
        }
        
        // 更新识别结果
        if (this.resultContent) {
            this.resultContent.innerHTML = this.formatRecognitionResult(imageData.homework_result);
        }
        
        // 更新答案信息
        if (this.baseAnswerEl) {
            this.baseAnswerEl.textContent = imageData.base_answer || '-';
        }
        if (this.aiAnswerEl) {
            this.aiAnswerEl.textContent = imageData.hw_user || '-';
        }
        if (this.errorTypeEl) {
            this.errorTypeEl.textContent = imageData.error_type || '-';
            this.errorTypeEl.className = 'value tag ' + this.getErrorTypeClass(imageData.error_type);
        }
        
        // 更新导航
        if (this.currentIndexEl) {
            this.currentIndexEl.textContent = index + 1;
        }
        if (this.totalCountEl) {
            this.totalCountEl.textContent = this.images.length;
        }
        
        // 更新按钮状态
        if (this.prevBtn) {
            this.prevBtn.disabled = index <= 0;
        }
        if (this.nextBtn) {
            this.nextBtn.disabled = index >= this.images.length - 1;
        }
    }
    
    /**
     * 格式化识别结果
     */
    formatRecognitionResult(resultStr) {
        if (!resultStr) return '<div class="empty-state">无识别结果</div>';
        
        try {
            const result = typeof resultStr === 'string' ? JSON.parse(resultStr) : resultStr;
            
            if (!Array.isArray(result) || result.length === 0) {
                return '<div class="empty-state">无识别结果</div>';
            }
            
            let html = '<div class="recognition-list">';
            for (const item of result) {
                const index = item.index || item.tempIndex || '?';
                const answer = item.user || item.answer || '-';
                const isCorrect = item.isCorrect === 'yes' || item.isCorrect === true;
                
                html += `
                    <div class="recognition-item ${isCorrect ? 'correct' : 'incorrect'}">
                        <span class="item-index">${index}</span>
                        <span class="item-answer">${answer}</span>
                        <span class="item-status">${isCorrect ? '正确' : '错误'}</span>
                    </div>
                `;
            }
            html += '</div>';
            return html;
        } catch (e) {
            return `<div class="result-raw">${resultStr}</div>`;
        }
    }
    
    /**
     * 获取错误类型样式类
     */
    getErrorTypeClass(errorType) {
        if (!errorType) return 'tag-default';
        
        if (errorType.includes('判断错误') || errorType.includes('幻觉') || errorType.includes('缺失')) {
            return 'tag-error';
        } else if (errorType.includes('识别错误')) {
            return 'tag-warning';
        }
        return 'tag-default';
    }
    
    /**
     * 上一张
     */
    prev() {
        if (this.currentIndex > 0) {
            this.showImage(this.currentIndex - 1);
        }
    }
    
    /**
     * 下一张
     */
    next() {
        if (this.currentIndex < this.images.length - 1) {
            this.showImage(this.currentIndex + 1);
        }
    }
    
    /**
     * 缩放
     */
    zoom(delta) {
        this.scale = Math.max(0.5, Math.min(3, this.scale + delta));
        this.updateTransform();
        
        if (this.zoomLevelEl) {
            this.zoomLevelEl.textContent = Math.round(this.scale * 100) + '%';
        }
    }
    
    /**
     * 重置缩放
     */
    resetZoom() {
        this.scale = 1;
        this.position = { x: 0, y: 0 };
        this.updateTransform();
        
        if (this.zoomLevelEl) {
            this.zoomLevelEl.textContent = '100%';
        }
    }
    
    /**
     * 重置变换
     */
    resetTransform() {
        this.scale = 1;
        this.position = { x: 0, y: 0 };
        this.updateTransform();
    }
    
    /**
     * 更新变换
     */
    updateTransform() {
        if (this.originalImage) {
            this.originalImage.style.transform = 
                `translate(${this.position.x}px, ${this.position.y}px) scale(${this.scale})`;
        }
    }
    
    /**
     * 开始拖拽
     */
    startDrag(e) {
        if (e.button !== 0) return;
        this.isDragging = true;
        this.dragStart = { x: e.clientX - this.position.x, y: e.clientY - this.position.y };
        if (this.imageWrapper) {
            this.imageWrapper.style.cursor = 'grabbing';
        }
    }
    
    /**
     * 拖拽中
     */
    drag(e) {
        if (!this.isDragging) return;
        this.position = {
            x: e.clientX - this.dragStart.x,
            y: e.clientY - this.dragStart.y
        };
        this.updateTransform();
    }
    
    /**
     * 结束拖拽
     */
    endDrag() {
        this.isDragging = false;
        if (this.imageWrapper) {
            this.imageWrapper.style.cursor = 'grab';
        }
    }
}

export default ImageCompareViewer;
