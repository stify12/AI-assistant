/**
 * 任务整合评估页面 JavaScript
 */

// ========== 全局状态 ==========
let taskList = [];
let selectedTaskIds = new Set();
let analysisResult = null;

// Chart.js 实例
let correctDistributionChart = null;
let taskAccuracyChart = null;
let errorTypeChart = null;
let highErrorQuestionsChart = null;
let typeAccuracyChart = null;

// 学科名称映射
const SUBJECT_NAMES = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理',
    4: '化学',
    5: '生物',
    6: '地理'
};

// ========== 页面初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    loadTasks();
});

// ========== 返回 ==========
function goBack() {
    window.location.href = '/batch-evaluation';
}

// ========== 加载任务列表 ==========
async function loadTasks() {
    const subjectFilter = document.getElementById('subjectFilter').value;
    const taskListEl = document.getElementById('taskList');
    
    taskListEl.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-text">加载中...</div>
        </div>
    `;
    
    try {
        let url = '/api/consolidation/tasks';
        if (subjectFilter) {
            url += `?subject_id=${subjectFilter}`;
        }
        
        const response = await fetch(url);
        const data = await response.json();
        
        if (data.success) {
            taskList = data.tasks;
            renderTaskList();
        } else {
            taskListEl.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-text">加载失败: ${data.error || '未知错误'}</div>
                </div>
            `;
        }
    } catch (e) {
        console.error('加载任务失败:', e);
        taskListEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-text">加载失败: ${e.message}</div>
            </div>
        `;
    }
}

// ========== 渲染任务列表 ==========
function renderTaskList() {
    const taskListEl = document.getElementById('taskList');
    
    if (taskList.length === 0) {
        taskListEl.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">--</div>
                <div class="empty-state-text">暂无已完成的评估任务</div>
            </div>
        `;
        return;
    }
    
    let html = '';
    for (const task of taskList) {
        const isSelected = selectedTaskIds.has(task.task_id);
        const accuracy = (task.overall_accuracy * 100).toFixed(1);
        const accuracyClass = accuracy >= 80 ? 'high' : (accuracy >= 60 ? 'medium' : 'low');
        
        html += `
            <div class="task-item ${isSelected ? 'selected' : ''}" onclick="toggleTaskSelection('${task.task_id}')">
                <input type="checkbox" class="task-checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleTaskSelection('${task.task_id}')">
                <div class="task-item-content">
                    <div class="task-item-title">
                        ${escapeHtml(task.name)}
                        <span class="task-badge subject">${task.subject_name}</span>
                    </div>
                    <div class="task-item-meta">
                        <span>${task.homework_count}份作业</span>
                        <span>${task.total_questions}题</span>
                        <span class="accuracy-badge ${accuracyClass}">${accuracy}%</span>
                    </div>
                    <div class="task-item-meta">
                        ${task.test_condition_name ? `<span>${escapeHtml(task.test_condition_name)}</span>` : ''}
                        ${task.page_range ? `<span>${task.page_range}</span>` : ''}
                    </div>
                </div>
            </div>
        `;
    }
    
    taskListEl.innerHTML = html;
    updateSelectionInfo();
}

// ========== 切换任务选择 ==========
function toggleTaskSelection(taskId) {
    if (selectedTaskIds.has(taskId)) {
        selectedTaskIds.delete(taskId);
    } else {
        selectedTaskIds.add(taskId);
    }
    renderTaskList();
}

// ========== 全选 ==========
function selectAllTasks() {
    for (const task of taskList) {
        selectedTaskIds.add(task.task_id);
    }
    renderTaskList();
}

// ========== 清空选择 ==========
function clearSelection() {
    selectedTaskIds.clear();
    renderTaskList();
}

// ========== 更新选择信息 ==========
function updateSelectionInfo() {
    document.getElementById('selectedCount').textContent = selectedTaskIds.size;
    document.getElementById('analyzeBtn').disabled = selectedTaskIds.size === 0;
}

// ========== 执行分析 ==========
async function runAnalysis() {
    if (selectedTaskIds.size === 0) {
        alert('请至少选择一个任务');
        return;
    }
    
    showLoading('正在整合分析...');
    
    try {
        const response = await fetch('/api/consolidation/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: Array.from(selectedTaskIds) })
        });
        
        const data = await response.json();
        
        if (data.success) {
            analysisResult = data.data;
            renderAnalysisResult();
        } else {
            alert('分析失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        console.error('分析失败:', e);
        alert('分析失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

// ========== 渲染分析结果 ==========
function renderAnalysisResult() {
    document.getElementById('emptyResult').style.display = 'none';
    document.getElementById('resultContainer').style.display = 'block';
    
    renderSummaryStats();
    renderCorrectDistributionChart();
    renderTaskAccuracyChart();
    renderErrorTypeChart();
    renderHighErrorQuestionsChart();
    renderTypeAccuracyChart();
    renderTaskDetailTable();
    renderAccuracyAnalysisTable();
}

// ========== 渲染总体统计 ==========
function renderSummaryStats() {
    const summary = analysisResult.summary;
    const accuracy = (summary.overall_accuracy * 100).toFixed(1);
    const dist = summary.grading_distribution || {};
    
    document.getElementById('summaryStats').innerHTML = `
        <div class="stat-card">
            <div class="stat-value">${summary.total_tasks}</div>
            <div class="stat-label">任务数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${summary.total_homework}</div>
            <div class="stat-label">作业数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${summary.total_questions}</div>
            <div class="stat-label">总题目数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value highlight">${summary.total_grading_match || 0}</div>
            <div class="stat-label">批改一致数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value" style="font-size:32px;font-weight:700;">${accuracy}%</div>
            <div class="stat-label">批改准确率</div>
        </div>
        <div class="stat-card">
            <div class="stat-value warning">${dist.mismatch || 0}</div>
            <div class="stat-label">批改不一致数</div>
        </div>
    `;
}

// ========== 渲染批改结果分布图 ==========
function renderCorrectDistributionChart() {
    const ctx = document.getElementById('correctDistributionChart').getContext('2d');
    const dist = analysisResult.summary.grading_distribution || {};
    
    if (correctDistributionChart) {
        correctDistributionChart.destroy();
    }
    
    correctDistributionChart = new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['批改一致', '批改不一致', '数据缺失'],
            datasets: [{
                data: [dist.match || 0, dist.mismatch || 0, dist.unknown || 0],
                backgroundColor: ['#22c55e', '#f59e0b', '#94a3b8'],
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: {
                        padding: 16,
                        usePointStyle: true,
                        color: '#1d1d1f'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    callbacks: {
                        label: function(context) {
                            const total = (dist.match || 0) + (dist.mismatch || 0) + (dist.unknown || 0);
                            const percentage = total > 0 ? ((context.raw / total) * 100).toFixed(1) : 0;
                            return `${context.label}: ${context.raw} (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

// ========== 渲染任务准确率对比图 ==========
function renderTaskAccuracyChart() {
    const ctx = document.getElementById('taskAccuracyChart').getContext('2d');
    const taskStats = analysisResult.task_stats;
    
    if (taskAccuracyChart) {
        taskAccuracyChart.destroy();
    }
    
    const labels = taskStats.map(t => truncateText(t.name, 15));
    const data = taskStats.map(t => (t.accuracy * 100).toFixed(1));
    // 彩色配色：绿色表示高准确率，蓝色表示中等，橙色表示低准确率
    const colors = data.map(v => v >= 80 ? '#10b981' : (v >= 60 ? '#3b82f6' : '#f59e0b'));
    
    taskAccuracyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '准确率 (%)',
                data: data,
                backgroundColor: colors,
                borderRadius: 4
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f0f0f0' },
                    ticks: { callback: v => v + '%', color: '#86868b' }
                },
                y: {
                    grid: { display: false },
                    ticks: { color: '#1d1d1f' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    callbacks: {
                        label: function(context) {
                            const task = taskStats[context.dataIndex];
                            return `准确率: ${context.raw}% (${task.match_count || 0}/${task.total_questions})`;
                        }
                    }
                }
            }
        }
    });
}

// ========== 渲染错误类型分布图 ==========
function renderErrorTypeChart() {
    const ctx = document.getElementById('errorTypeChart').getContext('2d');
    const errorTypes = analysisResult.error_types;
    
    if (errorTypeChart) {
        errorTypeChart.destroy();
    }
    
    if (errorTypes.length === 0) {
        ctx.canvas.parentElement.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无错误类型数据</div></div>';
        return;
    }
    
    const labels = errorTypes.slice(0, 8).map(e => e.type);
    const data = errorTypes.slice(0, 8).map(e => e.count);
    
    // 彩色配色（参考批量评估界面）
    const colors = [
        '#ef4444', '#f59e0b', '#eab308', '#22c55e',
        '#3b82f6', '#8b5cf6', '#ec4899', '#6b7280'
    ];
    
    errorTypeChart = new Chart(ctx, {
        type: 'pie',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors.slice(0, labels.length),
                borderWidth: 0
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            plugins: {
                legend: {
                    position: 'right',
                    labels: {
                        padding: 12,
                        usePointStyle: true,
                        font: { size: 11 },
                        color: '#1d1d1f'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)'
                }
            }
        }
    });
}

// ========== 渲染高频不一致题目图 ==========
function renderHighErrorQuestionsChart() {
    const ctx = document.getElementById('highErrorQuestionsChart').getContext('2d');
    const highErrors = analysisResult.high_error_questions.slice(0, 10);
    
    if (highErrorQuestionsChart) {
        highErrorQuestionsChart.destroy();
    }
    
    if (highErrors.length === 0) {
        ctx.canvas.parentElement.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无不一致数据</div></div>';
        return;
    }
    
    const labels = highErrors.map(e => `题${e.index}`);
    const mismatchCounts = highErrors.map(e => e.mismatch || 0);
    const matchCounts = highErrors.map(e => e.match || 0);
    
    highErrorQuestionsChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [
                {
                    label: '不一致',
                    data: mismatchCounts,
                    backgroundColor: '#f59e0b',
                    borderRadius: 4
                },
                {
                    label: '一致',
                    data: matchCounts,
                    backgroundColor: '#22c55e',
                    borderRadius: 4
                }
            ]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: { stacked: true, grid: { display: false }, ticks: { color: '#1d1d1f' } },
                y: { stacked: true, beginAtZero: true, grid: { color: '#f0f0f0' }, ticks: { color: '#86868b' } }
            },
            plugins: {
                legend: { position: 'top', labels: { color: '#1d1d1f' } },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    callbacks: {
                        afterBody: function(context) {
                            const idx = context[0].dataIndex;
                            const item = highErrors[idx];
                            return `不一致率: ${(item.error_rate * 100).toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// ========== 渲染题型准确率图 ==========
function renderTypeAccuracyChart() {
    const ctx = document.getElementById('typeAccuracyChart').getContext('2d');
    const typeAccuracy = analysisResult.type_accuracy || [];
    
    if (typeAccuracyChart) {
        typeAccuracyChart.destroy();
    }
    
    if (typeAccuracy.length === 0) {
        ctx.canvas.parentElement.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无题型数据</div></div>';
        return;
    }
    
    const labels = typeAccuracy.map(t => t.name);
    const accuracyData = typeAccuracy.map(t => (t.accuracy * 100).toFixed(1));
    // 根据准确率设置颜色
    const colors = accuracyData.map(v => v >= 80 ? '#10b981' : (v >= 60 ? '#3b82f6' : '#f59e0b'));
    
    typeAccuracyChart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '批改准确率 (%)',
                data: accuracyData,
                backgroundColor: colors,
                borderRadius: 6,
                barThickness: 40
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                x: {
                    grid: { display: false },
                    ticks: { color: '#1d1d1f', font: { weight: '500' } }
                },
                y: {
                    beginAtZero: true,
                    max: 100,
                    grid: { color: '#f0f0f0' },
                    ticks: { callback: v => v + '%', color: '#86868b' }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    callbacks: {
                        label: function(context) {
                            const item = typeAccuracy[context.dataIndex];
                            return `准确率: ${context.raw}% (一致${item.match}/总计${item.total})`;
                        }
                    }
                }
            },
            animation: { duration: 600, easing: 'easeOutQuart' }
        }
    });
}

// ========== 渲染任务详情表格 ==========
function renderTaskDetailTable() {
    const tbody = document.getElementById('taskDetailBody');
    const taskStats = analysisResult.task_stats;
    
    let html = '';
    for (const task of taskStats) {
        const accuracy = (task.accuracy * 100).toFixed(1);
        const accuracyClass = accuracy >= 80 ? 'high' : (accuracy >= 60 ? 'medium' : 'low');
        
        html += `
            <tr>
                <td>${escapeHtml(task.name)}</td>
                <td>${task.subject_name}</td>
                <td>${escapeHtml(task.test_condition_name || '-')}</td>
                <td>${task.homework_count}</td>
                <td>${task.total_questions}</td>
                <td>${task.match_count || 0}</td>
                <td class="accuracy-cell ${accuracyClass}">${accuracy}%</td>
            </tr>
        `;
    }
    
    tbody.innerHTML = html;
}

// ========== 渲染批改准确率分析表格 ==========
function renderAccuracyAnalysisTable() {
    const tbody = document.getElementById('accuracyAnalysisBody');
    const taskTypeAnalysis = analysisResult.task_type_analysis || [];
    
    if (taskTypeAnalysis.length === 0) {
        tbody.innerHTML = '<tr><td colspan="10" class="empty-cell">暂无数据</td></tr>';
        return;
    }
    
    // 按任务分组
    const taskGroups = {};
    for (const item of taskTypeAnalysis) {
        const taskId = item.task_id;
        if (!taskGroups[taskId]) {
            taskGroups[taskId] = {
                task_name: item.task_name,
                page_range: item.page_range,
                created_at: item.created_at,
                subject_name: item.subject_name,
                homework_count: item.homework_count,
                overall_accuracy: item.overall_accuracy,
                types: []
            };
        }
        taskGroups[taskId].types.push(item);
    }
    
    let html = '';
    for (const taskId in taskGroups) {
        const group = taskGroups[taskId];
        const typeCount = group.types.length;
        const overallAccuracy = (group.overall_accuracy * 100).toFixed(2);
        const overallClass = overallAccuracy >= 80 ? 'high' : (overallAccuracy >= 60 ? 'medium' : 'low');
        
        // 格式化日期
        let dateStr = '-';
        if (group.created_at) {
            const date = new Date(group.created_at);
            dateStr = `${date.getFullYear()}/${(date.getMonth()+1).toString().padStart(2,'0')}/${date.getDate().toString().padStart(2,'0')}`;
        }
        
        for (let i = 0; i < typeCount; i++) {
            const typeItem = group.types[i];
            const typeAccuracy = (typeItem.type_accuracy * 100).toFixed(2);
            const typeClass = typeAccuracy >= 80 ? 'high' : (typeAccuracy >= 60 ? 'medium' : 'low');
            
            html += '<tr>';
            
            // 第一行显示任务信息，其他行合并单元格
            if (i === 0) {
                html += `
                    <td rowspan="${typeCount}">${escapeHtml(group.task_name)}</td>
                    <td rowspan="${typeCount}">${group.page_range || '-'}</td>
                    <td rowspan="${typeCount}">${dateStr}</td>
                    <td rowspan="${typeCount}">${group.subject_name}</td>
                `;
            }
            
            // 题型数据
            html += `
                <td>${typeItem.type_name}</td>
                <td>${group.homework_count}</td>
                <td>${typeItem.type_total}</td>
                <td>${typeItem.type_error}</td>
                <td class="accuracy-cell ${typeClass}">${typeAccuracy}%</td>
            `;
            
            // 综合准确率只在第一行显示
            if (i === 0) {
                html += `<td rowspan="${typeCount}" class="accuracy-cell ${overallClass}">${overallAccuracy}%</td>`;
            }
            
            html += '</tr>';
        }
    }
    
    tbody.innerHTML = html;
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function truncateText(text, maxLen) {
    if (!text) return '';
    if (text.length <= maxLen) return text;
    return text.substring(0, maxLen) + '...';
}

function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

// ========== 导出批改准确率分析表格 ==========
async function exportAccuracyAnalysis() {
    if (selectedTaskIds.size === 0) {
        alert('请先选择任务并执行分析');
        return;
    }
    
    if (!analysisResult || !analysisResult.task_type_analysis || analysisResult.task_type_analysis.length === 0) {
        alert('暂无数据可导出，请先执行分析');
        return;
    }
    
    showLoading('正在导出Excel...');
    
    try {
        const response = await fetch('/api/consolidation/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_ids: Array.from(selectedTaskIds) })
        });
        
        if (!response.ok) {
            throw new Error('导出失败');
        }
        
        // 获取文件名
        const contentDisposition = response.headers.get('Content-Disposition');
        let filename = '批改准确率分析.xlsx';
        if (contentDisposition) {
            const match = contentDisposition.match(/filename\*?=['"]?(?:UTF-8'')?([^;\n"']+)/i);
            if (match && match[1]) {
                filename = decodeURIComponent(match[1]);
            }
        }
        
        // 下载文件
        const blob = await response.blob();
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    } catch (e) {
        console.error('导出失败:', e);
        alert('导出失败: ' + e.message);
    } finally {
        hideLoading();
    }
}
