/**
 * 错误样本库模块 (US-19)
 * @module ErrorSamples
 */

// 状态映射
const STATUS_MAP = {
    pending: { label: '待分析', class: 'tag-default' },
    analyzed: { label: '已分析', class: 'tag-info' },
    fixed: { label: '已修复', class: 'tag-success' },
    ignored: { label: '已忽略', class: 'tag-muted' }
};

// 严重程度映射
const SEVERITY_MAP = {
    high: { label: '高', class: 'tag-error' },
    medium: { label: '中', class: 'tag-warning' },
    low: { label: '低', class: 'tag-success' }
};

// 学科映射
const SUBJECT_MAP = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理',
    4: '化学', 5: '生物', 6: '地理'
};

/**
 * 错误样本API
 */
export const ErrorSamplesAPI = {
    /**
     * 获取样本列表
     * @param {Object} params - 查询参数
     * @returns {Promise<Object>}
     */
    getSamples: async (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`/api/error-samples?${query}`);
        return response.json();
    },
    
    /**
     * 获取统计数据
     * @returns {Promise<Object>}
     */
    getStatistics: async () => {
        const response = await fetch('/api/error-samples/statistics');
        return response.json();
    },
    
    /**
     * 获取样本详情
     * @param {string} sampleId - 样本ID
     * @returns {Promise<Object>}
     */
    getDetail: async (sampleId) => {
        const response = await fetch(`/api/error-samples/${sampleId}`);
        return response.json();
    },

    /**
     * 批量更新状态
     * @param {string[]} sampleIds - 样本ID列表
     * @param {string} status - 新状态
     * @param {string} notes - 备注
     * @returns {Promise<Object>}
     */
    batchUpdateStatus: async (sampleIds, status, notes = '') => {
        const response = await fetch('/api/error-samples/batch-status', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_ids: sampleIds, status, notes })
        });
        return response.json();
    },
    
    /**
     * 从任务收集样本
     * @param {string} taskId - 任务ID
     * @returns {Promise<Object>}
     */
    collectFromTask: async (taskId) => {
        const response = await fetch('/api/error-samples/collect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId })
        });
        return response.json();
    },
    
    /**
     * 导出样本
     * @param {Object} filters - 筛选条件
     * @param {string} format - 导出格式
     */
    exportSamples: async (filters = {}, format = 'xlsx') => {
        const response = await fetch('/api/error-samples/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ filters, format })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `error_samples.${format}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            const result = await response.json();
            throw new Error(result.error || '导出失败');
        }
    }
};

/**
 * 错误样本管理器类
 */
export class ErrorSamplesManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.currentPage = 1;
        this.pageSize = 20;
        this.filters = {};
        this.selectedIds = new Set();
        this.samples = [];
    }
    
    /**
     * 初始化
     */
    async init() {
        await this.loadStatistics();
        await this.loadSamples();
        this.bindEvents();
    }
    
    /**
     * 加载统计数据
     */
    async loadStatistics() {
        try {
            const result = await ErrorSamplesAPI.getStatistics();
            if (result.success) {
                this.renderStatistics(result.data);
            }
        } catch (e) {
            console.error('加载统计失败:', e);
        }
    }
    
    /**
     * 加载样本列表
     */
    async loadSamples() {
        try {
            const params = {
                page: this.currentPage,
                page_size: this.pageSize,
                ...this.filters
            };
            
            const result = await ErrorSamplesAPI.getSamples(params);
            if (result.success) {
                this.samples = result.data.items;
                this.renderSamples(result.data);
                this.renderPagination(result.data);
            }
        } catch (e) {
            console.error('加载样本失败:', e);
        }
    }

    
    /**
     * 渲染统计数据
     */
    renderStatistics(data) {
        const statsContainer = document.getElementById('errorSamplesStats');
        if (!statsContainer) return;
        
        const total = data.total || 0;
        const byStatus = data.by_status || {};
        const pending = byStatus.pending || 0;
        const analyzed = byStatus.analyzed || 0;
        const fixed = byStatus.fixed || 0;
        
        statsContainer.innerHTML = `
            <div class="stat-card">
                <div class="stat-value">${total}</div>
                <div class="stat-label">总样本</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #e65100;">${pending}</div>
                <div class="stat-label">待分析</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #1565c0;">${analyzed}</div>
                <div class="stat-label">已分析</div>
            </div>
            <div class="stat-card">
                <div class="stat-value" style="color: #1e7e34;">${fixed}</div>
                <div class="stat-label">已修复</div>
            </div>
        `;
    }
    
    /**
     * 渲染样本列表
     */
    renderSamples(data) {
        const listContainer = document.getElementById('errorSamplesList');
        if (!listContainer) return;
        
        if (!data.items || data.items.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">暂无错误样本</div>';
            return;
        }
        
        let html = '';
        for (const sample of data.items) {
            const statusInfo = STATUS_MAP[sample.status] || STATUS_MAP.pending;
            const severityInfo = SEVERITY_MAP[sample.severity] || SEVERITY_MAP.medium;
            const subjectName = SUBJECT_MAP[sample.subject_id] || '未知';
            const isSelected = this.selectedIds.has(sample.sample_id);
            
            html += `
                <div class="sample-item ${isSelected ? 'selected' : ''}" 
                     data-sample-id="${sample.sample_id}">
                    <input type="checkbox" class="sample-checkbox" 
                           ${isSelected ? 'checked' : ''}
                           onchange="window.errorSamplesManager.toggleSelect('${sample.sample_id}')">
                    <div class="sample-info" onclick="window.errorSamplesManager.showDetail('${sample.sample_id}')">
                        <div class="sample-title">
                            ${sample.book_name || '未知书本'} - P${sample.page_num || '?'} - 第${sample.question_index}题
                        </div>
                        <div class="sample-meta">
                            <span>${subjectName}</span>
                            <span class="tag ${severityInfo.class}">${sample.error_type}</span>
                        </div>
                    </div>
                    <div class="sample-status">
                        <span class="tag ${statusInfo.class}">${statusInfo.label}</span>
                    </div>
                </div>
            `;
        }
        
        listContainer.innerHTML = html;
        this.updateBatchActions();
    }
    
    /**
     * 渲染分页
     */
    renderPagination(data) {
        const paginationContainer = document.getElementById('errorSamplesPagination');
        if (!paginationContainer) return;
        
        const { page, total_pages } = data;
        
        if (total_pages <= 1) {
            paginationContainer.innerHTML = '';
            return;
        }
        
        let html = '<div class="pagination">';
        
        // 上一页
        html += `<button class="btn btn-sm" ${page <= 1 ? 'disabled' : ''} 
                  onclick="window.errorSamplesManager.goToPage(${page - 1})">上一页</button>`;
        
        // 页码
        html += `<span class="page-info">${page} / ${total_pages}</span>`;
        
        // 下一页
        html += `<button class="btn btn-sm" ${page >= total_pages ? 'disabled' : ''} 
                  onclick="window.errorSamplesManager.goToPage(${page + 1})">下一页</button>`;
        
        html += '</div>';
        paginationContainer.innerHTML = html;
    }

    
    /**
     * 切换选择
     */
    toggleSelect(sampleId) {
        if (this.selectedIds.has(sampleId)) {
            this.selectedIds.delete(sampleId);
        } else {
            this.selectedIds.add(sampleId);
        }
        
        // 更新UI
        const item = document.querySelector(`[data-sample-id="${sampleId}"]`);
        if (item) {
            item.classList.toggle('selected', this.selectedIds.has(sampleId));
        }
        
        this.updateBatchActions();
    }
    
    /**
     * 全选/取消全选
     */
    toggleSelectAll() {
        const allSelected = this.selectedIds.size === this.samples.length;
        
        if (allSelected) {
            this.selectedIds.clear();
        } else {
            this.samples.forEach(s => this.selectedIds.add(s.sample_id));
        }
        
        this.renderSamples({ items: this.samples });
    }
    
    /**
     * 更新批量操作栏
     */
    updateBatchActions() {
        const batchActions = document.getElementById('errorSamplesBatchActions');
        const selectedCount = document.getElementById('errorSamplesSelectedCount');
        
        if (batchActions) {
            batchActions.style.display = this.selectedIds.size > 0 ? 'flex' : 'none';
        }
        if (selectedCount) {
            selectedCount.textContent = this.selectedIds.size;
        }
    }
    
    /**
     * 批量更新状态
     */
    async batchUpdateStatus(status) {
        if (this.selectedIds.size === 0) return;
        
        try {
            const result = await ErrorSamplesAPI.batchUpdateStatus(
                Array.from(this.selectedIds), status
            );
            
            if (result.success) {
                this.selectedIds.clear();
                await this.loadSamples();
                await this.loadStatistics();
                this.showToast(`已更新 ${result.data.updated} 条记录`);
            } else {
                this.showToast(result.error || '更新失败', 'error');
            }
        } catch (e) {
            this.showToast('更新失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 显示样本详情
     */
    async showDetail(sampleId) {
        try {
            const result = await ErrorSamplesAPI.getDetail(sampleId);
            if (result.success) {
                this.renderDetailModal(result.data);
            }
        } catch (e) {
            this.showToast('获取详情失败', 'error');
        }
    }
    
    /**
     * 渲染详情弹窗
     */
    renderDetailModal(sample) {
        const modal = document.getElementById('errorSampleDetailModal');
        if (!modal) return;
        
        const statusInfo = STATUS_MAP[sample.status] || STATUS_MAP.pending;
        const severityInfo = SEVERITY_MAP[sample.severity] || SEVERITY_MAP.medium;
        
        document.getElementById('sampleDetailTitle').textContent = 
            `${sample.book_name || '未知'} - P${sample.page_num || '?'} - 第${sample.question_index}题`;
        
        document.getElementById('sampleDetailContent').innerHTML = `
            <div class="detail-row">
                <span class="detail-label">错误类型:</span>
                <span class="tag ${severityInfo.class}">${sample.error_type}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">状态:</span>
                <span class="tag ${statusInfo.class}">${statusInfo.label}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">基准答案:</span>
                <span class="detail-value">${sample.base_answer || '-'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">基准用户答案:</span>
                <span class="detail-value">${sample.base_user || '-'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">AI识别答案:</span>
                <span class="detail-value">${sample.hw_user || '-'}</span>
            </div>
            <div class="detail-row">
                <span class="detail-label">备注:</span>
                <span class="detail-value">${sample.notes || '无'}</span>
            </div>
        `;
        
        modal.style.display = 'flex';
        modal.dataset.sampleId = sample.sample_id;
    }
    
    /**
     * 关闭详情弹窗
     */
    closeDetailModal() {
        const modal = document.getElementById('errorSampleDetailModal');
        if (modal) {
            modal.style.display = 'none';
        }
    }
    
    /**
     * 跳转页面
     */
    goToPage(page) {
        if (page < 1) return;
        this.currentPage = page;
        this.loadSamples();
    }
    
    /**
     * 设置筛选条件
     */
    setFilter(key, value) {
        if (value) {
            this.filters[key] = value;
        } else {
            delete this.filters[key];
        }
        this.currentPage = 1;
        this.loadSamples();
    }
    
    /**
     * 导出样本
     */
    async exportSamples(format = 'xlsx') {
        try {
            await ErrorSamplesAPI.exportSamples(this.filters, format);
            this.showToast('导出成功');
        } catch (e) {
            this.showToast('导出失败: ' + e.message, 'error');
        }
    }
    
    /**
     * 绑定事件
     */
    bindEvents() {
        // 筛选器事件
        const errorTypeFilter = document.getElementById('errorTypeFilter');
        if (errorTypeFilter) {
            errorTypeFilter.addEventListener('change', (e) => {
                this.setFilter('error_type', e.target.value);
            });
        }
        
        const statusFilter = document.getElementById('statusFilter');
        if (statusFilter) {
            statusFilter.addEventListener('change', (e) => {
                this.setFilter('status', e.target.value);
            });
        }
    }
    
    /**
     * 显示提示
     */
    showToast(message, type = 'success') {
        // 使用全局 showToast 函数
        if (typeof window.showToast === 'function') {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    }
}

// 导出
export { STATUS_MAP, SEVERITY_MAP, SUBJECT_MAP };
