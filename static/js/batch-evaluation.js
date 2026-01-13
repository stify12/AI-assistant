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

// 学科名称映射
const SUBJECT_NAMES = {
    0: '英语',
    1: '语文',
    2: '数学',
    3: '物理'
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadTaskList();
    loadBookList();
});

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
async function loadTaskList() {
    try {
        const res = await fetch('/api/batch/tasks');
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
        <div class="task-item ${selectedTask?.task_id === task.task_id ? 'selected' : ''}" 
             onclick="selectTask('${task.task_id}')">
            <div class="task-item-title">
                ${escapeHtml(task.name)}
                <span class="task-item-status status-${task.status}">${getStatusText(task.status)}</span>
            </div>
            <div class="task-item-meta">
                ${task.homework_count || 0} 个作业 | 
                ${task.status === 'completed' ? `准确率: ${(task.overall_accuracy * 100).toFixed(1)}% | ` : ''}
                ${formatTime(task.created_at)}
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
    document.getElementById('startEvalBtn').disabled = !isPending;
    document.getElementById('startEvalBtn').textContent = isPending ? '开始评估' : (isCompleted ? '已完成' : '评估中...');
    document.getElementById('exportBtn').disabled = !isCompleted;
    document.getElementById('aiReportBtn').disabled = !isCompleted;
    
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
    
    // AI报告
    if (selectedTask.overall_report?.ai_analysis) {
        document.getElementById('aiReport').style.display = 'block';
        document.getElementById('aiReportContent').textContent = 
            selectedTask.overall_report.ai_analysis.summary || '';
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
    
    // 题目类型分类统计
    let detailHtml = '';
    const byType = report.by_question_type || {};
    if (Object.keys(byType).length > 0) {
        const objective = byType.objective || {};
        const subjective = byType.subjective || {};
        const choice = byType.choice || {};
        const nonChoice = byType.non_choice || {};
        
        detailHtml += `
            <div class="list-header">题目类型分类统计</div>
            <div class="type-stats-grid">
                <div class="type-stats-section">
                    <div class="type-stats-title">主观/客观题</div>
                    <table class="stats-table">
                        <thead><tr><th>类型</th><th>总数</th><th>正确</th><th>准确率</th></tr></thead>
                        <tbody>
                            <tr>
                                <td>客观题</td>
                                <td>${objective.total || 0}</td>
                                <td>${objective.correct || 0}</td>
                                <td>${objective.total > 0 ? ((objective.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                            <tr>
                                <td>主观题</td>
                                <td>${subjective.total || 0}</td>
                                <td>${subjective.correct || 0}</td>
                                <td>${subjective.total > 0 ? ((subjective.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
                <div class="type-stats-section">
                    <div class="type-stats-title">选择/非选择题</div>
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
                                <td>非选择题</td>
                                <td>${nonChoice.total || 0}</td>
                                <td>${nonChoice.correct || 0}</td>
                                <td>${nonChoice.total > 0 ? ((nonChoice.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                        </tbody>
                    </table>
                </div>
            </div>
        `;
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
    document.getElementById('taskNameInput').value = `批量评估-${new Date().toLocaleDateString()}`;
    selectedHomeworkIds.clear();
    loadHomeworkForTask();
    showModal('createTaskModal');
}

async function loadHomeworkForTask() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const hours = document.getElementById('hwTimeFilter').value;
    
    const container = document.getElementById('homeworkSelectList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        let url = `/api/batch/homework?hours=${hours}`;
        if (subjectId) url += `&subject_id=${subjectId}`;
        
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
        return;
    }
    
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
    if (!name) {
        alert('请输入任务名称');
        return;
    }
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


// ========== 批量评估执行 ==========
async function startBatchEvaluation() {
    if (!selectedTask) return;
    
    const btn = document.getElementById('startEvalBtn');
    btn.disabled = true;
    btn.textContent = '评估中...';
    
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
        btn.textContent = '开始评估';
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
                            'AI幻觉': '#8b5cf6'
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
                        <div class="error-card">
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
    
    if (baseEffect.length > 0 || aiResult.length > 0) {
        html += `
            <div class="list-header" style="margin-top: 24px;">完整数据对比</div>
            <div class="data-tables-container">
                <div class="data-table-section">
                    <div class="data-table-title">
                        <span class="title-icon base-icon">基</span>
                        基准效果数据 (${baseEffect.length}题)
                        <button class="btn btn-small btn-copy" onclick="copyToClipboard('baseEffectData')">复制JSON</button>
                    </div>
                    <div class="data-table-wrap">
                        <table class="full-data-table">
                            <thead>
                                <tr>
                                    <th>题号</th>
                                    <th>用户答案</th>
                                    <th>判断</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${baseEffect.map(item => `
                                    <tr>
                                        <td class="index-cell">${escapeHtml(String(item.index || '-'))}</td>
                                        <td class="answer-cell">${escapeHtml(item.userAnswer || '-')}</td>
                                        <td class="correct-cell"><span class="${item.correct === 'yes' || item.isRight === true ? 'text-success' : 'text-error'}">${item.correct || (item.isRight ? 'yes' : 'no') || '-'}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <pre class="json-data" id="baseEffectData" style="display:none;">${JSON.stringify(baseEffect, null, 2)}</pre>
                </div>
                
                <div class="data-table-section">
                    <div class="data-table-title">
                        <span class="title-icon ai-icon">AI</span>
                        AI批改结果数据 (${aiResult.length}题)
                        <button class="btn btn-small btn-copy" onclick="copyToClipboard('aiResultData')">复制JSON</button>
                    </div>
                    <div class="data-table-wrap">
                        <table class="full-data-table">
                            <thead>
                                <tr>
                                    <th>题号</th>
                                    <th>用户答案</th>
                                    <th>判断</th>
                                </tr>
                            </thead>
                            <tbody>
                                ${aiResult.map(item => `
                                    <tr>
                                        <td class="index-cell">${escapeHtml(String(item.index || '-'))}</td>
                                        <td class="answer-cell">${escapeHtml(item.userAnswer || '-')}</td>
                                        <td class="correct-cell"><span class="${item.correct === 'yes' || item.isRight === true ? 'text-success' : 'text-error'}">${item.correct || (item.isRight ? 'yes' : 'no') || '-'}</span></td>
                                    </tr>
                                `).join('')}
                            </tbody>
                        </table>
                    </div>
                    <pre class="json-data" id="aiResultData" style="display:none;">${JSON.stringify(aiResult, null, 2)}</pre>
                </div>
            </div>
        `;
    }
    
    document.getElementById('evalDetailBody').innerHTML = html;
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
        'AI幻觉': 'tag-purple',
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
            document.getElementById('aiReportContent').innerHTML = `
                <strong>总结：</strong>${escapeHtml(report.summary || '')}<br><br>
                <strong>诊断：</strong>${escapeHtml(report.diagnosis || '')}<br><br>
                <strong>建议：</strong><br>${(report.suggestions || []).map(s => '- ' + escapeHtml(s)).join('<br>')}
            `;
            
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
