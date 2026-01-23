/**
 * 看板图表模块 - 动态 Canvas 图表
 * @module dashboard-charts
 */

import { SUBJECT_COLORS, SUBJECT_MAP, ERROR_TYPE_COLORS } from './dashboard-utils.js';

// ========== 基础动画类 ==========

/**
 * 图表动画器基类
 */
export class ChartAnimator {
    constructor(canvas, options = {}) {
        this.canvas = canvas;
        this.ctx = canvas.getContext('2d');
        this.options = {
            duration: 800,
            easing: 'easeOutCubic',
            ...options
        };
        this.animationFrame = null;
        this.isAnimating = false;
    }
    
    /** 缓动函数 */
    easings = {
        linear: t => t,
        easeOutCubic: t => 1 - Math.pow(1 - t, 3),
        easeOutQuart: t => 1 - Math.pow(1 - t, 4),
        easeInOutCubic: t => t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2,
        easeOutElastic: t => t === 0 ? 0 : t === 1 ? 1 : Math.pow(2, -10 * t) * Math.sin((t * 10 - 0.75) * (2 * Math.PI) / 3) + 1
    };

    /**
     * 获取缓动值
     * @param {number} t - 进度 (0-1)
     * @returns {number}
     */
    ease(t) {
        const fn = this.easings[this.options.easing] || this.easings.easeOutCubic;
        return fn(t);
    }
    
    /**
     * 执行动画
     * @param {Function} drawFn - 绘制函数，接收 progress 参数
     * @param {Function} onComplete - 完成回调
     */
    animate(drawFn, onComplete = null) {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
        }
        
        this.isAnimating = true;
        const startTime = performance.now();
        const duration = this.options.duration;
        
        const loop = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            const easedProgress = this.ease(progress);
            
            this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
            drawFn(easedProgress);
            
            if (progress < 1) {
                this.animationFrame = requestAnimationFrame(loop);
            } else {
                this.isAnimating = false;
                if (onComplete) onComplete();
            }
        };
        
        this.animationFrame = requestAnimationFrame(loop);
    }
    
    /**
     * 停止动画
     */
    stop() {
        if (this.animationFrame) {
            cancelAnimationFrame(this.animationFrame);
            this.animationFrame = null;
        }
        this.isAnimating = false;
    }
    
    /**
     * 清空画布
     */
    clear() {
        this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    }
    
    /**
     * 设置高 DPI 支持
     */
    setupHiDPI() {
        const dpr = window.devicePixelRatio || 1;
        const rect = this.canvas.getBoundingClientRect();
        
        this.canvas.width = rect.width * dpr;
        this.canvas.height = rect.height * dpr;
        this.ctx.scale(dpr, dpr);
        
        this.canvas.style.width = rect.width + 'px';
        this.canvas.style.height = rect.height + 'px';
    }
}


// ========== 饼图类 ==========

/**
 * 动态饼图
 */
export class PieChart extends ChartAnimator {
    constructor(canvas, options = {}) {
        super(canvas, {
            duration: 1000,
            innerRadius: 0.6,  // 甜甜圈内圈比例
            hoverScale: 1.05,
            ...options
        });
        
        this.data = [];
        this.hoveredIndex = -1;
        this.setupInteraction();
    }
    
    /**
     * 设置数据并绘制
     * @param {Array} data - [{label, value, color}]
     * @param {Object} centerText - {title, subtitle}
     */
    setData(data, centerText = null) {
        this.data = data;
        this.centerText = centerText;
        this.total = data.reduce((sum, d) => sum + d.value, 0);
        
        this.animate((progress) => {
            this.draw(progress);
        });
    }
    
    /**
     * 绘制饼图
     * @param {number} progress - 动画进度
     */
    draw(progress = 1) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(centerX, centerY) - 20;
        const innerRadius = radius * this.options.innerRadius;
        
        if (this.total === 0) {
            // 绘制空状态
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
            ctx.fillStyle = '#f5f5f7';
            ctx.fill();
            return;
        }
        
        let startAngle = -Math.PI / 2;
        const animatedAngle = progress * 2 * Math.PI;
        
        this.data.forEach((item, index) => {
            const sliceAngle = (item.value / this.total) * 2 * Math.PI;
            const endAngle = Math.min(startAngle + sliceAngle, -Math.PI / 2 + animatedAngle);
            
            if (endAngle > startAngle) {
                const isHovered = index === this.hoveredIndex;
                const scale = isHovered ? this.options.hoverScale : 1;
                const r = radius * scale;
                
                // 绘制扇形
                ctx.beginPath();
                ctx.moveTo(centerX, centerY);
                ctx.arc(centerX, centerY, r, startAngle, endAngle);
                ctx.closePath();
                ctx.fillStyle = item.color || SUBJECT_COLORS[index % 7];
                ctx.fill();
                
                // 悬停时添加阴影
                if (isHovered) {
                    ctx.shadowColor = 'rgba(0,0,0,0.2)';
                    ctx.shadowBlur = 10;
                    ctx.fill();
                    ctx.shadowColor = 'transparent';
                }
            }
            
            startAngle += sliceAngle;
        });
        
        // 绘制内圆（甜甜圈效果）
        ctx.beginPath();
        ctx.arc(centerX, centerY, innerRadius, 0, 2 * Math.PI);
        ctx.fillStyle = '#ffffff';
        ctx.fill();
        
        // 绘制中心文字
        if (this.centerText && progress >= 1) {
            ctx.fillStyle = '#1d1d1f';
            ctx.font = 'bold 24px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(this.centerText.title || '', centerX, centerY - 8);
            
            ctx.font = '12px -apple-system, sans-serif';
            ctx.fillStyle = '#86868b';
            ctx.fillText(this.centerText.subtitle || '', centerX, centerY + 14);
        }
    }
    
    /**
     * 设置交互
     */
    setupInteraction() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const index = this.getSliceAtPoint(x, y);
            if (index !== this.hoveredIndex) {
                this.hoveredIndex = index;
                this.draw(1);
                
                // 触发悬停事件
                if (this.options.onHover) {
                    this.options.onHover(index >= 0 ? this.data[index] : null, index);
                }
            }
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredIndex = -1;
            this.draw(1);
        });
        
        this.canvas.addEventListener('click', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            const index = this.getSliceAtPoint(x, y);
            if (index >= 0 && this.options.onClick) {
                this.options.onClick(this.data[index], index);
            }
        });
    }
    
    /**
     * 获取点击位置的扇形索引
     */
    getSliceAtPoint(x, y) {
        const centerX = this.canvas.width / 2;
        const centerY = this.canvas.height / 2;
        const radius = Math.min(centerX, centerY) - 20;
        const innerRadius = radius * this.options.innerRadius;
        
        const dx = x - centerX;
        const dy = y - centerY;
        const distance = Math.sqrt(dx * dx + dy * dy);
        
        if (distance < innerRadius || distance > radius) return -1;
        
        let angle = Math.atan2(dy, dx) + Math.PI / 2;
        if (angle < 0) angle += 2 * Math.PI;
        
        let startAngle = 0;
        for (let i = 0; i < this.data.length; i++) {
            const sliceAngle = (this.data[i].value / this.total) * 2 * Math.PI;
            if (angle >= startAngle && angle < startAngle + sliceAngle) {
                return i;
            }
            startAngle += sliceAngle;
        }
        
        return -1;
    }
}


// ========== 雷达图类 ==========

/**
 * 动态雷达图
 */
export class RadarChart extends ChartAnimator {
    constructor(canvas, options = {}) {
        super(canvas, {
            duration: 1000,
            levels: 5,
            maxValue: 100,
            fillOpacity: 0.3,
            ...options
        });
        
        this.data = [];
        this.labels = [];
    }
    
    /**
     * 设置数据并绘制
     * @param {Array} labels - 标签数组
     * @param {Array} datasets - [{label, values, color}]
     */
    setData(labels, datasets) {
        this.labels = labels;
        this.data = datasets;
        
        this.animate((progress) => {
            this.draw(progress);
        });
    }
    
    /**
     * 绘制雷达图
     */
    draw(progress = 1) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(centerX, centerY) - 40;
        const levels = this.options.levels;
        const maxValue = this.options.maxValue;
        const angleStep = (2 * Math.PI) / this.labels.length;
        
        // 绘制背景网格
        ctx.strokeStyle = '#e5e5e5';
        ctx.lineWidth = 1;
        
        for (let level = 1; level <= levels; level++) {
            const levelRadius = (radius / levels) * level;
            ctx.beginPath();
            
            for (let i = 0; i <= this.labels.length; i++) {
                const angle = i * angleStep - Math.PI / 2;
                const x = centerX + levelRadius * Math.cos(angle);
                const y = centerY + levelRadius * Math.sin(angle);
                
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            
            ctx.closePath();
            ctx.stroke();
        }
        
        // 绘制轴线
        for (let i = 0; i < this.labels.length; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();
        }
        
        // 绘制标签
        ctx.fillStyle = '#1d1d1f';
        ctx.font = '12px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        for (let i = 0; i < this.labels.length; i++) {
            const angle = i * angleStep - Math.PI / 2;
            const labelRadius = radius + 20;
            const x = centerX + labelRadius * Math.cos(angle);
            const y = centerY + labelRadius * Math.sin(angle);
            
            ctx.fillText(this.labels[i], x, y);
        }
        
        // 绘制数据区域
        this.data.forEach((dataset, dataIndex) => {
            const color = dataset.color || SUBJECT_COLORS[dataIndex];
            
            ctx.beginPath();
            
            for (let i = 0; i <= this.labels.length; i++) {
                const idx = i % this.labels.length;
                const value = dataset.values[idx] || 0;
                const valueRadius = (value / maxValue) * radius * progress;
                const angle = idx * angleStep - Math.PI / 2;
                const x = centerX + valueRadius * Math.cos(angle);
                const y = centerY + valueRadius * Math.sin(angle);
                
                if (i === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            
            ctx.closePath();
            
            // 填充
            ctx.fillStyle = color + Math.round(this.options.fillOpacity * 255).toString(16).padStart(2, '0');
            ctx.fill();
            
            // 描边
            ctx.strokeStyle = color;
            ctx.lineWidth = 2;
            ctx.stroke();
            
            // 绘制数据点
            for (let i = 0; i < this.labels.length; i++) {
                const value = dataset.values[i] || 0;
                const valueRadius = (value / maxValue) * radius * progress;
                const angle = i * angleStep - Math.PI / 2;
                const x = centerX + valueRadius * Math.cos(angle);
                const y = centerY + valueRadius * Math.sin(angle);
                
                ctx.beginPath();
                ctx.arc(x, y, 4, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.stroke();
            }
        });
    }
}


// ========== 折线图类 ==========

/**
 * 动态折线图
 */
export class LineChart extends ChartAnimator {
    constructor(canvas, options = {}) {
        super(canvas, {
            duration: 1200,
            padding: { top: 20, right: 20, bottom: 40, left: 50 },
            showGrid: true,
            showDots: true,
            smooth: true,
            ...options
        });
        
        this.data = [];
        this.labels = [];
        this.hoveredPoint = null;
        this.setupInteraction();
    }
    
    /**
     * 设置数据并绘制
     * @param {Array} labels - X轴标签
     * @param {Array} datasets - [{label, values, color}]
     */
    setData(labels, datasets) {
        this.labels = labels;
        this.data = datasets;
        
        // 计算Y轴范围
        let minVal = Infinity, maxVal = -Infinity;
        datasets.forEach(ds => {
            ds.values.forEach(v => {
                if (v !== null && v !== undefined) {
                    minVal = Math.min(minVal, v);
                    maxVal = Math.max(maxVal, v);
                }
            });
        });
        
        this.minValue = Math.floor(minVal * 0.9);
        this.maxValue = Math.ceil(maxVal * 1.1);
        if (this.minValue === this.maxValue) {
            this.minValue -= 10;
            this.maxValue += 10;
        }
        
        this.animate((progress) => {
            this.draw(progress);
        });
    }
    
    /**
     * 绘制折线图
     */
    draw(progress = 1) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const padding = this.options.padding;
        
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        
        // 绘制网格
        if (this.options.showGrid) {
            this.drawGrid(chartWidth, chartHeight, padding);
        }
        
        // 绘制X轴标签
        this.drawXLabels(chartWidth, chartHeight, padding);
        
        // 绘制Y轴标签
        this.drawYLabels(chartHeight, padding);
        
        // 绘制数据线
        this.data.forEach((dataset, index) => {
            this.drawLine(dataset, chartWidth, chartHeight, padding, progress, index);
        });
        
        // 绘制悬停点
        if (this.hoveredPoint && progress >= 1) {
            this.drawHoverInfo();
        }
    }
    
    /**
     * 绘制网格
     */
    drawGrid(chartWidth, chartHeight, padding) {
        const ctx = this.ctx;
        const gridLines = 5;
        
        ctx.strokeStyle = '#f0f0f0';
        ctx.lineWidth = 1;
        
        // 水平线
        for (let i = 0; i <= gridLines; i++) {
            const y = padding.top + (chartHeight / gridLines) * i;
            ctx.beginPath();
            ctx.moveTo(padding.left, y);
            ctx.lineTo(padding.left + chartWidth, y);
            ctx.stroke();
        }
        
        // 垂直线
        const xStep = chartWidth / (this.labels.length - 1 || 1);
        for (let i = 0; i < this.labels.length; i++) {
            const x = padding.left + xStep * i;
            ctx.beginPath();
            ctx.moveTo(x, padding.top);
            ctx.lineTo(x, padding.top + chartHeight);
            ctx.stroke();
        }
    }
    
    /**
     * 绘制X轴标签
     */
    drawXLabels(chartWidth, chartHeight, padding) {
        const ctx = this.ctx;
        const xStep = chartWidth / (this.labels.length - 1 || 1);
        
        ctx.fillStyle = '#86868b';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'top';
        
        this.labels.forEach((label, i) => {
            const x = padding.left + xStep * i;
            ctx.fillText(label, x, padding.top + chartHeight + 8);
        });
    }
    
    /**
     * 绘制Y轴标签
     */
    drawYLabels(chartHeight, padding) {
        const ctx = this.ctx;
        const gridLines = 5;
        const valueStep = (this.maxValue - this.minValue) / gridLines;
        
        ctx.fillStyle = '#86868b';
        ctx.font = '11px -apple-system, sans-serif';
        ctx.textAlign = 'right';
        ctx.textBaseline = 'middle';
        
        for (let i = 0; i <= gridLines; i++) {
            const value = this.maxValue - valueStep * i;
            const y = padding.top + (chartHeight / gridLines) * i;
            ctx.fillText(value.toFixed(0) + '%', padding.left - 8, y);
        }
    }
    
    /**
     * 绘制数据线
     */
    drawLine(dataset, chartWidth, chartHeight, padding, progress, index) {
        const ctx = this.ctx;
        const color = dataset.color || SUBJECT_COLORS[index];
        const xStep = chartWidth / (this.labels.length - 1 || 1);
        
        const points = dataset.values.map((value, i) => {
            if (value === null || value === undefined) return null;
            const x = padding.left + xStep * i;
            const y = padding.top + chartHeight - ((value - this.minValue) / (this.maxValue - this.minValue)) * chartHeight;
            return { x, y, value };
        }).filter(p => p !== null);
        
        if (points.length === 0) return;
        
        // 绘制线条
        ctx.beginPath();
        ctx.strokeStyle = color;
        ctx.lineWidth = 2;
        ctx.lineCap = 'round';
        ctx.lineJoin = 'round';
        
        const animatedLength = Math.floor(points.length * progress);
        
        if (this.options.smooth && points.length > 2) {
            // 平滑曲线
            this.drawSmoothLine(points, animatedLength);
        } else {
            // 直线
            points.slice(0, animatedLength + 1).forEach((point, i) => {
                if (i === 0) ctx.moveTo(point.x, point.y);
                else ctx.lineTo(point.x, point.y);
            });
        }
        
        ctx.stroke();
        
        // 绘制数据点
        if (this.options.showDots && progress >= 1) {
            points.forEach(point => {
                ctx.beginPath();
                ctx.arc(point.x, point.y, 4, 0, 2 * Math.PI);
                ctx.fillStyle = color;
                ctx.fill();
                ctx.strokeStyle = '#fff';
                ctx.lineWidth = 2;
                ctx.stroke();
            });
        }
    }
    
    /**
     * 绘制平滑曲线
     */
    drawSmoothLine(points, length) {
        const ctx = this.ctx;
        
        ctx.moveTo(points[0].x, points[0].y);
        
        for (let i = 0; i < Math.min(length, points.length - 1); i++) {
            const p0 = points[Math.max(0, i - 1)];
            const p1 = points[i];
            const p2 = points[i + 1];
            const p3 = points[Math.min(points.length - 1, i + 2)];
            
            const cp1x = p1.x + (p2.x - p0.x) / 6;
            const cp1y = p1.y + (p2.y - p0.y) / 6;
            const cp2x = p2.x - (p3.x - p1.x) / 6;
            const cp2y = p2.y - (p3.y - p1.y) / 6;
            
            ctx.bezierCurveTo(cp1x, cp1y, cp2x, cp2y, p2.x, p2.y);
        }
    }
    
    /**
     * 设置交互
     */
    setupInteraction() {
        this.canvas.addEventListener('mousemove', (e) => {
            const rect = this.canvas.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;
            
            this.hoveredPoint = this.findNearestPoint(x, y);
            this.draw(1);
        });
        
        this.canvas.addEventListener('mouseleave', () => {
            this.hoveredPoint = null;
            this.draw(1);
        });
    }
    
    /**
     * 查找最近的数据点
     */
    findNearestPoint(mouseX, mouseY) {
        const padding = this.options.padding;
        const chartWidth = this.canvas.width - padding.left - padding.right;
        const chartHeight = this.canvas.height - padding.top - padding.bottom;
        const xStep = chartWidth / (this.labels.length - 1 || 1);
        
        let nearest = null;
        let minDist = 20;
        
        this.data.forEach((dataset, dsIndex) => {
            dataset.values.forEach((value, i) => {
                if (value === null || value === undefined) return;
                
                const x = padding.left + xStep * i;
                const y = padding.top + chartHeight - ((value - this.minValue) / (this.maxValue - this.minValue)) * chartHeight;
                const dist = Math.sqrt((mouseX - x) ** 2 + (mouseY - y) ** 2);
                
                if (dist < minDist) {
                    minDist = dist;
                    nearest = {
                        x, y, value,
                        label: this.labels[i],
                        dataset: dataset.label,
                        color: dataset.color || SUBJECT_COLORS[dsIndex]
                    };
                }
            });
        });
        
        return nearest;
    }
    
    /**
     * 绘制悬停信息
     */
    drawHoverInfo() {
        if (!this.hoveredPoint) return;
        
        const ctx = this.ctx;
        const { x, y, value, label, dataset, color } = this.hoveredPoint;
        
        // 高亮点
        ctx.beginPath();
        ctx.arc(x, y, 6, 0, 2 * Math.PI);
        ctx.fillStyle = color;
        ctx.fill();
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 3;
        ctx.stroke();
        
        // 提示框
        const text = `${dataset}: ${value.toFixed(1)}%`;
        ctx.font = '12px -apple-system, sans-serif';
        const textWidth = ctx.measureText(text).width;
        const boxWidth = textWidth + 16;
        const boxHeight = 28;
        let boxX = x - boxWidth / 2;
        let boxY = y - boxHeight - 10;
        
        // 边界检测
        if (boxX < 0) boxX = 0;
        if (boxX + boxWidth > this.canvas.width) boxX = this.canvas.width - boxWidth;
        if (boxY < 0) boxY = y + 10;
        
        // 绘制背景
        ctx.fillStyle = 'rgba(29, 29, 31, 0.9)';
        ctx.beginPath();
        ctx.roundRect(boxX, boxY, boxWidth, boxHeight, 4);
        ctx.fill();
        
        // 绘制文字
        ctx.fillStyle = '#fff';
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        ctx.fillText(text, boxX + boxWidth / 2, boxY + boxHeight / 2);
    }
}


// ========== 柱状图类 ==========

/**
 * 动态柱状图（支持堆叠）
 */
export class BarChart extends ChartAnimator {
    constructor(canvas, options = {}) {
        super(canvas, {
            duration: 800,
            padding: { top: 20, right: 20, bottom: 60, left: 100 },
            horizontal: true,
            stacked: false,
            barHeight: 24,
            barGap: 12,
            ...options
        });
        
        this.data = [];
        this.labels = [];
    }
    
    /**
     * 设置数据并绘制
     * @param {Array} labels - 标签
     * @param {Array} datasets - [{label, values, color}]
     */
    setData(labels, datasets) {
        this.labels = labels;
        this.data = datasets;
        
        // 计算最大值
        if (this.options.stacked) {
            this.maxValue = Math.max(...labels.map((_, i) => 
                datasets.reduce((sum, ds) => sum + (ds.values[i] || 0), 0)
            ));
        } else {
            this.maxValue = Math.max(...datasets.flatMap(ds => ds.values));
        }
        
        this.animate((progress) => {
            this.draw(progress);
        });
    }
    
    /**
     * 绘制柱状图
     */
    draw(progress = 1) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const padding = this.options.padding;
        
        const chartWidth = width - padding.left - padding.right;
        const chartHeight = height - padding.top - padding.bottom;
        
        if (this.options.horizontal) {
            this.drawHorizontal(chartWidth, chartHeight, padding, progress);
        } else {
            this.drawVertical(chartWidth, chartHeight, padding, progress);
        }
    }
    
    /**
     * 绘制水平柱状图
     */
    drawHorizontal(chartWidth, chartHeight, padding, progress) {
        const ctx = this.ctx;
        const barHeight = this.options.barHeight;
        const barGap = this.options.barGap;
        const totalHeight = this.labels.length * (barHeight + barGap);
        const startY = padding.top + (chartHeight - totalHeight) / 2;
        
        this.labels.forEach((label, i) => {
            const y = startY + i * (barHeight + barGap);
            
            // 绘制标签
            ctx.fillStyle = '#1d1d1f';
            ctx.font = '12px -apple-system, sans-serif';
            ctx.textAlign = 'right';
            ctx.textBaseline = 'middle';
            ctx.fillText(label, padding.left - 12, y + barHeight / 2);
            
            if (this.options.stacked) {
                // 堆叠柱状图
                let xOffset = 0;
                this.data.forEach((dataset, dsIndex) => {
                    const value = dataset.values[i] || 0;
                    const barWidth = (value / this.maxValue) * chartWidth * progress;
                    const color = dataset.color || ERROR_TYPE_COLORS[dataset.label] || SUBJECT_COLORS[dsIndex];
                    
                    ctx.fillStyle = color;
                    ctx.beginPath();
                    ctx.roundRect(padding.left + xOffset, y, barWidth, barHeight, 4);
                    ctx.fill();
                    
                    xOffset += barWidth;
                });
            } else {
                // 单一柱状图
                const value = this.data[0]?.values[i] || 0;
                const barWidth = (value / this.maxValue) * chartWidth * progress;
                const color = this.getBarColor(value);
                
                // 背景条
                ctx.fillStyle = '#f0f0f0';
                ctx.beginPath();
                ctx.roundRect(padding.left, y, chartWidth, barHeight, 4);
                ctx.fill();
                
                // 数据条
                ctx.fillStyle = color;
                ctx.beginPath();
                ctx.roundRect(padding.left, y, barWidth, barHeight, 4);
                ctx.fill();
                
                // 数值标签
                if (progress >= 1) {
                    ctx.fillStyle = '#1d1d1f';
                    ctx.textAlign = 'left';
                    ctx.fillText(`${value.toFixed(1)}%`, padding.left + barWidth + 8, y + barHeight / 2);
                }
            }
        });
        
        // 绘制图例（堆叠模式）
        if (this.options.stacked && progress >= 1) {
            this.drawLegend(padding);
        }
    }
    
    /**
     * 绘制垂直柱状图
     */
    drawVertical(chartWidth, chartHeight, padding, progress) {
        const ctx = this.ctx;
        const barWidth = Math.min(40, chartWidth / this.labels.length - 10);
        const barGap = (chartWidth - barWidth * this.labels.length) / (this.labels.length + 1);
        
        this.labels.forEach((label, i) => {
            const x = padding.left + barGap + i * (barWidth + barGap);
            
            // 绘制标签
            ctx.fillStyle = '#86868b';
            ctx.font = '11px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'top';
            ctx.fillText(label, x + barWidth / 2, padding.top + chartHeight + 8);
            
            const value = this.data[0]?.values[i] || 0;
            const barHeight = (value / this.maxValue) * chartHeight * progress;
            const color = this.getBarColor(value);
            
            // 数据条
            ctx.fillStyle = color;
            ctx.beginPath();
            ctx.roundRect(x, padding.top + chartHeight - barHeight, barWidth, barHeight, [4, 4, 0, 0]);
            ctx.fill();
        });
    }
    
    /**
     * 根据值获取颜色
     */
    getBarColor(value) {
        if (value >= 90) return '#10b981';
        if (value >= 80) return '#f59e0b';
        return '#ef4444';
    }
    
    /**
     * 绘制图例
     */
    drawLegend(padding) {
        const ctx = this.ctx;
        const legendY = this.canvas.height - 20;
        let legendX = padding.left;
        
        this.data.forEach((dataset, i) => {
            const color = dataset.color || ERROR_TYPE_COLORS[dataset.label] || SUBJECT_COLORS[i];
            
            // 色块
            ctx.fillStyle = color;
            ctx.fillRect(legendX, legendY - 6, 12, 12);
            
            // 文字
            ctx.fillStyle = '#86868b';
            ctx.font = '11px -apple-system, sans-serif';
            ctx.textAlign = 'left';
            ctx.textBaseline = 'middle';
            ctx.fillText(dataset.label, legendX + 16, legendY);
            
            legendX += ctx.measureText(dataset.label).width + 32;
        });
    }
}


// ========== 进度环类 ==========

/**
 * 动态进度环
 */
export class ProgressRing extends ChartAnimator {
    constructor(canvas, options = {}) {
        super(canvas, {
            duration: 1000,
            lineWidth: 8,
            bgColor: '#f0f0f0',
            ...options
        });
    }
    
    /**
     * 设置进度并绘制
     * @param {number} value - 进度值 (0-100)
     * @param {string} color - 颜色
     * @param {Object} centerText - {title, subtitle}
     */
    setValue(value, color = '#10b981', centerText = null) {
        this.value = Math.min(100, Math.max(0, value));
        this.color = color;
        this.centerText = centerText;
        
        this.animate((progress) => {
            this.draw(progress);
        });
    }
    
    /**
     * 绘制进度环
     */
    draw(progress = 1) {
        const ctx = this.ctx;
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(centerX, centerY) - this.options.lineWidth;
        
        // 背景环
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = this.options.bgColor;
        ctx.lineWidth = this.options.lineWidth;
        ctx.lineCap = 'round';
        ctx.stroke();
        
        // 进度环
        const endAngle = -Math.PI / 2 + (this.value / 100) * 2 * Math.PI * progress;
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, -Math.PI / 2, endAngle);
        ctx.strokeStyle = this.color;
        ctx.stroke();
        
        // 中心文字
        if (this.centerText && progress >= 1) {
            ctx.fillStyle = '#1d1d1f';
            ctx.font = 'bold 20px -apple-system, sans-serif';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            ctx.fillText(this.centerText.title || '', centerX, centerY - 6);
            
            if (this.centerText.subtitle) {
                ctx.font = '11px -apple-system, sans-serif';
                ctx.fillStyle = '#86868b';
                ctx.fillText(this.centerText.subtitle, centerX, centerY + 14);
            }
        }
    }
}

// ========== 数字动画 ==========

/**
 * 数字滚动动画
 * @param {HTMLElement} element - 目标元素
 * @param {number} endValue - 目标值
 * @param {Object} options - 配置
 */
export function animateNumber(element, endValue, options = {}) {
    const {
        duration = 800,
        decimals = 0,
        prefix = '',
        suffix = '',
        easing = 'easeOutCubic'
    } = options;
    
    const startValue = parseFloat(element.textContent.replace(/[^0-9.-]/g, '')) || 0;
    const startTime = performance.now();
    
    const easings = {
        linear: t => t,
        easeOutCubic: t => 1 - Math.pow(1 - t, 3)
    };
    
    const ease = easings[easing] || easings.easeOutCubic;
    
    function update(currentTime) {
        const elapsed = currentTime - startTime;
        const progress = Math.min(elapsed / duration, 1);
        const easedProgress = ease(progress);
        
        const currentValue = startValue + (endValue - startValue) * easedProgress;
        element.textContent = prefix + currentValue.toFixed(decimals) + suffix;
        
        if (progress < 1) {
            requestAnimationFrame(update);
        }
    }
    
    requestAnimationFrame(update);
}

// ========== 导出工厂函数 ==========

/**
 * 创建图表实例
 * @param {string} type - 图表类型
 * @param {HTMLCanvasElement} canvas - 画布元素
 * @param {Object} options - 配置
 * @returns {ChartAnimator}
 */
export function createChart(type, canvas, options = {}) {
    switch (type) {
        case 'pie':
            return new PieChart(canvas, options);
        case 'radar':
            return new RadarChart(canvas, options);
        case 'line':
            return new LineChart(canvas, options);
        case 'bar':
            return new BarChart(canvas, options);
        case 'progress':
            return new ProgressRing(canvas, options);
        default:
            throw new Error(`Unknown chart type: ${type}`);
    }
}

export default {
    ChartAnimator,
    PieChart,
    RadarChart,
    LineChart,
    BarChart,
    ProgressRing,
    animateNumber,
    createChart
};
