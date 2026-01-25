// 数据分析页面 JavaScript

let currentTaskId = null;
let pollingInterval = null;

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    loadTaskList();
    setupFileUpload();
});

// 返回导航
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// 加载任务列表
async function loadTaskList() {
    try {
        const response = await fetch('/api/analysis/tasks');
        const tasks = await response.json();
        
        const taskList = document.getElementById('taskList');
        if (tasks.length === 0) {
            taskList.innerHTML = '<div class="empty-hint">暂无任务</div>';
            return;
        }
        
        taskList.innerHTML = tasks.map(task => `
            <div class="task-item ${task.task_id === currentTaskId ? 'active' : ''}" 
                 onclick="loadTask('${task.task_id}')">
                <div class="task-item-name">${escapeHtml(task.name)}</div>
                <div class="task-item-meta">
                    <span>${task.file_count} 个文件</span>
                    <span class="task-item-status ${task.status}">${getStatusText(task.status)}</span>
                </div>
            </div>
        `).join('');
    } catch (error) {
        console.error('加载任务列表失败:', error);
    }
}

// 获取状态文本
function getStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'running': '进行中',
        'completed': '已完成',
        'failed': '失败'
    };
    return statusMap[status] || status;
}

// 显示创建任务弹窗
function showCreateTask() {
    document.getElementById('createTaskModal').classList.add('show');
    document.getElementById('newTaskName').focus();
}

// 隐藏创建任务弹窗
function hideCreateTask() {
    document.getElementById('createTaskModal').classList.remove('show');
    document.getElementById('newTaskName').value = '';
    document.getElementById('newTaskDesc').value = '';
}

// 创建任务
async function createTask() {
    const name = document.getElementById('newTaskName').value.trim();
    const description = document.getElementById('newTaskDesc').value.trim();
    
    if (!name) {
        alert('请输入任务名称');
        return;
    }
    
    try {
        const response = await fetch('/api/analysis/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, description })
        });
        
        const result = await response.json();
        hideCreateTask();
        loadTaskList();
        loadTask(result.task_id);
    } catch (error) {
        console.error('创建任务失败:', error);
        alert('创建任务失败');
    }
}

// 加载任务详情
async function loadTask(taskId) {
    currentTaskId = taskId;
    
    try {
        const response = await fetch(`/api/analysis/tasks/${taskId}`);
        const task = await response.json();
        
        if (task.error) {
            alert(task.error);
            return;
        }
        
        // 显示任务详情页
        document.getElementById('welcomePage').style.display = 'none';
        document.getElementById('taskDetail').style.display = 'block';
        
        // 更新任务信息
        document.getElementById('taskName').textContent = task.name;
        document.getElementById('taskStatus').textContent = getStatusText(task.status);
        document.getElementById('taskStatus').className = 'task-status ' + task.status;
        
        // 更新工作流步骤
        updateWorkflowSteps(task.workflow_state);
        
        // 更新文件列表
        updateFileList(task.files);
        
        // 更新结果展示
        if (task.status === 'completed' || task.results.template || task.results.report) {
            document.getElementById('resultsSection').style.display = 'block';
            updateResults(task);
        } else {
            document.getElementById('resultsSection').style.display = 'none';
        }
        
        // 更新任务列表高亮
        loadTaskList();
        
    } catch (error) {
        console.error('加载任务失败:', error);
    }
}

// 更新工作流步骤显示
function updateWorkflowSteps(workflowState) {
    const steps = workflowState.steps;
    const currentStep = workflowState.current_step;
    
    steps.forEach((step, index) => {
        const stepEl = document.querySelector(`.step[data-step="${step.id}"]`);
        if (!stepEl) return;
        
        stepEl.classList.remove('active', 'completed', 'running', 'pending');
        
        if (step.status === 'completed') {
            stepEl.classList.add('completed');
        } else if (step.status === 'running' || step.id === currentStep) {
            stepEl.classList.add('running');
        } else {
            stepEl.classList.add('pending');
        }
        
        // 更新连接线
        if (index > 0) {
            const connector = stepEl.previousElementSibling;
            if (connector && connector.classList.contains('step-connector')) {
                connector.classList.toggle('completed', step.status === 'completed');
            }
        }
    });
}

// 获取文件图标
function getFileIcon(filename) {
    if (filename.toLowerCase().endsWith('.xlsx')) {
        return '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#1e7e34" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>';
    } else if (filename.toLowerCase().endsWith('.docx')) {
        return '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#1565c0" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>';
    }
    return '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="#86868b" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 7V3.5L18.5 9H13z"/></svg>';
}

// 更新文件列表
function updateFileList(files) {
    const fileList = document.getElementById('fileList');
    const startBtn = document.getElementById('startWorkflowBtn');
    
    if (!files || files.length === 0) {
        fileList.innerHTML = '';
        startBtn.disabled = true;
        return;
    }
    
    fileList.innerHTML = files.map(file => `
        <div class="file-item" data-file-id="${file.file_id}">
            <div class="file-info">
                <span class="file-icon">${getFileIcon(file.filename)}</span>
                <div>
                    <div class="file-name">${escapeHtml(file.filename)}</div>
                    <div class="file-size">${formatFileSize(file.size)}</div>
                </div>
            </div>
            <span class="file-status ${file.status}">${getFileStatusText(file.status)}</span>
        </div>
    `).join('');
    
    startBtn.disabled = files.length === 0;
}

// 获取文件状态文本
function getFileStatusText(status) {
    const statusMap = {
        'uploaded': '已上传',
        'parsing': '解析中',
        'parsed': '已解析',
        'analyzing': '分析中',
        'analyzed': '已分析',
        'parse_failed': '解析失败',
        'analyze_failed': '分析失败'
    };
    return statusMap[status] || status;
}

// 格式化文件大小
function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(1) + ' MB';
}

// 设置文件上传
function setupFileUpload() {
    const uploadZone = document.getElementById('uploadZone');
    const fileInput = document.getElementById('fileInput');
    
    // 拖拽上传
    uploadZone.addEventListener('dragover', (e) => {
        e.preventDefault();
        uploadZone.classList.add('dragover');
    });
    
    uploadZone.addEventListener('dragleave', () => {
        uploadZone.classList.remove('dragover');
    });
    
    uploadZone.addEventListener('drop', (e) => {
        e.preventDefault();
        uploadZone.classList.remove('dragover');
        const files = e.dataTransfer.files;
        uploadFiles(files);
    });
    
    // 点击上传
    fileInput.addEventListener('change', (e) => {
        uploadFiles(e.target.files);
        fileInput.value = '';
    });
}

// 上传文件
async function uploadFiles(files) {
    if (!currentTaskId) {
        alert('请先创建或选择任务');
        return;
    }
    
    const formData = new FormData();
    for (const file of files) {
        formData.append('files', file);
    }
    
    try {
        const response = await fetch(`/api/analysis/tasks/${currentTaskId}/files`, {
            method: 'POST',
            body: formData
        });
        
        const result = await response.json();
        
        if (result.error) {
            alert(result.error);
            return;
        }
        
        if (result.errors && result.errors.length > 0) {
            const errorMsg = result.errors.map(e => `${e.filename}: ${e.error}`).join('\n');
            alert('部分文件上传失败:\n' + errorMsg);
        }
        
        // 刷新任务
        loadTask(currentTaskId);
        
    } catch (error) {
        console.error('上传失败:', error);
        alert('上传失败');
    }
}

// 启动工作流
async function startWorkflow() {
    if (!currentTaskId) return;
    
    try {
        // 启动工作流
        const response = await fetch(`/api/analysis/tasks/${currentTaskId}/workflow/start`, {
            method: 'POST'
        });
        
        const result = await response.json();
        if (result.error) {
            alert(result.error);
            return;
        }
        
        // 刷新任务状态
        loadTask(currentTaskId);
        
        // 执行第一步
        executeStep('parse');
        
    } catch (error) {
        console.error('启动工作流失败:', error);
        alert('启动工作流失败');
    }
}

// 执行工作流步骤
async function executeStep(stepId) {
    if (!currentTaskId) return;
    
    const resultsSection = document.getElementById('resultsSection');
    resultsSection.style.display = 'block';
    
    try {
        const response = await fetch(`/api/analysis/tasks/${currentTaskId}/workflow/step/${stepId}`, {
            method: 'POST'
        });
        
        if (stepId === 'parse' || stepId === 'analyze') {
            // 流式处理
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;
                
                const text = decoder.decode(value);
                const lines = text.split('\n');
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);
                        if (data === '[DONE]') {
                            // 刷新任务
                            loadTask(currentTaskId);
                            
                            // 执行下一步
                            if (stepId === 'parse') {
                                executeStep('analyze');
                            } else if (stepId === 'analyze') {
                                executeStep('template');
                            }
                            return;
                        }
                        
                        try {
                            const result = JSON.parse(data);
                            
                            if (result.file_id) {
                                // 更新文件状态
                                updateFileStatus(result.file_id, result.status);
                                updateFileResult(result);
                            }
                            
                            if (result.step_completed) {
                                loadTask(currentTaskId);
                            }
                        } catch (e) {}
                    }
                }
            }
        } else {
            // 非流式处理
            const result = await response.json();
            
            if (result.error) {
                alert(result.error);
                return;
            }
            
            // 刷新任务
            loadTask(currentTaskId);
            
            // 执行下一步
            if (stepId === 'template') {
                executeStep('report');
            }
        }
        
    } catch (error) {
        console.error('执行步骤失败:', error);
        alert('执行步骤失败: ' + error.message);
    }
}

// 更新文件状态
function updateFileStatus(fileId, status) {
    const fileItem = document.querySelector(`.file-item[data-file-id="${fileId}"]`);
    if (fileItem) {
        const statusEl = fileItem.querySelector('.file-status');
        statusEl.className = 'file-status ' + status;
        statusEl.textContent = getFileStatusText(status);
    }
}

// 更新文件结果
function updateFileResult(result) {
    const fileResults = document.getElementById('fileResults');
    let card = fileResults.querySelector(`[data-file-id="${result.file_id}"]`);
    
    if (!card) {
        card = document.createElement('div');
        card.className = 'file-result-card';
        card.dataset.fileId = result.file_id;
        card.innerHTML = `
            <div class="file-result-header" onclick="toggleFileResult(this)">
                <span class="file-result-title">${escapeHtml(result.filename)}</span>
                <span class="file-result-toggle">展开</span>
            </div>
            <div class="file-result-body"></div>
        `;
        fileResults.appendChild(card);
    }
    
    const body = card.querySelector('.file-result-body');
    
    if (result.result) {
        if (result.result.llm_analysis) {
            // 解析结果
            body.innerHTML = `
                <div class="result-section">
                    <div class="result-section-title">数据结构分析</div>
                    <div class="result-section-content">${formatAnalysis(result.result.llm_analysis)}</div>
                </div>
            `;
        }
        
        if (result.result.analysis) {
            // 内容分析结果
            body.innerHTML += `
                <div class="result-section">
                    <div class="result-section-title">内容分析</div>
                    <div class="result-section-content">${formatAnalysis(result.result.analysis)}</div>
                </div>
            `;
        }
    }
}

// 格式化分析结果
function formatAnalysis(analysis) {
    if (typeof analysis === 'string') return escapeHtml(analysis);
    if (analysis.raw) return escapeHtml(analysis.raw);
    
    let html = '';
    
    if (analysis.summary) {
        html += `<p><strong>概述:</strong> ${escapeHtml(analysis.summary)}</p>`;
    }
    
    if (analysis.key_findings) {
        html += `<p><strong>关键发现:</strong></p><ul>`;
        analysis.key_findings.forEach(f => {
            html += `<li>${escapeHtml(f)}</li>`;
        });
        html += '</ul>';
    }
    
    if (analysis.insights) {
        html += `<p><strong>洞察:</strong> ${escapeHtml(analysis.insights)}</p>`;
    }
    
    if (analysis.recommendations) {
        html += `<p><strong>建议:</strong></p><ul>`;
        analysis.recommendations.forEach(r => {
            html += `<li>${escapeHtml(r)}</li>`;
        });
        html += '</ul>';
    }
    
    return html || JSON.stringify(analysis, null, 2);
}

// 切换文件结果展开/折叠
function toggleFileResult(header) {
    const body = header.nextElementSibling;
    const toggle = header.querySelector('.file-result-toggle');
    
    body.classList.toggle('expanded');
    toggle.textContent = body.classList.contains('expanded') ? '收起' : '展开';
}

// 更新结果展示
function updateResults(task) {
    // 更新文件结果
    const fileResults = document.getElementById('fileResults');
    fileResults.innerHTML = '';
    
    task.files.forEach(file => {
        if (file.parse_result || file.analysis_result) {
            const card = document.createElement('div');
            card.className = 'file-result-card';
            card.dataset.fileId = file.file_id;
            
            let bodyContent = '';
            
            if (file.parse_result && file.parse_result.llm_analysis) {
                bodyContent += `
                    <div class="result-section">
                        <div class="result-section-title">数据结构分析</div>
                        <div class="result-section-content">${formatAnalysis(file.parse_result.llm_analysis)}</div>
                    </div>
                `;
            }
            
            if (file.analysis_result && file.analysis_result.analysis) {
                bodyContent += `
                    <div class="result-section">
                        <div class="result-section-title">内容分析</div>
                        <div class="result-section-content">${formatAnalysis(file.analysis_result.analysis)}</div>
                    </div>
                `;
            }
            
            card.innerHTML = `
                <div class="file-result-header" onclick="toggleFileResult(this)">
                    <span class="file-result-title">${escapeHtml(file.filename)}</span>
                    <span class="file-result-toggle">展开</span>
                </div>
                <div class="file-result-body">${bodyContent}</div>
            `;
            
            fileResults.appendChild(card);
        }
    });
    
    // 更新模板
    if (task.results.template) {
        const templateContent = document.getElementById('templateContent');
        const template = task.results.template;
        
        if (template.sections) {
            templateContent.innerHTML = template.sections.map(section => `
                <div class="template-section">
                    <div class="template-section-title">${escapeHtml(section.title)}</div>
                    <div class="template-section-desc">${escapeHtml(section.description || '')}</div>
                </div>
            `).join('');
        } else {
            templateContent.innerHTML = `<pre>${JSON.stringify(template, null, 2)}</pre>`;
        }
    }
    
    // 更新报告
    if (task.results.report) {
        const reportContent = document.getElementById('reportContent');
        const content = task.results.report.content || '';
        
        if (typeof marked !== 'undefined') {
            reportContent.innerHTML = marked.parse(content);
        } else {
            reportContent.innerHTML = `<pre>${escapeHtml(content)}</pre>`;
        }
    }
}

// 切换标签页
function switchTab(tabId) {
    // 更新按钮状态
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tabId);
    });
    
    // 更新内容显示
    document.querySelectorAll('.tab-content').forEach(content => {
        content.style.display = 'none';
    });
    document.getElementById(tabId + 'Tab').style.display = 'block';
}

// 下载报告
function downloadReport() {
    if (!currentTaskId) return;
    window.location.href = `/api/analysis/tasks/${currentTaskId}/download`;
}

// HTML转义
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}


// ==================== 优化日志功能 ====================

// 显示优化日志弹窗
function showOptimizationLogs() {
    document.getElementById('optimizationLogsModal').classList.add('show');
    loadOptimizationLogs();
}

// 隐藏优化日志弹窗
function hideOptimizationLogs() {
    document.getElementById('optimizationLogsModal').classList.remove('show');
}

// 加载优化日志
async function loadOptimizationLogs() {
    const logsList = document.getElementById('optimizationLogsList');
    
    try {
        const response = await fetch('/api/optimization/suggestions?limit=20');
        const result = await response.json();
        
        if (!result.success || !result.suggestions || result.suggestions.length === 0) {
            logsList.innerHTML = `
                <div class="empty-logs">
                    <svg viewBox="0 0 24 24" width="48" height="48"><path fill="currentColor" d="M9 21c0 .55.45 1 1 1h4c.55 0 1-.45 1-1v-1H9v1zm3-19C8.14 2 5 5.14 5 9c0 2.38 1.19 4.47 3 5.74V17c0 .55.45 1 1 1h6c.55 0 1-.45 1-1v-2.26c1.81-1.27 3-3.36 3-5.74 0-3.86-3.14-7-7-7z"/></svg>
                    <p>暂无优化日志</p>
                </div>
            `;
            return;
        }
        
        logsList.innerHTML = result.suggestions.map(log => `
            <div class="optimization-log-item">
                <div class="log-header">
                    <span class="log-title">${escapeHtml(log.title)}</span>
                    <span class="log-status ${log.status}">${getLogStatusText(log.status)}</span>
                </div>
                <div class="log-content">${escapeHtml(log.problem_description || log.suggestion_content || '')}</div>
                <div class="log-time">${formatLogTime(log.created_at)}</div>
            </div>
        `).join('');
        
    } catch (error) {
        console.error('加载优化日志失败:', error);
        logsList.innerHTML = `
            <div class="empty-logs">
                <svg viewBox="0 0 24 24" width="48" height="48"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                <p>加载失败，请稍后重试</p>
            </div>
        `;
    }
}

// 获取日志状态文本
function getLogStatusText(status) {
    const statusMap = {
        'pending': '待处理',
        'applied': '已应用',
        'rejected': '已拒绝',
        'in_progress': '处理中'
    };
    return statusMap[status] || status;
}

// 格式化日志时间
function formatLogTime(timeStr) {
    if (!timeStr) return '';
    const date = new Date(timeStr);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    if (diff < 604800000) return Math.floor(diff / 86400000) + '天前';
    
    return date.toLocaleDateString('zh-CN');
}

// ==================== 设置功能 ====================

// 设置状态
let settingsState = {
    analysisModel: 'deepseek-v3.2',
    autoSummary: true,
    includeRawData: false
};

// 显示设置弹窗
function showSettingsModal() {
    document.getElementById('settingsModal').classList.add('show');
    loadSettings();
}

// 隐藏设置弹窗
function hideSettingsModal() {
    document.getElementById('settingsModal').classList.remove('show');
}

// 加载设置
function loadSettings() {
    // 从 localStorage 加载设置
    const saved = localStorage.getItem('dataAnalysisSettings');
    if (saved) {
        try {
            settingsState = JSON.parse(saved);
        } catch (e) {}
    }
    
    // 更新 UI
    document.getElementById('settingsAnalysisModel').value = settingsState.analysisModel || 'deepseek-v3.2';
    
    const autoSummaryToggle = document.getElementById('settingsAutoSummary');
    autoSummaryToggle.classList.toggle('active', settingsState.autoSummary !== false);
    
    const includeRawDataToggle = document.getElementById('settingsIncludeRawData');
    includeRawDataToggle.classList.toggle('active', settingsState.includeRawData === true);
}

// 切换设置开关
function toggleSetting(key) {
    const toggle = document.getElementById('settings' + key.charAt(0).toUpperCase() + key.slice(1));
    toggle.classList.toggle('active');
    settingsState[key] = toggle.classList.contains('active');
}

// 保存设置
function saveSettings() {
    settingsState.analysisModel = document.getElementById('settingsAnalysisModel').value;
    
    // 保存到 localStorage
    localStorage.setItem('dataAnalysisSettings', JSON.stringify(settingsState));
    
    hideSettingsModal();
    
    // 显示保存成功提示
    showToast('设置已保存');
}

// 显示提示
function showToast(message) {
    // 创建 toast 元素
    let toast = document.querySelector('.toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.className = 'toast';
        toast.style.cssText = `
            position: fixed;
            bottom: 24px;
            left: 50%;
            transform: translateX(-50%);
            background: #1d1d1f;
            color: #fff;
            padding: 12px 24px;
            border-radius: 8px;
            font-size: 14px;
            z-index: 10000;
            opacity: 0;
            transition: opacity 0.3s;
        `;
        document.body.appendChild(toast);
    }
    
    toast.textContent = message;
    toast.style.opacity = '1';
    
    setTimeout(() => {
        toast.style.opacity = '0';
    }, 2000);
}
