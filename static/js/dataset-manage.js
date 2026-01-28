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
                    <div class="dataset-title">${escapeHtml(ds.name) || '未命名数据集'}</div>
                    <div class="dataset-meta">页码: ${ds.pages?.join(', ') || '-'} | ${ds.question_count || 0} 题 | 创建于 ${formatTime(ds.created_at)}</div>
                </div>
                <div class="dataset-actions">
                    <button class="btn btn-small btn-secondary" onclick="showAddToCollectionModal('${ds.dataset_id}', '${escapeHtml(ds.name || '')}')">加入合集</button>
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
    
    // 重置命名输入
    const nameInput = document.getElementById('datasetNameInput');
    const descInput = document.getElementById('datasetDescInput');
    if (nameInput) nameInput.value = '';
    if (descInput) descInput.value = '';
    
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
    document.getElementById('step4Section').style.display = 'none';
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
    // 检查是否有分数数据
    const hasScore = data.some(item => item.maxScore !== undefined || item.score !== undefined);
    
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
                    ${hasScore ? '<th class="col-maxscore">总分</th><th class="col-score">得分</th>' : ''}
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
                            <select onchange="updateTableCell(${page}, ${idx}, 'correct', this.value); autoUpdateScore(${page}, ${idx})">
                                <option value="yes" ${item.correct === 'yes' ? 'selected' : ''}>正确</option>
                                <option value="no" ${item.correct === 'no' || item.correct !== 'yes' ? 'selected' : ''}>错误</option>
                            </select>
                        </td>
                        ${hasScore ? `
                        <td class="col-maxscore">
                            <input type="number" class="maxscore-input" value="${item.maxScore !== undefined && item.maxScore !== null ? item.maxScore : ''}" 
                                   onchange="updateTableCell(${page}, ${idx}, 'maxScore', this.value ? parseFloat(this.value) : null)" step="0.5" min="0">
                        </td>
                        <td class="col-score">
                            <input type="number" class="score-input" value="${item.score !== undefined && item.score !== null ? item.score : ''}" 
                                   onchange="updateTableCell(${page}, ${idx}, 'score', this.value ? parseFloat(this.value) : null)" step="0.5" min="0">
                        </td>
                        ` : ''}
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

// 自动更新得分（当正确性改变时）
function autoUpdateScore(page, idx) {
    if (!recognizeResults[page]?.data?.[idx]) return;
    const item = recognizeResults[page].data[idx];
    
    // 只有当有 maxScore 时才自动更新 score
    if (item.maxScore !== undefined && item.maxScore !== null) {
        const newScore = item.correct === 'yes' ? item.maxScore : 0;
        item.score = newScore;
        
        // 更新输入框显示
        const row = document.querySelector(`#resultTableBody_${page} tr[data-idx="${idx}"]`);
        if (row) {
            const scoreInput = row.querySelector('.score-input');
            if (scoreInput) {
                scoreInput.value = newScore;
            }
        }
    }
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
    const step4Section = document.getElementById('step4Section');
    
    if (canSave) {
        // 显示步骤4（命名区域）
        if (step4Section) {
            step4Section.style.display = 'block';
            // 如果名称输入框为空，生成默认名称
            const nameInput = document.getElementById('datasetNameInput');
            if (nameInput && !nameInput.value.trim()) {
                nameInput.value = generateDefaultName();
            }
        }
        saveSection.style.display = 'block';
        // 更新保存按钮文案，显示成功/失败数量
        const saveBtn = saveSection.querySelector('.btn-primary');
        if (failCount > 0) {
            saveBtn.innerHTML = `保存数据集 (${successCount}/${pages.length} 页成功)`;
        } else {
            saveBtn.innerHTML = '保存数据集';
        }
    } else {
        if (step4Section) {
            step4Section.style.display = 'none';
        }
        saveSection.style.display = 'none';
    }
}

// ========== 数据集命名相关函数 ==========

// 生成默认数据集名称
function generateDefaultName() {
    const bookName = selectedBook?.book_name || '未知书本';
    const pages = Object.keys(selectedHomework).map(Number).sort((a, b) => a - b);
    let pageRange = '';
    if (pages.length === 1) {
        pageRange = `P${pages[0]}`;
    } else if (pages.length > 1) {
        pageRange = `P${pages[0]}-${pages[pages.length - 1]}`;
    }
    const now = new Date();
    const timestamp = `${String(now.getMonth() + 1).padStart(2, '0')}${String(now.getDate()).padStart(2, '0')}${String(now.getHours()).padStart(2, '0')}${String(now.getMinutes()).padStart(2, '0')}`;
    return `${bookName}_${pageRange}_${timestamp}`;
}

// 检查重复数据集
async function checkDuplicateDatasets() {
    const pages = Object.keys(selectedHomework).map(Number).sort((a, b) => a - b);
    if (pages.length === 0) return { hasDuplicate: false, duplicates: [] };
    
    try {
        const res = await fetch(`/api/batch/datasets/check-duplicate?book_id=${selectedBook.book_id}&pages=${pages.join(',')}`);
        const data = await res.json();
        return {
            hasDuplicate: data.has_duplicate || false,
            duplicates: data.duplicates || []
        };
    } catch (e) {
        console.error('Check duplicate failed:', e);
        return { hasDuplicate: false, duplicates: [] };
    }
}

// 显示重复检测弹窗
function showDuplicateModal(duplicates) {
    window.pendingDuplicates = duplicates;
    const list = document.getElementById('duplicateList');
    list.innerHTML = duplicates.map(ds => `
        <div class="duplicate-item" data-id="${ds.dataset_id}">
            <div class="duplicate-item-name">${escapeHtml(ds.name) || '未命名数据集'}</div>
            <div class="duplicate-item-meta">
                <span>页码: ${ds.pages?.join(', ') || '-'}</span>
                <span>${ds.question_count || 0} 题</span>
                <span>${formatTime(ds.created_at)}</span>
            </div>
        </div>
    `).join('');
    document.getElementById('duplicateModal').classList.add('show');
}

// 隐藏重复检测弹窗
function hideDuplicateModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('duplicateModal').classList.remove('show');
    window.pendingDuplicates = null;
}

// 编辑现有数据集
function editExistingDataset() {
    const duplicates = window.pendingDuplicates || [];
    if (duplicates.length > 0) {
        hideDuplicateModal();
        editDataset(duplicates[0].dataset_id);
    }
}

// 继续创建新数据集
function continueCreateNew() {
    hideDuplicateModal();
    proceedWithSave();
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
    
    // 获取数据集名称
    const nameInput = document.getElementById('datasetNameInput');
    let datasetName = (nameInput?.value || '').trim();
    
    // 如果名称为空，生成默认名称
    if (!datasetName) {
        datasetName = generateDefaultName();
        if (nameInput) {
            nameInput.value = datasetName;
        }
    }
    
    // 检查重复数据集
    showLoading('检查重复数据集...');
    const { hasDuplicate, duplicates } = await checkDuplicateDatasets();
    hideLoading();
    
    if (hasDuplicate && duplicates.length > 0) {
        // 保存当前状态供后续使用
        window.pendingSaveData = {
            successPages,
            baseEffects,
            failedPages,
            datasetName
        };
        showDuplicateModal(duplicates);
        return;
    }
    
    // 没有重复，直接保存
    window.pendingSaveData = {
        successPages,
        baseEffects,
        failedPages,
        datasetName
    };
    await proceedWithSave();
}

// 执行实际的保存操作
async function proceedWithSave() {
    const saveData = window.pendingSaveData;
    if (!saveData) {
        alert('保存数据丢失，请重试');
        return;
    }
    
    const { successPages, baseEffects, failedPages, datasetName } = saveData;
    
    // 获取描述
    const descInput = document.getElementById('datasetDescInput');
    const description = (descInput?.value || '').trim();
    
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
                base_effects: enrichedBaseEffects,
                name: datasetName,
                description: description
            })
        });
        const data = await res.json();
        
        if (data.success) {
            let msg = '数据集保存成功！';
            if (failedPages.length > 0) {
                msg += `\n\n已保存 ${successPages.length} 个页码，跳过了 ${failedPages.length} 个识别失败的页码。`;
            }
            alert(msg);
            // 清理临时数据
            window.pendingSaveData = null;
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
let pageImageUrls = {};  // 每个页码对应的图片信息
let reRecognizeImages = [];  // 重新识别可用的图片列表
let selectedReRecognizeImage = null;  // 选中用于重新识别的图片
let deletedPages = [];  // 记录已删除的页码

// 打开编辑弹窗
async function editDataset(datasetId) {
    showLoading('加载数据集详情...');
    
    // 重置状态
    pageImageUrls = {};
    reRecognizeImages = [];
    selectedReRecognizeImage = null;
    deletedPages = [];
    
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
        
        // 显示页面操作区
        document.getElementById('editPageActions').style.display = 'flex';
        
        // 隐藏重新识别面板
        document.getElementById('reRecognizePanel').style.display = 'none';
        
        // 渲染页码标签
        renderEditPageTabs();
        
        // 选择第一个页码
        const pages = Object.keys(editingData).map(Number).sort((a, b) => a - b);
        if (pages.length > 0) {
            selectEditPage(pages[0]);
        } else {
            document.getElementById('editTableBody').innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">暂无数据</td></tr>';
            // 隐藏页面操作区
            document.getElementById('editPageActions').style.display = 'none';
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
    pageImageUrls = {};
    reRecognizeImages = [];
    selectedReRecognizeImage = null;
    deletedPages = [];
    hideReRecognizePanel();
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
async function selectEditPage(page) {
    currentEditPage = page;
    renderEditPageTabs();
    renderEditTable();
    
    // 加载并显示当前页的图片预览
    await loadPageImagePreview(page);
    
    // 隐藏重新识别面板
    hideReRecognizePanel();
}

// 加载页面图片预览
async function loadPageImagePreview(page) {
    const previewImg = document.getElementById('pagePreviewImg');
    const noImagePlaceholder = document.getElementById('noImagePlaceholder');
    
    if (!editingDataset || !editingDataset.book_id) {
        previewImg.style.display = 'none';
        noImagePlaceholder.style.display = 'flex';
        return;
    }
    
    try {
        const res = await fetch(`/api/dataset/page-image-info?book_id=${editingDataset.book_id}&page_num=${page}`);
        const data = await res.json();
        
        if (data.success && data.data && data.data.has_image && data.data.pic_url) {
            previewImg.src = data.data.pic_url;
            previewImg.style.display = 'block';
            noImagePlaceholder.style.display = 'none';
            
            // 保存图片信息供重新识别使用
            pageImageUrls[page] = data.data;
        } else {
            previewImg.style.display = 'none';
            noImagePlaceholder.style.display = 'flex';
            pageImageUrls[page] = null;
        }
    } catch (e) {
        console.error('加载页面图片失败:', e);
        previewImg.style.display = 'none';
        noImagePlaceholder.style.display = 'flex';
    }
}

// 渲染编辑表格
function renderEditTable() {
    const tbody = document.getElementById('editTableBody');
    const data = editingData[currentEditPage] || [];
    
    // 检查是否有分数数据（兼容 maxScore、score、sorce 三种字段名，且值不为 null/undefined）
    const hasScore = data.some(item => 
        (item.maxScore !== undefined && item.maxScore !== null) || 
        (item.score !== undefined && item.score !== null) ||
        (item.sorce !== undefined && item.sorce !== null)
    );
    
    // 更新表头
    const thead = document.querySelector('#editTableContainer table thead tr');
    if (thead) {
        thead.innerHTML = `
            <th>题号</th>
            <th>标准答案</th>
            <th>学生答案</th>
            <th>是否正确</th>
            ${hasScore ? '<th style="width:60px">总分</th><th style="width:60px">得分</th>' : ''}
            <th>操作</th>
        `;
    }
    
    if (data.length === 0) {
        tbody.innerHTML = `<tr><td colspan="${hasScore ? 7 : 5}" style="text-align:center;color:#999;">暂无题目数据</td></tr>`;
        return;
    }
    
    tbody.innerHTML = data.map((item, idx) => {
        // 统一使用 correct 字段 ("yes"/"no")
        const isCorrect = item.correct === 'yes';
        // 兼容 maxScore 和 sorce 字段（原始数据中字段名是 sorce）
        const maxScoreValue = item.maxScore !== undefined && item.maxScore !== null 
            ? item.maxScore 
            : (item.sorce !== undefined && item.sorce !== null ? item.sorce : '');
        const scoreValue = item.score !== undefined && item.score !== null ? item.score : '';
        return `
        <tr data-idx="${idx}">
            <td><input type="text" class="edit-input" value="${escapeHtml(item.index || '')}" 
                       onchange="updateEditCell(${idx}, 'index', this.value)"></td>
            <td><input type="text" class="edit-input" value="${escapeHtml(item.answer || '')}" 
                       onchange="updateEditCell(${idx}, 'answer', this.value)"></td>
            <td><input type="text" class="edit-input" value="${escapeHtml(item.userAnswer || '')}" 
                       onchange="updateEditCell(${idx}, 'userAnswer', this.value)"></td>
            <td>
                <select class="edit-select" onchange="updateEditCell(${idx}, 'correct', this.value); autoUpdateEditScore(${idx})">
                    <option value="yes" ${isCorrect ? 'selected' : ''}>正确</option>
                    <option value="no" ${!isCorrect ? 'selected' : ''}>错误</option>
                </select>
            </td>
            ${hasScore ? `
            <td><input type="number" class="edit-input score-input" value="${maxScoreValue}" 
                       onchange="updateEditCell(${idx}, 'maxScore', this.value ? parseFloat(this.value) : null)" step="0.5" min="0"></td>
            <td><input type="number" class="edit-input score-input" value="${scoreValue}" 
                       onchange="updateEditCell(${idx}, 'score', this.value ? parseFloat(this.value) : null)" step="0.5" min="0"></td>
            ` : ''}
            <td><button class="btn-delete-row" onclick="deleteEditRow(${idx})">×</button></td>
        </tr>
    `}).join('');
}

// 自动更新编辑表格中的得分（当正确性改变时）
function autoUpdateEditScore(idx) {
    if (!editingData[currentEditPage]?.[idx]) return;
    const item = editingData[currentEditPage][idx];
    
    // 兼容 maxScore 和 sorce 字段
    const maxScore = item.maxScore !== undefined && item.maxScore !== null 
        ? item.maxScore 
        : (item.sorce !== undefined && item.sorce !== null ? item.sorce : null);
    
    // 只有当有 maxScore 时才自动更新 score
    if (maxScore !== null) {
        const newScore = item.correct === 'yes' ? maxScore : 0;
        item.score = newScore;
        // 同时更新 maxScore 字段（如果原来是 sorce）
        if (item.maxScore === undefined || item.maxScore === null) {
            item.maxScore = maxScore;
        }
        
        // 更新输入框显示
        const row = document.querySelector(`#editTableBody tr[data-idx="${idx}"]`);
        if (row) {
            const scoreInputs = row.querySelectorAll('.score-input');
            if (scoreInputs.length >= 2) {
                scoreInputs[1].value = newScore;
            }
        }
    }
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

// ========== 重新识别功能 ==========

// 显示重新识别面板
function showReRecognizePanel() {
    if (!currentEditPage) {
        alert('请先选择页码');
        return;
    }
    
    document.getElementById('reRecognizePanel').style.display = 'block';
    selectedReRecognizeImage = null;
    document.getElementById('startReRecognizeBtn').disabled = true;
    
    // 加载可用图片
    loadReRecognizeImages();
}

// 隐藏重新识别面板
function hideReRecognizePanel() {
    const panel = document.getElementById('reRecognizePanel');
    if (panel) {
        panel.style.display = 'none';
    }
    selectedReRecognizeImage = null;
    reRecognizeImages = [];
}

// 加载重新识别可用的图片
async function loadReRecognizeImages() {
    if (!editingDataset || !currentEditPage) return;
    
    const container = document.getElementById('reRecognizeImages');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    const hours = document.getElementById('reRecognizeTimeRange').value;
    
    try {
        const res = await fetch(`/api/dataset/available-homework?book_id=${editingDataset.book_id}&page_num=${currentEditPage}&hours=${hours}`);
        const data = await res.json();
        
        if (data.success && data.data && data.data.length > 0) {
            reRecognizeImages = data.data;
            renderReRecognizeImages();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无可用的作业图片，请调整时间范围</div></div>';
            reRecognizeImages = [];
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
        reRecognizeImages = [];
    }
}

// 渲染重新识别图片列表
function renderReRecognizeImages() {
    const container = document.getElementById('reRecognizeImages');
    
    if (reRecognizeImages.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无可用的作业图片</div></div>';
        return;
    }
    
    container.innerHTML = reRecognizeImages.map((img, idx) => `
        <div class="re-recognize-image-card ${selectedReRecognizeImage?.id === img.id ? 'selected' : ''}" 
             onclick="selectReRecognizeImage(${idx})">
            <img src="${img.pic_url || '/static/images/no-image.png'}" alt="作业图片" 
                 onerror="this.src='/static/images/no-image.png'">
            <div class="re-recognize-image-info">
                <div class="student-name">${escapeHtml(img.student_name || img.student_id || '未知学生')}</div>
                <div class="image-meta">ID: ${img.id} | ${formatTime(img.create_time)}</div>
            </div>
        </div>
    `).join('');
}

// 选择重新识别的图片
function selectReRecognizeImage(idx) {
    const img = reRecognizeImages[idx];
    if (!img) return;
    
    if (selectedReRecognizeImage?.id === img.id) {
        // 取消选择
        selectedReRecognizeImage = null;
    } else {
        selectedReRecognizeImage = img;
    }
    
    renderReRecognizeImages();
    document.getElementById('startReRecognizeBtn').disabled = !selectedReRecognizeImage;
}

// 开始重新识别
async function startReRecognize() {
    if (!selectedReRecognizeImage || !currentEditPage) {
        alert('请先选择一张图片');
        return;
    }
    
    const container = document.getElementById('reRecognizeImages');
    container.innerHTML = `
        <div class="re-recognize-loading">
            <div class="spinner"></div>
            <div class="loading-text">正在识别中，请稍候...</div>
        </div>
    `;
    
    document.getElementById('startReRecognizeBtn').disabled = true;
    
    try {
        const res = await fetch('/api/dataset/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                homework_id: selectedReRecognizeImage.id,
                pic_path: selectedReRecognizeImage.pic_path,
                subject_id: editingDataset.subject_id || selectedBook?.subject_id || 0
            })
        });
        
        const data = await res.json();
        
        if (data.success && data.data && data.data.length > 0) {
            // 更新当前页的数据
            editingData[currentEditPage] = data.data;
            
            // 更新图片信息
            pageImageUrls[currentEditPage] = {
                pic_url: selectedReRecognizeImage.pic_url,
                homework_id: selectedReRecognizeImage.id,
                has_image: true
            };
            
            // 更新图片预览
            const previewImg = document.getElementById('pagePreviewImg');
            const noImagePlaceholder = document.getElementById('noImagePlaceholder');
            previewImg.src = selectedReRecognizeImage.pic_url;
            previewImg.style.display = 'block';
            noImagePlaceholder.style.display = 'none';
            
            // 隐藏重新识别面板
            hideReRecognizePanel();
            
            // 重新渲染表格
            renderEditTable();
            
            alert(`识别成功！共识别 ${data.data.length} 道题目`);
        } else {
            alert('识别失败: ' + (data.error || '无法解析识别结果'));
            renderReRecognizeImages();
        }
    } catch (e) {
        alert('识别失败: ' + e.message);
        renderReRecognizeImages();
    }
    
    document.getElementById('startReRecognizeBtn').disabled = !selectedReRecognizeImage;
}

// ========== 删除页面功能 ==========

// 确认删除页面
function confirmDeletePage() {
    if (!currentEditPage) {
        alert('请先选择页码');
        return;
    }
    
    const pages = Object.keys(editingData).map(Number).sort((a, b) => a - b);
    
    if (pages.length === 1) {
        // 最后一页，需要二次确认
        if (confirm(`确定要删除第 ${currentEditPage} 页吗？\n\n这是数据集的最后一页，删除后整个数据集将被删除。`)) {
            executeDeletePage(currentEditPage);
        }
    } else {
        if (confirm(`确定要删除第 ${currentEditPage} 页吗？\n\n删除后该页的所有数据将被移除。`)) {
            executeDeletePage(currentEditPage);
        }
    }
}

// 执行删除页面
function executeDeletePage(page) {
    // 从编辑数据中删除该页
    delete editingData[page];
    
    // 记录已删除的页码
    if (!deletedPages.includes(page)) {
        deletedPages.push(page);
    }
    
    // 获取剩余页码
    const remainingPages = Object.keys(editingData).map(Number).sort((a, b) => a - b);
    
    if (remainingPages.length === 0) {
        // 没有剩余页码，提示用户保存将删除整个数据集
        alert('所有页面已删除，保存后将删除整个数据集。');
        currentEditPage = null;
        renderEditPageTabs();
        document.getElementById('editTableBody').innerHTML = '<tr><td colspan="5" style="text-align:center;color:#999;">所有页面已删除</td></tr>';
        
        // 隐藏页面操作区
        document.getElementById('editPageActions').style.display = 'none';
    } else {
        // 切换到下一个可用页码
        const nextPage = remainingPages.find(p => p > page) || remainingPages[0];
        selectEditPage(nextPage);
    }
}

// 保存编辑的数据集
async function saveEditDataset() {
    if (!editingDataset) {
        alert('没有正在编辑的数据集');
        return;
    }
    
    // 检查是否所有页面都被删除
    const remainingPages = Object.keys(editingData).filter(p => editingData[p] && editingData[p].length > 0);
    
    if (remainingPages.length === 0) {
        // 所有页面都被删除，确认删除整个数据集
        if (!confirm('所有页面已删除，确定要删除整个数据集吗？')) {
            return;
        }
    }
    
    showLoading('保存修改...');
    
    try {
        // 构建更新数据，将删除的页码设置为空数组
        const updateEffects = { ...editingData };
        
        // 将已删除的页码标记为空数组（后端会处理删除）
        for (const page of deletedPages) {
            updateEffects[page] = [];
        }
        
        const res = await fetch(`/api/batch/datasets/${editingDataset.dataset_id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                base_effects: updateEffects
            })
        });
        const data = await res.json();
        
        if (data.success) {
            if (data.deleted) {
                // 整个数据集被删除
                alert('数据集已删除');
            } else {
                alert('保存成功！');
            }
            hideEditModal();
            
            // 重新加载数据集列表
            if (selectedBook && selectedBook.book_id) {
                const datasetsRes = await fetch(`/api/batch/datasets?book_id=${selectedBook.book_id}`);
                const datasetsData = await datasetsRes.json();
                if (datasetsData.success) {
                    datasetList = datasetsData.data || [];
                }
                renderBookDetail();
            }
            
            // 刷新概览
            loadDatasetOverview();
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
    
    // 检查是否有分数数据
    const hasScore = baseEffects.some(item => item.maxScore !== undefined || item.score !== undefined) ||
                     aiResultData.some(item => item.score !== undefined);
    
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
                                            ${hasScore ? '<th class="col-score">得分</th>' : ''}
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
                                                ${hasScore ? `
                                                <td class="col-score">
                                                    <input type="number" class="correction-input score-input" 
                                                           value="${item.score !== undefined && item.score !== null ? item.score : ''}" 
                                                           onchange="updateCorrectionCell(${idx}, 'score', this.value ? parseFloat(this.value) : null)"
                                                           step="0.5" min="0">
                                                </td>
                                                ` : ''}
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
                                            ${hasScore ? '<th class="col-score">得分</th>' : ''}
                                            <th class="col-tempindex">tempIndex</th>
                                        </tr>
                                    </thead>
                                    <tbody id="correctionAiBody">
                                        ${aiResultData.map((item, idx) => `
                                            <tr data-idx="${idx}" class="${getMatchClass(item.tempIndex, baseEffects)}">
                                                <td class="col-index">${escapeHtml(item.index || '')}</td>
                                                <td class="ai-answer-cell">${escapeHtml(item.userAnswer || '')}</td>
                                                ${hasScore ? `<td class="col-score ai-score-cell">${item.score !== undefined && item.score !== null ? item.score : '-'}</td>` : ''}
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


// ========== 全局效果矫正功能（多页码） ==========
// 与单页效果矫正逻辑一致：只比对题号(index)和索引(tempIndex)是否匹配
let globalCorrectionData = {};  // 存储所有页码的矫正数据
let currentCorrectionPage = null;  // 当前选中的页码

/**
 * 显示全局效果矫正弹窗
 * 左右对比所有页码的基准效果与AI批改结果的题号/tempIndex
 */
async function showEffectCorrectionModal() {
    const pages = Object.keys(recognizeResults)
        .filter(p => recognizeResults[p]?.success && recognizeResults[p]?.data?.length > 0)
        .map(Number)
        .sort((a, b) => a - b);
    
    if (pages.length === 0) {
        alert('没有可用的识别结果，请先完成识别');
        return;
    }
    
    // 重置数据
    globalCorrectionData = {};
    
    // 显示弹窗
    document.getElementById('correctionModal').classList.add('show');
    document.getElementById('correctionLoading').style.display = 'flex';
    document.getElementById('correctionTableContainer').style.display = 'none';
    document.getElementById('correctionEmpty').style.display = 'none';
    
    // 加载所有页码的AI批改结果
    let totalMatched = 0;
    let totalUnmatched = 0;
    
    for (const page of pages) {
        const hw = selectedHomework[page];
        if (!hw) continue;
        
        try {
            const res = await fetch(`/api/dataset/homework-result/${hw.id}`);
            const data = await res.json();
            
            if (data.success) {
                const baseEffects = recognizeResults[page]?.data || [];
                const aiResults = data.data.homework_result || [];
                
                // 统计匹配情况（只比对tempIndex）
                const matched = countMatchedByTempIndex(baseEffects, aiResults);
                const unmatched = countUnmatchedByTempIndex(baseEffects, aiResults);
                
                globalCorrectionData[page] = {
                    baseEffects: baseEffects,
                    aiResults: aiResults,
                    matchedCount: matched,
                    unmatchedCount: unmatched
                };
                
                totalMatched += matched;
                totalUnmatched += unmatched;
            }
        } catch (e) {
            console.error(`加载第 ${page} 页AI批改结果失败:`, e);
        }
    }
    
    // 隐藏加载状态
    document.getElementById('correctionLoading').style.display = 'none';
    
    // 更新统计信息
    document.getElementById('correctionSummary').innerHTML = 
        `匹配: <span class="match-count">${totalMatched}</span> 题 | 未匹配: <span class="diff-count">${totalUnmatched}</span> 题`;
    
    // 渲染页码标签
    renderGlobalCorrectionPageTabs(pages);
    
    // 默认选中第一个有未匹配项的页码，或第一个页码
    const firstUnmatchedPage = pages.find(p => globalCorrectionData[p]?.unmatchedCount > 0) || pages[0];
    selectGlobalCorrectionPage(firstUnmatchedPage);
}

/**
 * 统计匹配数量（按tempIndex）
 */
function countMatchedByTempIndex(baseEffects, aiResults) {
    const aiTempIndexes = new Set(
        aiResults.map(item => item.tempIndex).filter(t => t !== undefined && t !== null)
    );
    return baseEffects.filter(item => 
        item.tempIndex !== undefined && item.tempIndex !== null && aiTempIndexes.has(item.tempIndex)
    ).length;
}

/**
 * 统计未匹配数量（按tempIndex）
 */
function countUnmatchedByTempIndex(baseEffects, aiResults) {
    const aiTempIndexes = new Set(
        aiResults.map(item => item.tempIndex).filter(t => t !== undefined && t !== null)
    );
    return baseEffects.filter(item => 
        item.tempIndex === undefined || item.tempIndex === null || !aiTempIndexes.has(item.tempIndex)
    ).length;
}

/**
 * 获取行的匹配状态CSS类
 */
function getGlobalMatchClass(tempIndex, compareData) {
    if (tempIndex === undefined || tempIndex === null) return 'row-unmatched';
    const found = compareData.find(item => item.tempIndex === tempIndex);
    return found ? 'row-matched' : 'row-unmatched';
}

/**
 * 渲染页码标签
 */
function renderGlobalCorrectionPageTabs(pages) {
    const container = document.getElementById('correctionPageTabs');
    
    container.innerHTML = pages.map(page => {
        const data = globalCorrectionData[page];
        const matchedCount = data?.matchedCount || 0;
        const unmatchedCount = data?.unmatchedCount || 0;
        
        let badge = '';
        if (unmatchedCount > 0) {
            badge = `<span class="diff-badge">${unmatchedCount}</span>`;
        } else {
            badge = `<span class="match-badge">${matchedCount}</span>`;
        }
        
        return `<div class="correction-page-tab" data-page="${page}" onclick="selectGlobalCorrectionPage(${page})">
            第 ${page} 页 ${badge}
        </div>`;
    }).join('');
}

/**
 * 选择页码
 */
function selectGlobalCorrectionPage(page) {
    currentCorrectionPage = page;
    
    // 更新标签选中状态
    document.querySelectorAll('.correction-page-tab').forEach(tab => {
        tab.classList.toggle('active', parseInt(tab.dataset.page) === page);
    });
    
    // 渲染左右对比表格
    renderGlobalCorrectionSplitView(page);
}

/**
 * 渲染左右对比视图（与单页效果矫正一致）
 */
function renderGlobalCorrectionSplitView(page) {
    const data = globalCorrectionData[page];
    if (!data) {
        document.getElementById('correctionTableContainer').style.display = 'none';
        document.getElementById('correctionEmpty').style.display = 'flex';
        return;
    }
    
    const baseEffects = data.baseEffects;
    const aiResults = data.aiResults;
    
    // 检查是否有分数数据
    const hasScore = baseEffects.some(item => item.maxScore !== undefined || item.score !== undefined) ||
                     aiResults.some(item => item.score !== undefined);
    
    document.getElementById('correctionTableContainer').style.display = 'block';
    document.getElementById('correctionEmpty').style.display = 'none';
    
    // 渲染左右分栏对比表格
    const container = document.getElementById('correctionTableContainer');
    container.innerHTML = `
        <div class="correction-split">
            <div class="correction-left">
                <div class="correction-panel-title">基准效果 (可编辑)</div>
                <div class="correction-table-wrap">
                    <table class="correction-table">
                        <thead>
                            <tr>
                                <th style="width:80px;">题号</th>
                                <th>手写答案</th>
                                ${hasScore ? '<th style="width:60px;">得分</th>' : ''}
                                <th style="width:100px;">tempIndex</th>
                            </tr>
                        </thead>
                        <tbody id="globalCorrectionBaseBody">
                            ${baseEffects.map((item, idx) => `
                                <tr data-idx="${idx}" class="${getGlobalMatchClass(item.tempIndex, aiResults)}">
                                    <td>
                                        <input type="text" class="correction-input" value="${escapeHtml(item.index || '')}" 
                                               onchange="updateGlobalCorrectionCell(${page}, ${idx}, 'index', this.value)">
                                    </td>
                                    <td>
                                        <textarea class="correction-textarea" 
                                                  onchange="updateGlobalCorrectionCell(${page}, ${idx}, 'userAnswer', this.value)">${escapeHtml(item.userAnswer || '')}</textarea>
                                    </td>
                                    ${hasScore ? `
                                    <td>
                                        <input type="number" class="correction-input score-input" 
                                               value="${item.score !== undefined && item.score !== null ? item.score : ''}" 
                                               onchange="updateGlobalCorrectionCell(${page}, ${idx}, 'score', this.value ? parseFloat(this.value) : null)"
                                               step="0.5" min="0">
                                    </td>
                                    ` : ''}
                                    <td>
                                        <input type="number" class="correction-input tempindex-input" 
                                               value="${item.tempIndex !== undefined ? item.tempIndex : ''}" 
                                               onchange="updateGlobalCorrectionCell(${page}, ${idx}, 'tempIndex', this.value === '' ? undefined : parseInt(this.value))">
                                    </td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
                <div class="correction-actions">
                    <button class="btn-add-row" onclick="addGlobalCorrectionRow(${page})">+ 添加题目</button>
                </div>
            </div>
            <div class="correction-right">
                <div class="correction-panel-title">AI批改结果 (只读参考)</div>
                <div class="correction-table-wrap">
                    <table class="correction-table">
                        <thead>
                            <tr>
                                <th style="width:80px;">题号</th>
                                <th>手写答案</th>
                                ${hasScore ? '<th style="width:60px;">得分</th>' : ''}
                                <th style="width:100px;">tempIndex</th>
                            </tr>
                        </thead>
                        <tbody id="globalCorrectionAiBody">
                            ${aiResults.map((item, idx) => `
                                <tr data-idx="${idx}" class="${getGlobalMatchClass(item.tempIndex, baseEffects)}">
                                    <td>${escapeHtml(item.index || '-')}</td>
                                    <td class="ai-answer-cell">${escapeHtml(item.userAnswer || '-')}</td>
                                    ${hasScore ? `<td class="ai-score-cell">${item.score !== undefined && item.score !== null ? item.score : '-'}</td>` : ''}
                                    <td class="tempindex-cell">${item.tempIndex !== undefined ? item.tempIndex : '-'}</td>
                                </tr>
                            `).join('')}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
        <div class="correction-stats-bar">
            <span class="stat-matched">匹配: ${data.matchedCount} 题</span>
            <span class="stat-unmatched">未匹配: ${data.unmatchedCount} 题</span>
        </div>
    `;
}

/**
 * 更新基准效果单元格
 */
function updateGlobalCorrectionCell(page, idx, field, value) {
    if (!recognizeResults[page]?.data?.[idx]) return;
    
    recognizeResults[page].data[idx][field] = value;
    
    // 更新统计并重新渲染
    const data = globalCorrectionData[page];
    if (data) {
        data.matchedCount = countMatchedByTempIndex(recognizeResults[page].data, data.aiResults);
        data.unmatchedCount = countUnmatchedByTempIndex(recognizeResults[page].data, data.aiResults);
        
        // 更新全局统计
        updateGlobalCorrectionSummary();
        
        // 更新页码标签
        const pages = Object.keys(globalCorrectionData).map(Number).sort((a, b) => a - b);
        renderGlobalCorrectionPageTabs(pages);
        document.querySelector(`.correction-page-tab[data-page="${page}"]`)?.classList.add('active');
        
        // 重新渲染当前页
        renderGlobalCorrectionSplitView(page);
    }
}

/**
 * 添加基准效果行
 */
function addGlobalCorrectionRow(page) {
    if (!recognizeResults[page]) {
        recognizeResults[page] = { success: true, data: [] };
    }
    
    const data = recognizeResults[page].data;
    const lastItem = data[data.length - 1];
    const newIndex = lastItem ? (parseInt(lastItem.index) + 1).toString() : '1';
    const newTempIndex = lastItem && lastItem.tempIndex !== undefined ? lastItem.tempIndex + 1 : 0;
    
    data.push({
        index: newIndex,
        userAnswer: '',
        correct: 'yes',
        tempIndex: newTempIndex
    });
    
    // 更新统计并重新渲染
    const corrData = globalCorrectionData[page];
    if (corrData) {
        corrData.matchedCount = countMatchedByTempIndex(data, corrData.aiResults);
        corrData.unmatchedCount = countUnmatchedByTempIndex(data, corrData.aiResults);
        updateGlobalCorrectionSummary();
        
        const pages = Object.keys(globalCorrectionData).map(Number).sort((a, b) => a - b);
        renderGlobalCorrectionPageTabs(pages);
        document.querySelector(`.correction-page-tab[data-page="${page}"]`)?.classList.add('active');
        renderGlobalCorrectionSplitView(page);
    }
}

/**
 * 更新全局统计信息
 */
function updateGlobalCorrectionSummary() {
    let totalMatched = 0;
    let totalUnmatched = 0;
    
    Object.values(globalCorrectionData).forEach(data => {
        totalMatched += data.matchedCount || 0;
        totalUnmatched += data.unmatchedCount || 0;
    });
    
    document.getElementById('correctionSummary').innerHTML = 
        `匹配: <span class="match-count">${totalMatched}</span> 题 | 未匹配: <span class="diff-count">${totalUnmatched}</span> 题`;
}

/**
 * 应用矫正修改
 */
function applyCorrectionChanges() {
    // 数据已经实时更新到 recognizeResults 中
    hideCorrectionModal();
    
    // 重新渲染识别结果
    renderRecognizePreview();
    checkCanSave();
    
    alert('矫正修改已应用');
}

/**
 * 隐藏效果矫正弹窗
 */
function hideCorrectionModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('correctionModal').classList.remove('show');
    globalCorrectionData = {};
    currentCorrectionPage = null;
}


// ========== 合集管理功能 ==========

let allDatasetsForCollection = [];  // 所有数据集（用于合集编辑）
let selectedDatasetIds = new Set();  // 选中的数据集ID
let currentCollectionId = null;  // 当前查看/编辑的合集ID
let currentDatasetTab = 'current';  // 当前数据集标签页: 'current' 或 'all'

/**
 * 显示书本合集管理弹窗
 */
function showBookCollectionModal() {
    if (!selectedBook) {
        alert('请先选择一个书本');
        return;
    }
    document.getElementById('collectionModalTitle').textContent = `${selectedBook.book_name} - 合集管理`;
    showCollectionManager();
}

/**
 * 显示合集管理弹窗
 */
function showCollectionManager() {
    document.getElementById('collectionModal').classList.add('show');
    showCollectionList();
    loadCollections();
}

/**
 * 隐藏合集管理弹窗
 */
function hideCollectionModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('collectionModal').classList.remove('show');
    currentCollectionId = null;
}

/**
 * 显示合集列表
 */
function showCollectionList() {
    document.getElementById('collectionListSection').style.display = 'flex';
    document.getElementById('collectionFormSection').style.display = 'none';
    document.getElementById('collectionDetailSection').style.display = 'none';
}

/**
 * 加载合集列表
 */
async function loadCollections() {
    const container = document.getElementById('collectionList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (data.success) {
            renderCollectionList(data.data || []);
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败: ' + e.message + '</div></div>';
    }
}

/**
 * 渲染合集列表
 */
function renderCollectionList(collections) {
    const container = document.getElementById('collectionList');
    
    if (!collections || collections.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无合集，点击上方按钮创建</div></div>';
        return;
    }
    
    container.innerHTML = collections.map(col => `
        <div class="collection-card" onclick="showCollectionDetail('${col.collection_id}')">
            <div class="collection-card-info">
                <div class="collection-card-name">${escapeHtml(col.name)}</div>
                <div class="collection-card-meta">
                    ${col.dataset_count || 0} 个数据集
                    ${col.description ? ' · ' + escapeHtml(col.description.substring(0, 30)) + (col.description.length > 30 ? '...' : '') : ''}
                </div>
            </div>
            <div class="collection-card-actions">
                <button class="btn btn-secondary btn-small" onclick="event.stopPropagation(); editCollection('${col.collection_id}')">编辑</button>
                <button class="btn btn-danger btn-small" onclick="event.stopPropagation(); deleteCollection('${col.collection_id}', '${escapeHtml(col.name)}')">删除</button>
            </div>
        </div>
    `).join('');
}

/**
 * 显示新建合集表单
 */
function showCreateCollectionForm() {
    currentCollectionId = null;
    currentDatasetTab = 'current';
    document.getElementById('editCollectionId').value = '';
    document.getElementById('collectionFormTitle').textContent = '新建合集';
    document.getElementById('collectionNameInput').value = '';
    document.getElementById('collectionDescInput').value = '';
    selectedDatasetIds = new Set();
    
    // 重置标签页
    document.querySelectorAll('.collection-datasets-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    document.querySelector('.collection-datasets-tabs .tab-btn').classList.add('active');
    
    document.getElementById('collectionListSection').style.display = 'none';
    document.getElementById('collectionFormSection').style.display = 'flex';
    document.getElementById('collectionDetailSection').style.display = 'none';
    
    loadAllDatasetsForCollection();
}

/**
 * 切换数据集标签页
 */
function switchDatasetTab(tab) {
    currentDatasetTab = tab;
    document.querySelectorAll('.collection-datasets-tabs .tab-btn').forEach(btn => {
        btn.classList.remove('active');
    });
    event.currentTarget.classList.add('active');
    renderDatasetsForCollection();
}

/**
 * 隐藏合集表单
 */
function hideCollectionForm() {
    showCollectionList();
    loadCollections();
}

/**
 * 加载所有数据集（用于合集编辑）
 */
async function loadAllDatasetsForCollection() {
    const container = document.getElementById('collectionDatasetsList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/datasets');
        const data = await res.json();
        
        if (data.success) {
            allDatasetsForCollection = data.data || [];
            renderDatasetsForCollection();
        } else {
            container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 筛选数据集
 */
function filterDatasetsForCollection() {
    renderDatasetsForCollection();
}

/**
 * 渲染数据集列表（用于合集编辑）
 */
function renderDatasetsForCollection() {
    const container = document.getElementById('collectionDatasetsList');
    const filterText = (document.getElementById('datasetFilterInput').value || '').toLowerCase();
    
    let datasets = allDatasetsForCollection;
    
    // 按标签页筛选
    if (currentDatasetTab === 'current' && selectedBook) {
        datasets = datasets.filter(ds => ds.book_id === selectedBook.book_id);
    }
    
    // 按搜索文本筛选
    if (filterText) {
        datasets = datasets.filter(ds => 
            (ds.name || '').toLowerCase().includes(filterText) ||
            (ds.book_name || '').toLowerCase().includes(filterText)
        );
    }
    
    if (!datasets || datasets.length === 0) {
        const emptyMsg = currentDatasetTab === 'current' && selectedBook 
            ? '当前书本暂无数据集' 
            : '暂无数据集';
        container.innerHTML = `<div class="empty-state"><div class="empty-state-text">${emptyMsg}</div></div>`;
        updateSelectedDatasetsCount();
        return;
    }
    
    container.innerHTML = datasets.map(ds => {
        const isSelected = selectedDatasetIds.has(ds.dataset_id);
        const pages = ds.pages || [];
        const pageStr = pages.length > 0 ? `P${pages[0]}${pages.length > 1 ? '-' + pages[pages.length - 1] : ''}` : '';
        
        return `
            <div class="collection-dataset-item ${isSelected ? 'selected' : ''}" onclick="toggleDatasetSelection('${ds.dataset_id}')">
                <input type="checkbox" ${isSelected ? 'checked' : ''} onclick="event.stopPropagation(); toggleDatasetSelection('${ds.dataset_id}')">
                <div class="collection-dataset-item-info">
                    <div class="collection-dataset-item-name">${escapeHtml(ds.name || ds.dataset_id)}</div>
                    <div class="collection-dataset-item-meta">${escapeHtml(ds.book_name || '')} ${pageStr} · ${ds.question_count || 0}题</div>
                </div>
            </div>
        `;
    }).join('');
    
    updateSelectedDatasetsCount();
}

/**
 * 切换数据集选择
 */
function toggleDatasetSelection(datasetId) {
    if (selectedDatasetIds.has(datasetId)) {
        selectedDatasetIds.delete(datasetId);
    } else {
        selectedDatasetIds.add(datasetId);
    }
    renderDatasetsForCollection();
}

/**
 * 更新已选择数据集数量
 */
function updateSelectedDatasetsCount() {
    document.getElementById('selectedDatasetsCount').textContent = selectedDatasetIds.size;
}

/**
 * 保存合集
 */
async function saveCollection() {
    const name = document.getElementById('collectionNameInput').value.trim();
    const description = document.getElementById('collectionDescInput').value.trim();
    const editId = document.getElementById('editCollectionId').value;
    
    if (!name) {
        alert('请输入合集名称');
        return;
    }
    
    showLoading('保存中...');
    
    try {
        let res;
        if (editId) {
            // 更新合集
            res = await fetch(`/api/batch/collections/${editId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description })
            });
            
            if (res.ok) {
                // 更新数据集关联
                const currentDatasets = await getCollectionDatasetIds(editId);
                const toAdd = [...selectedDatasetIds].filter(id => !currentDatasets.includes(id));
                const toRemove = currentDatasets.filter(id => !selectedDatasetIds.has(id));
                
                // 添加新数据集
                if (toAdd.length > 0) {
                    await fetch(`/api/batch/collections/${editId}/datasets`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ dataset_ids: toAdd })
                    });
                }
                
                // 移除数据集
                for (const dsId of toRemove) {
                    await fetch(`/api/batch/collections/${editId}/datasets/${dsId}`, {
                        method: 'DELETE'
                    });
                }
            }
        } else {
            // 创建新合集
            res = await fetch('/api/batch/collections', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name,
                    description,
                    dataset_ids: [...selectedDatasetIds]
                })
            });
        }
        
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            hideCollectionForm();
        } else {
            alert('保存失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        alert('保存失败: ' + e.message);
    }
}

/**
 * 获取合集当前的数据集ID列表
 */
async function getCollectionDatasetIds(collectionId) {
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}`);
        const data = await res.json();
        if (data.success && data.data && data.data.datasets) {
            return data.data.datasets.map(ds => ds.dataset_id);
        }
    } catch (e) {
        console.error('获取合集数据集失败:', e);
    }
    return [];
}

/**
 * 编辑合集
 */
async function editCollection(collectionId) {
    currentCollectionId = collectionId;
    document.getElementById('editCollectionId').value = collectionId;
    document.getElementById('collectionFormTitle').textContent = '编辑合集';
    
    showLoading('加载中...');
    
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}`);
        const data = await res.json();
        
        if (data.success && data.data) {
            const col = data.data;
            document.getElementById('collectionNameInput').value = col.name || '';
            document.getElementById('collectionDescInput').value = col.description || '';
            
            // 设置已选择的数据集
            selectedDatasetIds = new Set((col.datasets || []).map(ds => ds.dataset_id));
            
            document.getElementById('collectionListSection').style.display = 'none';
            document.getElementById('collectionFormSection').style.display = 'flex';
            document.getElementById('collectionDetailSection').style.display = 'none';
            
            await loadAllDatasetsForCollection();
        } else {
            alert('加载合集失败');
        }
    } catch (e) {
        alert('加载合集失败: ' + e.message);
    }
    
    hideLoading();
}

/**
 * 删除合集
 */
async function deleteCollection(collectionId, name) {
    if (!confirm(`确定要删除合集"${name}"吗？\n\n删除后不可恢复，但不会影响其中的数据集。`)) {
        return;
    }
    
    showLoading('删除中...');
    
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        
        hideLoading();
        
        if (data.success) {
            loadCollections();
        } else {
            alert('删除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        alert('删除失败: ' + e.message);
    }
}

/**
 * 显示合集详情
 */
async function showCollectionDetail(collectionId) {
    currentCollectionId = collectionId;
    
    showLoading('加载中...');
    
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}`);
        const data = await res.json();
        
        hideLoading();
        
        if (data.success && data.data) {
            const col = data.data;
            
            document.getElementById('collectionDetailName').textContent = col.name || '';
            document.getElementById('collectionDetailDesc').textContent = col.description || '';
            document.getElementById('collectionDatasetCount').textContent = (col.datasets || []).length;
            
            renderCollectionDetailDatasets(col.datasets || []);
            
            document.getElementById('collectionListSection').style.display = 'none';
            document.getElementById('collectionFormSection').style.display = 'none';
            document.getElementById('collectionDetailSection').style.display = 'flex';
        } else {
            alert('加载合集详情失败');
        }
    } catch (e) {
        hideLoading();
        alert('加载合集详情失败: ' + e.message);
    }
}

/**
 * 渲染合集详情中的数据集列表
 */
function renderCollectionDetailDatasets(datasets) {
    const container = document.getElementById('collectionDetailDatasetsList');
    
    if (!datasets || datasets.length === 0) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">暂无数据集</div></div>';
        return;
    }
    
    container.innerHTML = datasets.map(ds => {
        const pages = ds.pages || [];
        const pageStr = pages.length > 0 ? `P${pages[0]}${pages.length > 1 ? '-' + pages[pages.length - 1] : ''}` : '';
        
        return `
            <div class="collection-detail-dataset-card">
                <div class="collection-detail-dataset-info">
                    <div class="collection-detail-dataset-name">${escapeHtml(ds.name || ds.dataset_id)}</div>
                    <div class="collection-detail-dataset-meta">${escapeHtml(ds.book_name || '')} ${pageStr} · ${ds.question_count || 0}题</div>
                </div>
                <div class="collection-detail-dataset-actions">
                    <button class="btn-remove" onclick="removeDatasetFromCollection('${ds.dataset_id}')">移除</button>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 从合集中移除数据集
 */
async function removeDatasetFromCollection(datasetId) {
    if (!currentCollectionId) return;
    
    if (!confirm('确定要从合集中移除此数据集吗？')) {
        return;
    }
    
    showLoading('移除中...');
    
    try {
        const res = await fetch(`/api/batch/collections/${currentCollectionId}/datasets/${datasetId}`, {
            method: 'DELETE'
        });
        const data = await res.json();
        
        hideLoading();
        
        if (data.success) {
            showCollectionDetail(currentCollectionId);
        } else {
            alert('移除失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        alert('移除失败: ' + e.message);
    }
}

/**
 * 隐藏合集详情
 */
function hideCollectionDetail() {
    showCollectionList();
    loadCollections();
}

/**
 * 编辑当前合集
 */
function editCurrentCollection() {
    if (currentCollectionId) {
        editCollection(currentCollectionId);
    }
}

/**
 * 删除当前合集
 */
function deleteCurrentCollection() {
    if (currentCollectionId) {
        const name = document.getElementById('collectionDetailName').textContent;
        deleteCollection(currentCollectionId, name);
    }
}

/**
 * 添加当前书本的数据集到合集
 */
async function addCurrentBookDatasetsToCollection() {
    if (!currentCollectionId || !selectedBook) {
        alert('请先选择书本和合集');
        return;
    }
    
    // 获取当前书本的所有数据集
    const bookDatasets = allDatasetsForCollection.filter(ds => ds.book_id === selectedBook.book_id);
    
    if (bookDatasets.length === 0) {
        alert('当前书本暂无数据集');
        return;
    }
    
    // 获取合集中已有的数据集
    const existingIds = await getCollectionDatasetIds(currentCollectionId);
    const newIds = bookDatasets
        .map(ds => ds.dataset_id)
        .filter(id => !existingIds.includes(id));
    
    if (newIds.length === 0) {
        alert('当前书本的数据集已全部在合集中');
        return;
    }
    
    if (!confirm(`确定要将当前书本的 ${newIds.length} 个数据集添加到合集吗？`)) {
        return;
    }
    
    showLoading('添加中...');
    
    try {
        const res = await fetch(`/api/batch/collections/${currentCollectionId}/datasets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_ids: newIds })
        });
        
        const data = await res.json();
        hideLoading();
        
        if (data.success) {
            showCollectionDetail(currentCollectionId);
            alert(`成功添加 ${data.added_count || newIds.length} 个数据集`);
        } else {
            alert('添加失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        hideLoading();
        alert('添加失败: ' + e.message);
    }
}


// ========== 概览页面合集功能 ==========

/**
 * 显示全局合集管理（从概览页面进入）
 */
function showGlobalCollectionManager() {
    document.getElementById('collectionModalTitle').textContent = '基准合集管理';
    showCollectionManager();
}

/**
 * 加载概览页面的合集列表
 */
async function loadOverviewCollections() {
    const container = document.getElementById('overviewCollectionsList');
    if (!container) return;
    
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (data.success && data.data && data.data.length > 0) {
            container.innerHTML = data.data.map(col => `
                <div class="overview-collection-tag" onclick="showCollectionDetail('${col.collection_id}'); showCollectionManager();">
                    <span>${escapeHtml(col.name)}</span>
                    <span class="tag-count">${col.dataset_count || 0}个</span>
                </div>
            `).join('');
        } else {
            container.innerHTML = '<div class="empty-state" style="padding: 12px;"><div class="empty-state-text">暂无合集</div></div>';
        }
    } catch (e) {
        container.innerHTML = '<div class="empty-state" style="padding: 12px;"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 刷新概览页面合集
 */
function refreshOverviewCollections() {
    loadOverviewCollections();
}

// ========== 添加数据集到合集 ==========

let addToCollectionDatasetId = null;

/**
 * 显示添加到合集弹窗
 */
async function showAddToCollectionModal(datasetId, datasetName) {
    addToCollectionDatasetId = datasetId;
    document.getElementById('addToCollectionDatasetName').textContent = datasetName || datasetId;
    document.getElementById('addToCollectionModal').classList.add('show');
    
    await loadCollectionsForAddTo(datasetId);
}

/**
 * 隐藏添加到合集弹窗
 */
function hideAddToCollectionModal(e) {
    if (e && e.target !== e.currentTarget) return;
    document.getElementById('addToCollectionModal').classList.remove('show');
    addToCollectionDatasetId = null;
}

/**
 * 加载合集列表（用于添加数据集）
 */
async function loadCollectionsForAddTo(datasetId) {
    const container = document.getElementById('addToCollectionList');
    container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载中...</div></div>';
    
    try {
        const res = await fetch('/api/batch/collections');
        const data = await res.json();
        
        if (!data.success || !data.data || data.data.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-state-text">暂无合集</div>
                    <button class="btn btn-secondary btn-small" onclick="hideAddToCollectionModal(); showGlobalCollectionManager();" style="margin-top: 12px;">去创建合集</button>
                </div>
            `;
            return;
        }
        
        // 检查每个合集是否已包含该数据集
        const collectionsWithStatus = await Promise.all(data.data.map(async col => {
            try {
                const detailRes = await fetch(`/api/batch/collections/${col.collection_id}`);
                const detailData = await detailRes.json();
                const hasDataset = detailData.success && detailData.data && 
                    detailData.data.datasets && 
                    detailData.data.datasets.some(ds => ds.dataset_id === datasetId);
                return { ...col, hasDataset };
            } catch (e) {
                return { ...col, hasDataset: false };
            }
        }));
        
        container.innerHTML = collectionsWithStatus.map(col => `
            <div class="add-to-collection-item">
                <div class="add-to-collection-item-info">
                    <div class="add-to-collection-item-name">${escapeHtml(col.name)}</div>
                    <div class="add-to-collection-item-meta">${col.dataset_count || 0} 个数据集</div>
                </div>
                ${col.hasDataset 
                    ? '<span class="added-badge">已添加</span>'
                    : `<button class="btn-add" onclick="addDatasetToCollection('${col.collection_id}', '${escapeHtml(col.name)}')">添加</button>`
                }
            </div>
        `).join('');
    } catch (e) {
        container.innerHTML = '<div class="empty-state"><div class="empty-state-text">加载失败</div></div>';
    }
}

/**
 * 添加数据集到指定合集
 */
async function addDatasetToCollection(collectionId, collectionName) {
    if (!addToCollectionDatasetId) return;
    
    try {
        const res = await fetch(`/api/batch/collections/${collectionId}/datasets`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_ids: [addToCollectionDatasetId] })
        });
        
        const data = await res.json();
        
        if (data.success) {
            // 刷新列表
            await loadCollectionsForAddTo(addToCollectionDatasetId);
            // 刷新概览页面合集
            loadOverviewCollections();
        } else {
            alert('添加失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('添加失败: ' + e.message);
    }
}

// 页面加载时加载概览合集
document.addEventListener('DOMContentLoaded', function() {
    loadOverviewCollections();
});
