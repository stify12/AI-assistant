/**
 * 优化建议模块 (US-28)
 * @module Optimization
 */

/**
 * 优化建议API
 */
export const OptimizationAPI = {
    /**
     * 获取建议列表
     */
    getSuggestions: async (params = {}) => {
        const query = new URLSearchParams(params).toString();
        const response = await fetch(`/api/optimization/suggestions?${query}`);
        return response.json();
    },
    
    /**
     * 获取建议详情
     */
    getDetail: async (suggestionId) => {
        const response = await fetch(`/api/optimization/suggestions/${suggestionId}`);
        return response.json();
    },
    
    /**
     * 生成优化建议
     */
    generate: async (sampleIds = null, errorType = null, limit = 50) => {
        const response = await fetch('/api/optimization/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ sample_ids: sampleIds, error_type: errorType, limit })
        });
        return response.json();
    },
    
    /**
     * 更新建议状态
     */
    updateStatus: async (suggestionId, status) => {
        const response = await fetch(`/api/optimization/suggestions/${suggestionId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status })
        });
        return response.json();
    },
    
    /**
     * 删除建议
     */
    delete: async (suggestionId) => {
        const response = await fetch(`/api/optimization/suggestions/${suggestionId}`, {
            method: 'DELETE'
        });
        return response.json();
    },
    
    /**
     * 导出建议报告
     */
    export: async (suggestionIds = null, format = 'md') => {
        const response = await fetch('/api/optimization/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ suggestion_ids: suggestionIds, format })
        });
        
        if (response.ok) {
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `optimization_report.${format}`;
            a.click();
            window.URL.revokeObjectURL(url);
            return { success: true };
        }
        return response.json();
    }
};


/**
 * 优化建议管理器类
 */
export class OptimizationManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.suggestions = [];
        this.currentPage = 1;
        this.pageSize = 10;
        this.totalPages = 1;
        this.filters = {};
        this.isGenerating = false;
    }
    
    /**
     * 初始化
     */
    async init() {
        await this.loadSuggestions();
    }
    
    /**
     * 加载建议列表
     */
    async loadSuggestions() {
        try {
            const params = {
                page: this.currentPage,
                page_size: this.pageSize,
                ...this.filters
            };
            
            const result = await OptimizationAPI.getSuggestions(params);
            if (result.success) {
                this.suggestions = result.data.items;
                this.totalPages = result.data.total_pages;
                this.render();
            }
        } catch (e) {
            console.error('加载建议失败:', e);
        }
    }
    
    /**
     * 生成优化建议
     */
    async generate(errorType = null, limit = 50) {
        if (this.isGenerating) return;
        
        this.isGenerating = true;
        this.showLoading('正在生成优化建议...');
        
        try {
            const result = await OptimizationAPI.generate(null, errorType, limit);
            if (result.success) {
                await this.loadSuggestions();
                this.showMessage(result.message || '建议生成完成');
            } else {
                this.showError(result.error || '生成失败');
            }
        } catch (e) {
            this.showError('生成优化建议失败');
        } finally {
            this.isGenerating = false;
            this.hideLoading();
        }
    }
    
    /**
     * 渲染建议列表
     */
    render() {
        if (!this.container) return;
        
        if (this.suggestions.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <p>暂无优化建议</p>
                    <button class="btn btn-primary" onclick="optimizationManager.generate()">
                        生成优化建议
                    </button>
                </div>
            `;
            return;
        }
        
        let html = '<div class="suggestion-list">';
        
        for (const suggestion of this.suggestions) {
            const priorityClass = this.getPriorityClass(suggestion.priority);
            const statusLabel = this.getStatusLabel(suggestion.status);
            
            html += `
                <div class="suggestion-item" data-id="${suggestion.suggestion_id}">
                    <div class="suggestion-header">
                        <span class="suggestion-title">${suggestion.title}</span>
                        <div class="suggestion-tags">
                            <span class="tag ${priorityClass}">${this.getPriorityLabel(suggestion.priority)}</span>
                            <span class="tag tag-default">${statusLabel}</span>
                        </div>
                    </div>
                    <div class="suggestion-body">
                        ${suggestion.problem_description ? 
                            `<div class="problem-desc">${suggestion.problem_description}</div>` : ''}
                        <div class="suggestion-content">${suggestion.suggestion_content || ''}</div>
                    </div>
                    <div class="suggestion-footer">
                        <div class="suggestion-meta">
                            <span>样本数: ${suggestion.sample_count}</span>
                            <span>创建: ${this.formatDate(suggestion.created_at)}</span>
                        </div>
                        <div class="suggestion-actions">
                            ${this.renderStatusButtons(suggestion)}
                            <button class="btn btn-sm btn-danger" 
                                    onclick="optimizationManager.deleteSuggestion('${suggestion.suggestion_id}')">
                                删除
                            </button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        
        // 分页
        if (this.totalPages > 1) {
            html += this.renderPagination();
        }
        
        this.container.innerHTML = html;
    }
    
    /**
     * 渲染状态按钮
     */
    renderStatusButtons(suggestion) {
        const status = suggestion.status;
        let buttons = '';
        
        if (status === 'pending') {
            buttons += `
                <button class="btn btn-sm btn-primary" 
                        onclick="optimizationManager.updateStatus('${suggestion.suggestion_id}', 'in_progress')">
                    开始处理
                </button>
            `;
        } else if (status === 'in_progress') {
            buttons += `
                <button class="btn btn-sm btn-success" 
                        onclick="optimizationManager.updateStatus('${suggestion.suggestion_id}', 'completed')">
                    标记完成
                </button>
            `;
        }
        
        return buttons;
    }
    
    /**
     * 渲染分页
     */
    renderPagination() {
        let html = '<div class="pagination">';
        
        html += `
            <button class="btn btn-sm" 
                    ${this.currentPage <= 1 ? 'disabled' : ''}
                    onclick="optimizationManager.goToPage(${this.currentPage - 1})">
                上一页
            </button>
            <span class="page-info">${this.currentPage} / ${this.totalPages}</span>
            <button class="btn btn-sm" 
                    ${this.currentPage >= this.totalPages ? 'disabled' : ''}
                    onclick="optimizationManager.goToPage(${this.currentPage + 1})">
                下一页
            </button>
        `;
        
        html += '</div>';
        return html;
    }
    
    /**
     * 跳转页面
     */
    async goToPage(page) {
        if (page < 1 || page > this.totalPages) return;
        this.currentPage = page;
        await this.loadSuggestions();
    }
    
    /**
     * 更新状态
     */
    async updateStatus(suggestionId, status) {
        try {
            const result = await OptimizationAPI.updateStatus(suggestionId, status);
            if (result.success) {
                await this.loadSuggestions();
            } else {
                this.showError(result.error || '更新失败');
            }
        } catch (e) {
            this.showError('更新状态失败');
        }
    }
    
    /**
     * 删除建议
     */
    async deleteSuggestion(suggestionId) {
        if (!confirm('确定要删除此建议吗？')) return;
        
        try {
            const result = await OptimizationAPI.delete(suggestionId);
            if (result.success) {
                await this.loadSuggestions();
            } else {
                this.showError(result.error || '删除失败');
            }
        } catch (e) {
            this.showError('删除建议失败');
        }
    }
    
    /**
     * 导出报告
     */
    async exportReport(format = 'md') {
        try {
            await OptimizationAPI.export(null, format);
        } catch (e) {
            this.showError('导出失败');
        }
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
        this.loadSuggestions();
    }
    
    getPriorityClass(priority) {
        const map = { high: 'tag-error', medium: 'tag-warning', low: 'tag-info' };
        return map[priority] || 'tag-default';
    }
    
    getPriorityLabel(priority) {
        const map = { high: '高优先级', medium: '中优先级', low: '低优先级' };
        return map[priority] || priority;
    }
    
    getStatusLabel(status) {
        const map = { 
            pending: '待处理', 
            in_progress: '处理中', 
            completed: '已完成', 
            rejected: '已拒绝' 
        };
        return map[status] || status;
    }
    
    formatDate(dateStr) {
        if (!dateStr) return '-';
        return dateStr.split('T')[0];
    }
    
    showLoading(msg) { console.log(msg); }
    hideLoading() {}
    showMessage(msg) { console.log(msg); }
    showError(msg) { console.error(msg); alert(msg); }
}

export default OptimizationManager;
