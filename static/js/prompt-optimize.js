/**
 * Prompt 优化页面 JavaScript
 * Feature: prompt-optimization
 */

// ========== 全局状态 ==========
let currentTaskId = null;
let currentPrompt = '';
let currentModel = 'doubao-seed-1-8-251215';
let currentVersion = 'current';
let currentScore = null;
let currentTab = 'batch';
let currentModelResponse = '';
let editingSampleId = null;

// 任务场景和调优模式
let taskScene = 'vision';  // single, multi, vision
let evalMode = 'score';    // score, gsb
let currentGSB = null;     // G, S, B

// 数据集
let samples = [];
let currentPage = 1;
let pageSize = 20;

// 评分规则
let scoringRules = '';

// ========== 变量检测 ==========
function detectVariables(text) {
    if (!text) return [];
    const regex = /\{\{(\w+)\}\}/g;
    const variables = [];
    const seen = new Set();
    let match;
    while ((match = regex.exec(text)) !== null) {
        const varName = match[1];
        if (!seen.has(varName)) {
            seen.add(varName);
            variables.push(varName);
        }
    }
    return variables;
}

function isValidScore(score) {
    return Number.isInteger(score) && score >= 1 && score <= 10;
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', function() {
    const promptEditor = document.getElementById('promptEditor');
    if (promptEditor) {
        promptEditor.addEventListener('input', onPromptChange);
    }
    
    loadTaskList();
    initScoreButtons();
    initGSBButtons();
    
    // 初始化任务场景和调优模式
    onTaskSceneChange();
    onEvalModeChange();
    
    // 默认显示批量 Tab
    switchTab('batch');
});

// ========== 返回导航 ==========
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

// ========== 模型切换 ==========
function onModelChange() {
    const select = document.getElementById('modelSelect');
    currentModel = select.value;
}

// ========== 任务场景切换 ==========
function onTaskSceneChange() {
    const select = document.getElementById('taskSceneSelect');
    taskScene = select.value;
    
    // 更新Prompt标签
    const promptLabel = document.getElementById('promptLabel');
    if (taskScene === 'multi') {
        promptLabel.textContent = '系统 Prompt';
    } else {
        promptLabel.textContent = 'Prompt';
    }
    
    // 更新表格列头
    updateTableHeaders();
    
    // 视觉理解模式下禁用GSB比较
    const evalModeSelect = document.getElementById('evalModeSelect');
    if (taskScene === 'vision') {
        // 视觉理解支持评分模式
        evalModeSelect.value = 'score';
        evalMode = 'score';
        onEvalModeChange();
    }
}

// ========== 调优模式切换 ==========
function onEvalModeChange() {
    const select = document.getElementById('evalModeSelect');
    evalMode = select.value;
    
    // 切换评分/GSB区域显示
    const scoreModeSection = document.getElementById('scoreModeSection');
    const gsbModeSection = document.getElementById('gsbModeSection');
    
    if (evalMode === 'gsb') {
        scoreModeSection.style.display = 'none';
        gsbModeSection.style.display = 'block';
    } else {
        scoreModeSection.style.display = 'flex';
        gsbModeSection.style.display = 'none';
    }
    
    // 更新评估模式徽章
    const badge = document.getElementById('evalModeBadge');
    if (evalMode === 'gsb') {
        badge.textContent = 'GSB比较模式';
        badge.classList.add('gsb');
    } else {
        badge.textContent = '评分模式 (1-10分)';
        badge.classList.remove('gsb');
    }
    
    // 更新表格列头
    updateTableHeaders();
    renderTable();
}

// ========== 更新表格列头 ==========
function updateTableHeaders() {
    const colInputHeader = document.getElementById('colInputHeader');
    const colReferenceHeader = document.getElementById('colReferenceHeader');
    const colScoreHeader = document.getElementById('colScoreHeader');
    
    // 根据任务场景更新输入列
    if (taskScene === 'vision') {
        colInputHeader.textContent = '变量(文本/图像)';
    } else if (taskScene === 'multi') {
        colInputHeader.textContent = '用户内容';
    } else {
        colInputHeader.textContent = '变量(文本)';
    }
    
    // 根据调优模式更新参照列和评分列
    if (evalMode === 'gsb') {
        colReferenceHeader.textContent = '参照回答';
        colScoreHeader.textContent = 'GSB结果';
    } else {
        colReferenceHeader.textContent = '理想回答';
        colScoreHeader.textContent = '评分';
    }
}

// ========== GSB按钮初始化 ==========
function initGSBButtons() {
    document.querySelectorAll('.gsb-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const gsb = this.dataset.gsb;
            setGSB(gsb);
        });
    });
}

// ========== 设置GSB ==========
function setGSB(gsb) {
    currentGSB = gsb;
    
    document.querySelectorAll('.gsb-btn').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.gsb === gsb) {
            btn.classList.add('active');
        }
    });
}

// ========== 添加至评测集(GSB模式) ==========
async function addToDatasetGSB() {
    if (!currentModelResponse) {
        alert('请先生成模型回答');
        return;
    }
    
    if (!currentGSB) {
        alert('请先选择GSB评估结果');
        return;
    }
    
    const variables = getVariableValues();
    const referenceAnswer = document.getElementById('referenceAnswer').value;
    
    const sample = {
        task_id: currentTaskId,
        variables: variables,
        model_response: currentModelResponse,
        reference_answer: referenceAnswer,
        gsb_result: currentGSB,
        eval_mode: 'gsb'
    };
    
    try {
        const response = await fetch('/api/prompt-sample', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sample)
        });
        
        if (!response.ok) throw new Error('添加失败');
        
        const result = await response.json();
        
        samples.push({ sample_id: result.sample_id, ...sample });
        updateStats();
        renderTable();
        clearDebugStateGSB();
        
        alert('已添加至评测集');
        switchTab('batch');
        
    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

function clearDebugStateGSB() {
    currentModelResponse = '';
    currentGSB = null;
    
    document.getElementById('modelResponse').innerHTML = '<div class="empty-hint">点击"生成模型回答"查看结果</div>';
    document.getElementById('referenceAnswer').value = '';
    
    document.querySelectorAll('.gsb-btn').forEach(btn => btn.classList.remove('active'));
}

// ========== AI生成Prompt ==========
let generatedPromptText = '';

function generatePromptFromTask() {
    document.getElementById('promptGenModal').classList.add('show');
    document.getElementById('taskDescInput').value = '';
    document.getElementById('generatedPromptSection').style.display = 'none';
    document.getElementById('genPromptBtn').style.display = 'inline-block';
    document.getElementById('applyPromptBtn').style.display = 'none';
    generatedPromptText = '';
}

function hidePromptGenModal() {
    document.getElementById('promptGenModal').classList.remove('show');
}

function selectGenOption(el, option) {
    document.querySelectorAll('.gen-option').forEach(o => o.classList.remove('selected'));
    el.classList.add('selected');
    
    const templates = {
        '图片内容识别': '识别图片中的内容，提取关键信息并以结构化格式输出',
        '文本分类': '对输入文本进行分类，判断其所属类别',
        '信息提取': '从给定文本中提取指定的关键信息',
        '问答对话': '根据用户问题提供准确、有帮助的回答',
        '内容生成': '根据给定主题或要求生成相应内容'
    };
    
    document.getElementById('taskDescInput').value = templates[option] || option;
}

async function doGeneratePrompt() {
    const taskDesc = document.getElementById('taskDescInput').value.trim();
    if (!taskDesc) {
        alert('请输入任务描述');
        return;
    }
    
    const btn = document.getElementById('genPromptBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    
    try {
        const response = await fetch('/api/prompt-generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_description: taskDesc,
                task_scene: taskScene,
                eval_mode: evalMode
            })
        });
        
        if (!response.ok) throw new Error('生成失败');
        
        const result = await response.json();
        
        if (result.prompt) {
            generatedPromptText = result.prompt;
            document.getElementById('generatedPromptPreview').textContent = result.prompt;
            document.getElementById('generatedPromptSection').style.display = 'block';
            document.getElementById('genPromptBtn').style.display = 'none';
            document.getElementById('applyPromptBtn').style.display = 'inline-block';
        } else if (result.error) {
            alert('生成失败: ' + result.error);
        }
        
    } catch (error) {
        alert('生成Prompt失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '生成Prompt';
    }
}

function applyGeneratedPrompt() {
    if (generatedPromptText) {
        currentPrompt = generatedPromptText;
        document.getElementById('promptEditor').value = currentPrompt;
        onPromptChange();
        hidePromptGenModal();
    }
}

function initScoreButtons() {
    document.querySelectorAll('.score-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            const score = parseInt(this.dataset.score);
            setScore(score);
        });
    });
}

// ========== 侧边栏控制 ==========
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    sidebar.classList.toggle('collapsed');
}

function showScoringPanel() {
    const panel = document.getElementById('scoringSidebar');
    panel.classList.remove('hidden');
}

function hideScoringPanel() {
    const panel = document.getElementById('scoringSidebar');
    panel.classList.add('hidden');
}

// ========== Tab 切换 ==========
function switchTab(tab) {
    currentTab = tab;
    
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.tab === tab);
    });
    
    document.querySelectorAll('.tab-content').forEach(content => {
        content.classList.remove('active');
    });
    
    const contentId = tab + 'Content';
    const content = document.getElementById(contentId);
    if (content) {
        content.classList.add('active');
    }
    
    if (tab === 'optimize') {
        checkOptimizationPrerequisites();
    }
}

// ========== Prompt 编辑器 ==========
function onPromptChange() {
    const promptEditor = document.getElementById('promptEditor');
    currentPrompt = promptEditor.value;
    
    const variables = detectVariables(currentPrompt);
    updateVariablesInputs(variables);
}

function updateVariablesInputs(variables) {
    const container = document.getElementById('variablesInputs');
    if (!container) return;
    
    if (variables.length === 0) {
        container.innerHTML = '<div class="empty-hint">请在 Prompt 中使用 {{变量名}} 定义变量</div>';
        return;
    }
    
    container.innerHTML = variables.map(varName => {
        const isImage = varName.toLowerCase().includes('image') || 
                       varName.toLowerCase().includes('img') ||
                       varName.toLowerCase().includes('图') ||
                       varName.toLowerCase().includes('answer');
        
        if (isImage) {
            return `
                <div class="variable-input" data-var="${varName}">
                    <label>{{${varName}}} <span class="var-type">(图片)</span></label>
                    <div class="image-upload-area" onclick="triggerImageUpload('${varName}')">
                        <input type="file" id="file_${varName}" accept="image/*" hidden onchange="handleImageUpload(event, '${varName}')">
                        <div class="upload-placeholder" id="placeholder_${varName}">点击上传图片</div>
                        <img id="preview_${varName}" class="image-preview" style="display:none;">
                    </div>
                </div>
            `;
        } else {
            return `
                <div class="variable-input" data-var="${varName}">
                    <label>{{${varName}}}</label>
                    <textarea id="var_${varName}" placeholder="输入 ${varName} 的值..."></textarea>
                </div>
            `;
        }
    }).join('');
}

function triggerImageUpload(varName) {
    document.getElementById('file_' + varName).click();
}

function handleImageUpload(event, varName) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('preview_' + varName);
        const placeholder = document.getElementById('placeholder_' + varName);
        preview.src = e.target.result;
        preview.style.display = 'block';
        placeholder.style.display = 'none';
        preview.dataset.base64 = e.target.result;
    };
    reader.readAsDataURL(file);
}

function getVariableValues() {
    const variables = detectVariables(currentPrompt);
    const values = {};
    
    variables.forEach(varName => {
        const isImage = varName.toLowerCase().includes('image') || 
                       varName.toLowerCase().includes('img') ||
                       varName.toLowerCase().includes('图') ||
                       varName.toLowerCase().includes('answer');
        
        if (isImage) {
            const preview = document.getElementById('preview_' + varName);
            if (preview && preview.dataset.base64) {
                values[varName] = { type: 'image', value: preview.dataset.base64 };
            }
        } else {
            const input = document.getElementById('var_' + varName);
            if (input) {
                values[varName] = { type: 'text', value: input.value };
            }
        }
    });
    
    return values;
}


// ========== 生成模型回答 ==========
async function generateResponse() {
    const btn = document.getElementById('generateBtn');
    const responseDiv = document.getElementById('modelResponse');
    
    if (!currentPrompt.trim()) {
        alert('请先输入 Prompt');
        return;
    }
    
    const variables = getVariableValues();
    
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> 生成中...';
    responseDiv.innerHTML = '<div class="loading-hint">正在生成回答...</div>';
    
    try {
        const response = await fetch('/api/prompt-eval/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: currentPrompt,
                model: currentModel,
                variables: variables
            })
        });
        
        if (!response.ok) throw new Error('生成失败');
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let result = '';
        
        responseDiv.innerHTML = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const json = JSON.parse(data);
                        if (json.content) {
                            result += json.content;
                            responseDiv.innerHTML = marked.parse(result);
                        }
                    } catch (e) {}
                }
            }
        }
        
        currentModelResponse = result;
        
    } catch (error) {
        responseDiv.innerHTML = `<div class="error-hint">生成失败: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="18" height="18"><path fill="currentColor" d="M8 5v14l11-7z"/></svg> 生成模型回答';
    }
}

// ========== 评分功能 ==========
function setScore(score) {
    if (!isValidScore(score)) return;

    currentScore = score;

    // 更新所有评分按钮的状态
    document.querySelectorAll('#scoreButtons .score-btn, #debugScoreButtons .score-btn').forEach(btn => {
        const btnScore = parseInt(btn.dataset.score);
        btn.classList.toggle('active', btnScore === score);
    });
}

// ========== 添加至评测集 ==========
async function addToDataset() {
    if (!currentModelResponse) {
        alert('请先生成模型回答');
        return;
    }

    // 如果没有选择任务，自动创建一个默认任务
    if (!currentTaskId) {
        try {
            const createResponse = await fetch('/api/prompt-task', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    name: '默认任务 ' + new Date().toLocaleDateString(),
                    prompt: currentPrompt || document.getElementById('debugPromptArea')?.value || '',
                    model: currentModel
                })
            });

            if (!createResponse.ok) throw new Error('创建任务失败');

            const createResult = await createResponse.json();
            currentTaskId = createResult.task_id;

            // 更新任务选择器
            await loadTaskList();
            document.getElementById('taskSelect').value = currentTaskId;
        } catch (error) {
            alert('创建任务失败: ' + error.message);
            return;
        }
    }

    // 获取变量值 - 支持新旧两种界面
    let variables = {};
    if (debugImageBase64) {
        variables['IMAGE'] = { type: 'image', value: debugImageBase64 };
    } else {
        variables = getVariableValues();
    }

    // 获取理想回答 - 支持新旧两种界面
    const idealAnswerEl = document.getElementById('debugIdealAnswer') || document.getElementById('idealAnswer');
    const idealAnswer = idealAnswerEl ? idealAnswerEl.value : '';

    const sample = {
        task_id: currentTaskId,
        variables: variables,
        model_response: currentModelResponse,
        ideal_answer: idealAnswer,
        score: currentScore || null,  // 允许不评分
        score_source: currentScore ? 'manual' : null
    };

    try {
        const response = await fetch('/api/prompt-sample', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(sample)
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || '添加失败');
        }

        const result = await response.json();

        samples.push({ sample_id: result.sample_id, ...sample });
        updateStats();
        renderTable();
        clearDebugState();

        alert('已添加至评测集' + (currentScore ? '' : '，可在批量页面使用AI智能评分'));
        switchTab('batch');

    } catch (error) {
        alert('添加失败: ' + error.message);
    }
}

function clearDebugState() {
    currentModelResponse = '';
    currentScore = null;

    // 清空旧界面元素（如果存在）
    const modelResponse = document.getElementById('modelResponse');
    if (modelResponse) {
        modelResponse.innerHTML = '<div class="empty-hint">点击"生成模型回答"查看结果</div>';
    }
    const idealAnswer = document.getElementById('idealAnswer');
    if (idealAnswer) {
        idealAnswer.value = '';
    }

    // 清空新界面元素
    const debugResponseBody = document.getElementById('debugResponseBody');
    if (debugResponseBody) {
        debugResponseBody.innerHTML = '<div class="debug-response-placeholder">点击左侧「生成模型回答」后，大模型的回答将显示在这里</div>';
    }
    const debugIdealAnswer = document.getElementById('debugIdealAnswer');
    if (debugIdealAnswer) {
        debugIdealAnswer.value = '';
    }
    const debugScoringSection = document.getElementById('debugScoringSection');
    if (debugScoringSection) {
        debugScoringSection.style.display = 'none';
    }

    // 清空所有评分按钮
    document.querySelectorAll('.score-btn').forEach(btn => btn.classList.remove('active'));
}

// ========== 任务管理 ==========
async function loadTaskList() {
    try {
        const response = await fetch('/api/prompt-tasks');
        if (!response.ok) return;
        
        const tasks = await response.json();
        const select = document.getElementById('taskSelect');
        
        select.innerHTML = '<option value="">选择任务...</option>' +
            tasks.map(t => `<option value="${t.task_id}">${t.name} (${t.sample_count || 0}条)</option>`).join('');
            
    } catch (error) {
        console.error('加载任务列表失败:', error);
    }
}

async function loadTask() {
    const select = document.getElementById('taskSelect');
    const taskId = select.value;
    
    if (!taskId) {
        currentTaskId = null;
        currentPrompt = '';
        samples = [];
        document.getElementById('promptEditor').value = '';
        onPromptChange();
        renderTable();
        return;
    }
    
    try {
        const response = await fetch(`/api/prompt-task/${taskId}`);
        if (!response.ok) throw new Error('加载失败');
        
        const task = await response.json();
        currentTaskId = taskId;
        currentPrompt = task.current_prompt || '';
        samples = task.samples || [];
        scoringRules = task.scoring_rules || '';
        
        document.getElementById('promptEditor').value = currentPrompt;
        document.getElementById('scoringRules').value = scoringRules;
        onPromptChange();
        
        loadVersionList(task.versions || []);
        renderTable();
        updateStats();
        
    } catch (error) {
        alert('加载任务失败: ' + error.message);
    }
}

function loadVersionList(versions) {
    const select = document.getElementById('versionSelect');
    select.innerHTML = '<option value="current">当前版本</option>' +
        versions.map(v => `<option value="${v}">${v}</option>`).join('');
}

function showNewTaskModal() {
    document.getElementById('newTaskModal').classList.add('show');
    document.getElementById('newTaskName').value = '';
    document.getElementById('newTaskName').focus();
}

function hideNewTaskModal() {
    document.getElementById('newTaskModal').classList.remove('show');
}

async function createTask() {
    const name = document.getElementById('newTaskName').value.trim();
    if (!name) {
        alert('请输入任务名称');
        return;
    }
    
    try {
        const response = await fetch('/api/prompt-task', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: name, prompt: '', model: currentModel })
        });
        
        if (!response.ok) throw new Error('创建失败');
        
        const result = await response.json();
        
        hideNewTaskModal();
        await loadTaskList();
        
        document.getElementById('taskSelect').value = result.task_id;
        await loadTask();
        
    } catch (error) {
        alert('创建任务失败: ' + error.message);
    }
}


// ========== 批量评测 - 表格渲染 ==========
function renderTable() {
    const tbody = document.getElementById('dataTableBody');
    
    if (samples.length === 0) {
        tbody.innerHTML = `
            <tr class="empty-row">
                <td colspan="8">
                    <div class="empty-hint">暂无数据，点击"+"添加行或"上传文件"导入数据</div>
                </td>
            </tr>
        `;
        updatePagination();
        return;
    }
    
    const start = (currentPage - 1) * pageSize;
    const end = Math.min(start + pageSize, samples.length);
    const pageData = samples.slice(start, end);
    
    tbody.innerHTML = pageData.map((sample, idx) => {
        const globalIdx = start + idx + 1;
        const inputHtml = formatInputCell(sample.variables);
        const responseHtml = formatResponseCell(sample.model_response, sample.sample_id);
        const referenceHtml = formatReferenceCell(sample, sample.sample_id);
        const scoreHtml = formatScoreCell(sample.score, sample.score_source, sample.gsb_result);
        
        return `
            <tr data-id="${sample.sample_id}">
                <td class="col-checkbox"><input type="checkbox" class="row-checkbox" data-id="${sample.sample_id}"></td>
                <td class="col-index">${globalIdx}</td>
                <td class="col-input">${inputHtml}</td>
                <td class="col-response">${responseHtml}</td>
                <td class="col-reference">${referenceHtml}</td>
                <td class="col-score">${scoreHtml}</td>
                <td class="col-actions">
                    <button class="btn-icon" onclick="editRow('${sample.sample_id}')" title="编辑">
                        <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg>
                    </button>
                    <button class="btn-icon" onclick="deleteSample('${sample.sample_id}')" title="删除">
                        <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/></svg>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    updatePagination();
}

function formatInputCell(variables) {
    if (!variables) return '<span class="empty-hint">-</span>';
    
    let hasImage = false;
    let imgSrc = '';
    
    for (const [key, val] of Object.entries(variables)) {
        if (val.type === 'image' || val.type === 'image_url') {
            hasImage = true;
            imgSrc = val.value;
            break;
        }
    }
    
    if (hasImage) {
        const imageCount = Object.values(variables).filter(v => v.type === 'image' || v.type === 'image_url').length;
        return `
            <div class="cell-image-wrapper">
                <img src="${imgSrc}" class="cell-image" onclick="showImageModal('${imgSrc}')" alt="图片">
                <div class="cell-expand" onclick="showCellModal('变量详情', '${escapeHtml(JSON.stringify(variables))}')">${imageCount > 1 ? `共${imageCount}张图片` : '查看详情'}</div>
            </div>
        `;
    }
    
    // 文本变量
    const textVars = Object.entries(variables)
        .filter(([k, v]) => v.type === 'text')
        .map(([k, v]) => `${k}: ${v.value}`)
        .join(', ');
    
    return `<div class="cell-text" onclick="showCellModal('变量', '${escapeHtml(textVars)}')">${truncateText(textVars, 50)}</div>`;
}

function formatImageCell(variables) {
    return formatInputCell(variables);
}

function formatReferenceCell(sample, sampleId) {
    // GSB模式显示参照回答
    if (sample.eval_mode === 'gsb' || sample.reference_answer) {
        const text = sample.reference_answer;
        if (!text) return `<span class="cell-expand" onclick="editRow('${sampleId}')">点击编辑 ▸</span>`;
        return `<div class="cell-text" onclick="showCellModal('参照回答', '${escapeHtml(text)}')">${truncateText(text, 80)}</div>`;
    }
    
    // 评分模式显示理想回答
    const text = sample.ideal_answer;
    if (!text) return `<span class="cell-expand" onclick="editRow('${sampleId}')">点击编辑 ▸</span>`;
    return `<div class="cell-text" onclick="showCellModal('理想回答', '${escapeHtml(text)}')">${truncateText(text, 80)}</div>`;
}

function formatTextCell(text, type, sampleId) {
    if (!text) return `<span class="cell-expand" onclick="editIdealAnswer('${sampleId}')">点击编辑 ▸</span>`;
    return `<div class="cell-text" onclick="showCellModal('${type === 'ideal' ? '理想回答' : '内容'}', '${escapeHtml(text)}')">${truncateText(text, 80)}</div>`;
}

function formatResponseCell(response, sampleId) {
    if (!response) return '<span class="empty-hint">-</span>';
    
    // 尝试解析 JSON
    try {
        const parsed = JSON.parse(response);
        const jsonStr = JSON.stringify(parsed, null, 2);
        return `
            <div class="cell-json" onclick="showCellModal('模型回答', '${escapeHtml(jsonStr)}')">
                ${truncateText(jsonStr, 150)}
            </div>
            <div class="cell-expand" onclick="showCellModal('模型回答', '${escapeHtml(jsonStr)}')">▸ 生成回答</div>
        `;
    } catch (e) {
        return `<div class="cell-text" onclick="showCellModal('模型回答', '${escapeHtml(response)}')">${truncateText(response, 100)}</div>`;
    }
}

function formatScoreCell(score, source, gsbResult) {
    // GSB模式
    if (evalMode === 'gsb' || gsbResult) {
        if (!gsbResult) return '<span class="no-score">-</span>';
        
        const gsbClass = gsbResult === 'G' ? 'good' : (gsbResult === 'S' ? 'same' : 'bad');
        const gsbText = gsbResult === 'G' ? 'Good' : (gsbResult === 'S' ? 'Same' : 'Bad');
        
        return `<span class="gsb-result ${gsbClass}">${gsbText}</span>`;
    }
    
    // 评分模式 (1-10分)
    if (!score) return '<span class="no-score">-</span>';
    
    const colorClass = score >= 7 ? 'high' : (score >= 4 ? 'medium' : 'low');
    const label = source === 'ai' ? 'AI' : '';
    
    return `
        <div class="score-display">
            <span class="score-value ${colorClass}">${score}</span>
            ${label ? `<span class="score-label">${label}</span>` : ''}
        </div>
    `;
}

function truncateText(text, maxLen) {
    if (!text) return '';
    text = String(text);
    if (text.length <= maxLen) return escapeHtml(text);
    return escapeHtml(text.substring(0, maxLen)) + '...';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML.replace(/'/g, "\\'").replace(/"/g, '\\"');
}

// ========== 分页 ==========
function calculatePagination(total, pageSize) {
    return Math.ceil(total / pageSize);
}

function updatePagination() {
    const total = samples.length;
    const totalPages = calculatePagination(total, pageSize);
    
    document.getElementById('totalItems').textContent = total;
    document.getElementById('pageNumbers').textContent = currentPage;
    
    document.getElementById('prevBtn').disabled = currentPage <= 1;
    document.getElementById('nextBtn').disabled = currentPage >= totalPages;
}

function goToPage(direction) {
    const totalPages = calculatePagination(samples.length, pageSize);
    
    if (direction === 'prev') {
        currentPage = Math.max(1, currentPage - 1);
    } else if (direction === 'next') {
        currentPage = Math.min(totalPages, currentPage + 1);
    }
    
    renderTable();
}

function changePageSize() {
    pageSize = parseInt(document.getElementById('pageSize').value);
    currentPage = 1;
    renderTable();
}

// ========== 统计 ==========
function calculateStats(samples) {
    const scored = samples.filter(s => s.score != null);
    const total = samples.length;
    const scoredCount = scored.length;
    
    let avgScore = 0;
    if (scoredCount > 0) {
        const sum = scored.reduce((acc, s) => acc + s.score, 0);
        avgScore = sum / scoredCount;
    }
    
    return { avgScore, scoredCount, total };
}

function updateStats() {
    const stats = calculateStats(samples);
    // 可以在界面上显示统计信息
}

// ========== 添加行 ==========
function addRow() {
    const variables = detectVariables(currentPrompt);
    const emptyVars = {};
    variables.forEach(v => {
        emptyVars[v] = { type: 'text', value: '' };
    });
    
    const newSample = {
        sample_id: 'temp_' + Date.now(),
        variables: emptyVars,
        model_response: '',
        ideal_answer: '',
        score: null,
        score_source: null
    };
    
    samples.push(newSample);
    renderTable();
    
    // 打开编辑弹窗
    editRow(newSample.sample_id);
}

// ========== 文件上传 ==========
function uploadFile() {
    document.getElementById('batchFileInput').click();
}

async function handleFileUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('task_id', currentTaskId);
    
    try {
        const response = await fetch('/api/prompt-sample/batch', {
            method: 'POST',
            body: formData
        });
        
        if (!response.ok) throw new Error('上传失败');
        
        const result = await response.json();
        alert(`成功导入 ${result.imported} 条数据`);
        
        await loadTask();
        
    } catch (error) {
        alert('上传失败: ' + error.message);
    }
    
    event.target.value = '';
}

function toggleSelectAll() {
    const selectAll = document.getElementById('selectAll');
    document.querySelectorAll('.row-checkbox').forEach(cb => {
        cb.checked = selectAll.checked;
    });
}


// ========== 批量生成回答 ==========
async function generateAllResponses() {
    const unprocessed = samples.filter(s => !s.model_response);
    
    if (unprocessed.length === 0) {
        alert('所有样本都已有回答');
        return;
    }
    
    if (!confirm(`将为 ${unprocessed.length} 个样本生成回答，是否继续？`)) {
        return;
    }
    
    const btn = document.querySelector('.btn-toolbar.primary');
    btn.disabled = true;
    btn.innerHTML = '<span class="loading-spinner"></span> 生成中 0/' + unprocessed.length;
    
    let completed = 0;
    
    try {
        const response = await fetch('/api/prompt-eval/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: currentPrompt,
                model: currentModel,
                sample_ids: unprocessed.map(s => s.sample_id)
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const json = JSON.parse(data);
                        if (json.sample_id && json.response) {
                            const sample = samples.find(s => s.sample_id === json.sample_id);
                            if (sample) {
                                sample.model_response = json.response;
                            }
                            completed++;
                            btn.innerHTML = `<span class="loading-spinner"></span> 生成中 ${completed}/${unprocessed.length}`;
                            renderTable();
                        }
                    } catch (e) {}
                }
            }
        }
        
        alert(`生成完成，共处理 ${completed} 个样本`);
        
    } catch (error) {
        alert('生成失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M8 5v14l11-7z"/></svg> 生成全部回答';
    }
}

// ========== 智能评分 ==========
async function generateScoringRules() {
    const method = document.querySelector('input[name="scoringMethod"]:checked').value;
    const btn = document.querySelector('.btn-ai-generate');
    
    btn.disabled = true;
    btn.textContent = '生成中...';
    
    try {
        const response = await fetch('/api/prompt-score/rules', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: currentPrompt,
                method: method,
                samples: method === 'learn' ? samples.filter(s => s.score && s.score_source === 'manual') : []
            })
        });
        
        if (!response.ok) throw new Error('生成失败');
        
        const result = await response.json();
        document.getElementById('scoringRules').value = result.rules;
        scoringRules = result.rules;
        
    } catch (error) {
        alert('生成评分规则失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M19 9l-7 7-7-7"/></svg> AI生成';
    }
}

async function scoreUnscored() {
    const unscored = samples.filter(s => s.model_response && !s.score);
    
    if (unscored.length === 0) {
        alert('没有需要评分的样本');
        return;
    }
    
    await batchScore(unscored.map(s => s.sample_id));
}

async function scoreAll() {
    const withResponse = samples.filter(s => s.model_response);
    
    if (withResponse.length === 0) {
        alert('没有可评分的样本');
        return;
    }
    
    if (!confirm(`将重新评分 ${withResponse.length} 个样本，是否继续？`)) {
        return;
    }
    
    await batchScore(withResponse.map(s => s.sample_id));
}

async function batchScore(sampleIds) {
    const rules = document.getElementById('scoringRules').value;
    if (!rules.trim()) {
        alert('请先设置评分规则');
        return;
    }
    
    const btn = document.querySelector('.btn-score-action');
    btn.disabled = true;
    btn.innerHTML = `<span class="loading-spinner"></span> 评分中 0/${sampleIds.length}`;
    
    let completed = 0;
    
    try {
        const response = await fetch('/api/prompt-score/batch', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                sample_ids: sampleIds,
                rules: rules,
                prompt: currentPrompt
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const json = JSON.parse(data);
                        if (json.sample_id && json.score) {
                            const sample = samples.find(s => s.sample_id === json.sample_id);
                            if (sample) {
                                sample.score = json.score;
                                sample.score_source = 'ai';
                                sample.score_reason = json.reason;
                            }
                            completed++;
                            btn.innerHTML = `<span class="loading-spinner"></span> 评分中 ${completed}/${sampleIds.length}`;
                            renderTable();
                        }
                    } catch (e) {}
                }
            }
        }
        
        alert(`评分完成，共处理 ${completed} 个样本`);
        
    } catch (error) {
        alert('评分失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '为未评分的回答评分';
    }
}

// ========== 智能优化 ==========
function checkOptimizationPrerequisites() {
    const scoredSamples = samples.filter(s => s.score != null);
    const hasPrompt = currentPrompt.trim().length > 0;
    
    const reqSamples = document.getElementById('reqSamples');
    const reqPrompt = document.getElementById('reqPrompt');
    const checkStatus = document.getElementById('checkStatus');
    const startBtn = document.getElementById('startOptimizeBtn');
    
    if (scoredSamples.length >= 5) {
        reqSamples.querySelector('.req-icon').textContent = '✓';
        reqSamples.classList.add('passed');
    } else {
        reqSamples.querySelector('.req-icon').textContent = '○';
        reqSamples.classList.remove('passed');
    }
    
    if (hasPrompt) {
        reqPrompt.querySelector('.req-icon').textContent = '✓';
        reqPrompt.classList.add('passed');
    } else {
        reqPrompt.querySelector('.req-icon').textContent = '○';
        reqPrompt.classList.remove('passed');
    }
    
    const canOptimize = scoredSamples.length >= 5 && hasPrompt;
    
    if (canOptimize) {
        checkStatus.textContent = '✓ 满足优化条件';
        checkStatus.className = 'check-status passed';
        startBtn.disabled = false;
    } else {
        checkStatus.textContent = `当前: ${scoredSamples.length} 个已评分样本`;
        checkStatus.className = 'check-status';
        startBtn.disabled = true;
    }
}

async function startOptimization() {
    // 实现智能优化逻辑
    alert('智能优化功能开发中...');
}

// ========== 版本管理 ==========
async function saveVersion() {
    if (!currentTaskId) {
        alert('请先选择或创建任务');
        return;
    }
    
    try {
        const response = await fetch('/api/prompt-version', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: currentPrompt,
                scoring_rules: scoringRules
            })
        });
        
        if (!response.ok) throw new Error('保存失败');
        
        const result = await response.json();
        alert(`已保存为版本 ${result.version_id}`);
        
        await loadTask();
        
    } catch (error) {
        alert('保存版本失败: ' + error.message);
    }
}

async function loadVersion() {
    const versionId = document.getElementById('versionSelect').value;
    if (versionId === 'current' || !currentTaskId) return;
    
    try {
        const response = await fetch(`/api/prompt-version/${currentTaskId}/${versionId}`);
        if (!response.ok) throw new Error('加载失败');
        
        const version = await response.json();
        currentPrompt = version.prompt;
        scoringRules = version.scoring_rules || '';
        
        document.getElementById('promptEditor').value = currentPrompt;
        document.getElementById('scoringRules').value = scoringRules;
        onPromptChange();
        
    } catch (error) {
        alert('加载版本失败: ' + error.message);
    }
}

// ========== 一键改写 ==========
async function rewritePrompt() {
    if (!currentPrompt.trim()) {
        alert('请先输入 Prompt');
        return;
    }
    
    const btn = document.querySelector('.btn-small:first-child');
    btn.disabled = true;
    btn.textContent = '改写中...';
    
    try {
        const response = await fetch('/api/optimize-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: currentPrompt })
        });
        
        if (!response.ok) throw new Error('改写失败');
        
        const result = await response.json();
        
        if (result.optimized_prompt) {
            if (confirm('是否应用改写后的 Prompt？')) {
                currentPrompt = result.optimized_prompt;
                document.getElementById('promptEditor').value = currentPrompt;
                onPromptChange();
            }
        }
        
    } catch (error) {
        alert('改写失败: ' + error.message);
    } finally {
        btn.disabled = false;
        btn.textContent = '一键改写';
    }
}

// ========== AI 生成理想回答 ==========
async function generateIdealAnswer() {
    if (!currentModelResponse) {
        alert('请先生成模型回答');
        return;
    }
    
    try {
        const response = await fetch('/api/prompt-eval/generate-ideal', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                prompt: currentPrompt,
                variables: getVariableValues(),
                model_response: currentModelResponse
            })
        });
        
        if (!response.ok) throw new Error('生成失败');
        
        const result = await response.json();
        document.getElementById('idealAnswer').value = result.ideal_answer;
        
    } catch (error) {
        alert('生成理想回答失败: ' + error.message);
    }
}


// ========== 弹窗功能 ==========
function showCellModal(title, content) {
    document.getElementById('cellModalTitle').textContent = title;
    
    let displayContent = content;
    try {
        const parsed = JSON.parse(content.replace(/\\"/g, '"').replace(/\\'/g, "'"));
        displayContent = JSON.stringify(parsed, null, 2);
    } catch (e) {
        displayContent = content.replace(/\\n/g, '\n');
    }
    
    document.getElementById('cellContent').textContent = displayContent;
    document.getElementById('cellModal').classList.add('show');
}

function hideCellModal() {
    document.getElementById('cellModal').classList.remove('show');
}

function showImageModal(src) {
    document.getElementById('modalImg').src = src;
    document.getElementById('imageModal').classList.add('show');
}

function hideImageModal() {
    document.getElementById('imageModal').classList.remove('show');
}

function showConfigCheck(sampleId) {
    alert('配置检查功能开发中...');
}

// ========== 行编辑 ==========
function editRow(sampleId) {
    const sample = samples.find(s => s.sample_id === sampleId);
    if (!sample) return;
    
    editingSampleId = sampleId;
    
    // 填充图片
    const imageArea = document.getElementById('editImageArea');
    const preview = document.getElementById('editImagePreview');
    const placeholder = imageArea.querySelector('.upload-placeholder');
    
    let hasImage = false;
    for (const [key, val] of Object.entries(sample.variables || {})) {
        if (val.type === 'image' || val.type === 'image_url') {
            preview.src = val.value;
            preview.style.display = 'block';
            placeholder.style.display = 'none';
            hasImage = true;
            break;
        }
    }
    
    if (!hasImage) {
        preview.style.display = 'none';
        placeholder.style.display = 'block';
    }
    
    // 填充其他字段
    document.getElementById('editIdealAnswer').value = sample.ideal_answer || sample.reference_answer || '';
    document.getElementById('editModelResponse').textContent = sample.model_response || '-';
    
    // 根据评估模式显示不同的评分区域
    const editScoreSection = document.getElementById('editScoreSection');
    const editGSBSection = document.getElementById('editGSBSection');
    
    if (evalMode === 'gsb' || sample.eval_mode === 'gsb') {
        editScoreSection.style.display = 'none';
        editGSBSection.style.display = 'block';
        
        // 设置GSB
        document.querySelectorAll('#editGSBButtons .gsb-btn').forEach(btn => {
            btn.classList.remove('active');
            if (btn.dataset.gsb === sample.gsb_result) {
                btn.classList.add('active');
            }
            btn.onclick = function() {
                document.querySelectorAll('#editGSBButtons .gsb-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            };
        });
    } else {
        editScoreSection.style.display = 'block';
        editGSBSection.style.display = 'none';
        
        // 设置评分
        document.querySelectorAll('#editScoreButtons .score-btn').forEach(btn => {
            const btnScore = parseInt(btn.dataset.score);
            btn.classList.toggle('active', btnScore === sample.score);
            btn.onclick = function() {
                document.querySelectorAll('#editScoreButtons .score-btn').forEach(b => b.classList.remove('active'));
                this.classList.add('active');
            };
        });
    }
    
    document.getElementById('rowEditModal').classList.add('show');
}

function hideRowEditModal() {
    document.getElementById('rowEditModal').classList.remove('show');
    editingSampleId = null;
}

function handleEditImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        const preview = document.getElementById('editImagePreview');
        const placeholder = document.getElementById('editImageArea').querySelector('.upload-placeholder');
        preview.src = e.target.result;
        preview.style.display = 'block';
        placeholder.style.display = 'none';
        preview.dataset.base64 = e.target.result;
    };
    reader.readAsDataURL(file);
}


async function saveRowEdit() {
    if (!editingSampleId) return;
    
    const sample = samples.find(s => s.sample_id === editingSampleId);
    if (!sample) return;
    
    // 更新图片
    const preview = document.getElementById('editImagePreview');
    if (preview.dataset.base64) {
        const firstImageKey = Object.keys(sample.variables).find(k => 
            sample.variables[k].type === 'image' || sample.variables[k].type === 'image_url'
        ) || 'IMAGE_STUDENT_ANSWER';
        
        sample.variables[firstImageKey] = { type: 'image', value: preview.dataset.base64 };
    }
    
    // 更新理想回答/参照回答
    const answerValue = document.getElementById('editIdealAnswer').value;
    if (evalMode === 'gsb' || sample.eval_mode === 'gsb') {
        sample.reference_answer = answerValue;
    } else {
        sample.ideal_answer = answerValue;
    }
    
    // 更新评分/GSB
    if (evalMode === 'gsb' || sample.eval_mode === 'gsb') {
        const activeGSBBtn = document.querySelector('#editGSBButtons .gsb-btn.active');
        if (activeGSBBtn) {
            sample.gsb_result = activeGSBBtn.dataset.gsb;
            sample.eval_mode = 'gsb';
        }
    } else {
        const activeScoreBtn = document.querySelector('#editScoreButtons .score-btn.active');
        if (activeScoreBtn) {
            sample.score = parseInt(activeScoreBtn.dataset.score);
            sample.score_source = 'manual';
        }
    }
    
    // 保存到服务器
    if (!editingSampleId.startsWith('temp_')) {
        try {
            await fetch(`/api/prompt-sample/${editingSampleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ideal_answer: sample.ideal_answer,
                    reference_answer: sample.reference_answer,
                    score: sample.score,
                    score_source: sample.score_source,
                    gsb_result: sample.gsb_result,
                    eval_mode: sample.eval_mode
                })
            });
        } catch (error) {
            console.error('保存失败:', error);
        }
    }
    
    hideRowEditModal();
    renderTable();
}

function editIdealAnswer(sampleId) {
    editRow(sampleId);
}

async function deleteSample(sampleId) {
    if (!confirm('确定删除此样本？')) return;
    
    samples = samples.filter(s => s.sample_id !== sampleId);
    renderTable();
    
    if (!sampleId.startsWith('temp_')) {
        fetch(`/api/prompt-sample/${sampleId}`, { method: 'DELETE' });
    }
}

// ========== Modal 关闭 ==========
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        e.target.classList.remove('show');
    }
});


// ========== 新版调试界面功能 ==========
let debugHistory = [];
let debugImageBase64 = null;

// 同步Prompt到调试区域
function syncPromptToDebug() {
    const debugPromptArea = document.getElementById('debugPromptArea');
    if (debugPromptArea) {
        debugPromptArea.value = currentPrompt;
    }
}

// 从调试区域同步Prompt
function syncPromptFromDebug() {
    const debugPromptArea = document.getElementById('debugPromptArea');
    if (debugPromptArea) {
        currentPrompt = debugPromptArea.value;
        document.getElementById('promptEditor').value = currentPrompt;
    }
}

// 处理调试图片上传
function handleDebugImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;
    
    const reader = new FileReader();
    reader.onload = function(e) {
        debugImageBase64 = e.target.result;
        const preview = document.getElementById('debugImagePreview');
        const previewImg = document.getElementById('debugPreviewImg');
        previewImg.src = debugImageBase64;
        preview.style.display = 'inline-block';
    };
    reader.readAsDataURL(file);
}

// 移除调试图片
function removeDebugImage() {
    debugImageBase64 = null;
    document.getElementById('debugImagePreview').style.display = 'none';
    document.getElementById('debugImageInput').value = '';
}

// 清空调试变量
function clearDebugVariables() {
    document.getElementById('debugPromptArea').value = '';
    removeDebugImage();
    document.getElementById('debugResponseBody').innerHTML = '<div class="debug-response-placeholder">点击左侧「生成模型回答」后，大模型的回答将显示在这里</div>';
    document.getElementById('debugScoringSection').style.display = 'none';
}

// 填写变量弹窗
function fillVariables() {
    // 检测Prompt中的变量
    const promptText = document.getElementById('debugPromptArea').value;
    const variables = detectVariables(promptText);
    
    if (variables.length === 0) {
        alert('Prompt中没有检测到变量。请使用 {{变量名}} 格式定义变量。');
        return;
    }
    
    // 显示变量填写提示
    let message = '检测到以下变量:\n\n';
    variables.forEach(v => {
        message += `• {{${v}}}\n`;
    });
    message += '\n请在Prompt文本中直接替换变量值，或上传图片作为图片变量。';
    alert(message);
}

// 更新模型徽章
function updateDebugModelBadge() {
    const badge = document.getElementById('debugModelBadge');
    if (badge) {
        const select = document.getElementById('modelSelect');
        badge.textContent = select.options[select.selectedIndex].text;
    }
}

// 复制模型回答
function copyModelResponse() {
    if (currentModelResponse) {
        navigator.clipboard.writeText(currentModelResponse).then(() => {
            alert('已复制到剪贴板');
        });
    }
}

// 添加到历史记录
function addToDebugHistory(prompt, image, response, score) {
    const historyItem = {
        id: Date.now(),
        prompt: prompt.substring(0, 50) + (prompt.length > 50 ? '...' : ''),
        fullPrompt: prompt,
        image: image,
        response: response,
        score: score,
        timestamp: new Date().toLocaleString()
    };
    
    debugHistory.unshift(historyItem);
    if (debugHistory.length > 20) {
        debugHistory.pop();
    }
    
    renderDebugHistory();
}

// 渲染历史记录
function renderDebugHistory() {
    const container = document.getElementById('debugHistoryList');
    if (!container) return;
    
    if (debugHistory.length === 0) {
        container.innerHTML = '<div class="debug-history-empty">暂无历史记录</div>';
        return;
    }
    
    container.innerHTML = debugHistory.map(item => `
        <div class="debug-history-item" onclick="loadDebugHistory(${item.id})">
            <div class="history-item-icon">
                ${item.image ? `<img src="${item.image}" alt="">` : '<svg viewBox="0 0 24 24" width="20" height="20"><path fill="white" d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/></svg>'}
            </div>
            <div class="history-item-content">
                <div class="history-item-title">${escapeHtmlSimple(item.prompt)}</div>
                <div class="history-item-desc">${item.timestamp}${item.score ? ` · 评分: ${item.score}` : ''}</div>
            </div>
        </div>
    `).join('');
}

function escapeHtmlSimple(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// 加载历史记录
function loadDebugHistory(id) {
    const item = debugHistory.find(h => h.id === id);
    if (!item) return;
    
    document.getElementById('debugPromptArea').value = item.fullPrompt;
    
    if (item.image) {
        debugImageBase64 = item.image;
        document.getElementById('debugPreviewImg').src = item.image;
        document.getElementById('debugImagePreview').style.display = 'inline-block';
    } else {
        removeDebugImage();
    }
    
    if (item.response) {
        document.getElementById('debugResponseBody').innerHTML = marked.parse(item.response);
        currentModelResponse = item.response;
        document.getElementById('debugScoringSection').style.display = 'block';
    }
}

// 重写生成回答函数以支持新界面
async function generateResponse() {
    // 同步调试区域的Prompt
    syncPromptFromDebug();
    
    const btn = document.querySelector('.btn-debug-primary') || document.getElementById('generateBtn');
    const responseDiv = document.getElementById('debugResponseBody') || document.getElementById('modelResponse');
    
    if (!currentPrompt.trim()) {
        const debugPrompt = document.getElementById('debugPromptArea');
        if (debugPrompt && debugPrompt.value.trim()) {
            currentPrompt = debugPrompt.value;
        } else {
            alert('请先输入 Prompt');
            return;
        }
    }
    
    // 构建变量
    const variables = {};
    if (debugImageBase64) {
        variables['IMAGE'] = { type: 'image', value: debugImageBase64 };
    }
    
    // 更新模型徽章
    updateDebugModelBadge();
    
    btn.disabled = true;
    const originalText = btn.innerHTML;
    btn.innerHTML = '<span class="loading-spinner"></span> 生成中...';
    responseDiv.innerHTML = '<div class="loading-hint">正在生成回答...</div>';
    
    try {
        const response = await fetch('/api/prompt-eval/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: currentPrompt,
                model: currentModel,
                variables: variables
            })
        });
        
        if (!response.ok) throw new Error('生成失败');
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let result = '';
        
        responseDiv.innerHTML = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') continue;
                    try {
                        const json = JSON.parse(data);
                        if (json.content) {
                            result += json.content;
                            responseDiv.innerHTML = marked.parse(result);
                        }
                    } catch (e) {}
                }
            }
        }
        
        currentModelResponse = result;
        
        // 显示评分区域
        const scoringSection = document.getElementById('debugScoringSection');
        if (scoringSection) {
            scoringSection.style.display = 'block';
        }
        
        // 添加到历史记录
        addToDebugHistory(currentPrompt, debugImageBase64, result, null);
        
    } catch (error) {
        responseDiv.innerHTML = `<div class="error-hint">生成失败: ${error.message}</div>`;
    } finally {
        btn.disabled = false;
        btn.innerHTML = originalText;
    }
}

// 初始化调试评分按钮
function initDebugScoreButtons() {
    document.querySelectorAll('#debugScoreButtons .score-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('#debugScoreButtons .score-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentScore = parseInt(this.dataset.score);
        });
    });
}

// 在DOMContentLoaded中添加初始化
document.addEventListener('DOMContentLoaded', function() {
    initDebugScoreButtons();
    
    // 同步Prompt编辑器和调试区域
    const promptEditor = document.getElementById('promptEditor');
    const debugPromptArea = document.getElementById('debugPromptArea');
    
    if (promptEditor && debugPromptArea) {
        promptEditor.addEventListener('input', function() {
            debugPromptArea.value = this.value;
        });
        
        debugPromptArea.addEventListener('input', function() {
            promptEditor.value = this.value;
            currentPrompt = this.value;
        });
    }
});
