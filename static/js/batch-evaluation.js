/**
 * 批量评估页面 JavaScript
 */

// ========== 全局状态 ==========
let currentTab = 'tasks';
let taskList = [];
let selectedTask = null;
let bookList = {};
let selectedBook = null;
let datasetList = [];
let homeworkForTask = [];
let selectedHomeworkIds = new Set();
let selectedPages = new Set();
let pageBaseEffects = {};
let currentHwTaskId = ''; // 当前选中的作业任务ID
let hwTaskList = []; // 作业任务列表
let testConditions = []; // 测试条件列表
let selectedConditionId = null; // 新建任务时选中的测试条件ID
let selectedConditionName = ''; // 新建任务时选中的测试条件名称

// 学科名称映射
const SUBJECT_NAMES = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理'
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadTestConditions().then(() => {
        loadTaskList();
    });
    loadBookList();
});

// ========== 任务列表学科筛选 ==========
let currentSubjectFilter = '';
let currentConditionFilter = '';

// 加载测试条件列表
async function loadTestConditions() {
    try {
        const res = await fetch('/api/batch/test-conditions');
        const data = await res.json();
        if (data.success) {
            testConditions = data.data || [];
            renderConditionFilters();
        }
    } catch (e) {
        console.error('加载测试条件失败:', e);
    }
}

// 渲染测试条件下拉选项
function renderConditionFilters() {
    // 任务列表筛选下拉
    const taskFilter = document.getElementById('taskConditionFilter');
    if (taskFilter) {
        taskFilter.innerHTML = '<option value="">全部条件</option>' + 
            testConditions.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('');
    }
    
    // 新建任务下拉
    const hwSelect = document.getElementById('hwConditionSelect');
    if (hwSelect) {
        hwSelect.innerHTML = '<option value="">请选择测试条件</option>' + 
            testConditions.map(c => `<option value="${c.id}">${escapeHtml(c.name)}</option>`).join('') +
            '<option value="__add_new__">+ 添加新条件</option>';
    }
}

// 任务列表筛选变化
function onTaskFilterChange() {
    currentSubjectFilter = document.getElementById('taskSubjectFilter')?.value || '';
    currentConditionFilter = document.getElementById('taskConditionFilter')?.value || '';
    loadTaskList(currentSubjectFilter || null, currentConditionFilter || null);
}

function filterBySubject(subjectId) {
    currentSubjectFilter = subjectId;
    // 更新下拉选择
    const select = document.getElementById('taskSubjectFilter');
    if (select) select.value = subjectId;
    loadTaskList(subjectId || null, currentConditionFilter || null);
}

// 兼容旧函数名
function onTaskSubjectFilterChange() {
    onTaskFilterChange();
}

// ========== 返回导航 ==========
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/subject-grading';
    }
}

// ========== Tab切换 ==========
function switchTab(tab) {
    currentTab = tab;
    document.querySelectorAll('.tab-container .tab').forEach(t => {
        t.classList.toggle('active', t.dataset.tab === tab);
    });
    document.getElementById('tasksView').style.display = tab === 'tasks' ? 'flex' : 'none';
    document.getElementById('datasetsView').style.display = tab === 'datasets' ? 'flex' : 'none';
}

// ========== 加载/显示/隐藏 ==========
function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function showModal(id) {
    document.getElementById(id).classList.add('show');
}

function hideModal(id, event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById(id).classList.remove('show');
}


function showDrawer() {
    document.getElementById('evalDetailDrawer').classList.add('show');
}

function hideDrawer() {
    document.getElementById('evalDetailDrawer').classList.remove('show');
}

// ========== 任务管理 ==========
async function loadTaskList(subjectId = null, conditionId = null) {
    try {
        let url = '/api/batch/tasks';
        const params = [];
        if (subjectId !== null && subjectId !== '') {
            params.push(`subject_id=${subjectId}`);
        }
        if (conditionId !== null && conditionId !== '') {
            params.push(`test_condition_id=${conditionId}`);
        }
        if (params.length > 0) {
            url += '?' + params.join('&');
        }
        const res = await fetch(url);
        const data = await res.json();
        if (data.success) {
            taskList = data.data || [];
            renderTaskList();
        }
    } catch (e) {
        console.error('加载任务列表失败:', e);
    }
}

function renderTaskList() {
    const container = document.getElementById('taskList');
    if (taskList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">--</div>
                <div class="empty-state-text">暂无评估任务</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = taskList.map(task => `
        <div class="task-item ${selectedTask?.task_id === task.task_id ? 'selected' : ''}">
            <div class="task-item-content" onclick="selectTask('${task.task_id}')">
                <div class="task-item-title">
                    ${escapeHtml(task.name)}
                    <span class="task-item-status status-${task.status}">${getStatusText(task.status)}</span>
                </div>
                <div class="task-item-meta">
                    ${task.homework_count || 0} 个作业 | 
                    ${task.test_condition_name ? task.test_condition_name + ' | ' : ''}
                    ${task.status === 'completed' ? `准确率: ${(task.overall_accuracy * 100).toFixed(1)}% | ` : ''}
                    ${formatTime(task.created_at)}
                </div>
            </div>
        </div>
    `).join('');
}

function getStatusText(status) {
    const map = {
        'pending': '待评估',
        'running': '评估中',
        'completed': '已完成'
    };
    return map[status] || status;
}

async function selectTask(taskId) {
    showLoading('加载任务详情...');
    try {
        const res = await fetch(`/api/batch/tasks/${taskId}`);
        const data = await res.json();
        if (data.success) {
            selectedTask = data.data;
            renderTaskList();
            renderTaskDetail();
        }
    } catch (e) {
        alert('加载任务详情失败: ' + e.message);
    }
    hideLoading();
}

function renderTaskDetail() {
    if (!selectedTask) {
        document.getElementById('emptyTaskDetail').style.display = 'flex';
        document.getElementById('taskDetail').style.display = 'none';
        return;
    }
    
    document.getElementById('emptyTaskDetail').style.display = 'none';
    document.getElementById('taskDetail').style.display = 'block';
    
    document.getElementById('taskDetailTitle').textContent = selectedTask.name;
    document.getElementById('taskDetailMeta').textContent = 
        `创建时间: ${formatTime(selectedTask.created_at)} | 状态: ${getStatusText(selectedTask.status)}`;
    
    // 按钮状态
    const isCompleted = selectedTask.status === 'completed';
    const isPending = selectedTask.status === 'pending';
    const needsReset = checkTaskNeedsReset();
    
    document.getElementById('startEvalBtn').disabled = !isPending && !needsReset;
    
    if (needsReset) {
        document.getElementById('startEvalBtn').textContent = '重新评估';
        document.getElementById('startEvalBtn').className = 'btn btn-warning';
    } else if (isPending) {
        document.getElementById('startEvalBtn').textContent = '开始评估';
        document.getElementById('startEvalBtn').className = 'btn btn-secondary';
    } else if (isCompleted) {
        document.getElementById('startEvalBtn').textContent = '已完成';
        document.getElementById('startEvalBtn').className = 'btn btn-secondary';
    } else {
        document.getElementById('startEvalBtn').textContent = '评估中...';
        document.getElementById('startEvalBtn').className = 'btn btn-secondary';
    }
    
    document.getElementById('exportBtn').disabled = !isCompleted;
    document.getElementById('aiReportBtn').disabled = !isCompleted;
    
    // 显示/隐藏重新评估按钮
    const reEvalBtn = document.getElementById('reEvalBtn');
    if (reEvalBtn) {
        reEvalBtn.style.display = isCompleted ? 'inline-block' : 'none';
    }
    
    // 显示/隐藏重置按钮
    const resetBtn = document.getElementById('resetTaskBtn');
    if (resetBtn) {
        if (isCompleted && needsReset) {
            resetBtn.style.display = 'inline-block';
        } else {
            resetBtn.style.display = 'none';
        }
    }
    
    // 进度条
    if (selectedTask.status === 'running') {
        document.getElementById('progressContainer').style.display = 'block';
        const completed = selectedTask.homework_items.filter(h => h.status === 'completed' || h.status === 'failed').length;
        const total = selectedTask.homework_items.length;
        const percent = total > 0 ? (completed / total * 100) : 0;
        document.getElementById('progressFill').style.width = percent + '%';
        document.getElementById('progressText').textContent = `${completed}/${total}`;
    } else {
        document.getElementById('progressContainer').style.display = 'none';
    }
    
    // 总体报告
    if (isCompleted && selectedTask.overall_report) {
        renderOverallReport(selectedTask.overall_report);
    } else {
        document.getElementById('overallReport').style.display = 'none';
    }
    
    // 作业列表
    renderHomeworkList(selectedTask.homework_items || []);
    
    // AI报告 - 显示已保存的报告
    if (selectedTask.overall_report?.ai_analysis) {
        document.getElementById('aiReport').style.display = 'block';
        const report = selectedTask.overall_report.ai_analysis;
        
        // 构建报告内容 - 兼容新旧字段名
        let html = '';
        
        // 总体概览
        const overview = report.overview || {};
        if (overview.total) {
            html += `<div style="margin-bottom: 12px;">
                <strong>总体概览：</strong>
                总题目 ${overview.total} 题，正确 ${overview.passed} 题，错误 ${overview.failed} 题，准确率 ${overview.pass_rate}%
            </div>`;
        }
        
        // 能力评分
        const scores = report.capability_scores || {};
        if (scores.overall !== undefined) {
            html += `<div style="margin-bottom: 12px;">
                <strong>能力评分：</strong>
                识别能力 ${scores.recognition || 0}分 | 判断能力 ${scores.judgment || 0}分 | 综合评分 ${scores.overall || 0}分
            </div>`;
        }
        
        // 主要问题
        const topIssues = report.top_issues || [];
        if (topIssues.length > 0) {
            html += `<div style="margin-bottom: 12px;">
                <strong>主要问题：</strong><br>
                ${topIssues.map(i => `- ${escapeHtml(i.issue || '')}：${i.count || 0}次`).join('<br>')}
            </div>`;
        }
        
        // 改进建议
        const recommendations = report.recommendations || report.suggestions || [];
        if (recommendations.length > 0) {
            html += `<div style="margin-bottom: 12px;">
                <strong>改进建议：</strong><br>
                ${recommendations.map(s => '- ' + escapeHtml(s)).join('<br>')}
            </div>`;
        }
        
        // 总体结论
        const conclusion = report.conclusion || report.summary || '';
        if (conclusion) {
            html += `<div>
                <strong>总体结论：</strong>${escapeHtml(conclusion)}
            </div>`;
        }
        
        // 如果没有任何内容，显示原始数据
        if (!html) {
            html = `<pre style="white-space: pre-wrap; font-size: 13px;">${escapeHtml(JSON.stringify(report, null, 2))}</pre>`;
        }
        
        document.getElementById('aiReportContent').innerHTML = html;
    } else {
        document.getElementById('aiReport').style.display = 'none';
    }
}


function renderOverallReport(report) {
    document.getElementById('overallReport').style.display = 'block';
    
    const statsHtml = `
        <div class="stat-card highlight">
            <div class="stat-value">${(report.overall_accuracy * 100).toFixed(1)}%</div>
            <div class="stat-label">总体准确率</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${report.total_homework || 0}</div>
            <div class="stat-label">作业数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${report.total_questions || 0}</div>
            <div class="stat-label">题目数</div>
        </div>
        <div class="stat-card">
            <div class="stat-value">${report.correct_questions || 0}</div>
            <div class="stat-label">正确数</div>
        </div>
    `;
    document.getElementById('overallStats').innerHTML = statsHtml;
    
    // 渲染可视化图表
    renderOverallCharts(report);
    
    // 题目类型分类统计 (选择题、客观填空题、非选择题)
    let detailHtml = '';
    const byType = report.by_question_type || {};
    const byCombined = report.by_combined || {};
    
    if (Object.keys(byType).length > 0) {
        const choice = byType.choice || {};
        const objectiveFill = byType.objective_fill || {};
        const other = byType.other || {};
        
        detailHtml += `
            <div class="list-header">题目类型分类统计</div>
            <div class="type-stats-grid" style="display: flex; gap: 16px; flex-wrap: wrap;">
                <div class="type-stats-section" style="flex: 1; min-width: 280px;">
                    <table class="stats-table">
                        <thead><tr><th>类型</th><th>总数</th><th>正确</th><th>准确率</th></tr></thead>
                        <tbody>
                            <tr>
                                <td>选择题</td>
                                <td>${choice.total || 0}</td>
                                <td>${choice.correct || 0}</td>
                                <td>${choice.total > 0 ? ((choice.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                            <tr>
                                <td>客观填空题</td>
                                <td>${objectiveFill.total || 0}</td>
                                <td>${objectiveFill.correct || 0}</td>
                                <td>${objectiveFill.total > 0 ? ((objectiveFill.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                            <tr>
                                <td>非选择题</td>
                                <td>${other.total || 0}</td>
                                <td>${other.correct || 0}</td>
                                <td>${other.total > 0 ? ((other.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="type-stats-section" style="flex: 1; min-width: 280px; background: #f9f9fb; border-radius: 8px; padding: 12px;">
                    <div style="font-size: 13px; color: #86868b; margin-bottom: 8px;">自定义筛选</div>
                    <div class="filter-row" style="display: flex; gap: 8px; margin-bottom: 12px;">
                        <select id="filterObjective" style="flex: 1; padding: 8px 12px; border: 1px solid #d2d2d7; border-radius: 8px; font-size: 14px; background: #fff;">
                            <option value="objective">客观题</option>
                            <option value="subjective">主观题</option>
                        </select>
                        <select id="filterBvalue" style="flex: 1; padding: 8px 12px; border: 1px solid #d2d2d7; border-radius: 8px; font-size: 14px; background: #fff;">
                            <option value="1">单选</option>
                            <option value="3">判断</option>
                            <option value="2">多选</option>
                            <option value="4">填空</option>
                            <option value="5">解答</option>
                        </select>
                    </div>
                    <div id="filteredStatsResult" style="background: #fff; border-radius: 8px; padding: 16px; text-align: center;">
                        <div id="filteredTypeName" style="font-size: 14px; color: #1d1d1f; font-weight: 500; margin-bottom: 8px;">客观单选</div>
                        <div style="display: flex; justify-content: space-around;">
                            <div>
                                <div style="font-size: 24px; font-weight: 600; color: #1d1d1f;" id="filteredAccuracy">-</div>
                                <div style="font-size: 12px; color: #86868b;">准确率</div>
                            </div>
                            <div>
                                <div style="font-size: 18px; font-weight: 500; color: #1d1d1f;"><span id="filteredCorrect">0</span>/<span id="filteredTotal">0</span></div>
                                <div style="font-size: 12px; color: #86868b;">正确/总数</div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
        
        // 保存组合统计数据供筛选使用
        window.combinedStatsData = byCombined;
    }
    
    // 按书本统计
    if (report.by_book && Object.keys(report.by_book).length > 0) {
        detailHtml += `
            <div class="list-header">按书本统计</div>
            <table class="stats-table">
                <thead><tr><th>书本</th><th>作业数</th><th>准确率</th></tr></thead>
                <tbody>
                    ${Object.entries(report.by_book).map(([id, b]) => `
                        <tr>
                            <td>${escapeHtml(b.book_name || id)}</td>
                            <td>${b.homework_count || 0}</td>
                            <td>${(b.accuracy * 100).toFixed(1)}%</td>
                        </tr>
                    `).join('')}
                </tbody>
            </table>
        `;
    }
    document.getElementById('statsDetail').innerHTML = detailHtml;
    
    // 绑定筛选事件
    if (Object.keys(byType).length > 0) {
        const filterObjective = document.getElementById('filterObjective');
        const filterBvalue = document.getElementById('filterBvalue');
        if (filterObjective && filterBvalue) {
            const updateFilteredStats = () => {
                const objType = filterObjective.value;
                const bvalue = filterBvalue.value;
                const key = `${objType}_${bvalue}`;
                const stats = window.combinedStatsData?.[key] || { total: 0, correct: 0, accuracy: 0, name: '-' };
                const bvalueNames = { '1': '单选', '2': '多选', '3': '判断', '4': '填空', '5': '解答' };
                const typeName = (objType === 'objective' ? '客观' : '主观') + bvalueNames[bvalue];
                
                document.getElementById('filteredTypeName').textContent = typeName;
                document.getElementById('filteredAccuracy').textContent = stats.total > 0 ? ((stats.accuracy || 0) * 100).toFixed(1) + '%' : '-';
                document.getElementById('filteredCorrect').textContent = stats.correct || 0;
                document.getElementById('filteredTotal').textContent = stats.total || 0;
            };
            filterObjective.addEventListener('change', updateFilteredStats);
            filterBvalue.addEventListener('change', updateFilteredStats);
            // 初始化显示默认值 (客观单选)
            updateFilteredStats();
        }
    }
}

// ========== 图表实例 ==========
let batchChartInstances = {
    errorTypePie: null,
    typeBar: null,
    errorTrend: null,
    metricsRadar: null
};

// ========== 销毁图表 ==========
function destroyBatchCharts() {
    Object.values(batchChartInstances).forEach(chart => {
        if (chart) chart.destroy();
    });
    batchChartInstances = { errorTypePie: null, typeBar: null, errorTrend: null, metricsRadar: null };
}

// ========== 渲染总体报告图表 ==========
function renderOverallCharts(report) {
    destroyBatchCharts();
    
    // 1. 错误类型分布饼图
    const errorDist = aggregateErrorDistribution();
    const errorLabels = Object.keys(errorDist).filter(k => errorDist[k] > 0);
    const errorData = errorLabels.map(k => errorDist[k]);
    
    if (errorLabels.length > 0) {
        const colorMap = {
            '识别错误-判断正确': '#3b82f6',
            '识别错误-判断错误': '#ef4444',
            '识别正确-判断错误': '#f59e0b',
            '格式差异': '#10b981',
            '缺失题目': '#6b7280',
            'AI识别幻觉': '#8b5cf6'
        };
        const colors = errorLabels.map(label => colorMap[label] || '#6b7280');
        
        batchChartInstances.errorTypePie = new Chart(document.getElementById('errorTypePieChart'), {
            type: 'doughnut',
            data: {
                labels: errorLabels,
                datasets: [{
                    data: errorData,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: { 
                        position: 'bottom',
                        labels: { padding: 8, font: { size: 11 }, color: '#1d1d1f', boxWidth: 12 }
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                const value = context.parsed || 0;
                                const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                const percentage = ((value / total) * 100).toFixed(1);
                                return `${context.label}: ${value}题 (${percentage}%)`;
                            }
                        }
                    }
                }
            }
        });
    } else {
        // 没有错误时显示提示
        const canvas = document.getElementById('errorTypePieChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.font = '14px sans-serif';
            ctx.fillStyle = '#86868b';
            ctx.textAlign = 'center';
            ctx.fillText('暂无错误数据', canvas.width / 2, canvas.height / 2);
        }
    }
    
    // 2. 题型准确率对比柱状图 (选择题、客观填空题、非选择题)
    const byType = report.by_question_type || {};
    const choice = byType.choice || {};
    const objectiveFill = byType.objective_fill || {};
    const other = byType.other || {};
    
    const typeLabels = [];
    const typeData = [];
    const typeColors = [];
    
    if (choice.total > 0) {
        typeLabels.push('选择题');
        typeData.push((choice.accuracy || 0) * 100);
        typeColors.push('#3b82f6');
    }
    if (objectiveFill.total > 0) {
        typeLabels.push('客观填空题');
        typeData.push((objectiveFill.accuracy || 0) * 100);
        typeColors.push('#10b981');
    }
    if (other.total > 0) {
        typeLabels.push('非选择题');
        typeData.push((other.accuracy || 0) * 100);
        typeColors.push('#f59e0b');
    }
    
    if (typeLabels.length > 0) {
        batchChartInstances.typeBar = new Chart(document.getElementById('typeBarChart'), {
            type: 'bar',
            data: {
                labels: typeLabels,
                datasets: [{
                    label: '准确率',
                    data: typeData,
                    backgroundColor: typeColors,
                    borderRadius: 6,
                    barThickness: 40
                }]
            },
            options: {
                responsive: true,
                scales: {
                    y: { 
                        beginAtZero: true, 
                        max: 100,
                        ticks: { 
                            font: { size: 11 }, 
                            color: '#666',
                            callback: v => v + '%'
                        },
                        grid: { color: '#f0f0f0' }
                    },
                    x: {
                        ticks: { font: { size: 12 }, color: '#1d1d1f' },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: ctx => `准确率: ${ctx.parsed.y.toFixed(1)}%`
                        }
                    }
                }
            }
        });
    }
    
    // 3. 高频错误题目 TOP5 柱状图
    const homeworkItems = selectedTask?.homework_items || [];
    const completedItems = homeworkItems.filter(h => h.status === 'completed' && h.evaluation);
    
    if (completedItems.length > 0) {
        // 统计每道题的错误次数和错误类型（按页码+题号组合）
        const questionErrors = {}; // { 'P2-第5题': { total: 3, types: {...}, page: 2, index: '5' } }
        
        completedItems.forEach(item => {
            const pageNum = item.page_num || '?';
            // 错误数据在 evaluation.errors 数组中
            const errors = item.evaluation?.errors || [];
            errors.forEach(err => {
                const qIndex = err.index || '未知';
                const qKey = `P${pageNum}-${qIndex}`;
                const errorType = err.error_type || '未分类';
                
                if (!questionErrors[qKey]) {
                    questionErrors[qKey] = { total: 0, types: {}, page: pageNum, index: qIndex };
                }
                questionErrors[qKey].total++;
                questionErrors[qKey].types[errorType] = (questionErrors[qKey].types[errorType] || 0) + 1;
            });
        });
        
        // 按错误次数排序，取前5
        const sortedQuestions = Object.entries(questionErrors)
            .sort((a, b) => b[1].total - a[1].total)
            .slice(0, 5);
        
        // 保存到全局变量供点击事件使用
        window.topErrorQuestions = sortedQuestions;
        
        if (sortedQuestions.length > 0) {
            // 生成标签：第X题(PY)
            const labels = sortedQuestions.map(([, info]) => `第${info.index}题(P${info.page})`);
            
            // 错误类型配置
            const errorTypeConfig = [
                { key: '识别错误-判断正确', color: '#3b82f6' },
                { key: '识别错误-判断错误', color: '#ef4444' },
                { key: '识别正确-判断错误', color: '#f59e0b' },
                { key: '格式差异', color: '#10b981' },
                { key: '缺失题目', color: '#6b7280' },
                { key: 'AI识别幻觉', color: '#8b5cf6' }
            ];
            
            // 生成堆叠柱状图数据集
            const datasets = errorTypeConfig.map(type => {
                const data = sortedQuestions.map(([, info]) => info.types[type.key] || 0);
                const hasData = data.some(v => v > 0);
                return {
                    label: type.key,
                    data: data,
                    backgroundColor: type.color,
                    borderRadius: 4,
                    hidden: !hasData
                };
            });
            
            batchChartInstances.errorTrend = new Chart(document.getElementById('errorTrendChart'), {
                type: 'bar',
                data: { labels, datasets },
                options: {
                    responsive: true,
                    onClick: (event, elements) => {
                        if (elements.length > 0) {
                            const dataIndex = elements[0].index;
                            const questionInfo = window.topErrorQuestions[dataIndex];
                            if (questionInfo) {
                                const [, info] = questionInfo;
                                jumpToErrorCard(info.page, info.index);
                            }
                        }
                    },
                    scales: {
                        y: { 
                            beginAtZero: true,
                            stacked: true,
                            ticks: { font: { size: 11 }, color: '#666', stepSize: 1 },
                            grid: { color: '#f0f0f0' },
                            title: { display: true, text: '错误次数', font: { size: 11 }, color: '#666' }
                        },
                        x: {
                            stacked: true,
                            ticks: { font: { size: 11 }, color: '#1d1d1f' },
                            grid: { display: false }
                        }
                    },
                    plugins: {
                        legend: { 
                            position: 'bottom',
                            labels: { padding: 6, font: { size: 9 }, color: '#1d1d1f', boxWidth: 10 }
                        },
                        tooltip: {
                            callbacks: {
                                afterTitle: (items) => {
                                    const idx = items[0].dataIndex;
                                    const total = sortedQuestions[idx][1].total;
                                    return `总错误: ${total}次 (点击定位)`;
                                },
                                label: ctx => ctx.parsed.y > 0 ? `${ctx.dataset.label}: ${ctx.parsed.y}次` : null
                            }
                        }
                    }
                }
            });
        } else {
            // 没有错误数据
            const canvas = document.getElementById('errorTrendChart');
            if (canvas) {
                const ctx = canvas.getContext('2d');
                ctx.font = '14px sans-serif';
                ctx.fillStyle = '#86868b';
                ctx.textAlign = 'center';
                ctx.fillText('暂无错误数据', canvas.width / 2, canvas.height / 2);
            }
        }
    } else {
        // 没有数据时显示提示
        const canvas = document.getElementById('errorTrendChart');
        if (canvas) {
            const ctx = canvas.getContext('2d');
            ctx.font = '14px sans-serif';
            ctx.fillStyle = '#86868b';
            ctx.textAlign = 'center';
            ctx.fillText('暂无趋势数据', canvas.width / 2, canvas.height / 2);
        }
    }
    
    // 4. 评估指标雷达图
    const accuracy = (report.overall_accuracy || 0) * 100;
    const completeness = report.total_questions > 0 ? 100 : 0;
    const radarByType = report.by_question_type || {};
    const radarChoice = radarByType.choice || {};
    const radarObjFill = radarByType.objective_fill || {};
    const choiceAcc = radarChoice.total > 0 ? (radarChoice.accuracy || 0) * 100 : accuracy;
    const objFillAcc = radarObjFill.total > 0 ? (radarObjFill.accuracy || 0) * 100 : accuracy;
    const consistency = completedItems.length > 1 ? calculateConsistency(completedItems) : accuracy;
    
    batchChartInstances.metricsRadar = new Chart(document.getElementById('metricsRadarChart'), {
        type: 'radar',
        data: {
            labels: ['总体准确率', '选择题准确率', '客观填空准确率', '一致性', '完整性'],
            datasets: [{
                label: '评估指标',
                data: [accuracy, choiceAcc, objFillAcc, consistency, completeness],
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: '#3b82f6',
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20, font: { size: 10 }, color: '#666' },
                    pointLabels: { font: { size: 11 }, color: '#1d1d1f' },
                    grid: { color: '#e5e5e5' },
                    angleLines: { color: '#e5e5e5' }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
}

// ========== 计算一致性（准确率标准差的反向指标） ==========
function calculateConsistency(items) {
    if (items.length < 2) return 100;
    const accuracies = items.map(h => (h.accuracy || 0) * 100);
    const mean = accuracies.reduce((a, b) => a + b, 0) / accuracies.length;
    const variance = accuracies.reduce((sum, acc) => sum + Math.pow(acc - mean, 2), 0) / accuracies.length;
    const stdDev = Math.sqrt(variance);
    return Math.max(0, 100 - stdDev * 2);
}

// ========== 聚合所有作业的错误类型分布 ==========
function aggregateErrorDistribution() {
    const dist = {
        '识别错误-判断正确': 0,
        '识别错误-判断错误': 0,
        '识别正确-判断错误': 0,
        '格式差异': 0,
        '缺失题目': 0,
        'AI识别幻觉': 0
    };
    
    if (!selectedTask || !selectedTask.homework_items) return dist;
    
    selectedTask.homework_items.forEach(item => {
        const evaluation = item.evaluation || {};
        const errorDist = evaluation.error_distribution || {};
        
        Object.keys(dist).forEach(key => {
            dist[key] += errorDist[key] || 0;
        });
    });
    
    return dist;
}

function renderHomeworkList(items) {
    const container = document.getElementById('homeworkList');
    if (!items || items.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无作业</div></div>';
        return;
    }
    
    container.innerHTML = items.map(item => {
        const accuracyClass = item.accuracy >= 0.8 ? 'accuracy-high' : (item.accuracy >= 0.6 ? 'accuracy-medium' : 'accuracy-low');
        const matchStatus = item.matched_dataset ? 
            '<span class="match-status matched">已匹配</span>' : 
            '<span class="match-status unmatched">未匹配</span>';
        
        return `
            <div class="homework-item">
                <div class="homework-item-content" onclick="showHomeworkDetail('${item.homework_id}')">
                    <div class="homework-item-title">
                        ${escapeHtml(item.book_name || '未知书本')} - 第${item.page_num || '-'}页
                        ${matchStatus}
                        <span class="task-item-status status-${item.status}">${getHomeworkStatusText(item.status)}</span>
                    </div>
                    <div class="homework-item-meta">
                        学生: ${escapeHtml(item.student_name || item.student_id || '-')}
                        ${item.status === 'completed' ? ` | 准确率: <span class="homework-item-accuracy ${accuracyClass}">${(item.accuracy * 100).toFixed(1)}%</span>` : ''}
                    </div>
                </div>
                <div class="homework-item-actions">
                    <button class="btn btn-small btn-secondary" onclick="event.stopPropagation(); editBaselineData('${item.homework_id}')" title="编辑基准数据">
                        编辑
                    </button>
                    <button class="btn btn-small btn-ai" onclick="event.stopPropagation(); openAiEvaluation('${item.homework_id}')" title="AI评估">
                        AI评估
                    </button>
                </div>
            </div>
        `;
    }).join('');
}

function getHomeworkStatusText(status) {
    const map = {
        'pending': '待评估',
        'matched': '已匹配',
        'auto_recognize': '自动识别',
        'evaluating': '评估中',
        'completed': '已完成',
        'failed': '失败'
    };
    return map[status] || status;
}

// ========== 新建任务 ==========
function showCreateTaskModal() {
    // 清空任务名称，让用户选择学科后自动生成
    document.getElementById('taskNameInput').value = '';
    document.getElementById('taskNameInput').placeholder = '留空则自动生成：学科-月/日';
    selectedHomeworkIds.clear();
    currentHwTaskId = '';
    selectedConditionId = null;
    selectedConditionName = '';
    
    // 重置测试条件选择
    const conditionSelect = document.getElementById('hwConditionSelect');
    if (conditionSelect) conditionSelect.value = '';
    const addRow = document.getElementById('conditionAddRow');
    if (addRow) addRow.style.display = 'none';
    
    // 刷新测试条件列表
    renderConditionFilters();
    
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
    showModal('createTaskModal');
}

// ========== 测试条件选择变化 ==========
function onConditionSelectChange() {
    const select = document.getElementById('hwConditionSelect');
    const addRow = document.getElementById('conditionAddRow');
    
    if (select.value === '__add_new__') {
        // 显示添加新条件输入框
        addRow.style.display = 'flex';
        document.getElementById('newConditionInput').focus();
        selectedConditionId = null;
        selectedConditionName = '';
    } else {
        addRow.style.display = 'none';
        selectedConditionId = select.value ? parseInt(select.value) : null;
        // 获取选中的条件名称
        const selectedOption = select.options[select.selectedIndex];
        selectedConditionName = selectedOption && select.value ? selectedOption.text : '';
    }
}

// 保存新测试条件
async function saveNewCondition() {
    const input = document.getElementById('newConditionInput');
    const name = input.value.trim();
    
    if (!name) {
        alert('请输入测试条件名称');
        return;
    }
    
    try {
        const res = await fetch('/api/batch/test-conditions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        
        if (data.success) {
            // 添加到列表并选中
            testConditions.push({ id: data.data.id, name: name, is_system: 0 });
            renderConditionFilters();
            
            // 选中新添加的条件
            const select = document.getElementById('hwConditionSelect');
            select.value = data.data.id;
            selectedConditionId = data.data.id;
            selectedConditionName = name;
            
            // 隐藏输入框
            document.getElementById('conditionAddRow').style.display = 'none';
            input.value = '';
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

// 取消添加新条件
function cancelAddCondition() {
    document.getElementById('conditionAddRow').style.display = 'none';
    document.getElementById('newConditionInput').value = '';
    document.getElementById('hwConditionSelect').value = '';
    selectedConditionId = null;
    selectedConditionName = '';
}

// ========== 学科筛选变化时更新任务名称 ==========
function onSubjectFilterChange() {
    updateAutoTaskName();
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}

function updateAutoTaskName() {
    const nameInput = document.getElementById('taskNameInput');
    const subjectId = document.getElementById('hwSubjectFilter').value;
    
    // 如果用户已经手动输入了名称，不自动更新
    if (nameInput.value && !nameInput.value.match(/^(批量评估|语文|数学|英语|物理)-\d{1,2}\/\d{1,2}$/)) {
        return;
    }
    
    const now = new Date();
    const monthDay = `${now.getMonth() + 1}/${now.getDate()}`;
    
    if (subjectId && SUBJECT_NAMES[subjectId]) {
        nameInput.placeholder = `${SUBJECT_NAMES[subjectId]}-${monthDay}`;
    } else {
        nameInput.placeholder = `批量评估-${monthDay}`;
    }
}

// ========== 加载作业任务列表（用于筛选） ==========
async function loadHomeworkTasksForFilter() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const hours = document.getElementById('hwTimeFilter').value;
    
    try {
        let url = `/api/batch/homework-tasks?hours=${hours}`;
        if (subjectId) url += `&subject_id=${subjectId}`;
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success) {
            hwTaskList = data.data || [];
            renderHwTaskList();
        }
    } catch (e) {
        console.error('加载作业任务失败:', e);
    }
}

// ========== 渲染作业任务列表 ==========
function renderHwTaskList() {
    const container = document.getElementById('hwTaskList');
    
    let html = `
        <div class="task-item ${currentHwTaskId === '' ? 'active' : ''}" data-task-id="" onclick="selectHomeworkTask(this, '')">
            <span class="task-name">全部作业</span>
        </div>
    `;
    
    if (hwTaskList.length > 0) {
        html += hwTaskList.map(task => `
            <div class="task-item ${currentHwTaskId == task.hw_publish_id ? 'active' : ''}" 
                 data-task-id="${task.hw_publish_id}" 
                 onclick="selectHomeworkTask(this, '${task.hw_publish_id}')">
                <span class="task-name">${escapeHtml(task.task_name || '未命名任务')}</span>
                <span class="task-count">${task.homework_count || 0}</span>
            </div>
        `).join('');
    }
    
    container.innerHTML = html;
}

// ========== 选择作业任务 ==========
function selectHomeworkTask(element, taskId) {
    currentHwTaskId = taskId;
    
    // 更新选中状态
    document.querySelectorAll('#hwTaskList .task-item').forEach(item => {
        item.classList.toggle('active', item.dataset.taskId === taskId);
    });
    
    // 重新加载作业列表
    loadHomeworkForTask();
}

// ========== 过滤已选作业（只保留当前列表中存在的） ==========
function filterSelectedHomework() {
    const currentIds = new Set(homeworkForTask.map(hw => hw.id));
    const toRemove = [];
    selectedHomeworkIds.forEach(id => {
        if (!currentIds.has(id)) {
            toRemove.push(id);
        }
    });
    toRemove.forEach(id => selectedHomeworkIds.delete(id));
}

// ========== 学科筛选变化 ==========
function onSubjectFilterChange() {
    currentHwTaskId = '';
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}

// ========== 时间筛选变化 ==========
function onTimeFilterChange() {
    currentHwTaskId = '';
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}

async function loadHomeworkForTask() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const hours = document.getElementById('hwTimeFilter').value;
    
    const container = document.getElementById('homeworkSelectList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        let url = `/api/batch/homework?hours=${hours}`;
        if (subjectId) url += `&subject_id=${subjectId}`;
        if (currentHwTaskId) url += `&hw_publish_id=${currentHwTaskId}`;
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success) {
            homeworkForTask = data.data || [];
            renderHomeworkSelectList();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

function renderHomeworkSelectList() {
    const container = document.getElementById('homeworkSelectList');
    if (homeworkForTask.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无可选作业</div></div>';
        updateSelectedCount();
        return;
    }
    
    // 过滤已选作业，只保留当前列表中存在的
    filterSelectedHomework();
    
    container.innerHTML = homeworkForTask.map(hw => `
        <div class="homework-select-item ${selectedHomeworkIds.has(hw.id) ? 'selected' : ''}" 
             onclick="toggleHomeworkSelection('${hw.id}')">
            <input type="checkbox" ${selectedHomeworkIds.has(hw.id) ? 'checked' : ''} onclick="event.stopPropagation()">
            <div class="homework-select-info">
                <div class="homework-select-title">${escapeHtml(hw.homework_name || '未知作业')}</div>
                <div class="homework-select-meta">
                    ${SUBJECT_NAMES[hw.subject_id] || '未知学科'} | 
                    ${escapeHtml(hw.student_name || hw.student_id || '-')} | 
                    页码: ${hw.page_num || '-'} | 
                    ${hw.question_count || 0}题
                </div>
            </div>
        </div>
    `).join('');
    
    updateSelectedCount();
}

function toggleHomeworkSelection(hwId) {
    if (selectedHomeworkIds.has(hwId)) {
        selectedHomeworkIds.delete(hwId);
    } else {
        selectedHomeworkIds.add(hwId);
    }
    renderHomeworkSelectList();
}

function selectAllHomework() {
    homeworkForTask.forEach(hw => selectedHomeworkIds.add(hw.id));
    renderHomeworkSelectList();
}

function clearHomeworkSelection() {
    selectedHomeworkIds.clear();
    renderHomeworkSelectList();
}

function updateSelectedCount() {
    document.getElementById('selectedCount').textContent = selectedHomeworkIds.size;
}

async function createTask() {
    const name = document.getElementById('taskNameInput').value.trim();
    const subjectId = document.getElementById('hwSubjectFilter').value;
    
    if (selectedHomeworkIds.size === 0) {
        alert('请至少选择一个作业');
        return;
    }
    
    showLoading('创建任务中...');
    try {
        const res = await fetch('/api/batch/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                subject_id: subjectId ? parseInt(subjectId) : null,
                test_condition_id: selectedConditionId,
                test_condition_name: selectedConditionName,
                homework_ids: Array.from(selectedHomeworkIds)
            })
        });
        const data = await res.json();
        
        if (data.success) {
            hideModal('createTaskModal');
            await loadTaskList();
            selectTask(data.task_id);
        } else {
            alert('创建失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('创建失败: ' + e.message);
    }
    hideLoading();
}


// ========== 重新评估任务（从任务列表触发） ==========
async function reEvaluateTask(taskId) {
    if (!confirm('确定要重新评估此任务吗？将使用本地评估重新计算所有作业的评估结果。')) {
        return;
    }
    
    showLoading('正在重置任务...');
    
    try {
        // 1. 先重置任务状态
        const resetRes = await fetch(`/api/batch/tasks/${taskId}/reset`, {
            method: 'POST'
        });
        const resetData = await resetRes.json();
        
        if (!resetData.success) {
            hideLoading();
            alert('重置任务失败: ' + (resetData.error || '未知错误'));
            return;
        }
        
        // 2. 选中该任务
        selectedTask = resetData.data;
        renderTaskList();
        renderTaskDetail();
        
        hideLoading();
        
        // 3. 自动开始评估
        await startBatchEvaluation();
        
        // 4. 刷新任务列表
        await loadTaskList();
        
    } catch (e) {
        hideLoading();
        alert('重新评估失败: ' + e.message);
    }
}

// ========== 重新评估当前任务（从任务详情触发） ==========
function reEvaluateCurrentTask() {
    if (selectedTask && selectedTask.task_id) {
        reEvaluateTask(selectedTask.task_id);
    }
}


// ========== 批量评估执行 ==========
async function startBatchEvaluation() {
    if (!selectedTask) return;
    
    const needsReset = checkTaskNeedsReset();
    
    // 如果需要重置，先重置任务状态
    if (needsReset) {
        showLoading('准备重新评估...');
        try {
            const resetRes = await fetch(`/api/batch/tasks/${selectedTask.task_id}/reset`, {
                method: 'POST'
            });
            const resetData = await resetRes.json();
            
            if (!resetData.success) {
                hideLoading();
                alert('重置任务失败: ' + (resetData.error || '未知错误'));
                return;
            }
            
            selectedTask = resetData.data;
            renderTaskDetail();
        } catch (e) {
            hideLoading();
            alert('重置任务失败: ' + e.message);
            return;
        }
    }
    
    const btn = document.getElementById('startEvalBtn');
    btn.disabled = true;
    btn.textContent = '评估中...';
    btn.className = 'btn btn-secondary';
    
    document.getElementById('progressContainer').style.display = 'block';
    document.getElementById('progressFill').style.width = '0%';
    document.getElementById('progressText').textContent = '0/' + selectedTask.homework_items.length;
    
    try {
        const response = await fetch(`/api/batch/tasks/${selectedTask.task_id}/evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ auto_recognize: true })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            const lines = text.split('\n').filter(line => line.startsWith('data: '));
            
            for (const line of lines) {
                try {
                    const data = JSON.parse(line.substring(6));
                    handleEvaluationProgress(data);
                } catch (e) {
                    console.error('解析SSE数据失败:', e);
                }
            }
        }
        
        // 评估完成，重新加载任务
        await selectTask(selectedTask.task_id);
        
    } catch (e) {
        alert('评估失败: ' + e.message);
        btn.disabled = false;
        btn.textContent = needsReset ? '重新评估' : '开始评估';
        btn.className = needsReset ? 'btn btn-warning' : 'btn btn-secondary';
    }
}

function handleEvaluationProgress(data) {
    if (data.type === 'progress') {
        // 更新进度
        const item = selectedTask.homework_items.find(h => h.homework_id === data.homework_id);
        if (item) item.status = data.status;
        renderHomeworkList(selectedTask.homework_items);
    } else if (data.type === 'result') {
        // 更新结果
        const item = selectedTask.homework_items.find(h => h.homework_id === data.homework_id);
        if (item) {
            item.status = 'completed';
            item.accuracy = data.accuracy;
        }
        
        // 更新进度条
        const completed = selectedTask.homework_items.filter(h => h.status === 'completed' || h.status === 'failed').length;
        const total = selectedTask.homework_items.length;
        const percent = total > 0 ? (completed / total * 100) : 0;
        document.getElementById('progressFill').style.width = percent + '%';
        document.getElementById('progressText').textContent = `${completed}/${total}`;
        
        renderHomeworkList(selectedTask.homework_items);
    } else if (data.type === 'complete') {
        // 评估完成
        selectedTask.status = 'completed';
        selectedTask.overall_accuracy = data.overall_accuracy;
    }
}

// ========== AI评估 ==========
async function openAiEvaluation(homeworkId) {
    if (!selectedTask) return;
    
    showLoading('加载作业数据...');
    try {
        // 获取作业详情
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/homework/${homeworkId}`);
        const data = await res.json();
        
        if (!data.success) {
            hideLoading();
            alert('加载失败: ' + (data.error || '未知错误'));
            return;
        }
        
        const detail = data.data;
        hideLoading();
        
        // 打开AI评估弹窗
        showAiEvalModal(detail);
        
    } catch (e) {
        hideLoading();
        alert('加载失败: ' + e.message);
    }
}

function showAiEvalModal(homeworkDetail) {
    // 创建或获取弹窗
    let modal = document.getElementById('aiEvalModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'aiEvalModal';
        modal.className = 'modal';
        modal.onclick = (e) => { if (e.target === modal) hideModal('aiEvalModal'); };
        document.body.appendChild(modal);
    }
    
    const evaluation = homeworkDetail.evaluation || {};
    const baseEffect = homeworkDetail.base_effect || [];

    modal.innerHTML = `
        <div class="modal-content modal-large" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3>AI评估 - ${escapeHtml(homeworkDetail.book_name || '未知书本')} 第${homeworkDetail.page_num || '-'}页</h3>
                <button class="close-btn" onclick="hideModal('aiEvalModal')">x</button>
            </div>
            <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                <div class="ai-eval-info">
                    <div class="info-row">
                        <span class="info-label">学生:</span>
                        <span class="info-value">${escapeHtml(homeworkDetail.student_name || homeworkDetail.student_id || '-')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">当前准确率:</span>
                        <span class="info-value">${evaluation.accuracy ? (evaluation.accuracy * 100).toFixed(1) + '%' : '未评估'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">题目数:</span>
                        <span class="info-value">${evaluation.total_questions || baseEffect.length || 0}</span>
                    </div>
                </div>
                
                <div class="ai-eval-options">
                    <label class="eval-option">
                        <input type="checkbox" id="aiEvalUseDeepseek" checked>
                        <span>使用DeepSeek进行语义级评估</span>
                    </label>
                </div>
                
                <div class="ai-eval-actions">
                    <button class="btn btn-primary" onclick="runAiEvaluation('${homeworkDetail.homework_id}')">
                        开始评估
                    </button>
                </div>
                
                <div class="ai-eval-result" id="aiEvalResult" style="display:none;">
                    <div class="result-title">评估结果</div>
                    <div class="result-content" id="aiEvalResultContent"></div>
                </div>
            </div>
        </div>
    `;
    
    // 保存当前作业数据供评估使用
    window.currentAiEvalHomework = homeworkDetail;
    
    showModal('aiEvalModal');
}

async function runAiEvaluation(homeworkId) {
    const homework = window.currentAiEvalHomework;
    if (!homework) {
        alert('作业数据丢失，请重新打开');
        return;
    }
    
    const useDeepseek = document.getElementById('aiEvalUseDeepseek')?.checked;
    const detailAnalysis = document.getElementById('aiEvalDetailAnalysis')?.checked;
    
    showLoading('正在进行AI评估...');
    
    try {
        // 准备评估数据
        const baseEffect = homework.base_effect || [];
        const aiResult = homework.ai_result || [];
        
        if (baseEffect.length === 0) {
            hideLoading();
            alert('没有基准效果数据，无法进行评估');
            return;
        }
        
        // 调用AI评估API
        const res = await fetch('/api/grading/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effect: baseEffect,
                homework_result: aiResult,
                use_ai_compare: useDeepseek,
                detail_analysis: detailAnalysis
            })
        });
        
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            renderAiEvalResult(data.evaluation);
            
            // 更新任务中的作业评估结果
            if (selectedTask) {
                const item = selectedTask.homework_items.find(h => h.homework_id === homeworkId);
                if (item) {
                    item.accuracy = data.evaluation.accuracy;
                    item.evaluation = data.evaluation;
                    renderHomeworkList(selectedTask.homework_items);
                }
            }
        } else {
            alert('评估失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        alert('评估失败: ' + e.message);
    }
}

function renderAiEvalResult(evaluation) {
    const container = document.getElementById('aiEvalResult');
    const content = document.getElementById('aiEvalResultContent');
    
    if (!container || !content) return;
    
    const accuracy = ((evaluation.accuracy || 0) * 100).toFixed(1);
    const precision = ((evaluation.precision || evaluation.accuracy || 0) * 100).toFixed(1);
    const recall = ((evaluation.recall || evaluation.accuracy || 0) * 100).toFixed(1);
    const f1Score = ((evaluation.f1_score || evaluation.accuracy || 0) * 100).toFixed(1);
    
    let html = `
        <div class="stats-grid" style="margin-bottom: 16px;">
            <div class="stat-card highlight">
                <div class="stat-value">${accuracy}%</div>
                <div class="stat-label">准确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${precision}%</div>
                <div class="stat-label">精确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${recall}%</div>
                <div class="stat-label">召回率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${f1Score}%</div>
                <div class="stat-label">F1值</div>
            </div>
        </div>
    `;
    
    // 错误列表
    const errors = evaluation.errors || [];
    if (errors.length > 0) {
        html += `
            <div class="list-header">错误题目 (${errors.length}题)</div>
            <div class="error-list">
                ${errors.slice(0, 10).map(err => `
                    <div class="error-item">
                        <div class="error-index">题${err.index || '-'}</div>
                        <div class="error-detail">
                            <div><span class="label">错误类型:</span> <span class="tag ${getErrorTypeClass(err.error_type)}">${escapeHtml(err.error_type || '-')}</span></div>
                            <div><span class="label">说明:</span> ${escapeHtml(err.explanation || '-')}</div>
                        </div>
                    </div>
                `).join('')}
                ${errors.length > 10 ? `<div class="more-errors">还有 ${errors.length - 10} 个错误...</div>` : ''}
            </div>
        `;
    } else {
        html += '<div class="success-message">✓ 所有题目评估正确</div>';
    }
    
    content.innerHTML = html;
    container.style.display = 'block';
}

// ========== 一键AI评估所有作业 ==========
let batchEvalRunning = false;

async function batchAiEvaluation() {
    if (!selectedTask) return;
    if (batchEvalRunning) {
        alert('评估正在进行中，请稍候');
        return;
    }
    
    const items = selectedTask.homework_items || [];
    if (items.length === 0) {
        alert('没有作业可评估');
        return;
    }
    
    if (!confirm(`确定要对该任务的 ${items.length} 个作业进行AI智能评估吗？\n将调用大模型并行处理，可能需要较长时间。`)) {
        return;
    }
    
    batchEvalRunning = true;
    const btn = document.getElementById('batchAiEvalBtn');
    btn.disabled = true;
    btn.textContent = 'AI评估中...';
    
    // 显示进度条
    showBatchEvalProgress(0, items.length, 0, 0);
    
    try {
        // 使用SSE调用并行AI评估API
        const response = await fetch(`/api/batch/tasks/${selectedTask.task_id}/ai-evaluate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ parallel: 8 })  // 8个并行
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let completed = 0;
        let failed = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const text = decoder.decode(value);
            const lines = text.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6));
                        
                        if (data.type === 'start') {
                            console.log(`开始并行AI评估，共${data.total}个作业，并行数${data.parallel}`);
                        } else if (data.type === 'result') {
                            completed = data.completed;
                            updateBatchEvalProgress(completed, items.length, completed - failed, failed);
                            // 更新对应作业的状态
                            const item = items.find(i => i.homework_id == data.homework_id);
                            if (item) {
                                item.accuracy = data.accuracy;
                                item.status = 'completed';
                            }
                            renderHomeworkList(selectedTask.homework_items);
                        } else if (data.type === 'error') {
                            failed++;
                            completed = data.completed;
                            updateBatchEvalProgress(completed, items.length, completed - failed, failed);
                        } else if (data.type === 'complete') {
                            completeBatchEvalProgress(completed - failed, failed, data.overall_accuracy);
                        }
                    } catch (e) {
                        console.error('解析SSE数据失败:', e);
                    }
                }
            }
        }
    } catch (e) {
        console.error('AI评估失败:', e);
        alert('AI评估失败: ' + e.message);
    }
    
    batchEvalRunning = false;
    btn.disabled = false;
    btn.textContent = '一键AI评估';
    
    // 重新加载任务详情
    await selectTask(selectedTask.task_id);
}

async function evaluateSingleHomework(item) {
    try {
        // 获取作业详情
        const detailRes = await fetch(`/api/batch/tasks/${selectedTask.task_id}/homework/${item.homework_id}`);
        const detailData = await detailRes.json();
        
        if (!detailData.success || !detailData.data) {
            return { success: false, error: '获取详情失败' };
        }
        
        const homework = detailData.data;
        const baseEffect = homework.base_effect || [];
        const aiResult = homework.ai_result || [];
        
        if (baseEffect.length === 0) {
            return { success: false, error: '无基准效果' };
        }
        
        // 调用评估API（本地计算）
        const evalRes = await fetch('/api/grading/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effect: baseEffect,
                homework_result: aiResult,
                use_ai_compare: false
            })
        });
        
        const evalData = await evalRes.json();
        return evalData;
        
    } catch (e) {
        console.error('评估失败:', e);
        return { success: false, error: e.message };
    }
}

function showBatchEvalProgress(current, total, success, fail) {
    let progressBar = document.getElementById('batchEvalProgressBar');
    if (!progressBar) {
        progressBar = document.createElement('div');
        progressBar.id = 'batchEvalProgressBar';
        progressBar.className = 'batch-eval-progress';
        progressBar.innerHTML = `
            <div class="progress-info">
                <span class="progress-title">批量评估进度</span>
                <span class="progress-stats" id="batchEvalStats">0/${total}</span>
            </div>
            <div class="progress-bar-wrap">
                <div class="progress-bar-fill" id="batchEvalFill" style="width: 0%"></div>
            </div>
            <div class="progress-detail" id="batchEvalDetail">成功: 0 | 失败: 0</div>
        `;
        
        // 插入到任务详情区域
        const taskDetail = document.getElementById('taskDetail');
        if (taskDetail) {
            const section = taskDetail.querySelector('.section');
            if (section) {
                section.insertBefore(progressBar, section.querySelector('.homework-list-container'));
            }
        }
    }
    
    progressBar.style.display = 'block';
}

function updateBatchEvalProgress(current, total, success, fail) {
    const percent = total > 0 ? (current / total * 100) : 0;
    const fill = document.getElementById('batchEvalFill');
    const stats = document.getElementById('batchEvalStats');
    const detail = document.getElementById('batchEvalDetail');
    
    if (fill) fill.style.width = percent + '%';
    if (stats) stats.textContent = `${current}/${total}`;
    if (detail) detail.textContent = `成功: ${success} | 失败: ${fail}`;
}

function completeBatchEvalProgress(success, fail, overallAccuracy) {
    const progressBar = document.getElementById('batchEvalProgressBar');
    if (progressBar) {
        const detail = document.getElementById('batchEvalDetail');
        if (detail) {
            let msg = `<span style="color: #1d1d1f; font-weight: 500;">评估完成 - 成功: ${success} | 失败: ${fail}`;
            if (overallAccuracy !== undefined) {
                msg += ` | 总体准确率: ${(overallAccuracy * 100).toFixed(1)}%`;
            }
            msg += '</span>';
            detail.innerHTML = msg;
        }
        
        // 5秒后隐藏
        setTimeout(() => {
            progressBar.style.display = 'none';
        }, 5000);
    }
}

// ========== 作业详情 ==========
async function showHomeworkDetail(homeworkId) {
    if (!selectedTask) return;
    
    showLoading('加载评估详情...');
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/homework/${homeworkId}`);
        const data = await res.json();
        
        if (data.success) {
            renderEvalDetail(data.data);
            showDrawer();
        } else {
            alert('加载失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
    hideLoading();
}

function renderEvalDetail(detail) {
    document.getElementById('evalDetailTitle').textContent = 
        `${detail.book_name || '未知书本'} - 第${detail.page_num || '-'}页`;
    
    const evaluation = detail.evaluation || {};
    const errors = evaluation.errors || [];
    const errorDist = evaluation.error_distribution || {};
    
    // 计算各项指标
    const accuracy = ((evaluation.accuracy || 0) * 100).toFixed(1);
    const precision = ((evaluation.precision || evaluation.accuracy || 0) * 100).toFixed(1);
    const recall = ((evaluation.recall || evaluation.accuracy || 0) * 100).toFixed(1);
    const f1Score = ((evaluation.f1_score || evaluation.accuracy || 0) * 100).toFixed(1);
    const hallucinationRate = ((evaluation.hallucination_rate || 0) * 100).toFixed(1);
    
    let html = `
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-value">${accuracy}%</div>
                <div class="stat-label">准确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${precision}%</div>
                <div class="stat-label">精确率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${recall}%</div>
                <div class="stat-label">召回率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${f1Score}%</div>
                <div class="stat-label">F1值</div>
            </div>
            <div class="stat-card warning">
                <div class="stat-value">${hallucinationRate}%</div>
                <div class="stat-label">幻觉率</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${evaluation.total_questions || 0}</div>
                <div class="stat-label">总题数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${evaluation.correct_count || 0}</div>
                <div class="stat-label">正确数</div>
            </div>
            <div class="stat-card error">
                <div class="stat-value">${evaluation.error_count || 0}</div>
                <div class="stat-label">错误数</div>
            </div>
        </div>
    `;
    
    // 错误类型分布
    if (Object.keys(errorDist).length > 0) {
        const hasErrors = Object.values(errorDist).some(v => v > 0);
        if (hasErrors) {
            html += `
                <div class="list-header">错误类型分布</div>
                <div class="error-dist-grid">
                    ${Object.entries(errorDist).map(([type, count]) => {
                        if (count === 0) return '';
                        const colorMap = {
                            '识别错误-判断正确': '#3b82f6',
                            '识别错误-判断错误': '#ef4444',
                            '识别正确-判断错误': '#f59e0b',
                            '格式差异': '#10b981',
                            '缺失题目': '#6b7280',
                            'AI识别幻觉': '#8b5cf6'
                        };
                        const color = colorMap[type] || '#6b7280';
                        return `
                            <div class="error-dist-item" style="border-left: 4px solid ${color};">
                                <div class="error-dist-type">${type}</div>
                                <div class="error-dist-count">${count}题</div>
                            </div>
                        `;
                    }).join('')}
                </div>
            `;
        }
    }
    
    // 错误题目详情 - 卡片式展示
    if (errors.length > 0) {
        html += `<div class="list-header">错误题目详情</div>
            <div class="error-cards-container">
                ${errors.map(err => {
                    const baseEffect = err.base_effect || {};
                    const aiResult = err.ai_result || {};
                    const errorTypeClass = getErrorTypeClass(err.error_type);
                    const severity = err.severity || err.severity_code || 'medium';
                    const severityClass = getSeverityClass(severity);
                    
                    return `
                        <div class="error-card" data-page="${detail.page_num || ''}" data-index="${err.index || ''}">
                            <div class="error-card-header">
                                <div class="error-card-title">
                                    <span class="error-index">题${err.index || '-'}</span>
                                    <span class="severity-badge severity-${severityClass}">${severity === 'high' ? '高' : severity === 'low' ? '低' : '中'}</span>
                                    <span class="tag ${errorTypeClass}">${escapeHtml(err.error_type || '-')}</span>
                                </div>
                            </div>
                            <div class="error-card-body">
                                <div class="compare-table-wrap">
                                    <table class="compare-detail-table">
                                        <thead>
                                            <tr>
                                                <th class="field-col">字段</th>
                                                <th class="base-col">基准效果</th>
                                                <th class="ai-col">AI批改结果</th>
                                                <th class="match-col">匹配</th>
                                            </tr>
                                        </thead>
                                        <tbody>
                                            <tr class="highlight-row">
                                                <td class="field-name">用户答案</td>
                                                <td class="base-value user-answer">${escapeHtml(baseEffect.userAnswer || '-')}</td>
                                                <td class="ai-value user-answer">${escapeHtml(aiResult.userAnswer || '-')}</td>
                                                <td class="match-status">${(baseEffect.userAnswer || '') === (aiResult.userAnswer || '') ? '<span class="match-yes">✓</span>' : '<span class="match-no">✗</span>'}</td>
                                            </tr>
                                            <tr>
                                                <td class="field-name">判断结果</td>
                                                <td class="base-value"><span class="${baseEffect.correct === 'yes' ? 'text-success' : 'text-error'}">${baseEffect.correct || '-'}</span></td>
                                                <td class="ai-value"><span class="${aiResult.correct === 'yes' ? 'text-success' : 'text-error'}">${aiResult.correct || '-'}</span></td>
                                                <td class="match-status">${(baseEffect.correct || '') === (aiResult.correct || '') ? '<span class="match-yes">✓</span>' : '<span class="match-no">✗</span>'}</td>
                                            </tr>
                                        </tbody>
                                    </table>
                                </div>
                                <div class="error-explanation">
                                    <span class="explanation-label">分析：</span>
                                    <span class="explanation-text">${escapeHtml(err.explanation || '-')}</span>
                                </div>
                            </div>
                        </div>
                    `;
                }).join('')}
            </div>
        `;
    }
    
    // 添加完整的基准效果和AI批改结果数据表格
    const baseEffect = detail.base_effect || [];
    const aiResult = detail.ai_result || [];
    
    // 展开AI结果中的children结构
    const flattenAiResult = flattenHomeworkResult(aiResult);
    const totalAiQuestions = countTotalQuestions(aiResult);
    
    if (baseEffect.length > 0 || aiResult.length > 0) {
        html += `
            <div class="list-header" style="margin-top: 24px;">
                完整数据对比
                <div class="view-toggle-btns">
                    <button class="btn btn-small view-toggle-btn active" onclick="toggleDataView('table')">表格视图</button>
                    <button class="btn btn-small view-toggle-btn" onclick="toggleDataView('compare')">逐题对比</button>
                </div>
            </div>
            
            <!-- 表格视图 -->
            <div class="data-view-container" id="tableView">
                <div class="data-tables-container">
                    <div class="data-table-section">
                        <div class="data-table-title">
                            <span class="title-icon base-icon">基</span>
                            基准效果数据 (${baseEffect.length}题)
                            <button class="btn btn-small btn-toggle-json" onclick="toggleJsonView('baseEffect')">切换JSON</button>
                        </div>
                        <div class="data-table-wrap" id="baseEffectTableWrap">
                            <table class="full-data-table">
                                <thead>
                                    <tr>
                                        <th>题号</th>
                                        <th>用户答案</th>
                                        <th>标准答案</th>
                                        <th>判断</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${baseEffect.map(item => `
                                        <tr>
                                            <td class="index-cell">${escapeHtml(String(item.index || '-'))}</td>
                                            <td class="answer-cell">${escapeHtml(item.userAnswer || '-')}</td>
                                            <td class="answer-cell muted">${escapeHtml(item.answer || item.mainAnswer || '-')}</td>
                                            <td class="correct-cell"><span class="${getCorrectClass(item)}">${getCorrectText(item)}</span></td>
                                        </tr>
                                    `).join('')}
                                </tbody>
                            </table>
                        </div>
                        <div class="json-view-wrap" id="baseEffectJsonWrap" style="display:none;">
                            <pre class="json-data-display">${JSON.stringify(baseEffect, null, 2)}</pre>
                        </div>
                    </div>
                    
                    <div class="data-table-section">
                        <div class="data-table-title">
                            <span class="title-icon ai-icon">AI</span>
                            AI批改结果数据 (${totalAiQuestions}题)
                            <button class="btn btn-small btn-toggle-json" onclick="toggleJsonView('aiResult')">切换JSON</button>
                        </div>
                        <div class="data-table-wrap" id="aiResultTableWrap">
                            <table class="full-data-table ai-result-table">
                                <thead>
                                    <tr>
                                        <th>题号</th>
                                        <th>用户答案</th>
                                        <th>标准答案</th>
                                        <th>判断</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    ${renderAiResultRows(aiResult)}
                                </tbody>
                            </table>
                        </div>
                        <div class="json-view-wrap" id="aiResultJsonWrap" style="display:none;">
                            <pre class="json-data-display">${JSON.stringify(aiResult, null, 2)}</pre>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 逐题对比视图 -->
            <div class="data-view-container" id="compareView" style="display:none;">
                <div class="question-compare-list">
                    ${renderQuestionCompareCards(baseEffect, flattenAiResult)}
                </div>
            </div>
        `;
    }
    
    document.getElementById('evalDetailBody').innerHTML = html;
}

// 展开homework_result中的children结构
function flattenHomeworkResult(result) {
    if (!result || !Array.isArray(result)) return [];
    const flattened = [];
    result.forEach(item => {
        const children = item.children || [];
        if (children.length > 0) {
            children.forEach(child => flattened.push(child));
        } else {
            flattened.push(item);
        }
    });
    return flattened;
}

// 统计AI结果总题数（包括小题）
function countTotalQuestions(result) {
    if (!result || !Array.isArray(result)) return 0;
    let count = 0;
    result.forEach(item => {
        const children = item.children || [];
        if (children.length > 0) {
            count += children.length;
        } else {
            count += 1;
        }
    });
    return count;
}

// 获取判断结果的CSS类
function getCorrectClass(item) {
    const correct = item.correct || (item.isRight ? 'yes' : (item.isRight === false ? 'no' : ''));
    if (correct === 'yes' || correct === true) return 'text-success';
    if (correct === 'no' || correct === false) return 'text-error';
    return 'text-muted';
}

// 获取判断结果文本
function getCorrectText(item) {
    const correct = item.correct;
    if (correct !== undefined) return correct;
    if (item.isRight === true) return 'yes';
    if (item.isRight === false) return 'no';
    return '-';
}

// 渲染AI结果表格行（直接展开显示所有小题）
function renderAiResultRows(aiResult) {
    if (!aiResult || !Array.isArray(aiResult)) return '<tr><td colspan="4" class="empty-cell">暂无数据</td></tr>';
    
    // 按索引排序
    const sortedResult = [...aiResult].sort((a, b) => {
        const indexA = parseFloat(a.index) || 0;
        const indexB = parseFloat(b.index) || 0;
        return indexA - indexB;
    });
    
    let html = '';
    sortedResult.forEach(item => {
        const children = item.children || [];
        const hasChildren = children.length > 0;
        
        if (hasChildren) {
            // 有小题时，显示父题作为分组标题，然后直接展示所有小题
            html += `
                <tr class="parent-row-header">
                    <td colspan="4" class="parent-title-cell">
                        <span class="parent-index">第${escapeHtml(String(item.index || '-'))}题</span>
                        <span class="children-count">(${children.length}个小题)</span>
                    </td>
                </tr>
            `;
            // 对小题也按索引排序后渲染
            const sortedChildren = [...children].sort((a, b) => {
                const indexA = parseFloat(a.index) || 0;
                const indexB = parseFloat(b.index) || 0;
                return indexA - indexB;
            });
            sortedChildren.forEach((child, idx) => {
                html += `
                    <tr class="child-row-visible">
                        <td class="index-cell child-index">${escapeHtml(String(child.index || `${item.index}-${idx+1}`))}</td>
                        <td class="answer-cell">${escapeHtml(child.userAnswer || '-')}</td>
                        <td class="answer-cell muted">${escapeHtml(child.answer || child.mainAnswer || '-')}</td>
                        <td class="correct-cell"><span class="${getCorrectClass(child)}">${getCorrectText(child)}</span></td>
                    </tr>
                `;
            });
        } else {
            // 无小题，直接显示
            html += `
                <tr>
                    <td class="index-cell">${escapeHtml(String(item.index || '-'))}</td>
                    <td class="answer-cell">${escapeHtml(item.userAnswer || '-')}</td>
                    <td class="answer-cell muted">${escapeHtml(item.answer || item.mainAnswer || '-')}</td>
                    <td class="correct-cell"><span class="${getCorrectClass(item)}">${getCorrectText(item)}</span></td>
                </tr>
            `;
        }
    });
    
    return html || '<tr><td colspan="4" class="empty-cell">暂无数据</td></tr>';
}

// 渲染逐题对比卡片
function renderQuestionCompareCards(baseEffect, flatAiResult) {
    if (!baseEffect || baseEffect.length === 0) {
        return '<div class="empty-state"><div class="empty-state-text">暂无基准数据</div></div>';
    }
    
    // 构建AI结果索引
    const aiDict = {};
    flatAiResult.forEach(item => {
        const idx = String(item.index || '');
        if (idx) aiDict[idx] = item;
    });
    
    let html = '';
    baseEffect.forEach((base, i) => {
        const idx = String(base.index || '');
        const ai = aiDict[idx] || null;
        
        // 判断是否匹配
        const baseUser = (base.userAnswer || '').trim();
        const aiUser = ai ? (ai.userAnswer || '').trim() : '';
        const baseCorrect = base.correct || (base.isRight ? 'yes' : 'no');
        const aiCorrect = ai ? (ai.correct || (ai.isRight ? 'yes' : 'no')) : '';
        
        const userMatch = baseUser === aiUser;
        const correctMatch = baseCorrect === aiCorrect;
        const isMatch = userMatch && correctMatch;
        
        const cardClass = !ai ? 'missing' : (isMatch ? 'match' : 'mismatch');
        
        html += `
            <div class="question-compare-card ${cardClass}">
                <div class="compare-card-header">
                    <span class="compare-index">第${idx || (i+1)}题</span>
                    <span class="compare-status ${cardClass}">${!ai ? '缺失' : (isMatch ? '匹配' : '不匹配')}</span>
                </div>
                <div class="compare-card-body">
                    <div class="compare-row">
                        <div class="compare-label">用户答案</div>
                        <div class="compare-base ${!userMatch ? 'highlight' : ''}">${escapeHtml(baseUser || '-')}</div>
                        <div class="compare-ai ${!userMatch ? 'highlight' : ''}">${escapeHtml(aiUser || '-')}</div>
                        <div class="compare-match">${userMatch ? '<span class="match-yes">✓</span>' : '<span class="match-no">✗</span>'}</div>
                    </div>
                    <div class="compare-row">
                        <div class="compare-label">标准答案</div>
                        <div class="compare-base">${escapeHtml(base.answer || base.mainAnswer || '-')}</div>
                        <div class="compare-ai">${ai ? escapeHtml(ai.answer || ai.mainAnswer || '-') : '-'}</div>
                        <div class="compare-match">-</div>
                    </div>
                    <div class="compare-row">
                        <div class="compare-label">判断结果</div>
                        <div class="compare-base"><span class="${baseCorrect === 'yes' ? 'text-success' : 'text-error'}">${baseCorrect}</span></div>
                        <div class="compare-ai"><span class="${aiCorrect === 'yes' ? 'text-success' : (aiCorrect === 'no' ? 'text-error' : '')}">${aiCorrect || '-'}</span></div>
                        <div class="compare-match">${correctMatch ? '<span class="match-yes">✓</span>' : '<span class="match-no">✗</span>'}</div>
                    </div>
                </div>
            </div>
        `;
    });
    
    return html;
}

// 切换数据视图
function toggleDataView(view) {
    const tableView = document.getElementById('tableView');
    const compareView = document.getElementById('compareView');
    const btns = document.querySelectorAll('.view-toggle-btn');
    
    btns.forEach(btn => btn.classList.remove('active'));
    
    if (view === 'table') {
        tableView.style.display = 'block';
        compareView.style.display = 'none';
        btns[0].classList.add('active');
    } else {
        tableView.style.display = 'none';
        compareView.style.display = 'block';
        btns[1].classList.add('active');
    }
}

// 切换表格/JSON视图
function toggleJsonView(type) {
    const tableWrap = document.getElementById(type + 'TableWrap');
    const jsonWrap = document.getElementById(type + 'JsonWrap');
    const btn = event.target;
    
    if (tableWrap && jsonWrap) {
        if (jsonWrap.style.display === 'none') {
            tableWrap.style.display = 'none';
            jsonWrap.style.display = 'block';
            btn.textContent = '切换表格';
            btn.classList.add('active');
        } else {
            tableWrap.style.display = 'block';
            jsonWrap.style.display = 'none';
            btn.textContent = '切换JSON';
            btn.classList.remove('active');
        }
    }
}

// 复制JSON到剪贴板
function copyToClipboard(elementId) {
    const element = document.getElementById(elementId);
    if (element) {
        navigator.clipboard.writeText(element.textContent).then(() => {
            alert('已复制到剪贴板');
        }).catch(err => {
            console.error('复制失败:', err);
            // 降级方案
            const textarea = document.createElement('textarea');
            textarea.value = element.textContent;
            document.body.appendChild(textarea);
            textarea.select();
            document.execCommand('copy');
            document.body.removeChild(textarea);
            alert('已复制到剪贴板');
        });
    }
}

function getErrorTypeClass(errorType) {
    const classMap = {
        '识别错误-判断正确': 'tag-info',
        '识别错误-判断错误': 'tag-error',
        '识别正确-判断错误': 'tag-warning',
        '格式差异': 'tag-success',
        '缺失题目': 'tag-default',
        'AI识别幻觉': 'tag-purple',
        '标准答案不一致': 'tag-orange'
    };
    return classMap[errorType] || 'tag-default';
}

function getSeverityClass(severity) {
    const map = {
        'high': 'high',
        'medium': 'medium',
        'low': 'low',
        '高': 'high',
        '中': 'medium',
        '低': 'low'
    };
    return map[severity] || 'medium';
}

// ========== AI报告 ==========
async function generateAIReport() {
    if (!selectedTask) return;
    
    showLoading('生成AI分析报告...');
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/ai-report`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
            document.getElementById('aiReport').style.display = 'block';
            const report = data.report || {};
            
            // 构建报告内容 - 兼容新旧字段名
            let html = '';
            
            // 总体概览
            const overview = report.overview || {};
            if (overview.total) {
                html += `<div style="margin-bottom: 12px;">
                    <strong>总体概览：</strong>
                    总题目 ${overview.total} 题，正确 ${overview.passed} 题，错误 ${overview.failed} 题，准确率 ${overview.pass_rate}%
                </div>`;
            }
            
            // 能力评分
            const scores = report.capability_scores || {};
            if (scores.overall !== undefined) {
                html += `<div style="margin-bottom: 12px;">
                    <strong>能力评分：</strong>
                    识别能力 ${scores.recognition || 0}分 | 判断能力 ${scores.judgment || 0}分 | 综合评分 ${scores.overall || 0}分
                </div>`;
            }
            
            // 主要问题
            const topIssues = report.top_issues || [];
            if (topIssues.length > 0) {
                html += `<div style="margin-bottom: 12px;">
                    <strong>主要问题：</strong><br>
                    ${topIssues.map(i => `- ${escapeHtml(i.issue || '')}：${i.count || 0}次`).join('<br>')}
                </div>`;
            }
            
            // 改进建议
            const recommendations = report.recommendations || report.suggestions || [];
            if (recommendations.length > 0) {
                html += `<div style="margin-bottom: 12px;">
                    <strong>改进建议：</strong><br>
                    ${recommendations.map(s => '- ' + escapeHtml(s)).join('<br>')}
                </div>`;
            }
            
            // 总体结论
            const conclusion = report.conclusion || report.summary || '';
            if (conclusion) {
                html += `<div>
                    <strong>总体结论：</strong>${escapeHtml(conclusion)}
                </div>`;
            }
            
            // 如果没有任何内容，显示原始数据
            if (!html) {
                html = `<pre style="white-space: pre-wrap; font-size: 13px;">${escapeHtml(JSON.stringify(report, null, 2))}</pre>`;
            }
            
            document.getElementById('aiReportContent').innerHTML = html;
            
            // 更新任务数据
            if (!selectedTask.overall_report) selectedTask.overall_report = {};
            selectedTask.overall_report.ai_analysis = report;
        } else {
            alert('生成失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('生成失败: ' + e.message);
    }
    hideLoading();
}

// ========== Excel导出 ==========
async function exportExcel() {
    if (!selectedTask) return;
    
    showLoading('生成Excel文件...');
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/export`);
        if (res.ok) {
            const blob = await res.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `批量评估报告_${selectedTask.name}.xlsx`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(url);
        } else {
            const data = await res.json();
            alert('导出失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
    hideLoading();
}

// ========== 删除任务 ==========
async function deleteCurrentTask() {
    if (!selectedTask) return;
    if (!confirm('确定要删除此任务吗？删除后无法恢复。')) return;
    
    showLoading('删除任务...');
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        
        if (data.success) {
            selectedTask = null;
            await loadTaskList();
            renderTaskDetail();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
    hideLoading();
}


// ========== 图书和数据集管理 ==========
async function loadBookList() {
    try {
        const res = await fetch('/api/batch/books');
        const data = await res.json();
        if (data.success) {
            bookList = data.data || {};
            renderBookList();
        }
    } catch (e) {
        console.error('加载图书列表失败:', e);
    }
}

function filterBooks() {
    renderBookList();
}

function renderBookList() {
    const container = document.getElementById('bookList');
    const filterSubject = document.getElementById('subjectFilter').value;
    
    let html = '';
    let hasBooks = false;
    
    for (const [subjectId, books] of Object.entries(bookList)) {
        if (filterSubject && filterSubject !== subjectId) continue;
        if (!books || books.length === 0) continue;
        
        hasBooks = true;
        html += `
            <div class="subject-group">
                <div class="subject-group-title">${SUBJECT_NAMES[subjectId] || '未知学科'}</div>
                ${books.map(book => `
                    <div class="book-item ${selectedBook?.book_id === book.book_id ? 'selected' : ''}" 
                         onclick="selectBook('${book.book_id}', ${subjectId})">
                        <div class="book-item-title">${escapeHtml(book.book_name)}</div>
                        <div class="book-item-meta">${book.page_count || 0} 页</div>
                    </div>
                `).join('')}
            </div>
        `;
    }
    
    if (!hasBooks) {
        html = `
            <div class="empty-state">
                <div class="empty-state-icon">--</div>
                <div class="empty-state-text">暂无图书数据</div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

async function selectBook(bookId, subjectId) {
    showLoading('加载书本详情...');
    try {
        // 查找书本信息
        const books = bookList[subjectId] || [];
        selectedBook = books.find(b => b.book_id === bookId);
        
        if (!selectedBook) {
            alert('未找到书本信息');
            hideLoading();
            return;
        }
        
        // 加载页码列表
        const pagesRes = await fetch(`/api/batch/books/${bookId}/pages`);
        const pagesData = await pagesRes.json();
        
        // 加载数据集列表
        const datasetsRes = await fetch(`/api/batch/datasets?book_id=${bookId}`);
        const datasetsData = await datasetsRes.json();
        
        if (pagesData.success) {
            selectedBook.pages = pagesData.data?.all_pages || [];
            selectedBook.chapters = pagesData.data?.chapters || [];
        }
        
        if (datasetsData.success) {
            datasetList = datasetsData.data || [];
        }
        
        renderBookList();
        renderBookDetail();
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
    hideLoading();
}

function renderBookDetail() {
    if (!selectedBook) {
        document.getElementById('emptyBookDetail').style.display = 'flex';
        document.getElementById('bookDetail').style.display = 'none';
        return;
    }
    
    document.getElementById('emptyBookDetail').style.display = 'none';
    document.getElementById('bookDetail').style.display = 'block';
    
    document.getElementById('bookDetailTitle').textContent = selectedBook.book_name;
    document.getElementById('bookDetailMeta').textContent = 
        `共 ${selectedBook.pages?.length || 0} 页 | ${datasetList.length} 个数据集`;
    
    // 渲染数据集列表
    const datasetContainer = document.getElementById('datasetList');
    if (datasetList.length === 0) {
        datasetContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集</div></div>';
    } else {
        datasetContainer.innerHTML = datasetList.map(ds => `
            <div class="dataset-item">
                <div class="dataset-item-title">页码: ${ds.pages?.join(', ') || '-'}</div>
                <div class="dataset-item-meta">
                    ${ds.question_count || 0} 题 | ${formatTime(ds.created_at)}
                </div>
                <div class="dataset-item-actions">
                    <button class="btn btn-small btn-danger" onclick="deleteDataset('${ds.dataset_id}')">删除</button>
                </div>
            </div>
        `).join('');
    }
    
    // 渲染页码列表
    const pageContainer = document.getElementById('pageList');
    const pagesWithDataset = new Set();
    datasetList.forEach(ds => (ds.pages || []).forEach(p => pagesWithDataset.add(p)));
    
    if (!selectedBook.pages || selectedBook.pages.length === 0) {
        pageContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无页码数据</div></div>';
    } else {
        pageContainer.innerHTML = selectedBook.pages.map(page => `
            <span class="page-item ${pagesWithDataset.has(page) ? 'has-dataset' : ''}">${page}</span>
        `).join('');
    }
}

// ========== 数据集管理 ==========
function showAddDatasetModal() {
    if (!selectedBook) {
        alert('请先选择图书');
        return;
    }
    
    selectedPages.clear();
    pageBaseEffects = {};
    
    // 渲染页码选择
    const pageSelectContainer = document.getElementById('pageSelectList');
    pageSelectContainer.innerHTML = (selectedBook.pages || []).map(page => `
        <div class="page-select-item" data-page="${page}" onclick="togglePageSelection(${page})">${page}</div>
    `).join('');
    
    document.getElementById('baseEffectConfig').innerHTML = 
        '<div class="empty-state"><div class="empty-state-text">请先选择页码</div></div>';
    
    showModal('addDatasetModal');
}

function togglePageSelection(page) {
    if (selectedPages.has(page)) {
        selectedPages.delete(page);
    } else {
        selectedPages.add(page);
    }
    
    // 更新选中状态
    document.querySelectorAll('.page-select-item').forEach(el => {
        el.classList.toggle('selected', selectedPages.has(parseInt(el.dataset.page)));
    });
    
    renderBaseEffectConfig();
}

function renderBaseEffectConfig() {
    const container = document.getElementById('baseEffectConfig');
    
    if (selectedPages.size === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">请先选择页码</div></div>';
        return;
    }
    
    const sortedPages = Array.from(selectedPages).sort((a, b) => a - b);
    
    container.innerHTML = sortedPages.map(page => `
        <div class="page-effect-section">
            <div class="page-effect-header">
                <span class="page-effect-title">第 ${page} 页</span>
                <button class="btn btn-small" onclick="autoRecognizePage(${page})">自动识别</button>
            </div>
            <textarea id="pageEffect_${page}" rows="4" placeholder="输入基准效果JSON数组，或点击自动识别"
                      onchange="updatePageEffect(${page}, this.value)">${pageBaseEffects[page] ? JSON.stringify(pageBaseEffects[page], null, 2) : ''}</textarea>
        </div>
    `).join('');
}

function updatePageEffect(page, value) {
    try {
        pageBaseEffects[page] = JSON.parse(value);
    } catch (e) {
        // 解析失败，保持原值
    }
}

async function autoRecognizePage(page) {
    if (!selectedBook) {
        alert('请先选择图书');
        return;
    }
    
    showLoading('检查可用作业图片...');
    
    try {
        // 先检查是否有可用的作业图片
        const checkRes = await fetch(`/api/batch/datasets/available-homework?book_id=${selectedBook.book_id}&page_num=${page}&minutes=60`);
        const checkData = await checkRes.json();
        
        if (!checkData.success) {
            hideLoading();
            alert('检查失败: ' + (checkData.error || '未知错误'));
            return;
        }
        
        if (!checkData.data.available || checkData.data.homework_list.length === 0) {
            hideLoading();
            alert(`第${page}页在最近60分钟内没有可用的作业图片，请手动输入基准效果JSON`);
            return;
        }
        
        // 显示可选作业列表
        const homeworkList = checkData.data.homework_list;
        
        // 如果只有一个作业，直接使用
        let selectedHomeworkId = homeworkList[0].homework_id;
        
        // 如果有多个作业，让用户选择
        if (homeworkList.length > 1) {
            const options = homeworkList.map((hw, idx) => 
                `${idx + 1}. ${hw.student_name} (${formatTime(hw.create_time)})`
            ).join('\n');
            
            const choice = prompt(`第${page}页有${homeworkList.length}个可用作业，请选择（输入序号）：\n${options}`, '1');
            
            if (!choice) {
                hideLoading();
                return;
            }
            
            const idx = parseInt(choice) - 1;
            if (idx < 0 || idx >= homeworkList.length) {
                hideLoading();
                alert('无效的选择');
                return;
            }
            
            selectedHomeworkId = homeworkList[idx].homework_id;
        }
        
        // 调用自动识别API
        showLoading('正在识别基准效果...');
        
        const recognizeRes = await fetch('/api/batch/datasets/auto-recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: selectedBook.book_id,
                page_num: page,
                homework_id: selectedHomeworkId
            })
        });
        
        const recognizeData = await recognizeRes.json();
        hideLoading();
        
        if (!recognizeData.success) {
            alert('识别失败: ' + (recognizeData.error || '未知错误'));
            return;
        }
        
        // 更新基准效果
        pageBaseEffects[page] = recognizeData.base_effect;
        
        // 更新文本框
        const textarea = document.getElementById(`pageEffect_${page}`);
        if (textarea) {
            textarea.value = JSON.stringify(recognizeData.base_effect, null, 2);
        }
        
        // 显示来源信息
        const source = recognizeData.source_homework;
        alert(`识别成功！\n来源: ${source.student_name}\n识别到 ${recognizeData.base_effect.length} 道题`);
        
    } catch (e) {
        hideLoading();
        alert('自动识别失败: ' + e.message);
    }
}

async function saveDataset() {
    if (!selectedBook) {
        alert('请先选择图书');
        return;
    }
    
    if (selectedPages.size === 0) {
        alert('请至少选择一个页码');
        return;
    }
    
    // 收集基准效果数据
    const baseEffects = {};
    for (const page of selectedPages) {
        const textarea = document.getElementById(`pageEffect_${page}`);
        if (textarea && textarea.value.trim()) {
            try {
                baseEffects[page] = JSON.parse(textarea.value);
            } catch (e) {
                alert(`第${page}页的基准效果JSON格式错误`);
                return;
            }
        }
    }
    
    showLoading('保存数据集...');
    try {
        const res = await fetch('/api/batch/datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: selectedBook.book_id,
                pages: Array.from(selectedPages),
                base_effects: baseEffects
            })
        });
        const data = await res.json();
        
        if (data.success) {
            hideModal('addDatasetModal');
            // 重新加载数据集
            const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedBook.book_id}`);
            const datasetsData = await datasetsRes.json();
            if (datasetsData.success) {
                datasetList = datasetsData.data || [];
            }
            renderBookDetail();
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
    hideLoading();
}

async function deleteDataset(datasetId) {
    if (!confirm('确定要删除此数据集吗？')) return;
    
    showLoading('删除数据集...');
    try {
        const res = await fetch(`/api/batch/datasets/${datasetId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        
        if (data.success) {
            // 重新加载数据集
            const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedBook.book_id}`);
            const datasetsData = await datasetsRes.json();
            if (datasetsData.success) {
                datasetList = datasetsData.data || [];
            }
            renderBookDetail();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
    hideLoading();
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timeStr) {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return date.toLocaleString('zh-CN', {
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ========== 编辑基准数据功能 ==========
async function editBaselineData(homeworkId) {
    if (!selectedTask) return;
    
    showLoading('加载基准数据...');
    try {
        // 获取作业详情
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/homework/${homeworkId}`);
        const data = await res.json();
        
        if (!data.success) {
            hideLoading();
            alert('加载失败: ' + (data.error || '未知错误'));
            return;
        }
        
        const detail = data.data;
        hideLoading();
        
        // 打开编辑基准数据弹窗
        showEditBaselineModal(detail);
        
    } catch (e) {
        hideLoading();
        alert('加载失败: ' + e.message);
    }
}

// 编辑基准数据的临时存储
let baselineEditData = [];

function showEditBaselineModal(homeworkDetail) {
    // 创建或获取弹窗
    let modal = document.getElementById('editBaselineModal');
    if (!modal) {
        modal = document.createElement('div');
        modal.id = 'editBaselineModal';
        modal.className = 'modal';
        modal.onclick = (e) => { if (e.target === modal) hideModal('editBaselineModal'); };
        document.body.appendChild(modal);
    }
    
    // 深拷贝基准数据到临时存储
    const baseEffect = homeworkDetail.base_effect || [];
    baselineEditData = JSON.parse(JSON.stringify(baseEffect));
    
    const aiResult = homeworkDetail.ai_result || [];
    
    modal.innerHTML = `
        <div class="modal-content modal-large" onclick="event.stopPropagation()">
            <div class="modal-header">
                <h3>编辑基准数据 - ${escapeHtml(homeworkDetail.book_name || '未知书本')} 第${homeworkDetail.page_num || '-'}页</h3>
                <button class="close-btn" onclick="hideModal('editBaselineModal')">x</button>
            </div>
            <div class="modal-body" style="max-height: 70vh; overflow-y: auto;">
                <div class="baseline-edit-info">
                    <div class="info-row">
                        <span class="info-label">学生:</span>
                        <span class="info-value">${escapeHtml(homeworkDetail.student_name || homeworkDetail.student_id || '-')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">书本ID:</span>
                        <span class="info-value">${escapeHtml(homeworkDetail.book_id || '-')}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">页码:</span>
                        <span class="info-value">${homeworkDetail.page_num || '-'}</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">当前基准题目数:</span>
                        <span class="info-value" id="baselineQuestionCount">${baseEffect.length}</span>
                    </div>
                </div>
                
                <div class="baseline-edit-tabs">
                    <div class="tab-buttons">
                        <button class="tab-btn active" onclick="switchBaselineTab('table')">表格编辑</button>
                        <button class="tab-btn" onclick="switchBaselineTab('json')">JSON编辑</button>
                        <button class="tab-btn" onclick="switchBaselineTab('compare')">对比视图</button>
                    </div>
                </div>
                
                <!-- 表格编辑视图 -->
                <div class="baseline-tab-content" id="baselineTableTab">
                    <div class="baseline-table-actions">
                        <button class="btn btn-small" onclick="addBaselineQuestion()">添加题目</button>
                        <button class="btn btn-small btn-secondary" onclick="autoFillFromAI()">从AI结果填充</button>
                        <button class="btn btn-small btn-secondary" onclick="clearAllBaseline()">清空全部</button>
                    </div>
                    <div class="baseline-table-container">
                        <table class="baseline-edit-table" id="baselineEditTable">
                            <thead>
                                <tr>
                                    <th style="width:80px">题号</th>
                                    <th>用户答案</th>
                                    <th style="width:100px">判断结果</th>
                                    <th style="width:60px">操作</th>
                                </tr>
                            </thead>
                            <tbody id="baselineTableBody">
                                <!-- 动态生成 -->
                            </tbody>
                        </table>
                    </div>
                </div>
                
                <!-- JSON编辑视图 -->
                <div class="baseline-tab-content" id="baselineJsonTab" style="display:none;">
                    <div class="json-edit-actions">
                        <button class="btn btn-small" onclick="formatBaselineJson()">格式化</button>
                        <button class="btn btn-small btn-secondary" onclick="validateBaselineJson()">验证并应用</button>
                    </div>
                    <textarea id="baselineJsonEditor" rows="20" placeholder="输入基准效果JSON数组...">${JSON.stringify(baseEffect, null, 2)}</textarea>
                    <div class="json-validation-result" id="jsonValidationResult"></div>
                </div>
                
                <!-- 对比视图 -->
                <div class="baseline-tab-content" id="baselineCompareTab" style="display:none;">
                    <div class="compare-view-container">
                        <div class="compare-section">
                            <div class="compare-section-title">基准数据 (<span id="compareBaseCount">${baseEffect.length}</span>题)</div>
                            <div class="compare-data-table" id="compareBaseTable">
                                <!-- 动态生成 -->
                            </div>
                        </div>
                        <div class="compare-section">
                            <div class="compare-section-title">AI批改结果 (${aiResult.length}题)</div>
                            <div class="compare-data-table">
                                <table class="compare-table">
                                    <thead>
                                        <tr><th>题号</th><th>用户答案</th><th>判断</th></tr>
                                    </thead>
                                    <tbody>
                                        ${aiResult.map(item => `
                                            <tr>
                                                <td>${escapeHtml(String(item.index || '-'))}</td>
                                                <td>${escapeHtml(item.userAnswer || '-')}</td>
                                                <td><span class="${item.correct === 'yes' ? 'text-success' : 'text-error'}">${item.correct || '-'}</span></td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn btn-secondary" onclick="hideModal('editBaselineModal')">取消</button>
                <button class="btn btn-primary" onclick="saveBaselineData('${homeworkDetail.homework_id}')">保存基准数据</button>
            </div>
        </div>
    `;
    
    // 保存当前作业数据
    window.currentEditingHomework = homeworkDetail;
    window.currentEditingAiResult = aiResult;
    
    // 渲染表格
    renderBaselineEditTable();
    
    showModal('editBaselineModal');
}

function switchBaselineTab(tabName) {
    // 更新按钮状态
    document.querySelectorAll('.baseline-edit-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.target.classList.add('active');
    
    // 显示对应内容
    document.querySelectorAll('.baseline-tab-content').forEach(content => {
        content.style.display = 'none';
    });
    
    if (tabName === 'table') {
        document.getElementById('baselineTableTab').style.display = 'block';
        renderBaselineEditTable();
    } else if (tabName === 'json') {
        document.getElementById('baselineJsonTab').style.display = 'block';
        syncJsonFromTable();
    } else if (tabName === 'compare') {
        document.getElementById('baselineCompareTab').style.display = 'block';
        renderCompareBaseTable();
    }
}

function renderBaselineEditTable() {
    const tbody = document.getElementById('baselineTableBody');
    if (!tbody) return;
    
    // 按题号排序
    const sortedData = [...baselineEditData].sort((a, b) => {
        const indexA = parseFloat(a.index) || 0;
        const indexB = parseFloat(b.index) || 0;
        return indexA - indexB;
    });
    
    tbody.innerHTML = sortedData.map((item, displayIndex) => {
        // 找到原始索引
        const originalIndex = baselineEditData.findIndex(d => d === item);
        return `
        <tr data-index="${originalIndex}">
            <td>
                <input type="text" class="form-input-small baseline-index-input" 
                       value="${escapeHtml(String(item.index || ''))}" 
                       data-field="index" data-idx="${originalIndex}">
            </td>
            <td>
                <input type="text" class="form-input baseline-answer-input" 
                       value="${escapeHtml(item.userAnswer || '')}" 
                       data-field="userAnswer" data-idx="${originalIndex}">
            </td>
            <td>
                <select class="form-select baseline-correct-select" data-field="correct" data-idx="${originalIndex}">
                    <option value="">请选择</option>
                    <option value="yes" ${item.correct === 'yes' ? 'selected' : ''}>正确</option>
                    <option value="no" ${item.correct === 'no' ? 'selected' : ''}>错误</option>
                </select>
            </td>
            <td>
                <button class="btn btn-small btn-danger" onclick="removeBaselineQuestion(${originalIndex})">删除</button>
            </td>
        </tr>
    `}).join('');
    
    // 绑定输入事件
    tbody.querySelectorAll('input, select').forEach(el => {
        el.addEventListener('change', handleBaselineFieldChange);
        el.addEventListener('input', handleBaselineFieldChange);
    });
    
    updateBaselineCount();
}

function handleBaselineFieldChange(e) {
    const field = e.target.dataset.field;
    const idx = parseInt(e.target.dataset.idx, 10);
    const value = e.target.value;
    
    if (idx >= 0 && idx < baselineEditData.length) {
        baselineEditData[idx][field] = value;
    }
}

function updateBaselineCount() {
    const countEl = document.getElementById('baselineQuestionCount');
    if (countEl) {
        countEl.textContent = baselineEditData.length;
    }
}

function addBaselineQuestion() {
    // 计算新题号
    let maxIndex = 0;
    baselineEditData.forEach(item => {
        const idx = parseFloat(item.index) || 0;
        if (idx > maxIndex) maxIndex = idx;
    });
    
    baselineEditData.push({
        index: String(Math.floor(maxIndex) + 1),
        userAnswer: '',
        correct: ''
    });
    
    renderBaselineEditTable();
}

function removeBaselineQuestion(index) {
    if (index < 0 || index >= baselineEditData.length) return;
    
    if (confirm('确定要删除这道题吗？')) {
        baselineEditData.splice(index, 1);
        renderBaselineEditTable();
    }
}

function autoFillFromAI() {
    const aiResult = window.currentEditingAiResult || [];
    if (aiResult.length === 0) {
        alert('没有AI批改结果可以填充');
        return;
    }
    
    if (!confirm(`确定要用AI批改结果(${aiResult.length}题)覆盖当前基准数据吗？`)) {
        return;
    }
    
    // 展开AI结果中的children
    baselineEditData = [];
    aiResult.forEach(item => {
        const children = item.children || [];
        if (children.length > 0) {
            children.forEach(child => {
                baselineEditData.push({
                    index: String(child.index || ''),
                    userAnswer: child.userAnswer || '',
                    correct: child.correct || ''
                });
            });
        } else {
            baselineEditData.push({
                index: String(item.index || ''),
                userAnswer: item.userAnswer || '',
                correct: item.correct || ''
            });
        }
    });
    
    renderBaselineEditTable();
    alert('已从AI批改结果填充基准数据');
}

function clearAllBaseline() {
    if (!confirm('确定要清空所有基准数据吗？')) {
        return;
    }
    
    baselineEditData = [];
    renderBaselineEditTable();
}

function syncJsonFromTable() {
    const jsonEditor = document.getElementById('baselineJsonEditor');
    if (jsonEditor) {
        jsonEditor.value = JSON.stringify(baselineEditData, null, 2);
    }
}

function renderCompareBaseTable() {
    const container = document.getElementById('compareBaseTable');
    const countEl = document.getElementById('compareBaseCount');
    if (!container) return;
    
    if (countEl) {
        countEl.textContent = baselineEditData.length;
    }
    
    container.innerHTML = `
        <table class="compare-table">
            <thead>
                <tr><th>题号</th><th>用户答案</th><th>判断</th></tr>
            </thead>
            <tbody>
                ${baselineEditData.map(item => `
                    <tr>
                        <td>${escapeHtml(String(item.index || '-'))}</td>
                        <td>${escapeHtml(item.userAnswer || '-')}</td>
                        <td><span class="${item.correct === 'yes' ? 'text-success' : 'text-error'}">${item.correct || '-'}</span></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
    `;
}

function formatBaselineJson() {
    const jsonEditor = document.getElementById('baselineJsonEditor');
    if (!jsonEditor) return;
    
    try {
        const parsed = JSON.parse(jsonEditor.value);
        jsonEditor.value = JSON.stringify(parsed, null, 2);
        document.getElementById('jsonValidationResult').innerHTML = 
            '<span style="color: #10b981;">JSON格式正确</span>';
    } catch (e) {
        document.getElementById('jsonValidationResult').innerHTML = 
            '<span style="color: #ef4444;">JSON格式错误: ' + escapeHtml(e.message) + '</span>';
    }
}

function validateBaselineJson() {
    const jsonEditor = document.getElementById('baselineJsonEditor');
    if (!jsonEditor) return;
    
    try {
        const parsed = JSON.parse(jsonEditor.value);
        if (!Array.isArray(parsed)) {
            throw new Error('基准数据必须是数组格式');
        }
        
        // 验证每个题目的必要字段
        for (let i = 0; i < parsed.length; i++) {
            const item = parsed[i];
            if (!item.hasOwnProperty('index')) {
                throw new Error(`第${i+1}个题目缺少index字段`);
            }
            if (!item.hasOwnProperty('userAnswer')) {
                throw new Error(`第${i+1}个题目缺少userAnswer字段`);
            }
            if (!item.hasOwnProperty('correct')) {
                throw new Error(`第${i+1}个题目缺少correct字段`);
            }
        }
        
        document.getElementById('jsonValidationResult').innerHTML = 
            `<span style="color: #10b981;">JSON格式正确，包含${parsed.length}道题目，已应用到编辑数据</span>`;
        
        // 更新临时存储的数据
        baselineEditData = parsed;
        updateBaselineCount();
        
    } catch (e) {
        document.getElementById('jsonValidationResult').innerHTML = 
            '<span style="color: #ef4444;">' + escapeHtml(e.message) + '</span>';
    }
}

async function saveBaselineData(homeworkId) {
    const homework = window.currentEditingHomework;
    if (!homework) {
        alert('没有可保存的数据');
        return;
    }
    
    // 如果当前在JSON编辑模式，先验证并同步数据
    const activeTab = document.querySelector('.baseline-edit-tabs .tab-btn.active');
    if (activeTab && activeTab.textContent.includes('JSON')) {
        const jsonEditor = document.getElementById('baselineJsonEditor');
        if (jsonEditor) {
            try {
                const parsed = JSON.parse(jsonEditor.value);
                baselineEditData = parsed;
            } catch (e) {
                alert('JSON格式错误，请先修正: ' + e.message);
                return;
            }
        }
    }
    
    // 使用临时存储的数据
    const baseEffect = baselineEditData || [];
    
    if (baseEffect.length === 0) {
        if (!confirm('基准数据为空，确定要保存吗？')) {
            return;
        }
    }
    
    showLoading('保存基准数据...');
    
    try {
        // 查找或创建对应的数据集
        const bookId = homework.book_id;
        const pageNum = homework.page_num;
        const pageNumInt = parseInt(pageNum, 10);
        
        if (!bookId || pageNum === null || pageNum === undefined) {
            hideLoading();
            alert('缺少书本ID或页码信息，无法保存');
            return;
        }
        
        // 先查找是否已有对应book_id的数据集（不管页码）
        const datasetsRes = await fetch(`/api/batch/datasets?book_id=${bookId}`);
        const datasetsData = await datasetsRes.json();
        
        let targetDatasetId = null;
        let existingDataset = null;
        
        if (datasetsData.success) {
            const datasets = datasetsData.data || [];
            // 优先查找包含该页码的数据集
            for (const ds of datasets) {
                if (ds.pages) {
                    // 同时检查整数和字符串形式的页码
                    const hasPage = ds.pages.some(p => 
                        parseInt(p, 10) === pageNumInt || String(p) === String(pageNum)
                    );
                    if (hasPage) {
                        targetDatasetId = ds.dataset_id;
                        existingDataset = ds;
                        break;
                    }
                }
            }
            
            // 如果没有找到包含该页码的数据集，使用同一book_id的第一个数据集
            if (!targetDatasetId && datasets.length > 0) {
                targetDatasetId = datasets[0].dataset_id;
                existingDataset = datasets[0];
            }
        }
        
        if (targetDatasetId) {
            // 更新现有数据集 - 添加或更新该页码的基准效果
            // 先获取完整的数据集数据
            const fullDatasetRes = await fetch(`/api/batch/datasets/${targetDatasetId}`);
            const fullDatasetData = await fullDatasetRes.json();
            
            if (!fullDatasetData.success) {
                throw new Error('获取数据集详情失败');
            }
            
            const existingBaseEffects = fullDatasetData.data.base_effects || {};
            const existingPages = fullDatasetData.data.pages || [];
            
            // 合并基准效果
            existingBaseEffects[String(pageNumInt)] = baseEffect;
            
            // 确保页码列表包含当前页码
            const newPages = [...new Set([...existingPages.map(p => parseInt(p, 10)), pageNumInt])].sort((a, b) => a - b);
            
            const updateRes = await fetch(`/api/batch/datasets/${targetDatasetId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    pages: newPages,
                    base_effects: existingBaseEffects
                })
            });
            
            const updateData = await updateRes.json();
            if (!updateData.success) {
                throw new Error(updateData.error || '更新数据集失败');
            }
            
            console.log(`已更新数据集 ${targetDatasetId}，页码: ${pageNumInt}`);
        } else {
            // 创建新数据集
            const createRes = await fetch('/api/batch/datasets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    book_id: bookId,
                    pages: [pageNumInt],
                    base_effects: {
                        [String(pageNumInt)]: baseEffect
                    }
                })
            });
            
            const createData = await createRes.json();
            if (!createData.success) {
                throw new Error(createData.error || '创建数据集失败');
            }
            
            targetDatasetId = createData.dataset_id;
            console.log(`已创建新数据集 ${targetDatasetId}，页码: ${pageNumInt}`);
        }
        
        hideLoading();
        hideModal('editBaselineModal');
        
        // 更新任务中的作业匹配状态
        if (selectedTask) {
            const item = selectedTask.homework_items.find(h => h.homework_id === homeworkId);
            if (item) {
                item.matched_dataset = targetDatasetId;
                item.status = 'matched';
                // 如果之前已经评估过，清除评估结果以便重新评估
                if (item.accuracy !== null || item.evaluation) {
                    item.accuracy = null;
                    item.evaluation = null;
                }
                renderHomeworkList(selectedTask.homework_items);
            }
            
            // 刷新整个任务的数据集匹配状态
            refreshTaskDatasets();
        }
        
        alert(`基准数据保存成功！\n数据集ID: ${targetDatasetId}\n题目数: ${baseEffect.length}`);
        
    } catch (e) {
        hideLoading();
        alert('保存失败: ' + e.message);
    }
}
// ========== 任务状态管理 ==========
async function refreshTaskDatasets() {
    if (!selectedTask) return;
    
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/refresh-datasets`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
            // 更新本地任务数据
            selectedTask = data.data;
            renderTaskDetail();
            
            // 如果有更新，显示提示
            if (data.updated_count > 0) {
                console.log(`已刷新 ${data.updated_count} 个作业的数据集匹配状态`);
            }
        }
    } catch (e) {
        console.error('刷新数据集匹配状态失败:', e);
    }
}

async function resetBatchTask() {
    if (!selectedTask) return;
    
    if (!confirm('确定要重置此任务吗？\n重置后可以重新进行批量评估，但会清除当前的评估结果。')) {
        return;
    }
    
    showLoading('重置任务状态...');
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/reset`, {
            method: 'POST'
        });
        const data = await res.json();
        
        if (data.success) {
            selectedTask = data.data;
            renderTaskDetail();
            alert('任务已重置，可以重新进行批量评估');
        } else {
            alert('重置失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('重置失败: ' + e.message);
    }
    hideLoading();
}

function checkTaskNeedsReset() {
    if (!selectedTask) return false;
    
    // 检查是否有作业的数据集匹配状态发生变化但任务仍为已完成状态
    if (selectedTask.status === 'completed') {
        const hasNewMatches = selectedTask.homework_items.some(item => 
            item.matched_dataset && (item.status === 'matched' || item.status === 'pending')
        );
        
        if (hasNewMatches) {
            return true;
        }
    }
    
    return false;
}


// ========== 从图表跳转到错误卡片 ==========
function jumpToErrorCard(pageNum, questionIndex) {
    // 首先需要找到对应页码的作业并展开详情
    if (!selectedTask || !selectedTask.homework_items) {
        console.log('没有选中的任务');
        return;
    }
    
    // 查找匹配页码的作业
    const targetHomework = selectedTask.homework_items.find(item => 
        String(item.page_num) === String(pageNum) && item.status === 'completed'
    );
    
    if (!targetHomework) {
        // 如果没有找到精确匹配，尝试在抽屉中查找错误卡片
        const errorCards = document.querySelectorAll('.error-card');
        for (const card of errorCards) {
            const cardPage = card.dataset.page;
            const cardIndex = card.dataset.index;
            if (String(cardPage) === String(pageNum) && String(cardIndex) === String(questionIndex)) {
                // 移除其他卡片的高亮
                errorCards.forEach(c => c.classList.remove('highlighted'));
                // 高亮目标卡片
                card.classList.add('highlighted');
                // 滚动到卡片
                card.scrollIntoView({ behavior: 'smooth', block: 'center' });
                return;
            }
        }
        console.log('未找到匹配的作业:', pageNum, questionIndex);
        return;
    }
    
    // 打开作业详情抽屉
    showHomeworkDetail(targetHomework.homework_id).then(() => {
        // 等待抽屉渲染完成后查找错误卡片
        setTimeout(() => {
            const errorCards = document.querySelectorAll('.error-card');
            let targetCard = null;
            
            for (const card of errorCards) {
                const cardIndex = card.dataset.index;
                if (String(cardIndex) === String(questionIndex)) {
                    targetCard = card;
                    break;
                }
            }
            
            if (targetCard) {
                // 移除其他卡片的高亮
                errorCards.forEach(c => c.classList.remove('highlighted'));
                // 高亮目标卡片
                targetCard.classList.add('highlighted');
                // 滚动到卡片
                targetCard.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }
        }, 300);
    });
}
