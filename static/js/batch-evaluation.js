/**
 * 批量评估页面 JavaScript
 */

// ========== 更多操作下拉菜单 ==========
function toggleMoreActions(event) {
    event.stopPropagation();
    const menu = document.getElementById('moreActionsMenu');
    menu.classList.toggle('show');
}

function hideMoreActions() {
    const menu = document.getElementById('moreActionsMenu');
    if (menu) menu.classList.remove('show');
}

// 点击页面其他地方关闭下拉菜单
document.addEventListener('click', function(e) {
    if (!e.target.closest('.more-actions-dropdown')) {
        hideMoreActions();
    }
});

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
let selectedHwTaskIds = new Set(); // 选中的作业任务ID集合（支持多选）
let hwTaskList = []; // 作业任务列表
let isLoadingHomework = false; // 作业列表加载状态
let testConditions = []; // 测试条件列表
let selectedConditionId = null; // 新建任务时选中的测试条件ID
let selectedConditionName = ''; // 新建任务时选中的测试条件名称

// 评估设置（从localStorage加载）
let evalSettings = {
    fuzzyThreshold: 85,
    ignoreIndexPrefix: true
};

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

// ========== LaTeX/Markdown 公式转换 ==========
// 希腊字母映射
const GREEK_LETTERS = {
    '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ', '\\delta': 'δ',
    '\\epsilon': 'ε', '\\varepsilon': 'ε', '\\zeta': 'ζ', '\\eta': 'η',
    '\\theta': 'θ', '\\iota': 'ι', '\\kappa': 'κ', '\\lambda': 'λ',
    '\\mu': 'μ', '\\nu': 'ν', '\\xi': 'ξ', '\\pi': 'π',
    '\\rho': 'ρ', '\\sigma': 'σ', '\\tau': 'τ', '\\upsilon': 'υ',
    '\\phi': 'φ', '\\chi': 'χ', '\\psi': 'ψ', '\\omega': 'ω',
    '\\Gamma': 'Γ', '\\Delta': 'Δ', '\\Theta': 'Θ', '\\Lambda': 'Λ',
    '\\Xi': 'Ξ', '\\Pi': 'Π', '\\Sigma': 'Σ', '\\Phi': 'Φ',
    '\\Psi': 'Ψ', '\\Omega': 'Ω'
};

// 数学运算符映射
const MATH_OPERATORS = {
    '\\times': '×', '\\div': '÷', '\\pm': '±', '\\cdot': '·',
    '\\leq': '≤', '\\le': '≤', '\\geq': '≥', '\\ge': '≥',
    '\\neq': '≠', '\\approx': '≈', '\\equiv': '≡',
    '\\infty': '∞', '\\partial': '∂', '\\nabla': '∇',
    '\\angle': '∠', '\\perp': '⊥', '\\parallel': '∥',
    '\\triangle': '△', '\\rightarrow': '→', '\\leftarrow': '←',
    '\\Rightarrow': '⇒', '\\Leftarrow': '⇐',
    '\\int': '∫', '\\sum': 'Σ', '\\prod': 'Π'
};

// 上标字符映射
const SUPERSCRIPT_MAP = {
    '0': '⁰', '1': '¹', '2': '²', '3': '³', '4': '⁴',
    '5': '⁵', '6': '⁶', '7': '⁷', '8': '⁸', '9': '⁹',
    '+': '⁺', '-': '⁻', '=': '⁼', '(': '⁽', ')': '⁾',
    'a': 'ᵃ', 'b': 'ᵇ', 'c': 'ᶜ', 'd': 'ᵈ', 'e': 'ᵉ',
    'f': 'ᶠ', 'g': 'ᵍ', 'h': 'ʰ', 'i': 'ⁱ', 'j': 'ʲ',
    'k': 'ᵏ', 'l': 'ˡ', 'm': 'ᵐ', 'n': 'ⁿ', 'o': 'ᵒ',
    'p': 'ᵖ', 'r': 'ʳ', 's': 'ˢ', 't': 'ᵗ', 'u': 'ᵘ',
    'v': 'ᵛ', 'w': 'ʷ', 'x': 'ˣ', 'y': 'ʸ', 'z': 'ᶻ'
};

// 下标字符映射
const SUBSCRIPT_MAP = {
    '0': '₀', '1': '₁', '2': '₂', '3': '₃', '4': '₄',
    '5': '₅', '6': '₆', '7': '₇', '8': '₈', '9': '₉',
    '+': '₊', '-': '₋', '=': '₌', '(': '₍', ')': '₎',
    'a': 'ₐ', 'e': 'ₑ', 'h': 'ₕ', 'i': 'ᵢ', 'j': 'ⱼ',
    'k': 'ₖ', 'l': 'ₗ', 'm': 'ₘ', 'n': 'ₙ', 'o': 'ₒ',
    'p': 'ₚ', 'r': 'ᵣ', 's': 'ₛ', 't': 'ₜ', 'u': 'ᵤ',
    'v': 'ᵥ', 'x': 'ₓ'
};

/**
 * 将 LaTeX/Markdown 公式转换为可读纯文本
 */
function normalizeMarkdownFormula(text) {
    if (!text) return '';
    text = String(text);
    
    // 1. 双反斜杠转单反斜杠
    text = text.replace(/\\\\/g, '\\');
    
    // 2. 移除 $ 符号
    text = text.replace(/\$\$(.*?)\$\$/gs, '$1');
    text = text.replace(/\$(.*?)\$/g, '$1');
    text = text.replace(/\\\((.*?)\\\)/gs, '$1');
    text = text.replace(/\\\[(.*?)\\\]/gs, '$1');
    
    // 3. 处理 \text 命令
    for (let i = 0; i < 5; i++) {
        const prev = text;
        text = text.replace(/\\text(?:rm|bf|it|sf|tt)?\s*\{([^{}]*)\}/g, '$1');
        text = text.replace(/\\mathrm\s*\{([^{}]*)\}/g, '$1');
        text = text.replace(/\\mathbf\s*\{([^{}]*)\}/g, '$1');
        if (text === prev) break;
    }
    
    // 4. 处理下标 _{...}
    for (let i = 0; i < 5; i++) {
        const prev = text;
        text = text.replace(/_\{([^{}]*)\}/g, (match, content) => {
            // 中文下标直接保留
            if (/[\u4e00-\u9fff]/.test(content)) return content;
            return content.split('').map(c => SUBSCRIPT_MAP[c] || c).join('');
        });
        if (text === prev) break;
    }
    // 单字符下标
    text = text.replace(/_([0-9a-zA-Z])/g, (m, c) => SUBSCRIPT_MAP[c] || c);
    text = text.replace(/_([\u4e00-\u9fff])/g, '$1');
    
    // 5. 处理上标 ^{...}
    for (let i = 0; i < 5; i++) {
        const prev = text;
        text = text.replace(/\^\{([^{}]*)\}/g, (match, content) => {
            return content.split('').map(c => SUPERSCRIPT_MAP[c] || c).join('');
        });
        if (text === prev) break;
    }
    // 单字符上标
    text = text.replace(/\^([0-9a-zA-Z+\-])/g, (m, c) => SUPERSCRIPT_MAP[c] || ('^' + c));
    
    // 6. 处理分数
    for (let i = 0; i < 5; i++) {
        const prev = text;
        text = text.replace(/\\(?:d|t|c)?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, '($1)/($2)');
        if (text === prev) break;
    }
    // 简化括号
    text = text.replace(/\(([a-zA-Z0-9α-ωΑ-Ω])\)\/\(([a-zA-Z0-9α-ωΑ-Ω])\)/g, '$1/$2');
    text = text.replace(/\(([a-zA-Z0-9α-ωΑ-Ω])\)\//g, '$1/');
    text = text.replace(/\/\(([a-zA-Z0-9α-ωΑ-Ω])\)/g, '/$1');
    
    // 7. 处理根号
    text = text.replace(/\\sqrt\s*\[([^\]]+)\]\s*\{([^{}]*)\}/g, (m, n, c) => {
        const prefix = {'2': '√', '3': '³√', '4': '⁴√', 'n': 'ⁿ√'}[n] || (n + '√');
        return prefix + c;
    });
    text = text.replace(/\\sqrt\s*\{([^{}]*)\}/g, '√$1');
    
    // 8. 替换希腊字母和运算符
    const allSymbols = {...GREEK_LETTERS, ...MATH_OPERATORS};
    Object.keys(allSymbols).sort((a, b) => b.length - a.length).forEach(latex => {
        text = text.split(latex).join(allSymbols[latex]);
    });
    
    // 9. 处理空格命令
    text = text.replace(/\\quad/g, '  ');
    text = text.replace(/\\qquad/g, '    ');
    text = text.replace(/\\[,;:\s!]/g, ' ');
    
    // 10. 移除剩余的 LaTeX 命令
    text = text.replace(/\\[a-zA-Z]+\s*(?:\[[^\]]*\])?\s*(?:\{[^{}]*\})?/g, '');
    
    // 11. 清理空白
    text = text.replace(/[ \t]+/g, ' ').trim();
    
    return text;
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    loadEvalSettings();
    // 首屏只加载必要数据：测试条件和任务列表
    // loadBookList 延迟到新建任务弹窗打开时加载
    Promise.all([
        loadTestConditions(),
        loadTaskList()
    ]).catch(e => console.error('初始化加载失败:', e));
});


// ========== 评估设置 ==========
function loadEvalSettings() {
    try {
        const saved = localStorage.getItem('batchEvalSettings');
        if (saved) {
            evalSettings = { ...evalSettings, ...JSON.parse(saved) };
        }
    } catch (e) {
        console.error('加载设置失败:', e);
    }
}

function saveEvalSettings() {
    try {
        localStorage.setItem('batchEvalSettings', JSON.stringify(evalSettings));
    } catch (e) {
        console.error('保存设置失败:', e);
    }
}

function showSettingsModal() {
    document.getElementById('settingsFuzzyThreshold').value = evalSettings.fuzzyThreshold;
    document.getElementById('settingsFuzzyThresholdValue').textContent = evalSettings.fuzzyThreshold + '%';
    document.getElementById('settingsIgnoreIndexPrefix').checked = evalSettings.ignoreIndexPrefix;
    document.getElementById('settingsModal').classList.add('show');
}

function hideSettingsModal() {
    document.getElementById('settingsModal').classList.remove('show');
}

function updateSettingsThresholdDisplay() {
    const val = document.getElementById('settingsFuzzyThreshold').value;
    document.getElementById('settingsFuzzyThresholdValue').textContent = val + '%';
}

function saveSettings() {
    evalSettings.fuzzyThreshold = parseInt(document.getElementById('settingsFuzzyThreshold').value);
    evalSettings.ignoreIndexPrefix = document.getElementById('settingsIgnoreIndexPrefix').checked;
    saveEvalSettings();
    hideSettingsModal();
    alert('设置已保存，重新评估时生效');
}

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
function showLoading(text, subtext = '') {
    document.getElementById('loadingText').textContent = text || '处理中...';
    const subtextEl = document.getElementById('loadingSubtext');
    if (subtextEl) {
        subtextEl.textContent = subtext;
        subtextEl.style.display = subtext ? 'block' : 'none';
    }
    // 重置进度条为不确定模式
    const progressBar = document.getElementById('loadingProgressBar');
    if (progressBar) {
        progressBar.classList.remove('determinate');
        progressBar.style.width = '40%';
    }
    document.getElementById('loadingOverlay').classList.add('show');
}

function updateLoadingProgress(percent, text, subtext) {
    const progressBar = document.getElementById('loadingProgressBar');
    if (progressBar) {
        progressBar.classList.add('determinate');
        progressBar.style.width = Math.min(100, Math.max(0, percent)) + '%';
    }
    if (text) {
        document.getElementById('loadingText').textContent = text;
    }
    const subtextEl = document.getElementById('loadingSubtext');
    if (subtextEl && subtext !== undefined) {
        subtextEl.textContent = subtext;
        subtextEl.style.display = subtext ? 'block' : 'none';
    }
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
    // 重置进度条
    const progressBar = document.getElementById('loadingProgressBar');
    if (progressBar) {
        progressBar.classList.remove('determinate');
        progressBar.style.width = '40%';
    }
    const subtextEl = document.getElementById('loadingSubtext');
    if (subtextEl) {
        subtextEl.textContent = '';
        subtextEl.style.display = 'none';
    }
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
    
    // 按日期分组
    const groupedTasks = groupTasksByDate(taskList);
    
    let html = '';
    for (const [dateKey, tasks] of Object.entries(groupedTasks)) {
        // 日期分隔线
        html += `<div class="date-divider"><span>${dateKey}</span></div>`;
        
        // 该日期下的任务
        html += tasks.map(task => {
            const subjectId = task.subject_id !== undefined ? task.subject_id : '';
            const timeOnly = formatTimeOnly(task.created_at);
            
            return `
                <div class="task-item ${selectedTask?.task_id === task.task_id ? 'selected' : ''}" 
                     data-subject="${subjectId}"
                     data-task-id="${task.task_id}"
                     onmouseenter="showTaskTooltip(event, '${task.task_id}')"
                     onmouseleave="hideTaskTooltip()">
                    <div class="task-item-content" onclick="selectTask('${task.task_id}')">
                        <div class="task-item-header">
                            <div class="task-item-title">
                                <span class="task-item-title-text">${escapeHtml(task.name)}</span>
                                <span class="task-item-status status-${task.status}">${getStatusText(task.status)}</span>
                            </div>
                            <span class="task-item-time">${timeOnly}</span>
                        </div>
                        <div class="task-item-meta">
                            ${task.homework_count || 0} 个作业 | 
                            ${task.test_condition_name ? task.test_condition_name + ' | ' : ''}
                            ${task.status === 'completed' ? `准确率: ${(task.overall_accuracy * 100).toFixed(1)}%` : ''}
                        </div>
                    </div>
                </div>
            `;
        }).join('');
    }
    
    container.innerHTML = html;
}

// 按日期分组任务
function groupTasksByDate(tasks) {
    const groups = {};
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    
    tasks.forEach(task => {
        const taskDate = new Date(task.created_at);
        taskDate.setHours(0, 0, 0, 0);
        
        // 计算日期差
        const diffDays = Math.floor((today - taskDate) / (1000 * 60 * 60 * 24));
        
        let dateKey;
        if (diffDays === 0) {
            dateKey = '今天';
        } else if (diffDays === 1) {
            dateKey = '昨天';
        } else {
            // 格式: M/DD
            dateKey = `${taskDate.getMonth() + 1}/${String(taskDate.getDate()).padStart(2, '0')}`;
        }
        
        if (!groups[dateKey]) {
            groups[dateKey] = [];
        }
        groups[dateKey].push(task);
    });
    
    return groups;
}

// 只返回时间部分 (HH:mm)
function formatTimeOnly(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    return date.toLocaleTimeString('zh-CN', {
        hour: '2-digit',
        minute: '2-digit',
        hour12: false
    });
}

function getStatusText(status) {
    const map = {
        'pending': '待评估',
        'running': '评估中',
        'completed': '已完成'
    };
    return map[status] || status;
}

async function selectTask(taskId, fullMode = false) {
    showLoading('加载任务详情...', '正在获取数据');
    
    // 模拟进度动画
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 15;
        if (progress > 90) progress = 90;
        updateLoadingProgress(progress, '加载任务详情...', '正在获取数据');
    }, 100);
    
    try {
        // 默认使用精简模式加载，加快速度
        const slim = fullMode ? '0' : '1';
        const res = await fetch(`/api/batch/tasks/${taskId}?slim=${slim}`);
        
        updateLoadingProgress(95, '加载任务详情...', '解析数据中');
        const data = await res.json();
        
        if (data.success) {
            updateLoadingProgress(100, '加载完成', '');
            selectedTask = data.data;
            renderTaskList();
            renderTaskDetail();
        }
    } catch (e) {
        alert('加载任务详情失败: ' + e.message);
    }
    
    clearInterval(progressInterval);
    setTimeout(hideLoading, 150);
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
    
    // 显示已应用的合集
    updateTaskCollectionDisplay(selectedTask);
    
    // 显示备注
    const remarkRow = document.getElementById('taskRemarkRow');
    const remarkText = document.getElementById('taskRemarkText');
    if (remarkRow && remarkText) {
        remarkRow.style.display = 'flex';
        remarkText.textContent = selectedTask.remark || '';
    }
    
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
    document.getElementById('viewAnalysisBtn').disabled = !isCompleted;
    
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
    
    // 英语作文评分展示（仅当有作文数据时显示）
    if (selectedTask.essay_data && selectedTask.essay_data.has_essay) {
        renderEssayScores(selectedTask.essay_data);
    } else {
        const essaySection = document.getElementById('essayScoreSection');
        if (essaySection) essaySection.style.display = 'none';
    }
    
    // 作业列表
    renderHomeworkList(selectedTask.homework_items || []);
    
    // AI报告 - 如果有缓存报告，显示简要信息和查看按钮
    if (selectedTask.overall_report?.ai_analysis) {
        document.getElementById('aiReport').style.display = 'block';
        const report = selectedTask.overall_report.ai_analysis;
        const overview = report.overview || {};
        const scores = report.capability_scores || {};
        const generatedAt = report.generated_at || '';
        
        document.getElementById('aiReportContent').innerHTML = `
            <div class="ai-report-summary">
                <div class="summary-stats">
                    <span>准确率 <strong>${overview.pass_rate || 0}%</strong></span>
                    <span class="divider">|</span>
                    <span>综合评分 <strong>${scores.overall || 0}</strong></span>
                    <span class="divider">|</span>
                    <span>错误 <strong>${overview.failed || 0}</strong> 题</span>
                </div>
                <div class="summary-actions">
                    ${generatedAt ? `<span class="summary-time">生成于 ${generatedAt}</span>` : ''}
                    <button class="btn btn-small btn-primary" onclick="generateAIReport()">查看完整报告</button>
                </div>
            </div>
        `;
    } else {
        document.getElementById('aiReport').style.display = 'none';
    }
}

// ========== 渲染测试条件信息 ==========
function renderTestConditionsInfo() {
    const container = document.getElementById('testConditionsInfo');
    if (!container || !selectedTask) {
        if (container) container.style.display = 'none';
        return;
    }
    
    const testConditionName = selectedTask.test_condition_name || '';
    const subjectName = selectedTask.subject_name || '';
    const homeworkItems = selectedTask.homework_items || [];
    
    // 统计学生数和作业数
    const studentIds = new Set();
    homeworkItems.forEach(item => {
        if (item.student_id) {
            studentIds.add(item.student_id);
        }
    });
    const studentCount = studentIds.size;
    const homeworkCount = homeworkItems.length;
    const avgHomework = studentCount > 0 ? (homeworkCount / studentCount).toFixed(1) : 0;
    
    // 构建显示内容
    let infoItems = [];
    
    if (testConditionName) {
        infoItems.push(`<span class="condition-tag">${escapeHtml(testConditionName)}</span>`);
    }
    if (subjectName) {
        infoItems.push(`<span class="info-item">${escapeHtml(subjectName)}</span>`);
    }
    if (studentCount > 0) {
        infoItems.push(`<span class="info-item"><strong>${studentCount}</strong> 个学生</span>`);
        infoItems.push(`<span class="info-item">每人 <strong>${avgHomework}</strong> 份作业</span>`);
    }
    
    if (infoItems.length > 0) {
        container.innerHTML = `
            <div class="conditions-row">
                <span class="conditions-label">测试条件:</span>
                ${infoItems.join('<span class="info-divider">|</span>')}
            </div>
        `;
        container.style.display = 'block';
    } else {
        container.style.display = 'none';
    }
}


function renderOverallReport(report) {
    document.getElementById('overallReport').style.display = 'block';
    
    // 渲染测试条件信息
    renderTestConditionsInfo();
    
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
    
    // 题目类型分类统计 (选择题、客观填空题、主观题)
    let detailHtml = '';
    const byType = report.by_question_type || {};
    const byCombined = report.by_combined || {};
    
    if (Object.keys(byType).length > 0) {
        const choice = byType.choice || {};
        const objectiveFill = byType.objective_fill || {};
        const subjective = byType.subjective || {};
        
        detailHtml += `
            <div class="list-header">题目类型分类统计</div>
            <div class="type-stats-grid" style="display: flex; gap: 16px; flex-wrap: wrap;">
                <div class="type-stats-section" style="flex: 1; min-width: 280px;">
                    <table class="stats-table type-clickable-table">
                        <thead><tr><th>类型</th><th>总数</th><th>正确</th><th>准确率</th></tr></thead>
                        <tbody>
                            <tr class="clickable-row" onclick="showTypeDetail('choice')" title="点击查看详情">
                                <td>选择题</td>
                                <td>${choice.total || 0}</td>
                                <td>${choice.correct || 0}</td>
                                <td>${choice.total > 0 ? ((choice.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                            <tr class="clickable-row" onclick="showTypeDetail('objective_fill')" title="点击查看详情">
                                <td>客观填空题</td>
                                <td>${objectiveFill.total || 0}</td>
                                <td>${objectiveFill.correct || 0}</td>
                                <td>${objectiveFill.total > 0 ? ((objectiveFill.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
                            </tr>
                            <tr class="clickable-row" onclick="showTypeDetail('subjective')" title="点击查看详情">
                                <td>主观题</td>
                                <td>${subjective.total || 0}</td>
                                <td>${subjective.correct || 0}</td>
                                <td>${subjective.total > 0 ? ((subjective.accuracy || 0) * 100).toFixed(1) + '%' : '-'}</td>
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
    recognitionPie: null,
    gradingPie: null
};

// ========== 销毁图表 ==========
function destroyBatchCharts() {
    Object.values(batchChartInstances).forEach(chart => {
        if (chart) chart.destroy();
    });
    batchChartInstances = { errorTypePie: null, typeBar: null, errorTrend: null, recognitionPie: null, gradingPie: null };
}

// ========== 渲染总体报告图表 ==========
function renderOverallCharts(report) {
    // 检查 Chart.js 是否已加载
    if (typeof Chart === 'undefined') {
        // Chart.js 尚未加载，延迟重试
        setTimeout(() => renderOverallCharts(report), 100);
        return;
    }
    
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
            '识别题干-判断正确': '#06b6d4',
            '识别差异-判断正确': '#14b8a6',  // 新增：语文主观题模糊匹配
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
                onClick: (event, elements) => {
                    if (elements.length > 0) {
                        const index = elements[0].index;
                        const errorType = errorLabels[index];
                        showErrorTypeDetail(errorType);
                    }
                },
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
                                return `${context.label}: ${value}题 (${percentage}%) - 点击查看详情`;
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
    
    // 2. 题型准确率对比柱状图 (选择题、客观填空题、主观题)
    const byType = report.by_question_type || {};
    const choice = byType.choice || {};
    const objectiveFill = byType.objective_fill || {};
    const subjective = byType.subjective || {};
    
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
    if (subjective.total > 0) {
        typeLabels.push('主观题');
        typeData.push((subjective.accuracy || 0) * 100);
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
    
    console.log('homeworkItems count:', homeworkItems.length);
    console.log('completedItems count:', completedItems.length);
    if (completedItems.length > 0) {
        console.log('First completedItem:', completedItems[0]);
    }
    
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
                { key: '识别题干-判断正确', color: '#06b6d4' },
                { key: '识别差异-判断正确', color: '#14b8a6' },  // 语文主观题模糊匹配
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
    
    // 4. 准确率分析进度条
    console.log('Before calculateAccuracyStats - completedItems:', completedItems.length);
    if (completedItems.length > 0) {
        console.log('First item for accuracy:', JSON.stringify({
            status: completedItems[0].status,
            hasEvaluation: !!completedItems[0].evaluation,
            total_questions: completedItems[0].evaluation?.total_questions,
            error_distribution: completedItems[0].evaluation?.error_distribution
        }));
    }
    const accuracyStats = calculateAccuracyStats(completedItems);
    console.log('Accuracy stats:', accuracyStats);
    
    // 渲染识别准确率进度条
    const recTotal = accuracyStats.totalQuestions || 0;
    const recCorrect = accuracyStats.recognitionCorrect || 0;
    const recRate = accuracyStats.recognitionRate || 0;
    
    const recRateEl = document.getElementById('recognitionRateValue');
    const recFillEl = document.getElementById('recognitionProgressFill');
    const recStatsEl = document.getElementById('recognitionStats');
    
    if (recRateEl) recRateEl.textContent = recTotal > 0 ? recRate.toFixed(1) + '%' : '-';
    if (recFillEl) recFillEl.style.width = recTotal > 0 ? recRate + '%' : '0%';
    if (recStatsEl) recStatsEl.textContent = `正确 ${recCorrect} / 总计 ${recTotal}`;
    
    // 渲染批改准确率进度条
    const gradCorrect = accuracyStats.gradingCorrect || 0;
    const gradRate = accuracyStats.gradingRate || 0;
    
    const gradRateEl = document.getElementById('gradingRateValue');
    const gradFillEl = document.getElementById('gradingProgressFill');
    const gradStatsEl = document.getElementById('gradingStats');
    
    if (gradRateEl) gradRateEl.textContent = recTotal > 0 ? gradRate.toFixed(1) + '%' : '-';
    if (gradFillEl) gradFillEl.style.width = recTotal > 0 ? gradRate + '%' : '0%';
    if (gradStatsEl) gradStatsEl.textContent = `正确 ${gradCorrect} / 总计 ${recTotal}`;
}

// 旧的 showAccuracyDetail 函数已移除，使用新版本（在文件后面定义）

// ========== 计算识别准确率和批改准确率 ==========
// 简化版：直接使用后端计算的 correct_count 和 error_distribution
function calculateAccuracyStats(completedItems) {
    let totalQuestions = 0;
    let recognitionCorrect = 0;
    let gradingCorrect = 0;
    
    // 收集详情数据 - 遍历每道题的 errors 数组
    window.accuracyDetails = { recognition: { correct: [], wrong: [] }, grading: { correct: [], wrong: [] } };
    
    // 识别错误类型列表
    const recognitionErrorTypes = ['识别错误-判断正确', '识别错误-判断错误', '识别题干-判断正确', 
                                   '识别差异-判断正确', '缺失题目', 'AI识别幻觉', '答案不匹配'];
    // 批改错误类型列表
    const gradingErrorTypes = ['识别错误-判断错误', '识别正确-判断错误', '缺失题目', 'AI识别幻觉', '答案不匹配'];
    
    completedItems.forEach((item, idx) => {
        const evaluation = item.evaluation || {};
        const total = evaluation.total_questions || 0;
        const correctCount = evaluation.correct_count || 0;
        const errorDist = evaluation.error_distribution || {};
        const errors = evaluation.errors || [];
        const pageNum = item.page_num || '?';
        
        // 调试：打印第一个item的详细信息
        if (idx === 0) {
            console.log('First item evaluation:', evaluation);
            console.log('error_distribution:', errorDist);
            console.log('total_questions:', total, 'correct_count:', correctCount);
            console.log('errors array:', errors);
        }
        
        totalQuestions += total;
        
        // 收集错误题目详情
        const errorIndexSet = new Set(); // 记录有错误的题号
        errors.forEach(err => {
            const errorType = err.error_type || '';
            
            // 兼容两种数据格式：
            // 格式1: base_effect/ai_result 对象 (语文等学科)
            // 格式2: base_answer/base_user/hw_user 字段 (其他学科)
            let baseAnswer = '-';
            let baseUser = '-';
            let hwUser = '-';
            let baseCorrect = '-';
            let aiCorrect = '-';
            
            if (err.base_effect) {
                // 格式1: 使用 base_effect 和 ai_result
                baseAnswer = err.base_effect.answer || '-';
                baseUser = err.base_effect.userAnswer || '-';
                baseCorrect = err.base_effect.correct || '-';
                hwUser = err.ai_result?.userAnswer || '-';
                aiCorrect = err.ai_result?.correct || '-';
            } else {
                // 格式2: 直接使用字段
                baseAnswer = err.base_answer || '-';
                baseUser = err.base_user || '-';
                hwUser = err.hw_user || '-';
            }
            
            const questionInfo = {
                pageNum: pageNum,
                index: err.index || '-',
                errorType: errorType,
                baseAnswer: baseAnswer,
                baseUser: baseUser,
                hwUser: hwUser,
                baseCorrect: baseCorrect,
                aiCorrect: aiCorrect,
                explanation: err.explanation || '',
                reason: errorType
            };
            
            errorIndexSet.add(err.index);
            
            // 识别错误
            if (recognitionErrorTypes.includes(errorType)) {
                window.accuracyDetails.recognition.wrong.push(questionInfo);
            }
            // 批改错误
            if (gradingErrorTypes.includes(errorType)) {
                window.accuracyDetails.grading.wrong.push(questionInfo);
            }
        });
        
        // 计算正确题目数量并收集正确题目详情
        // 正确题目 = 总题数 - 错误题数
        const correctQuestions = total - errors.length;
        
        // 尝试从 homework_result 解析正确的题目
        let hwResult = [];
        try {
            if (item.homework_result) {
                hwResult = typeof item.homework_result === 'string' ? 
                    JSON.parse(item.homework_result) : item.homework_result;
            }
        } catch (e) {
            hwResult = [];
        }
        
        // 遍历作业结果，找出正确的题目
        hwResult.forEach(q => {
            const qIndex = q.index || q.tempIndex;
            // 如果这道题不在错误列表中，说明是正确的
            if (!errorIndexSet.has(qIndex) && !errorIndexSet.has(String(qIndex))) {
                const correctInfo = {
                    pageNum: pageNum,
                    index: qIndex || '-',
                    errorType: '正确',
                    baseAnswer: q.answer || q.mainAnswer || '-',
                    baseUser: q.userAnswer || '-',
                    hwUser: q.userAnswer || '-',
                    reason: '完全匹配'
                };
                window.accuracyDetails.recognition.correct.push(correctInfo);
                window.accuracyDetails.grading.correct.push(correctInfo);
            }
        });
        
        // 如果没有 error_distribution，使用 correct_count 作为备选
        if (Object.keys(errorDist).length === 0) {
            // 没有错误分布数据，直接用 correct_count
            recognitionCorrect += correctCount;
            gradingCorrect += correctCount;
        } else {
            // 识别正确 = 总数 - 识别错误类型的数量
            const recErrors = (errorDist['识别错误-判断正确'] || 0) + 
                              (errorDist['识别错误-判断错误'] || 0) + 
                              (errorDist['识别题干-判断正确'] || 0) +
                              (errorDist['识别差异-判断正确'] || 0) +
                              (errorDist['缺失题目'] || 0) + 
                              (errorDist['AI识别幻觉'] || 0) +
                              (errorDist['答案不匹配'] || 0);
            recognitionCorrect += (total - recErrors);
            
            // 批改正确 = 总数 - 批改错误类型的数量
            const gradErrors = (errorDist['识别错误-判断错误'] || 0) + 
                               (errorDist['识别正确-判断错误'] || 0) + 
                               (errorDist['缺失题目'] || 0) + 
                               (errorDist['AI识别幻觉'] || 0) +
                               (errorDist['答案不匹配'] || 0);
            gradingCorrect += (total - gradErrors);
        }
    });
    
    console.log('Final stats:', { totalQuestions, recognitionCorrect, gradingCorrect });
    console.log('accuracyDetails:', window.accuracyDetails);
    
    // 保存计算结果到全局变量，供弹窗使用
    const stats = {
        totalQuestions,
        recognitionCorrect: Math.max(0, recognitionCorrect),
        recognitionWrong: Math.max(0, totalQuestions - recognitionCorrect),
        recognitionRate: totalQuestions > 0 ? (recognitionCorrect / totalQuestions) * 100 : 0,
        gradingCorrect: Math.max(0, gradingCorrect),
        gradingWrong: Math.max(0, totalQuestions - gradingCorrect),
        gradingRate: totalQuestions > 0 ? (gradingCorrect / totalQuestions) * 100 : 0
    };
    window.accuracyStats = stats;
    
    return stats;
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
        '识别题干-判断正确': 0,
        '识别差异-判断正确': 0,  // 语文主观题模糊匹配
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

// ========== 英语作文评分图表实例 ==========
let essayChartInstance = null;

// ========== 渲染英语作文评分 ==========
function renderEssayScores(essayData) {
    let section = document.getElementById('essayScoreSection');
    
    // 如果section不存在，动态创建
    if (!section) {
        const overallReport = document.getElementById('overallReport');
        if (overallReport) {
            section = document.createElement('div');
            section.id = 'essayScoreSection';
            section.className = 'section';
            section.style.marginTop = '16px';
            overallReport.parentNode.insertBefore(section, overallReport.nextSibling);
        } else {
            return;
        }
    }
    
    if (!essayData || !essayData.has_essay) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    const stats = essayData.stats || {};
    const essays = essayData.essays || [];
    
    // 计算标准差
    const scores = essays.map(e => e.score);
    const avg = stats.avg_score || 0;
    const variance = scores.length > 0 ? scores.reduce((sum, s) => sum + Math.pow(s - avg, 2), 0) / scores.length : 0;
    const stdDev = Math.sqrt(variance).toFixed(2);
    
    // 构建HTML - 简洁布局
    let html = `
        <div class="section-header" style="margin-bottom: 12px;">
            <h3 class="section-title" style="font-size: 15px; margin: 0;">英语作文评分统计</h3>
        </div>
        <div style="display: flex; gap: 16px; margin-bottom: 16px;">
            <div class="stats-grid" style="grid-template-columns: repeat(5, 1fr); gap: 8px; flex: 1;">
                <div class="stat-card highlight" style="padding: 12px;">
                    <div class="stat-value" style="font-size: 20px;">${stats.avg_score || 0}</div>
                    <div class="stat-label" style="font-size: 11px;">平均分</div>
                </div>
                <div class="stat-card" style="padding: 12px;">
                    <div class="stat-value" style="font-size: 20px;">${stats.max_score || 0}</div>
                    <div class="stat-label" style="font-size: 11px;">最高分</div>
                </div>
                <div class="stat-card" style="padding: 12px;">
                    <div class="stat-value" style="font-size: 20px;">${stats.min_score || 0}</div>
                    <div class="stat-label" style="font-size: 11px;">最低分</div>
                </div>
                <div class="stat-card" style="padding: 12px;">
                    <div class="stat-value" style="font-size: 20px;">${stdDev}</div>
                    <div class="stat-label" style="font-size: 11px;">标准差</div>
                </div>
                <div class="stat-card" style="padding: 12px;">
                    <div class="stat-value" style="font-size: 20px;">${essays.length}</div>
                    <div class="stat-label" style="font-size: 11px;">作文数</div>
                </div>
            </div>
        </div>
        <div style="background: #f9f9fb; border-radius: 8px; padding: 12px; margin-bottom: 16px;">
            <div style="font-size: 13px; font-weight: 500; color: #1d1d1f; margin-bottom: 8px;">得分分布</div>
            <canvas id="essayScoreChart" height="120"></canvas>
        </div>
        <div class="list-header" style="font-size: 14px;">作文详情列表 (${essays.length}篇)</div>
        <div class="essay-list" style="max-height: 300px; overflow-y: auto;">
            ${essays.map((essay, idx) => `
                <div class="essay-item">
                    <div class="essay-header">
                        <div class="essay-student">${essay.student_name || '学生' + (idx + 1)}</div>
                        <div class="essay-score" style="color: ${getScoreColor(essay.score)};">${essay.score}分</div>
                    </div>
                    <div class="essay-content">
                        <div class="essay-eval"><span class="essay-label">综合评价：</span>${escapeHtml(essay.evaluation || '-')}</div>
                        <div class="essay-suggest"><span class="essay-label">改进建议：</span>${escapeHtml(essay.suggestions || '-')}</div>
                    </div>
                    <div class="essay-toggle">
                        <button class="btn btn-secondary" style="padding: 4px 8px; font-size: 11px;" onclick="toggleEssayRaw(this)">查看原文</button>
                        <div class="essay-raw">${escapeHtml(essay.raw || '')}</div>
                    </div>
                </div>
            `).join('')}
        </div>
    `;
    
    section.innerHTML = html;
    
    // 渲染得分分布图表
    renderEssayScoreChart(essays);
}

// 获取分数对应的颜色
function getScoreColor(score) {
    if (score >= 12) return '#1e7e34';
    if (score >= 9) return '#1565c0';
    if (score >= 6) return '#e65100';
    return '#d73a49';
}

// 切换显示原文
function toggleEssayRaw(btn) {
    const rawDiv = btn.nextElementSibling;
    if (rawDiv.style.display === 'none') {
        rawDiv.style.display = 'block';
        btn.textContent = '收起原文';
    } else {
        rawDiv.style.display = 'none';
        btn.textContent = '查看原文';
    }
}

// 渲染得分分布图表 - 只显示有数据的分数
function renderEssayScoreChart(essays) {
    const scoreCanvas = document.getElementById('essayScoreChart');
    if (!scoreCanvas) return;
    
    // 销毁旧图表
    if (essayChartInstance) { essayChartInstance.destroy(); essayChartInstance = null; }
    
    const scores = essays.map(e => e.score);
    const total = scores.length;
    
    // 统计每个分数的数量（精确到0.5分）
    const buckets = {};
    scores.forEach(s => {
        const key = s.toFixed(1);
        buckets[key] = (buckets[key] || 0) + 1;
    });
    
    // 只保留有数据的分数，按分数排序
    const sortedKeys = Object.keys(buckets).sort((a, b) => parseFloat(a) - parseFloat(b));
    const labels = sortedKeys;
    const data = sortedKeys.map(k => buckets[k]);
    
    if (labels.length === 0) return;
    
    // 找出众数（标准分数）- 最多人得分的分数
    let modeScore = sortedKeys[0];
    let maxCount = 0;
    sortedKeys.forEach(k => {
        if (buckets[k] > maxCount) {
            maxCount = buckets[k];
            modeScore = k;
        }
    });
    const modeScoreValue = parseFloat(modeScore);
    
    // 计算累积分布：低于各分数的学生比例
    let cumulative = 0;
    const cumulativeData = sortedKeys.map(k => {
        // 低于当前分数的比例（不含当前分数）
        const ratio = (cumulative / total) * 100;
        cumulative += buckets[k];
        return ratio.toFixed(1);
    });
    
    // 根据分数设置颜色
    const colors = labels.map(k => {
        const s = parseFloat(k);
        if (s >= 12) return '#10b981';
        if (s >= 9) return '#3b82f6';
        if (s >= 6) return '#f59e0b';
        return '#ef4444';
    });
    
    // 标准分数点用橙色，其他用紫色
    const pointColors = labels.map(k => k === modeScore ? '#f59e0b' : '#8b5cf6');
    const pointRadius = labels.map(k => k === modeScore ? 8 : 4);
    
    essayChartInstance = new Chart(scoreCanvas, {
        type: 'bar',
        data: {
            labels: labels.map(l => l === modeScore ? l + '分(标准)' : l + '分'),
            datasets: [
                { 
                    type: 'bar',
                    label: '人数',
                    data: data, 
                    backgroundColor: colors, 
                    borderRadius: 4,
                    yAxisID: 'y',
                    order: 2  // 柱状图在下层
                },
                {
                    type: 'line',
                    label: '低于该分数比例',
                    data: cumulativeData,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    pointRadius: pointRadius,
                    pointBackgroundColor: pointColors,
                    pointBorderColor: pointColors,
                    fill: false,
                    tension: 0.3,
                    yAxisID: 'y1',
                    order: 1  // 折线图在上层
                }
            ]
        },
        options: {
            responsive: true,
            interaction: { mode: 'index', intersect: false },
            plugins: { 
                legend: { 
                    display: true, 
                    position: 'bottom',
                    labels: { font: { size: 11 }, color: '#1d1d1f', boxWidth: 12 }
                },
                tooltip: {
                    callbacks: {
                        afterBody: function(context) {
                            const idx = context[0].dataIndex;
                            const score = sortedKeys[idx];
                            if (score === modeScore) {
                                return '(标准分数 - 最多人得分)';
                            }
                            return '';
                        }
                    }
                }
            },
            scales: { 
                y: { 
                    beginAtZero: true, 
                    ticks: { stepSize: 1 },
                    title: { display: true, text: '人数', font: { size: 11 }, color: '#666' }
                },
                y1: {
                    position: 'right',
                    beginAtZero: true,
                    max: 100,
                    ticks: { callback: v => v + '%' },
                    title: { display: true, text: '低于该分数比例', font: { size: 11 }, color: '#8b5cf6' },
                    grid: { drawOnChartArea: false }
                }
            }
        }
    });
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
        
        // 处理图片路径
        const picPath = item.pic_path || '';
        const hasImage = picPath && picPath.length > 0;
        
        // 数据集名称徽章
        let datasetBadge = '';
        if (item.matched_dataset) {
            const datasetName = item.matched_dataset_name || item.matched_dataset;
            datasetBadge = `<span class="dataset-name-badge" title="${escapeHtml(datasetName)}">${escapeHtml(datasetName)}</span>`;
        } else {
            datasetBadge = '<span class="no-dataset-badge">无数据集</span>';
        }
        
        return `
            <div class="homework-item" data-homework-id="${item.homework_id}">
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
                    <div class="homework-item-dataset">
                        ${datasetBadge}
                        <button class="btn-select-dataset" onclick="event.stopPropagation(); showDatasetSelector('${item.homework_id}')" title="选择数据集">
                            选择数据集
                        </button>
                    </div>
                </div>
                <div class="homework-item-actions">
                    ${hasImage ? `<button class="btn btn-small btn-view" onclick="event.stopPropagation(); viewHomeworkImage('${escapeHtml(picPath)}', '${escapeHtml(item.student_name || item.student_id || '-')}')" title="查看作业图片">查看</button>` : ''}
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

// 查看作业图片 - 非模态浮动窗口
function viewHomeworkImage(picPath, studentName) {
    // 创建或获取图片浮窗
    let floatWin = document.getElementById('homeworkImageFloat');
    if (!floatWin) {
        floatWin = document.createElement('div');
        floatWin.id = 'homeworkImageFloat';
        floatWin.className = 'homework-image-float';
        floatWin.innerHTML = `
            <div class="float-header" onmousedown="startDragFloat(event)">
                <span id="imageFloatTitle">作业图片</span>
                <button class="float-close" onclick="closeImageFloat()">&times;</button>
            </div>
            <div class="float-body">
                <img id="homeworkImageView" src="" alt="作业图片" />
            </div>
        `;
        document.body.appendChild(floatWin);
    }
    
    // 设置标题和图片
    document.getElementById('imageFloatTitle').textContent = `${studentName} 的作业`;
    const imgEl = document.getElementById('homeworkImageView');
    imgEl.src = picPath;
    imgEl.onerror = function() {
        this.src = '';
        this.alt = '图片加载失败';
        this.style.display = 'none';
        this.parentElement.innerHTML = '<div style="padding: 40px; text-align: center; color: #86868b;">图片加载失败</div>';
    };
    imgEl.style.display = 'block';
    
    floatWin.style.display = 'block';
}

function closeImageFloat() {
    const floatWin = document.getElementById('homeworkImageFloat');
    if (floatWin) floatWin.style.display = 'none';
}

// 拖拽浮窗
let isDragging = false;
let dragOffsetX = 0, dragOffsetY = 0;

function startDragFloat(e) {
    const floatWin = document.getElementById('homeworkImageFloat');
    isDragging = true;
    dragOffsetX = e.clientX - floatWin.offsetLeft;
    dragOffsetY = e.clientY - floatWin.offsetTop;
    document.addEventListener('mousemove', dragFloat);
    document.addEventListener('mouseup', stopDragFloat);
}

function dragFloat(e) {
    if (!isDragging) return;
    const floatWin = document.getElementById('homeworkImageFloat');
    floatWin.style.left = (e.clientX - dragOffsetX) + 'px';
    floatWin.style.top = (e.clientY - dragOffsetY) + 'px';
}

function stopDragFloat() {
    isDragging = false;
    document.removeEventListener('mousemove', dragFloat);
    document.removeEventListener('mouseup', stopDragFloat);
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
    selectedHwTaskIds.clear(); // 清空作业任务选择
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
    
    // 语文学科显示模糊匹配阈值配置
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const fuzzyGroup = document.getElementById('fuzzyThresholdGroup');
    if (fuzzyGroup) {
        fuzzyGroup.style.display = subjectId === '1' ? 'block' : 'none';
    }
}

// 更新阈值显示
function updateThresholdDisplay() {
    const input = document.getElementById('fuzzyThresholdInput');
    const display = document.getElementById('fuzzyThresholdValue');
    if (input && display) {
        display.textContent = input.value + '%';
    }
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
    
    // 显示加载状态
    const container = document.getElementById('hwTaskList');
    container.innerHTML = '<div class="task-loading">加载中...</div>';
    
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
        container.innerHTML = '<div class="task-loading error">加载失败</div>';
    }
}

// ========== 渲染作业任务列表 ==========
function renderHwTaskList() {
    const container = document.getElementById('hwTaskList');
    
    let html = `
        <div class="task-item ${selectedHwTaskIds.size === 0 ? 'active' : ''}" data-task-id="" onclick="toggleHomeworkTaskSelection(this, '')">
            <input type="checkbox" class="task-checkbox" ${selectedHwTaskIds.size === 0 ? 'checked' : ''} onclick="event.stopPropagation(); toggleHomeworkTaskSelection(this.parentElement, '')">
            <span class="task-name">全部作业</span>
        </div>
    `;
    
    if (hwTaskList.length > 0) {
        html += hwTaskList.map(task => {
            const taskId = String(task.hw_publish_id);
            const isSelected = selectedHwTaskIds.has(taskId);
            return `
            <div class="task-item ${isSelected ? 'active' : ''}" 
                 data-task-id="${taskId}" 
                 data-student-count="${task.student_count || 0}"
                 data-homework-count="${task.homework_count || 0}"
                 data-avg-homework="${task.avg_homework_per_student || 0}"
                 onclick="toggleHomeworkTaskSelection(this, '${taskId}')">
                <input type="checkbox" class="task-checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleHomeworkTaskSelection(this.parentElement, '${taskId}')">
                <span class="task-name">${escapeHtml(task.task_name || '未命名任务')}</span>
                <span class="task-count">${task.student_count || 0}人/${task.homework_count || 0}份</span>
            </div>
        `}).join('');
    }
    
    container.innerHTML = html;
    
    // 更新统计信息
    updateTaskStatsInfo();
}

// ========== 切换作业任务选择（多选） ==========
function toggleHomeworkTaskSelection(element, taskId) {
    const id = String(taskId);
    
    if (id === '') {
        // 选择"全部作业"时，清空其他选择
        selectedHwTaskIds.clear();
    } else {
        // 选择具体任务时
        if (selectedHwTaskIds.has(id)) {
            selectedHwTaskIds.delete(id);
        } else {
            selectedHwTaskIds.add(id);
        }
    }
    
    // 重新渲染列表
    renderHwTaskList();
    
    // 重新加载作业列表
    loadHomeworkForTask();
}

// ========== 更新任务统计信息 ==========
function updateTaskStatsInfo() {
    const container = document.getElementById('taskStatsInfo');
    if (!container) return;
    
    if (selectedHwTaskIds.size === 0) {
        container.innerHTML = '';
        container.style.display = 'none';
        return;
    }
    
    // 计算选中任务的统计信息
    let totalStudents = 0;
    let totalHomework = 0;
    
    selectedHwTaskIds.forEach(taskId => {
        const taskItem = document.querySelector(`#hwTaskList .task-item[data-task-id="${taskId}"]`);
        if (taskItem) {
            totalStudents += parseInt(taskItem.dataset.studentCount) || 0;
            totalHomework += parseInt(taskItem.dataset.homeworkCount) || 0;
        }
    });
    
    const avgHomework = totalStudents > 0 ? (totalHomework / totalStudents).toFixed(1) : 0;
    
    container.innerHTML = `
        <div class="task-stats-info">
            <span class="stats-item">已选 <strong>${selectedHwTaskIds.size}</strong> 个任务</span>
            <span class="stats-divider">|</span>
            <span class="stats-item"><strong>${totalStudents}</strong> 个学生</span>
            <span class="stats-divider">|</span>
            <span class="stats-item">共 <strong>${totalHomework}</strong> 份作业</span>
        </div>
    `;
    container.style.display = 'block';
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
    selectedHwTaskIds.clear();
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}

// ========== 时间筛选变化 ==========
function onTimeFilterChange() {
    selectedHwTaskIds.clear();
    loadHomeworkTasksForFilter();
    loadHomeworkForTask();
}

async function loadHomeworkForTask() {
    const subjectId = document.getElementById('hwSubjectFilter').value;
    const hours = document.getElementById('hwTimeFilter').value;
    
    const container = document.getElementById('homeworkSelectList');
    container.innerHTML = '<div class="empty-state"><div class="loading-spinner"></div><div class="empty-state-text">加载中...</div></div>';
    isLoadingHomework = true;
    
    try {
        let url = `/api/batch/homework?hours=${hours}`;
        if (subjectId) url += `&subject_id=${subjectId}`;
        
        // 支持多个作业任务ID
        if (selectedHwTaskIds.size > 0) {
            const taskIds = Array.from(selectedHwTaskIds).join(',');
            url += `&hw_publish_ids=${taskIds}`;
            console.log('[loadHomeworkForTask] 筛选作业任务IDs:', taskIds);
        } else {
            console.log('[loadHomeworkForTask] 加载全部作业');
        }
        
        console.log('[loadHomeworkForTask] 请求URL:', url);
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success) {
            homeworkForTask = data.data || [];
            console.log('[loadHomeworkForTask] 返回作业数量:', homeworkForTask.length);
            renderHomeworkSelectList();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
    isLoadingHomework = false;
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
    const collectionId = document.getElementById('taskCollectionSelect')?.value || '';
    
    // 验证必须选择学科
    if (!subjectId) {
        alert('请先选择学科');
        return;
    }
    
    if (selectedHomeworkIds.size === 0) {
        alert('请至少选择一个作业');
        return;
    }
    
    // 获取模糊匹配阈值（仅语文学科）
    let fuzzyThreshold = 0.85;
    if (subjectId === '1') {
        const thresholdInput = document.getElementById('fuzzyThresholdInput');
        if (thresholdInput) {
            fuzzyThreshold = parseInt(thresholdInput.value) / 100;
        }
    }
    
    showLoading('创建任务中...', `共 ${selectedHomeworkIds.size} 份作业`);
    
    // 模拟进度动画
    let progress = 0;
    const progressInterval = setInterval(() => {
        progress += Math.random() * 10;
        if (progress > 85) progress = 85;
        updateLoadingProgress(progress, '创建任务中...', '正在处理作业数据');
    }, 150);
    
    try {
        const res = await fetch('/api/batch/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                subject_id: parseInt(subjectId),
                test_condition_id: selectedConditionId,
                test_condition_name: selectedConditionName,
                fuzzy_threshold: fuzzyThreshold,
                homework_ids: Array.from(selectedHomeworkIds),
                collection_id: collectionId || null
            })
        });
        
        updateLoadingProgress(90, '创建任务中...', '保存任务数据');
        const data = await res.json();
        
        if (data.success) {
            updateLoadingProgress(100, '创建成功', '');
            clearInterval(progressInterval);
            setTimeout(async () => {
                hideLoading();
                hideModal('createTaskModal');
                await loadTaskList();
                selectTask(data.task_id);
            }, 200);
            return;
        } else {
            alert('创建失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('创建失败: ' + e.message);
    }
    clearInterval(progressInterval);
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
            hideLoading();  // 重置完成后隐藏加载状态
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
            body: JSON.stringify({ 
                auto_recognize: true,
                fuzzy_threshold: evalSettings.fuzzyThreshold / 100,
                ignore_index_prefix: evalSettings.ignoreIndexPrefix
            })
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
    
    let html = `
        <div class="stats-grid" style="margin-bottom: 16px;">
            <div class="stat-card highlight">
                <div class="stat-value">${accuracy}%</div>
                <div class="stat-label">准确率</div>
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
    
    // 错误列表（包含识别题干和识别差异的情况）
    const errors = evaluation.errors || [];
    if (errors.length > 0) {
        // 区分真正的错误、识别题干和识别差异（模糊匹配）
        const realErrors = errors.filter(e => e.error_type !== '识别题干-判断正确' && e.error_type !== '识别差异-判断正确');
        const stemRecognitions = errors.filter(e => e.error_type === '识别题干-判断正确');
        const fuzzyMatches = errors.filter(e => e.error_type === '识别差异-判断正确');
        
        let listTitle = '错误题目';
        const parts = [];
        if (realErrors.length > 0) parts.push(`错误 ${realErrors.length}题`);
        if (stemRecognitions.length > 0) parts.push(`识别题干 ${stemRecognitions.length}题`);
        if (fuzzyMatches.length > 0) parts.push(`识别差异 ${fuzzyMatches.length}题`);
        listTitle = parts.join(' + ') || '错误题目';
        
        html += `
            <div class="list-header">${listTitle}</div>
            <div class="error-list">
                ${errors.slice(0, 10).map(err => {
                    const isStemOrFuzzy = err.error_type === '识别题干-判断正确' || err.error_type === '识别差异-判断正确';
                    const similarityText = err.similarity != null ? ` (相似度: ${(err.similarity * 100).toFixed(1)}%)` : '';
                    return `
                    <div class="error-item ${isStemOrFuzzy ? 'stem-recognition' : ''}">
                        <div class="error-index">题${err.index || '-'}</div>
                        <div class="error-detail">
                            <div><span class="label">类型:</span> <span class="tag ${getErrorTypeClass(err.error_type)}">${escapeHtml(err.error_type || '-')}</span>${similarityText}</div>
                            <div><span class="label">说明:</span> ${escapeHtml(err.explanation || '-')}</div>
                        </div>
                    </div>
                `}).join('')}
                ${errors.length > 10 ? `<div class="more-errors">还有 ${errors.length - 10} 个...</div>` : ''}
            </div>
        `;
    } else {
        html += '<div class="success-message">所有题目评估正确</div>';
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
    
    // 高亮选中的作业项
    document.querySelectorAll('.homework-item').forEach(el => {
        el.classList.remove('selected');
    });
    const selectedItem = document.querySelector(`.homework-item[data-homework-id="${homeworkId}"]`);
    if (selectedItem) {
        selectedItem.classList.add('selected');
    }
    
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
    
    let html = `
        <div class="stats-grid">
            <div class="stat-card highlight">
                <div class="stat-value">${accuracy}%</div>
                <div class="stat-label">准确率</div>
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
                            '识别题干-判断正确': '#06b6d4',
                            '识别差异-判断正确': '#14b8a6',  // 语文主观题模糊匹配
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
                    
                    // 获取题型名称
                    const questionTypeName = getQuestionTypeName(err.question_category, baseEffect);
                    
                    // 判断是否为不计入错误的类型（识别差异-判断正确、识别题干-判断正确、格式差异）
                    const isNotCountedAsError = ['识别差异-判断正确', '识别题干-判断正确', '格式差异'].includes(err.error_type);
                    const cardClass = isNotCountedAsError ? 'error-card not-counted-error' : 'error-card';
                    const headerClass = isNotCountedAsError ? 'error-card-header fuzzy-match-header' : 'error-card-header';
                    
                    return `
                        <div class="${cardClass}" data-page="${detail.page_num || ''}" data-index="${err.index || ''}">
                            <div class="${headerClass}">
                                <div class="error-card-title">
                                    <span class="error-index">题${err.index || '-'}</span>
                                    ${questionTypeName ? `<span class="question-type-badge">${escapeHtml(questionTypeName)}</span>` : ''}
                                    ${isNotCountedAsError ? '<span class="not-counted-badge">不计入错误</span>' : `<span class="severity-badge severity-${severityClass}">${severity === 'high' ? '高' : severity === 'low' ? '低' : '中'}</span>`}
                                    <span class="tag ${errorTypeClass}">${escapeHtml(err.error_type || '-')}</span>
                                    ${err.similarity != null ? `<span class="similarity-badge">${(err.similarity * 100).toFixed(1)}%</span>` : ''}
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
                                            <td class="answer-cell">${escapeHtml(normalizeMarkdownFormula(item.userAnswer) || '-')}</td>
                                            <td class="answer-cell muted">${escapeHtml(normalizeMarkdownFormula(item.answer || item.mainAnswer) || '-')}</td>
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
                        <td class="answer-cell">${escapeHtml(normalizeMarkdownFormula(child.userAnswer) || '-')}</td>
                        <td class="answer-cell muted">${escapeHtml(normalizeMarkdownFormula(child.answer || child.mainAnswer) || '-')}</td>
                        <td class="correct-cell"><span class="${getCorrectClass(child)}">${getCorrectText(child)}</span></td>
                    </tr>
                `;
            });
        } else {
            // 无小题，直接显示
            html += `
                <tr>
                    <td class="index-cell">${escapeHtml(String(item.index || '-'))}</td>
                    <td class="answer-cell">${escapeHtml(normalizeMarkdownFormula(item.userAnswer) || '-')}</td>
                    <td class="answer-cell muted">${escapeHtml(normalizeMarkdownFormula(item.answer || item.mainAnswer) || '-')}</td>
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
                        <div class="compare-base ${!userMatch ? 'highlight' : ''}">${escapeHtml(normalizeMarkdownFormula(baseUser) || '-')}</div>
                        <div class="compare-ai ${!userMatch ? 'highlight' : ''}">${escapeHtml(normalizeMarkdownFormula(aiUser) || '-')}</div>
                        <div class="compare-match">${userMatch ? '<span class="match-yes">✓</span>' : '<span class="match-no">✗</span>'}</div>
                    </div>
                    <div class="compare-row">
                        <div class="compare-label">标准答案</div>
                        <div class="compare-base">${escapeHtml(normalizeMarkdownFormula(base.answer || base.mainAnswer) || '-')}</div>
                        <div class="compare-ai">${ai ? escapeHtml(normalizeMarkdownFormula(ai.answer || ai.mainAnswer) || '-') : '-'}</div>
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

// 获取题型名称
function getQuestionTypeName(questionCategory, baseEffect) {
    if (!questionCategory && !baseEffect) return '';
    
    // 优先从 question_category 获取
    if (questionCategory) {
        if (questionCategory.is_choice) {
            const choiceTypeMap = {
                'single': '单选题',
                'multiple': '多选题',
                'judge': '判断题'
            };
            return choiceTypeMap[questionCategory.choice_type] || '选择题';
        }
        if (questionCategory.is_fill) return '填空题';
        if (questionCategory.is_subjective) return '主观解答题';
    }
    
    // 从 base_effect 的 bvalue 推断
    const bvalue = String(baseEffect?.bvalue || '');
    const bvalueMap = {
        '1': '单选题',
        '2': '多选题',
        '3': '判断题',
        '4': '填空题',
        '5': '主观解答题'
    };
    return bvalueMap[bvalue] || '';
}

function getErrorTypeClass(errorType) {
    const classMap = {
        '识别错误-判断正确': 'tag-info',
        '识别错误-判断错误': 'tag-error',
        '识别正确-判断错误': 'tag-warning',
        '识别题干-判断正确': 'tag-stem',
        '识别差异-判断正确': 'tag-fuzzy',  // 语文主观题模糊匹配
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

// ========== 错误类型详情弹窗 ==========
function showErrorTypeDetail(errorType) {
    if (!selectedTask || !selectedTask.homework_items) return;
    
    // 收集该错误类型的所有题目
    const errorItems = [];
    const colorMap = {
        '识别错误-判断正确': '#3b82f6',
        '识别错误-判断错误': '#ef4444',
        '识别正确-判断错误': '#f59e0b',
        '识别题干-判断正确': '#06b6d4',
        '识别差异-判断正确': '#14b8a6',
        '格式差异': '#10b981',
        '缺失题目': '#6b7280',
        'AI识别幻觉': '#8b5cf6'
    };
    const typeColor = colorMap[errorType] || '#6b7280';
    
    selectedTask.homework_items.forEach(item => {
        if (item.status !== 'completed') return;
        const errors = item.evaluation?.errors || [];
        errors.forEach(err => {
            if (err.error_type === errorType) {
                errorItems.push({
                    pageNum: item.page_num || '?',
                    homeworkId: item.homework_id,
                    index: err.index || '-',
                    baseUser: err.base_effect?.userAnswer || '-',
                    aiUser: err.ai_result?.userAnswer || '-',
                    baseCorrect: err.base_effect?.correct || '-',
                    aiCorrect: err.ai_result?.correct || '-',
                    explanation: err.explanation || '-',
                    similarity: err.similarity,
                    baseAnswer: err.base_effect?.answer || '-',
                    aiAnswer: err.ai_result?.answer || '-'
                });
            }
        });
    });
    
    if (errorItems.length === 0) {
        alert(`没有找到"${errorType}"类型的错误`);
        return;
    }
    
    // 创建弹窗
    const modal = document.createElement('div');
    modal.className = 'error-detail-modal';
    modal.innerHTML = `
        <div class="error-detail-overlay" onclick="closeErrorDetailModal()"></div>
        <div class="error-detail-content">
            <div class="error-detail-header">
                <div class="error-detail-title">
                    <span class="error-type-dot" style="background: ${typeColor}"></span>
                    ${escapeHtml(errorType)}
                    <span class="error-count">${errorItems.length}题</span>
                </div>
                <button class="error-detail-close" onclick="closeErrorDetailModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="error-detail-body">
                <div class="error-cards-list">
                    ${errorItems.map((item, idx) => `
                        <div class="error-card" data-idx="${idx}">
                            <div class="error-card-header" onclick="toggleErrorCard(this)">
                                <div class="error-card-summary">
                                    <span class="error-card-page">P${item.pageNum}</span>
                                    <span class="error-card-index">题${escapeHtml(item.index)}</span>
                                    <span class="error-card-preview">${escapeHtml(truncateText(item.baseUser, 30))} vs ${escapeHtml(truncateText(item.aiUser, 30))}</span>
                                    ${item.similarity != null ? `<span class="error-card-similarity">${(item.similarity * 100).toFixed(1)}%</span>` : ''}
                                </div>
                                <span class="error-card-toggle">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M6 9l6 6 6-6"/>
                                    </svg>
                                </span>
                            </div>
                            <div class="error-card-detail" style="display: none;">
                                <div class="error-card-row">
                                    <div class="error-card-label">基准用户答案</div>
                                    <div class="error-card-value full-text">${escapeHtml(item.baseUser)}</div>
                                </div>
                                <div class="error-card-row">
                                    <div class="error-card-label">AI识别答案</div>
                                    <div class="error-card-value full-text">${escapeHtml(item.aiUser)}</div>
                                </div>
                                <div class="error-card-row two-col">
                                    <div class="error-card-col">
                                        <div class="error-card-label">基准判断</div>
                                        <div class="error-card-value ${item.baseCorrect === 'yes' ? 'correct-yes' : 'correct-no'}">${item.baseCorrect}</div>
                                    </div>
                                    <div class="error-card-col">
                                        <div class="error-card-label">AI判断</div>
                                        <div class="error-card-value ${item.aiCorrect === 'yes' ? 'correct-yes' : 'correct-no'}">${item.aiCorrect}</div>
                                    </div>
                                    ${item.similarity != null ? `
                                    <div class="error-card-col">
                                        <div class="error-card-label">相似度</div>
                                        <div class="error-card-value similarity-value">${(item.similarity * 100).toFixed(1)}%</div>
                                    </div>
                                    ` : ''}
                                </div>
                                <div class="error-card-row">
                                    <div class="error-card-label">说明</div>
                                    <div class="error-card-value explanation">${escapeHtml(item.explanation)}</div>
                                </div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.addEventListener('keydown', handleModalEsc);
}

function toggleErrorCard(header) {
    const card = header.closest('.error-card');
    const detail = card.querySelector('.error-card-detail');
    const toggle = card.querySelector('.error-card-toggle svg');
    
    if (detail.style.display === 'none') {
        detail.style.display = 'block';
        toggle.style.transform = 'rotate(180deg)';
        card.classList.add('expanded');
    } else {
        detail.style.display = 'none';
        toggle.style.transform = 'rotate(0deg)';
        card.classList.remove('expanded');
    }
}

function closeErrorDetailModal() {
    const modal = document.querySelector('.error-detail-modal');
    if (modal) {
        modal.remove();
    }
    document.removeEventListener('keydown', handleModalEsc);
}

function handleModalEsc(e) {
    if (e.key === 'Escape') {
        closeErrorDetailModal();
        closeAccuracyDetailModal();
    }
}

// ========== 准确率详情弹窗 ==========
function showAccuracyDetail(type, subType) {
    if (!window.accuracyDetails) {
        alert('暂无详情数据');
        return;
    }
    
    let title = '';
    let items = [];
    let colorCorrect = '';
    let colorWrong = '';
    
    if (type === 'recognition') {
        title = subType === 'correct' ? '识别正确详情' : (subType === 'wrong' ? '识别错误详情' : '识别准确率详情');
        colorCorrect = '#34c759';
        colorWrong = '#ff3b30';
        
        if (subType === 'correct') {
            items = window.accuracyDetails.recognition.correct || [];
        } else if (subType === 'wrong') {
            items = window.accuracyDetails.recognition.wrong || [];
        } else {
            // 显示汇总 - 使用新弹窗
            const correct = window.accuracyDetails.recognition.correct || [];
            const wrong = window.accuracyDetails.recognition.wrong || [];
            showAccuracySummaryModal('recognition', correct, wrong, colorCorrect, colorWrong);
            return;
        }
    } else if (type === 'grading') {
        title = subType === 'correct' ? '批改正确详情' : (subType === 'wrong' ? '批改错误详情' : '批改准确率详情');
        colorCorrect = '#007aff';
        colorWrong = '#ff9500';
        
        if (subType === 'correct') {
            items = window.accuracyDetails.grading.correct || [];
        } else if (subType === 'wrong') {
            items = window.accuracyDetails.grading.wrong || [];
        } else {
            // 显示汇总 - 使用新弹窗
            const correct = window.accuracyDetails.grading.correct || [];
            const wrong = window.accuracyDetails.grading.wrong || [];
            showAccuracySummaryModal('grading', correct, wrong, colorCorrect, colorWrong);
            return;
        }
    }
    
    // 显示详情列表 - 使用类似错误类型详情的卡片式弹窗
    if (items.length === 0) {
        alert('暂无数据');
        return;
    }
    
    const color = subType === 'correct' ? colorCorrect : colorWrong;
    const typeName = type === 'recognition' ? '识别' : '批改';
    const statusName = subType === 'correct' ? '正确' : '错误';
    
    // 创建弹窗
    const modal = document.createElement('div');
    modal.className = 'error-detail-modal';
    modal.innerHTML = `
        <div class="error-detail-overlay" onclick="closeAccuracyDetailModal()"></div>
        <div class="error-detail-content">
            <div class="error-detail-header">
                <div class="error-detail-title">
                    <span class="error-type-dot" style="background: ${color}"></span>
                    ${typeName}${statusName}详情
                    <span class="error-count">${items.length}题</span>
                </div>
                <button class="error-detail-close" onclick="closeAccuracyDetailModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="error-detail-body">
                <div class="error-cards-list">
                    ${items.map((item, idx) => `
                        <div class="error-card" data-idx="${idx}">
                            <div class="error-card-header" onclick="toggleErrorCard(this)">
                                <div class="error-card-summary">
                                    <span class="error-card-page">P${item.pageNum}</span>
                                    <span class="error-card-index">题${escapeHtml(String(item.index))}</span>
                                    <span class="error-card-preview">${escapeHtml(truncateText(item.baseUser || '-', 30))}</span>
                                    <span class="error-card-type" style="background: ${subType === 'correct' ? '#e3f9e5' : '#ffeef0'}; color: ${subType === 'correct' ? '#1e7e34' : '#d73a49'};">${escapeHtml(item.errorType || statusName)}</span>
                                </div>
                                <span class="error-card-toggle">
                                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M6 9l6 6 6-6"/>
                                    </svg>
                                </span>
                            </div>
                            <div class="error-card-detail" style="display: none;">
                                <div class="error-card-row">
                                    <div class="error-card-label">标准答案</div>
                                    <div class="error-card-value full-text">${escapeHtml(item.baseAnswer || '-')}</div>
                                </div>
                                <div class="error-card-row">
                                    <div class="error-card-label">基准用户答案</div>
                                    <div class="error-card-value full-text">${escapeHtml(item.baseUser || '-')}</div>
                                </div>
                                <div class="error-card-row">
                                    <div class="error-card-label">AI识别答案</div>
                                    <div class="error-card-value full-text">${escapeHtml(item.hwUser || '-')}</div>
                                </div>
                                ${item.baseCorrect && item.baseCorrect !== '-' ? `
                                <div class="error-card-row two-col">
                                    <div class="error-card-col">
                                        <div class="error-card-label">基准判断</div>
                                        <div class="error-card-value ${item.baseCorrect === 'yes' ? 'correct-yes' : 'correct-no'}">${item.baseCorrect}</div>
                                    </div>
                                    <div class="error-card-col">
                                        <div class="error-card-label">AI判断</div>
                                        <div class="error-card-value ${item.aiCorrect === 'yes' ? 'correct-yes' : 'correct-no'}">${item.aiCorrect || '-'}</div>
                                    </div>
                                </div>
                                ` : ''}
                                ${item.explanation ? `
                                <div class="error-card-row">
                                    <div class="error-card-label">说明</div>
                                    <div class="error-card-value explanation">${escapeHtml(item.explanation)}</div>
                                </div>
                                ` : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.addEventListener('keydown', handleAccuracyModalEsc);
}

// 显示准确率汇总弹窗
function showAccuracySummaryModal(type, correct, wrong, colorCorrect, colorWrong) {
    const typeName = type === 'recognition' ? '识别' : '批改';
    
    // 使用计算出来的统计数字（从 window.accuracyStats 获取）
    const stats = window.accuracyStats || {};
    let correctCount, wrongCount, total, rate;
    
    if (type === 'recognition') {
        correctCount = stats.recognitionCorrect || 0;
        wrongCount = stats.recognitionWrong || 0;
        total = stats.totalQuestions || 0;
        rate = stats.recognitionRate || 0;
    } else {
        correctCount = stats.gradingCorrect || 0;
        wrongCount = stats.gradingWrong || 0;
        total = stats.totalQuestions || 0;
        rate = stats.gradingRate || 0;
    }
    
    const modal = document.createElement('div');
    modal.className = 'error-detail-modal';
    modal.innerHTML = `
        <div class="error-detail-overlay" onclick="closeAccuracyDetailModal()"></div>
        <div class="error-detail-content" style="max-width: 800px;">
            <div class="error-detail-header">
                <div class="error-detail-title">
                    ${typeName}准确率详情
                    <span class="error-count">${total}题</span>
                </div>
                <button class="error-detail-close" onclick="closeAccuracyDetailModal()">
                    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M18 6L6 18M6 6l12 12"/>
                    </svg>
                </button>
            </div>
            <div class="error-detail-body">
                <div class="accuracy-summary-stats" style="display: flex; gap: 16px; margin-bottom: 20px;">
                    <div class="accuracy-stat-card" style="flex: 1; background: #e3f9e5; padding: 16px; border-radius: 8px; text-align: center; cursor: pointer;" onclick="showAccuracyDetail('${type}', 'correct')">
                        <div style="font-size: 24px; font-weight: 600; color: #1e7e34;">${correctCount}</div>
                        <div style="font-size: 12px; color: #1e7e34;">${typeName}正确</div>
                    </div>
                    <div class="accuracy-stat-card" style="flex: 1; background: #ffeef0; padding: 16px; border-radius: 8px; text-align: center; cursor: pointer;" onclick="showAccuracyDetail('${type}', 'wrong')">
                        <div style="font-size: 24px; font-weight: 600; color: #d73a49;">${wrongCount}</div>
                        <div style="font-size: 12px; color: #d73a49;">${typeName}错误</div>
                    </div>
                    <div class="accuracy-stat-card" style="flex: 1; background: #f5f5f7; padding: 16px; border-radius: 8px; text-align: center;">
                        <div style="font-size: 24px; font-weight: 600; color: ${colorCorrect};">${rate.toFixed(1)}%</div>
                        <div style="font-size: 12px; color: #86868b;">准确率</div>
                    </div>
                </div>
                
                <div style="margin-bottom: 16px;">
                    <div style="font-weight: 500; margin-bottom: 8px; color: #d73a49;">错误题目列表 (${wrong.length}题)</div>
                    <div class="error-cards-list" style="max-height: 400px; overflow-y: auto;">
                        ${wrong.length === 0 ? '<div style="text-align: center; color: #86868b; padding: 20px;">无错误题目</div>' : 
                        wrong.map((item, idx) => `
                            <div class="error-card" data-idx="${idx}" style="background: #fff; border: 1px solid #e5e5e5; border-radius: 8px; margin-bottom: 8px;">
                                <div class="error-card-header" onclick="toggleErrorCard(this)" style="display: flex; align-items: center; justify-content: space-between; padding: 12px 16px; cursor: pointer; background: #fff;">
                                    <div class="error-card-summary" style="display: flex; align-items: center; gap: 8px; flex: 1; color: #1d1d1f;">
                                        <span style="font-size: 12px; font-weight: 500; color: #1d1d1f; background: #f5f5f7; padding: 2px 8px; border-radius: 4px;">P${item.pageNum || '?'}</span>
                                        <span style="font-size: 13px; font-weight: 600; color: #1d1d1f;">题${escapeHtml(String(item.index || '-'))}</span>
                                        <span style="font-size: 13px; color: #666; flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">${escapeHtml(truncateText(item.baseUser || '-', 20))} vs ${escapeHtml(truncateText(item.hwUser || '-', 20))}</span>
                                        <span style="background: #ffeef0; color: #d73a49; padding: 2px 6px; border-radius: 4px; font-size: 11px;">${escapeHtml(item.errorType || '-')}</span>
                                    </div>
                                    <span class="error-card-toggle" style="color: #1d1d1f;">
                                        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                                            <path d="M6 9l6 6 6-6"/>
                                        </svg>
                                    </span>
                                </div>
                                <div class="error-card-detail" style="display: none; padding: 12px 16px; border-top: 1px solid #e5e5e5; background: #fafafa;">
                                    <div style="margin-bottom: 8px;">
                                        <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">标准答案</div>
                                        <div style="font-size: 13px; color: #1d1d1f; background: #fff; padding: 8px; border-radius: 4px;">${escapeHtml(item.baseAnswer || '-')}</div>
                                    </div>
                                    <div style="margin-bottom: 8px;">
                                        <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">基准用户答案</div>
                                        <div style="font-size: 13px; color: #1d1d1f; background: #fff; padding: 8px; border-radius: 4px;">${escapeHtml(item.baseUser || '-')}</div>
                                    </div>
                                    <div style="margin-bottom: 8px;">
                                        <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">AI识别答案</div>
                                        <div style="font-size: 13px; color: #1d1d1f; background: #fff; padding: 8px; border-radius: 4px;">${escapeHtml(item.hwUser || '-')}</div>
                                    </div>
                                    ${item.baseCorrect && item.baseCorrect !== '-' ? `
                                    <div style="display: flex; gap: 16px; margin-bottom: 8px;">
                                        <div style="flex: 1;">
                                            <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">基准判断</div>
                                            <div style="font-size: 13px; font-weight: 600; color: ${item.baseCorrect === 'yes' ? '#10b981' : '#ef4444'};">${item.baseCorrect}</div>
                                        </div>
                                        <div style="flex: 1;">
                                            <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">AI判断</div>
                                            <div style="font-size: 13px; font-weight: 600; color: ${item.aiCorrect === 'yes' ? '#10b981' : '#ef4444'};">${item.aiCorrect || '-'}</div>
                                        </div>
                                    </div>
                                    ` : ''}
                                    ${item.explanation ? `
                                    <div>
                                        <div style="font-size: 11px; color: #86868b; margin-bottom: 4px;">说明</div>
                                        <div style="font-size: 12px; color: #666;">${escapeHtml(item.explanation)}</div>
                                    </div>
                                    ` : ''}
                                </div>
                            </div>
                        `).join('')}
                    </div>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    document.addEventListener('keydown', handleAccuracyModalEsc);
}

function closeAccuracyDetailModal() {
    // 关闭动态创建的准确率详情弹窗
    const modals = document.querySelectorAll('.error-detail-modal');
    modals.forEach(modal => {
        // 只移除动态创建的弹窗（不是 #errorDetailModal）
        if (!modal.id) {
            modal.remove();
        }
    });
    document.removeEventListener('keydown', handleAccuracyModalEsc);
}

function handleAccuracyModalEsc(e) {
    if (e.key === 'Escape') {
        closeAccuracyDetailModal();
    }
}

function truncateText(text, maxLen) {
    if (!text) return '';
    text = String(text);
    return text.length > maxLen ? text.substring(0, maxLen) + '...' : text;
}

// ========== AI报告弹窗 ==========
let currentAIReport = null;

function showAIReportModal() {
    document.getElementById('aiReportModal').classList.add('show');
}

function hideAIReportModal() {
    document.getElementById('aiReportModal').classList.remove('show');
}

// 查看 AI 智能分析报告
function viewAnalysisReport() {
    if (!selectedTask) return;
    window.open(`/analysis-report/${selectedTask.task_id}`, '_blank');
}

async function generateAIReport(forceRegenerate = false) {
    if (!selectedTask) return;
    
    // 显示弹窗
    showAIReportModal();
    
    // 显示加载状态（带进度提示）
    const loadingHtml = forceRegenerate ? `
        <div class="ai-report-loading">
            <div class="spinner"></div>
            <div class="loading-title">正在调用 DeepSeek 大模型分析...</div>
            <div class="loading-progress">
                <div class="progress-steps">
                    <div class="step active">收集数据</div>
                    <div class="step active">调用AI模型</div>
                    <div class="step">生成报告</div>
                </div>
            </div>
            <div class="loading-hint">预计需要 10-30 秒，请耐心等待</div>
        </div>
    ` : `
        <div class="ai-report-loading">
            <div class="spinner"></div>
            <div class="loading-title">正在加载分析报告...</div>
        </div>
    `;
    document.getElementById('aiReportModalBody').innerHTML = loadingHtml;
    document.getElementById('reportGeneratedTime').textContent = '';
    
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/ai-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: forceRegenerate })
        });
        const data = await res.json();
        
        if (data.success) {
            currentAIReport = data.report;
            renderAIReportModal(data.report, data.cached);
            
            // 更新任务数据
            if (!selectedTask.overall_report) selectedTask.overall_report = {};
            selectedTask.overall_report.ai_analysis = data.report;
        } else {
            document.getElementById('aiReportModalBody').innerHTML = `
                <div class="ai-report-error">
                    <div class="error-icon">!</div>
                    <div class="error-title">AI分析失败</div>
                    <div class="error-text">${escapeHtml(data.error || '未知错误')}</div>
                    <button class="btn btn-primary" onclick="regenerateAIReport()">重试</button>
                </div>
            `;
        }
    } catch (e) {
        document.getElementById('aiReportModalBody').innerHTML = `
            <div class="ai-report-error">
                <div class="error-icon">!</div>
                <div class="error-title">请求失败</div>
                <div class="error-text">${escapeHtml(e.message)}</div>
                <button class="btn btn-primary" onclick="regenerateAIReport()">重试</button>
            </div>
        `;
    }
}

function regenerateAIReport() {
    generateAIReport(true);
}

function renderAIReportModal(report, cached) {
    if (!report) return;
    
    const overview = report.overview || {};
    const scores = report.capability_scores || {};
    const topIssues = report.top_issues || [];
    const errorCases = report.error_case_analysis || [];
    const recommendations = report.recommendations || [];
    const conclusion = report.conclusion || '';
    const typePerf = report.type_performance || {};
    
    let html = '';
    
    // 评分卡片
    html += `
        <div class="ai-report-scores">
            <div class="score-card highlight">
                <div class="score-value">${overview.pass_rate || 0}%</div>
                <div class="score-label">总准确率</div>
            </div>
            <div class="score-card">
                <div class="score-value">${scores.recognition || 0}</div>
                <div class="score-label">识别能力</div>
            </div>
            <div class="score-card">
                <div class="score-value">${scores.judgment || 0}</div>
                <div class="score-label">判断能力</div>
            </div>
            <div class="score-card">
                <div class="score-value">${scores.overall || 0}</div>
                <div class="score-label">综合评分</div>
            </div>
        </div>
    `;
    
    // 数据概览
    html += `
        <div class="ai-report-section">
            <div class="section-title">数据概览</div>
            <div class="overview-stats">
                <span>总题目 <strong>${overview.total || 0}</strong></span>
                <span class="divider">|</span>
                <span>正确 <strong>${overview.passed || 0}</strong></span>
                <span class="divider">|</span>
                <span>错误 <strong>${overview.failed || 0}</strong></span>
                <span class="divider">|</span>
                <span>作业数 <strong>${overview.homework_count || 0}</strong></span>
            </div>
        </div>
    `;
    
    // 主要问题
    if (topIssues.length > 0) {
        html += `
            <div class="ai-report-section">
                <div class="section-title">主要问题</div>
                <div class="issues-list">
                    ${topIssues.map((issue, i) => `
                        <div class="issue-item">
                            <span class="issue-rank">${i + 1}</span>
                            <span class="issue-name">${escapeHtml(issue.issue || '')}</span>
                            <span class="issue-count">${issue.count || 0}次</span>
                            <span class="issue-severity severity-${issue.severity || 'medium'}">${getSeverityText(issue.severity)}</span>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // 典型错误案例分析
    if (errorCases.length > 0) {
        html += `
            <div class="ai-report-section">
                <div class="section-title">典型错误案例分析</div>
                <div class="error-cases">
                    ${errorCases.map((c, i) => `
                        <div class="error-case-card">
                            <div class="case-header">
                                <span class="case-index">案例${i + 1}: 第${escapeHtml(c.index || '?')}题</span>
                                <span class="case-type">${escapeHtml(c.error_type || '')}</span>
                            </div>
                            <div class="case-comparison">
                                <div class="case-row">
                                    <span class="case-label">基准答案:</span>
                                    <span class="case-value">${escapeHtml(c.base_answer || '-')}</span>
                                </div>
                                <div class="case-row">
                                    <span class="case-label">AI识别:</span>
                                    <span class="case-value">${escapeHtml(c.ai_answer || '-')}</span>
                                </div>
                                ${c.standard_answer ? `
                                <div class="case-row">
                                    <span class="case-label">标准答案:</span>
                                    <span class="case-value">${escapeHtml(c.standard_answer)}</span>
                                </div>
                                ` : ''}
                                <div class="case-row">
                                    <span class="case-label">判断对比:</span>
                                    <span class="case-value">基准=${c.base_correct || '-'}, AI=${c.ai_correct || '-'}</span>
                                </div>
                            </div>
                            <div class="case-analysis">
                                <div class="analysis-title">错误原因分析:</div>
                                <div class="analysis-content">${escapeHtml(c.root_cause || '暂无分析')}</div>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // 改进建议
    if (recommendations.length > 0) {
        html += `
            <div class="ai-report-section">
                <div class="section-title">改进建议</div>
                <div class="recommendations-list">
                    ${recommendations.map(rec => {
                        if (typeof rec === 'string') {
                            return `<div class="recommendation-item"><span class="rec-text">${escapeHtml(rec)}</span></div>`;
                        }
                        return `
                            <div class="recommendation-item">
                                <span class="rec-title">${escapeHtml(rec.title || '')}</span>
                                <span class="rec-detail">${escapeHtml(rec.detail || '')}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }
    
    // 总体结论
    if (conclusion) {
        html += `
            <div class="ai-report-section">
                <div class="section-title">总体结论</div>
                <div class="conclusion-text">${escapeHtml(conclusion)}</div>
            </div>
        `;
    }
    
    document.getElementById('aiReportModalBody').innerHTML = html;
    
    // 显示生成时间
    const generatedAt = report.generated_at || '';
    const cacheText = cached ? '(缓存)' : '(新生成)';
    document.getElementById('reportGeneratedTime').textContent = generatedAt ? `生成时间: ${generatedAt} ${cacheText}` : '';
}

function getSeverityText(severity) {
    const map = { 'high': '高', 'medium': '中', 'low': '低' };
    return map[severity] || '中';
}

async function downloadReportScreenshot() {
    if (!currentAIReport) {
        alert('没有可下载的报告');
        return;
    }
    
    const modalBody = document.getElementById('aiReportModalBody');
    if (!modalBody) {
        alert('报告内容不存在');
        return;
    }
    
    // 显示加载提示
    const downloadBtn = event.target;
    const originalText = downloadBtn.textContent;
    downloadBtn.textContent = '生成中...';
    downloadBtn.disabled = true;
    
    try {
        // 使用 html2canvas 生成截图
        const canvas = await html2canvas(modalBody, {
            backgroundColor: '#ffffff',
            scale: 2, // 2倍清晰度
            useCORS: true,
            logging: false,
            windowWidth: modalBody.scrollWidth,
            windowHeight: modalBody.scrollHeight
        });
        
        // 转换为图片并下载
        const link = document.createElement('a');
        const taskName = selectedTask?.name || 'AI分析报告';
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `${taskName}_${timestamp}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
        
    } catch (e) {
        console.error('截图失败:', e);
        alert('截图生成失败: ' + e.message);
    } finally {
        downloadBtn.textContent = originalText;
        downloadBtn.disabled = false;
    }
}

// 保留复制报告功能（可选）
function copyAIReport() {
    if (!currentAIReport) {
        alert('没有可复制的报告');
        return;
    }
    
    // 构建纯文本报告
    const report = currentAIReport;
    const overview = report.overview || {};
    const scores = report.capability_scores || {};
    const topIssues = report.top_issues || [];
    const errorCases = report.error_case_analysis || [];
    const recommendations = report.recommendations || [];
    const conclusion = report.conclusion || '';
    
    let text = `AI 批改效果分析报告\n`;
    text += `${'='.repeat(40)}\n\n`;
    
    text += `【数据概览】\n`;
    text += `总准确率: ${overview.pass_rate || 0}%\n`;
    text += `总题目: ${overview.total || 0} | 正确: ${overview.passed || 0} | 错误: ${overview.failed || 0}\n\n`;
    
    text += `【能力评分】\n`;
    text += `识别能力: ${scores.recognition || 0} | 判断能力: ${scores.judgment || 0} | 综合评分: ${scores.overall || 0}\n\n`;
    
    if (topIssues.length > 0) {
        text += `【主要问题】\n`;
        topIssues.forEach((issue, i) => {
            text += `${i + 1}. ${issue.issue}: ${issue.count}次\n`;
        });
        text += '\n';
    }
    
    if (errorCases.length > 0) {
        text += `【典型错误案例】\n`;
        errorCases.forEach((c, i) => {
            text += `案例${i + 1}: 第${c.index}题 (${c.error_type})\n`;
            text += `  基准答案: ${c.base_answer}\n`;
            text += `  AI识别: ${c.ai_answer}\n`;
            text += `  错误原因: ${c.root_cause}\n\n`;
        });
    }
    
    if (recommendations.length > 0) {
        text += `【改进建议】\n`;
        recommendations.forEach(rec => {
            if (typeof rec === 'string') {
                text += `- ${rec}\n`;
            } else {
                text += `- ${rec.title}: ${rec.detail}\n`;
            }
        });
        text += '\n';
    }
    
    if (conclusion) {
        text += `【总体结论】\n${conclusion}\n`;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        alert('报告已复制到剪贴板');
    }).catch(() => {
        alert('复制失败，请手动复制');
    });
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


// ========== 数据集选择功能 ==========

// 当前选择的数据集ID
let selectedDatasetId = null;
// 当前正在选择数据集的作业ID列表
let currentSelectingHomeworkIds = [];

/**
 * 显示数据集选择弹窗
 * @param {string} homeworkId - 作业ID
 */
async function showDatasetSelector(homeworkId) {
    // 查找作业信息
    const homework = selectedTask?.homework_items?.find(h => h.homework_id === homeworkId);
    if (!homework) {
        alert('未找到作业信息');
        return;
    }
    
    // 设置当前选择的作业
    currentSelectingHomeworkIds = [homeworkId];
    selectedDatasetId = homework.matched_dataset || null;
    
    // 显示作业信息
    const selectorInfo = document.getElementById('selectorInfo');
    selectorInfo.innerHTML = `
        <div class="info-row">
            <span class="info-label">书本:</span>
            <span class="info-value">${escapeHtml(homework.book_name || '未知书本')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">页码:</span>
            <span class="info-value">第 ${homework.page_num || '-'} 页</span>
        </div>
        <div class="info-row">
            <span class="info-label">学生:</span>
            <span class="info-value">${escapeHtml(homework.student_name || homework.student_id || '-')}</span>
        </div>
    `;
    
    // 显示弹窗
    showModal('datasetSelectorModal');
    
    // 加载匹配的数据集
    await loadMatchingDatasets(homework.book_id, homework.page_num);
}

/**
 * 批量选择数据集
 * @param {Array<string>} homeworkIds - 作业ID列表
 */
async function batchSelectDataset(homeworkIds) {
    if (!homeworkIds || homeworkIds.length === 0) {
        alert('请先选择作业');
        return;
    }
    
    // 获取第一个作业的信息作为参考
    const firstHomework = selectedTask?.homework_items?.find(h => homeworkIds.includes(h.homework_id));
    if (!firstHomework) {
        alert('未找到作业信息');
        return;
    }
    
    // 设置当前选择的作业列表
    currentSelectingHomeworkIds = [...homeworkIds];
    selectedDatasetId = null;
    
    // 显示批量选择信息
    const selectorInfo = document.getElementById('selectorInfo');
    selectorInfo.innerHTML = `
        <div class="info-row">
            <span class="info-label">批量选择:</span>
            <span class="info-value">已选择 ${homeworkIds.length} 个作业</span>
        </div>
        <div class="info-row">
            <span class="info-label">书本:</span>
            <span class="info-value">${escapeHtml(firstHomework.book_name || '未知书本')}</span>
        </div>
        <div class="info-row">
            <span class="info-label">页码:</span>
            <span class="info-value">第 ${firstHomework.page_num || '-'} 页</span>
        </div>
    `;
    
    // 显示弹窗
    showModal('datasetSelectorModal');
    
    // 加载匹配的数据集
    await loadMatchingDatasets(firstHomework.book_id, firstHomework.page_num);
}

/**
 * 加载匹配的数据集列表
 * @param {string} bookId - 书本ID
 * @param {number} pageNum - 页码
 */
async function loadMatchingDatasets(bookId, pageNum) {
    const listContainer = document.getElementById('matchingDatasetList');
    listContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    // 禁用确认按钮
    document.getElementById('confirmDatasetBtn').disabled = true;
    
    try {
        const res = await fetch(`/api/batch/matching-datasets?book_id=${encodeURIComponent(bookId)}&page_num=${pageNum}`);
        const data = await res.json();
        
        if (!data.success) {
            listContainer.innerHTML = `<div class="empty-state"><div class="empty-state-text">加载失败: ${escapeHtml(data.error || '未知错误')}</div></div>`;
            return;
        }
        
        const datasets = data.data || [];
        
        if (datasets.length === 0) {
            listContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">未找到匹配的数据集</div></div>';
            return;
        }
        
        // 渲染数据集列表
        listContainer.innerHTML = datasets.map((ds, index) => {
            const isSelected = ds.dataset_id === selectedDatasetId;
            const isLatest = index === 0;
            const pagesStr = Array.isArray(ds.pages) ? ds.pages.join(', ') : ds.pages;
            
            return `
                <div class="dataset-selector-item ${isSelected ? 'selected' : ''}" 
                     onclick="selectDatasetItem('${ds.dataset_id}')">
                    <input type="radio" name="datasetSelect" value="${ds.dataset_id}" 
                           ${isSelected ? 'checked' : ''} 
                           onchange="selectDatasetItem('${ds.dataset_id}')">
                    <div class="dataset-selector-info">
                        <div class="dataset-selector-name">
                            ${escapeHtml(ds.name || ds.dataset_id)}
                            ${isLatest ? '<span class="latest-tag">最新</span>' : ''}
                        </div>
                        <div class="dataset-selector-meta">
                            <span>页码: ${pagesStr}</span>
                            <span>题目数: ${ds.question_count || 0}</span>
                            <span>创建: ${formatTime(ds.created_at)}</span>
                        </div>
                        ${ds.description ? `<div class="dataset-selector-desc">${escapeHtml(ds.description)}</div>` : ''}
                    </div>
                </div>
            `;
        }).join('');
        
        // 如果有预选的数据集，启用确认按钮
        if (selectedDatasetId) {
            document.getElementById('confirmDatasetBtn').disabled = false;
        }
        
    } catch (e) {
        console.error('加载匹配数据集失败:', e);
        listContainer.innerHTML = `<div class="empty-state"><div class="empty-state-text">加载失败: ${e.message}</div></div>`;
    }
}

/**
 * 选择数据集项
 * @param {string} datasetId - 数据集ID
 */
function selectDatasetItem(datasetId) {
    selectedDatasetId = datasetId;
    
    // 更新选中状态
    document.querySelectorAll('.dataset-selector-item').forEach(item => {
        const radio = item.querySelector('input[type="radio"]');
        if (radio && radio.value === datasetId) {
            item.classList.add('selected');
            radio.checked = true;
        } else {
            item.classList.remove('selected');
            if (radio) radio.checked = false;
        }
    });
    
    // 启用确认按钮
    document.getElementById('confirmDatasetBtn').disabled = false;
}

/**
 * 确认数据集选择
 */
async function confirmDatasetSelection() {
    if (!selectedDatasetId) {
        alert('请选择一个数据集');
        return;
    }
    
    if (!currentSelectingHomeworkIds || currentSelectingHomeworkIds.length === 0) {
        alert('未选择作业');
        return;
    }
    
    if (!selectedTask) {
        alert('未选择任务');
        return;
    }
    
    showLoading('更新数据集...');
    
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/select-dataset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_ids: currentSelectingHomeworkIds,
                dataset_id: selectedDatasetId
            })
        });
        
        const data = await res.json();
        
        if (!data.success) {
            throw new Error(data.error || '更新失败');
        }
        
        // 关闭弹窗
        hideModal('datasetSelectorModal');
        
        // 刷新任务详情
        await selectTask(selectedTask.task_id);
        
        // 显示成功提示
        const count = data.updated_count || 0;
        if (count > 0) {
            console.log(`已更新 ${count} 个作业的数据集`);
        }
        
    } catch (e) {
        alert('更新数据集失败: ' + e.message);
    }
    
    hideLoading();
}

/**
 * 隐藏数据集选择弹窗
 */
function hideDatasetSelector() {
    hideModal('datasetSelectorModal');
    selectedDatasetId = null;
    currentSelectingHomeworkIds = [];
}


// ========== 题目类型详情功能 ==========

// 当前查看的题目类型详情状态
let typeDetailState = {
    type: '',
    status: 'all',
    page: 1,
    pageSize: 50,
    loading: false
};

/**
 * 显示题目类型详情弹窗
 * @param {string} questionType - 题目类型: choice/objective_fill/subjective
 */
async function showTypeDetail(questionType) {
    if (!selectedTask || !selectedTask.task_id) {
        alert('请先选择任务');
        return;
    }
    
    typeDetailState.type = questionType;
    typeDetailState.status = 'all';
    typeDetailState.page = 1;
    
    // 显示弹窗
    showModal('typeDetailModal');
    
    // 加载数据
    await loadTypeDetailData();
}

/**
 * 加载题目类型详情数据
 */
async function loadTypeDetailData() {
    if (typeDetailState.loading) return;
    
    const container = document.getElementById('typeDetailContent');
    if (!container) return;
    
    typeDetailState.loading = true;
    container.innerHTML = `
        <div class="loading-state">
            <div class="loading-spinner"></div>
            <div>加载中...</div>
        </div>
    `;
    
    try {
        const params = new URLSearchParams({
            type: typeDetailState.type,
            status: typeDetailState.status,
            page: typeDetailState.page,
            page_size: typeDetailState.pageSize
        });
        
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/type-details?${params}`);
        const data = await res.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="error-state">加载失败: ${escapeHtml(data.error || '未知错误')}</div>`;
            return;
        }
        
        renderTypeDetailContent(data.data);
        
    } catch (e) {
        container.innerHTML = `<div class="error-state">加载失败: ${escapeHtml(e.message)}</div>`;
    } finally {
        typeDetailState.loading = false;
    }
}

/**
 * 渲染题目类型详情内容
 */
function renderTypeDetailContent(data) {
    const container = document.getElementById('typeDetailContent');
    if (!container) return;
    
    const stats = data.stats || {};
    const questions = data.questions || [];
    const pagination = data.pagination || {};
    const errorDist = data.error_type_distribution || {};
    
    // 更新弹窗标题
    const titleEl = document.getElementById('typeDetailTitle');
    if (titleEl) {
        titleEl.textContent = `${data.type_name || '题目'}详情`;
    }
    
    // 构建HTML
    let html = '';
    
    // 统计卡片
    html += `
        <div class="type-detail-stats">
            <div class="stat-card highlight">
                <div class="stat-value">${stats.total || 0}</div>
                <div class="stat-label">总数</div>
            </div>
            <div class="stat-card success">
                <div class="stat-value">${stats.correct || 0}</div>
                <div class="stat-label">正确</div>
            </div>
            <div class="stat-card error">
                <div class="stat-value">${(stats.total || 0) - (stats.correct || 0)}</div>
                <div class="stat-label">错误</div>
            </div>
            <div class="stat-card">
                <div class="stat-value">${stats.accuracy ? (stats.accuracy * 100).toFixed(1) + '%' : '-'}</div>
                <div class="stat-label">准确率</div>
            </div>
        </div>
    `;
    
    // 错误类型分布
    if (Object.keys(errorDist).length > 0) {
        html += `
            <div class="error-dist-section">
                <div class="section-subtitle">错误类型分布</div>
                <div class="error-dist-tags">
                    ${Object.entries(errorDist).map(([type, count]) => `
                        <span class="error-dist-tag ${getErrorTypeClass(type)}">${escapeHtml(type)}: ${count}</span>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    // 筛选器
    html += `
        <div class="type-detail-filter">
            <select id="typeDetailStatusFilter" onchange="onTypeDetailFilterChange()">
                <option value="all" ${typeDetailState.status === 'all' ? 'selected' : ''}>全部</option>
                <option value="error" ${typeDetailState.status === 'error' ? 'selected' : ''}>仅错误</option>
                <option value="correct" ${typeDetailState.status === 'correct' ? 'selected' : ''}>仅正确(有差异)</option>
            </select>
            <span class="filter-info">共 ${pagination.total || 0} 条记录</span>
        </div>
    `;
    
    // 题目列表
    if (questions.length === 0) {
        html += `
            <div class="empty-state">
                <div class="empty-state-text">暂无数据</div>
            </div>
        `;
    } else {
        html += `<div class="type-detail-list">`;
        
        for (const q of questions) {
            const isError = q.is_error;
            const baseEffect = q.base_effect || {};
            const aiResult = q.ai_result || {};
            
            html += `
                <div class="type-detail-item ${isError ? 'is-error' : 'is-correct'}">
                    <div class="item-header">
                        <span class="item-index">第${escapeHtml(q.index || '-')}题</span>
                        <span class="item-source">${escapeHtml(q.book_name || '')} P${q.page_num || '-'}</span>
                        <span class="error-type-tag ${getErrorTypeClass(q.error_type)}">${escapeHtml(q.error_type || '-')}</span>
                        ${!isError ? '<span class="not-counted-tag">不计入错误</span>' : ''}
                        ${q.similarity ? `<span class="similarity-tag">相似度: ${(q.similarity * 100).toFixed(1)}%</span>` : ''}
                    </div>
                    <div class="item-compare">
                        <div class="compare-row">
                            <span class="compare-label">基准答案:</span>
                            <span class="compare-value base">${escapeHtml(baseEffect.userAnswer || '-')}</span>
                            <span class="compare-correct ${baseEffect.correct === 'yes' ? 'yes' : 'no'}">${baseEffect.correct === 'yes' ? '对' : baseEffect.correct === 'no' ? '错' : '-'}</span>
                        </div>
                        <div class="compare-row">
                            <span class="compare-label">AI识别:</span>
                            <span class="compare-value ai">${escapeHtml(aiResult.userAnswer || '-')}</span>
                            <span class="compare-correct ${aiResult.correct === 'yes' ? 'yes' : 'no'}">${aiResult.correct === 'yes' ? '对' : aiResult.correct === 'no' ? '错' : '-'}</span>
                        </div>
                    </div>
                    ${q.explanation ? `<div class="item-explanation">${escapeHtml(q.explanation)}</div>` : ''}
                </div>
            `;
        }
        
        html += `</div>`;
        
        // 分页
        if (pagination.total_pages > 1) {
            html += renderTypeDetailPagination(pagination);
        }
    }
    
    container.innerHTML = html;
}

/**
 * 获取错误类型对应的CSS类
 */
function getErrorTypeClass(errorType) {
    const classMap = {
        '识别错误-判断正确': 'type-recognition-error',
        '识别错误-判断错误': 'type-both-error',
        '识别正确-判断错误': 'type-judgment-error',
        '识别题干-判断正确': 'type-stem',
        '识别差异-判断正确': 'type-fuzzy',
        '格式差异': 'type-format',
        '缺失题目': 'type-missing',
        'AI识别幻觉': 'type-hallucination'
    };
    return classMap[errorType] || 'type-default';
}

/**
 * 渲染分页组件
 */
function renderTypeDetailPagination(pagination) {
    const { page, total_pages } = pagination;
    
    let html = '<div class="type-detail-pagination">';
    
    // 上一页
    html += `<button class="pagination-btn" ${page <= 1 ? 'disabled' : ''} onclick="goTypeDetailPage(${page - 1})">上一页</button>`;
    
    // 页码
    const maxVisible = 5;
    let startPage = Math.max(1, page - Math.floor(maxVisible / 2));
    let endPage = Math.min(total_pages, startPage + maxVisible - 1);
    
    if (endPage - startPage < maxVisible - 1) {
        startPage = Math.max(1, endPage - maxVisible + 1);
    }
    
    if (startPage > 1) {
        html += `<button class="pagination-btn" onclick="goTypeDetailPage(1)">1</button>`;
        if (startPage > 2) {
            html += `<span class="pagination-ellipsis">...</span>`;
        }
    }
    
    for (let i = startPage; i <= endPage; i++) {
        html += `<button class="pagination-btn ${i === page ? 'active' : ''}" onclick="goTypeDetailPage(${i})">${i}</button>`;
    }
    
    if (endPage < total_pages) {
        if (endPage < total_pages - 1) {
            html += `<span class="pagination-ellipsis">...</span>`;
        }
        html += `<button class="pagination-btn" onclick="goTypeDetailPage(${total_pages})">${total_pages}</button>`;
    }
    
    // 下一页
    html += `<button class="pagination-btn" ${page >= total_pages ? 'disabled' : ''} onclick="goTypeDetailPage(${page + 1})">下一页</button>`;
    
    html += '</div>';
    return html;
}

/**
 * 切换分页
 */
function goTypeDetailPage(page) {
    typeDetailState.page = page;
    loadTypeDetailData();
}

/**
 * 筛选条件变化
 */
function onTypeDetailFilterChange() {
    const select = document.getElementById('typeDetailStatusFilter');
    if (select) {
        typeDetailState.status = select.value;
        typeDetailState.page = 1;
        loadTypeDetailData();
    }
}

/**
 * 关闭题目类型详情弹窗
 */
function hideTypeDetailModal() {
    hideModal('typeDetailModal');
}


// ========== 任务悬停气泡 ==========
let taskTooltipEl = null;
let taskTooltipPinned = false;
let currentTooltipTaskId = null;

/**
 * 初始化气泡元素
 */
function initTaskTooltip() {
    if (taskTooltipEl) return;
    
    taskTooltipEl = document.createElement('div');
    taskTooltipEl.className = 'task-tooltip';
    taskTooltipEl.innerHTML = `
        <div class="task-tooltip-header">
            <span class="task-tooltip-title">任务详情</span>
            <button class="task-tooltip-close" onclick="closeTaskTooltip()">&times;</button>
        </div>
        <div class="task-tooltip-body"></div>
        <div class="task-tooltip-remark" style="display:none;">
            <div class="task-tooltip-remark-title">备注</div>
            <div class="task-tooltip-remark-content"></div>
        </div>
    `;
    
    // 点击气泡固定显示
    taskTooltipEl.addEventListener('click', (e) => {
        if (e.target.closest('.task-tooltip-close')) return;
        pinTaskTooltip();
    });
    
    document.body.appendChild(taskTooltipEl);
}

/**
 * 显示任务气泡
 */
function showTaskTooltip(event, taskId) {
    if (taskTooltipPinned) return;
    
    initTaskTooltip();
    
    const task = taskList.find(t => t.task_id === taskId);
    if (!task) return;
    
    currentTooltipTaskId = taskId;
    
    // 构建内容
    const bodyEl = taskTooltipEl.querySelector('.task-tooltip-body');
    const remarkEl = taskTooltipEl.querySelector('.task-tooltip-remark');
    const remarkContentEl = taskTooltipEl.querySelector('.task-tooltip-remark-content');
    
    // 格式化创建时间
    const createdAt = task.created_at ? formatTime(task.created_at) : '-';
    
    // 构建测试条件汇总（测试条件|学科|学生数|每人作业数）
    let conditionParts = [];
    if (task.test_condition_name) conditionParts.push(task.test_condition_name);
    if (task.subject_name) conditionParts.push(task.subject_name);
    if (task.student_count > 0) conditionParts.push(`${task.student_count} 个学生`);
    if (task.homework_per_student > 0) conditionParts.push(`每人 ${task.homework_per_student} 份作业`);
    const conditionSummary = conditionParts.join(' | ');
    
    // 构建信息行
    let rows = `
        <div class="task-tooltip-row">
            <span class="task-tooltip-label">创建时间</span>
            <span class="task-tooltip-value">${createdAt}</span>
        </div>
    `;
    
    if (task.book_name) {
        rows += `
            <div class="task-tooltip-row">
                <span class="task-tooltip-label">书本名称</span>
                <span class="task-tooltip-value">${escapeHtml(task.book_name)}</span>
            </div>
        `;
    }
    
    if (task.page_range) {
        rows += `
            <div class="task-tooltip-row">
                <span class="task-tooltip-label">页码范围</span>
                <span class="task-tooltip-value">${escapeHtml(task.page_range)}</span>
            </div>
        `;
    }
    
    rows += `
        <div class="task-tooltip-row">
            <span class="task-tooltip-label">作业数量</span>
            <span class="task-tooltip-value">${task.homework_count || 0} 份</span>
        </div>
    `;
    
    // 测试条件汇总行
    if (conditionSummary) {
        rows += `
            <div class="task-tooltip-row">
                <span class="task-tooltip-label">测试条件</span>
                <span class="task-tooltip-value">${escapeHtml(conditionSummary)}</span>
            </div>
        `;
    }
    
    bodyEl.innerHTML = rows;
    
    // 备注区
    if (task.remark) {
        remarkContentEl.textContent = task.remark;
        remarkEl.style.display = 'block';
    } else {
        remarkEl.style.display = 'none';
    }
    
    // 定位气泡
    positionTooltip(event);
    
    // 显示气泡
    taskTooltipEl.classList.add('visible');
}

/**
 * 隐藏任务气泡
 */
function hideTaskTooltip() {
    if (taskTooltipPinned || !taskTooltipEl) return;
    taskTooltipEl.classList.remove('visible');
    currentTooltipTaskId = null;
}

/**
 * 固定气泡显示
 */
function pinTaskTooltip() {
    if (!taskTooltipEl) return;
    taskTooltipPinned = true;
    taskTooltipEl.classList.add('pinned');
}

/**
 * 关闭固定的气泡
 */
function closeTaskTooltip() {
    if (!taskTooltipEl) return;
    taskTooltipPinned = false;
    taskTooltipEl.classList.remove('pinned', 'visible');
    currentTooltipTaskId = null;
}

/**
 * 定位气泡（避免超出视口）
 */
function positionTooltip(event) {
    if (!taskTooltipEl) return;
    
    const rect = event.currentTarget.getBoundingClientRect();
    const tooltipWidth = 400;
    const tooltipHeight = taskTooltipEl.offsetHeight || 250;
    const padding = 12;
    
    let left = rect.right + padding;
    let top = rect.top;
    
    // 检查右侧是否有足够空间
    if (left + tooltipWidth > window.innerWidth) {
        left = rect.left - tooltipWidth - padding;
    }
    
    // 检查左侧是否有足够空间
    if (left < 0) {
        left = padding;
    }
    
    // 检查底部是否超出
    if (top + tooltipHeight > window.innerHeight) {
        top = window.innerHeight - tooltipHeight - padding;
    }
    
    // 检查顶部是否超出
    if (top < padding) {
        top = padding;
    }
    
    taskTooltipEl.style.left = left + 'px';
    taskTooltipEl.style.top = top + 'px';
}

// 点击页面其他地方关闭固定的气泡
document.addEventListener('click', (e) => {
    if (taskTooltipPinned && taskTooltipEl && !taskTooltipEl.contains(e.target) && !e.target.closest('.task-item')) {
        closeTaskTooltip();
    }
});


// ========== 任务备注编辑 ==========

/**
 * 显示备注编辑弹窗
 */
function showRemarkModal() {
    if (!selectedTask) return;
    
    const nameInput = document.getElementById('taskNameEditInput');
    const remarkInput = document.getElementById('remarkInput');
    
    if (nameInput) {
        nameInput.value = selectedTask.name || '';
    }
    if (remarkInput) {
        remarkInput.value = selectedTask.remark || '';
    }
    showModal('remarkModal');
}

/**
 * 保存任务信息（名称和备注）
 */
async function saveTaskInfo() {
    if (!selectedTask) return;
    
    const nameInput = document.getElementById('taskNameEditInput');
    const remarkInput = document.getElementById('remarkInput');
    
    const name = nameInput ? nameInput.value.trim() : '';
    const remark = remarkInput ? remarkInput.value.trim() : '';
    
    if (!name) {
        alert('任务名称不能为空');
        return;
    }
    
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/remark`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, remark })
        });
        
        const data = await res.json();
        if (data.success) {
            // 更新本地数据
            selectedTask.name = name;
            selectedTask.remark = remark;
            
            // 更新任务列表中的数据
            const taskInList = taskList.find(t => t.task_id === selectedTask.task_id);
            if (taskInList) {
                taskInList.name = name;
                taskInList.remark = remark;
            }
            
            // 更新显示
            document.getElementById('taskDetailTitle').textContent = name;
            const remarkText = document.getElementById('taskRemarkText');
            if (remarkText) {
                remarkText.textContent = remark;
            }
            
            // 刷新任务列表显示
            renderTaskList();
            
            hideModal('remarkModal');
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

// 兼容旧函数名
function saveTaskRemark() {
    saveTaskInfo();
}


// ========== 基准合集功能 ==========

// 当前编辑的合集ID（null表示新建）
let editingCollectionId = null;
// 当前合集中的数据集列表
let currentCollectionDatasets = [];
// 所有可用数据集列表（用于添加到合集）
let allDatasetsForCollection = [];
// 选中要添加到合集的数据集ID
let selectedDatasetsToAdd = [];

/**
 * 加载合集列表（用于快速选择）
 */
async function loadCollectionsForQuickSelect() {
    const container = document.getElementById('collectionSelectList');
    if (!container) return;
    
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-text">加载失败</div></div>`;
            return;
        }
        
        const collections = data.data || [];
        
        if (collections.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无合集，点击"管理合集"创建</div></div>';
            return;
        }
        
        container.innerHTML = collections.map(col => `
            <div class="collection-select-item" onclick="selectCollectionForTask('${col.collection_id}', '${escapeHtml(col.name)}')">
                <span class="collection-name">${escapeHtml(col.name)}</span>
                <span class="collection-count">${col.dataset_count || 0}个数据集</span>
            </div>
        `).join('');
    } catch (e) {
        console.error('加载合集列表失败:', e);
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 选择合集应用到当前任务
 */
async function selectCollectionForTask(collectionId, collectionName) {
    if (!selectedTask) {
        alert('请先选择任务');
        return;
    }
    
    // 先预览匹配结果
    try {
        showLoading('正在预览匹配结果...');
        
        const previewRes = await fetch(`/api/batch/collections/${collectionId}/match-preview?task_id=${selectedTask.task_id}`);
        const previewData = await previewRes.json();
        
        hideLoading();
        
        if (!previewData.success) {
            alert('预览失败: ' + (previewData.error || '未知错误'));
            return;
        }
        
        const preview = previewData.data;
        const confirmMsg = `合集"${collectionName}"匹配预览：\n\n` +
            `- 总作业数: ${preview.total_homework}\n` +
            `- 可匹配: ${preview.matched_count} 个\n` +
            `- 无法匹配: ${preview.unmatched_count} 个\n\n` +
            `确定应用此合集吗？`;
        
        if (!confirm(confirmMsg)) {
            return;
        }
        
        // 执行匹配
        showLoading('正在应用合集...');
        
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/select-collection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collection_id: collectionId })
        });
        
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            alert(`应用成功！\n匹配: ${data.matched_count} 个\n未匹配: ${data.unmatched_count} 个`);
            
            // 关闭弹窗并刷新任务详情
            hideModal('datasetSelectorModal');
            await loadTaskDetail(selectedTask.task_id);
        } else {
            alert('应用失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        console.error('应用合集失败:', e);
        alert('应用合集失败: ' + e.message);
    }
}

/**
 * 显示合集管理弹窗
 */
async function showCollectionManager() {
    showModal('collectionManagerModal');
    await loadCollectionManagerList();
}

/**
 * 加载合集管理列表
 */
async function loadCollectionManagerList() {
    const container = document.getElementById('collectionManagerList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-text">加载失败: ${escapeHtml(data.error)}</div></div>`;
            return;
        }
        
        const collections = data.data || [];
        
        if (collections.length === 0) {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无合集</div></div>';
            return;
        }
        
        container.innerHTML = collections.map(col => {
            const createdAt = col.created_at ? new Date(col.created_at).toLocaleDateString() : '-';
            return `
                <div class="collection-item">
                    <div class="collection-item-info">
                        <div class="collection-item-name">${escapeHtml(col.name)}</div>
                        <div class="collection-item-meta">
                            <span>${col.dataset_count || 0} 个数据集</span>
                            <span>创建于 ${createdAt}</span>
                        </div>
                        ${col.description ? `<div class="collection-item-meta">${escapeHtml(col.description)}</div>` : ''}
                    </div>
                    <div class="collection-item-actions">
                        <button class="btn btn-small btn-secondary" onclick="editCollection('${col.collection_id}')">编辑</button>
                        <button class="btn btn-small btn-danger" onclick="deleteCollection('${col.collection_id}', '${escapeHtml(col.name)}')">删除</button>
                    </div>
                </div>
            `;
        }).join('');
    } catch (e) {
        console.error('加载合集列表失败:', e);
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 显示新建合集弹窗
 */
function showCreateCollectionModal() {
    editingCollectionId = null;
    currentCollectionDatasets = [];
    
    document.getElementById('collectionEditTitle').textContent = '新建合集';
    document.getElementById('collectionNameInput').value = '';
    document.getElementById('collectionDescInput').value = '';
    
    renderCollectionDatasetsList();
    showModal('collectionEditModal');
}

/**
 * 编辑合集
 */
async function editCollection(collectionId) {
    try {
        showLoading('加载合集信息...');
        
        const res = await fetch(`/api/batch/collections/${collectionId}`);
        const data = await res.json();
        
        hideLoading();
        
        if (!data.success) {
            alert('加载失败: ' + (data.error || '未知错误'));
            return;
        }
        
        const collection = data.data;
        editingCollectionId = collectionId;
        currentCollectionDatasets = collection.datasets || [];
        
        document.getElementById('collectionEditTitle').textContent = '编辑合集';
        document.getElementById('collectionNameInput').value = collection.name || '';
        document.getElementById('collectionDescInput').value = collection.description || '';
        
        renderCollectionDatasetsList();
        showModal('collectionEditModal');
    } catch (e) {
        hideLoading();
        console.error('加载合集失败:', e);
        alert('加载合集失败: ' + e.message);
    }
}

/**
 * 渲染合集中的数据集列表
 */
function renderCollectionDatasetsList() {
    const container = document.getElementById('collectionDatasetsList');
    
    if (currentCollectionDatasets.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集，点击下方按钮添加</div></div>';
        return;
    }
    
    container.innerHTML = currentCollectionDatasets.map(ds => {
        const pagesStr = Array.isArray(ds.pages) ? `P${ds.pages.join(',')}` : '';
        return `
            <div class="collection-dataset-item">
                <div class="collection-dataset-info">
                    <div class="collection-dataset-name">${escapeHtml(ds.name || ds.dataset_id)}</div>
                    <div class="collection-dataset-meta">${escapeHtml(ds.book_name || '')} ${pagesStr} (${ds.question_count || 0}题)</div>
                </div>
                <button class="btn-remove-dataset" onclick="removeDatasetFromCurrentCollection('${ds.dataset_id}')">移除</button>
            </div>
        `;
    }).join('');
}

/**
 * 从当前编辑的合集中移除数据集
 */
function removeDatasetFromCurrentCollection(datasetId) {
    currentCollectionDatasets = currentCollectionDatasets.filter(ds => ds.dataset_id !== datasetId);
    renderCollectionDatasetsList();
}

/**
 * 保存合集
 */
async function saveCollection() {
    const name = document.getElementById('collectionNameInput').value.trim();
    const description = document.getElementById('collectionDescInput').value.trim();
    
    if (!name) {
        alert('请输入合集名称');
        return;
    }
    
    try {
        showLoading('保存中...');
        
        if (editingCollectionId) {
            // 更新合集
            const updateRes = await fetch(`/api/batch/collections/${editingCollectionId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description })
            });
            
            const updateData = await updateRes.json();
            if (!updateData.success) {
                hideLoading();
                alert('保存失败: ' + (updateData.error || '未知错误'));
                return;
            }
            
            // 更新数据集列表（先获取当前的，对比差异）
            const currentRes = await fetch(`/api/batch/collections/${editingCollectionId}`);
            const currentData = await currentRes.json();
            const existingIds = new Set((currentData.data?.datasets || []).map(ds => ds.dataset_id));
            const newIds = new Set(currentCollectionDatasets.map(ds => ds.dataset_id));
            
            // 添加新的
            const toAdd = currentCollectionDatasets.filter(ds => !existingIds.has(ds.dataset_id)).map(ds => ds.dataset_id);
            if (toAdd.length > 0) {
                await fetch(`/api/batch/collections/${editingCollectionId}/datasets`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ dataset_ids: toAdd })
                });
            }
            
            // 移除旧的
            for (const ds of (currentData.data?.datasets || [])) {
                if (!newIds.has(ds.dataset_id)) {
                    await fetch(`/api/batch/collections/${editingCollectionId}/datasets/${ds.dataset_id}`, {
                        method: 'DELETE'
                    });
                }
            }
        } else {
            // 创建新合集
            const createRes = await fetch('/api/batch/collections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    dataset_ids: currentCollectionDatasets.map(ds => ds.dataset_id)
                })
            });
            
            const createData = await createRes.json();
            if (!createData.success) {
                hideLoading();
                alert('创建失败: ' + (createData.error || '未知错误'));
                return;
            }
        }
        
        hideLoading();
        hideModal('collectionEditModal');
        
        // 刷新列表
        await loadCollectionManagerList();
        await loadCollectionsForQuickSelect();
        
        alert('保存成功');
    } catch (e) {
        hideLoading();
        console.error('保存合集失败:', e);
        alert('保存失败: ' + e.message);
    }
}

/**
 * 删除合集
 */
async function deleteCollection(collectionId, collectionName) {
    if (!confirm(`确定要删除合集"${collectionName}"吗？\n\n注意：这不会删除合集中的数据集，只是解除关联。`)) {
        return;
    }
    
    try {
        showLoading('删除中...');
        
        const res = await fetch(`/api/batch/collections/${collectionId}`, {
            method: 'DELETE'
        });
        
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            await loadCollectionManagerList();
            await loadCollectionsForQuickSelect();
            alert('删除成功');
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        console.error('删除合集失败:', e);
        alert('删除失败: ' + e.message);
    }
}

/**
 * 显示添加数据集到合集的弹窗
 */
async function showAddDatasetToCollectionModal() {
    selectedDatasetsToAdd = [];
    document.getElementById('datasetSearchInput').value = '';
    
    showModal('addDatasetToCollectionModal');
    await loadAllDatasetsForCollection();
}

/**
 * 加载所有数据集（用于添加到合集）
 */
async function loadAllDatasetsForCollection() {
    const container = document.getElementById('datasetAddList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/datasets');
        const data = await res.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="empty-state"><div class="empty-state-text">加载失败</div></div>`;
            return;
        }
        
        allDatasetsForCollection = data.data || [];
        renderDatasetsForCollection();
    } catch (e) {
        console.error('加载数据集失败:', e);
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 渲染可添加的数据集列表
 */
function renderDatasetsForCollection() {
    const container = document.getElementById('datasetAddList');
    const searchText = (document.getElementById('datasetSearchInput')?.value || '').toLowerCase();
    
    // 过滤已在合集中的数据集
    const existingIds = new Set(currentCollectionDatasets.map(ds => ds.dataset_id));
    let datasets = allDatasetsForCollection.filter(ds => !existingIds.has(ds.dataset_id));
    
    // 搜索过滤
    if (searchText) {
        datasets = datasets.filter(ds => 
            (ds.name || '').toLowerCase().includes(searchText) ||
            (ds.book_name || '').toLowerCase().includes(searchText)
        );
    }
    
    if (datasets.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">没有可添加的数据集</div></div>';
        return;
    }
    
    container.innerHTML = datasets.map(ds => {
        const isSelected = selectedDatasetsToAdd.includes(ds.dataset_id);
        const pagesStr = Array.isArray(ds.pages) ? `P${ds.pages.join(',')}` : '';
        return `
            <div class="dataset-add-item ${isSelected ? 'selected' : ''}" onclick="toggleDatasetToAdd('${ds.dataset_id}')">
                <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleDatasetToAdd('${ds.dataset_id}')">
                <div class="dataset-add-info">
                    <div class="dataset-add-name">${escapeHtml(ds.name || ds.dataset_id)}</div>
                    <div class="dataset-add-meta">${escapeHtml(ds.book_name || '')} ${pagesStr} (${ds.question_count || 0}题)</div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 切换选择要添加的数据集
 */
function toggleDatasetToAdd(datasetId) {
    const index = selectedDatasetsToAdd.indexOf(datasetId);
    if (index >= 0) {
        selectedDatasetsToAdd.splice(index, 1);
    } else {
        selectedDatasetsToAdd.push(datasetId);
    }
    renderDatasetsForCollection();
}

/**
 * 过滤数据集列表
 */
function filterDatasetsForCollection() {
    renderDatasetsForCollection();
}

/**
 * 确认添加数据集到合集
 */
function confirmAddDatasetsToCollection() {
    if (selectedDatasetsToAdd.length === 0) {
        alert('请选择要添加的数据集');
        return;
    }
    
    // 将选中的数据集添加到当前合集
    for (const dsId of selectedDatasetsToAdd) {
        const ds = allDatasetsForCollection.find(d => d.dataset_id === dsId);
        if (ds && !currentCollectionDatasets.find(d => d.dataset_id === dsId)) {
            currentCollectionDatasets.push({
                dataset_id: ds.dataset_id,
                name: ds.name,
                book_id: ds.book_id,
                book_name: ds.book_name,
                pages: ds.pages,
                question_count: ds.question_count
            });
        }
    }
    
    selectedDatasetsToAdd = [];
    hideModal('addDatasetToCollectionModal');
    renderCollectionDatasetsList();
}

// 修改原有的 showDatasetSelector 函数，添加合集加载
const originalShowDatasetSelector = typeof showDatasetSelector === 'function' ? showDatasetSelector : null;

// 在数据集选择弹窗显示时加载合集列表
document.addEventListener('DOMContentLoaded', function() {
    // 监听数据集选择弹窗显示
    const datasetModal = document.getElementById('datasetSelectorModal');
    if (datasetModal) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'style' || mutation.attributeName === 'class') {
                    const isVisible = datasetModal.style.display !== 'none' && 
                                     !datasetModal.classList.contains('hidden');
                    if (isVisible) {
                        loadCollectionsForQuickSelect();
                    }
                }
            });
        });
        observer.observe(datasetModal, { attributes: true });
    }
});


// ========== 一键应用合集功能 ==========

let selectedApplyCollectionId = null;

/**
 * 显示一键应用合集弹窗
 */
function showApplyCollectionModal() {
    if (!currentTaskId) {
        alert('请先选择一个任务');
        return;
    }
    
    selectedApplyCollectionId = null;
    document.getElementById('applyCollectionPreview').style.display = 'none';
    document.getElementById('confirmApplyCollectionBtn').disabled = true;
    
    showModal('applyCollectionModal');
    loadCollectionsForApply();
}

/**
 * 加载合集列表（用于一键应用）
 */
async function loadCollectionsForApply() {
    const container = document.getElementById('applyCollectionList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (data.success) {
            renderCollectionsForApply(data.data || []);
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

/**
 * 渲染合集列表（用于一键应用）
 */
function renderCollectionsForApply(collections) {
    const container = document.getElementById('applyCollectionList');
    
    if (!collections || collections.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-text">暂无合集</div>
                <button class="btn btn-secondary btn-small" onclick="hideModal('applyCollectionModal'); showCollectionManager();" style="margin-top: 12px;">去创建合集</button>
            </div>
        `;
        return;
    }
    
    container.innerHTML = collections.map(col => `
        <div class="apply-collection-item ${selectedApplyCollectionId === col.collection_id ? 'selected' : ''}" 
             onclick="selectCollectionForApply('${col.collection_id}')">
            <div class="apply-collection-item-info">
                <div class="apply-collection-item-name">${escapeHtml(col.name)}</div>
                <div class="apply-collection-item-meta">
                    ${col.dataset_count || 0} 个数据集
                    ${col.description ? ' · ' + escapeHtml(col.description.substring(0, 40)) + (col.description.length > 40 ? '...' : '') : ''}
                </div>
            </div>
            <div class="apply-collection-item-check"></div>
        </div>
    `).join('');
}

/**
 * 选择要应用的合集
 */
async function selectCollectionForApply(collectionId) {
    selectedApplyCollectionId = collectionId;
    
    // 更新选中状态
    document.querySelectorAll('.apply-collection-item').forEach(item => {
        item.classList.remove('selected');
    });
    event.currentTarget.classList.add('selected');
    
    // 加载匹配预览
    await loadApplyCollectionPreview(collectionId);
}

/**
 * 加载合集匹配预览
 */
async function loadApplyCollectionPreview(collectionId) {
    const previewEl = document.getElementById('applyCollectionPreview');
    const confirmBtn = document.getElementById('confirmApplyCollectionBtn');
    
    previewEl.style.display = 'block';
    document.getElementById('previewMatchedCount').textContent = '...';
    document.getElementById('previewUnmatchedCount').textContent = '...';
    confirmBtn.disabled = true;
    
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}/match-preview?task_id=${currentTaskId}`);
        const data = await res.json();
        
        if (data.success && data.data) {
            document.getElementById('previewMatchedCount').textContent = data.data.matched_count || 0;
            document.getElementById('previewUnmatchedCount').textContent = data.data.unmatched_count || 0;
            
            // 只有有匹配的才能应用
            confirmBtn.disabled = (data.data.matched_count || 0) === 0;
        } else {
            document.getElementById('previewMatchedCount').textContent = '0';
            document.getElementById('previewUnmatchedCount').textContent = '-';
        }
    } catch (e) {
        console.error('加载匹配预览失败:', e);
        document.getElementById('previewMatchedCount').textContent = '-';
        document.getElementById('previewUnmatchedCount').textContent = '-';
    }
}

/**
 * 确认应用合集
 */
async function confirmApplyCollection() {
    if (!selectedApplyCollectionId || !currentTaskId) {
        return;
    }
    
    const confirmBtn = document.getElementById('confirmApplyCollectionBtn');
    confirmBtn.disabled = true;
    confirmBtn.textContent = '应用中...';
    
    try {
        const res = await fetch(`/api/batch/tasks/${currentTaskId}/select-collection`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ collection_id: selectedApplyCollectionId })
        });
        
        const data = await res.json();
        
        if (data.success) {
            hideModal('applyCollectionModal');
            
            // 刷新任务详情
            loadTaskDetail(currentTaskId);
            
            alert(`合集应用成功！\n匹配: ${data.matched_count} 个作业\n未匹配: ${data.unmatched_count} 个作业`);
        } else {
            alert('应用失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('应用失败: ' + e.message);
    } finally {
        confirmBtn.disabled = false;
        confirmBtn.textContent = '应用合集';
    }
}


// ========== 任务创建时关联合集 ==========

/**
 * 加载合集列表（用于任务创建）
 */
async function loadCollectionsForTaskCreate() {
    const select = document.getElementById('taskCollectionSelect');
    if (!select) return;
    
    select.innerHTML = '<option value="">不使用合集</option><option value="" disabled>加载中...</option>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        select.innerHTML = '<option value="">不使用合集</option>';
        
        if (data.success && data.data) {
            data.data.forEach(col => {
                const option = document.createElement('option');
                option.value = col.collection_id;
                option.textContent = `${col.name} (${col.dataset_count || 0}个数据集)`;
                select.appendChild(option);
            });
        }
    } catch (e) {
        console.error('加载合集列表失败:', e);
        select.innerHTML = '<option value="">不使用合集</option>';
    }
}

/**
 * 刷新合集列表
 */
function refreshCollectionsForTask() {
    loadCollectionsForTaskCreate();
}

/**
 * 合集选择变化
 */
function onTaskCollectionChange() {
    // 可以在这里添加预览逻辑
}

// 在显示创建任务弹窗时加载合集
const originalShowCreateTaskModal = typeof showCreateTaskModal === 'function' ? showCreateTaskModal : null;

// ========== 显示任务已应用的合集 ==========

/**
 * 更新任务详情中的合集显示
 */
function updateTaskCollectionDisplay(taskData) {
    const row = document.getElementById('taskCollectionRow');
    const nameEl = document.getElementById('taskCollectionName');
    
    if (!row || !nameEl) return;
    
    // 检查任务中是否有应用合集的作业
    const homeworkItems = taskData.homework_items || [];
    const collectionNames = new Set();
    
    homeworkItems.forEach(item => {
        if (item.matched_collection_name) {
            collectionNames.add(item.matched_collection_name);
        }
    });
    
    if (collectionNames.size > 0) {
        nameEl.textContent = [...collectionNames].join(', ');
        row.style.display = 'flex';
    } else {
        row.style.display = 'none';
    }
}

// ========== 从当前任务创建合集 ==========

let taskMatchedDatasets = [];  // 当前任务已匹配的数据集

/**
 * 显示一键应用合集弹窗（增强版）
 */
const originalShowApplyCollectionModal = showApplyCollectionModal;
showApplyCollectionModal = async function() {
    if (!currentTaskId) {
        alert('请先选择一个任务');
        return;
    }
    
    selectedApplyCollectionId = null;
    document.getElementById('applyCollectionPreview').style.display = 'none';
    document.getElementById('confirmApplyCollectionBtn').disabled = true;
    
    showModal('applyCollectionModal');
    loadCollectionsForApply();
    
    // 检查当前任务已匹配的数据集
    await checkTaskMatchedDatasets();
};

/**
 * 检查当前任务已匹配的数据集
 */
async function checkTaskMatchedDatasets() {
    const createSection = document.getElementById('createCollectionFromTask');
    const countEl = document.getElementById('taskMatchedDatasetCount');
    
    if (!createSection || !countEl) return;
    
    try {
        const res = await fetch(`/api/batch/tasks/${currentTaskId}`);
        const data = await res.json();
        
        if (data.success && data.task) {
            const homeworkItems = data.task.homework_items || [];
            const datasetIds = new Set();
            
            homeworkItems.forEach(item => {
                if (item.matched_dataset) {
                    datasetIds.add(item.matched_dataset);
                }
            });
            
            taskMatchedDatasets = [...datasetIds];
            
            if (taskMatchedDatasets.length > 0) {
                countEl.textContent = homeworkItems.filter(item => item.matched_dataset).length;
                createSection.style.display = 'block';
            } else {
                createSection.style.display = 'none';
            }
        }
    } catch (e) {
        console.error('检查任务数据集失败:', e);
        createSection.style.display = 'none';
    }
}

/**
 * 显示从当前任务创建合集弹窗
 */
function showCreateCollectionFromTaskModal() {
    if (taskMatchedDatasets.length === 0) {
        alert('当前任务没有已匹配的数据集');
        return;
    }
    
    document.getElementById('newCollectionFromTaskName').value = '';
    document.getElementById('newCollectionFromTaskDesc').value = '';
    document.getElementById('newCollectionDatasetCount').textContent = taskMatchedDatasets.length;
    
    showModal('createCollectionFromTaskModal');
}

/**
 * 确认从当前任务创建合集
 */
async function confirmCreateCollectionFromTask() {
    const name = document.getElementById('newCollectionFromTaskName').value.trim();
    const desc = document.getElementById('newCollectionFromTaskDesc').value.trim();
    
    if (!name) {
        alert('请输入合集名称');
        return;
    }
    
    if (taskMatchedDatasets.length === 0) {
        alert('没有可添加的数据集');
        return;
    }
    
    try {
        const res = await fetch('/api/batch/collections', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                name: name,
                description: desc,
                dataset_ids: taskMatchedDatasets
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            hideModal('createCollectionFromTaskModal');
            hideModal('applyCollectionModal');
            alert(`合集"${name}"创建成功，包含 ${taskMatchedDatasets.length} 个数据集`);
        } else {
            alert('创建失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('创建失败: ' + e.message);
    }
}

// 初始化：在创建任务弹窗显示时加载合集
document.addEventListener('DOMContentLoaded', function() {
    const createTaskModal = document.getElementById('createTaskModal');
    if (createTaskModal) {
        const observer = new MutationObserver(function(mutations) {
            mutations.forEach(function(mutation) {
                if (mutation.attributeName === 'class') {
                    if (createTaskModal.classList.contains('show')) {
                        loadCollectionsForTaskCreate();
                    }
                }
            });
        });
        observer.observe(createTaskModal, { attributes: true });
    }
});
