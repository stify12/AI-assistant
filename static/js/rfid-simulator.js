/**
 * RFID 模拟器 - 增强版
 */

// ==================== 状态 ====================

const state = {
    currentTab: 'class',
    currentGrade: 0,
    currentSubject: 0,    // 学科筛选
    selectedItem: null,
    allStudents: [],      // 原始学生列表
    students: [],         // 筛选后的学生列表
    studentFilter: 'all', // all | rep | normal
    intervalSeconds: 5,
    isRunning: false,
    isPaused: false,
    countdown: 0,
    countdownTimer: null,
    pollTimer: null,
    searchTimer: null,
    startTime: null,      // 执行开始时间
    elapsedTimer: null,   // 耗时计时器
    logExpanded: false    // 日志面板展开状态
};

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    initGradeFilter();
    initSubjectFilter();
    initTabSwitch();
    initIntervalButtons();
    initCustomInterval();
    initSearch();
    initKeyboardShortcuts();
    initLogFilter();
    initStudentFilter();
    loadFavorites();
    loadList();
    refreshStatus();
    startPolling();
});

function initGradeFilter() {
    const select = document.getElementById('gradeSelect');
    if (select) {
        select.addEventListener('change', () => {
            state.currentGrade = parseInt(select.value);
            loadList();
        });
    }
}

function initSubjectFilter() {
    document.querySelectorAll('#subjectFilterBar .filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('#subjectFilterBar .filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentSubject = parseInt(btn.dataset.subject);
            loadList();
        });
    });
}

function initTabSwitch() {
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentTab = btn.dataset.tab;
            
            const input = document.getElementById('searchInput');
            const gradeBar = document.getElementById('gradeFilterBar');
            const subjectBar = document.getElementById('subjectFilterBar');
            
            if (state.currentTab === 'class') {
                input.placeholder = '搜索班级名称...';
                gradeBar.style.display = 'flex';
                subjectBar.style.display = 'none';
            } else {
                input.placeholder = '搜索书本名称...';
                gradeBar.style.display = 'none';
                subjectBar.style.display = 'flex';
            }
            input.value = '';
            
            loadList();
        });
    });
}

function initIntervalButtons() {
    document.querySelectorAll('.interval-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.interval-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.intervalSeconds = parseInt(btn.dataset.value);
            document.getElementById('customInterval').value = '';
        });
    });
}

function initCustomInterval() {
    const input = document.getElementById('customInterval');
    if (!input) return;
    input.addEventListener('change', () => {
        const val = parseInt(input.value);
        if (val >= 1 && val <= 60) {
            document.querySelectorAll('.interval-btn').forEach(b => b.classList.remove('active'));
            state.intervalSeconds = val;
        }
    });
}

function initSearch() {
    const input = document.getElementById('searchInput');
    input.addEventListener('input', () => {
        if (state.searchTimer) clearTimeout(state.searchTimer);
        state.searchTimer = setTimeout(() => loadList(), 300);
    });
}

function initKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Space: 暂停/继续
        if (e.code === 'Space' && state.isRunning && !e.target.matches('input, textarea')) {
            e.preventDefault();
            if (state.isPaused) {
                resumeBatch();
            } else {
                pauseBatch();
            }
        }
        // Esc: 停止
        if (e.code === 'Escape' && state.isRunning) {
            stopBatch();
        }
    });
}

function startPolling() {
    state.pollTimer = setInterval(() => {
        refreshStatus();
        refreshLogs();
    }, 2000);
}

// ==================== API ====================

async function apiCall(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    const result = await res.json();
    if (!result.success) throw new Error(result.error);
    return result.data;
}

// ==================== 列表加载 ====================

async function loadList() {
    const container = document.getElementById('listContainer');
    container.innerHTML = '<div class="list-loading">加载中...</div>';
    
    try {
        const keyword = document.getElementById('searchInput').value.trim();
        let data;
        
        if (state.currentTab === 'class') {
            const params = new URLSearchParams();
            if (state.currentGrade > 0) params.append('grade', state.currentGrade);
            if (keyword) params.append('keyword', keyword);
            data = await apiCall(`/api/nfc/classes?${params}`);
            renderClassList(data);
        } else {
            const params = new URLSearchParams();
            if (keyword) params.append('keyword', keyword);
            data = await apiCall(`/api/nfc/books?${params}`);
            // 学科筛选
            if (state.currentSubject > 0) {
                data = data.filter(b => b.subject_id === state.currentSubject);
            }
            renderBookList(data);
        }
    } catch (e) {
        container.innerHTML = `<div class="list-empty">加载失败: ${e.message}</div>`;
    }
}

// 年级映射
const GRADE_MAP = {
    '1': "一年级", '2': "二年级", '3': "三年级",
    '4': "四年级", '5': "五年级", '6': "六年级",
    '7': "七年级", '8': "八年级", '9': "九年级",
    '10': "高一", '11': "高二", '12': "高三",
    1: "一年级", 2: "二年级", 3: "三年级",
    4: "四年级", 5: "五年级", 6: "六年级",
    7: "七年级", 8: "八年级", 9: "九年级",
    10: "高一", 11: "高二", 12: "高三"
};

function renderClassList(classes) {
    const container = document.getElementById('listContainer');
    
    if (!classes || classes.length === 0) {
        container.innerHTML = '<div class="list-empty">暂无班级数据</div>';
        return;
    }
    
    container.innerHTML = `<div class="list-grid">${classes.map(cls => {
        // 构建完整班级名称：年级 + 班级名
        const gradeKey = cls.grade || cls.grade_id;
        const gradeName = GRADE_MAP[gradeKey] || '';
        // 如果班级名已包含年级信息，则不重复添加
        const hasGradePrefix = cls.name.includes('年级') || cls.name.includes('高一') || cls.name.includes('高二') || cls.name.includes('高三') || cls.name.includes('年');
        const fullName = hasGradePrefix ? cls.name : (gradeName ? `${gradeName}${cls.name}` : cls.name);
        
        return `
        <div class="list-item ${state.selectedItem?.id === cls.id && state.selectedItem?.type === 'class' ? 'active' : ''}" 
             onclick="selectClass('${cls.id}', '${escapeHtml(fullName)}', '${gradeKey || 0}', event)">
            <div class="item-name">${escapeHtml(fullName)}</div>
            <div class="item-meta">
                <span>${cls.student_count || 0} 人</span>
            </div>
        </div>
    `}).join('')}</div>`;
}

function renderBookList(books) {
    const container = document.getElementById('listContainer');
    
    if (!books || books.length === 0) {
        container.innerHTML = '<div class="list-empty">暂无书本数据</div>';
        return;
    }
    
    container.innerHTML = `<div class="list-grid">${books.map(book => `
        <div class="list-item ${state.selectedItem?.id === book.id && state.selectedItem?.type === 'book' ? 'active' : ''}" 
             onclick="selectBook('${book.id}', '${escapeHtml(book.book_name)}', event)">
            <div class="item-name">${escapeHtml(book.book_name)}</div>
            <div class="item-meta">
                ${book.subject_name ? `<span>${escapeHtml(book.subject_name)}</span>` : ''}
                ${book.grade_name ? `<span>${escapeHtml(book.grade_name)}</span>` : ''}
            </div>
        </div>
    `).join('')}</div>`;
}

// ==================== 选择处理 ====================

async function selectClass(classId, className, gradeId, evt) {
    state.selectedItem = { type: 'class', id: classId, name: className, grade: gradeId };
    
    // 清除所有选中状态
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
    
    // 设置当前选中（兼容多种调用方式）
    const target = evt?.currentTarget || event?.currentTarget;
    if (target) {
        target.classList.add('active');
    }
    
    // 加载关联书籍
    loadClassBooks(classId);
    
    // 先加载学生数据
    await loadStudents(`/api/nfc/class/${classId}/students`, className);
    
    // 加载完成后再添加到最近使用（此时 state.allStudents 已有数据）
    if (typeof addToRecent === 'function') {
        addToRecent('class', { id: classId, name: className, type: 'class' });
    }
}

async function selectBook(bookId, bookName, evt) {
    state.selectedItem = { type: 'book', id: bookId, name: bookName };
    
    // 清除所有选中状态
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
    
    // 设置当前选中（兼容多种调用方式）
    const target = evt?.currentTarget || event?.currentTarget;
    if (target) {
        target.classList.add('active');
    }
    
    try {
        const classes = await apiCall(`/api/nfc/book/${bookId}/classes`);
        if (classes && classes.length > 0) {
            const firstClass = classes[0];
            await loadStudents(
                `/api/nfc/book/${bookId}/class/${firstClass.id}/students`,
                `${bookName} - ${firstClass.name}`
            );
        } else {
            showSelectedCard(bookName, [], 0, 0);
        }
    } catch (e) {
        console.error('加载书本班级失败:', e);
    }
    
    // 加载完成后再添加到最近使用
    if (typeof addToRecent === 'function') {
        addToRecent('book', { id: bookId, name: bookName, type: 'book' });
    }
}

async function loadStudents(url, title) {
    try {
        const students = await apiCall(url);
        // 保存原始列表
        state.allStudents = (students || []).filter(s => s.rfid_no && /^\d+$/.test(s.rfid_no));
        
        // 排序：课代表优先
        state.allStudents.sort((a, b) => {
            if (a.is_representative && !b.is_representative) return -1;
            if (!a.is_representative && b.is_representative) return 1;
            return 0;
        });
        
        // 应用筛选
        applyFilter();
        
        const repCount = state.allStudents.filter(s => s.is_representative).length;
        showSelectedCard(title, state.allStudents, repCount, state.allStudents.length);
    } catch (e) {
        console.error('加载学生失败:', e);
        showSelectedCard(title, [], 0, 0);
    }
}

function applyFilter() {
    // 从 DOM 获取筛选值
    const filterEl = document.querySelector('input[name="studentFilter"]:checked');
    const filter = filterEl ? filterEl.value : 'all';
    state.studentFilter = filter;
    
    if (filter === 'all') {
        state.students = [...state.allStudents];
    } else if (filter === 'rep') {
        state.students = state.allStudents.filter(s => s.is_representative);
    } else {
        state.students = state.allStudents.filter(s => !s.is_representative);
    }
    
    // 更新学生列表显示
    renderStudentList();
    
    // 更新按钮状态
    const startBtn = document.getElementById('startBtn');
    if (startBtn) {
        startBtn.disabled = state.students.length === 0;
    }
}

// 渲染学生列表
function renderStudentList() {
    const container = document.getElementById('studentList');
    if (!container) return;
    
    if (state.students.length === 0) {
        container.innerHTML = '<div class="student-empty">暂无符合条件的学生</div>';
        return;
    }
    
    container.innerHTML = state.students.map(s => `
        <div class="student-item">
            <span class="student-name">${escapeHtml(s.name)}</span>
            <span class="student-rfid">${escapeHtml(s.rfid_no)}</span>
            ${s.is_representative ? '<span class="student-rep">课代表</span>' : ''}
        </div>
    `).join('');
}

// 初始化学生筛选事件
function initStudentFilter() {
    document.querySelectorAll('input[name="studentFilter"]').forEach(radio => {
        radio.addEventListener('change', applyFilter);
    });
}

function showSelectedCard(title, allStudents, repCount, validCount) {
    document.getElementById('emptyHint').style.display = 'none';
    document.getElementById('selectedInfo').style.display = 'block';
    const batchControl = document.getElementById('batchControl');
    if (batchControl) batchControl.style.display = 'block';
    document.getElementById('selectedTitle').textContent = title;
    document.getElementById('studentCount').textContent = allStudents.length;
    document.getElementById('repCount').textContent = repCount;
    document.getElementById('validCount').textContent = validCount;
    
    document.getElementById('startBtn').disabled = state.students.length === 0;
}

function clearSelection() {
    state.selectedItem = null;
    state.allStudents = [];
    state.students = [];
    
    document.getElementById('selectedInfo').style.display = 'none';
    document.getElementById('relatedBooksCard').style.display = 'none';
    document.getElementById('emptyHint').style.display = 'flex';
    const batchControl = document.getElementById('batchControl');
    if (batchControl) batchControl.style.display = 'none';
    document.getElementById('startBtn').disabled = true;
    
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
}

// ==================== 关联书籍 ====================

async function loadClassBooks(classId) {
    const card = document.getElementById('relatedBooksCard');
    const list = document.getElementById('booksList');
    const countEl = document.getElementById('bookCount');
    
    try {
        const books = await apiCall(`/api/nfc/class/${classId}/books`);
        
        if (!books || books.length === 0) {
            card.style.display = 'none';
            return;
        }
        
        card.style.display = 'block';
        countEl.textContent = books.length;
        
        list.innerHTML = books.map(book => `
            <div class="book-item">
                ${book.cover_path 
                    ? `<img class="book-cover" src="${escapeHtml(book.cover_path)}" alt="" onerror="this.style.display='none';this.nextElementSibling.style.display='flex'"><div class="book-cover-placeholder" style="display:none"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg></div>`
                    : `<div class="book-cover-placeholder"><svg viewBox="0 0 24 24"><path fill="currentColor" d="M18 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM6 4h5v8l-2.5-1.5L6 12V4z"/></svg></div>`
                }
                <div class="book-info">
                    <div class="book-name" title="${escapeHtml(book.book_name)}">${escapeHtml(book.book_name)}</div>
                    <div class="book-meta">
                        ${book.subject_name ? `<span class="book-subject">${escapeHtml(book.subject_name)}</span>` : ''}
                        <span class="book-student-count">${book.student_count || 0}人绑定</span>
                    </div>
                </div>
            </div>
        `).join('');
        
    } catch (e) {
        console.error('加载关联书籍失败:', e);
        card.style.display = 'none';
    }
}

// ==================== 连接状态 ====================

async function refreshStatus() {
    try {
        const data = await apiCall('/api/rfid-simulator/status');
        updateConnectionStatus(data);
        updateTaskStatus(data.task);
    } catch (e) {
        console.error('刷新状态失败:', e);
    }
}

function updateConnectionStatus(data) {
    const connectHint = document.getElementById('connectHint');
    const connectionChain = document.getElementById('connectionChain');
    const clientDot = document.getElementById('clientDot');
    const clientIp = document.getElementById('clientIp');
    const deviceDot = document.getElementById('deviceDot');
    const deviceIp = document.getElementById('deviceIp');
    
    // 始终显示状态链路，隐藏提示
    if (connectHint) connectHint.style.display = 'none';
    if (connectionChain) connectionChain.style.display = 'block';
    
    if (data.connected && data.client) {
        const client = data.client;
        
        // 客户端在线
        if (clientDot) clientDot.className = 'node-dot online';
        if (clientIp) clientIp.textContent = client.ip_address || '已连接';
        
        // 更新设备状态
        const deviceInfo = client.device_info || {};
        if (deviceInfo.connected) {
            if (deviceDot) deviceDot.className = 'node-dot online';
            if (deviceIp) deviceIp.textContent = deviceInfo.device_ip || '已连接';
        } else {
            if (deviceDot) deviceDot.className = 'node-dot';
            if (deviceIp) deviceIp.textContent = deviceInfo.device_ip || '未连接';
        }
    } else {
        // 客户端离线
        if (clientDot) clientDot.className = 'node-dot';
        if (clientIp) clientIp.textContent = '未连接';
        if (deviceDot) deviceDot.className = 'node-dot';
        if (deviceIp) deviceIp.textContent = '-';
    }
}

function updateTaskStatus(task) {
    const progressCard = document.getElementById('progressCard');
    const startBtn = document.getElementById('startBtn');
    const runningBtns = document.getElementById('runningBtns');
    const pauseBtn = document.getElementById('pauseBtn');
    const resumeBtn = document.getElementById('resumeBtn');
    
    if (!task || task.status === 'completed' || task.status === 'stopped') {
        progressCard.style.display = 'none';
        startBtn.style.display = 'flex';
        runningBtns.style.display = 'none';
        state.isRunning = false;
        state.isPaused = false;
        stopCountdown();
        stopElapsedTimer();
        return;
    }
    
    progressCard.style.display = 'block';
    startBtn.style.display = 'none';
    runningBtns.style.display = 'flex';
    state.isRunning = true;
    
    document.getElementById('taskStatus').textContent = task.status === 'paused' ? '已暂停' : '运行中';
    document.getElementById('progressText').textContent = `${task.current_index + 1} / ${task.total_count}`;
    
    const percent = task.total_count > 0 ? Math.round(((task.current_index + 1) / task.total_count) * 100) : 0;
    document.getElementById('progressBar').style.width = `${percent}%`;
    
    // 更新统计
    document.getElementById('successCount').textContent = task.success_count || 0;
    document.getElementById('failCount').textContent = task.failed_count || 0;
    
    // 更新当前发送
    if (task.cards && task.cards[task.current_index]) {
        const current = task.cards[task.current_index];
        document.getElementById('currentName').textContent = current.name || '-';
        document.getElementById('currentCard').textContent = current.cardNumber || '-';
    }
    
    if (task.status === 'paused') {
        pauseBtn.style.display = 'none';
        resumeBtn.style.display = 'flex';
        state.isPaused = true;
    } else {
        pauseBtn.style.display = 'flex';
        resumeBtn.style.display = 'none';
        state.isPaused = false;
    }
}

// ==================== 便捷操作 ====================

function copyCommand() {
    const cmd = document.getElementById('cmdText').textContent;
    navigator.clipboard.writeText(cmd).then(() => {
        const btn = document.querySelector('.btn-copy');
        btn.textContent = '已复制';
        setTimeout(() => btn.textContent = '复制', 2000);
    });
}

async function testConnection() {
    try {
        await apiCall('/api/rfid-simulator/test-connection', { method: 'POST' });
    } catch (e) {
        alert('测试连接失败: ' + e.message);
    }
}

async function detectDevice() {
    try {
        await apiCall('/api/rfid-simulator/detect-device', { method: 'POST' });
    } catch (e) {
        alert('检测设备失败: ' + e.message);
    }
}

async function sendTestCard() {
    const cardNo = document.getElementById('testCardNo').value.trim();
    if (!cardNo) {
        alert('请输入卡号');
        return;
    }
    if (!/^\d+$/.test(cardNo)) {
        alert('卡号只能包含数字');
        return;
    }
    
    try {
        await apiCall('/api/rfid-simulator/send', {
            method: 'POST',
            body: JSON.stringify({ rfid_code: cardNo })
        });
        document.getElementById('testCardNo').value = '';
    } catch (e) {
        alert('发送失败: ' + e.message);
    }
}

async function sendPreset(cardNo) {
    try {
        await apiCall('/api/rfid-simulator/send', {
            method: 'POST',
            body: JSON.stringify({ rfid_code: cardNo })
        });
    } catch (e) {
        alert('发送失败: ' + e.message);
    }
}

// ==================== 日志 ====================

let currentLogFilter = 'all';
let allLogs = [];

// 初始化日志过滤
function initLogFilter() {
    document.querySelectorAll('.log-filter-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.log-filter-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            currentLogFilter = btn.dataset.filter;
            filterLogs();
        });
    });
}

async function refreshLogs() {
    try {
        const logs = await apiCall('/api/rfid-simulator/logs?limit=50');
        allLogs = logs || [];
        updateLogStats();
        filterLogs();
    } catch (e) {
        console.error('刷新日志失败:', e);
    }
}

// 过滤日志
function filterLogs() {
    const logList = document.getElementById('logList');
    if (!logList) return;
    
    let filtered = allLogs;
    
    if (currentLogFilter === 'success') {
        filtered = allLogs.filter(log => log.level === 'success');
    } else if (currentLogFilter === 'error') {
        filtered = allLogs.filter(log => log.level === 'error');
    }
    
    if (filtered.length === 0) {
        logList.innerHTML = '<div class="log-empty">暂无日志</div>';
        return;
    }
    
    logList.innerHTML = filtered.map(log => `
        <div class="log-item ${log.level}">
            <span class="log-time">${log.time}</span>
            <span class="log-content">${escapeHtml(log.message)}</span>
        </div>
    `).join('');
}

// 更新日志统计
function updateLogStats() {
    const successCount = allLogs.filter(log => log.level === 'success').length;
    const errorCount = allLogs.filter(log => log.level === 'error').length;
    
    const successEl = document.getElementById('logSuccessCount');
    const errorEl = document.getElementById('logFailCount');
    
    if (successEl) successEl.textContent = successCount;
    if (errorEl) errorEl.textContent = errorCount;
}

async function clearLogs() {
    try {
        await apiCall('/api/rfid-simulator/logs', { method: 'DELETE' });
        allLogs = [];
        updateLogStats();
        filterLogs();
    } catch (e) {
        console.error('清空日志失败:', e);
    }
}

// 日志面板折叠切换
function toggleLogPanel() {
    const collapse = document.getElementById('logCollapse');
    const body = document.getElementById('logCollapseBody');
    
    if (!collapse || !body) return;
    
    state.logExpanded = !state.logExpanded;
    
    if (state.logExpanded) {
        collapse.classList.add('expanded');
        body.style.display = 'flex';
    } else {
        collapse.classList.remove('expanded');
        body.style.display = 'none';
    }
}

// ==================== 批量操作 ====================

async function startBatch() {
    if (state.students.length === 0) {
        alert('请先选择班级');
        return;
    }
    
    const cards = state.students.map(s => ({
        id: s.id,
        name: s.name,
        cardNumber: s.rfid_no,
        isRepresentative: s.is_representative
    }));
    
    const sendEnter = document.getElementById('sendEnter')?.checked || false;
    
    try {
        await apiCall('/api/rfid-simulator/batch/start', {
            method: 'POST',
            body: JSON.stringify({
                cards: cards,
                interval_seconds: state.intervalSeconds,
                send_enter: sendEnter
            })
        });
        
        state.isRunning = true;
        state.startTime = Date.now();
        
        // 立即切换按钮显示
        document.getElementById('startBtn').style.display = 'none';
        document.getElementById('runningBtns').style.display = 'flex';
        document.getElementById('pauseBtn').style.display = 'flex';
        document.getElementById('resumeBtn').style.display = 'none';
        document.getElementById('progressCard').style.display = 'block';
        document.getElementById('taskStatus').textContent = '运行中';
        document.getElementById('progressText').textContent = `1 / ${cards.length}`;
        
        startCountdown();
        startElapsedTimer();
        refreshStatus();
    } catch (e) {
        alert('开始模拟失败: ' + e.message);
    }
}

async function pauseBatch() {
    try {
        await apiCall('/api/rfid-simulator/batch/pause', { method: 'POST' });
        state.isPaused = true;
        stopCountdown();
        refreshStatus();
    } catch (e) {
        alert('暂停失败: ' + e.message);
    }
}

async function resumeBatch() {
    try {
        await apiCall('/api/rfid-simulator/batch/resume', { method: 'POST' });
        state.isPaused = false;
        startCountdown();
        refreshStatus();
    } catch (e) {
        alert('恢复失败: ' + e.message);
    }
}

async function stopBatch() {
    try {
        await apiCall('/api/rfid-simulator/batch/stop', { method: 'POST' });
        state.isRunning = false;
        state.isPaused = false;
        stopCountdown();
        stopElapsedTimer();
        refreshStatus();
    } catch (e) {
        alert('停止失败: ' + e.message);
    }
}

function startCountdown() {
    state.countdown = state.intervalSeconds;
    updateCountdownDisplay();
    
    state.countdownTimer = setInterval(() => {
        if (state.isPaused) return;
        state.countdown--;
        if (state.countdown <= 0) state.countdown = state.intervalSeconds;
        updateCountdownDisplay();
    }, 1000);
}

function stopCountdown() {
    if (state.countdownTimer) {
        clearInterval(state.countdownTimer);
        state.countdownTimer = null;
    }
    document.getElementById('countdown').textContent = '-';
}

function updateCountdownDisplay() {
    document.getElementById('countdown').textContent = `${state.countdown}s`;
}

function startElapsedTimer() {
    state.elapsedTimer = setInterval(() => {
        if (state.startTime && !state.isPaused) {
            const elapsed = Math.floor((Date.now() - state.startTime) / 1000);
            const mins = Math.floor(elapsed / 60);
            const secs = elapsed % 60;
            document.getElementById('elapsedTime').textContent = `${mins}:${secs.toString().padStart(2, '0')}`;
        }
    }, 1000);
}

function stopElapsedTimer() {
    if (state.elapsedTimer) {
        clearInterval(state.elapsedTimer);
        state.elapsedTimer = null;
    }
}

// ==================== 工具函数 ====================

function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ==================== 收藏夹功能 ====================

const FAVORITES_KEY = 'rfid_favorites';
let favorites = [];
let editingFavoriteId = null;

// 加载收藏夹
function loadFavorites() {
    try {
        const saved = localStorage.getItem(FAVORITES_KEY);
        favorites = saved ? JSON.parse(saved) : [];
    } catch (e) {
        console.error('加载收藏夹失败:', e);
        favorites = [];
    }
    renderFavoriteCards();
}

// 保存收藏夹
function saveFavorites() {
    try {
        localStorage.setItem(FAVORITES_KEY, JSON.stringify(favorites));
    } catch (e) {
        console.error('保存收藏夹失败:', e);
    }
}

// 渲染收藏卡片
function renderFavoriteCards() {
    const container = document.getElementById('favoriteCards');
    if (!container) return;
    
    if (favorites.length === 0) {
        container.innerHTML = '<div class="favorite-empty">暂无记录</div>';
        return;
    }
    
    container.innerHTML = favorites.map(fav => `
        <div class="favorite-card ${state.selectedItem?.id === fav.id ? 'active' : ''}" 
             onclick="selectFavorite('${fav.id}', '${fav.type}')">
            <div class="fav-info">
                <div class="fav-name">${escapeHtml(fav.name)}</div>
                <div class="fav-meta">
                    <span class="fav-count">${fav.studentCount || 0} 人</span>
                    ${fav.tag ? `<span class="fav-tag">${escapeHtml(fav.tag)}</span>` : ''}
                </div>
            </div>
            <div class="fav-actions">
                <button class="fav-btn" onclick="event.stopPropagation(); openEditTagModal('${fav.id}')" title="编辑标签">
                    <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                </button>
                <button class="fav-btn" onclick="event.stopPropagation(); removeFavorite('${fav.id}')" title="移除">
                    <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/></svg>
                </button>
            </div>
        </div>
    `).join('');
}

// 添加到收藏（最近使用）
function addToRecent(type, item) {
    // 检查是否已存在
    const existIndex = favorites.findIndex(f => f.id === item.id && f.type === type);
    
    if (existIndex >= 0) {
        // 已存在，移到最前面并更新学生数
        const existing = favorites.splice(existIndex, 1)[0];
        existing.lastUsed = Date.now();
        existing.studentCount = state.allStudents?.length || existing.studentCount || 0;
        favorites.unshift(existing);
    } else {
        // 新增
        favorites.unshift({
            id: item.id,
            type: type,
            name: item.name,
            studentCount: state.allStudents?.length || 0,
            tag: '',
            lastUsed: Date.now()
        });
        
        // 最多保留10个
        if (favorites.length > 10) {
            favorites = favorites.slice(0, 10);
        }
    }
    
    saveFavorites();
    renderFavoriteCards();
}

// 选择收藏项
async function selectFavorite(id, type) {
    const fav = favorites.find(f => f.id === id);
    if (!fav) return;
    
    if (type === 'class') {
        await selectClass(id, fav.name);
    } else if (type === 'book') {
        await selectBook(id, fav.name);
    }
}

// 移除收藏
function removeFavorite(id) {
    favorites = favorites.filter(f => f.id !== id);
    saveFavorites();
    renderFavoriteCards();
}

// 清空收藏
function clearFavorites() {
    if (favorites.length === 0) return;
    if (!confirm('确定清空所有最近使用记录?')) return;
    
    favorites = [];
    saveFavorites();
    renderFavoriteCards();
}

// 打开编辑标签弹窗
function openEditTagModal(id) {
    const fav = favorites.find(f => f.id === id);
    if (!fav) return;
    
    editingFavoriteId = id;
    document.getElementById('editTagName').textContent = fav.name;
    document.getElementById('editTagCount').textContent = `${fav.studentCount || 0} 人`;
    document.getElementById('editTagInput').value = fav.tag || '';
    document.getElementById('editTagModal').style.display = 'flex';
}

// 关闭编辑标签弹窗
function closeEditTagModal() {
    editingFavoriteId = null;
    document.getElementById('editTagModal').style.display = 'none';
}

// 设置预设标签
function setTagPreset(tag) {
    document.getElementById('editTagInput').value = tag;
}

// 保存标签
function saveEditTag() {
    if (!editingFavoriteId) return;
    
    const tag = document.getElementById('editTagInput').value.trim();
    const fav = favorites.find(f => f.id === editingFavoriteId);
    
    if (fav) {
        fav.tag = tag;
        saveFavorites();
        renderFavoriteCards();
    }
    
    closeEditTagModal();
}


// ==================== 一键发布作业 ====================

// 发布状态
const publishState = {
    loggedIn: false,
    token: null,
    teacherInfo: null,
    bookList: [],
    classList: []
};

// API 登录
async function apiLogin() {
    const username = document.getElementById('apiUsername').value.trim();
    const password = document.getElementById('apiPassword').value.trim();
    
    if (!username || !password) {
        alert('请输入账号和密码');
        return;
    }
    
    const statusEl = document.getElementById('apiLoginStatus');
    const statusDot = statusEl.querySelector('.status-dot');
    const statusText = statusEl.querySelector('.status-text');
    const loginBtn = statusEl.querySelector('button');
    
    statusText.textContent = '登录中...';
    loginBtn.disabled = true;
    
    try {
        const result = await apiCall('/api/rfid-simulator/homework/login', {
            method: 'POST',
            body: JSON.stringify({ username, password })
        });
        
        publishState.loggedIn = true;
        publishState.token = result.token;
        publishState.teacherInfo = result.userInfo;
        publishState.bookList = result.bookList || [];
        publishState.classList = result.classList || [];
        
        // 更新登录状态
        statusDot.className = 'status-dot online';
        statusText.textContent = '已登录';
        loginBtn.textContent = '重新登录';
        
        // 显示教师信息
        showTeacherInfo(result);
        
    } catch (e) {
        statusDot.className = 'status-dot offline';
        statusText.textContent = '登录失败';
        alert('登录失败: ' + e.message);
    } finally {
        loginBtn.disabled = false;
    }
}

// 显示教师信息
function showTeacherInfo(data) {
    const card = document.getElementById('teacherInfoCard');
    card.style.display = 'block';
    
    // 教师名称
    const userInfo = data.userInfo || {};
    document.getElementById('teacherName').textContent = userInfo.realname || userInfo.username || '-';
    
    // 科目（从书本列表推断）
    const subjectMap = { 0: '英语', 1: '语文', 2: '数学', 3: '物理', 4: '化学', 5: '生物', 6: '地理' };
    const subjectId = publishState.bookList[0]?.subjectId;
    document.getElementById('teacherSubject').textContent = subjectMap[subjectId] || '-';
    
    // 填充书本下拉框
    const bookSelect = document.getElementById('apiBookSelect');
    bookSelect.innerHTML = '<option value="">请选择书本</option>' + 
        publishState.bookList.map(book => 
            `<option value="${book.id}" data-subject="${book.subjectId}">${escapeHtml(book.bookName)}</option>`
        ).join('');
    
    // 填充班级下拉框
    const classSelect = document.getElementById('apiClassSelect');
    classSelect.innerHTML = '<option value="">请选择班级</option>' + 
        publishState.classList.map(cls => 
            `<option value="${cls.id}">${escapeHtml(cls.className || cls.name)}</option>`
        ).join('');
    
    // 启用发布按钮
    updatePublishBtnState();
}

// 书本选择变化
function onBookChange() {
    updatePublishBtnState();
}

// 更新发布按钮状态
function updatePublishBtnState() {
    const bookId = document.getElementById('apiBookSelect').value;
    const classId = document.getElementById('apiClassSelect').value;
    const pageRegion = document.getElementById('apiPageRegion').value.trim();
    
    const btn = document.getElementById('apiPublishBtn');
    btn.disabled = !publishState.loggedIn || !bookId || !classId || !pageRegion;
}

// 一键发布作业
async function oneClickPublish() {
    const bookId = document.getElementById('apiBookSelect').value;
    const classId = document.getElementById('apiClassSelect').value;
    const pageRegion = document.getElementById('apiPageRegion').value.trim();
    
    if (!bookId || !classId || !pageRegion) {
        alert('请填写完整信息');
        return;
    }
    
    // 获取科目 ID
    const bookOption = document.getElementById('apiBookSelect').selectedOptions[0];
    const subjectId = parseInt(bookOption.dataset.subject) || 2;
    
    const btn = document.getElementById('apiPublishBtn');
    const originalText = btn.textContent;
    btn.textContent = '发布中...';
    btn.disabled = true;
    
    try {
        const username = document.getElementById('apiUsername').value.trim();
        const password = document.getElementById('apiPassword').value.trim();
        
        await apiCall('/api/rfid-simulator/homework/one-click', {
            method: 'POST',
            body: JSON.stringify({
                username,
                password,
                book_id: bookId,
                class_id: classId,
                subject_id: subjectId,
                page_region: pageRegion
            })
        });
        
        alert('作业发布成功！');
        
        // 更新发布状态
        const statusEl = document.getElementById('publishStatus');
        if (statusEl) {
            statusEl.textContent = '已完成';
            statusEl.className = 'workflow-card-status success';
        }
        
    } catch (e) {
        alert('发布失败: ' + e.message);
    } finally {
        btn.textContent = originalText;
        updatePublishBtnState();
    }
}

// 页码输入监听
document.addEventListener('DOMContentLoaded', () => {
    const pageInput = document.getElementById('apiPageRegion');
    if (pageInput) {
        pageInput.addEventListener('input', updatePublishBtnState);
    }
    
    const classSelect = document.getElementById('apiClassSelect');
    if (classSelect) {
        classSelect.addEventListener('change', updatePublishBtnState);
    }
});


// ==================== 智能发布作业 ====================

// 智能发布状态
const smartPublishState = {
    mode: 'smart',  // smart | manual
    books: [],
    teachers: [],
    selectedTeacher: null,
    selectedBook: null
};

// 切换发布模式
function switchPublishMode(mode) {
    smartPublishState.mode = mode;
    
    // 更新按钮状态
    document.querySelectorAll('.publish-mode-switch .mode-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.mode === mode);
    });
    
    // 切换内容显示
    document.getElementById('smartModeContent').style.display = mode === 'smart' ? 'block' : 'none';
    document.getElementById('manualModeContent').style.display = mode === 'manual' ? 'block' : 'none';
}

// 加载书本列表（智能模式）
async function loadSmartBooks() {
    const select = document.getElementById('smartBookSelect');
    if (!select) return;
    
    try {
        const result = await apiCall('/api/smart-publish/books');
        smartPublishState.books = result || [];
        
        select.innerHTML = '<option value="">请选择书本...</option>' + 
            smartPublishState.books.map(book => 
                `<option value="${book.id}">${escapeHtml(book.book_name)} (${book.subject_name})</option>`
            ).join('');
    } catch (e) {
        console.error('加载书本列表失败:', e);
        select.innerHTML = '<option value="">加载失败</option>';
    }
}

// 书本选择变化
async function onSmartBookChange() {
    const bookId = document.getElementById('smartBookSelect').value;
    const teacherInfo = document.getElementById('teacherAutoInfo');
    const teacherDisplay = document.getElementById('autoTeacherDisplay');
    const changeBtn = document.getElementById('changeTeacherBtn');
    
    if (!bookId) {
        teacherInfo.style.display = 'none';
        smartPublishState.selectedTeacher = null;
        smartPublishState.teachers = [];
        updateSmartPublishBtn();
        return;
    }
    
    try {
        const result = await apiCall(`/api/smart-publish/teachers?book_id=${bookId}`);
        smartPublishState.teachers = result.teachers || [];
        smartPublishState.selectedTeacher = result.selected_teacher;
        
        teacherInfo.style.display = 'block';
        
        if (smartPublishState.selectedTeacher) {
            const t = smartPublishState.selectedTeacher;
            teacherDisplay.textContent = `${t.teacher_name} - ${t.class_name}`;
        } else if (smartPublishState.teachers.length > 0) {
            teacherDisplay.textContent = '请选择老师';
        } else {
            teacherDisplay.textContent = '无绑定老师';
        }
        
        // 多个老师时显示切换按钮
        changeBtn.style.display = result.need_select ? 'inline-block' : 'none';
        
    } catch (e) {
        console.error('加载老师列表失败:', e);
        teacherInfo.style.display = 'block';
        teacherDisplay.textContent = '加载失败';
    }
    
    updateSmartPublishBtn();
}

// 更新智能发布按钮状态
function updateSmartPublishBtn() {
    const bookId = document.getElementById('smartBookSelect').value;
    const pageRegion = document.getElementById('smartPageRegion').value.trim();
    const btn = document.getElementById('smartPublishBtn');
    const preview = document.getElementById('homeworkPreview');
    const previewValue = document.getElementById('homeworkNamePreview');
    
    const canPublish = bookId && smartPublishState.selectedTeacher && pageRegion;
    btn.disabled = !canPublish;
    
    // 更新作业名称预览
    if (pageRegion) {
        const timestamp = new Date().toISOString().slice(0,10).replace(/-/g,'') + '_' + 
                         new Date().toTimeString().slice(0,8).replace(/:/g,'');
        previewValue.textContent = `自动测试P${pageRegion}_${timestamp}`;
        preview.style.display = 'flex';
    } else {
        preview.style.display = 'none';
    }
}

// 执行智能发布
async function smartPublish() {
    const bookId = document.getElementById('smartBookSelect').value;
    const pageRegion = document.getElementById('smartPageRegion').value.trim();
    
    if (!bookId || !smartPublishState.selectedTeacher || !pageRegion) {
        alert('请填写完整信息');
        return;
    }
    
    const btn = document.getElementById('smartPublishBtn');
    const originalText = btn.textContent;
    btn.textContent = '发布中...';
    btn.disabled = true;
    
    try {
        const result = await apiCall('/api/smart-publish/publish', {
            method: 'POST',
            body: JSON.stringify({
                book_id: bookId,
                teacher_id: smartPublishState.selectedTeacher.id,
                class_id: smartPublishState.selectedTeacher.class_id,
                pages: pageRegion
            })
        });
        
        // 根据是否触发了提交流程显示不同提示
        let msg = `发布成功！\n作业名称: ${result.homework_name}\n老师: ${result.teacher_name}\n班级: ${result.class_name}`;
        if (result.submit_triggered) {
            msg += '\n\n已自动触发提交作业流程，请关注 ADB 客户端执行状态。';
        } else if (result.submit_error) {
            msg += `\n\n自动提交失败: ${result.submit_error}`;
        } else {
            msg += '\n\n未触发自动提交（无 ADB 连接或无学生数据）';
        }
        alert(msg);
        
        // 更新发布状态
        const statusEl = document.getElementById('publishStatus');
        if (statusEl) {
            statusEl.textContent = result.submit_triggered ? '发布+提交中' : '已发布';
            statusEl.className = 'workflow-card-status success';
        }
        
        // 清空页码输入
        document.getElementById('smartPageRegion').value = '';
        updateSmartPublishBtn();
        
    } catch (e) {
        alert('发布失败: ' + e.message);
    } finally {
        btn.textContent = originalText;
        updateSmartPublishBtn();
    }
}

// 显示老师选择弹窗
function showTeacherSelectModal() {
    const modal = document.getElementById('teacherSelectModal');
    const list = document.getElementById('teacherSelectList');
    
    if (!smartPublishState.teachers || smartPublishState.teachers.length === 0) {
        alert('没有可选择的老师');
        return;
    }
    
    list.innerHTML = smartPublishState.teachers.map(t => `
        <div class="teacher-select-item ${smartPublishState.selectedTeacher?.id === t.id && smartPublishState.selectedTeacher?.class_id === t.class_id ? 'selected' : ''}" 
             onclick="selectSmartTeacher('${t.id}', '${t.class_id}')">
            <div>
                <div class="teacher-name">${escapeHtml(t.teacher_name)}</div>
                <div class="teacher-class">${escapeHtml(t.class_name)}</div>
            </div>
        </div>
    `).join('');
    
    modal.style.display = 'flex';
}

// 关闭老师选择弹窗
function closeTeacherSelectModal() {
    document.getElementById('teacherSelectModal').style.display = 'none';
}

// 选择老师
function selectSmartTeacher(teacherId, classId) {
    const teacher = smartPublishState.teachers.find(t => t.id === teacherId && t.class_id === classId);
    if (teacher) {
        smartPublishState.selectedTeacher = teacher;
        document.getElementById('autoTeacherDisplay').textContent = `${teacher.teacher_name} - ${teacher.class_name}`;
        updateSmartPublishBtn();
    }
    closeTeacherSelectModal();
}

// 初始化智能发布
document.addEventListener('DOMContentLoaded', () => {
    // 加载书本列表
    loadSmartBooks();
    
    // 页码输入监听
    const smartPageInput = document.getElementById('smartPageRegion');
    if (smartPageInput) {
        smartPageInput.addEventListener('input', updateSmartPublishBtn);
    }
});
