/**
 * 进度条组件
 */
class ProgressRing {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        this.options = {
            size: options.size || 120,
            strokeWidth: options.strokeWidth || 8,
            color: options.color || '#1d1d1f',
            bgColor: options.bgColor || '#e5e5e5',
            ...options
        };
        this.progress = 0;
        this.render();
    }

    render() {
        const { size, strokeWidth, color, bgColor } = this.options;
        const radius = (size - strokeWidth) / 2;
        const circumference = 2 * Math.PI * radius;
        
        this.container.innerHTML = `
            <div class="progress-ring-wrapper" style="position: relative; width: ${size}px; height: ${size}px;">
                <svg viewBox="0 0 ${size} ${size}" style="transform: rotate(-90deg);">
                    <circle 
                        cx="${size/2}" cy="${size/2}" r="${radius}"
                        fill="none" stroke="${bgColor}" stroke-width="${strokeWidth}"
                    />
                    <circle 
                        class="progress-ring-bar"
                        cx="${size/2}" cy="${size/2}" r="${radius}"
                        fill="none" stroke="${color}" stroke-width="${strokeWidth}"
                        stroke-linecap="round"
                        stroke-dasharray="${circumference}"
                        stroke-dashoffset="${circumference}"
                        style="transition: stroke-dashoffset 0.3s ease;"
                    />
                </svg>
                <div class="progress-ring-text" style="
                    position: absolute;
                    top: 50%;
                    left: 50%;
                    transform: translate(-50%, -50%);
                    font-size: 24px;
                    font-weight: 600;
                ">0%</div>
            </div>
        `;
        
        this.bar = this.container.querySelector('.progress-ring-bar');
        this.text = this.container.querySelector('.progress-ring-text');
        this.circumference = circumference;
    }

    setProgress(percent) {
        this.progress = Math.min(100, Math.max(0, percent));
        const offset = this.circumference - (this.progress / 100) * this.circumference;
        this.bar.style.strokeDashoffset = offset;
        this.text.textContent = `${Math.round(this.progress)}%`;
    }

    getProgress() {
        return this.progress;
    }
}

/**
 * 分析进度轮询器
 */
class AnalysisProgressPoller {
    constructor(taskId, options = {}) {
        this.taskId = taskId;
        this.options = {
            interval: options.interval || 2000,
            onProgress: options.onProgress || (() => {}),
            onComplete: options.onComplete || (() => {}),
            onError: options.onError || (() => {}),
            ...options
        };
        this.polling = false;
        this.intervalId = null;
        this.startTime = null;
    }

    start() {
        if (this.polling) return;
        
        this.polling = true;
        this.startTime = Date.now();
        this.poll();
        this.intervalId = setInterval(() => this.poll(), this.options.interval);
    }

    stop() {
        this.polling = false;
        if (this.intervalId) {
            clearInterval(this.intervalId);
            this.intervalId = null;
        }
    }

    async poll() {
        if (!this.polling) return;
        
        try {
            const response = await fetch('/api/analysis/queue');
            const result = await response.json();
            
            if (!result.success) {
                this.options.onError(result.error || '获取状态失败');
                return;
            }
            
            const running = result.data.running || [];
            const task = running.find(t => t.task_id === this.taskId);
            
            if (task) {
                const elapsed = Date.now() - this.startTime;
                const estimatedRemaining = task.progress > 0 
                    ? Math.round((elapsed / task.progress) * (100 - task.progress) / 1000)
                    : null;
                
                this.options.onProgress({
                    progress: task.progress || 0,
                    step: task.step || '分析中...',
                    estimatedRemaining
                });
            } else {
                // 检查是否完成
                const completed = result.data.recent_completed || [];
                const failed = result.data.recent_failed || [];
                
                if (completed.some(t => t.task_id === this.taskId)) {
                    this.stop();
                    this.options.onComplete();
                } else if (failed.some(t => t.task_id === this.taskId)) {
                    this.stop();
                    const failedTask = failed.find(t => t.task_id === this.taskId);
                    this.options.onError(failedTask?.error || '分析失败');
                }
            }
        } catch (error) {
            console.error('轮询失败:', error);
            this.options.onError('网络错误');
        }
    }
}

window.ProgressRing = ProgressRing;
window.AnalysisProgressPoller = AnalysisProgressPoller;
