/**
 * RFID 模拟器 - 增强版
 */

// ==================== 状态 ====================

const state = {
    currentTab: 'class',
    currentGrade: 0,
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
    elapsedTimer: null    // 耗时计时器
};

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', () => {
    initGradeFilter();
    initTabSwitch();
    initIntervalButtons();
    initCustomInterval();
    initSearch();
    initKeyboardShortcuts();
    loadList();
    refreshStatus();
    startPolling();
});

function initGradeFilter() {
    document.querySelectorAll('.grade-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            document.querySelectorAll('.grade-btn').forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            state.currentGrade = parseInt(btn.dataset.grade);
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
            input.placeholder = state.currentTab === 'class' ? '搜索班级名称...' : '搜索书本名称...';
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
            if (state.currentGrade > 0) {
                data = data.filter(b => b.grade_id === state.currentGrade);
            }
            renderBookList(data);
        }
    } catch (e) {
        container.innerHTML = `<div class="list-empty">加载失败: ${e.message}</div>`;
    }
}

function renderClassList(classes) {
    const container = document.getElementById('listContainer');
    
    if (!classes || classes.length === 0) {
        container.innerHTML = '<div class="list-empty">暂无班级数据</div>';
        return;
    }
    
    container.innerHTML = classes.map(cls => `
        <div class="list-item ${state.selectedItem?.id === cls.id && state.selectedItem?.type === 'class' ? 'active' : ''}" 
             onclick="selectClass('${cls.id}', '${escapeHtml(cls.name)}')">
            <div class="item-name">${escapeHtml(cls.name)}</div>
            <div class="item-meta">
                <span>${cls.student_count || 0} 人</span>
            </div>
        </div>
    `).join('');
}

function renderBookList(books) {
    const container = document.getElementById('listContainer');
    
    if (!books || books.length === 0) {
        container.innerHTML = '<div class="list-empty">暂无书本数据</div>';
        return;
    }
    
    container.innerHTML = books.map(book => `
        <div class="list-item ${state.selectedItem?.id === book.id && state.selectedItem?.type === 'book' ? 'active' : ''}" 
             onclick="selectBook('${book.id}', '${escapeHtml(book.book_name)}')">
            <div class="item-name">${escapeHtml(book.book_name)}</div>
            <div class="item-meta">
                ${book.subject_name ? `<span>${escapeHtml(book.subject_name)}</span>` : ''}
                ${book.grade_name ? `<span>${escapeHtml(book.grade_name)}</span>` : ''}
            </div>
        </div>
    `).join('');
}

// ==================== 选择处理 ====================

async function selectClass(classId, className) {
    state.selectedItem = { type: 'class', id: classId, name: className };
    
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
    await loadStudents(`/api/nfc/class/${classId}/students`, className);
}

async function selectBook(bookId, bookName) {
    state.selectedItem = { type: 'book', id: bookId, name: bookName };
    
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
    event.currentTarget.classList.add('active');
    
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
    const filter = document.querySelector('input[name="studentFilter"]:checked')?.value || 'all';
    state.studentFilter = filter;
    
    if (filter === 'all') {
        state.students = [...state.allStudents];
    } else if (filter === 'rep') {
        state.students = state.allStudents.filter(s => s.is_representative);
    } else {
        state.students = state.allStudents.filter(s => !s.is_representative);
    }
    
    // 更新预览
    updateStudentPreview();
    
    // 更新按钮状态
    document.getElementById('startBtn').disabled = state.students.length === 0;
}

function updateStudentPreview() {
    const preview = document.getElementById('studentPreview');
    if (state.students.length === 0) {
        preview.innerHTML = '<span style="color:var(--text-muted)">暂无符合条件的学生</span>';
    } else {
        preview.innerHTML = state.students.slice(0, 15).map(s => 
            `<span class="student-tag ${s.is_representative ? 'rep' : ''}">${escapeHtml(s.name)}</span>`
        ).join('') + (state.students.length > 15 ? `<span class="student-tag">+${state.students.length - 15}</span>` : '');
    }
}

function showSelectedCard(title, allStudents, repCount, validCount) {
    document.getElementById('selectedInfo').style.display = 'block';
    document.getElementById('filterRow').style.display = 'flex';
    document.getElementById('studentPreview').style.display = 'block';
    document.getElementById('configSection').style.display = 'block';
    document.getElementById('selectedTitle').textContent = title;
    document.getElementById('studentCount').textContent = allStudents.length;
    document.getElementById('repCount').textContent = repCount;
    document.getElementById('validCount').textContent = validCount;
    
    updateStudentPreview();
    document.getElementById('startBtn').disabled = state.students.length === 0;
}

function clearSelection() {
    state.selectedItem = null;
    state.allStudents = [];
    state.students = [];
    
    document.getElementById('selectedInfo').style.display = 'none';
    document.getElementById('filterRow').style.display = 'none';
    document.getElementById('studentPreview').style.display = 'none';
    document.getElementById('configSection').style.display = 'none';
    document.getElementById('startBtn').disabled = true;
    
    document.querySelectorAll('.list-item').forEach(item => item.classList.remove('active'));
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
    const quickActions = document.getElementById('quickActions');
    
    if (data.connected && data.client) {
        const client = data.client;
        
        // 隐藏提示，显示链路
        connectHint.style.display = 'none';
        connectionChain.style.display = 'block';
        quickActions.style.display = 'flex';
        
        // 更新客户端状态
        document.getElementById('clientDot').className = 'node-dot online';
        document.getElementById('clientIp').textContent = client.ip_address || '-';
        document.getElementById('clientStatus').textContent = '在线';
        document.getElementById('clientStatus').className = 'node-status online';
        
        // 更新设备状态
        const deviceInfo = client.device_info || {};
        if (deviceInfo.connected) {
            document.getElementById('deviceDot').className = 'node-dot online';
            document.getElementById('deviceIp').textContent = deviceInfo.device_ip || '-';
            document.getElementById('deviceStatus').textContent = '已连接';
            document.getElementById('deviceStatus').className = 'node-status online';
            
            document.getElementById('deviceDetail').style.display = 'flex';
            document.getElementById('deviceModel').textContent = deviceInfo.model || '-';
            document.getElementById('devicePath').textContent = deviceInfo.device_path || '/dev/input/event2';
        } else {
            document.getElementById('deviceDot').className = 'node-dot warning';
            document.getElementById('deviceIp').textContent = deviceInfo.device_ip || '-';
            document.getElementById('deviceStatus').textContent = '未连接';
            document.getElementById('deviceStatus').className = 'node-status';
            document.getElementById('deviceDetail').style.display = 'none';
        }
    } else {
        // 显示提示，隐藏链路
        connectHint.style.display = 'flex';
        connectionChain.style.display = 'none';
        quickActions.style.display = 'none';
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

async function refreshLogs() {
    try {
        const logs = await apiCall('/api/rfid-simulator/logs?limit=30');
        renderLogs(logs);
    } catch (e) {
        console.error('刷新日志失败:', e);
    }
}

function renderLogs(logs) {
    const logList = document.getElementById('logList');
    
    if (!logs || logs.length === 0) {
        logList.innerHTML = '<div class="log-empty">暂无日志</div>';
        return;
    }
    
    logList.innerHTML = logs.map(log => `
        <div class="log-item ${log.level}">
            <span class="log-time">${log.time}</span>
            <span>${escapeHtml(log.message)}</span>
        </div>
    `).join('');
}

async function clearLogs() {
    try {
        await apiCall('/api/rfid-simulator/logs', { method: 'DELETE' });
        refreshLogs();
    } catch (e) {
        console.error('清空日志失败:', e);
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
    
    const sendEnter = document.getElementById('sendEnter').checked;
    
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
