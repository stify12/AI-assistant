/**
 * 作业测试工具 - JavaScript（解耦版7步流程）
 */

// ==================== 全局状态 ====================
const state = {
    currentStep: 1,
    // 步骤1: 服务器配置
    deviceApiUrl: 'https://cms.test.gzzhengpu.cn/api/v1/device',
    javaBackendUrl: 'https://oss.test.gzzhengpu.cn/jeecg-boot',
    deviceMac: '59411cc01588',
    // 步骤2: 基础配置
    bookId: '',
    classId: '',
    pageStart: 102,
    pageEnd: 108,
    excludeStudents: ['李小龙', '陈逸飞'],
    // 步骤3: 学生管理
    studentMode: 'real', // 'real' | 'virtual'
    students: [],
    selectedStudents: new Set(),
    // 步骤4: 发布作业
    taskMode: 'existing', // 'existing' | 'publish'
    tasks: [],
    selectedTaskId: '',
    publishedTaskId: '',
    // 步骤5: 图片来源
    images: [],
    selectedImages: new Set(),
    // 步骤6: 映射
    mappingMode: 'one_to_one',
    mappingPageStart: 1,
    mappingData: [],
    // 步骤7: 提交
    submitTaskId: '',
    imagesByPage: {}
};

// ==================== 初始化 ====================
document.addEventListener('DOMContentLoaded', function() {
    loadBooks();
    loadClasses();
    syncPageRegion();
    updateStepUI();
});

// ==================== 步骤导航 ====================
function goToStep(step) {
    state.currentStep = step;
    updateStepUI();
    // 进入特定步骤时触发
    if (step === 4) syncPageRegion();
    if (step === 6) updateMappingPreview();
    if (step === 7) updateSummary();
}

function updateStepUI() {
    document.querySelectorAll('.step-content').forEach(el => el.classList.add('hidden'));
    const el = document.getElementById(`step${state.currentStep}`);
    if (el) el.classList.remove('hidden');

    document.querySelectorAll('.step-item').forEach(el => {
        const n = parseInt(el.dataset.step);
        el.classList.remove('active', 'completed');
        if (n === state.currentStep) el.classList.add('active');
        else if (n < state.currentStep) el.classList.add('completed');
    });
}

// 同步页码范围到发布面板
function syncPageRegion() {
    const ps = document.getElementById('pageStart')?.value;
    const pe = document.getElementById('pageEnd')?.value;
    const input = document.getElementById('publishPageRegion');
    if (input && ps && pe && !input.value) {
        input.value = `${ps}-${pe}`;
    }
}

// ==================== 步骤1: 服务器配置 ====================
async function testConnection() {
    const statusEl = document.getElementById('connectionStatus');
    statusEl.innerHTML = '<span class="status-dot offline"></span><span class="status-text">检测中...</span>';

    const deviceUrl = document.getElementById('deviceApiUrl').value;
    const javaUrl = document.getElementById('javaBackendUrl').value;
    state.deviceApiUrl = deviceUrl;
    state.javaBackendUrl = javaUrl;
    state.deviceMac = document.getElementById('deviceMac').value;

    try {
        const resp = await fetch('/api/homework-test/test-connection', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ device_api_url: deviceUrl, java_backend_url: javaUrl })
        });
        const data = await resp.json();
        if (data.success) {
            statusEl.innerHTML = '<span class="status-dot online"></span><span class="status-text">连接正常</span>';
        } else {
            statusEl.innerHTML = `<span class="status-dot error"></span><span class="status-text">${data.message || '连接失败'}</span>`;
        }
    } catch (e) {
        statusEl.innerHTML = '<span class="status-dot error"></span><span class="status-text">请求失败</span>';
    }
}

// ==================== 步骤2: 基础配置 ====================
async function loadBooks() {
    try {
        const resp = await fetch('/api/homework-test/books');
        const data = await resp.json();
        if (data.success) {
            const select = document.getElementById('bookSelect');
            data.books.forEach(book => {
                const opt = document.createElement('option');
                opt.value = book.id;
                opt.textContent = book.book_name;
                select.appendChild(opt);
            });
        }
    } catch (e) { console.error('加载书籍失败:', e); }
}

async function loadClasses() {
    try {
        const resp = await fetch('/api/homework-test/classes');
        const data = await resp.json();
        if (data.success) {
            const select = document.getElementById('classSelect');
            data.classes.forEach(cls => {
                const opt = document.createElement('option');
                opt.value = cls.id;
                opt.textContent = cls.class_name;
                select.appendChild(opt);
            });
        }
    } catch (e) { console.error('加载班级失败:', e); }
}

function onBookChange() { state.bookId = document.getElementById('bookSelect').value; }
function onClassChange() { state.classId = document.getElementById('classSelect').value; }

// ==================== 步骤3: 学生管理 ====================
function switchStudentMode(mode) {
    state.studentMode = mode;
    document.querySelectorAll('#step3 .mode-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
    });
    document.getElementById('realStudentPanel').classList.toggle('hidden', mode !== 'real');
    document.getElementById('virtualStudentPanel').classList.toggle('hidden', mode !== 'virtual');
}

async function loadStudents() {
    const bookId = document.getElementById('bookSelect').value;
    const classId = document.getElementById('classSelect').value;
    const exclude = document.getElementById('excludeStudents').value;
    if (!bookId || !classId) { alert('请先选择书籍和班级'); return; }

    const grid = document.getElementById('studentGrid');
    grid.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在加载...</div>';

    try {
        const resp = await fetch(`/api/homework-test/students?book_id=${bookId}&class_id=${classId}&exclude=${encodeURIComponent(exclude)}`);
        const data = await resp.json();
        if (data.success) {
            state.students = data.students.map(s => ({ ...s, _type: 'real' }));
            state.selectedStudents.clear();
            renderStudents();
        } else {
            grid.innerHTML = `<div class="empty-state"><p class="empty-state-text">${data.message}</p></div>`;
        }
    } catch (e) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">网络请求失败</p></div>';
    }
}

async function generateVirtualStudents() {
    const count = parseInt(document.getElementById('virtualCount').value) || 10;
    const prefix = document.getElementById('virtualPrefix').value || '测试学生';
    const bookId = document.getElementById('bookSelect').value;
    const classId = document.getElementById('classSelect').value;
    if (!bookId || !classId) { alert('请先在步骤2中选择书籍和班级'); return; }
    if (count < 1 || count > 30) { alert('数量须在1-30之间'); return; }

    const grid = document.getElementById('studentGrid');
    grid.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在生成...</div>';

    try {
        const resp = await fetch('/api/homework-test/virtual-students/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ count, prefix, book_id: bookId, class_id: classId })
        });
        const data = await resp.json();
        if (data.success) {
            state.students = data.students.map(s => ({ ...s, _type: 'virtual' }));
            state.selectedStudents.clear();
            // 自动全选
            state.students.forEach(s => state.selectedStudents.add(s.id));
            renderStudents();
        } else {
            grid.innerHTML = `<div class="empty-state"><p class="empty-state-text">${data.message}</p></div>`;
        }
    } catch (e) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">生成失败</p></div>';
    }
}

async function loadVirtualStudents() {
    const bookId = document.getElementById('bookSelect').value;
    const classId = document.getElementById('classSelect').value;
    if (!bookId || !classId) { alert('请先选择书籍和班级'); return; }

    const grid = document.getElementById('studentGrid');
    grid.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在加载...</div>';

    try {
        const resp = await fetch(`/api/homework-test/virtual-students?book_id=${bookId}&class_id=${classId}`);
        const data = await resp.json();
        if (data.success) {
            state.students = data.students.map(s => ({ ...s, _type: 'virtual' }));
            state.selectedStudents.clear();
            state.students.forEach(s => state.selectedStudents.add(s.id));
            renderStudents();
        } else {
            grid.innerHTML = `<div class="empty-state"><p class="empty-state-text">${data.message}</p></div>`;
        }
    } catch (e) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">加载失败</p></div>';
    }
}

async function cleanupVirtualStudents() {
    if (!confirm('确定要清理所有虚拟学生数据吗？此操作不可恢复。')) return;
    const classId = document.getElementById('classSelect').value;

    try {
        const resp = await fetch('/api/homework-test/virtual-students', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ class_id: classId || null })
        });
        const data = await resp.json();
        alert(data.success ? `已清理 ${data.deleted || 0} 个虚拟学生` : (data.message || '清理失败'));
        if (data.success) {
            state.students = [];
            state.selectedStudents.clear();
            renderStudents();
        }
    } catch (e) { alert('请求失败'); }
}

function renderStudents() {
    const grid = document.getElementById('studentGrid');
    grid.innerHTML = '';

    if (state.students.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">没有学生数据</p></div>';
        updateStudentStats();
        return;
    }

    state.students.forEach(student => {
        const isVirtual = student._type === 'virtual';
        const selected = state.selectedStudents.has(student.id);
        const div = document.createElement('div');
        div.className = `student-item ${selected ? 'selected' : ''} ${isVirtual ? 'virtual' : ''}`;
        div.onclick = () => toggleStudent(student.id);
        div.innerHTML = `
            <div class="student-name">${student.name}</div>
            <div class="student-rfid">${student.rfid_no || '-'}</div>
            <div class="student-id">${student.stu_num || ''}</div>
            <span class="student-tag ${isVirtual ? 'tag-virtual' : 'tag-real'}">${isVirtual ? '虚拟' : '真实'}</span>
        `;
        grid.appendChild(div);
    });
    updateStudentStats();
}

function updateStudentStats() {
    const statsEl = document.getElementById('studentStats');
    if (state.students.length > 0) statsEl.classList.remove('hidden');
    else statsEl.classList.add('hidden');

    document.getElementById('totalStudents').textContent = state.students.length;
    document.getElementById('selectedStudents').textContent = state.selectedStudents.size;
    document.getElementById('studentType').textContent =
        state.students.length > 0 ? (state.students[0]._type === 'virtual' ? '虚拟' : '真实') : '-';
}

function toggleStudent(id) {
    state.selectedStudents.has(id) ? state.selectedStudents.delete(id) : state.selectedStudents.add(id);
    renderStudents();
}

function selectAllStudents() {
    state.students.forEach(s => state.selectedStudents.add(s.id));
    renderStudents();
}

function selectTopStudents(n) {
    state.selectedStudents.clear();
    state.students.slice(0, n).forEach(s => state.selectedStudents.add(s.id));
    renderStudents();
}

// ==================== 步骤4: 发布作业 ====================
function switchTaskMode(mode) {
    state.taskMode = mode;
    document.querySelectorAll('#step4 .mode-btn').forEach(b => {
        b.classList.toggle('active', b.dataset.mode === mode);
    });
    document.getElementById('existingTaskPanel').classList.toggle('hidden', mode !== 'existing');
    document.getElementById('publishTaskPanel').classList.toggle('hidden', mode !== 'publish');
}

async function loadTasks() {
    const classId = document.getElementById('classSelect').value;
    if (!classId) { alert('请先选择班级'); return; }

    const list = document.getElementById('taskList');
    list.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在加载...</div>';

    try {
        const resp = await fetch(`/api/homework-test/tasks?class_id=${classId}`);
        const data = await resp.json();
        if (data.success) {
            state.tasks = data.tasks;
            renderTasks();
        } else {
            list.innerHTML = `<div class="empty-state"><p class="empty-state-text">${data.message}</p></div>`;
        }
    } catch (e) {
        list.innerHTML = '<div class="empty-state"><p class="empty-state-text">网络请求失败</p></div>';
    }
}

function renderTasks() {
    const list = document.getElementById('taskList');
    list.innerHTML = '';
    if (state.tasks.length === 0) {
        list.innerHTML = '<div class="empty-state"><p class="empty-state-text">没有作业任务</p></div>';
        return;
    }
    state.tasks.forEach(task => {
        const div = document.createElement('div');
        div.className = `task-item ${state.selectedTaskId === task.id ? 'selected' : ''}`;
        div.onclick = () => { state.selectedTaskId = task.id; renderTasks(); };
        div.innerHTML = `
            <div class="task-info">
                <div class="task-name">${task.content || '(无名称)'}</div>
                <div class="task-pages">页码: ${task.page_region}</div>
                <div class="task-time">${task.create_time}</div>
            </div>
            <span class="task-status ${task.status === 0 ? 'active' : 'ended'}">
                ${task.status === 0 ? '进行中' : '已结束'}
            </span>
        `;
        list.appendChild(div);
    });
}

async function publishHomework() {
    const bookId = document.getElementById('bookSelect').value;
    const classId = document.getElementById('classSelect').value;
    if (!bookId || !classId) { alert('请先在步骤2选择书籍和班级'); return; }

    const username = document.getElementById('teacherUsername').value;
    const password = document.getElementById('teacherPassword').value;
    const subjectId = document.getElementById('subjectSelect').value;
    const pageRegion = document.getElementById('publishPageRegion').value;
    const content = document.getElementById('publishContent').value;
    const endTime = document.getElementById('publishEndTime').value;

    if (!username || !password) { alert('请输入教师账号密码'); return; }
    if (!pageRegion) { alert('请输入页码范围'); return; }

    const btn = document.getElementById('publishBtn');
    btn.disabled = true;
    btn.textContent = '发布中...';
    const resultEl = document.getElementById('publishResult');
    resultEl.classList.add('hidden');

    try {
        const resp = await fetch('/api/homework-test/publish', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username, password, book_id: bookId, class_id: classId,
                subject_id: parseInt(subjectId), page_region: pageRegion,
                content: content || null,
                end_time: endTime ? endTime.replace('T', ' ') + ':00' : null
            })
        });
        const data = await resp.json();
        resultEl.classList.remove('hidden', 'success', 'error');
        if (data.success) {
            resultEl.classList.add('success');
            resultEl.textContent = `发布成功！任务ID: ${data.hw_publish_id || '-'}`;
            state.selectedTaskId = data.hw_publish_id || '';
            state.publishedTaskId = data.hw_publish_id || '';
        } else {
            resultEl.classList.add('error');
            resultEl.textContent = `发布失败: ${data.error || data.message || '未知错误'}`;
        }
    } catch (e) {
        resultEl.classList.remove('hidden');
        resultEl.classList.add('error');
        resultEl.textContent = '网络请求失败';
    } finally {
        btn.disabled = false;
        btn.textContent = '发布作业';
    }
}

// ==================== 步骤5: 图片来源 ====================
async function loadOssImages() {
    const bookId = document.getElementById('bookSelect').value;
    if (!bookId) { alert('请先选择书籍'); return; }

    const grid = document.getElementById('imageGrid');
    grid.innerHTML = '<div class="loading"><div class="loading-spinner"></div>正在加载...</div>';

    try {
        const resp = await fetch('/api/homework-test/oss/list', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                book_id: bookId,
                start_date: document.getElementById('startDate').value,
                end_date: document.getElementById('endDate').value,
                page_num: document.getElementById('filterPageNum').value,
                limit: parseInt(document.getElementById('imageLimit').value) || 200
            })
        });
        const data = await resp.json();
        if (data.success) {
            state.images = data.images;
            renderImages();
        } else {
            grid.innerHTML = `<div class="empty-state"><p class="empty-state-text">${data.message}</p></div>`;
        }
    } catch (e) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">网络请求失败</p></div>';
    }
}

function renderImages() {
    const grid = document.getElementById('imageGrid');
    grid.innerHTML = '';

    if (state.images.length === 0) {
        grid.innerHTML = '<div class="empty-state"><p class="empty-state-text">没有找到图片</p></div>';
        updateImageStats();
        return;
    }

    // 按页码分组
    const byPage = {};
    state.images.forEach(img => {
        const m = img.key.match(/_(\d+)_[^_]+\.jpg$/i);
        const page = m ? m[1] : 'other';
        if (!byPage[page]) byPage[page] = [];
        byPage[page].push(img);
    });

    Object.keys(byPage).sort((a, b) => parseInt(a) - parseInt(b)).forEach(page => {
        const section = document.createElement('div');
        section.className = 'image-page-section';

        const title = document.createElement('div');
        title.className = 'image-page-title';
        title.innerHTML = `页码 ${page} <span class="image-page-count">(${byPage[page].length}张)</span>`;
        section.appendChild(title);

        const imgsDiv = document.createElement('div');
        imgsDiv.className = 'image-grid';
        byPage[page].forEach(img => {
            const div = document.createElement('div');
            div.className = `image-item ${state.selectedImages.has(img.key) ? 'selected' : ''}`;
            div.onclick = () => { toggleImage(img.key); };
            div.innerHTML = `<img src="${img.url}" alt="" loading="lazy"><div class="image-item-overlay">&#10003;</div>`;
            imgsDiv.appendChild(div);
        });
        section.appendChild(imgsDiv);
        grid.appendChild(section);
    });
    updateImageStats();
}

function toggleImage(key) {
    state.selectedImages.has(key) ? state.selectedImages.delete(key) : state.selectedImages.add(key);
    renderImages();
}
function selectAllImages() { state.images.forEach(img => state.selectedImages.add(img.key)); renderImages(); }
function deselectAllImages() { state.selectedImages.clear(); renderImages(); }

function updateImageStats() {
    const el = document.getElementById('imageStats');
    if (state.images.length > 0) el.classList.remove('hidden');
    else el.classList.add('hidden');
    document.getElementById('totalImages').textContent = state.images.length;
    document.getElementById('selectedImages').textContent = state.selectedImages.size;
}

// ==================== 步骤6: 映射预览 ====================
function updateMappingPreview() {
    const mode = document.getElementById('mappingMode').value;
    const pageStart = parseInt(document.getElementById('mappingPageStart').value) || 1;
    state.mappingMode = mode;
    state.mappingPageStart = pageStart;

    const selectedStudents = state.students.filter(s => state.selectedStudents.has(s.id));
    const selectedImgs = state.images.filter(img => state.selectedImages.has(img.key));

    const mapping = [];

    if (mode === 'all_to_one') {
        // 所有图给第一个学生，每张为不同页码
        const student = selectedStudents[0];
        if (student) {
            selectedImgs.forEach((img, idx) => {
                mapping.push({
                    student: student.name,
                    rfid: student.rfid_no,
                    page: pageStart + idx,
                    imageUrl: img.url,
                    imageKey: img.key
                });
            });
        }
    } else if (mode === 'one_to_one') {
        // 每个学生一张图，页码相同
        const maxLen = Math.min(selectedStudents.length, selectedImgs.length);
        for (let i = 0; i < maxLen; i++) {
            mapping.push({
                student: selectedStudents[i].name,
                rfid: selectedStudents[i].rfid_no,
                page: pageStart,
                imageUrl: selectedImgs[i].url,
                imageKey: selectedImgs[i].key
            });
        }
    } else {
        // round_robin: 图片轮流分配
        selectedStudents.forEach((student, i) => {
            const img = selectedImgs[i % selectedImgs.length];
            if (img) {
                mapping.push({
                    student: student.name,
                    rfid: student.rfid_no,
                    page: pageStart,
                    imageUrl: img.url,
                    imageKey: img.key
                });
            }
        });
    }

    state.mappingData = mapping;

    // 更新统计
    document.getElementById('mapStudentCount').textContent = selectedStudents.length;
    document.getElementById('mapImageCount').textContent = selectedImgs.length;
    document.getElementById('mapTotalSubmits').textContent = mapping.length;

    // 渲染表格
    const tbody = document.getElementById('mappingTableBody');
    if (mapping.length === 0) {
        tbody.innerHTML = '<tr><td colspan="4" class="empty-cell">请先选择学生和图片</td></tr>';
        return;
    }

    tbody.innerHTML = mapping.map(m => `
        <tr>
            <td>${m.student}</td>
            <td><span class="rfid-tag">${m.rfid}</span></td>
            <td>${m.page}</td>
            <td><img class="img-thumb" src="${m.imageUrl}" alt="" loading="lazy"></td>
        </tr>
    `).join('');
}

// ==================== 步骤7: 提交执行 ====================
function updateSummary() {
    const selectedStudents = state.students.filter(s => state.selectedStudents.has(s.id));
    const selectedImgs = state.images.filter(img => state.selectedImages.has(img.key));
    const task = state.tasks.find(t => t.id === state.selectedTaskId);

    document.getElementById('summaryStudents').textContent = selectedStudents.length;
    document.getElementById('summaryImages').textContent = selectedImgs.length;
    document.getElementById('summaryPages').textContent = state.mappingData.length > 0
        ? [...new Set(state.mappingData.map(m => m.page))].length : '-';
    document.getElementById('summaryTask').textContent = task ? (task.content || task.id) : (state.publishedTaskId || '-');
    document.getElementById('summaryServer').textContent = state.deviceApiUrl;

    const modeLabels = { one_to_one: '一对一', all_to_one: '全给一人', round_robin: '轮流分配' };
    document.getElementById('summaryMode').textContent = modeLabels[state.mappingMode] || '-';
    document.getElementById('summaryStudentType').textContent =
        selectedStudents.length > 0 ? (selectedStudents[0]._type === 'virtual' ? '虚拟学生' : '真实学生') : '-';
    document.getElementById('summaryNote').textContent = `预计提交: ${state.mappingData.length} 次`;
}

async function startSubmit() {
    const selectedStudents = state.students.filter(s => state.selectedStudents.has(s.id));
    const taskId = state.selectedTaskId || state.publishedTaskId;

    if (!taskId) { alert('请先选择或发布作业任务'); return; }
    if (selectedStudents.length === 0) { alert('请选择学生'); return; }
    if (state.mappingData.length === 0) { alert('请先在映射预览中确认分配'); return; }

    document.getElementById('submitBtn').disabled = true;
    document.getElementById('progressContainer').classList.remove('hidden');
    document.getElementById('logContainer').classList.remove('hidden');
    document.getElementById('logContainer').innerHTML = '';

    // 构建提交数据
    const selectedImgs = state.images.filter(img => state.selectedImages.has(img.key));

    try {
        const resp = await fetch('/api/homework-test/submit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: taskId,
                students: selectedStudents,
                images: selectedImgs.map(i => i.url),
                mode: state.mappingMode,
                page_start: state.mappingPageStart,
                device_api_url: state.deviceApiUrl,
                device_mac: state.deviceMac,
                // 兼容旧接口
                images_by_page: state.imagesByPage
            })
        });
        const data = await resp.json();
        if (data.success) {
            state.submitTaskId = data.task_id;
            pollStatus();
        } else {
            alert('提交失败: ' + (data.message || '未知错误'));
            document.getElementById('submitBtn').disabled = false;
        }
    } catch (e) {
        alert('网络请求失败');
        document.getElementById('submitBtn').disabled = false;
    }
}

async function pollStatus() {
    try {
        const resp = await fetch(`/api/homework-test/submit/status/${state.submitTaskId}`);
        const data = await resp.json();

        if (data.success) {
            const pct = data.total > 0 ? (data.completed / data.total * 100) : 0;
            document.getElementById('progressBar').style.width = `${pct}%`;
            document.getElementById('progressText').textContent =
                `${data.completed}/${data.total} (成功: ${data.success_count ?? data.success ?? 0}, 失败: ${data.failed_count ?? data.failed ?? 0})`;

            const logEl = document.getElementById('logContainer');
            logEl.innerHTML = (data.logs || []).map(log => {
                let cls = '';
                if (log.includes('✓')) cls = 'success';
                if (log.includes('✗')) cls = 'error';
                if (log.includes('---')) cls = 'info';
                return `<div class="log-line ${cls}">${log}</div>`;
            }).join('');
            logEl.scrollTop = logEl.scrollHeight;

            if (data.status === 'running') {
                setTimeout(pollStatus, 1000);
            } else {
                document.getElementById('submitBtn').disabled = false;
                if (data.status === 'completed') alert('提交完成！');
            }
        }
    } catch (e) {
        console.error('轮询失败:', e);
        setTimeout(pollStatus, 2000);
    }
}
