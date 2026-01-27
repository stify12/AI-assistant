/**
 * 异常检测模块 (US-26)
 * @module AnomalyDetection
 */

// 异常类型映射
const ANOMALY_TYPE_MAP = {
    accuracy_drop: { label: '准确率下降', icon: 'down' },
    accuracy_spike: { label: '准确率异常升高', icon: 'up' },
    error_surge: { label: '错误激增', icon: 'alert' },
    task_failure: { label: '任务失败', icon: 'error' }
};

// 严重程度映射
const SEVERITY_MAP = {
    low: { label: '低', class: 'tag-success' },
    medium: { label: '中', class: 'tag-warning' },
    high: { label: '高', class: 'tag-error' },
    critical: { label: '严重', class: 'tag-error' }
};

/**
 * 异常检测API
 */
export const AnomalyAPI = {
    /**
     * 获取异常日志列表
     */
    getLogs: async (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`/api/anomaly/logs?${query}`);
        return response.json();
    },
    
    /**
     * 获取统计数据
     */
    getStatistics: async () => {
        const response = await fetch('/api/anomaly/statistics');
        return response.json();
    },
    
    /**
     * 手动触发检测
     */
    detect: async (taskId) => {
        const response = await fetch('/api/anomaly/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId })
        });
        return response.json();
    },
    
    /**
     * 确认异常
     */
    acknowledge: async (anomalyId) => {
        const response = await fetch(`/api/anomaly/${anomalyId}/acknowledge`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' }
        });
        return response.json();
    },
    
    /**
     * 设置阈值
     */
    setThreshold: async (threshold) => {
        const response = await fetch('/api/anomaly/threshold', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ threshold_sigma: threshold })
        });
        return response.json();
    },
    
    /**
     * 导出异常检测结果到Excel
     */
    exportToExcel: (taskId) => {
        window.location.href = `/api/anomaly/task/${taskId}/export`;
    }
};


/**
 * 异常检测管理器类
 */
export class AnomalyManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentPage = 1;
        this.pageSize = 20;
        this.filters = { is_acknowledged: 'false' };
    }
    
    /**
     * 初始化
     */
    async init() {
        await this.loadStatistics();
        await this.loadLogs();
        this.bindEvents();
    }
    
    /**
     * 加载统计数据
     */
    async loadStatistics() {
        try {
            const result = await AnomalyAPI.getStatistics();
            if (result.success) {
                this.renderStatistics(result.data);
            }
        } catch (e) {
            console.error('加载异常统计失败:', e);
        }
    }
    
    /**
     * 加载异常日志
     */
    async loadLogs() {
        try {
            const params = {
                page: this.currentPage,
                page_size: this.pageSize,
                ...this.filters
            };
            
            const result = await AnomalyAPI.getLogs(params);
            if (result.success) {
                this.renderLogs(result.data);
            }
        } catch (e) {
            console.error('加载异常日志失败:', e);
        }
    }
    
    /**
     * 渲染统计数据
     */
    renderStatistics(data) {
        const statsContainer = document.getElementById('anomalyStats');
        if (!statsContainer) return;
        
        statsContainer.innerHTML = `
            <div class="stat-card ${data.unacknowledged > 0 ? 'stat-warning' : ''}">
                <div class="stat-value">${data.unacknowledged || 0}</div>
                <div class="stat-label">待确认</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${data.today_count || 0}</div>
                <div class="stat-label">今日异常</div>
            </div>
        `;
    }
    
    /**
     * 渲染异常日志列表
     */
    renderLogs(data) {
        const listContainer = document.getElementById('anomalyList');
        if (!listContainer) return;
        
        if (!data.items || data.items.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">暂无异常记录</div>';
            return;
        }
        
        let html = '';
        for (const log of data.items) {
            const typeInfo = ANOMALY_TYPE_MAP[log.anomaly_type] || { label: log.anomaly_type };
            const severityInfo = SEVERITY_MAP[log.severity] || SEVERITY_MAP.medium;
            const isAcknowledged = log.is_acknowledged;
            
            html += `
                <div class="anomaly-item ${isAcknowledged ? 'acknowledged' : ''}" 
                     data-anomaly-id="${log.anomaly_id}">
                    <div class="anomaly-icon ${log.severity}">
                        <span class="icon-${typeInfo.icon || 'alert'}"></span>
                    </div>
                    <div class="anomaly-info">
                        <div class="anomaly-title">${typeInfo.label}</div>
                        <div class="anomaly-message">${log.message || ''}</div>
                        <div class="anomaly-meta">
                            <span class="tag ${severityInfo.class}">${severityInfo.label}</span>
                            <span class="anomaly-time">${this.formatTime(log.created_at)}</span>
                        </div>
                    </div>
                    <div class="anomaly-actions">
                        ${isAcknowledged ? 
                            '<span class="tag tag-success">已确认</span>' :
                            `<button class="btn btn-sm" onclick="window.anomalyManager.acknowledge('${log.anomaly_id}')">确认</button>`
                        }
                    </div>
                </div>
            `;
        }
        
        listContainer.innerHTML = html;
    }
    
    /**
     * 确认异常
     */
    async acknowledge(anomalyId) {
        try {
            const result = await AnomalyAPI.acknowledge(anomalyId);
            if (result.success) {
                await this.loadLogs();
                await this.loadStatistics();
                this.showToast('已确认');
            } else {
                this.showToast(result.error || '确认失败', 'error');
            }
        } catch (e) {
            this.showToast('确认失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 设置阈值
     */
    async setThreshold(threshold) {
        try {
            const result = await AnomalyAPI.setThreshold(threshold);
            if (result.success) {
                this.showToast(result.message);
            } else {
                this.showToast(result.error || '设置失败', 'error');
            }
        } catch (e) {
            this.showToast('设置失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 手动检测
     */
    async detectTask(taskId) {
        try {
            const result = await AnomalyAPI.detect(taskId);
            if (result.success) {
                if (result.data) {
                    this.showToast('检测到异常: ' + result.data.message, 'warning');
                    await this.loadLogs();
                    await this.loadStatistics();
                } else {
                    this.showToast('未检测到异常');
                }
            } else {
                this.showToast(result.error || '检测失败', 'error');
            }
        } catch (e) {
            this.showToast('检测失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 切换筛选
     */
    toggleFilter(key, value) {
        if (this.filters[key] === value) {
            delete this.filters[key];
        } else {
            this.filters[key] = value;
        }
        this.currentPage = 1;
        this.loadLogs();
    }
    
    /**
     * 格式化时间
     */
    formatTime(isoString) {
        if (!isoString) return '';
        const date = new Date(isoString);
        return date.toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 阈值设置
        const thresholdInput = document.getElementById('anomalyThreshold');
        const saveThresholdBtn = document.getElementById('saveThresholdBtn');
        
        if (thresholdInput && saveThresholdBtn) {
            saveThresholdBtn.addEventListener('click', () => {
                const value = parseFloat(thresholdInput.value);
                if (value >= 1 && value <= 5) {
                    this.setThreshold(value);
                } else {
                    this.showToast('阈值必须在 1-5 之间', 'error');
                }
            });
        }
    }
    
    /**
     * 显示提示
     */
    showToast(message, type = 'success') {
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
}

export { ANOMALY_TYPE_MAP, SEVERITY_MAP };
