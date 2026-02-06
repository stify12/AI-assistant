/**
 * 模块化流程执行器
 * 支持原子操作组合、流程编辑、保存
 */

// ==================== 状态 ====================

const workflowState = {
    publishRunning: false,
    submitRunning: false,
    currentStep: null,
    logs: [],
    workflows: {},      // 流程配置缓存
    atomActions: {},    // 原子操作定义
    editingWorkflow: null  // 当前编辑的流程
};

// ==================== 初始化 ====================

document.addEventListener('DOMContentLoaded', async () => {
    // 加载流程配置
    await loadWorkflowConfig();
    
    // 默认展开发布作业流程
    const publishCard = document.getElementById('publishWorkflow');
    if (publishCard) {
        publishCard.classList.add('expanded');
    }
    
    // 监听学生数据变化，同步到提交作业流程
    syncStudentInfo();
});

// ==================== 流程配置加载 ====================

async function loadWorkflowConfig() {
    try {
        const res = await fetch('/api/rfid-simulator/workflows');
        const result = await res.json();
        if (result.success) {
            workflowState.workflows = result.data.workflows || {};
            workflowState.atomActions = result.data.atom_actions || {};
            renderWorkflowSteps('publish_homework');
            renderWorkflowSteps('submit_homework');
        }
    } catch (e) {
        console.error('加载流程配置失败:', e);
    }
}

// ==================== 流程步骤渲染 ====================

function renderWorkflowSteps(workflowId) {
    const workflow = workflowState.workflows[workflowId];
    if (!workflow) return;
    
    // 根据 workflowId 选择容器
    const containerId = workflowId === 'publish_homework' ? 'publishStepsList' : 'submitStepsList';
    const container = document.getElementById(containerId);
    if (!container) return;
    
    container.innerHTML = workflow.steps.map((step, index) => {
        const actionInfo = workflowState.atomActions[step.action] || {};
        const detail = formatStepDetail(step);
        
        // 特殊处理循环步骤
        if (step.action === 'loop') {
            const loopSteps = step.steps || [];
            return `
                <div class="workflow-step-item loop-step" data-step="${index}" data-workflow="${workflowId}">
                    <span class="step-num">${index + 1}</span>
                    <span class="step-name">${step.desc || '循环'}</span>
                    <span class="step-detail">目标: ${step.target}</span>
                    <button class="step-edit-btn" onclick="editStep('${workflowId}', ${index})" title="编辑">E</button>
                </div>
                <div class="loop-substeps">
                    ${loopSteps.map((subStep, subIndex) => `
                        <div class="workflow-step-item substep" data-step="${index}_${subIndex}" data-workflow="${workflowId}">
                            <span class="step-num">${index + 1}.${subIndex + 1}</span>
                            <span class="step-name">${subStep.desc || subStep.action}</span>
                            <span class="step-detail">${formatStepDetail(subStep)}</span>
                        </div>
                    `).join('')}
                </div>
            `;
        }
        
        // 特殊处理 RFID 步骤
        if (step.action === 'rfid') {
            const targetLabel = step.target === 'rep' ? '课代表' : step.target === 'current' ? '当前学生' : step.target;
            return `
                <div class="workflow-step-item rfid-step" data-step="${index}" data-workflow="${workflowId}">
                    <span class="step-num">${index + 1}</span>
                    <span class="step-name">${step.desc || '刷卡'}</span>
                    <span class="step-detail">${targetLabel}</span>
                    <span class="step-status" id="step_${workflowId}_${index}"></span>
                    <button class="step-edit-btn" onclick="editStep('${workflowId}', ${index})" title="编辑">E</button>
                </div>
            `;
        }
        
        return `
            <div class="workflow-step-item" data-step="${index}" data-workflow="${workflowId}">
                <span class="step-num">${index + 1}</span>
                <span class="step-name">${step.desc || actionInfo.name || step.action}</span>
                <span class="step-detail">${detail}</span>
                <span class="step-status" id="step_${workflowId}_${index}"></span>
                <button class="step-edit-btn" onclick="editStep('${workflowId}', ${index})" title="编辑">E</button>
            </div>
        `;
    }).join('');
}

function formatStepDetail(step) {
    const parts = [];
    if (step.x !== undefined && step.y !== undefined) {
        parts.push(`(${step.x}, ${step.y})`);
    }
    if (step.text) {
        const text = step.text.startsWith('${') ? step.text : step.text.substring(0, 15);
        parts.push(text);
    }
    if (step.wait) {
        parts.push(`${step.wait}s`);
    }
    return parts.join(' ');
}

// ==================== 流程卡片切换 ====================

function toggleWorkflowCard(type) {
    const card = document.getElementById(type + 'Workflow');
    if (!card) return;
    card.classList.toggle('expanded');
}

// ==================== 发布作业流程 ====================

async function runPublishWorkflow() {
    if (workflowState.publishRunning) return;
    
    // 检查客户端连接
    if (!await checkClientConnection()) {
        addWorkflowLog('error', '请先连接 ADB 客户端');
        return;
    }
    
    workflowState.publishRunning = true;
    updateWorkflowStatus('publish', 'running', '执行中');
    
    const username = document.getElementById('publishUsername')?.value || 'shuxue';
    const password = document.getElementById('publishPassword')?.value || '123456zp.';
    const homeworkName = document.getElementById('publishHomeworkName')?.value || '';
    
    // 从配置获取流程步骤
    const workflow = workflowState.workflows['publish_homework'];
    if (!workflow) {
        addWorkflowLog('error', '未找到发布作业流程配置');
        workflowState.publishRunning = false;
        return;
    }
    
    // 替换变量
    const params = { username, password, homework_name: homeworkName || `auto_${Date.now()}` };
    const steps = JSON.parse(JSON.stringify(workflow.steps)); // 深拷贝
    
    steps.forEach(step => {
        if (step.text && step.text.startsWith('${')) {
            const varName = step.text.slice(2, -1);
            step.text = params[varName] || '';
        }
    });
    
    try {
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            setStepActive('publish_homework', i);
            
            const detail = formatStepDetail(step);
            addWorkflowLog('info', `执行: ${step.desc || step.action} ${detail}`);
            
            const success = await executeAtomStep(step);
            
            if (success) {
                setStepDone('publish_homework', i);
                addWorkflowLog('success', `完成: ${step.desc || step.action}`);
            } else {
                setStepError('publish_homework', i);
                addWorkflowLog('error', `失败: ${step.desc || step.action}`);
                throw new Error(`步骤失败: ${step.desc}`);
            }
            
            // 等待
            if (step.wait) {
                addWorkflowLog('info', `等待 ${step.wait}s...`);
                await sleep(step.wait * 1000);
            }
        }
        
        updateWorkflowStatus('publish', 'success', '已完成');
        addWorkflowLog('success', '发布作业流程完成');
    } catch (e) {
        updateWorkflowStatus('publish', 'error', '执行失败');
        addWorkflowLog('error', `流程异常: ${e.message}`);
    } finally {
        workflowState.publishRunning = false;
    }
}

// ==================== 原子操作执行 ====================

async function executeAtomStep(step) {
    try {
        const response = await fetch('/api/rfid-simulator/workflow/step', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(step)
        });
        const result = await response.json();
        return result.success;
    } catch (e) {
        console.error('执行步骤失败:', e);
        return false;
    }
}

// ==================== 步骤编辑 ====================

function editStep(workflowId, stepIndex) {
    const workflow = workflowState.workflows[workflowId];
    if (!workflow) return;
    
    const step = workflow.steps[stepIndex];
    workflowState.editingWorkflow = { workflowId, stepIndex };
    
    // 显示编辑弹窗
    showStepEditor(step);
}

function showStepEditor(step) {
    const modal = document.getElementById('stepEditorModal');
    if (!modal) {
        createStepEditorModal();
    }
    
    // 填充表单
    document.getElementById('stepAction').value = step.action;
    document.getElementById('stepDesc').value = step.desc || '';
    document.getElementById('stepWait').value = step.wait || 1;
    
    // 根据操作类型显示不同参数
    updateStepParamsUI(step);
    
    document.getElementById('stepEditorModal').style.display = 'flex';
}

function createStepEditorModal() {
    const modal = document.createElement('div');
    modal.id = 'stepEditorModal';
    modal.className = 'modal-overlay';
    modal.innerHTML = `
        <div class="modal-content small-modal">
            <div class="modal-header">
                <h3 class="modal-title">编辑步骤</h3>
                <button class="btn-close" onclick="closeStepEditor()">X</button>
            </div>
            <div class="modal-body">
                <div class="form-group">
                    <label>操作类型</label>
                    <select id="stepAction" onchange="onStepActionChange()">
                        <option value="tap">点击</option>
                        <option value="long_press">长按</option>
                        <option value="swipe">滑动</option>
                        <option value="input">输入文本</option>
                        <option value="clear">清除输入</option>
                        <option value="key">按键</option>
                        <option value="wait">等待</option>
                        <option value="launch">启动应用</option>
                        <option value="stop_app">停止应用</option>
                        <option value="screenshot">截图</option>
                        <option value="rfid">刷RFID卡</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>步骤描述</label>
                    <input type="text" id="stepDesc" placeholder="如: 点击登录按钮">
                </div>
                <div id="stepParamsContainer"></div>
                <div class="form-group">
                    <label>等待时间(秒)</label>
                    <input type="number" id="stepWait" value="1" step="0.5" min="0">
                </div>
            </div>
            <div class="modal-footer">
                <button class="btn-secondary" onclick="deleteCurrentStep()">删除</button>
                <button class="btn-secondary" onclick="closeStepEditor()">取消</button>
                <button class="btn-primary" onclick="saveStepEdit()" style="width:auto;margin-top:0;">保存</button>
            </div>
        </div>
    `;
    document.body.appendChild(modal);
}

function updateStepParamsUI(step) {
    const container = document.getElementById('stepParamsContainer');
    const action = step?.action || document.getElementById('stepAction').value;
    
    let html = '';
    switch (action) {
        case 'tap':
        case 'long_press':
            html = `
                <div class="form-row">
                    <div class="form-group"><label>X</label><input type="number" id="stepX" value="${step?.x || 0}"></div>
                    <div class="form-group"><label>Y</label><input type="number" id="stepY" value="${step?.y || 0}"></div>
                </div>
            `;
            if (action === 'long_press') {
                html += `<div class="form-group"><label>时长(ms)</label><input type="number" id="stepDuration" value="${step?.duration || 1000}"></div>`;
            }
            break;
        case 'swipe':
            html = `
                <div class="form-row">
                    <div class="form-group"><label>起点X</label><input type="number" id="stepX1" value="${step?.x1 || 0}"></div>
                    <div class="form-group"><label>起点Y</label><input type="number" id="stepY1" value="${step?.y1 || 0}"></div>
                </div>
                <div class="form-row">
                    <div class="form-group"><label>终点X</label><input type="number" id="stepX2" value="${step?.x2 || 0}"></div>
                    <div class="form-group"><label>终点Y</label><input type="number" id="stepY2" value="${step?.y2 || 0}"></div>
                </div>
                <div class="form-group"><label>时长(ms)</label><input type="number" id="stepDuration" value="${step?.duration || 300}"></div>
            `;
            break;
        case 'input':
            html = `<div class="form-group"><label>文本内容</label><input type="text" id="stepText" value="${step?.text || ''}" placeholder="支持变量 \${username}"></div>`;
            break;
        case 'key':
            html = `
                <div class="form-group">
                    <label>按键</label>
                    <select id="stepKey">
                        <option value="enter" ${step?.key === 'enter' ? 'selected' : ''}>回车 Enter</option>
                        <option value="back" ${step?.key === 'back' ? 'selected' : ''}>返回 Back</option>
                        <option value="home" ${step?.key === 'home' ? 'selected' : ''}>主页 Home</option>
                        <option value="tab" ${step?.key === 'tab' ? 'selected' : ''}>Tab</option>
                        <option value="del" ${step?.key === 'del' ? 'selected' : ''}>删除 Delete</option>
                    </select>
                </div>
            `;
            break;
        case 'launch':
        case 'stop_app':
            html = `<div class="form-group"><label>包名</label><input type="text" id="stepPackage" value="${step?.package || 'com.zpzn.terminal'}"></div>`;
            break;
        case 'wait':
            html = `<div class="form-group"><label>等待秒数</label><input type="number" id="stepSeconds" value="${step?.seconds || 1}" step="0.5"></div>`;
            break;
        case 'rfid':
            html = `
                <div class="form-group">
                    <label>目标</label>
                    <select id="stepTarget">
                        <option value="rep" ${step?.target === 'rep' ? 'selected' : ''}>课代表</option>
                        <option value="current" ${step?.target === 'current' ? 'selected' : ''}>当前学生(循环中)</option>
                    </select>
                </div>
            `;
            break;
    }
    container.innerHTML = html;
}

function onStepActionChange() {
    updateStepParamsUI(null);
}

function closeStepEditor() {
    const modal = document.getElementById('stepEditorModal');
    if (modal) modal.style.display = 'none';
    workflowState.editingWorkflow = null;
}

async function saveStepEdit() {
    if (!workflowState.editingWorkflow) return;
    
    const { workflowId, stepIndex, isNew } = workflowState.editingWorkflow;
    const workflow = workflowState.workflows[workflowId];
    if (!workflow) return;
    
    const action = document.getElementById('stepAction').value;
    const step = {
        action,
        desc: document.getElementById('stepDesc').value,
        wait: parseFloat(document.getElementById('stepWait').value) || 1
    };
    
    // 根据操作类型获取参数
    switch (action) {
        case 'tap':
        case 'long_press':
            step.x = parseInt(document.getElementById('stepX').value) || 0;
            step.y = parseInt(document.getElementById('stepY').value) || 0;
            if (action === 'long_press') {
                step.duration = parseInt(document.getElementById('stepDuration').value) || 1000;
            }
            break;
        case 'swipe':
            step.x1 = parseInt(document.getElementById('stepX1').value) || 0;
            step.y1 = parseInt(document.getElementById('stepY1').value) || 0;
            step.x2 = parseInt(document.getElementById('stepX2').value) || 0;
            step.y2 = parseInt(document.getElementById('stepY2').value) || 0;
            step.duration = parseInt(document.getElementById('stepDuration').value) || 300;
            break;
        case 'input':
            step.text = document.getElementById('stepText').value;
            break;
        case 'key':
            step.key = document.getElementById('stepKey').value;
            break;
        case 'launch':
        case 'stop_app':
            step.package = document.getElementById('stepPackage').value;
            break;
        case 'wait':
            step.seconds = parseFloat(document.getElementById('stepSeconds').value) || 1;
            break;
        case 'rfid':
            step.target = document.getElementById('stepTarget').value;
            break;
    }
    
    // 新增或更新
    if (isNew) {
        workflow.steps.push(step);
    } else {
        workflow.steps[stepIndex] = step;
    }
    
    // 保存到服务器
    try {
        const res = await fetch(`/api/rfid-simulator/workflows/${workflowId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ steps: workflow.steps })
        });
        const result = await res.json();
        if (result.success) {
            addWorkflowLog('success', '步骤已保存');
            renderWorkflowSteps(workflowId);
        } else {
            addWorkflowLog('error', '保存失败: ' + result.error);
        }
    } catch (e) {
        addWorkflowLog('error', '保存失败: ' + e.message);
    }
    
    closeStepEditor();
}

async function deleteCurrentStep() {
    if (!workflowState.editingWorkflow) return;
    if (!confirm('确定删除此步骤？')) return;
    
    const { workflowId, stepIndex } = workflowState.editingWorkflow;
    const workflow = workflowState.workflows[workflowId];
    if (!workflow) return;
    
    workflow.steps.splice(stepIndex, 1);
    
    try {
        await fetch(`/api/rfid-simulator/workflows/${workflowId}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ steps: workflow.steps })
        });
        addWorkflowLog('success', '步骤已删除');
        renderWorkflowSteps(workflowId);
    } catch (e) {
        addWorkflowLog('error', '删除失败');
    }
    
    closeStepEditor();
}

// ==================== 添加新步骤 ====================

function addNewStep(workflowId) {
    workflowState.editingWorkflow = { 
        workflowId, 
        stepIndex: workflowState.workflows[workflowId]?.steps?.length || 0,
        isNew: true
    };
    showStepEditor({ action: 'tap', x: 0, y: 0, wait: 1, desc: '' });
}

// ==================== 提交作业流程 ====================

async function runSubmitWorkflow() {
    if (workflowState.submitRunning) return;
    
    if (!await checkClientConnection()) {
        addWorkflowLog('error', '请先连接 ADB 客户端');
        return;
    }
    
    // 从 rfid-simulator.js 获取学生数据
    if (!state || !state.students || state.students.length === 0) {
        addWorkflowLog('error', '请先从左侧选择班级');
        return;
    }
    
    workflowState.submitRunning = true;
    updateWorkflowStatus('submit', 'running', '执行中');
    
    const workflow = workflowState.workflows['submit_homework'];
    if (!workflow) {
        addWorkflowLog('error', '未找到提交作业流程配置');
        workflowState.submitRunning = false;
        return;
    }
    
    // 获取参数
    const photoInterval = parseFloat(document.getElementById('submitPhotoInterval')?.value) || 2;
    
    // 获取课代表和普通学生
    const rep = state.allStudents.find(s => s.is_representative);
    const normalStudents = state.students.filter(s => !s.is_representative);
    
    if (!rep) {
        addWorkflowLog('error', '未找到课代表');
        workflowState.submitRunning = false;
        updateWorkflowStatus('submit', 'error', '无课代表');
        return;
    }
    
    addWorkflowLog('info', `提交作业流程开始，课代表: ${rep.name}，学生: ${normalStudents.length} 人`);
    
    try {
        const steps = workflow.steps;
        
        for (let i = 0; i < steps.length; i++) {
            const step = steps[i];
            setStepActive('submit_homework', i);
            
            // 处理不同类型的步骤
            if (step.action === 'rfid') {
                // RFID 刷卡
                if (step.target === 'rep') {
                    addWorkflowLog('info', `刷课代表卡: ${rep.name} (${rep.rfid_no})`);
                    const success = await sendRfidCard(rep.rfid_no);
                    if (!success) throw new Error('刷课代表卡失败');
                    setStepDone('submit_homework', i);
                }
            } else if (step.action === 'loop') {
                // 循环处理学生
                addWorkflowLog('info', `开始循环处理 ${normalStudents.length} 名学生`);
                
                for (let j = 0; j < normalStudents.length; j++) {
                    const student = normalStudents[j];
                    addWorkflowLog('info', `[${j + 1}/${normalStudents.length}] 处理学生: ${student.name}`);
                    
                    // 执行循环内的子步骤
                    for (const subStep of step.steps) {
                        if (subStep.action === 'rfid' && subStep.target === 'current') {
                            addWorkflowLog('info', `刷学生卡: ${student.name} (${student.rfid_no})`);
                            const success = await sendRfidCard(student.rfid_no);
                            if (!success) {
                                addWorkflowLog('error', `刷卡失败: ${student.name}`);
                            }
                            if (subStep.wait) await sleep(subStep.wait * 1000);
                        } else if (subStep.action === 'tap') {
                            addWorkflowLog('info', `${subStep.desc || '点击'}`);
                            await executeAtomStep(subStep);
                            // 使用参数中的拍照间隔
                            const waitTime = subStep.text === '${photo_interval}' ? photoInterval : (subStep.wait || 1);
                            await sleep(waitTime * 1000);
                        } else {
                            await executeAtomStep(subStep);
                            if (subStep.wait) await sleep(subStep.wait * 1000);
                        }
                    }
                }
                
                setStepDone('submit_homework', i);
                addWorkflowLog('success', '学生循环处理完成');
            } else {
                // 普通原子操作
                addWorkflowLog('info', `执行: ${step.desc || step.action}`);
                const success = await executeAtomStep(step);
                
                if (success) {
                    setStepDone('submit_homework', i);
                } else {
                    setStepError('submit_homework', i);
                    throw new Error(`步骤失败: ${step.desc}`);
                }
            }
            
            // 等待
            if (step.wait && step.action !== 'loop') {
                await sleep(step.wait * 1000);
            }
        }
        
        updateWorkflowStatus('submit', 'success', '已完成');
        addWorkflowLog('success', '提交作业流程完成');
    } catch (e) {
        updateWorkflowStatus('submit', 'error', '执行失败');
        addWorkflowLog('error', `流程异常: ${e.message}`);
    } finally {
        workflowState.submitRunning = false;
    }
}

// 发送 RFID 卡号
async function sendRfidCard(rfidCode) {
    try {
        const response = await fetch('/api/rfid-simulator/send', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rfid_code: rfidCode })
        });
        const result = await response.json();
        return result.success;
    } catch (e) {
        console.error('发送 RFID 失败:', e);
        return false;
    }
}

// 同步学生信息到提交作业流程
function syncStudentInfo() {
    // 定时检查学生数据变化
    setInterval(() => {
        if (typeof state !== 'undefined' && state.students) {
            const infoEl = document.getElementById('workflowStudentInfo');
            const countEl = document.getElementById('workflowStudentCount');
            
            if (state.students.length > 0) {
                if (infoEl) infoEl.style.display = 'block';
                if (countEl) countEl.textContent = state.students.length;
            } else {
                if (infoEl) infoEl.style.display = 'none';
            }
        }
    }, 1000);
}

// ==================== 辅助函数 ====================

async function checkClientConnection() {
    try {
        const response = await fetch('/api/rfid-simulator/status');
        const result = await response.json();
        return result.success && result.data?.connected;
    } catch (e) {
        return false;
    }
}

function updateWorkflowStatus(type, status, text) {
    const statusEl = document.getElementById(type + 'Status');
    if (statusEl) {
        statusEl.textContent = text;
        statusEl.className = 'workflow-card-status ' + status;
    }
}

function setStepActive(workflowId, index) {
    const stepEl = document.querySelector(`[data-step="${index}"][data-workflow="${workflowId}"]`);
    if (stepEl) {
        stepEl.classList.remove('done', 'error');
        stepEl.classList.add('active');
    }
}

function setStepDone(workflowId, index) {
    const stepEl = document.querySelector(`[data-step="${index}"][data-workflow="${workflowId}"]`);
    if (stepEl) {
        stepEl.classList.remove('active', 'error');
        stepEl.classList.add('done');
    }
}

function setStepError(workflowId, index) {
    const stepEl = document.querySelector(`[data-step="${index}"][data-workflow="${workflowId}"]`);
    if (stepEl) {
        stepEl.classList.remove('active', 'done');
        stepEl.classList.add('error');
    }
}

function addWorkflowLog(level, message) {
    const logList = document.getElementById('workflowLogList');
    if (!logList) return;
    
    const emptyEl = logList.querySelector('.log-empty');
    if (emptyEl) emptyEl.remove();
    
    const time = new Date().toLocaleTimeString('zh-CN', { hour12: false });
    const logItem = document.createElement('div');
    logItem.className = `workflow-log-item ${level}`;
    logItem.textContent = `[${time}] ${message}`;
    
    logList.appendChild(logItem);
    logList.scrollTop = logList.scrollHeight;
}

function clearWorkflowLog() {
    const logList = document.getElementById('workflowLogList');
    if (logList) {
        logList.innerHTML = '<div class="log-empty">暂无日志</div>';
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

// ==================== 坐标配置 ====================

function toggleCoordinateEditor() {
    const modal = document.getElementById('coordinateModal');
    if (modal) {
        modal.style.display = modal.style.display === 'flex' ? 'none' : 'flex';
        if (modal.style.display === 'flex') {
            loadCoordinates();
        }
    }
}

function closeCoordinateEditor() {
    const modal = document.getElementById('coordinateModal');
    if (modal) modal.style.display = 'none';
}

async function loadCoordinates() {
    try {
        const response = await fetch('/api/rfid-simulator/coordinates');
        const result = await response.json();
        if (result.success) {
            renderCoordinateList(result.data);
        }
    } catch (e) {
        console.error('加载坐标配置失败:', e);
    }
}

function renderCoordinateList(coords) {
    const list = document.getElementById('coordList');
    if (!list || !coords) return;
    
    list.innerHTML = Object.entries(coords).map(([key, coord]) => `
        <div class="coord-item" data-key="${key}">
            <div class="coord-info">
                <div class="coord-name">${coord.description || key}</div>
                <div class="coord-key">${key}</div>
            </div>
            <div class="coord-values">
                <input type="number" class="coord-input" value="${coord.x}" data-field="x">
                <span class="coord-sep">,</span>
                <input type="number" class="coord-input" value="${coord.y}" data-field="y">
            </div>
            <div class="coord-wait">
                <input type="number" class="coord-wait-input" value="${coord.wait_after || 1}" data-field="wait_after" step="0.5">s
            </div>
        </div>
    `).join('');
}
