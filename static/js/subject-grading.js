/**
 * AI 学科批改评估页面 JavaScript
 */

// ========== 全局状态 ==========
let currentSubject = 0;
let homeworkList = [];
let selectedHomework = null;
let baseEffect = [];
let evaluationResult = null;
let uploadedImage = null;
let currentResultData = []; // 当前批改结果数据
let currentQuestionFilter = 'all'; // 当前题型筛选
let currentTaskId = ''; // 当前选中的作业任务ID
let taskList = []; // 作业任务列表

// 学科配置
const SUBJECTS = {
    0: { id: 0, name: '英语' },
    1: { id: 1, name: '语文' },
    2: { id: 2, name: '数学' },
    3: { id: 3, name: '物理' }
};

// 图表实例
let chartInstances = {
    errorPie: null,
    radar: null,
    questionBar: null,
    severityBar: null,
    deviationChart: null,
    historyTrend: null
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    setupImageUpload();
    loadHomeworkTasks();
    loadHomeworkData();
});

// ========== 返回导航 ==========
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// ========== 学科切换 ==========
function switchSubject(subjectId) {
    document.querySelectorAll('.tab').forEach((tab, i) => {
        tab.classList.toggle('active', i === (subjectId === -1 ? 4 : subjectId));
    });
    
    if (subjectId === -1) {
        document.getElementById('dataListSection').style.display = 'none';
        document.getElementById('selectedDataSection').style.display = 'none';
        document.getElementById('historyContent').style.display = 'block';
        hideRightPanelSections();
        document.getElementById('emptyRightPanel').style.display = 'flex';
        loadHistory();
    } else {
        document.getElementById('dataListSection').style.display = 'block';
        document.getElementById('historyContent').style.display = 'none';
        currentSubject = subjectId;
        resetState();
        loadHomeworkTasks();
        loadHomeworkData();
    }
}

// ========== 重置状态 ==========
function resetState() {
    selectedHomework = null;
    baseEffect = [];
    evaluationResult = null;
    uploadedImage = null;
    currentTaskId = '';
    
    document.getElementById('selectedDataSection').style.display = 'none';
    hideRightPanelSections();
    document.getElementById('emptyRightPanel').style.display = 'flex';
    
    document.getElementById('previewBox').style.display = 'none';
    document.getElementById('uploadArea').classList.remove('has-file');
    document.getElementById('questionCards').innerHTML = '';
    
    // 重置任务选择
    document.querySelectorAll('.task-item').forEach(item => {
        item.classList.toggle('active', item.dataset.taskId === '');
    });
    
    destroyCharts();
}

function hideRightPanelSections() {
    document.getElementById('aiResultSection').style.display = 'none';
    document.getElementById('baseEffectSection').style.display = 'none';
    document.getElementById('evaluateSection').style.display = 'none';
    document.getElementById('resultSection').style.display = 'none';
}

// ========== 加载批改数据 ==========
async function loadHomeworkData() {
    showLoading('正在加载批改数据...');
    
    const hours = document.getElementById('timeRangeFilter')?.value || 1;
    
    try {
        let url = `/api/grading/homework?subject_id=${currentSubject}&hours=${hours}`;
        if (currentTaskId) {
            url += `&hw_publish_id=${currentTaskId}`;
        }
        
        const res = await fetch(url);
        const data = await res.json();
        
        if (data.success) {
            homeworkList = data.data || [];
            renderHomeworkList();
        } else {
            showError('加载失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        showError('请求失败: ' + e.message);
    }
    
    hideLoading();
}

// ========== 加载作业任务列表 ==========
async function loadHomeworkTasks() {
    try {
        const res = await fetch(`/api/grading/homework-tasks?subject_id=${currentSubject}&hours=168`);
        const data = await res.json();
        
        if (data.success) {
            taskList = data.data || [];
            renderTaskList();
        }
    } catch (e) {
        console.error('加载作业任务失败:', e);
    }
}

// ========== 渲染作业任务列表 ==========
function renderTaskList() {
    const container = document.getElementById('taskList');
    
    let html = `
        <div class="task-item ${currentTaskId === '' ? 'active' : ''}" data-task-id="" onclick="selectTask(this, '')">
            <span class="task-name">全部作业</span>
        </div>
    `;
    
    if (taskList.length > 0) {
        html += taskList.map(task => `
            <div class="task-item ${currentTaskId == task.hw_publish_id ? 'active' : ''}" 
                 data-task-id="${task.hw_publish_id}" 
                 onclick="selectTask(this, '${task.hw_publish_id}')">
                <span class="task-name">${escapeHtml(task.task_name || '未命名任务')}</span>
                <span class="task-count">${task.homework_count || 0}</span>
            </div>
        `).join('');
    }
    
    container.innerHTML = html;
}

// ========== 选择作业任务 ==========
function selectTask(element, taskId) {
    currentTaskId = taskId;
    
    // 更新选中状态
    document.querySelectorAll('.task-item').forEach(item => {
        item.classList.toggle('active', item.dataset.taskId === taskId);
    });
    
    // 重新加载数据
    loadHomeworkData();
}

// ========== 渲染批改数据列表 ==========
function renderHomeworkList() {
    const container = document.getElementById('dataList');
    const countEl = document.getElementById('dataCount');
    
    countEl.textContent = `共 ${homeworkList.length} 条记录`;
    
    // 更新批量模式UI
    if (BatchEvaluation && BatchEvaluation.enabled) {
        document.querySelector('.data-list-container')?.classList.add('batch-mode');
    } else {
        document.querySelector('.data-list-container')?.classList.remove('batch-mode');
    }
    
    if (homeworkList.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">--</div>
                <div class="empty-state-text">暂无批改数据</div>
            </div>
        `;
        return;
    }
    
    const isBatchMode = BatchEvaluation && BatchEvaluation.enabled;
    
    container.innerHTML = homeworkList.map((item, index) => {
        const isSelected = selectedHomework?.id === item.id;
        const isBatchSelected = isBatchMode && BatchEvaluation.selectedItems.has(index);
        
        return `
            <div class="data-item ${isSelected ? 'selected' : ''} ${isBatchSelected ? 'batch-selected' : ''}" 
                 data-index="${index}"
                 onclick="${isBatchMode ? `BatchEvaluation.toggleItem(${index})` : `selectHomework(${index})`}">
                ${isBatchMode ? `
                    <div class="batch-checkbox-wrap">
                        <input type="checkbox" class="batch-checkbox" ${isBatchSelected ? 'checked' : ''} 
                               onclick="event.stopPropagation(); BatchEvaluation.toggleItem(${index})">
                    </div>
                ` : ''}
                <div class="data-item-info">
                    <div class="data-item-title">${escapeHtml(item.homework_name || '未知作业')}</div>
                    <div class="data-item-meta">
                        ${escapeHtml(item.student_name || item.student_id || '-')} | 页码: ${item.page_num || '-'} | ${formatTime(item.create_time)}
                    </div>
                </div>
                <div class="data-item-count">${item.question_count || 0} 题</div>
            </div>
        `;
    }).join('');
}

// ========== 选择批改记录 ==========
function selectHomework(index) {
    selectedHomework = homeworkList[index];
    
    document.querySelectorAll('.data-item').forEach((item, i) => {
        item.classList.toggle('selected', i === index);
    });
    
    document.getElementById('selectedDataSection').style.display = 'block';
    document.getElementById('emptyRightPanel').style.display = 'none';
    document.getElementById('baseEffectSection').style.display = 'block';
    document.getElementById('evaluateSection').style.display = 'block';
    
    renderSelectedData();
    
    // 尝试自动加载已保存的基准效果
    loadSavedBaseEffect();
}

// ========== 渲染选中数据详情 ==========
function renderSelectedData() {
    if (!selectedHomework) return;
    
    // 构建图片预览HTML
    const picPath = selectedHomework.pic_path || '';
    const thumbnailHtml = picPath ? `
        <div class="thumbnail-preview" onclick="showCompareMode()">
            <img src="${picPath}" alt="作业图片" onerror="this.parentElement.style.display='none'">
            <div class="thumbnail-hint">详细比对</div>
        </div>
    ` : '';
    
    const infoHtml = `
        ${thumbnailHtml}
        <div class="info-item">
            <div class="info-label">学生</div>
            <div class="info-value">${selectedHomework.student_name || selectedHomework.student_id || '-'}</div>
        </div>
        <div class="info-item">
            <div class="info-label">作业</div>
            <div class="info-value">${selectedHomework.homework_name || selectedHomework.hw_publish_id || '-'}</div>
        </div>
        <div class="info-item">
            <div class="info-label">页码</div>
            <div class="info-value">${selectedHomework.page_num || '-'}</div>
        </div>
        <div class="info-item">
            <div class="info-label">题目数量</div>
            <div class="info-value">${selectedHomework.question_count || 0}</div>
        </div>
        <div class="info-item">
            <div class="info-label">创建时间</div>
            <div class="info-value">${formatTime(selectedHomework.create_time)}</div>
        </div>
    `;
    document.getElementById('selectedDataInfo').innerHTML = infoHtml;
    
    // 隐藏大图预览
    document.getElementById('largeImagePreview').style.display = 'none';
    
    // 在右侧渲染AI批改结果表格
    let resultData = [];
    try {
        resultData = JSON.parse(selectedHomework.homework_result || '[]');
    } catch (e) {
        resultData = [];
    }
    
    currentResultData = resultData; // 保存原始数据
    currentQuestionFilter = 'all'; // 重置筛选
    updateFilterButtons('all');
    
    document.getElementById('aiResultSection').style.display = 'block';
    renderFilteredTable(resultData);
}

// ========== 显示比对模式 ==========
let imageScale = 0.6; // 初始缩放比例60%
let originalMainLayoutHtml = null; // 保存原始布局HTML

function showCompareMode() {
    if (!selectedHomework || !selectedHomework.pic_path) return;
    
    // 获取主布局容器
    const mainLayout = document.querySelector('.main-layout');
    
    // 保存原始HTML以便退出时恢复
    if (!originalMainLayoutHtml) {
        originalMainLayoutHtml = mainLayout.innerHTML;
    }
    
    // 替换整个布局为比对模式
    mainLayout.innerHTML = `
        <div class="compare-layout">
            <div class="compare-left" id="compareLeft">
                <div class="compare-mode-panel">
                    <div class="compare-header">
                        <h3>AI批改结果</h3>
                        <button class="btn-small" onclick="exitCompareMode()">退出比对</button>
                    </div>
                    <div class="filter-btns-compare">
                        <button class="filter-btn active" data-filter="all" onclick="filterQuestionType('all')">全部</button>
                        <button class="filter-btn" data-filter="choice" onclick="filterQuestionType('choice')">选择题</button>
                        <button class="filter-btn" data-filter="non-choice" onclick="filterQuestionType('non-choice')">非选择题</button>
                    </div>
                    <div class="compare-table-wrap" id="compareTableWrap"></div>
                </div>
            </div>
            <div class="resize-handle" id="resizeHandle"></div>
            <div class="compare-right" id="compareRight">
                <div class="compare-image-panel">
                    <div class="compare-header">
                        <h3>作业图片</h3>
                        <div class="zoom-controls">
                            <button class="btn-small" onclick="zoomOut()">-</button>
                            <span id="zoomLevel">60%</span>
                            <button class="btn-small" onclick="zoomIn()">+</button>
                            <button class="btn-small" onclick="resetZoom()">重置</button>
                        </div>
                    </div>
                    <div class="compare-image-wrap">
                        <img id="compareImage" src="${selectedHomework.pic_path}" alt="作业图片" style="width: 60%;">
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 重置缩放
    imageScale = 0.6;
    
    // 渲染表格
    updateFilterButtons('all');
    document.getElementById('compareTableWrap').innerHTML = renderResultTable(currentResultData);
    
    // 初始化拖拽功能
    initResizeHandle();
}

// ========== 初始化拖拽分隔条 ==========
function initResizeHandle() {
    const handle = document.getElementById('resizeHandle');
    const leftPanel = document.getElementById('compareLeft');
    const rightPanel = document.getElementById('compareRight');
    const container = document.querySelector('.compare-layout');
    
    let isResizing = false;
    
    handle.addEventListener('mousedown', (e) => {
        isResizing = true;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    });
    
    document.addEventListener('mousemove', (e) => {
        if (!isResizing) return;
        
        const containerRect = container.getBoundingClientRect();
        const newLeftWidth = e.clientX - containerRect.left;
        const containerWidth = containerRect.width;
        
        // 限制最小宽度
        const minWidth = 300;
        const maxWidth = containerWidth - 300;
        
        if (newLeftWidth >= minWidth && newLeftWidth <= maxWidth) {
            const leftPercent = (newLeftWidth / containerWidth) * 100;
            leftPanel.style.width = leftPercent + '%';
            rightPanel.style.width = (100 - leftPercent) + '%';
        }
    });
    
    document.addEventListener('mouseup', () => {
        isResizing = false;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    });
}

// ========== 缩放控制 ==========
function zoomIn() {
    imageScale = Math.min(imageScale + 0.1, 2); // 最大200%
    updateImageScale();
}

function zoomOut() {
    imageScale = Math.max(imageScale - 0.1, 0.3); // 最小30%
    updateImageScale();
}

function resetZoom() {
    imageScale = 0.6;
    updateImageScale();
}

function updateImageScale() {
    const img = document.getElementById('compareImage');
    const zoomLevel = document.getElementById('zoomLevel');
    if (img) {
        img.style.width = (imageScale * 100) + '%';
    }
    if (zoomLevel) {
        zoomLevel.textContent = Math.round(imageScale * 100) + '%';
    }
}

// ========== 退出比对模式 ==========
function exitCompareMode() {
    // 恢复原始布局
    if (originalMainLayoutHtml) {
        const mainLayout = document.querySelector('.main-layout');
        mainLayout.innerHTML = originalMainLayoutHtml;
        originalMainLayoutHtml = null;
        
        // 重新渲染当前选中的作业详情
        if (selectedHomework) {
            renderHomeworkDetail(selectedHomework);
        }
    }
}

// ========== 显示大图 ==========
function showLargeImage(imagePath) {
    document.getElementById('largeImage').src = imagePath;
    document.getElementById('largeImagePreview').style.display = 'block';
}

// ========== 关闭大图 ==========
function closeLargeImage() {
    document.getElementById('largeImagePreview').style.display = 'none';
}

// ========== 渲染批改结果表格 ==========
// JSON结构: {"answer":"A","correct":"yes","index":"13","tempIndex":0,"userAnswer":"A"}
function renderResultTable(data) {
    if (!data || data.length === 0) return '<div class="empty-hint">暂无数据</div>';
    
    let html = `
        <table class="result-table-simple">
            <thead>
                <tr>
                    <th>题号</th>
                    <th>标准答案</th>
                    <th>学生答案</th>
                    <th>结果</th>
                </tr>
            </thead>
            <tbody>
    `;
    
    data.forEach((item) => {
        const index = item.index || item.tempIndex || '-';
        // 标准答案：优先取 answer，没有则取 mainAnswer
        const answer = item.answer || item.mainAnswer || '-';
        const userAnswer = item.userAnswer || '-';
        const correct = item.correct;
        
        // 判断正确/错误状态
        let statusClass = '';
        let statusText = '-';
        if (correct === 'yes' || correct === true || correct === 1) {
            statusClass = 'status-correct';
            statusText = '✓';
        } else if (correct === 'no' || correct === false || correct === 0) {
            statusClass = 'status-wrong';
            statusText = '✗';
        } else if (correct === 'partial') {
            statusClass = 'status-partial';
            statusText = '△';
        }
        
        html += `
            <tr class="${statusClass}">
                <td class="col-no">${index}</td>
                <td class="col-std">${escapeHtml(String(answer))}</td>
                <td class="col-user">${escapeHtml(String(userAnswer))}</td>
                <td class="col-result ${statusClass}">${statusText}</td>
            </tr>
        `;
    });
    
    html += '</tbody></table>';
    return html;
}

// ========== 渲染筛选后的表格 ==========
function renderFilteredTable(data) {
    const tableWrap = document.getElementById('aiResultTableWrap');
    if (Array.isArray(data) && data.length > 0) {
        tableWrap.innerHTML = renderResultTable(data);
    } else {
        tableWrap.innerHTML = '<div class="empty-hint">暂无批改数据</div>';
    }
}

// ========== 题型筛选 ==========
function filterQuestionType(type) {
    currentQuestionFilter = type;
    updateFilterButtons(type);
    
    if (!currentResultData || currentResultData.length === 0) return;
    
    let filteredData = currentResultData;
    
    if (type === 'choice') {
        // 选择题：答案是单个大写字母 A/B/C/D（或多选如AB、ABC）
        filteredData = currentResultData.filter(item => {
            const answer = (item.answer || item.mainAnswer || '').toString().trim().toUpperCase();
            // 只匹配1-4个字母且都是A-D范围内的选项
            return /^[A-D]{1,4}$/.test(answer);
        });
    } else if (type === 'non-choice') {
        // 非选择题：不是选择题选项的都算非选择题
        filteredData = currentResultData.filter(item => {
            const answer = (item.answer || item.mainAnswer || '').toString().trim().toUpperCase();
            return !/^[A-D]{1,4}$/.test(answer);
        });
    }
    
    renderFilteredTable(filteredData);
}

// ========== 更新筛选按钮状态 ==========
function updateFilterButtons(activeType) {
    document.querySelectorAll('.filter-btns .filter-btn').forEach(btn => {
        const filterType = btn.getAttribute('data-filter');
        if (filterType === activeType) {
            btn.classList.add('active');
        } else {
            btn.classList.remove('active');
        }
    });
}

// ========== HTML转义 ==========
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 图片上传 ==========
function setupImageUpload() {
    const input = document.getElementById('imageInput');
    const area = document.getElementById('uploadArea');
    
    input.addEventListener('change', (e) => {
        if (e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = (ev) => {
                uploadedImage = ev.target.result;
                document.getElementById('imagePreview').src = uploadedImage;
                document.getElementById('previewBox').style.display = 'block';
                area.classList.add('has-file');
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });
    
    area.addEventListener('dragover', (e) => {
        e.preventDefault();
        area.style.borderColor = '#1d1d1f';
    });
    
    area.addEventListener('dragleave', () => {
        area.style.borderColor = '#d2d2d7';
    });
    
    area.addEventListener('drop', (e) => {
        e.preventDefault();
        area.style.borderColor = '#d2d2d7';
        const file = e.dataTransfer.files[0];
        if (file && file.type.startsWith('image/')) {
            input.files = e.dataTransfer.files;
            input.dispatchEvent(new Event('change'));
        }
    });
}

// ========== 自动识别（从数据库图片） ==========
async function autoRecognizeFromDB() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (!selectedHomework.pic_path) {
        alert('该作业没有图片，无法自动识别');
        return;
    }
    
    // 修改按钮状态
    const btn = document.getElementById('autoRecognizeBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>识别中...</span>';
    
    try {
        const res = await fetch('/api/grading/auto-recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_id: selectedHomework.id,
                pic_path: selectedHomework.pic_path,
                subject_id: currentSubject,
                homework_name: selectedHomework.homework_name || '',
                page_num: selectedHomework.page_num || ''
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            baseEffect = data.base_effect || [];
            renderQuestionCards();
            
            // 显示成功提示
            btn.innerHTML = '<span style="color: #34c759;">识别成功</span>';
            setTimeout(() => {
                btn.innerHTML = originalText;
                btn.disabled = false;
            }, 2000);
        } else {
            alert('识别失败: ' + (data.error || '未知错误'));
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ========== 识别图片 ==========
async function recognizeImage() {
    if (!uploadedImage) {
        alert('请先上传图片');
        return;
    }
    
    showLoading('正在识别图片...');
    
    try {
        const res = await fetch('/api/grading/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: uploadedImage,
                subject_id: currentSubject
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            baseEffect = data.base_effect || [];
            renderQuestionCards();
        } else {
            alert('识别失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
    
    hideLoading();
}

// ========== 渲染题目卡片 ==========
function renderQuestionCards() {
    const container = document.getElementById('questionCards');
    
    if (baseEffect.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无题目数据，点击"自动识别"按钮或手动添加</div></div>';
        return;
    }
    
    // 添加保存按钮
    const saveBtn = `
        <div class="editor-actions" style="margin-bottom: 16px;">
            <button class="btn btn-primary" onclick="saveBaseEffect()">保存基准效果</button>
            <button class="btn btn-secondary" onclick="deleteCurrentBaseline()">删除基准效果</button>
            <span id="saveStatus" style="margin-left: 12px; color: #666;"></span>
        </div>
    `;
    
    const cardsHtml = baseEffect.map((item, index) => {
        // 判断使用哪个字段存储标准答案
        const answerField = item.answer !== undefined ? 'answer' : 'mainAnswer';
        const answerValue = item.answer || item.mainAnswer || '';
        return `
        <div class="question-card" data-index="${index}">
            <div class="question-card-header">
                <span class="question-index">第 ${item.index || index + 1} 题</span>
                <button class="question-delete" onclick="deleteQuestion(${index})">x</button>
            </div>
            <div class="question-field">
                <label>标准答案</label>
                <input type="text" value="${escapeHtml(answerValue)}" 
                       onchange="updateQuestion(${index}, '${answerField}', this.value)">
            </div>
            <div class="question-field">
                <label>用户答案 (userAnswer)</label>
                <input type="text" value="${escapeHtml(item.userAnswer || '')}" 
                       onchange="updateQuestion(${index}, 'userAnswer', this.value)">
            </div>
            <div class="question-field">
                <label>是否正确 (correct)</label>
                <select onchange="updateQuestion(${index}, 'correct', this.value)">
                    <option value="yes" ${item.correct === 'yes' ? 'selected' : ''}>yes - 正确</option>
                    <option value="no" ${item.correct === 'no' ? 'selected' : ''}>no - 错误</option>
                </select>
            </div>
        </div>
    `;}).join('');
    
    container.innerHTML = saveBtn + cardsHtml;
}

// ========== 更新题目 ==========
function updateQuestion(index, field, value) {
    if (baseEffect[index]) {
        baseEffect[index][field] = value;
    }
}

// ========== 添加题目 ==========
function addQuestion() {
    const maxIndex = baseEffect.length > 0 
        ? Math.max(...baseEffect.map(q => parseInt(q.index) || 0)) 
        : 0;
    
    baseEffect.push({
        answer: '',
        correct: 'yes',
        index: String(maxIndex + 1),
        tempIndex: baseEffect.length,
        userAnswer: ''
    });
    
    renderQuestionCards();
}

// ========== 删除题目 ==========
function deleteQuestion(index) {
    baseEffect.splice(index, 1);
    baseEffect.forEach((item, i) => {
        item.index = String(i + 1);
        item.tempIndex = i;
    });
    renderQuestionCards();
}

// ========== 清空基准效果 ==========
function clearBaseEffect() {
    if (confirm('确定要清空所有题目吗？')) {
        baseEffect = [];
        renderQuestionCards();
    }
}

// ========== 删除当前基准效果 ==========
async function deleteCurrentBaseline() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (!confirm('确定要删除当前作业的基准效果吗？删除后无法恢复。')) {
        return;
    }
    
    try {
        const res = await fetch('/api/grading/delete-baseline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_name: selectedHomework.homework_name || '',
                page_num: selectedHomework.page_num || ''
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            baseEffect = [];
            renderQuestionCards();
            alert('基准效果已删除');
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// ========== 显示全部基准效果 ==========
async function showAllBaselines() {
    const modal = document.getElementById('baselineModal');
    const body = document.getElementById('baselineModalBody');
    
    modal.style.display = 'flex';
    body.innerHTML = '<div class="loading-text">加载中...</div>';
    
    try {
        const res = await fetch('/api/grading/list-baselines');
        const data = await res.json();
        
        if (data.success) {
            renderBaselineList(data.baselines || []);
        } else {
            body.innerHTML = '<div class="empty-state-text">加载失败: ' + (data.error || '未知错误') + '</div>';
        }
    } catch (e) {
        body.innerHTML = '<div class="empty-state-text">加载失败: ' + e.message + '</div>';
    }
}

// ========== 渲染基准效果列表 ==========
function renderBaselineList(baselines) {
    const body = document.getElementById('baselineModalBody');
    
    if (baselines.length === 0) {
        body.innerHTML = '<div class="empty-state-text">暂无保存的基准效果</div>';
        return;
    }
    
    const html = baselines.map(item => {
        const sourceLabel = item.source === 'dataset' ? 
            '<span style="background:#e3f2fd;color:#1565c0;padding:2px 6px;border-radius:4px;font-size:11px;margin-left:8px;">数据集</span>' : 
            '<span style="background:#f5f5f5;color:#666;padding:2px 6px;border-radius:4px;font-size:11px;margin-left:8px;">手动保存</span>';
        
        return `
            <div class="baseline-item">
                <div class="baseline-item-info">
                    <div class="baseline-item-title">${escapeHtml(item.homework_name || '未知作业')}${sourceLabel}</div>
                    <div class="baseline-item-meta">
                        页码: ${item.page_num || '-'} | 
                        题目数: ${item.question_count || 0} | 
                        创建时间: ${formatTime(item.created_at)}
                    </div>
                </div>
                <div class="baseline-item-actions">
                    <button class="btn btn-small" onclick="loadBaselineById('${escapeHtml(item.filename)}', '${item.source || 'baseline'}', '${item.page_num || ''}')">加载</button>
                    <button class="btn btn-small" style="background:#c53030;color:#fff;" onclick="deleteBaselineById('${escapeHtml(item.filename)}', '${item.source || 'baseline'}')">删除</button>
                </div>
            </div>
        `;
    }).join('');
    
    body.innerHTML = html;
}

// ========== 通过文件名加载基准效果 ==========
async function loadBaselineById(filename, source, pageNum) {
    try {
        const res = await fetch('/api/grading/load-baseline-by-file', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                filename: filename,
                source: source || 'baseline',
                page_num: pageNum || ''
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            baseEffect = data.base_effect || [];
            renderQuestionCards();
            hideBaselineModal();
            alert('基准效果已加载');
        } else {
            alert('加载失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
}

// ========== 通过文件名删除基准效果 ==========
async function deleteBaselineById(filename, source) {
    if (!confirm('确定要删除这个基准效果吗？删除后无法恢复。')) {
        return;
    }
    
    try {
        let url = '/api/grading/delete-baseline-by-file';
        let body = { filename: filename };
        
        // 如果是数据集来源，使用数据集删除API
        if (source === 'dataset') {
            const datasetId = filename.replace('.json', '');
            url = `/api/batch/datasets/${datasetId}`;
            
            const res = await fetch(url, { method: 'DELETE' });
            const data = await res.json();
            
            if (data.success) {
                showAllBaselines();
            } else {
                alert('删除失败: ' + (data.error || '未知错误'));
            }
            return;
        }
        
        const res = await fetch(url, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        
        const data = await res.json();
        
        if (data.success) {
            // 重新加载列表
            showAllBaselines();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
}

// ========== 隐藏基准效果弹窗 ==========
function hideBaselineModal(event) {
    if (event && event.target !== event.currentTarget) {
        return;
    }
    document.getElementById('baselineModal').style.display = 'none';
}

// ========== 保存基准效果 ==========
async function saveBaseEffect() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (baseEffect.length === 0) {
        alert('基准效果为空，无法保存');
        return;
    }
    
    const statusEl = document.getElementById('saveStatus');
    if (statusEl) statusEl.textContent = '保存中...';
    
    try {
        const res = await fetch('/api/grading/save-baseline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_name: selectedHomework.homework_name || '',
                page_num: selectedHomework.page_num || '',
                base_effect: baseEffect,
                subject_id: currentSubject
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            if (statusEl) {
                statusEl.textContent = '✓ 保存成功';
                statusEl.style.color = '#34c759';
                setTimeout(() => {
                    statusEl.textContent = '';
                }, 3000);
            }
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
            if (statusEl) statusEl.textContent = '';
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
        if (statusEl) statusEl.textContent = '';
    }
}

// ========== 加载已保存的基准效果 ==========
async function loadSavedBaseEffect() {
    if (!selectedHomework) return;
    
    try {
        const res = await fetch('/api/grading/load-baseline', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_name: selectedHomework.homework_name || '',
                page_num: selectedHomework.page_num || '',
                book_id: selectedHomework.book_id || ''
            })
        });
        
        const data = await res.json();
        
        if (data.success && data.base_effect && data.base_effect.length > 0) {
            baseEffect = data.base_effect;
            renderQuestionCards();
            
            // 显示提示
            const statusEl = document.getElementById('saveStatus');
            if (statusEl) {
                const sourceText = data.source === 'dataset' ? '数据集' : '基准效果';
                statusEl.textContent = `已自动加载${sourceText}中的基准效果`;
                statusEl.style.color = '#1d1d1f';
                setTimeout(() => {
                    statusEl.textContent = '';
                }, 5000);
            }
        }
    } catch (e) {
        console.log('加载基准效果失败:', e);
    }
}

// ========== 开始评估 ==========
async function startEvaluation() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (baseEffect.length === 0) {
        alert('请先设置基准效果');
        return;
    }
    
    showLoading('正在进行本地评估...');
    
    try {
        let homeworkResult = [];
        try {
            homeworkResult = JSON.parse(selectedHomework.homework_result || '[]');
        } catch (e) {}
        
        const res = await fetch('/api/grading/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effect: baseEffect,
                homework_result: homeworkResult,
                subject_id: currentSubject,
                use_ai_compare: false  // 本地计算
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            evaluationResult = data.evaluation;
            renderEvaluationResult();
            document.getElementById('saveBtn').disabled = false;
        } else {
            alert('评估失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
    
    hideLoading();
}

// ========== 一键AI评估 ==========
async function startAIEvaluation() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (baseEffect.length === 0) {
        alert('请先设置基准效果');
        return;
    }
    
    const btn = document.getElementById('aiEvaluateBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>AI评估中...</span>';
    
    showLoading('正在调用AI大模型进行智能比对...');
    
    try {
        let homeworkResult = [];
        try {
            homeworkResult = JSON.parse(selectedHomework.homework_result || '[]');
        } catch (e) {}
        
        const res = await fetch('/api/grading/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effect: baseEffect,
                homework_result: homeworkResult,
                subject_id: currentSubject,
                use_ai_compare: true  // 使用AI比对
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            evaluationResult = data.evaluation;
            renderEvaluationResult();
            document.getElementById('saveBtn').disabled = false;
        } else {
            alert('AI评估失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
    
    hideLoading();
    btn.disabled = false;
    btn.innerHTML = originalText;
}

// ========== 渲染评估结果 ==========
function renderEvaluationResult() {
    if (!evaluationResult) return;
    
    document.getElementById('resultSection').style.display = 'block';
    
    // 渲染数据摘要（黑白简洁风格）
    if (typeof renderSummary === 'function') {
        renderSummary(evaluationResult);
    }
    
    // 使用优化后的统计卡片渲染器
    const statsOptimizedContainer = document.getElementById('statsGridOptimized');
    if (statsOptimizedContainer && typeof StatsRenderer !== 'undefined') {
        StatsRenderer.render(evaluationResult, statsOptimizedContainer);
    }
    
    // 渲染详细分析视图
    const detailSection = document.getElementById('detailedAnalysisSection');
    const detailContainer = document.getElementById('detailedAnalysisContainer');
    if (detailSection && detailContainer && typeof DetailedAnalysis !== 'undefined') {
        // 构建完整的详细分析数据
        const detailedData = buildDetailedAnalysisData(evaluationResult);
        DetailedAnalysis.currentData = detailedData;
        DetailedAnalysis.render(detailContainer);
        detailSection.style.display = 'block';
    }
    
    // 旧版统计卡片（隐藏）
    document.getElementById('statsGrid').style.display = 'none';
    
    if (evaluationResult.errors && evaluationResult.errors.length > 0) {
        document.getElementById('errorTableContainer').style.display = 'block';
        const tbody = document.getElementById('errorTableBody');
        tbody.innerHTML = evaluationResult.errors.map((err, index) => {
            // 获取严重程度样式
            const severityClass = getSeverityClass(err.severity_code || err.severity || 'medium');
            const severityText = err.severity || '中';
            
            // 获取分析数据
            const analysis = err.analysis || {};
            const analysisHtml = analysis.recognition_match !== undefined ? `
                <div class="analysis-badges">
                    <span class="analysis-badge ${analysis.recognition_match ? 'badge-success' : 'badge-error'}">
                        识别${analysis.recognition_match ? '✓' : '✗'}
                    </span>
                    <span class="analysis-badge ${analysis.judgment_match ? 'badge-success' : 'badge-error'}">
                        判断${analysis.judgment_match ? '✓' : '✗'}
                    </span>
                    ${analysis.is_hallucination ? '<span class="analysis-badge badge-warning">幻觉</span>' : ''}
                </div>
            ` : '';
            
            // 改进建议
            const suggestionHtml = err.suggestion ? `<div class="suggestion-text">💡 ${escapeHtml(err.suggestion)}</div>` : '';
            
            return `
                <tr data-index="${err.index}" data-error-type="${err.error_type}" data-severity="${err.severity_code || 'medium'}">
                    <td class="error-index">
                        <strong>${err.index}</strong>
                        <span class="severity-badge severity-${severityClass}">${severityText}</span>
                    </td>
                    <td class="error-base">${formatEffectCellDetailed(err.base_effect)}</td>
                    <td class="error-ai">${formatEffectCellDetailed(err.ai_result)}</td>
                    <td class="error-type">
                        <span class="tag tag-${getErrorTypeClass(err.error_type)}">${err.error_type}</span>
                        ${analysisHtml}
                    </td>
                    <td class="error-explain">
                        <div class="explanation-text">${escapeHtml(err.explanation || '-')}</div>
                        ${suggestionHtml}
                    </td>
                </tr>
            `;
        }).join('');
        
        // 填充错误类型筛选器
        if (typeof populateErrorTypeFilter === 'function') {
            populateErrorTypeFilter(evaluationResult.errors);
        }
    } else {
        document.getElementById('errorTableContainer').style.display = 'none';
    }
    
    renderCharts();
    
    // 默认隐藏分析报告，显示生成按钮
    document.getElementById('analysisReport').style.display = 'none';
    document.getElementById('generateReportBtn').style.display = 'block';
}

// ========== 获取错误类型样式类 ==========
function getErrorTypeClass(errorType) {
    const typeMap = {
        '识别错误-判断正确': 'info',
        '识别错误-判断错误': 'error',
        '识别正确-判断错误': 'warning',
        '格式差异': 'success',
        '缺失题目': 'default',
        'AI幻觉': 'purple',
        '标准答案不一致': 'orange'
    };
    return typeMap[errorType] || 'default';
}

// ========== 格式化效果单元格（详细版） ==========
function formatEffectCellSimple(effect) {
    if (!effect) return '<span class="text-muted">-</span>';
    
    const answer = effect.answer || '-';
    const userAnswer = effect.userAnswer || '-';
    const correct = effect.correct || '-';
    
    const correctClass = correct === 'yes' ? 'text-success' : correct === 'no' ? 'text-error' : 'text-muted';
    
    return `
        <div class="effect-cell">
            <div><span class="effect-label">答案:</span> ${escapeHtml(answer)}</div>
            <div><span class="effect-label">用户:</span> ${escapeHtml(userAnswer)}</div>
            <div><span class="effect-label">正确:</span> <span class="${correctClass}">${correct}</span></div>
        </div>
    `;
}

// ========== 格式化效果单元格（更详细版本） ==========
function formatEffectCellDetailed(effect) {
    if (!effect) return '<span class="text-muted">-</span>';
    
    const answer = effect.answer || '-';
    const userAnswer = effect.userAnswer || '-';
    const correct = effect.correct || '-';
    
    const correctClass = correct === 'yes' ? 'text-success' : correct === 'no' ? 'text-error' : 'text-muted';
    const correctIcon = correct === 'yes' ? '✓' : correct === 'no' ? '✗' : '-';
    
    return `
        <div class="effect-cell-detailed">
            <div class="effect-row">
                <span class="effect-label">标准答案:</span>
                <span class="effect-value answer-value">${escapeHtml(answer)}</span>
            </div>
            <div class="effect-row">
                <span class="effect-label">用户答案:</span>
                <span class="effect-value user-value">${escapeHtml(userAnswer)}</span>
            </div>
            <div class="effect-row">
                <span class="effect-label">判断结果:</span>
                <span class="effect-value ${correctClass}">
                    <span class="correct-icon">${correctIcon}</span> ${correct}
                </span>
            </div>
        </div>
    `;
}

// ========== 获取严重程度样式类 ==========
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

// ========== 生成DeepSeek分析报告 ==========
async function generateAnalysisReport() {
    if (!evaluationResult) {
        alert('请先完成评估');
        return;
    }
    
    const btn = document.getElementById('generateReportBtn');
    const originalText = btn.innerHTML;
    btn.disabled = true;
    btn.innerHTML = '<span>生成中...</span>';
    
    try {
        const res = await fetch('/api/grading/generate-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                evaluation: evaluationResult,
                subject_id: currentSubject
            })
        });
        
        const data = await res.json();
        
        if (data.success && data.report) {
            // 渲染Markdown为HTML
            const htmlContent = renderMarkdownToHtml(data.report);
            document.getElementById('reportContent').innerHTML = htmlContent;
            document.getElementById('analysisReport').style.display = 'block';
            btn.style.display = 'none';
        } else {
            alert('生成失败: ' + (data.error || '未知错误'));
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    } catch (e) {
        alert('生成失败: ' + e.message);
        btn.innerHTML = originalText;
        btn.disabled = false;
    }
}

// ========== 渲染Markdown为HTML ==========
function renderMarkdownToHtml(markdown) {
    if (!markdown) return '';
    
    let html = markdown;
    
    // 标题
    html = html.replace(/^### (.*$)/gim, '<h3 class="md-h3">$1</h3>');
    html = html.replace(/^## (.*$)/gim, '<h2 class="md-h2">$1</h2>');
    html = html.replace(/^# (.*$)/gim, '<h1 class="md-h1">$1</h1>');
    
    // 粗体
    html = html.replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>');
    
    // 列表
    html = html.replace(/^\d+\.\s+(.*$)/gim, '<li class="md-ol-item">$1</li>');
    html = html.replace(/^[-*]\s+(.*$)/gim, '<li class="md-ul-item">$1</li>');
    
    // 包装列表
    html = html.replace(/(<li class="md-ol-item">.*?<\/li>)/s, '<ol class="md-ol">$1</ol>');
    html = html.replace(/(<li class="md-ul-item">.*?<\/li>)/s, '<ul class="md-ul">$1</ul>');
    
    // 段落
    html = html.split('\n\n').map(para => {
        if (para.startsWith('<h') || para.startsWith('<ol') || para.startsWith('<ul') || para.startsWith('<li')) {
            return para;
        }
        return `<p class="md-p">${para}</p>`;
    }).join('');
    
    // 换行
    html = html.replace(/\n/g, '<br>');
    
    return html;
}

// ========== 渲染图表 ==========
function renderCharts() {
    destroyCharts();
    
    // 1. 错误类型分布饼图（彩色）
    if (evaluationResult.error_distribution) {
        const dist = evaluationResult.error_distribution;
        const labels = Object.keys(dist);
        const data = Object.values(dist);
        
        if (data.some(v => v > 0)) {
            // 为不同错误类型分配颜色（彩色）
            const colorMap = {
                '识别错误-判断正确': '#3b82f6',    // 蓝色
                '识别错误-判断错误': '#ef4444',    // 红色 - 最严重
                '识别正确-判断错误': '#f59e0b',    // 橙色
                '格式差异': '#10b981',             // 绿色
                '缺失题目': '#6b7280',             // 灰色
                'AI幻觉': '#8b5cf6'                // 紫色
            };
            
            const colors = labels.map(label => colorMap[label] || '#6b7280');
            
            chartInstances.errorPie = new Chart(document.getElementById('errorPieChart'), {
                type: 'doughnut',
                data: {
                    labels: labels,
                    datasets: [{
                        data: data,
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
                            labels: {
                                padding: 10,
                                font: { size: 11 },
                                color: '#1d1d1f',
                                boxWidth: 12
                            }
                        },
                        tooltip: {
                            callbacks: {
                                label: function(context) {
                                    const label = context.label || '';
                                    const value = context.parsed || 0;
                                    const total = context.dataset.data.reduce((a, b) => a + b, 0);
                                    const percentage = ((value / total) * 100).toFixed(1);
                                    return `${label}: ${value}题 (${percentage}%)`;
                                }
                            }
                        }
                    }
                }
            });
            
            if (typeof setupPieChartFilter === 'function') {
                setupPieChartFilter(chartInstances.errorPie);
            }
        }
    }
    
    // 2. 真实能力维度雷达图（彩色）
    const recognitionAccuracy = calculateRecognitionAccuracy();
    const judgmentAccuracy = calculateJudgmentAccuracy();
    const formatAccuracy = calculateFormatAccuracy();
    const completeness = calculateCompleteness();
    const antiHallucination = 100 - (typeof calculateHallucinationRate === 'function' ? calculateHallucinationRate(evaluationResult) : 0);
    
    chartInstances.radar = new Chart(document.getElementById('radarChart'), {
        type: 'radar',
        data: {
            labels: ['识别能力', '判断能力', '格式规范', '完整性', '抗幻觉能力'],
            datasets: [{
                label: '能力维度',
                data: [recognitionAccuracy, judgmentAccuracy, formatAccuracy, completeness, antiHallucination],
                backgroundColor: 'rgba(59, 130, 246, 0.2)',
                borderColor: '#3b82f6',
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                pointHoverBackgroundColor: '#fff',
                pointHoverBorderColor: '#3b82f6',
                borderWidth: 2
            }]
        },
        options: {
            responsive: true,
            scales: {
                r: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { stepSize: 20, font: { size: 11 }, color: '#666' },
                    pointLabels: { font: { size: 12 }, color: '#1d1d1f' },
                    grid: { color: '#e5e5e5' },
                    angleLines: { color: '#e5e5e5' }
                }
            },
            plugins: { legend: { display: false } }
        }
    });
    
    // 3. 错误严重程度分布柱状图（彩色）
    const severityData = calculateSeverityDistribution();
    chartInstances.severityBar = new Chart(document.getElementById('severityBarChart'), {
        type: 'bar',
        data: {
            labels: ['高严重', '中严重', '低严重'],
            datasets: [{
                label: '错误数量',
                data: [severityData.high, severityData.medium, severityData.low],
                backgroundColor: ['#ef4444', '#f59e0b', '#10b981'],
                borderRadius: 4,
                barThickness: 50
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: { 
                    beginAtZero: true,
                    ticks: { font: { size: 11 }, color: '#666' },
                    grid: { color: '#f0f0f0' }
                },
                x: {
                    ticks: { font: { size: 12, weight: '600' }, color: '#1d1d1f' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `${context.label}: ${context.parsed.y}题`;
                        }
                    }
                }
            }
        }
    });
    
    // 4. 选择题与非选择题准确率（彩色，带趋势线）
    if (baseEffect.length > 0 && evaluationResult) {
        function isChoiceQuestion(answer) {
            if (!answer) return false;
            const normalized = String(answer).trim().toUpperCase();
            return /^[A-D]{1,4}$/.test(normalized);
        }
        
        let choiceCorrect = 0, choiceTotal = 0;
        let nonChoiceCorrect = 0, nonChoiceTotal = 0;
        
        baseEffect.forEach(q => {
            const isChoice = isChoiceQuestion(q.answer);
            const idx = String(q.index);
            const hasError = evaluationResult.errors && evaluationResult.errors.some(err => String(err.index) === idx);
            const isCorrect = !hasError;
            
            if (isChoice) {
                choiceTotal++;
                if (isCorrect) choiceCorrect++;
            } else {
                nonChoiceTotal++;
                if (isCorrect) nonChoiceCorrect++;
            }
        });
        
        const choiceAccuracy = choiceTotal > 0 ? (choiceCorrect / choiceTotal * 100) : 0;
        const nonChoiceAccuracy = nonChoiceTotal > 0 ? (nonChoiceCorrect / nonChoiceTotal * 100) : 0;
        const avgAccuracy = (choiceAccuracy + nonChoiceAccuracy) / 2;
        
        chartInstances.questionBar = new Chart(document.getElementById('questionBarChart'), {
            type: 'bar',
            data: {
                labels: ['选择题', '非选择题'],
                datasets: [
                    {
                        label: '准确率',
                        data: [choiceAccuracy, nonChoiceAccuracy],
                        backgroundColor: ['#3b82f6', '#10b981'],
                        borderRadius: 6,
                        barThickness: 60,
                        order: 2
                    },
                    {
                        label: '平均线',
                        data: [avgAccuracy, avgAccuracy],
                        type: 'line',
                        borderColor: '#f59e0b',
                        borderDash: [5, 5],
                        borderWidth: 2,
                        pointRadius: 0,
                        fill: false,
                        order: 1
                    }
                ]
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
                            callback: function(value) { return value + '%'; }
                        },
                        grid: { color: '#f0f0f0' }
                    },
                    x: {
                        ticks: { font: { size: 13, weight: '600' }, color: '#1d1d1f' },
                        grid: { display: false }
                    }
                },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                if (context.dataset.label === '平均线') {
                                    return `平均: ${context.parsed.y.toFixed(1)}%`;
                                }
                                const label = context.label;
                                const value = context.parsed.y.toFixed(1);
                                let detail = '';
                                if (label === '选择题') {
                                    detail = `${choiceCorrect}/${choiceTotal}题`;
                                } else {
                                    detail = `${nonChoiceCorrect}/${nonChoiceTotal}题`;
                                }
                                return `准确率: ${value}% (${detail})`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // 5. 偏差程度图（替代热力图）
    renderDeviationChart();
    
    // 6. 准确率历史趋势图
    renderHistoryTrendChart();
}

// ========== 计算识别准确率 ==========
function calculateRecognitionAccuracy() {
    if (!evaluationResult || !evaluationResult.error_distribution) return 100;
    const dist = evaluationResult.error_distribution;
    const recognitionErrors = (dist['识别错误-判断正确'] || 0) + (dist['识别错误-判断错误'] || 0);
    const total = evaluationResult.total_questions || 1;
    return Math.max(0, 100 - (recognitionErrors / total * 100));
}

// ========== 计算判断准确率 ==========
function calculateJudgmentAccuracy() {
    if (!evaluationResult || !evaluationResult.error_distribution) return 100;
    const dist = evaluationResult.error_distribution;
    const judgmentErrors = (dist['识别正确-判断错误'] || 0) + (dist['识别错误-判断错误'] || 0);
    const total = evaluationResult.total_questions || 1;
    return Math.max(0, 100 - (judgmentErrors / total * 100));
}

// ========== 计算格式规范率 ==========
function calculateFormatAccuracy() {
    if (!evaluationResult || !evaluationResult.error_distribution) return 100;
    const dist = evaluationResult.error_distribution;
    const formatErrors = dist['格式差异'] || 0;
    const total = evaluationResult.total_questions || 1;
    return Math.max(0, 100 - (formatErrors / total * 100));
}

// ========== 计算完整性 ==========
function calculateCompleteness() {
    if (!evaluationResult || !evaluationResult.error_distribution) return 100;
    const dist = evaluationResult.error_distribution;
    const missingErrors = dist['缺失题目'] || 0;
    const total = evaluationResult.total_questions || 1;
    return Math.max(0, 100 - (missingErrors / total * 100));
}

// ========== 计算严重程度分布 ==========
function calculateSeverityDistribution() {
    const result = { high: 0, medium: 0, low: 0 };
    if (!evaluationResult || !evaluationResult.error_distribution) return result;
    
    const dist = evaluationResult.error_distribution;
    // 高严重：识别错误-判断错误、识别正确-判断错误、缺失题目
    result.high = (dist['识别错误-判断错误'] || 0) + (dist['识别正确-判断错误'] || 0) + (dist['缺失题目'] || 0);
    // 中严重：识别错误-判断正确
    result.medium = dist['识别错误-判断正确'] || 0;
    // 低严重：格式差异
    result.low = dist['格式差异'] || 0;
    
    return result;
}

// ========== 渲染偏差程度图 ==========
function renderDeviationChart() {
    const container = document.getElementById('heatmapContainer');
    if (!container || !baseEffect || baseEffect.length === 0) {
        if (container) container.innerHTML = '<div class="empty-state-text">暂无数据</div>';
        return;
    }
    
    // 计算每题的偏差程度
    const deviationData = baseEffect.map((q, i) => {
        const idx = String(q.index);
        const error = evaluationResult.errors?.find(err => String(err.index) === idx);
        
        let deviation = 0; // 0=正确, 1=轻微, 2=中等, 3=严重
        let label = '正确';
        
        if (error) {
            switch (error.error_type) {
                case '格式差异':
                    deviation = 1;
                    label = '轻微';
                    break;
                case '识别错误-判断正确':
                    deviation = 2;
                    label = '中等';
                    break;
                case '识别错误-判断错误':
                case '识别正确-判断错误':
                case '缺失题目':
                    deviation = 3;
                    label = '严重';
                    break;
                default:
                    deviation = 2;
                    label = '中等';
            }
        }
        
        return { index: q.index, deviation, label };
    });
    
    // 颜色映射（彩色）
    const colorMap = {
        0: '#10b981',  // 正确 - 绿色
        1: '#fbbf24',  // 轻微 - 黄色
        2: '#f59e0b',  // 中等 - 橙色
        3: '#ef4444'   // 严重 - 红色
    };
    
    const textColorMap = {
        0: '#fff',
        1: '#1d1d1f',
        2: '#fff',
        3: '#fff'
    };
    
    const cells = deviationData.map(d => `
        <div class="deviation-cell" 
             style="background:${colorMap[d.deviation]};color:${textColorMap[d.deviation]}"
             title="第${d.index}题: ${d.label}">
            ${d.index}
        </div>
    `).join('');
    
    const cols = Math.min(deviationData.length, 10);
    container.innerHTML = `
        <div class="deviation-legend">
            <span><span class="legend-dot" style="background:#10b981;"></span>正确</span>
            <span><span class="legend-dot" style="background:#fbbf24;"></span>轻微</span>
            <span><span class="legend-dot" style="background:#f59e0b;"></span>中等</span>
            <span><span class="legend-dot" style="background:#ef4444;"></span>严重</span>
        </div>
        <div class="deviation-grid" style="grid-template-columns: repeat(${cols}, 1fr);">
            ${cells}
        </div>
    `;
}

// ========== 渲染准确率历史趋势图 ==========
function renderHistoryTrendChart() {
    const canvas = document.getElementById('historyTrendChart');
    if (!canvas) return;
    
    // 从localStorage获取历史记录
    const history = JSON.parse(localStorage.getItem('grading_history') || '[]');
    const currentSubjectHistory = history.filter(r => r.subject_id === currentSubject).slice(0, 10).reverse();
    
    // 添加当前评估结果
    const allData = [...currentSubjectHistory.map(r => ({
        accuracy: r.accuracy * 100,
        time: new Date(r.timestamp).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
    }))];
    
    if (evaluationResult) {
        allData.push({
            accuracy: evaluationResult.accuracy * 100,
            time: '当前'
        });
    }
    
    if (allData.length < 2) {
        canvas.parentElement.innerHTML = '<div class="empty-state-text" style="height:200px;display:flex;align-items:center;justify-content:center;">历史数据不足，无法显示趋势</div>';
        return;
    }
    
    chartInstances.historyTrend = new Chart(canvas, {
        type: 'line',
        data: {
            labels: allData.map(d => d.time),
            datasets: [{
                label: '准确率',
                data: allData.map(d => d.accuracy),
                borderColor: '#3b82f6',
                backgroundColor: 'rgba(59, 130, 246, 0.1)',
                fill: true,
                tension: 0.3,
                pointBackgroundColor: '#3b82f6',
                pointBorderColor: '#fff',
                pointRadius: 4,
                pointHoverRadius: 6
            }]
        },
        options: {
            responsive: true,
            scales: {
                y: {
                    beginAtZero: false,
                    min: Math.max(0, Math.min(...allData.map(d => d.accuracy)) - 10),
                    max: 100,
                    ticks: {
                        font: { size: 11 },
                        color: '#666',
                        callback: function(value) { return value + '%'; }
                    },
                    grid: { color: '#f0f0f0' }
                },
                x: {
                    ticks: { font: { size: 11 }, color: '#666' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `准确率: ${context.parsed.y.toFixed(1)}%`;
                        }
                    }
                }
            }
        }
    });
}

// ========== 销毁图表 ==========
function destroyCharts() {
    Object.values(chartInstances).forEach(chart => {
        if (chart) chart.destroy();
    });
    chartInstances = { errorPie: null, radar: null, questionBar: null, severityBar: null, deviationChart: null, historyTrend: null };
}

// ========== 构建详细分析数据 ==========
function buildDetailedAnalysisData(evaluation) {
    if (!evaluation || !baseEffect) return [];
    
    // 如果后端已返回detailed_analysis，直接使用
    if (evaluation.detailed_analysis && evaluation.detailed_analysis.length > 0) {
        return evaluation.detailed_analysis;
    }
    
    // 否则根据baseEffect和errors构建
    const errorMap = {};
    (evaluation.errors || []).forEach(err => {
        errorMap[String(err.index)] = err;
    });
    
    // 构建homework_result字典
    let homeworkResult = [];
    try {
        homeworkResult = JSON.parse(selectedHomework?.homework_result || '[]');
    } catch (e) {}
    
    const hwDict = {};
    homeworkResult.forEach((item, i) => {
        const tempIdx = item.tempIndex !== undefined ? item.tempIndex : i;
        hwDict[tempIdx] = item;
    });
    
    return baseEffect.map((base, i) => {
        const idx = String(base.index || i + 1);
        const error = errorMap[idx];
        const tempIdx = base.tempIndex !== undefined ? base.tempIndex : i;
        const ai = hwDict[tempIdx] || {};
        
        if (error) {
            return {
                index: idx,
                is_correct: false,
                error_type: error.error_type,
                severity: error.severity || '中',
                severity_code: error.severity_code || 'medium',
                base_effect: error.base_effect || {
                    answer: base.answer || base.mainAnswer || '',
                    userAnswer: base.userAnswer || '',
                    correct: base.correct || ''
                },
                ai_result: error.ai_result || {
                    answer: ai.answer || ai.mainAnswer || '',
                    userAnswer: ai.userAnswer || '',
                    correct: ai.correct || ''
                },
                analysis: error.analysis || {},
                explanation: error.explanation || '',
                suggestion: error.suggestion || ''
            };
        } else {
            return {
                index: idx,
                is_correct: true,
                base_effect: {
                    answer: base.answer || base.mainAnswer || '',
                    userAnswer: base.userAnswer || '',
                    correct: base.correct || ''
                },
                ai_result: {
                    answer: ai.answer || ai.mainAnswer || '',
                    userAnswer: ai.userAnswer || '',
                    correct: ai.correct || ''
                }
            };
        }
    });
}

// ========== 切换详细分析视图显示 ==========
function toggleDetailedAnalysis() {
    const section = document.getElementById('detailedAnalysisSection');
    const container = document.getElementById('detailedAnalysisContainer');
    
    if (!section) return;
    
    if (container.style.display === 'none' || !container.innerHTML) {
        container.style.display = 'block';
        if (typeof DetailedAnalysis !== 'undefined' && evaluationResult) {
            const detailedData = buildDetailedAnalysisData(evaluationResult);
            DetailedAnalysis.currentData = detailedData;
            DetailedAnalysis.render(container);
        }
    } else {
        container.style.display = 'none';
    }
}

// ========== 保存评估记录 ==========
function saveEvaluation() {
    if (!evaluationResult || !selectedHomework) {
        alert('没有可保存的评估结果');
        return;
    }
    
    const record = {
        id: generateId(),
        subject_id: currentSubject,
        subject_name: SUBJECTS[currentSubject].name,
        homework_id: selectedHomework.id,
        timestamp: new Date().toISOString(),
        accuracy: evaluationResult.accuracy,
        evaluation: evaluationResult,
        base_effect: baseEffect
    };
    
    const history = JSON.parse(localStorage.getItem('grading_history') || '[]');
    history.unshift(record);
    if (history.length > 100) history.pop();
    localStorage.setItem('grading_history', JSON.stringify(history));
    
    alert('评估记录已保存');
}

// ========== 加载历史记录 ==========
function loadHistory() {
    const history = JSON.parse(localStorage.getItem('grading_history') || '[]');
    const filter = document.getElementById('historySubjectFilter').value;
    
    let filtered = history;
    if (filter !== '') {
        filtered = history.filter(r => r.subject_id === parseInt(filter));
    }
    
    renderHistoryList(filtered);
}

// ========== 筛选历史记录 ==========
function filterHistory() {
    loadHistory();
}

// ========== 渲染历史记录列表 ==========
function renderHistoryList(records) {
    const container = document.getElementById('historyList');
    
    if (records.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">--</div>
                <div class="empty-state-text">暂无历史记录</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = records.map(record => `
        <div class="history-item">
            <div class="history-item-info">
                <div class="history-item-subject">${record.subject_name || '未知学科'}</div>
                <div class="history-item-meta">${formatTime(record.timestamp)} | ID: ${record.homework_id?.substring(0, 12) || '-'}...</div>
            </div>
            <div class="history-item-accuracy">${(record.accuracy * 100).toFixed(1)}%</div>
            <div class="history-item-actions">
                <button class="btn btn-small btn-secondary" onclick="viewHistoryDetail('${record.id}')">查看</button>
                <button class="btn btn-small" style="background:#c53030;" onclick="deleteHistoryRecord('${record.id}')">删除</button>
            </div>
        </div>
    `).join('');
}

// ========== 查看历史详情 ==========
function viewHistoryDetail(recordId) {
    const history = JSON.parse(localStorage.getItem('grading_history') || '[]');
    const record = history.find(r => r.id === recordId);
    
    if (record) {
        alert(`评估详情:\n\n学科: ${record.subject_name}\n准确率: ${(record.accuracy * 100).toFixed(1)}%\n时间: ${formatTime(record.timestamp)}\n\n详细数据请查看控制台`);
        console.log('评估记录详情:', record);
    }
}

// ========== 删除历史记录 ==========
function deleteHistoryRecord(recordId) {
    if (!confirm('确定要删除这条记录吗？')) return;
    
    let history = JSON.parse(localStorage.getItem('grading_history') || '[]');
    history = history.filter(r => r.id !== recordId);
    localStorage.setItem('grading_history', JSON.stringify(history));
    
    loadHistory();
}

// ========== 清空历史记录 ==========
function clearHistory() {
    if (!confirm('确定要清空所有历史记录吗？')) return;
    
    localStorage.removeItem('grading_history');
    loadHistory();
}

// ========== 刷新数据 ==========
function refreshData() {
    loadHomeworkData();
}

// ========== 工具函数 ==========
function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function showError(msg) {
    alert(msg);
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timeStr) {
    if (!timeStr) return '-';
    try {
        const date = new Date(timeStr);
        return date.toLocaleString('zh-CN');
    } catch (e) {
        return timeStr;
    }
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

function showImageModal(src) {
    if (!src) return;
    document.getElementById('modalImg').src = src;
    document.getElementById('imageModal').classList.add('show');
}

function hideImageModal() {
    document.getElementById('imageModal').classList.remove('show');
}

document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideImageModal();
    }
});


// ========== 设置功能 ==========
let gradingPromptConfig = {};
let editingPromptKey = '';

// 学科批改评估提示词配置
const GRADING_PROMPTS = {
    'recognize_english': {
        name: '英语识别',
        icon: '🔤',
        desc: '识别英语作业答案',
        key: 'recognize_english'
    },
    'recognize_chinese': {
        name: '语文识别',
        icon: '📝',
        desc: '识别语文作业答案',
        key: 'recognize_chinese'
    },
    'recognize_math': {
        name: '数学识别',
        icon: '🔢',
        desc: '识别数学作业答案',
        key: 'recognize_math'
    },
    'recognize_physics': {
        name: '物理识别',
        icon: '⚡',
        desc: '识别物理作业答案',
        key: 'recognize_physics'
    },
    'evaluate': {
        name: '评估对比',
        icon: '📊',
        desc: 'DeepSeek评估对比提示词',
        key: 'evaluate'
    }
};

// 显示设置弹窗
let currentPromptKey = 'recognize';
let promptsConfig = {};

async function showSettingsModal() {
    document.getElementById('settingsModal').classList.add('show');
    await loadPromptsConfig();
    switchPromptTab('recognize');
}

// 隐藏设置弹窗
function hideSettingsModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('settingsModal').classList.remove('show');
}

// 加载提示词配置
async function loadPromptsConfig() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        promptsConfig = data.prompts || {};
    } catch (e) {
        promptsConfig = {};
    }
}

// 切换提示词标签页
function switchPromptTab(key) {
    currentPromptKey = key;
    
    // 更新标签页状态
    document.querySelectorAll('.prompt-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.key === key);
    });
    
    // 显示对应的提示词内容
    const textarea = document.getElementById('promptTextarea');
    textarea.value = promptsConfig[key] || getDefaultPrompt(key);
}

// 保存当前编辑的提示词到内存
function saveCurrentPromptToMemory() {
    const textarea = document.getElementById('promptTextarea');
    promptsConfig[currentPromptKey] = textarea.value;
}

// 保存所有提示词
async function saveAllPrompts() {
    // 先保存当前编辑的
    saveCurrentPromptToMemory();
    
    try {
        // 获取完整配置
        const res = await fetch('/api/config');
        const config = await res.json();
        
        // 更新提示词配置
        config.prompts = promptsConfig;
        
        // 保存
        const saveRes = await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        
        const saveData = await saveRes.json();
        if (saveData.success) {
            alert('保存成功');
            hideSettingsModal();
        } else {
            alert('保存失败');
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
}

// 恢复默认提示词
function resetPrompt() {
    if (!confirm('确定要恢复当前提示词为默认值吗？')) return;
    
    const defaultPrompt = getDefaultPrompt(currentPromptKey);
    document.getElementById('promptTextarea').value = defaultPrompt;
    promptsConfig[currentPromptKey] = defaultPrompt;
}

// 获取默认提示词
function getDefaultPrompt(key) {
    const defaults = {
        'recognize': `请识别图片中作业的每道题答案。

严格按照以下JSON格式输出，每道题包含以下字段：
- index: 题号（字符串，只输出大题号如"1"、"2"，不输出小题）
- answer: 标准答案（如果有多个空或多个小题，答案之间用;隔开）
- userAnswer: 用户手写答案（识别到的，如果有多个空或多个小题，答案之间用;隔开）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始的数字）

重要规则：
1. 只输出大题，不要拆分小题
2. 一道大题有多个填空时，所有答案用;隔开放在同一条记录中
3. 答案之间用英文分号;隔开

示例格式：
[
  {"index": "1", "answer": "冷热程度;摄氏度", "userAnswer": "热量", "correct": "no", "tempIndex": 0},
  {"index": "2", "answer": "温度计;热胀冷缩", "userAnswer": "火枪;冷热", "correct": "no", "tempIndex": 1},
  {"index": "3", "answer": "A", "userAnswer": "A", "correct": "yes", "tempIndex": 2}
]

请直接输出JSON数组，不要包含其他内容。`,

        'recognize_english': `你是专业的英语作业批改识别助手，擅长识别手写英文字母、单词和句子。

任务：识别图片中英语作业的每道题答案，包括：
- 选择题答案（A/B/C/D）
- 填空题答案（单词、短语）
- 判断题答案（T/F）
- 简答题答案（句子、段落）

英语特殊处理规则：
1. 字母大小写：严格按手写形式记录，不自动转换大小写
2. 单词拼写：完全按手写内容记录，即使拼写错误也不纠正
3. 标点符号：识别句号、逗号、问号、感叹号等
4. 连写/草书：尽量识别，无法识别写"不清晰"
5. 涂改内容：只记录最终答案，划掉的内容忽略

输出格式JSON数组，每道题包含：
- index: 题号（字符串）
- answer: 标准答案（如有）
- userAnswer: 用户手写答案（严格按原样记录）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始）

示例：
[{"index":"1","answer":"B","userAnswer":"B","correct":"yes","tempIndex":0}]

请直接输出JSON数组，不要包含其他内容。`,

        'recognize_chinese': `你是专业的语文作业批改识别助手，擅长识别手写汉字和语文答案。

任务：识别图片中语文作业的每道题答案，包括：
- 选择题答案（A/B/C/D）
- 填空题答案（字、词、成语）
- 默写题答案（诗句、古文）
- 简答题答案（句子、段落）
- 作文/阅读理解答案

语文特殊处理规则：
1. 汉字识别：严格按手写笔画识别，不自动纠正错别字
2. 繁简体：按手写形式记录，不转换
3. 标点符号：识别中文标点
4. 诗词格式：保留原有换行和格式
5. 连笔字：尽量识别，无法识别写"不清晰"
6. 涂改内容：只记录最终答案

输出格式JSON数组，每道题包含：
- index: 题号（字符串）
- answer: 标准答案（如有）
- userAnswer: 用户手写答案（严格按原样记录）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始）

示例：
[{"index":"1","answer":"春眠不觉晓","userAnswer":"春眠不觉晓","correct":"yes","tempIndex":0}]

请直接输出JSON数组，不要包含其他内容。`,

        'recognize_math': `你是专业的数学作业批改识别助手，擅长识别手写数学公式和计算过程。

任务：识别图片中数学作业的每道题答案，包括：
- 选择题答案（A/B/C/D）
- 填空题答案（数字、公式）
- 计算题答案（算式、结果）
- 应用题答案（解题过程、最终答案）
- 证明题答案

数学特殊处理规则：
1. 数字识别：严格区分0和O、1和l、6和b等易混字符
2. 运算符号：+、-、*、/、=等
3. 分数表示：用 a/b 格式，如 3/4
4. 根号表示：用 sqrt 或 sqrt(内容)
5. 幂指数：用 ^ 表示，如 x^2
6. 下标：用 _ 表示，如 a_1
7. 竖式计算：按多行格式记录，用\\n换行
8. 单位：识别cm、m、kg等单位
9. 涂改内容：只记录最终答案

输出格式JSON数组，每道题包含：
- index: 题号（字符串）
- answer: 标准答案（如有）
- userAnswer: 用户手写答案（严格按原样记录）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始）

示例：
[{"index":"1","answer":"x=3","userAnswer":"x=3","correct":"yes","tempIndex":0}]

请直接输出JSON数组，不要包含其他内容。`,

        'recognize_physics': `你是专业的物理作业批改识别助手，擅长识别手写物理公式和解题过程。

任务：识别图片中物理作业的每道题答案，包括：
- 选择题答案（A/B/C/D）
- 填空题答案（数值、单位、公式）
- 计算题答案（公式推导、数值计算）
- 实验题答案（数据、结论）
- 简答题答案

物理特殊处理规则：
1. 物理量符号：v(速度)、a(加速度)、F(力)、m(质量)、t(时间)等
2. 单位识别：m/s、N、kg、J、W、Pa等
3. 科学计数法：如 3*10^8
4. 希腊字母：可用英文替代
5. 公式格式：F=ma、v=s/t等
6. 分数/除法：用 / 表示
7. 下标：用 _ 表示，如 v_0
8. 涂改内容：只记录最终答案

输出格式JSON数组，每道题包含：
- index: 题号（字符串）
- answer: 标准答案（如有）
- userAnswer: 用户手写答案（严格按原样记录）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始）

示例：
[{"index":"1","answer":"10m/s","userAnswer":"10m/s","correct":"yes","tempIndex":0}]

请直接输出JSON数组，不要包含其他内容。`,

        'evaluate': `你是专业的AI批改效果评估专家。

任务：对比基准效果（人工标注）和AI批改结果，分析差异并给出评估。

评估维度：
1. 识别准确性：AI识别的userAnswer是否与基准一致
2. 判断正确性：AI的correct判断是否与基准一致
3. 错误分类：
   - 识别错误-判断正确：识别有误但判断对了
   - 识别错误-判断错误：识别和判断都错了（最严重）
   - 识别正确-判断错误：识别对了但判断错了
   - 格式差异：内容正确但格式不同
   - 缺失题目：AI结果中缺少该题

输出格式JSON对象，包含评估结果。`
    };
    return defaults[key] || '';
}


// ========== 数据集管理功能 ==========
let datasetBookList = {};
let selectedDatasetBook = null;
let datasetList = [];
let selectedDatasetPages = new Set();
let pageEffectsData = {};

const DATASET_SUBJECT_NAMES = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理', 4: '化学', 5: '生物', 6: '地理'
};

function showDatasetModal() {
    document.getElementById('datasetModal').classList.add('show');
    loadDatasetBooks();
}

function hideDatasetModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('datasetModal').classList.remove('show');
}

async function loadDatasetBooks() {
    const container = document.getElementById('datasetBookList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/books');
        const data = await res.json();
        
        if (data.success) {
            datasetBookList = data.data || {};
            renderDatasetBooks();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

function filterDatasetBooks() {
    renderDatasetBooks();
}

function renderDatasetBooks() {
    const container = document.getElementById('datasetBookList');
    const filterSubject = document.getElementById('datasetSubjectFilter').value;
    
    let html = '';
    let hasBooks = false;
    
    for (const [subjectId, books] of Object.entries(datasetBookList)) {
        if (filterSubject && filterSubject !== subjectId) continue;
        if (!books || books.length === 0) continue;
        
        hasBooks = true;
        html += `<div class="dataset-book-group">
            <div class="dataset-book-group-title">${DATASET_SUBJECT_NAMES[subjectId] || '未知学科'}</div>
            ${books.map(book => `
                <div class="dataset-book-item ${selectedDatasetBook?.book_id === book.book_id ? 'selected' : ''}" 
                     onclick="selectDatasetBook('${book.book_id}', ${subjectId})">
                    <div class="dataset-book-item-title">${escapeHtml(book.book_name)}</div>
                    <div class="dataset-book-item-meta">${book.page_count || 0} 页</div>
                </div>
            `).join('')}
        </div>`;
    }
    
    if (!hasBooks) {
        html = '<div class="empty-state"><div class="empty-state-text">暂无图书数据</div></div>';
    }
    
    container.innerHTML = html;
}

async function selectDatasetBook(bookId, subjectId) {
    showLoading('加载书本详情...');
    try {
        const books = datasetBookList[subjectId] || [];
        selectedDatasetBook = books.find(b => b.book_id === bookId);
        
        if (!selectedDatasetBook) {
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
            selectedDatasetBook.pages = pagesData.data?.all_pages || [];
        }
        
        if (datasetsData.success) {
            datasetList = datasetsData.data || [];
        }
        
        renderDatasetBooks();
        renderDatasetDetail();
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
    hideLoading();
}

function renderDatasetDetail() {
    if (!selectedDatasetBook) {
        document.getElementById('datasetDetailEmpty').style.display = 'flex';
        document.getElementById('datasetDetail').style.display = 'none';
        return;
    }
    
    document.getElementById('datasetDetailEmpty').style.display = 'none';
    document.getElementById('datasetDetail').style.display = 'block';
    
    document.getElementById('datasetBookTitle').textContent = selectedDatasetBook.book_name;
    document.getElementById('datasetBookMeta').textContent = 
        `共 ${selectedDatasetBook.pages?.length || 0} 页 | ${datasetList.length} 个数据集`;
    
    // 渲染数据集列表
    const itemsContainer = document.getElementById('datasetItems');
    if (datasetList.length === 0) {
        itemsContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集</div></div>';
    } else {
        itemsContainer.innerHTML = datasetList.map(ds => `
            <div class="dataset-item">
                <div class="dataset-item-info">
                    <div class="dataset-item-title">页码: ${ds.pages?.join(', ') || '-'}</div>
                    <div class="dataset-item-meta">${ds.question_count || 0} 题 | ${formatTime(ds.created_at)}</div>
                </div>
                <div class="dataset-item-actions">
                    <button class="btn btn-small btn-danger" onclick="deleteDataset('${ds.dataset_id}')">删除</button>
                </div>
            </div>
        `).join('');
    }
    
    // 渲染页码列表
    const pagesContainer = document.getElementById('datasetPages');
    const pagesWithDataset = new Set();
    datasetList.forEach(ds => (ds.pages || []).forEach(p => pagesWithDataset.add(p)));
    
    if (!selectedDatasetBook.pages || selectedDatasetBook.pages.length === 0) {
        pagesContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无页码数据</div></div>';
    } else {
        pagesContainer.innerHTML = selectedDatasetBook.pages.map(page => 
            `<span class="dataset-page-tag ${pagesWithDataset.has(page) ? 'has-dataset' : ''}">${page}</span>`
        ).join('');
    }
}

function showAddDatasetForm() {
    if (!selectedDatasetBook) {
        alert('请先选择图书');
        return;
    }
    
    selectedDatasetPages.clear();
    pageEffectsData = {};
    
    // 渲染页码选择
    const pageGrid = document.getElementById('pageSelectGrid');
    pageGrid.innerHTML = (selectedDatasetBook.pages || []).map(page => 
        `<div class="page-select-tag" data-page="${page}" onclick="toggleDatasetPage(${page})">${page}</div>`
    ).join('');
    
    document.getElementById('pageEffectsConfig').innerHTML = 
        '<div class="empty-state"><div class="empty-state-text">请先选择页码</div></div>';
    
    document.getElementById('addDatasetModal').classList.add('show');
}

function hideAddDatasetModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('addDatasetModal').classList.remove('show');
}

function toggleDatasetPage(page) {
    if (selectedDatasetPages.has(page)) {
        selectedDatasetPages.delete(page);
    } else {
        selectedDatasetPages.add(page);
    }
    
    document.querySelectorAll('.page-select-tag').forEach(el => {
        el.classList.toggle('selected', selectedDatasetPages.has(parseInt(el.dataset.page)));
    });
    
    renderPageEffectsConfig();
}

function renderPageEffectsConfig() {
    const container = document.getElementById('pageEffectsConfig');
    
    if (selectedDatasetPages.size === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">请先选择页码</div></div>';
        return;
    }
    
    const sortedPages = Array.from(selectedDatasetPages).sort((a, b) => a - b);
    
    container.innerHTML = sortedPages.map(page => `
        <div class="page-effect-item">
            <div class="page-effect-header">
                <span class="page-effect-title">第 ${page} 页</span>
                <button class="btn btn-small" onclick="autoRecognizeDatasetPage(${page})">自动识别</button>
            </div>
            <textarea class="page-effect-textarea" id="pageEffect_${page}" 
                      placeholder="输入基准效果JSON数组，或点击自动识别"
                      onchange="updatePageEffectData(${page}, this.value)">${pageEffectsData[page] ? JSON.stringify(pageEffectsData[page], null, 2) : ''}</textarea>
        </div>
    `).join('');
}

function updatePageEffectData(page, value) {
    try {
        pageEffectsData[page] = JSON.parse(value);
    } catch (e) {
        // 解析失败，保持原值
    }
}

async function autoRecognizeDatasetPage(page) {
    if (!selectedDatasetBook) return;
    
    showLoading('检查可用作业图片...');
    
    try {
        const checkRes = await fetch(`/api/batch/datasets/available-homework?book_id=${selectedDatasetBook.book_id}&page_num=${page}&minutes=60`);
        const checkData = await checkRes.json();
        
        if (!checkData.success || !checkData.data.available) {
            hideLoading();
            alert(`第${page}页在最近60分钟内没有可用的作业图片`);
            return;
        }
        
        // 使用第一个可用的作业图片进行识别
        const homework = checkData.data.homework_list[0];
        
        showLoading('正在识别基准效果...');
        const recognizeRes = await fetch('/api/batch/datasets/auto-recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: selectedDatasetBook.book_id,
                page_num: page,
                homework_id: homework.id
            })
        });
        const recognizeData = await recognizeRes.json();
        
        if (recognizeData.success) {
            pageEffectsData[page] = recognizeData.data.base_effect || [];
            document.getElementById(`pageEffect_${page}`).value = 
                JSON.stringify(pageEffectsData[page], null, 2);
            alert('识别成功！');
        } else {
            alert('识别失败: ' + (recognizeData.error || '未知错误'));
        }
    } catch (e) {
        alert('识别失败: ' + e.message);
    }
    hideLoading();
}

async function saveNewDataset() {
    if (!selectedDatasetBook) {
        alert('请先选择图书');
        return;
    }
    
    if (selectedDatasetPages.size === 0) {
        alert('请至少选择一个页码');
        return;
    }
    
    // 检查所有页码是否都有基准效果
    const pages = Array.from(selectedDatasetPages);
    for (const page of pages) {
        if (!pageEffectsData[page] || pageEffectsData[page].length === 0) {
            alert(`第${page}页的基准效果为空，请先配置`);
            return;
        }
    }
    
    showLoading('保存数据集...');
    try {
        const res = await fetch('/api/batch/datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: selectedDatasetBook.book_id,
                pages: pages,
                base_effects: pageEffectsData
            })
        });
        const data = await res.json();
        
        if (data.success) {
            hideAddDatasetModal();
            // 重新加载数据集列表
            const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedDatasetBook.book_id}`);
            const datasetsData = await datasetsRes.json();
            if (datasetsData.success) {
                datasetList = datasetsData.data || [];
            }
            renderDatasetDetail();
            alert('数据集保存成功！');
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
        const res = await fetch(`/api/batch/datasets/${datasetId}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            // 重新加载数据集列表
            const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedDatasetBook.book_id}`);
            const datasetsData = await datasetsRes.json();
            if (datasetsData.success) {
                datasetList = datasetsData.data || [];
            }
            renderDatasetDetail();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('删除失败: ' + e.message);
    }
    hideLoading();
}

function formatTime(timeStr) {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
}


// ========== AI比对开关功能 ==========
let useAiCompare = false;

// 加载评估选项
async function loadEvalOptions() {
    try {
        const res = await fetch('/api/config');
        const data = await res.json();
        useAiCompare = data.use_ai_compare || false;
        
        const checkbox = document.getElementById('useAiCompareCheckbox');
        if (checkbox) {
            checkbox.checked = useAiCompare;
        }
    } catch (e) {
        console.log('加载评估选项失败:', e);
    }
}

// 保存评估选项
async function saveEvalOptions() {
    const checkbox = document.getElementById('useAiCompareCheckbox');
    useAiCompare = checkbox ? checkbox.checked : false;
    
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        config.use_ai_compare = useAiCompare;
        
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
    } catch (e) {
        console.log('保存评估选项失败:', e);
    }
}

// 在页面加载时初始化
document.addEventListener('DOMContentLoaded', () => {
    loadEvalOptions();
});

// 更新开始评估函数，支持AI比对
async function startEvaluationWithAI() {
    if (!selectedHomework) {
        alert('请先选择批改记录');
        return;
    }
    
    if (baseEffect.length === 0) {
        alert('请先设置基准效果');
        return;
    }
    
    const loadingText = useAiCompare ? '正在进行AI模型比对评估...' : '正在进行本地评估...';
    showLoading(loadingText);
    
    try {
        let homeworkResult = [];
        try {
            homeworkResult = JSON.parse(selectedHomework.homework_result || '[]');
        } catch (e) {}
        
        const res = await fetch('/api/grading/evaluate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effect: baseEffect,
                homework_result: homeworkResult,
                subject_id: currentSubject,
                use_ai_compare: useAiCompare
            })
        });
        
        const data = await res.json();
        
        if (data.success) {
            evaluationResult = data.evaluation;
            renderEvaluationResult();
            document.getElementById('saveBtn').disabled = false;
            
            // 显示评估模式提示
            if (evaluationResult.ai_compared) {
                console.log('使用AI模型比对完成评估');
            } else {
                console.log('使用本地计算完成评估');
            }
        } else {
            alert('评估失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
    
    hideLoading();
}

// 覆盖原有的startEvaluation函数
window.startEvaluation = startEvaluationWithAI;

// 添加答案比对提示词的默认值
function getDefaultPrompt(key) {
    const defaults = {
        'recognize': `请识别图片中作业的每道题答案。

严格按照以下JSON格式输出，每道题包含以下字段：
- index: 题号（字符串，只输出大题号如"1"、"2"，不输出小题）
- answer: 标准答案（如果有多个空或多个小题，答案之间用;隔开）
- userAnswer: 用户手写答案（识别到的，如果有多个空或多个小题，答案之间用;隔开）
- correct: 判断是否正确，"yes"或"no"
- tempIndex: 临时索引（从0开始的数字）

重要规则：
1. 只输出大题，不要拆分小题
2. 一道大题有多个填空时，所有答案用;隔开放在同一条记录中
3. 答案之间用英文分号;隔开
4. 禁止推理或猜测答案，必须100%忠实于图片中的实际手写内容

示例格式：
[
  {"index": "1", "answer": "冷热程度;摄氏度", "userAnswer": "热量", "correct": "no", "tempIndex": 0},
  {"index": "2", "answer": "温度计;热胀冷缩", "userAnswer": "火枪;冷热", "correct": "no", "tempIndex": 1},
  {"index": "3", "answer": "A", "userAnswer": "A", "correct": "yes", "tempIndex": 2}
]

请直接输出JSON数组，不要包含其他内容。`,

        'compare_answer': `你是专业的答案比对专家。请逐题比对基准效果和AI批改结果。

【任务】
对于每道题，分析以下内容：
1. 基准效果中的标准答案(answer)、用户答案(userAnswer)、判断结果(correct)
2. AI批改结果中的标准答案(answer)、用户答案(userAnswer)、判断结果(correct)
3. 判断AI批改是否正确，并给出错误类型

【错误类型定义】
- correct: 完全正确，识别和判断都一致
- recognition_error_judgment_correct: 识别错误但判断正确
- recognition_error_judgment_error: 识别错误且判断错误（最严重）
- recognition_correct_judgment_error: 识别正确但判断错误
- format_diff: 格式差异，内容本质相同但格式不同
- missing: AI结果中缺少该题
- hallucination: AI幻觉，学生答错但AI识别成了正确答案

【输出格式】
输出JSON数组，每个元素包含：
{
  "index": "题号",
  "error_type": "错误类型",
  "is_correct": true/false,
  "base_answer": "基准标准答案",
  "base_user_answer": "基准用户答案",
  "base_correct": "基准判断",
  "ai_answer": "AI标准答案",
  "ai_user_answer": "AI用户答案",
  "ai_correct": "AI判断",
  "explanation": "详细说明"
}

请直接输出JSON数组，不要输出其他内容。`,

        'evaluate': `你是专业的AI批改效果评估专家。

任务：对比基准效果（人工标注）和AI批改结果，分析差异并给出评估。

评估维度：
1. 识别准确性：AI识别的userAnswer是否与基准一致
2. 判断正确性：AI的correct判断是否与基准一致
3. 错误分类：
   - 识别错误-判断正确：识别有误但判断对了
   - 识别错误-判断错误：识别和判断都错了（最严重）
   - 识别正确-判断错误：识别对了但判断错了
   - 格式差异：内容正确但格式不同
   - 缺失题目：AI结果中缺少该题
   - AI幻觉：学生答错但AI识别成了正确答案

输出格式JSON对象，包含评估结果。`
    };
    
    // 如果key不在defaults中，返回空字符串
    return defaults[key] || '';
}
