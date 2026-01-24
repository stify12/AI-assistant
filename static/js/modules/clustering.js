/**
 * 错误聚类模块 (US-27)
 * @module Clustering
 */

/**
 * 聚类API
 */
export const ClusteringAPI = {
    /**
     * 获取聚类列表
     */
    getClusters: async (errorType = null) => {
        const params = errorType ? `?error_type=${encodeURIComponent(errorType)}` : '';
        const response = await fetch(`/api/clustering/clusters${params}`);
        return response.json();
    },
    
    /**
     * 获取聚类下的样本
     */
    getClusterSamples: async (clusterId, page = 1, pageSize = 20) => {
        const response = await fetch(
            `/api/clustering/clusters/${clusterId}/samples?page=${page}&page_size=${pageSize}`
        );
        return response.json();
    },
    
    /**
     * 执行聚类分析
     */
    analyze: async (errorType = null, limit = 100) => {
        const response = await fetch('/api/clustering/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error_type: errorType, limit })
        });
        return response.json();
    },
    
    /**
     * 更新聚类标签
     */
    updateLabel: async (clusterId, label) => {
        const response = await fetch(`/api/clustering/clusters/${clusterId}/label`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ label })
        });
        return response.json();
    },
    
    /**
     * 合并聚类
     */
    merge: async (clusterIds, newLabel) => {
        const response = await fetch('/api/clustering/merge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ cluster_ids: clusterIds, new_label: newLabel })
        });
        return response.json();
    },
    
    /**
     * 删除聚类
     */
    delete: async (clusterId) => {
        const response = await fetch(`/api/clustering/clusters/${clusterId}`, {
            method: 'DELETE'
        });
        return response.json();
    }
};


/**
 * 聚类管理器类
 */
export class ClusteringManager {
    constructor(containerId) {
        this.container = document.getElementById(containerId);
        this.clusters = [];
        this.selectedClusters = new Set();
        this.isAnalyzing = false;
    }
    
    /**
     * 初始化
     */
    async init() {
        await this.loadClusters();
        this.bindEvents();
    }
    
    /**
     * 加载聚类列表
     */
    async loadClusters(errorType = null) {
        try {
            const result = await ClusteringAPI.getClusters(errorType);
            if (result.success) {
                this.clusters = result.data;
                this.render();
            }
        } catch (e) {
            console.error('加载聚类失败:', e);
        }
    }
    
    /**
     * 执行聚类分析
     */
    async analyze(errorType = null, limit = 100) {
        if (this.isAnalyzing) return;
        
        this.isAnalyzing = true;
        this.showLoading('正在分析...');
        
        try {
            const result = await ClusteringAPI.analyze(errorType, limit);
            if (result.success) {
                await this.loadClusters();
                this.showMessage(result.message || '聚类完成');
            } else {
                this.showError(result.error || '聚类失败');
            }
        } catch (e) {
            this.showError('聚类分析失败');
        } finally {
            this.isAnalyzing = false;
            this.hideLoading();
        }
    }
    
    /**
     * 渲染聚类列表
     */
    render() {
        if (!this.container) return;
        
        if (this.clusters.length === 0) {
            this.container.innerHTML = `
                <div class="empty-state">
                    <p>暂无聚类数据</p>
                    <button class="btn btn-primary" onclick="clusteringManager.analyze()">
                        开始聚类分析
                    </button>
                </div>
            `;
            return;
        }
        
        let html = '<div class="cluster-list">';
        
        for (const cluster of this.clusters) {
            const isSelected = this.selectedClusters.has(cluster.cluster_id);
            
            html += `
                <div class="cluster-item ${isSelected ? 'selected' : ''}" 
                     data-cluster-id="${cluster.cluster_id}">
                    <div class="cluster-checkbox">
                        <input type="checkbox" 
                               ${isSelected ? 'checked' : ''}
                               onchange="clusteringManager.toggleSelect('${cluster.cluster_id}')" />
                    </div>
                    <div class="cluster-info">
                        <div class="cluster-label">${cluster.label}</div>
                        <div class="cluster-meta">
                            <span class="sample-count">${cluster.sample_count} 个样本</span>
                            ${cluster.error_type ? `<span class="error-type">${cluster.error_type}</span>` : ''}
                            ${cluster.ai_generated ? '<span class="tag tag-info">AI生成</span>' : ''}
                        </div>
                        ${cluster.description ? `<div class="cluster-desc">${cluster.description}</div>` : ''}
                    </div>
                    <div class="cluster-actions">
                        <button class="btn btn-sm" onclick="clusteringManager.viewSamples('${cluster.cluster_id}')">
                            查看样本
                        </button>
                        <button class="btn btn-sm" onclick="clusteringManager.editLabel('${cluster.cluster_id}', '${cluster.label}')">
                            编辑
                        </button>
                        <button class="btn btn-sm btn-danger" onclick="clusteringManager.deleteCluster('${cluster.cluster_id}')">
                            删除
                        </button>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        
        // 批量操作栏
        if (this.selectedClusters.size >= 2) {
            html += `
                <div class="batch-actions">
                    <span>已选择 ${this.selectedClusters.size} 个聚类</span>
                    <button class="btn btn-primary" onclick="clusteringManager.mergeSelected()">
                        合并聚类
                    </button>
                </div>
            `;
        }
        
        this.container.innerHTML = html;
    }
    
    /**
     * 切换选择
     */
    toggleSelect(clusterId) {
        if (this.selectedClusters.has(clusterId)) {
            this.selectedClusters.delete(clusterId);
        } else {
            this.selectedClusters.add(clusterId);
        }
        this.render();
    }
    
    /**
     * 查看聚类样本
     */
    async viewSamples(clusterId) {
        // 触发自定义事件，由父组件处理
        const event = new CustomEvent('viewClusterSamples', { 
            detail: { clusterId } 
        });
        document.dispatchEvent(event);
    }
    
    /**
     * 编辑标签
     */
    async editLabel(clusterId, currentLabel) {
        const newLabel = prompt('请输入新标签:', currentLabel);
        if (!newLabel || newLabel === currentLabel) return;
        
        try {
            const result = await ClusteringAPI.updateLabel(clusterId, newLabel);
            if (result.success) {
                await this.loadClusters();
            } else {
                this.showError(result.error || '更新失败');
            }
        } catch (e) {
            this.showError('更新标签失败');
        }
    }
    
    /**
     * 删除聚类
     */
    async deleteCluster(clusterId) {
        if (!confirm('确定要删除此聚类吗？样本将变为未分类状态。')) return;
        
        try {
            const result = await ClusteringAPI.delete(clusterId);
            if (result.success) {
                await this.loadClusters();
            } else {
                this.showError(result.error || '删除失败');
            }
        } catch (e) {
            this.showError('删除聚类失败');
        }
    }
    
    /**
     * 合并选中的聚类
     */
    async mergeSelected() {
        if (this.selectedClusters.size < 2) {
            this.showError('请至少选择2个聚类');
            return;
        }
        
        const newLabel = prompt('请输入合并后的标签:');
        if (!newLabel) return;
        
        try {
            const result = await ClusteringAPI.merge(
                Array.from(this.selectedClusters),
                newLabel
            );
            if (result.success) {
                this.selectedClusters.clear();
                await this.loadClusters();
                this.showMessage('聚类已合并');
            } else {
                this.showError(result.error || '合并失败');
            }
        } catch (e) {
            this.showError('合并聚类失败');
        }
    }
    
    bindEvents() {}
    showLoading(msg) { console.log(msg); }
    hideLoading() {}
    showMessage(msg) { console.log(msg); }
    showError(msg) { console.error(msg); alert(msg); }
}

export default ClusteringManager;
