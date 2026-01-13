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
        return '📊';
    } else if (filename.toLowerCase().endsWith('.docx')) {
        return '📄';
    }
    return '📁';
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
