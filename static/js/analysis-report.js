/**
 * AI 分析报告页面脚本
 */

// 全局状态
let taskId = null;
let currentChart = 'pie';
let currentDimension = 'subject';
let progressPoller = null;
let progressRing = null;

// 页面初始化
document.addEventListener('DOMContentLoaded', function() {
    const pathParts = window.location.pathname.split('/');
    taskId = pathParts[pathParts.length - 1];
    
    if (!taskId) {
        toast.error('缺少任务ID');
        return;
    }
    
    document.getElementById('taskId').textContent = `任务: ${taskId}`;
    loadAnalysisData();
    bindEvents();
});

// 绑定事件
function bindEvents() {
    document.getElementById('refreshBtn').addEventListener('click', () => {
        confirmDialog.show({
            title: '刷新分析',
            message: '确定要重新执行 AI 分析吗？',
            description: '这将消耗 API 调用额度',
            onConfirm: triggerAnalysis
        });
    });
    
    document.getElementById('exportBtn').addEventListener('click', showExportModal);
    document.getElementById('cancelExport').addEventListener('click', hideExportModal);
    document.getElementById('confirmExport').addEventListener('click', doExport);

    // 图表切换
    document.querySelectorAll('.chart-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.chart-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentChart = this.dataset.chart;
            loadChart();
        });
    });
    
    // 维度切换
    document.querySelectorAll('.dimension-tab').forEach(tab => {
        tab.addEventListener('click', function() {
            document.querySelectorAll('.dimension-tab').forEach(t => t.classList.remove('active'));
            this.classList.add('active');
            currentDimension = this.dataset.dimension;
            loadDimensionData();
        });
    });
    
    document.getElementById('cancelAnalysis').addEventListener('click', cancelAnalysis);
}

// 加载分析数据
async function loadAnalysisData() {
    try {
        const response = await fetch(`/api/analysis/task/${taskId}`);
        const result = await response.json();
        
        if (!result.success) {
            toast.error(result.error || '加载失败');
            return;
        }
        
        const data = result.data;
        renderOverview(data.quick_stats);
        renderSummary(data.llm_analysis);
        renderStatus(data.analysis_status);
        loadChart();
        loadDimensionData();
        loadClusters();
        loadAnomalies();
        loadSuggestions();
    } catch (error) {
        console.error('加载分析数据失败:', error);
        toast.error('加载分析数据失败');
    }
}

// 渲染概览卡片
function renderOverview(stats) {
    if (!stats) return;
    document.getElementById('totalErrors').textContent = stats.total_errors || 0;
    document.getElementById('errorRate').textContent = ((stats.error_rate || 0) * 100).toFixed(1) + '%';
    document.getElementById('pendingCount').textContent = stats.pending_count || stats.total_errors || 0;
    document.getElementById('fixedCount').textContent = stats.fixed_count || 0;
}

// 渲染执行摘要
function renderSummary(llmAnalysis) {
    const container = document.getElementById('summaryContent');
    if (!llmAnalysis || !llmAnalysis.task_summary) {
        EmptyState.render('summaryContent', 'analysisNotStarted', {
            title: '暂无 AI 分析摘要',
            description: '点击"刷新分析"生成智能分析报告',
            actionText: '开始分析',
            onAction: triggerAnalysis
        });
        return;
    }
    container.innerHTML = `<p>${llmAnalysis.task_summary}</p>`;
}

// 渲染分析状态
function renderStatus(status) {
    const indicator = document.getElementById('statusIndicator');
    const statusText = document.getElementById('analysisStatus');
    const statusMap = {
        'completed': { text: '已完成', class: 'completed' },
        'analyzing': { text: '分析中', class: 'analyzing' },
        'pending': { text: '待分析', class: 'pending' },
        'stale': { text: '需更新', class: 'pending' }
    };
    const info = statusMap[status] || statusMap['pending'];
    indicator.className = `status-indicator ${info.class}`;
    statusText.textContent = info.text;
}

// 加载图表
async function loadChart() {
    const container = document.getElementById('chartContainer');
    Skeleton.show('chartContainer', 'chart');
    
    try {
        let data;
        switch (currentChart) {
            case 'pie':
                data = await loadPieChartData();
                renderPieChart(container, data);
                break;
            case 'sankey':
                data = await loadSankeyData();
                renderSankeyChart(container, data);
                break;
            case 'heatmap':
                data = await loadHeatmapData();
                renderHeatmapChart(container, data);
                break;
            case 'radar':
                data = await loadRadarData();
                renderRadarChart(container, data);
                break;
        }
    } catch (error) {
        console.error('加载图表失败:', error);
        container.innerHTML = '<p class="text-muted" style="text-align:center;padding:40px;">图表加载失败</p>';
    }
}

async function loadPieChartData() {
    const response = await fetch(`/api/analysis/task/${taskId}`);
    const result = await response.json();
    return result.data?.quick_stats?.error_type_distribution || {};
}

function renderPieChart(container, data) {
    const entries = Object.entries(data);
    if (entries.length === 0) {
        EmptyState.render('chartContainer', 'noData');
        return;
    }
    const total = entries.reduce((sum, [, count]) => sum + count, 0);
    const colors = ['#d73a49', '#e65100', '#1565c0', '#1e7e34', '#86868b', '#9c27b0'];
    
    let html = '<div style="display:flex;align-items:center;gap:40px;justify-content:center;padding:20px;">';
    html += '<div style="flex:1;max-width:450px;">';
    entries.forEach(([type, count], index) => {
        const percentage = (count / total * 100).toFixed(1);
        const color = colors[index % colors.length];
        html += `<div style="margin-bottom:12px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:14px;">${type}</span>
                <span style="font-size:14px;color:#86868b;">${count} (${percentage}%)</span>
            </div>
            <div style="height:8px;background:#e5e5e5;border-radius:4px;overflow:hidden;">
                <div style="height:100%;width:${percentage}%;background:${color};border-radius:4px;transition:width 0.3s;"></div>
            </div>
        </div>`;
    });
    html += '</div>';
    html += '<div style="display:flex;flex-direction:column;gap:8px;">';
    entries.forEach(([type], index) => {
        const color = colors[index % colors.length];
        html += `<div style="display:flex;align-items:center;gap:8px;">
            <div style="width:12px;height:12px;background:${color};border-radius:2px;"></div>
            <span style="font-size:13px;">${type}</span>
        </div>`;
    });
    html += '</div></div>';
    container.innerHTML = html;
}

async function loadSankeyData() {
    const response = await fetch(`/api/analysis/chart/sankey?task_id=${taskId}`);
    const result = await response.json();
    return result.data;
}

function renderSankeyChart(container, data) {
    if (!data || !data.nodes || data.nodes.length === 0) {
        EmptyState.render('chartContainer', 'noData');
        return;
    }
    let html = '<div style="display:flex;justify-content:space-around;padding:20px;">';
    const categories = ['error_type', 'root_cause', 'suggestion'];
    const categoryNames = { error_type: '错误类型', root_cause: '根因', suggestion: '建议' };
    
    categories.forEach(cat => {
        const nodes = data.nodes.filter(n => n.category === cat);
        html += `<div style="text-align:center;flex:1;">
            <h4 style="margin-bottom:12px;color:#86868b;font-size:13px;">${categoryNames[cat]}</h4>
            <div style="display:flex;flex-direction:column;gap:8px;">`;
        nodes.slice(0, 5).forEach(node => {
            html += `<div style="padding:8px 16px;background:#f5f5f7;border-radius:6px;font-size:13px;">
                ${node.name} <span style="color:#86868b;">(${node.value})</span>
            </div>`;
        });
        html += '</div></div>';
    });
    html += '</div>';
    container.innerHTML = html;
}

async function loadHeatmapData() {
    const response = await fetch(`/api/analysis/chart/heatmap?task_id=${taskId}`);
    const result = await response.json();
    return result.data;
}

function renderHeatmapChart(container, data) {
    if (!data || !data.data || data.data.length === 0) {
        EmptyState.render('chartContainer', 'noData');
        return;
    }
    const maxValue = data.max_value || 1;
    let html = '<div style="overflow-x:auto;padding:20px;"><table style="border-collapse:collapse;margin:0 auto;">';
    html += '<tr><th style="padding:4px 8px;"></th>';
    (data.x_axis || []).forEach(x => {
        html += `<th style="padding:4px 8px;font-size:12px;color:#86868b;">${x}</th>`;
    });
    html += '</tr>';
    (data.y_axis || []).forEach((y, yIdx) => {
        html += `<tr><td style="padding:4px 8px;font-size:12px;color:#86868b;">${y}</td>`;
        (data.x_axis || []).forEach((_, xIdx) => {
            const cell = data.data.find(d => d[0] === xIdx && d[1] === yIdx);
            const value = cell ? cell[2] : 0;
            const intensity = value / maxValue;
            const bgColor = value > 0 ? `rgba(215,58,73,${0.2 + intensity * 0.8})` : '#f5f5f7';
            html += `<td style="width:30px;height:30px;background:${bgColor};text-align:center;font-size:11px;">${value > 0 ? value : ''}</td>`;
        });
        html += '</tr>';
    });
    html += '</table></div>';
    container.innerHTML = html;
}

async function loadRadarData() {
    const response = await fetch(`/api/analysis/chart/radar?task_id=${taskId}&dimension=error_type`);
    const result = await response.json();
    return result.data;
}

function renderRadarChart(container, data) {
    if (!data || !data.indicators || data.indicators.length === 0) {
        EmptyState.render('chartContainer', 'noData');
        return;
    }
    const values = data.series?.[0]?.values || [];
    let html = '<div style="max-width:500px;margin:0 auto;padding:20px;">';
    data.indicators.forEach((ind, idx) => {
        const value = values[idx] || 0;
        html += `<div style="margin-bottom:16px;">
            <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
                <span style="font-size:14px;">${ind.name}</span>
                <span style="font-size:14px;color:#86868b;">${value.toFixed(1)}%</span>
            </div>
            <div style="height:8px;background:#e5e5e5;border-radius:4px;overflow:hidden;">
                <div style="height:100%;width:${value}%;background:#1565c0;border-radius:4px;"></div>
            </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

// 加载维度数据
async function loadDimensionData() {
    const container = document.getElementById('dimensionContent');
    Skeleton.show('dimensionContent', 'list');
    
    try {
        let endpoint;
        switch (currentDimension) {
            case 'subject':
                endpoint = `/api/analysis/subject?task_id=${taskId}`;
                break;
            case 'book':
                endpoint = `/api/analysis/book?task_id=${taskId}`;
                break;
            case 'question-type':
                endpoint = `/api/analysis/question-type?task_id=${taskId}`;
                break;
            case 'trend':
                container.innerHTML = '<p style="text-align:center;color:#86868b;padding:40px;">请选择多个任务进行趋势分析</p>';
                return;
            case 'compare':
                container.innerHTML = '<p style="text-align:center;color:#86868b;padding:40px;">请选择两个任务进行对比分析</p>';
                return;
        }
        
        const response = await fetch(endpoint);
        const result = await response.json();
        
        if (!result.success) {
            container.innerHTML = `<p style="text-align:center;color:#86868b;padding:40px;">${result.error || '加载失败'}</p>`;
            return;
        }
        renderDimensionList(container, result.data);
    } catch (error) {
        console.error('加载维度数据失败:', error);
        container.innerHTML = '<p style="text-align:center;color:#86868b;padding:40px;">加载失败</p>';
    }
}

function renderDimensionList(container, data) {
    const items = data.quick_stats?.subjects || data.quick_stats?.books || data.quick_stats?.question_types || [];
    if (items.length === 0) {
        EmptyState.render('dimensionContent', 'noData');
        return;
    }
    const maxCount = Math.max(...items.map(i => i.error_count || i.count || 0));
    let html = '<div class="dimension-list">';
    items.forEach(item => {
        const name = item.name || item.subject_id || '未知';
        const count = item.error_count || item.count || 0;
        const percentage = maxCount > 0 ? (count / maxCount * 100) : 0;
        html += `<div class="dimension-item">
            <div class="dimension-item-header">
                <span class="dimension-item-name">${name}</span>
                <span class="dimension-item-count">${count}</span>
            </div>
            <div class="dimension-item-bar">
                <div class="dimension-item-bar-fill" style="width:${percentage}%"></div>
            </div>
        </div>`;
    });
    html += '</div>';
    container.innerHTML = html;
}

// 加载聚类
async function loadClusters() {
    const container = document.getElementById('clustersList');
    Skeleton.show('clustersList', 'card', 3);
    
    try {
        const response = await fetch(`/api/analysis/clusters?task_id=${taskId}&page_size=5`);
        const result = await response.json();
        
        if (!result.success) {
            container.innerHTML = '<p style="color:#86868b;">加载失败</p>';
            return;
        }
        const clusters = result.data.quick_stats?.clusters || [];
        if (clusters.length === 0) {
            EmptyState.render('clustersList', 'noData', { title: '暂无聚类数据' });
            return;
        }
        let html = '';
        clusters.slice(0, 5).forEach(cluster => {
            const severity = cluster.sample_count > 10 ? 'high' : cluster.sample_count > 5 ? 'medium' : 'low';
            html += `<div class="cluster-card" onclick="viewCluster('${cluster.cluster_key}')">
                <div class="cluster-header">
                    <span class="cluster-name">${cluster.error_type} - ${cluster.book_name}</span>
                    <span class="severity-tag ${severity}">${severity}</span>
                </div>
                <div class="cluster-description">页码范围: ${cluster.page_range}</div>
                <div class="cluster-footer">
                    <span class="cluster-count">${cluster.sample_count} 个样本</span>
                    <div class="cluster-actions">
                        <a href="#" class="cluster-action" onclick="event.stopPropagation();viewSamples('${cluster.cluster_key}')">查看样本</a>
                    </div>
                </div>
            </div>`;
        });
        container.innerHTML = html;
    } catch (error) {
        console.error('加载聚类失败:', error);
        container.innerHTML = '<p style="color:#86868b;">加载失败</p>';
    }
}

// 加载异常
async function loadAnomalies() {
    try {
        const response = await fetch(`/api/analysis/anomalies?task_id=${taskId}`);
        const result = await response.json();
        if (!result.success) return;
        
        const anomalies = result.data.anomalies || [];
        const section = document.getElementById('anomaliesSection');
        const container = document.getElementById('anomaliesList');
        const badge = document.getElementById('anomalyBadge');
        
        if (anomalies.length === 0) {
            section.style.display = 'none';
            return;
        }
        section.style.display = 'block';
        badge.textContent = anomalies.length;
        
        let html = '';
        anomalies.slice(0, 5).forEach(anomaly => {
            const typeText = anomaly.anomaly_type === 'inconsistent_grading' ? '批改不一致' : anomaly.anomaly_type;
            html += `<div class="anomaly-card">
                <div class="anomaly-header">
                    <span class="anomaly-type">${typeText}</span>
                    <span class="severity-tag ${anomaly.severity}">${anomaly.severity}</span>
                </div>
                <div class="anomaly-description">${anomaly.description || '检测到异常模式'}</div>
            </div>`;
        });
        container.innerHTML = html;
    } catch (error) {
        console.error('加载异常失败:', error);
    }
}

// 加载建议
async function loadSuggestions() {
    const container = document.getElementById('suggestionsList');
    Skeleton.show('suggestionsList', 'card', 2);
    
    try {
        const response = await fetch(`/api/analysis/suggestions?task_id=${taskId}`);
        const result = await response.json();
        
        if (!result.success) {
            container.innerHTML = '<p style="color:#86868b;">加载失败</p>';
            return;
        }
        const suggestions = result.data.suggestions || [];
        if (suggestions.length === 0) {
            EmptyState.render('suggestionsList', 'noData', { title: '暂无优化建议' });
            return;
        }
        let html = '';
        suggestions.forEach(suggestion => {
            const priorityClass = suggestion.priority === 'P0' ? 'high' : suggestion.priority === 'P1' ? 'medium' : 'low';
            html += `<div class="suggestion-card">
                <div class="suggestion-header">
                    <span class="suggestion-title">${suggestion.title}</span>
                    <span class="priority-tag ${priorityClass}">${suggestion.priority}</span>
                </div>
                <div class="suggestion-description">${suggestion.description}</div>
                <div class="suggestion-effect">${suggestion.expected_impact || suggestion.expected_effect || ''}</div>
            </div>`;
        });
        container.innerHTML = html;
    } catch (error) {
        console.error('加载建议失败:', error);
        container.innerHTML = '<p style="color:#86868b;">加载失败</p>';
    }
}

// 触发分析
async function triggerAnalysis() {
    try {
        const response = await fetch(`/api/analysis/trigger/${taskId}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ priority: 'high' })
        });
        const result = await response.json();
        
        if (result.success && result.data.queued) {
            showProgressModal();
            startPolling();
        } else {
            toast.warning(result.data?.message || result.error || '触发分析失败');
        }
    } catch (error) {
        console.error('触发分析失败:', error);
        toast.error('触发分析失败');
    }
}

function showProgressModal() {
    document.getElementById('progressModal').style.display = 'flex';
    if (!progressRing) {
        progressRing = new ProgressRing('progressRingContainer', { size: 120 });
    }
    progressRing.setProgress(0);
    document.getElementById('progressStep').textContent = '初始化...';
    document.getElementById('progressEta').textContent = '';
}

function hideProgressModal() {
    document.getElementById('progressModal').style.display = 'none';
    stopPolling();
}

function startPolling() {
    progressPoller = new AnalysisProgressPoller(taskId, {
        onProgress: ({ progress, step, estimatedRemaining }) => {
            progressRing.setProgress(progress);
            document.getElementById('progressStep').textContent = step;
            if (estimatedRemaining) {
                document.getElementById('progressEta').textContent = `预计剩余 ${estimatedRemaining} 秒`;
            }
        },
        onComplete: () => {
            hideProgressModal();
            toast.success('分析完成');
            loadAnalysisData();
        },
        onError: (error) => {
            hideProgressModal();
            toast.error(error);
        }
    });
    progressPoller.start();
}

function stopPolling() {
    if (progressPoller) {
        progressPoller.stop();
        progressPoller = null;
    }
}

function cancelAnalysis() {
    hideProgressModal();
    toast.info('已取消分析');
}

// 导出功能
function showExportModal() {
    document.getElementById('exportModal').style.display = 'flex';
}

function hideExportModal() {
    document.getElementById('exportModal').style.display = 'none';
}

async function doExport() {
    const format = document.querySelector('input[name="exportFormat"]:checked').value;
    const sections = Array.from(document.querySelectorAll('.export-sections input:checked')).map(cb => cb.value);
    
    try {
        const response = await fetch('/api/analysis/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId, format, sections })
        });
        const result = await response.json();
        
        if (result.success) {
            hideExportModal();
            toast.success('导出成功，正在下载...');
            window.location.href = `/api/analysis/export/download/${result.data.export_id}`;
        } else {
            toast.error(result.error || '导出失败');
        }
    } catch (error) {
        console.error('导出失败:', error);
        toast.error('导出失败');
    }
}

// 导航函数
function viewCluster(clusterId) {
    window.location.href = `/cluster-detail/${encodeURIComponent(clusterId)}?task_id=${taskId}`;
}

function viewSamples(clusterId) {
    window.location.href = `/error-samples?task_id=${taskId}&cluster=${encodeURIComponent(clusterId)}`;
}
