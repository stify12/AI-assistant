/**
 * 数据集管理页面 JavaScript
 */

// ========== 全局状态 ==========
let bookList = {};
let selectedBook = null;
let datasetList = [];
let selectedPages = new Set();
let availableHomework = {};  // 按页码分组的可用作业
let selectedHomework = {};   // 每个页码选中的作业
let recognizeResults = {};   // 识别结果
let currentView = 'overview';  // 当前视图: 'overview' 或 'detail'

const SUBJECT_NAMES = {
    0: '英语', 1: '语文', 2: '数学', 3: '物理', 4: '化学', 5: '生物', 6: '地理'
};

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 优先加载数据集概览（快速）
    loadDatasetOverview();
    // 后台加载书本列表（较慢，不阻塞页面）
    loadBooks();
});

// ========== 返回导航 ==========
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/subject-grading';
    }
}

// ========== 工具函数 ==========
function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timeStr) {
    if (!timeStr) return '-';
    const date = new Date(timeStr);
    return `${date.getMonth() + 1}/${date.getDate()} ${date.getHours()}:${String(date.getMinutes()).padStart(2, '0')}`;
}

function showImageModal(src) {
    event.stopPropagation();
    document.getElementById('modalImage').src = src;
    document.getElementById('imageModal').classList.add('show');
}

function hideImageModal() {
    document.getElementById('imageModal').classList.remove('show');
}

// ========== 图书列表 ==========
let booksLoaded = false;  // 标记是否已加载

async function loadBooks() {
    if (booksLoaded && Object.keys(bookList).length > 0) {
        return;  // 已加载过，不重复加载
    }
    
    const container = document.getElementById('bookList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/books');
        const data = await res.json();
        
        if (data.success) {
            bookList = data.data || {};
            booksLoaded = true;
            renderBooks();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

function filterBooks() {
    renderBooks();
}

function renderBooks() {
    const container = document.getElementById('bookList');
    const filterSubject = document.getElementById('subjectFilter').value;
    const searchText = (document.getElementById('bookSearchInput').value || '').toLowerCase().trim();
    
    let html = '';
    let hasBooks = false;
    
    for (const [subjectId, books] of Object.entries(bookList)) {
        if (filterSubject && filterSubject !== subjectId) continue;
        if (!books || books.length === 0) continue;
        
        // 过滤书名
        const filteredBooks = books.filter(book => {
            if (!searchText) return true;
            return (book.book_name || '').toLowerCase().includes(searchText);
        });
        
        if (filteredBooks.length === 0) continue;
        
        hasBooks = true;
        html += `<div class="book-group">
            <div class="book-group-title">${SUBJECT_NAMES[subjectId] || '未知学科'} (${filteredBooks.length})</div>
            ${filteredBooks.map(book => `
                <div class="book-item ${selectedBook?.book_id === book.book_id ? 'selected' : ''}" 
                     onclick="selectBook('${book.book_id}', ${subjectId})">
                    <div class="book-item-title" title="${escapeHtml(book.book_name)}">${escapeHtml(book.book_name)}</div>
                    <div class="book-item-meta">${book.page_count || 0} 页</div>
                </div>
            `).join('')}
        </div>`;
    }
    
    if (!hasBooks) {
        html = '<div class="empty-state"><div class="empty-state-text">暂无匹配的图书</div></div>';
    }
    
    container.innerHTML = html;
}

// ========== 选择图书 ==========
async function selectBook(bookId, subjectId) {
    showLoading('加载书本详情...');
    
    try {
        const books = bookList[subjectId] || [];
        selectedBook = books.find(b => b.book_id === bookId);
        
        if (!selectedBook) {
            alert('未找到书本信息');
            hideLoading();
            return;
        }
        
        selectedBook.subject_id = subjectId;
        
        // 加载页码
        const pagesRes = await fetch(`/api/batch/books/${bookId}/pages`);
        const pagesData = await pagesRes.json();
        
        if (pagesData.success) {
            selectedBook.pages = pagesData.data?.all_pages || [];
        }
        
        // 加载数据集
        const datasetsRes = await fetch(`/api/batch/datasets?book_id=${bookId}`);
        const datasetsData = await datasetsRes.json();
        
        if (datasetsData.success) {
            datasetList = datasetsData.data || [];
        }
        
        renderBooks();
        renderBookDetail();
        
        // 隐藏概览，显示详情
        currentView = 'detail';
        document.getElementById('datasetOverview').style.display = 'none';
        document.getElementById('addDatasetPanel').style.display = 'none';
        document.getElementById('bookDetail').style.display = 'block';
        document.getElementById('emptyRight').style.display = 'none';
        
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
    hideLoading();
}

function renderBookDetail() {
    if (!selectedBook) return;
    
    document.getElementById('bookTitle').textContent = selectedBook.book_name;
    document.getElementById('bookMeta').textContent = 
        `${SUBJECT_NAMES[selectedBook.subject_id] || '未知学科'} | 共 ${selectedBook.pages?.length || 0} 页 | ${datasetList.length} 个数据集`;
    
    // 渲染数据集列表
    const datasetContainer = document.getElementById('datasetList');
    if (datasetList.length === 0) {
        datasetContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集，点击右上角添加</div></div>';
    } else {
        datasetContainer.innerHTML = datasetList.map(ds => `
            <div class="dataset-card">
                <div class="dataset-info">
                    <div class="dataset-title">页码: ${ds.pages?.join(', ') || '-'}</div>
                    <div class="dataset-meta">${ds.question_count || 0} 题 | 创建于 ${formatTime(ds.created_at)}</div>
                </div>
                <div class="dataset-actions">
                    <button class="btn btn-small btn-secondary" onclick="exportDataset('${ds.dataset_id}')">导出</button>
                    <button class="btn btn-small btn-secondary" onclick="viewDataset('${ds.dataset_id}')">查看</button>
                    <button class="btn btn-small btn-primary" onclick="editDataset('${ds.dataset_id}')">编辑</button>
                    <button class="btn btn-small btn-danger" onclick="deleteDataset('${ds.dataset_id}')">删除</button>
                </div>
            </div>
        `).join('');
    }
    
    // 渲染页码概览
    const pageContainer = document.getElementById('pageOverview');
    const pagesWithDataset = new Set();
    datasetList.forEach(ds => (ds.pages || []).forEach(p => pagesWithDataset.add(p)));
    
    if (!selectedBook.pages || selectedBook.pages.length === 0) {
        pageContainer.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无页码数据</div></div>';
    } else {
        pageContainer.innerHTML = selectedBook.pages.map(page => 
            `<span class="page-tag ${pagesWithDataset.has(page) ? 'has-dataset' : ''}">${page}</span>`
        ).join('');
    }
}

// ========== 添加数据集 ==========
function showAddDatasetPanel() {
    if (!selectedBook) {
        alert('请先选择图书');
        return;
    }
    
    // 重置状态
    selectedPages.clear();
    availableHomework = {};
    selectedHomework = {};
    recognizeResults = {};
    
    // 渲染页码选择
    const pagesWithDataset = new Set();
    datasetList.forEach(ds => (ds.pages || []).forEach(p => pagesWithDataset.add(p)));
    
    const pageGrid = document.getElementById('pageSelectGrid');
    pageGrid.innerHTML = (selectedBook.pages || []).map(page => 
        `<div class="page-select-item ${pagesWithDataset.has(page) ? 'has-dataset' : ''}" 
              data-page="${page}" onclick="togglePage(${page})">${page}</div>`
    ).join('');
    
    // 隐藏后续步骤
    document.getElementById('step2Section').style.display = 'none';
    document.getElementById('step3Section').style.display = 'none';
    document.getElementById('saveSection').style.display = 'none';
    document.getElementById('homeworkGrid').innerHTML = '<div class="empty-state"><div class="empty-state-text">请先选择页码</div></div>';
    document.getElementById('recognizeResult').innerHTML = '<div class="empty-state"><div class="empty-state-text">选择作业图片后点击"开始识别"</div></div>';
    
    // 显示添加面板
    document.getElementById('bookDetail').style.display = 'none';
    document.getElementById('addDatasetPanel').style.display = 'block';
}

function hideAddDatasetPanel() {
    document.getElementById('addDatasetPanel').style.display = 'none';
    
    // 根据当前视图显示对应内容
    if (currentView === 'overview') {
        document.getElementById('bookDetail').style.display = 'none';
        document.getElementById('datasetOverview').style.display = 'flex';
    } else {
        document.getElementById('bookDetail').style.display = 'block';
        document.getElementById('datasetOverview').style.display = 'none';
    }
}

function togglePage(page) {
    if (selectedPages.has(page)) {
        selectedPages.delete(page);
    } else {
        selectedPages.add(page);
    }
    
    updatePageSelection();
}

function updatePageSelection() {
    // 更新选中状态
    document.querySelectorAll('.page-select-item').forEach(el => {
        el.classList.toggle('selected', selectedPages.has(parseInt(el.dataset.page)));
    });
    
    // 更新选中数量显示
    document.getElementById('pageSelectInfo').textContent = `已选择 ${selectedPages.size} 个页码`;
    
    // 显示/隐藏步骤2
    if (selectedPages.size > 0) {
        document.getElementById('step2Section').style.display = 'block';
        loadAvailableHomework();
    } else {
        document.getElementById('step2Section').style.display = 'none';
        document.getElementById('step3Section').style.display = 'none';
        document.getElementById('saveSection').style.display = 'none';
    }
}

// 全选页码
function selectAllPages() {
    if (!selectedBook || !selectedBook.pages) return;
    selectedBook.pages.forEach(page => selectedPages.add(page));
    updatePageSelection();
}

// 清空页码选择
function clearPageSelection() {
    selectedPages.clear();
    updatePageSelection();
}

// 应用范围选择
function applyPageRange() {
    const input = document.getElementById('pageRangeInput').value.trim();
    if (!input) return;
    
    const availablePages = new Set(selectedBook?.pages || []);
    const parts = input.split(',').map(s => s.trim());
    
    for (const part of parts) {
        if (part.includes('-')) {
            // 范围格式: 1-10
            const [start, end] = part.split('-').map(s => parseInt(s.trim()));
            if (!isNaN(start) && !isNaN(end)) {
                for (let i = start; i <= end; i++) {
                    if (availablePages.has(i)) {
                        selectedPages.add(i);
                    }
                }
            }
        } else {
            // 单个页码
            const page = parseInt(part);
            if (!isNaN(page) && availablePages.has(page)) {
                selectedPages.add(page);
            }
        }
    }
    
    updatePageSelection();
    document.getElementById('pageRangeInput').value = '';
}

// ========== 加载可用作业 ==========
async function loadAvailableHomework() {
    if (selectedPages.size === 0) return;
    
    const hours = document.getElementById('timeRangeSelect').value;
    const container = document.getElementById('homeworkGrid');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    showLoading('加载可用作业图片...');
    
    try {
        availableHomework = {};
        const pages = Array.from(selectedPages).sort((a, b) => a - b);
        
        for (const page of pages) {
            const res = await fetch(`/api/dataset/available-homework?book_id=${selectedBook.book_id}&page_num=${page}&hours=${hours}`);
            const data = await res.json();
            
            if (data.success && data.data && data.data.length > 0) {
                availableHomework[page] = data.data;
            }
        }
        
        renderHomeworkGrid();
        
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
    
    hideLoading();
}

function renderHomeworkGrid() {
    const container = document.getElementById('homeworkGrid');
    const pages = Array.from(selectedPages).sort((a, b) => a - b);
    
    let html = '';
    let hasHomework = false;
    
    for (const page of pages) {
        const homeworkList = availableHomework[page] || [];
        
        if (homeworkList.length > 0) {
            hasHomework = true;
            html += `<div class="page-group">
                <div class="page-group-title">第 ${page} 页 (${homeworkList.length} 个可用)</div>
                <div class="homework-grid" style="display:grid;grid-template-columns:repeat(auto-fill,minmax(240px,1fr));gap:12px;">
                    ${homeworkList.map(hw => `
                        <div class="homework-card ${selectedHomework[page]?.id === hw.id ? 'selected' : ''}" 
                             onclick="selectHomework(${page}, '${hw.id}')">
                            <img class="homework-image" 
                                 src="${hw.pic_url || '/static/images/no-image.png'}" 
                                 alt="作业图片"
                                 onclick="showImageModal('${hw.pic_url}')">
                            <div class="homework-info">
                                <div class="homework-title" title="${escapeHtml(hw.student_name || hw.student_id)}">${escapeHtml(hw.student_name || hw.student_id || '未知学生')}</div>
                                <div class="homework-meta">
                                    作业ID: ${hw.id}<br>
                                    时间: ${formatTime(hw.create_time)}<br>
                                    题目数: ${hw.question_count || 0}
                                </div>
                                ${selectedHomework[page]?.id === hw.id ? '<span class="homework-select-badge">已选择</span>' : ''}
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>`;
        } else {
            html += `<div class="page-group">
                <div class="page-group-title">第 ${page} 页</div>
                <div class="empty-state" style="padding:20px;"><div class="empty-state-text">该页码暂无可用作业图片</div></div>
            </div>`;
        }
    }
    
    if (!hasHomework) {
        html = '<div class="empty-state"><div class="empty-state-text">所选页码暂无可用作业图片，请调整时间范围或选择其他页码</div></div>';
    }
    
    container.innerHTML = html;
    
    // 检查是否可以进入步骤3
    updateStep3Visibility();
}

function selectHomework(page, homeworkId) {
    const homeworkList = availableHomework[page] || [];
    const hw = homeworkList.find(h => h.id == homeworkId);
    
    if (hw) {
        if (selectedHomework[page]?.id === hw.id) {
            // 取消选择
            delete selectedHomework[page];
        } else {
            selectedHomework[page] = hw;
        }
        renderHomeworkGrid();
    }
}

function updateStep3Visibility() {
    const hasSelection = Object.keys(selectedHomework).length > 0;
    document.getElementById('step3Section').style.display = hasSelection ? 'block' : 'none';
    
    if (hasSelection) {
        renderRecognizePreview();
    }
}

function renderRecognizePreview() {
    const container = document.getElementById('recognizeResult');
    const pages = Object.keys(selectedHomework).map(Number).sort((a, b) => a - b);
    
    if (pages.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">请先选择作业图片</div></div>';
        return;
    }
    
    container.innerHTML = pages.map(page => {
        const hw = selectedHomework[page];
        const result = recognizeResults[page];
        
        // 判断状态
        let status, statusText, statusActions = '';
        if (result?.status === 'recognizing') {
            status = 'recognizing';
            statusText = '识别中...';
        } else if (result?.success && result?.data && result.data.length > 0) {
            status = 'success';
            statusText = '识别成功';
            statusActions = `<button class="btn btn-small btn-text" onclick="retryRecognize(${page})">重新识别</button>`;
        } else if (result && !result.success) {
            status = 'error';
            statusText = '识别失败';
            statusActions = `<button class="btn btn-small btn-primary" onclick="retryRecognize(${page})">重新识别</button>`;
        } else {
            status = 'pending';
            statusText = '待识别';
            statusActions = `<button class="btn btn-small btn-text" onclick="retryRecognize(${page})">单独识别</button>`;
        }
        
        let dataHtml = '';
        if (result?.status === 'recognizing') {
            // 识别中状态
            dataHtml = `
                <div class="recognizing-indicator">
                    <div class="recognizing-spinner"></div>
                    <span>正在识别中，请稍候...</span>
                </div>
            `;
        } else if (result && result.success && result.data && result.data.length > 0) {
            // 表格形式展示
            dataHtml = `
                <div class="view-toggle">
                    <button class="view-toggle-btn active" onclick="toggleResultView(${page}, 'table')">表格视图</button>
                    <button class="view-toggle-btn" onclick="toggleResultView(${page}, 'json')">JSON视图</button>
                </div>
                <div id="resultTable_${page}">
                    ${renderResultTable(page, result.data)}
                </div>
                <div id="resultJson_${page}" style="display:none;">
                    <textarea class="recognize-textarea" id="recognizeData_${page}" 
                              onchange="updateRecognizeData(${page}, this.value)">${JSON.stringify(result.data, null, 2)}</textarea>
                </div>
                <div class="recognize-count">共 ${result.data.length} 题</div>
            `;
        } else {
            // 错误或待识别状态
            let errorMsg = '';
            if (result?.error) {
                errorMsg = `<div class="recognize-error">错误: ${escapeHtml(result.error)}</div>`;
            }
            
            // 如果有 raw_preview，显示预览
            if (result?.raw_preview) {
                errorMsg += `<details style="margin-top:10px;">
                    <summary style="cursor:pointer;color:#666;">查看AI返回内容预览</summary>
                    <pre style="background:#f5f5f5;padding:10px;border-radius:4px;font-size:12px;max-height:200px;overflow:auto;">${escapeHtml(result.raw_preview)}</pre>
                </details>`;
            }
            
            dataHtml = `
                <textarea class="recognize-textarea" id="recognizeData_${page}" 
                          placeholder="点击"重新识别"自动识别，或手动输入JSON数组"
                          onchange="updateRecognizeData(${page}, this.value)"></textarea>
                ${errorMsg}
            `;
        }
        
        return `
            <div class="recognize-item ${status === 'error' ? 'recognize-item-error' : ''}">
                <div class="recognize-item-header">
                    <span class="recognize-item-title">第 ${page} 页</span>
                    <div class="recognize-item-actions">
                        ${statusActions}
                        <span class="recognize-status ${status}">${statusText}</span>
                    </div>
                </div>
                <div class="recognize-preview">
                    <img class="recognize-image" src="${hw.pic_url || '/static/images/no-image.png'}" 
                         onclick="showImageModal('${hw.pic_url}')">
                    <div class="recognize-data">
                        ${dataHtml}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderResultTable(page, data) {
    return `
        <div class="result-table-header">
            <button class="btn btn-small btn-secondary" onclick="showEffectCorrection(${page})">效果矫正</button>
        </div>
        <table class="recognize-table recognize-table-v2">
            <thead>
                <tr>
                    <th class="col-index">题号</th>
                    <th class="col-answer">标准答案</th>
                    <th class="col-user-answer">学生答案</th>
                    <th class="col-correct">是否正确</th>
                    <th class="col-tempindex">tempIndex</th>
                    <th class="col-action">操作</th>
                </tr>
            </thead>
            <tbody id="resultTableBody_${page}">
                ${data.map((item, idx) => `
                    <tr data-idx="${idx}">
                        <td class="col-index"><span class="index-text">${escapeHtml(item.index || '')}</span></td>
                        <td class="col-answer"><div class="standard-answer-box">${escapeHtml(item.answer || '-')}</div></td>
                        <td class="col-user-answer"><textarea class="answer-textarea" onchange="updateTableCell(${page}, ${idx}, 'userAnswer', this.value)">${escapeHtml(item.userAnswer || '')}</textarea></td>
                        <td class="col-correct">
                            <select onchange="updateTableCell(${page}, ${idx}, 'correct', this.value)">
                                <option value="yes" ${item.correct === 'yes' ? 'selected' : ''}>正确</option>
                                <option value="no" ${item.correct === 'no' || item.correct !== 'yes' ? 'selected' : ''}>错误</option>
                            </select>
                        </td>
                        <td class="col-tempindex">
                            <input type="number" value="${item.tempIndex !== undefined ? item.tempIndex : ''}" 
                                   onchange="updateTableCell(${page}, ${idx}, 'tempIndex', parseInt(this.value))">
                        </td>
                        <td class="col-action"><button class="btn-delete-row" onclick="deleteTableRow(${page}, ${idx})">x</button></td>
                    </tr>
                `).join('')}
            </tbody>
        </table>
        <div class="table-actions">
            <button class="btn-add-row" onclick="addTableRow(${page})">+ 添加题目</button>
        </div>
    `;
}

function toggleResultView(page, view) {
    const tableDiv = document.getElementById(`resultTable_${page}`);
    const jsonDiv = document.getElementById(`resultJson_${page}`);
    const buttons = tableDiv.parentElement.querySelectorAll('.view-toggle-btn');
    
    if (view === 'table') {
        tableDiv.style.display = 'block';
        jsonDiv.style.display = 'none';
        buttons[0].classList.add('active');
        buttons[1].classList.remove('active');
    } else {
        tableDiv.style.display = 'none';
        jsonDiv.style.display = 'block';
        buttons[0].classList.remove('active');
        buttons[1].classList.add('active');
        // 同步JSON
        document.getElementById(`recognizeData_${page}`).value = JSON.stringify(recognizeResults[page].data, null, 2);
    }
}

function updateTableCell(page, idx, field, value) {
    if (recognizeResults[page] && recognizeResults[page].data && recognizeResults[page].data[idx]) {
        recognizeResults[page].data[idx][field] = value;
    }
    checkCanSave();
}

function deleteTableRow(page, idx) {
    if (recognizeResults[page] && recognizeResults[page].data) {
        recognizeResults[page].data.splice(idx, 1);
        renderRecognizePreview();
        checkCanSave();
    }
}

function addTableRow(page) {
    if (recognizeResults[page] && recognizeResults[page].data) {
        const lastItem = recognizeResults[page].data[recognizeResults[page].data.length - 1];
        const newIndex = lastItem ? (parseInt(lastItem.index) + 1).toString() : '1';
        recognizeResults[page].data.push({
            index: newIndex,
            userAnswer: '',
            correct: 'yes',
            type: 'choice'
        });
        renderRecognizePreview();
        checkCanSave();
    }
}

function updateRecognizeData(page, value) {
    try {
        // 忽略空值
        if (!value || !value.trim()) {
            return;
        }
        
        const data = JSON.parse(value);
        
        // 验证是否为数组
        if (!Array.isArray(data)) {
            console.error('识别数据必须是数组格式');
            return;
        }
        
        recognizeResults[page] = { success: true, data: data };
    } catch (e) {
        console.error('JSON解析失败:', e.message);
        // 不更新 recognizeResults，保持原有错误状态
    }
    checkCanSave();
}

// ========== 开始识别 ==========
let isRecognizing = false;

async function startRecognize() {
    const pages = Object.keys(selectedHomework).map(Number).sort((a, b) => a - b);
    
    if (pages.length === 0) {
        alert('请先选择作业图片');
        return;
    }
    
    if (isRecognizing) {
        alert('正在识别中，请稍候...');
        return;
    }
    
    isRecognizing = true;
    
    // 初始化所有页码为"识别中"状态
    for (const page of pages) {
        recognizeResults[page] = { status: 'recognizing' };
    }
    renderRecognizePreview();
    
    // 并行发起所有识别请求
    const recognizePromises = pages.map(page => recognizePage(page));
    
    // 等待所有识别完成
    await Promise.all(recognizePromises);
    
    isRecognizing = false;
    renderRecognizePreview();
    checkCanSave();
}

// 单个页码识别
async function recognizePage(page) {
    const hw = selectedHomework[page];
    
    // 创建 AbortController 用于超时控制
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 300000); // 5分钟超时
    
    try {
        const res = await fetch('/api/dataset/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_id: hw.id,
                pic_path: hw.pic_path,
                subject_id: selectedBook.subject_id
            }),
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);
        
        // 检查响应状态
        if (!res.ok) {
            const contentType = res.headers.get('content-type');
            let errorMsg = `HTTP ${res.status}`;
            
            if (contentType && contentType.includes('application/json')) {
                const data = await res.json();
                errorMsg = data.error || errorMsg;
            } else {
                // 返回的是HTML或其他非JSON内容
                errorMsg = `服务器错误 (${res.status})，请稍后重试`;
            }
            
            recognizeResults[page] = {
                success: false,
                error: errorMsg
            };
            renderRecognizePreview();
            checkCanSave();
            return;
        }
        
        const data = await res.json();
        
        if (data.success) {
            recognizeResults[page] = {
                success: true,
                data: data.data || []
            };
        } else {
            recognizeResults[page] = {
                success: false,
                error: data.error || '识别失败',
                raw_preview: data.raw_preview || ''
            };
        }
    } catch (e) {
        clearTimeout(timeoutId);
        
        let errorMsg = '请求失败';
        if (e.name === 'AbortError') {
            errorMsg = '请求超时，AI模型响应时间过长，请点击"重新识别"重试';
        } else if (e.message.includes('NetworkError') || e.message.includes('fetch')) {
            errorMsg = '网络连接失败，请检查网络后重试';
        } else {
            errorMsg = `请求失败: ${e.message}`;
        }
        
        recognizeResults[page] = {
            success: false,
            error: errorMsg
        };
    }
    
    // 单个完成后立即更新UI
    renderRecognizePreview();
    checkCanSave();
}

// 重新识别单个页码
async function retryRecognize(page) {
    if (!selectedHomework[page]) {
        alert('未找到该页码的作业图片');
        return;
    }
    
    // 设置为识别中状态
    recognizeResults[page] = { status: 'recognizing' };
    renderRecognizePreview();
    
    // 执行识别
    await recognizePage(page);
}

function checkCanSave() {
    const pages = Object.keys(selectedHomework).map(Number);
    let successCount = 0;
    let failCount = 0;
    let pendingCount = 0;
    
    for (const page of pages) {
        const result = recognizeResults[page];
        if (result?.status === 'recognizing') {
            pendingCount++;
        } else if (result?.success && result?.data && result.data.length > 0) {
            successCount++;
        } else if (result && !result.success) {
            failCount++;
        } else {
            pendingCount++;
        }
    }
    
    // 只要有成功识别的页码就可以保存
    const canSave = successCount > 0;
    const saveSection = document.getElementById('saveSection');
    
    if (canSave) {
        saveSection.style.display = 'block';
        // 更新保存按钮文案，显示成功/失败数量
        const saveBtn = saveSection.querySelector('.btn-primary');
        if (failCount > 0) {
            saveBtn.innerHTML = `保存数据集 (${successCount}/${pages.length} 页成功)`;
        } else {
            saveBtn.innerHTML = '保存数据集';
        }
    } else {
        saveSection.style.display = 'none';
    }
}

// ========== 保存数据集 ==========
async function saveDataset() {
    const allPages = Object.keys(selectedHomework).map(Number).sort((a, b) => a - b);
    
    if (allPages.length === 0) {
        alert('请先选择作业图片并完成识别');
        return;
    }
    
    // 只收集识别成功的页码
    const successPages = [];
    const baseEffects = {};
    
    for (const page of allPages) {
        const result = recognizeResults[page];
        if (result && result.success && result.data && result.data.length > 0) {
            successPages.push(page);
            baseEffects[page] = result.data;
        }
    }
    
    if (successPages.length === 0) {
        alert('没有识别成功的页码，无法保存数据集');
        return;
    }
    
    // 如果有失败的页码，提示用户确认
    const failedPages = allPages.filter(p => !successPages.includes(p));
    if (failedPages.length > 0) {
        const confirmMsg = `有 ${failedPages.length} 个页码识别失败（第 ${failedPages.join(', ')} 页），是否只保存成功的 ${successPages.length} 个页码？\n\n点击"确定"保存成功的页码，点击"取消"返回继续处理失败的页码。`;
        if (!confirm(confirmMsg)) {
            return;
        }
    }
    
    showLoading('保存数据集...');
    
    try {
        // 为每个页码的基准效果添加题目类型信息
        const enrichedBaseEffects = {};
        for (const page of successPages) {
            const effects = baseEffects[page];
            if (effects && effects.length > 0) {
                try {
                    const enrichRes = await fetch('/api/batch/datasets/enrich-base-effects', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            book_id: selectedBook.book_id,
                            page_num: page,
                            base_effects: effects
                        })
                    });
                    const enrichData = await enrichRes.json();
                    
                    if (enrichData.success && enrichData.data) {
                        enrichedBaseEffects[page] = enrichData.data;
                    } else {
                        // 如果添加题目类型失败，使用原始数据
                        enrichedBaseEffects[page] = effects;
                    }
                } catch (e) {
                    // 如果请求失败，使用原始数据
                    enrichedBaseEffects[page] = effects;
                }
            }
        }
        
        const res = await fetch('/api/batch/datasets', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: selectedBook.book_id,
                pages: successPages,
                base_effects: enrichedBaseEffects
            })
        });
        const data = await res.json();
        
        if (data.success) {
            let msg = '数据集保存成功！';
            if (failedPages.length > 0) {
                msg += `\n\n已保存 ${successPages.length} 个页码，跳过了 ${failedPages.length} 个识别失败的页码。`;
            }
            alert(msg);
            // 重新加载数据集列表
            const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedBook.book_id}`);
            const datasetsData = await datasetsRes.json();
            if (datasetsData.success) {
                datasetList = datasetsData.data || [];
            }
            hideAddDatasetPanel();
            renderBookDetail();
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('保存失败: ' + e.message);
    }
    
    hideLoading();
}

// ========== 查看/删除数据集 ==========
function viewDataset(datasetId) {
    const ds = datasetList.find(d => d.dataset_id === datasetId);
    if (ds) {
        alert(`数据集详情:\n\n页码: ${ds.pages?.join(', ')}\n题目数: ${ds.question_count}\n创建时间: ${ds.created_at}\n\n基准效果:\n${JSON.stringify(ds.base_effects, null, 2)}`);
    }
}

async function deleteDataset(datasetId) {
    if (!confirm('确定要删除此数据集吗？')) return;
    
    showLoading('删除数据集...');
    
    try {
        const res = await fetch(`/api/batch/datasets/${datasetId}`, { method: 'DELETE' });
        const data = await res.json();
        
        if (data.success) {
            // 重新加载
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


// ========== 导入导出功能 ==========
let importData = null;

// 导出所有数据集
async function exportAllDatasets() {
    if (!selectedBook || datasetList.length === 0) {
        alert('当前书本没有数据集可导出');
        return;
    }
    
    showLoading('准备导出数据...');
    
    try {
        // 获取完整的数据集数据
        const fullDatasets = [];
        for (const ds of datasetList) {
            const res = await fetch(`/api/batch/datasets/${ds.dataset_id}`);
            const data = await res.json();
            if (data.success) {
                fullDatasets.push(data.data);
            }
        }
        
        const exportData = {
            book_id: selectedBook.book_id,
            book_name: selectedBook.book_name,
            subject_id: selectedBook.subject_id,
            export_time: new Date().toISOString(),
            datasets: fullDatasets
        };
        
        // 下载JSON文件
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `dataset_${selectedBook.book_name}_${new Date().toISOString().slice(0,10)}.json`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
        
        hideLoading();
    } catch (e) {
        hideLoading();
        alert('导出失败: ' + e.message);
    }
}

// 显示导入弹窗
function showImportModal() {
    importData = null;
    document.getElementById('importFileInput').value = '';
    document.getElementById('importPreview').style.display = 'none';
    document.getElementById('confirmImportBtn').disabled = true;
    document.getElementById('importModal').classList.add('show');
}

function hideImportModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('importModal').classList.remove('show');
}

// 预览导入文件
function previewImportFile() {
    const fileInput = document.getElementById('importFileInput');
    const file = fileInput.files[0];
    
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            importData = JSON.parse(e.target.result);
            
            // 验证数据格式
            if (!importData.datasets || !Array.isArray(importData.datasets)) {
                throw new Error('无效的数据格式');
            }
            
            // 显示预览
            const previewContent = document.getElementById('importPreviewContent');
            previewContent.innerHTML = `
                <div class="preview-item"><strong>来源书本:</strong> ${escapeHtml(importData.book_name || '未知')}</div>
                <div class="preview-item"><strong>导出时间:</strong> ${importData.export_time || '未知'}</div>
                <div class="preview-item"><strong>数据集数量:</strong> ${importData.datasets.length} 个</div>
                <div class="preview-item"><strong>包含页码:</strong> ${[...new Set(importData.datasets.flatMap(d => d.pages || []))].sort((a,b) => a-b).join(', ')}</div>
            `;
            
            document.getElementById('importPreview').style.display = 'block';
            document.getElementById('confirmImportBtn').disabled = false;
            
        } catch (err) {
            alert('文件解析失败: ' + err.message);
            importData = null;
            document.getElementById('importPreview').style.display = 'none';
            document.getElementById('confirmImportBtn').disabled = true;
        }
    };
    reader.readAsText(file);
}

// 确认导入
async function confirmImport() {
    if (!importData || !importData.datasets || !selectedBook) {
        alert('没有可导入的数据');
        return;
    }
    
    showLoading('正在导入数据集...');
    
    let successCount = 0;
    let failCount = 0;
    
    for (const ds of importData.datasets) {
        try {
            // 为每个页码的基准效果添加题目类型信息
            const enrichedBaseEffects = {};
            for (const [page, effects] of Object.entries(ds.base_effects || {})) {
                if (effects && effects.length > 0) {
                    try {
                        const enrichRes = await fetch('/api/batch/datasets/enrich-base-effects', {
                            method: 'POST',
                            headers: { 'Content-Type': 'application/json' },
                            body: JSON.stringify({
                                book_id: selectedBook.book_id,
                                page_num: parseInt(page),
                                base_effects: effects
                            })
                        });
                        const enrichData = await enrichRes.json();
                        
                        if (enrichData.success && enrichData.data) {
                            enrichedBaseEffects[page] = enrichData.data;
                        } else {
                            enrichedBaseEffects[page] = effects;
                        }
                    } catch (e) {
                        enrichedBaseEffects[page] = effects;
                    }
                }
            }
            
            const res = await fetch('/api/batch/datasets', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    book_id: selectedBook.book_id,
                    pages: ds.pages || [],
                    base_effects: enrichedBaseEffects
                })
            });
            const data = await res.json();
            
            if (data.success) {
                successCount++;
            } else {
                failCount++;
            }
        } catch (e) {
            failCount++;
        }
    }
    
    hideLoading();
    hideImportModal();
    
    alert(`导入完成！成功: ${successCount} 个，失败: ${failCount} 个`);
    
    // 重新加载数据集列表
    const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedBook.book_id}`);
    const datasetsData = await datasetsRes.json();
    if (datasetsData.success) {
        datasetList = datasetsData.data || [];
    }
    renderBookDetail();
}

// 导出单个数据集
async function exportDataset(datasetId) {
    showLoading('准备导出...');
    
    try {
        const res = await fetch(`/api/batch/datasets/${datasetId}`);
        const data = await res.json();
        
        if (data.success) {
            const exportData = {
                book_id: selectedBook.book_id,
                book_name: selectedBook.book_name,
                export_time: new Date().toISOString(),
                datasets: [data.data]
            };
            
            const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = `dataset_pages_${data.data.pages?.join('-')}.json`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
        }
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
    
    hideLoading();
}


// ========== 编辑数据集功能 ==========
let editingDataset = null;
let editingData = {};  // 按页码存储编辑中的数据
let currentEditPage = null;

// 打开编辑弹窗
async function editDataset(datasetId) {
    showLoading('加载数据集详情...');
    
    try {
        const res = await fetch(`/api/batch/datasets/${datasetId}`);
        const data = await res.json();
        
        if (!data.success) {
            alert('加载失败: ' + (data.error || '未知错误'));
            hideLoading();
            return;
        }
        
        editingDataset = data.data;
        editingData = JSON.parse(JSON.stringify(editingDataset.base_effects || {}));
        
        // 渲染页码标签
        renderEditPageTabs();
        
        // 选择第一个页码
        const pages = Object.keys(editingData).map(Number).sort((a, b) => a - b);
        if (pages.length > 0) {
            selectEditPage(pages[0]);
        } else {
            document.getElementById('editTableBody').innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">暂无数据</td></tr>';
        }
        
        // 显示弹窗
        document.getElementById('editModal').classList.add('show');
        
    } catch (e) {
        alert('加载失败: ' + e.message);
    }
    
    hideLoading();
}

// 隐藏编辑弹窗
function hideEditModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('editModal').classList.remove('show');
    editingDataset = null;
    editingData = {};
    currentEditPage = null;
}

// 渲染页码标签
function renderEditPageTabs() {
    const container = document.getElementById('editPageTabs');
    const pages = Object.keys(editingData).map(Number).sort((a, b) => a - b);
    
    container.innerHTML = pages.map(page => 
        `<div class="edit-page-tab ${currentEditPage === page ? 'active' : ''}" 
              onclick="selectEditPage(${page})">第 ${page} 页</div>`
    ).join('');
}

// 选择编辑页码
function selectEditPage(page) {
    currentEditPage = page;
    renderEditPageTabs();
    renderEditTable();
}

// 渲染编辑表格
function renderEditTable() {
    const tbody = document.getElementById('editTableBody');
    const data = editingData[currentEditPage] || [];
    
    if (data.length === 0) {
        tbody.innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">暂无题目数据</td></tr>';
        return;
    }
    
    tbody.innerHTML = data.map((item, idx) => {
        // 统一使用 correct 字段 ("yes"/"no")
        const isCorrect = item.correct === 'yes';
        return `
        <tr data-idx="${idx}">
            <td><input type="text" class="edit-input" value="${escapeHtml(item.index || '')}" 
                       onchange="updateEditCell(${idx}, 'index', this.value)"></td>
            <td><input type="text" class="edit-input" value="${escapeHtml(item.answer || '')}" 
                       onchange="updateEditCell(${idx}, 'answer', this.value)"></td>
            <td><input type="text" class="edit-input" value="${escapeHtml(item.userAnswer || '')}" 
                       onchange="updateEditCell(${idx}, 'userAnswer', this.value)"></td>
            <td>
                <select class="edit-select" onchange="updateEditCell(${idx}, 'correct', this.value)">
                    <option value="yes" ${isCorrect ? 'selected' : ''}>正确</option>
                    <option value="no" ${!isCorrect ? 'selected' : ''}>错误</option>
                </select>
            </td>
            <td><button class="btn-delete-row" onclick="deleteEditRow(${idx})">×</button></td>
        </tr>
    `}).join('');
}

// 更新编辑单元格
function updateEditCell(idx, field, value) {
    if (editingData[currentEditPage] && editingData[currentEditPage][idx]) {
        editingData[currentEditPage][idx][field] = value;
    }
}

// 删除编辑行
function deleteEditRow(idx) {
    if (editingData[currentEditPage]) {
        editingData[currentEditPage].splice(idx, 1);
        renderEditTable();
    }
}

// 添加编辑行
function addEditRow() {
    if (!currentEditPage) return;
    
    if (!editingData[currentEditPage]) {
        editingData[currentEditPage] = [];
    }
    
    const data = editingData[currentEditPage];
    const lastItem = data[data.length - 1];
    const newIndex = lastItem ? (parseInt(lastItem.index) + 1).toString() : '1';
    
    data.push({
        index: newIndex,
        answer: '',
        userAnswer: '',
        correct: 'yes',
        type: 'choice'
    });
    
    renderEditTable();
    
    // 滚动到底部
    const container = document.getElementById('editTableContainer');
    container.scrollTop = container.scrollHeight;
}

// 保存编辑的数据集
async function saveEditDataset() {
    if (!editingDataset) {
        alert('没有正在编辑的数据集');
        return;
    }
    
    showLoading('保存修改...');
    
    try {
        const res = await fetch(`/api/batch/datasets/${editingDataset.dataset_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effects: editingData
            })
        });
        const data = await res.json();
        
        if (data.success) {
            alert('保存成功！');
            hideEditModal();
            
            // 重新加载数据集列表
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


// ========== 数据集概览功能（首页默认显示） ==========
let allBooksWithDatasets = [];  // 所有有数据集的书本

// 页面加载时加载概览
async function loadDatasetOverview() {
    const container = document.getElementById('overviewBookList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        // 获取所有有数据集的书本
        const res = await fetch('/api/batch/datasets/all-books');
        const data = await res.json();
        
        if (data.success) {
            allBooksWithDatasets = data.data || [];
            renderOverviewBookList();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

// 渲染概览书本列表
function renderOverviewBookList() {
    const container = document.getElementById('overviewBookList');
    const statsContainer = document.getElementById('overviewStats');
    
    if (allBooksWithDatasets.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集，请从左侧选择图书添加</div></div>';
        statsContainer.innerHTML = '';
        return;
    }
    
    // 统计
    const totalBooks = allBooksWithDatasets.length;
    const totalDatasets = allBooksWithDatasets.reduce((sum, b) => sum + (b.dataset_count || 0), 0);
    const totalQuestions = allBooksWithDatasets.reduce((sum, b) => sum + (b.question_count || 0), 0);
    
    statsContainer.innerHTML = `
        <div class="overview-stat-card">
            <div class="overview-stat-num">${totalBooks}</div>
            <div class="overview-stat-label">本书</div>
        </div>
        <div class="overview-stat-card">
            <div class="overview-stat-num">${totalDatasets}</div>
            <div class="overview-stat-label">数据集</div>
        </div>
        <div class="overview-stat-card">
            <div class="overview-stat-num">${totalQuestions}</div>
            <div class="overview-stat-label">题目</div>
        </div>
    `;
    
    // 按学科分组
    const bySubject = {};
    allBooksWithDatasets.forEach(book => {
        const subjectId = book.subject_id || 0;
        if (!bySubject[subjectId]) {
            bySubject[subjectId] = [];
        }
        bySubject[subjectId].push(book);
    });
    
    let html = '';
    for (const [subjectId, books] of Object.entries(bySubject)) {
        html += `
            <div class="overview-subject-group">
                <div class="overview-subject-header">
                    <span class="overview-subject-tag">${SUBJECT_NAMES[subjectId] || '未知学科'}</span>
                    <span class="overview-subject-count">${books.length} 本书</span>
                </div>
                <div class="overview-book-grid">
                    ${books.map(book => `
                        <div class="overview-book-card" onclick="goToBookDetail('${book.book_id}', ${subjectId})">
                            <div class="overview-book-header">
                                <div class="overview-book-name" title="${escapeHtml(book.book_name)}">${escapeHtml(book.book_name)}</div>
                            </div>
                            <div class="overview-book-stats">
                                <div class="overview-book-stat">
                                    <span class="stat-value">${book.dataset_count || 0}</span>
                                    <span class="stat-label">数据集</span>
                                </div>
                                <div class="overview-book-stat">
                                    <span class="stat-value">${book.question_count || 0}</span>
                                    <span class="stat-label">题目</span>
                                </div>
                                <div class="overview-book-stat">
                                    <span class="stat-value">${book.pages?.length || 0}</span>
                                    <span class="stat-label">页码</span>
                                </div>
                            </div>
                            <div class="overview-book-pages">
                                <span class="pages-label">覆盖页码:</span>
                                <span class="pages-list">${book.pages?.slice(0, 8).join(', ') || '-'}${book.pages?.length > 8 ? ' ...' : ''}</span>
                            </div>
                        </div>
                    `).join('')}
                </div>
            </div>
        `;
    }
    
    container.innerHTML = html;
}

// 点击概览中的书本，跳转到详情
async function goToBookDetail(bookId, subjectId) {
    // 隐藏概览，显示详情
    document.getElementById('datasetOverview').style.display = 'none';
    
    // 调用选择书本的逻辑
    await selectBook(bookId, subjectId);
}

// 返回概览
function backToOverview() {
    selectedBook = null;
    datasetList = [];
    currentView = 'overview';
    
    // 重置左侧选中状态
    renderBooks();
    
    // 隐藏详情，显示概览
    document.getElementById('bookDetail').style.display = 'none';
    document.getElementById('addDatasetPanel').style.display = 'none';
    document.getElementById('datasetOverview').style.display = 'block';
    
    // 刷新概览数据
    loadDatasetOverview();
}



// ========== 效果矫正功能 ==========
let correctionModal = null;
let correctionPage = null;
let aiResultData = null;

// 显示效果矫正弹窗
async function showEffectCorrection(page) {
    correctionPage = page;
    const hw = selectedHomework[page];
    
    if (!hw) {
        alert('未找到该页码的作业信息');
        return;
    }
    
    showLoading('加载AI批改结果...');
    
    try {
        // 获取AI批改结果
        const res = await fetch(`/api/dataset/homework-result/${hw.id}`);
        const data = await res.json();
        
        if (!data.success) {
            alert('获取AI批改结果失败: ' + (data.error || '未知错误'));
            hideLoading();
            return;
        }
        
        aiResultData = data.data.homework_result || [];
        
        // 渲染效果矫正弹窗
        renderCorrectionModal(page);
        
    } catch (e) {
        alert('获取AI批改结果失败: ' + e.message);
    }
    
    hideLoading();
}

// 渲染效果矫正弹窗
function renderCorrectionModal(page) {
    const baseEffects = recognizeResults[page]?.data || [];
    
    // 创建弹窗HTML
    const modalHtml = `
        <div class="correction-modal show" id="correctionModal" onclick="hideCorrectionModal(event)">
            <div class="correction-modal-content" onclick="event.stopPropagation()">
                <div class="correction-modal-header">
                    <h3>效果矫正 - 第 ${page} 页</h3>
                    <button class="close-btn" onclick="hideCorrectionModal()">x</button>
                </div>
                <div class="correction-modal-body">
                    <div class="correction-split">
                        <div class="correction-left">
                            <div class="correction-panel-title">基准效果 (可编辑)</div>
                            <div class="correction-table-wrap">
                                <table class="correction-table">
                                    <thead>
                                        <tr>
                                            <th class="col-index">题号</th>
                                            <th>手写答案</th>
                                            <th class="col-tempindex">tempIndex</th>
                                        </tr>
                                    </thead>
                                    <tbody id="correctionBaseBody">
                                        ${baseEffects.map((item, idx) => `
                                            <tr data-idx="${idx}" class="${getMatchClass(item.tempIndex, aiResultData)}">
                                                <td class="col-index">
                                                    <input type="text" class="correction-input index-input" value="${escapeHtml(item.index || '')}" 
                                                           onchange="updateCorrectionCell(${idx}, 'index', this.value)">
                                                </td>
                                                <td>
                                                    <textarea class="correction-textarea" 
                                                              onchange="updateCorrectionCell(${idx}, 'userAnswer', this.value)">${escapeHtml(item.userAnswer || '')}</textarea>
                                                </td>
                                                <td class="col-tempindex">
                                                    <input type="number" class="correction-input tempindex-input" 
                                                           value="${item.tempIndex !== undefined ? item.tempIndex : ''}" 
                                                           onchange="updateCorrectionCell(${idx}, 'tempIndex', parseInt(this.value))">
                                                </td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                            <div class="correction-actions">
                                <button class="btn-add-row" onclick="addCorrectionRow()">+ 添加题目</button>
                            </div>
                        </div>
                        <div class="correction-right">
                            <div class="correction-panel-title">AI批改结果 (只读)</div>
                            <div class="correction-table-wrap">
                                <table class="correction-table">
                                    <thead>
                                        <tr>
                                            <th class="col-index">题号</th>
                                            <th>手写答案</th>
                                            <th class="col-tempindex">tempIndex</th>
                                        </tr>
                                    </thead>
                                    <tbody id="correctionAiBody">
                                        ${aiResultData.map((item, idx) => `
                                            <tr data-idx="${idx}" class="${getMatchClass(item.tempIndex, baseEffects)}">
                                                <td class="col-index">${escapeHtml(item.index || '')}</td>
                                                <td class="ai-answer-cell">${escapeHtml(item.userAnswer || '')}</td>
                                                <td class="col-tempindex tempindex-cell">${item.tempIndex !== undefined ? item.tempIndex : '-'}</td>
                                            </tr>
                                        `).join('')}
                                    </tbody>
                                </table>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="correction-modal-footer">
                    <div class="correction-stats">
                        <span class="stat-matched">匹配: ${countMatched(baseEffects, aiResultData)} 题</span>
                        <span class="stat-unmatched">未匹配: ${countUnmatched(baseEffects, aiResultData)} 题</span>
                    </div>
                    <div class="correction-buttons">
                        <button class="btn btn-secondary" onclick="hideCorrectionModal()">取消</button>
                        <button class="btn btn-primary" onclick="saveCorrectionChanges()">保存修改</button>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 移除旧弹窗
    const oldModal = document.getElementById('correctionModal');
    if (oldModal) oldModal.remove();
    
    // 添加新弹窗
    document.body.insertAdjacentHTML('beforeend', modalHtml);
}

// 获取匹配状态的CSS类
function getMatchClass(tempIndex, compareData) {
    if (tempIndex === undefined || tempIndex === null) return 'row-warning';
    const found = compareData.find(item => item.tempIndex === tempIndex);
    return found ? 'row-matched' : 'row-unmatched';
}

// 统计匹配数量
function countMatched(baseEffects, aiResults) {
    const aiTempIndexes = new Set(aiResults.map(item => item.tempIndex).filter(t => t !== undefined));
    return baseEffects.filter(item => item.tempIndex !== undefined && aiTempIndexes.has(item.tempIndex)).length;
}

// 统计未匹配数量
function countUnmatched(baseEffects, aiResults) {
    const aiTempIndexes = new Set(aiResults.map(item => item.tempIndex).filter(t => t !== undefined));
    return baseEffects.filter(item => item.tempIndex === undefined || !aiTempIndexes.has(item.tempIndex)).length;
}

// 更新矫正单元格
function updateCorrectionCell(idx, field, value) {
    if (recognizeResults[correctionPage] && recognizeResults[correctionPage].data && recognizeResults[correctionPage].data[idx]) {
        recognizeResults[correctionPage].data[idx][field] = value;
        // 重新渲染以更新匹配状态
        renderCorrectionModal(correctionPage);
    }
}

// 添加矫正行
function addCorrectionRow() {
    if (!correctionPage || !recognizeResults[correctionPage]) return;
    
    const data = recognizeResults[correctionPage].data || [];
    const lastItem = data[data.length - 1];
    const newIndex = lastItem ? (parseInt(lastItem.index) + 1).toString() : '1';
    const newTempIndex = lastItem && lastItem.tempIndex !== undefined ? lastItem.tempIndex + 1 : 0;
    
    data.push({
        index: newIndex,
        userAnswer: '',
        correct: 'yes',
        tempIndex: newTempIndex
    });
    
    recognizeResults[correctionPage].data = data;
    renderCorrectionModal(correctionPage);
}

// 保存矫正修改
function saveCorrectionChanges() {
    // 数据已经实时更新到 recognizeResults 中
    hideCorrectionModal();
    // 重新渲染识别结果表格
    renderRecognizePreview();
    checkCanSave();
}

// 隐藏效果矫正弹窗
function hideCorrectionModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('correctionModal');
    if (modal) modal.remove();
    correctionPage = null;
    aiResultData = null;
}
