/**
 * 知识点类题生成 - 前端JavaScript
 * 优化版：每步可导出、每题一个知识点、并行生成类题
 */

let currentTaskId = null;
let currentStep = 1;
let parsedQuestions = [];
let uniqueKnowledgePoints = [];
let similarQuestions = [];

// 优化后的提示词模板
const DEFAULT_PROMPTS = {
    parse: `你是一个专业的作业识别助手。请仔细分析这张作业图片，识别其中的所有题目。

【输出格式】JSON数组，每道题一个对象：
[
    {
        "content": "完整题目内容，包括题号、选项、条件等",
        "subject": "数学",
        "question_type": "选择题",
        "difficulty": "中等"
    }
]

【字段说明】
- content: 题目完整内容，保留原始格式，数学公式用LaTeX表示
- subject: 学科（数学/物理/化学/语文/英语/生物/地理/历史/政治）
- question_type: 题型（选择题/填空题/计算题/证明题/简答题/应用题）
- difficulty: 难度（简单/中等/困难）

【重要要求】
1. 每道题必须单独识别，不要合并
2. 保留题目的完整信息，包括所有选项和条件
3. 只输出JSON数组，不要任何解释文字`,

    extract: `你是一个专业的教育知识点分析专家。请分析以下题目，提取其核心知识点。

【题目信息】
内容：{content}
学科：{subject}

【输出格式】只输出一个知识点对象：
{
    "primary": "一级知识点",
    "secondary": "二级知识点详细描述",
    "solution_approach": "解题思路"
}

【字段说明】
- primary: 一级知识点，精炼概括，不超过10个字
- secondary: 二级知识点，详细描述具体考查内容
- solution_approach: 解题思路，包含解题步骤、关键公式

【重要要求】
1. 每道题只提取一个最核心的知识点
2. 一级知识点必须精炼
3. 只输出JSON对象，不要任何解释文字`,

    generate: `你是一个专业的题目生成专家。请根据以下知识点信息，生成{count}道类似的练习题。

【知识点信息】
一级知识点：{primary}
二级知识点：{secondary}
解题思路：{solution_approach}
难度要求：{difficulty}
题型要求：{type}

【输出格式】JSON数组：
[
    {
        "primary": "一级知识点",
        "secondary": "二级知识点",
        "content": "题目内容",
        "answer": "标准答案",
        "solution_steps": "详细解题步骤"
    }
]

【重要要求】
1. 题目必须考查相同的知识点
2. 每道题都要包含primary和secondary字段
3. 只输出JSON数组，不要任何解释文字`,

    verify: `你是一个专业的数学教育专家和审题专家。请仔细校验以下题目的准确性和解题步骤的合理性。

【待校验题目】
题目内容：{content}
答案：{answer}
解题步骤：{solution_steps}

【校验任务】
1. 检查题目内容是否完整、表述是否清晰
2. 验证答案是否正确
3. 检查解题步骤是否合理、逻辑是否清晰
4. 如有错误或可优化之处，请修正

【输出格式】JSON对象：
{
    "is_correct": true或false,
    "issues": ["发现的问题1", "发现的问题2"],
    "content": "优化后的题目内容（如无需修改则保持原样）",
    "answer": "正确的答案",
    "solution_steps": "优化后的解题步骤（精简、清晰、分步骤）"
}

【重要要求】
1. 解题步骤要精简，每步一行，用数字编号
2. 去除冗余的推导过程，保留关键步骤
3. 确保答案与解题步骤一致
4. 只输出JSON对象，不要任何解释文字`
};

let PROMPTS = loadPrompts();

function loadPrompts() {
    const saved = localStorage.getItem('knowledge_agent_prompts_v2');
    if (saved) {
        try { return JSON.parse(saved); } catch (e) {}
    }
    return { ...DEFAULT_PROMPTS };
}

function savePromptsToStorage() {
    localStorage.setItem('knowledge_agent_prompts_v2', JSON.stringify(PROMPTS));
}

// DOM元素
const uploadZone = document.getElementById('uploadZone');
const fileInput = document.getElementById('fileInput');
const previewList = document.getElementById('previewList');
const startParseBtn = document.getElementById('startParseBtn');
const confirmParseBtn = document.getElementById('confirmParseBtn');
const startGenerateBtn = document.getElementById('startGenerateBtn');
const goExportBtn = document.getElementById('goExportBtn');
const thresholdSlider = document.getElementById('thresholdSlider');
const thresholdValue = document.getElementById('thresholdValue');

// 初始化
document.addEventListener('DOMContentLoaded', () => {
    initUploadZone();
    initModelSelectors();
    initThresholdSlider();
    initEventListeners();
});

// 返回导航
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}

function initUploadZone() {
    uploadZone.addEventListener('click', () => fileInput.click());
    uploadZone.addEventListener('dragover', (e) => { e.preventDefault(); uploadZone.classList.add('dragover'); });
    uploadZone.addEventListener('dragleave', () => uploadZone.classList.remove('dragover'));
    uploadZone.addEventListener('drop', (e) => { e.preventDefault(); uploadZone.classList.remove('dragover'); handleFiles(e.dataTransfer.files); });
    fileInput.addEventListener('change', (e) => handleFiles(e.target.files));
}

async function handleFiles(files) {
    if (!files.length) return;
    const formData = new FormData();
    for (const file of files) formData.append('files', file);
    
    try {
        const response = await fetch('/api/knowledge-agent/upload', { method: 'POST', body: formData });
        const result = await response.json();
        if (result.success) {
            currentTaskId = result.task_id;
            displayPreviews(result.images);
            startParseBtn.disabled = false;
            document.getElementById('autoRunBtn').disabled = false;
            if (result.errors.length > 0) alert('部分文件上传失败：\n' + result.errors.map(e => `${e.filename}: ${e.error}`).join('\n'));
        } else {
            alert('上传失败：' + result.error);
        }
    } catch (error) {
        alert('上传出错：' + error.message);
    }
}

function displayPreviews(images) {
    previewList.innerHTML = images.map(img => `
        <div class="preview-item" data-id="${img.id}">
            <img src="${img.preview_url}" alt="${img.filename}">
            <div class="preview-name">${img.filename}</div>
            <button class="preview-remove" onclick="removePreview('${img.id}')">×</button>
        </div>
    `).join('');
}

function removePreview(id) {
    const item = document.querySelector(`.preview-item[data-id="${id}"]`);
    if (item) item.remove();
    if (previewList.children.length === 0) startParseBtn.disabled = true;
}

async function initModelSelectors() {
    try {
        const response = await fetch('/api/knowledge-agent/models');
        const result = await response.json();
        if (result.success) {
            const { models, preferences } = result;
            document.getElementById('multimodalModel').innerHTML = models.multimodal.map(m => 
                `<option value="${m.name}" ${m.name === preferences.multimodal_model ? 'selected' : ''}>${m.desc}</option>`
            ).join('');
            document.getElementById('textModel').innerHTML = models.text_generation.map(m => 
                `<option value="${m.name}" ${m.name === preferences.text_model ? 'selected' : ''}>${m.desc}</option>`
            ).join('');
        }
    } catch (error) { console.error('加载模型列表失败:', error); }
}

function initThresholdSlider() {
    thresholdSlider.addEventListener('input', () => thresholdValue.textContent = thresholdSlider.value);
}

function initEventListeners() {
    startParseBtn.addEventListener('click', startParse);
    confirmParseBtn.addEventListener('click', () => goToStep(3));
    startGenerateBtn.addEventListener('click', startGenerate);
    document.getElementById('startVerifyBtn').addEventListener('click', startVerify);
    goExportBtn.addEventListener('click', () => goToStep(6));
    document.getElementById('autoRunBtn').addEventListener('click', startAutoRun);
}

function togglePrompt(id) {
    document.getElementById(id).classList.toggle('show');
}

function goToStep(step) {
    document.querySelectorAll('.step').forEach((el, idx) => {
        el.classList.remove('active', 'completed');
        if (idx + 1 < step) el.classList.add('completed');
        if (idx + 1 === step) el.classList.add('active');
    });
    document.querySelectorAll('.step-panel').forEach((el, idx) => {
        el.classList.remove('active');
        if (idx + 1 === step) el.classList.add('active');
    });
    currentStep = step;
    if (step === 3) performDedupe();
}

function safeJsonParse(text) {
    try { return JSON.parse(text); } catch (e) {
        let fixed = text.replace(/\\([^"\\/bfnrtu])/g, '\\\\$1');
        try { return JSON.parse(fixed); } catch (e2) {
            fixed = text.replace(/\\/g, '\\\\').replace(/\\\\\"/g, '\\"').replace(/\\\\n/g, '\\n');
            try { return JSON.parse(fixed); } catch (e3) { throw e; }
        }
    }
}

function generateId() { return Math.random().toString(36).substr(2, 8); }
function escapeHtml(text) { if (!text) return ''; const div = document.createElement('div'); div.textContent = text; return div.innerHTML; }

// ========== 解析流程 ==========
async function startParse() {
    if (!currentTaskId) { alert('请先上传图片'); return; }
    
    const multimodalModel = document.getElementById('multimodalModel').value;
    const textModel = document.getElementById('textModel').value;
    
    document.getElementById('parsePrompt').textContent = PROMPTS.parse;
    document.getElementById('parsePrompt').classList.add('show');
    
    const streamEl = document.getElementById('parseStream');
    streamEl.textContent = '';
    const statusEl = document.getElementById('parseStatus');
    statusEl.textContent = '正在识别题目...';
    statusEl.className = 'stream-status loading';
    
    goToStep(2);
    
    try {
        const response = await fetch('/api/knowledge-agent/parse-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, multimodal_model: multimodalModel, prompt: PROMPTS.parse })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let imageResponses = {};
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'progress') statusEl.textContent = data.message;
                            else if (data.type === 'chunk') { streamEl.textContent += data.content; streamEl.scrollTop = streamEl.scrollHeight; }
                            else if (data.type === 'image_done') { imageResponses[data.image] = data.response; streamEl.textContent += '\n\n--- 图片解析完成 ---\n\n'; }
                            else if (data.type === 'error') streamEl.textContent += `\n[错误: ${data.error}]\n`;
                        } catch (e) {}
                    }
                }
            }
            if (done) break;
        }
        
        if (Object.keys(imageResponses).length > 0) {
            statusEl.textContent = '正在提取知识点...';
            await extractKnowledgePoints(imageResponses, textModel, streamEl, statusEl);
        } else {
            statusEl.textContent = '未能解析图片';
            statusEl.className = 'stream-status error';
        }
    } catch (error) {
        statusEl.textContent = '错误';
        statusEl.className = 'stream-status error';
        streamEl.textContent += '\n请求出错: ' + error.message;
    }
}

async function extractKnowledgePoints(imageResponses, textModel, streamEl, statusEl) {
    let questions = [];
    
    for (const [image, response] of Object.entries(imageResponses)) {
        try {
            const jsonMatch = response.match(/\[[\s\S]*\]/);
            if (jsonMatch) {
                const parsed = safeJsonParse(jsonMatch[0]);
                if (Array.isArray(parsed)) {
                    parsed.forEach(q => questions.push({ ...q, image_source: image, knowledge_points: [] }));
                }
            } else {
                const objMatch = response.match(/\{[\s\S]*\}/);
                if (objMatch) {
                    const parsed = safeJsonParse(objMatch[0]);
                    questions.push({ ...parsed, image_source: image, knowledge_points: [] });
                }
            }
        } catch (e) {
            console.error('JSON解析失败:', e);
            questions.push({ content: response, subject: '', question_type: '简答题', difficulty: '中等', image_source: image, knowledge_points: [] });
        }
    }
    
    if (questions.length === 0) { statusEl.textContent = '未识别到题目'; statusEl.className = 'stream-status error'; return; }
    
    streamEl.textContent += `\n\n=== 开始提取知识点（共${questions.length}道题）===\n\n`;
    
    let questionResponses = {};
    try {
        const response = await fetch('/api/knowledge-agent/extract-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, text_model: textModel, prompt: PROMPTS.extract, questions: questions })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'progress') statusEl.textContent = data.message;
                            else if (data.type === 'chunk') { streamEl.textContent += data.content; streamEl.scrollTop = streamEl.scrollHeight; }
                            else if (data.type === 'question_done') { questionResponses[data.question_idx] = data.response; streamEl.textContent += '\n\n--- 知识点提取完成 ---\n\n'; }
                            else if (data.type === 'error') streamEl.textContent += `\n[错误: ${data.error}]\n`;
                        } catch (e) {}
                    }
                }
            }
            if (done) break;
        }
    } catch (error) {
        statusEl.textContent = '知识点提取失败';
        statusEl.className = 'stream-status error';
        return;
    }
    
    // 解析知识点 - 每道题只有一个知识点
    for (const [idx, resp] of Object.entries(questionResponses)) {
        try {
            // 优先尝试解析单个对象
            const objMatch = resp.match(/\{[\s\S]*\}/);
            if (objMatch) {
                const kp = safeJsonParse(objMatch[0]);
                questions[idx].knowledge_points = [{
                    id: generateId(),
                    primary: (kp.primary || '').substring(0, 10),
                    secondary: kp.secondary || '',
                    analysis: kp.solution_approach || kp.analysis || ''
                }];
            }
        } catch (e) {
            questions[idx].knowledge_points = [{ id: generateId(), primary: '解析失败', secondary: '', analysis: e.message }];
        }
    }
    
    parsedQuestions = questions.map(q => ({ id: generateId(), ...q }));
    await saveParseResults();
    
    statusEl.textContent = `完成（${parsedQuestions.length}道题）`;
    statusEl.className = 'stream-status done';
    
    displayParseResults(parsedQuestions);
    document.getElementById('parseResultSection').style.display = 'block';
    confirmParseBtn.disabled = false;
}

async function saveParseResults() {
    try {
        await fetch('/api/knowledge-agent/save-parse', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, questions: parsedQuestions })
        });
    } catch (e) { console.error('保存解析结果失败:', e); }
}

function displayParseResults(questions) {
    const tbody = document.querySelector('#parseResultTable tbody');
    tbody.innerHTML = questions.map((q, idx) => `
        <tr>
            <td>${idx + 1}</td>
            <td class="content-cell" title="${escapeHtml(q.content)}">${escapeHtml(q.content)}</td>
            <td>${q.subject || '-'}</td>
            <td>${q.question_type || '-'}</td>
            <td>${q.difficulty || '-'}</td>
            <td>
                ${(q.knowledge_points || []).map(kp => `
                    <div class="kp-item">
                        <strong>${escapeHtml(kp.primary)}</strong>
                        <div class="kp-secondary">${escapeHtml(kp.secondary)}</div>
                    </div>
                `).join('')}
            </td>
        </tr>
    `).join('');
}

// ========== 去重 ==========
async function performDedupe() {
    const threshold = parseFloat(thresholdSlider.value);
    const list = document.getElementById('knowledgeList');
    const dedupeInfo = document.getElementById('dedupeInfo');
    
    // 显示加载状态
    list.innerHTML = '<div class="loading-state">正在智能去重中，请稍候...</div>';
    dedupeInfo.innerHTML = '正在分析知识点...';
    
    try {
        const response = await fetch('/api/knowledge-agent/dedupe', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, threshold: threshold, use_llm: true })
        });
        const result = await response.json();
        if (result.success) {
            uniqueKnowledgePoints = result.unique_points;
            displayKnowledgePoints(uniqueKnowledgePoints, result.dedupe_results);
            startGenerateBtn.disabled = false;
        } else {
            list.innerHTML = '<div class="error-state">去重失败：' + escapeHtml(result.error) + '</div>';
            dedupeInfo.innerHTML = '去重失败';
        }
    } catch (error) {
        list.innerHTML = '<div class="error-state">去重出错：' + escapeHtml(error.message) + '</div>';
        dedupeInfo.innerHTML = '去重出错';
    }
}

function displayKnowledgePoints(points, dedupeResults) {
    const list = document.getElementById('knowledgeList');
    list.innerHTML = points.map((kp, idx) => `
        <div class="knowledge-item">
            <div class="knowledge-item-header">
                <input type="checkbox" id="kp_${kp.id}" checked>
                <label for="kp_${kp.id}">
                    <span class="kp-primary">${escapeHtml(kp.primary)}</span>
                </label>
            </div>
            <div class="knowledge-item-body">
                <div class="kp-secondary">${escapeHtml(kp.secondary)}</div>
                <div class="kp-analysis">${escapeHtml(kp.analysis)}</div>
            </div>
        </div>
    `).join('');
    
    const mergedCount = dedupeResults.filter(r => r.is_merged).length;
    document.getElementById('dedupeInfo').innerHTML = `共 ${points.length} 个唯一知识点，合并了 ${mergedCount} 个重复项`;
}

// ========== 生成类题（并行） ==========
async function startGenerate() {
    const textModel = document.getElementById('textModel').value;
    const count = parseInt(document.getElementById('questionCount').value);
    
    const sampleKp = uniqueKnowledgePoints[0] || { primary: '示例', secondary: '示例', analysis: '示例' };
    document.getElementById('generatePrompt').textContent = PROMPTS.generate
        .replace('{primary}', sampleKp.primary)
        .replace('{secondary}', sampleKp.secondary)
        .replace('{solution_approach}', sampleKp.analysis)
        .replace('{difficulty}', '中等')
        .replace('{type}', '简答题')
        .replace('{count}', count);
    document.getElementById('generatePrompt').classList.add('show');
    
    const streamEl = document.getElementById('generateStream');
    streamEl.textContent = '';
    const statusEl = document.getElementById('generateStatus');
    statusEl.textContent = '正在并行生成类题...';
    statusEl.className = 'stream-status loading';
    
    goToStep(4);
    
    // 准备知识点数据
    const kpData = uniqueKnowledgePoints.map(kp => {
        let difficulty = '中等', questionType = '简答题';
        for (const q of parsedQuestions) {
            for (const qkp of (q.knowledge_points || [])) {
                if (qkp.id === kp.id) { difficulty = q.difficulty; questionType = q.question_type; break; }
            }
        }
        return { id: kp.id, primary: kp.primary, secondary: kp.secondary, analysis: kp.analysis, difficulty, question_type: questionType };
    });
    
    try {
        const response = await fetch('/api/knowledge-agent/generate-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, text_model: textModel, prompt: PROMPTS.generate, knowledge_points: kpData, count: count })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let kpResponses = {};
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'progress') statusEl.textContent = data.message;
                            else if (data.type === 'kp_done') {
                                kpResponses[data.kp_idx] = { kp_name: data.kp_name, response: data.response };
                                streamEl.textContent += `\n[${data.kp_name}] 生成完成\n`;
                                streamEl.scrollTop = streamEl.scrollHeight;
                            }
                            else if (data.type === 'error') streamEl.textContent += `\n[错误: ${data.error}]\n`;
                            else if (data.type === 'done') {
                                // 解析所有类题结果
                                similarQuestions = [];
                                for (const [idx, resp] of Object.entries(kpResponses)) {
                                    const kp = kpData[idx];
                                    try {
                                        const jsonMatch = resp.response.match(/\[[\s\S]*\]/);
                                        if (jsonMatch) {
                                            const questions = safeJsonParse(jsonMatch[0]);
                                            questions.forEach(q => {
                                                similarQuestions.push({
                                                    id: generateId(),
                                                    knowledge_point_id: kp.id,
                                                    primary: q.primary || kp.primary,
                                                    secondary: q.secondary || kp.secondary,
                                                    content: q.content || '',
                                                    answer: q.answer || '',
                                                    solution_steps: q.solution_steps || '',
                                                    difficulty: kp.difficulty,
                                                    question_type: kp.question_type
                                                });
                                            });
                                        }
                                    } catch (e) {
                                        similarQuestions.push({ id: generateId(), knowledge_point_id: kp.id, primary: kp.primary, secondary: kp.secondary, content: '生成失败: ' + e.message, answer: '', solution_steps: '', difficulty: kp.difficulty, question_type: kp.question_type });
                                    }
                                }
                                await saveSimilarResults();
                                statusEl.textContent = `完成（${similarQuestions.length}道类题）`;
                                statusEl.className = 'stream-status done';
                                displaySimilarQuestions(similarQuestions);
                                document.getElementById('startVerifyBtn').disabled = false;
                            }
                        } catch (e) {}
                    }
                }
            }
            if (done) break;
        }
    } catch (error) {
        statusEl.textContent = '错误';
        statusEl.className = 'stream-status error';
        streamEl.textContent += '\n请求出错: ' + error.message;
    }
}

async function saveSimilarResults() {
    try {
        await fetch('/api/knowledge-agent/save-similar', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, similar_questions: similarQuestions })
        });
    } catch (e) { console.error('保存类题结果失败:', e); }
}

function displaySimilarQuestions(questions) {
    const list = document.getElementById('similarList');
    list.innerHTML = questions.map((sq, idx) => `
        <div class="similar-card" data-id="${sq.id}">
            <div class="similar-header">
                <span class="similar-number">类题 ${idx + 1}</span>
                <span class="similar-kp">${escapeHtml(sq.primary)} - ${escapeHtml(sq.secondary)}</span>
                <span class="similar-meta">${sq.difficulty} | ${sq.question_type}</span>
            </div>
            <div class="similar-section">
                <label>题目</label>
                <div class="similar-text" contenteditable="true" data-field="content">${escapeHtml(sq.content)}</div>
            </div>
            <div class="similar-section">
                <label>答案</label>
                <div class="similar-text" contenteditable="true" data-field="answer">${escapeHtml(sq.answer)}</div>
            </div>
            <div class="similar-section">
                <label>解题步骤</label>
                <div class="similar-text" contenteditable="true" data-field="solution_steps">${escapeHtml(sq.solution_steps)}</div>
            </div>
            <button class="similar-save" onclick="saveEdit('${sq.id}')">保存修改</button>
        </div>
    `).join('');
}

async function saveEdit(questionId) {
    const card = document.querySelector(`.similar-card[data-id="${questionId}"]`);
    const updates = {};
    card.querySelectorAll('[data-field]').forEach(el => updates[el.dataset.field] = el.textContent);
    
    try {
        const response = await fetch('/api/knowledge-agent/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: currentTaskId, question_id: questionId, updates: updates })
        });
        const result = await response.json();
        if (result.success) showToast('保存成功');
        else alert('保存失败：' + result.error);
    } catch (error) { alert('保存出错：' + error.message); }
}

// ========== 导出 ==========
function exportResult(type) {
    if (!currentTaskId) { alert('没有可导出的数据'); return; }
    window.location.href = `/api/knowledge-agent/export/${type}?task_id=${currentTaskId}`;
}

function startNewTask() {
    currentTaskId = null;
    parsedQuestions = [];
    uniqueKnowledgePoints = [];
    similarQuestions = [];
    previewList.innerHTML = '';
    startParseBtn.disabled = true;
    confirmParseBtn.disabled = true;
    goExportBtn.disabled = true;
    document.getElementById('parseStream').textContent = '';
    document.getElementById('generateStream').textContent = '';
    document.getElementById('parseResultSection').style.display = 'none';
    goToStep(1);
}

// ========== 设置功能 ==========
function showSettings() {
    document.getElementById('editParsePrompt').value = PROMPTS.parse;
    document.getElementById('editExtractPrompt').value = PROMPTS.extract;
    document.getElementById('editGeneratePrompt').value = PROMPTS.generate;
    document.getElementById('editVerifyPrompt').value = PROMPTS.verify;
    document.getElementById('settingsModal').classList.add('show');
}

function hideSettings() {
    document.getElementById('settingsModal').classList.remove('show');
}

function switchSettingsTab(tab) {
    document.querySelectorAll('.settings-tab').forEach(btn => {
        btn.classList.remove('active');
        if (btn.dataset.tab === tab) btn.classList.add('active');
    });
    document.querySelectorAll('.settings-panel').forEach(panel => panel.classList.remove('active'));
    const panelId = 'settings' + tab.charAt(0).toUpperCase() + tab.slice(1);
    document.getElementById(panelId).classList.add('active');
}

function savePrompts() {
    PROMPTS.parse = document.getElementById('editParsePrompt').value;
    PROMPTS.extract = document.getElementById('editExtractPrompt').value;
    PROMPTS.generate = document.getElementById('editGeneratePrompt').value;
    PROMPTS.verify = document.getElementById('editVerifyPrompt').value;
    savePromptsToStorage();
    hideSettings();
    showToast('提示词设置已保存');
}

function resetPrompts() {
    if (confirm('确定要恢复默认提示词吗？')) {
        PROMPTS = { ...DEFAULT_PROMPTS };
        savePromptsToStorage();
        document.getElementById('editParsePrompt').value = PROMPTS.parse;
        document.getElementById('editExtractPrompt').value = PROMPTS.extract;
        document.getElementById('editGeneratePrompt').value = PROMPTS.generate;
        document.getElementById('editVerifyPrompt').value = PROMPTS.verify;
        showToast('已恢复默认提示词');
    }
}

function showToast(message) {
    let toast = document.getElementById('toast');
    if (!toast) {
        toast = document.createElement('div');
        toast.id = 'toast';
        toast.className = 'toast';
        document.body.appendChild(toast);
    }
    toast.textContent = message;
    toast.classList.add('show');
    setTimeout(() => toast.classList.remove('show'), 2000);
}

document.addEventListener('click', (e) => {
    const modal = document.getElementById('settingsModal');
    if (e.target === modal) hideSettings();
});

// ========== 校验功能 ==========
async function startVerify() {
    const streamEl = document.getElementById('verifyStream');
    streamEl.textContent = '';
    const statusEl = document.getElementById('verifyStatus');
    statusEl.textContent = '正在校验类题...';
    statusEl.className = 'stream-status loading';
    
    // 显示校验提示词
    document.getElementById('verifyPrompt').textContent = PROMPTS.verify;
    document.getElementById('verifyPrompt').classList.add('show');
    
    goToStep(5);
    
    const progressEl = document.getElementById('verifyProgress');
    progressEl.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: 0%"></div></div><div class="progress-text">0 / ${similarQuestions.length}</div>`;
    
    try {
        const response = await fetch('/api/knowledge-agent/verify-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                prompt: PROMPTS.verify,
                questions: similarQuestions
            })
        });
        
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        let verifiedCount = 0;
        
        while (true) {
            const { done, value } = await reader.read();
            if (value) {
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const data = JSON.parse(line.slice(6));
                            if (data.type === 'progress') {
                                statusEl.textContent = data.message;
                            } else if (data.type === 'chunk') {
                                streamEl.textContent += data.content;
                                streamEl.scrollTop = streamEl.scrollHeight;
                            } else if (data.type === 'question_verified') {
                                verifiedCount++;
                                const percent = (verifiedCount / similarQuestions.length * 100).toFixed(0);
                                progressEl.innerHTML = `<div class="progress-bar"><div class="progress-fill" style="width: ${percent}%"></div></div><div class="progress-text">${verifiedCount} / ${similarQuestions.length}</div>`;
                                
                                // 更新类题数据
                                const idx = data.question_idx;
                                if (data.result && similarQuestions[idx]) {
                                    similarQuestions[idx].content = data.result.content || similarQuestions[idx].content;
                                    similarQuestions[idx].answer = data.result.answer || similarQuestions[idx].answer;
                                    similarQuestions[idx].solution_steps = data.result.solution_steps || similarQuestions[idx].solution_steps;
                                    similarQuestions[idx].is_correct = data.result.is_correct;
                                    similarQuestions[idx].issues = data.result.issues || [];
                                }
                                
                                streamEl.textContent += `\n--- 类题 ${idx + 1} 校验完成 ---\n\n`;
                            } else if (data.type === 'error') {
                                streamEl.textContent += `\n[错误: ${data.error}]\n`;
                            } else if (data.type === 'done') {
                                await saveSimilarResults();
                                statusEl.textContent = `校验完成（${verifiedCount}道）`;
                                statusEl.className = 'stream-status done';
                                displayVerifiedQuestions(similarQuestions);
                                goExportBtn.disabled = false;
                            }
                        } catch (e) {}
                    }
                }
            }
            if (done) break;
        }
    } catch (error) {
        statusEl.textContent = '校验出错';
        statusEl.className = 'stream-status error';
        streamEl.textContent += '\n请求出错: ' + error.message;
    }
}

function displayVerifiedQuestions(questions) {
    const list = document.getElementById('verifiedList');
    list.innerHTML = questions.map((sq, idx) => `
        <div class="verified-card ${sq.is_correct === false ? 'has-issues' : ''}" data-id="${sq.id}">
            <div class="verified-header">
                <span class="verified-number">类题 ${idx + 1}</span>
                <span class="verified-status ${sq.is_correct === false ? 'status-warning' : 'status-ok'}">${sq.is_correct === false ? '已修正' : '正确'}</span>
                <span class="similar-kp">${escapeHtml(sq.primary)}</span>
            </div>
            ${sq.issues && sq.issues.length > 0 ? `<div class="verified-issues"><strong>发现问题：</strong>${sq.issues.join('；')}</div>` : ''}
            <div class="similar-section">
                <label>题目</label>
                <div class="similar-text">${escapeHtml(sq.content)}</div>
            </div>
            <div class="similar-section">
                <label>答案</label>
                <div class="similar-text">${escapeHtml(sq.answer)}</div>
            </div>
            <div class="similar-section">
                <label>解题步骤</label>
                <div class="similar-text solution-steps">${escapeHtml(sq.solution_steps)}</div>
            </div>
        </div>
    `).join('');
}


// ========== 一键自动执行 ==========
let autoRunning = false;
let autoStartTime = null;
let totalTokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };

const AUTO_STEPS = [
    { id: 'parse', name: '解析题目', desc: '识别图片中的题目' },
    { id: 'extract', name: '提取知识点', desc: '分析每道题的知识点' },
    { id: 'dedupe', name: '知识点去重', desc: '合并相似知识点' },
    { id: 'generate', name: '生成类题', desc: '根据知识点生成练习题' },
    { id: 'verify', name: '校验优化', desc: '校验并优化类题' },
    { id: 'export', name: '完成', desc: '准备导出结果' }
];

function createAutoProgressPanel() {
    const panel = document.createElement('div');
    panel.id = 'autoProgressPanel';
    panel.className = 'auto-progress-panel';
    panel.innerHTML = `
        <div class="auto-progress-title">
            <div class="spinner"></div>
            <span>自动执行中...</span>
        </div>
        <div class="auto-token-stats" id="autoTokenStats">
            <span class="token-label">Token消耗：</span>
            <span class="token-value" id="tokenTotal">0</span>
            <span class="token-detail">(<span id="tokenPrompt">0</span> + <span id="tokenCompletion">0</span>)</span>
        </div>
        <div class="auto-steps">
            ${AUTO_STEPS.map((step, idx) => `
                <div class="auto-step" data-step="${step.id}">
                    <div class="auto-step-icon">${idx + 1}</div>
                    <div class="auto-step-content">
                        <div class="auto-step-name">${step.name}</div>
                        <div class="auto-step-status">${step.desc}</div>
                    </div>
                    <div class="auto-step-tokens"></div>
                    <div class="auto-step-time"></div>
                </div>
            `).join('')}
        </div>
        <div class="auto-log" id="autoLog"></div>
    `;
    return panel;
}

function updateTokenDisplay() {
    const totalEl = document.getElementById('tokenTotal');
    const promptEl = document.getElementById('tokenPrompt');
    const completionEl = document.getElementById('tokenCompletion');
    if (totalEl) totalEl.textContent = totalTokenUsage.total_tokens.toLocaleString();
    if (promptEl) promptEl.textContent = totalTokenUsage.prompt_tokens.toLocaleString();
    if (completionEl) completionEl.textContent = totalTokenUsage.completion_tokens.toLocaleString();
}

function updateStepTokens(stepId, tokens) {
    const stepEl = document.querySelector(`.auto-step[data-step="${stepId}"]`);
    if (!stepEl) return;
    const tokensEl = stepEl.querySelector('.auto-step-tokens');
    if (tokensEl && tokens > 0) {
        tokensEl.textContent = `${tokens.toLocaleString()} tokens`;
    }
}

function updateAutoStep(stepId, status, message) {
    const stepEl = document.querySelector(`.auto-step[data-step="${stepId}"]`);
    if (!stepEl) return;
    
    stepEl.classList.remove('active', 'completed', 'error');
    stepEl.classList.add(status);
    
    const statusEl = stepEl.querySelector('.auto-step-status');
    if (message) statusEl.textContent = message;
    
    const timeEl = stepEl.querySelector('.auto-step-time');
    if (status === 'completed' || status === 'error') {
        const elapsed = ((Date.now() - autoStartTime) / 1000).toFixed(1);
        timeEl.textContent = `${elapsed}s`;
    }
}

function addAutoLog(message, type = 'info') {
    const logEl = document.getElementById('autoLog');
    if (!logEl) return;
    
    const time = new Date().toLocaleTimeString();
    const entry = document.createElement('div');
    entry.className = `auto-log-entry ${type}`;
    entry.textContent = `[${time}] ${message}`;
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
}

async function startAutoRun() {
    if (!currentTaskId) {
        alert('请先上传图片');
        return;
    }
    
    if (autoRunning) {
        alert('自动执行正在进行中');
        return;
    }
    
    autoRunning = true;
    autoStartTime = Date.now();
    totalTokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
    
    // 禁用按钮
    document.getElementById('autoRunBtn').disabled = true;
    startParseBtn.disabled = true;
    
    // 创建进度面板
    const contentArea = document.querySelector('.content-area');
    const existingPanel = document.getElementById('autoProgressPanel');
    if (existingPanel) existingPanel.remove();
    
    const progressPanel = createAutoProgressPanel();
    contentArea.insertBefore(progressPanel, contentArea.firstChild);
    
    // 隐藏所有步骤面板
    document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
    
    const multimodalModel = document.getElementById('multimodalModel').value;
    const textModel = document.getElementById('textModel').value;
    const threshold = parseFloat(thresholdSlider.value);
    const count = parseInt(document.getElementById('questionCount').value);
    
    let stepTokens = { parse: 0, extract: 0, dedupe: 0, generate: 0, verify: 0 };
    
    try {
        // ===== 步骤1: 解析题目 =====
        updateAutoStep('parse', 'active', '正在识别图片中的题目...');
        addAutoLog('开始解析图片', 'info');
        
        const parseResult = await autoParseImages(multimodalModel);
        if (!parseResult.success) throw new Error(parseResult.error || '解析失败');
        
        stepTokens.parse = parseResult.tokens || 0;
        updateStepTokens('parse', stepTokens.parse);
        updateAutoStep('parse', 'completed', `识别到 ${parseResult.imageCount} 张图片`);
        addAutoLog(`图片解析完成，消耗 ${stepTokens.parse.toLocaleString()} tokens`, 'success');
        
        // ===== 步骤2: 提取知识点 =====
        updateAutoStep('extract', 'active', '正在提取知识点...');
        addAutoLog('开始提取知识点', 'info');
        
        const extractResult = await autoExtractKnowledge(textModel, parseResult.imageResponses);
        if (!extractResult.success) throw new Error(extractResult.error || '知识点提取失败');
        
        parsedQuestions = extractResult.questions;
        await saveParseResults();
        
        stepTokens.extract = extractResult.tokens || 0;
        updateStepTokens('extract', stepTokens.extract);
        updateAutoStep('extract', 'completed', `提取了 ${parsedQuestions.length} 道题的知识点`);
        addAutoLog(`知识点提取完成，消耗 ${stepTokens.extract.toLocaleString()} tokens`, 'success');
        
        // 更新步骤指示器
        goToStepSilent(2);
        
        // ===== 步骤3: 知识点去重 =====
        updateAutoStep('dedupe', 'active', '正在智能合并相似知识点...');
        addAutoLog('开始LLM智能去重', 'info');
        
        const dedupeResult = await autoDedupeKnowledge(threshold);
        if (!dedupeResult.success) throw new Error(dedupeResult.error || '去重失败');
        
        uniqueKnowledgePoints = dedupeResult.unique_points;
        
        stepTokens.dedupe = dedupeResult.tokens || 0;
        updateStepTokens('dedupe', stepTokens.dedupe);
        
        // 如果有合并，显示去重详情
        if (dedupeResult.merge_groups && dedupeResult.merge_groups.length > 0) {
            addAutoLog(`发现 ${dedupeResult.merge_groups.length} 组相似知识点被合并`, 'warning');
            showDedupeDetails(dedupeResult);
        }
        
        updateAutoStep('dedupe', 'completed', `去重后 ${uniqueKnowledgePoints.length} 个知识点`);
        addAutoLog(`去重完成，消耗 ${(stepTokens.dedupe || 0).toLocaleString()} tokens`, 'success');
        
        goToStepSilent(3);
        
        // ===== 步骤4: 生成类题 =====
        updateAutoStep('generate', 'active', '正在生成类题...');
        addAutoLog('开始生成类题', 'info');
        
        const generateResult = await autoGenerateSimilar(textModel, count);
        if (!generateResult.success) throw new Error(generateResult.error || '生成失败');
        
        similarQuestions = generateResult.questions;
        await saveSimilarResults();
        
        stepTokens.generate = generateResult.tokens || 0;
        updateStepTokens('generate', stepTokens.generate);
        updateAutoStep('generate', 'completed', `生成了 ${similarQuestions.length} 道类题`);
        addAutoLog(`类题生成完成，消耗 ${stepTokens.generate.toLocaleString()} tokens`, 'success');
        
        goToStepSilent(4);
        
        // ===== 步骤5: 校验优化 =====
        updateAutoStep('verify', 'active', '正在校验类题...');
        addAutoLog('开始校验类题', 'info');
        
        const verifyResult = await autoVerifyQuestions();
        if (!verifyResult.success) throw new Error(verifyResult.error || '校验失败');
        
        similarQuestions = verifyResult.questions;
        await saveSimilarResults();
        
        stepTokens.verify = verifyResult.tokens || 0;
        updateStepTokens('verify', stepTokens.verify);
        updateAutoStep('verify', 'completed', `校验完成，修正 ${verifyResult.fixedCount} 道`);
        addAutoLog(`校验完成，消耗 ${stepTokens.verify.toLocaleString()} tokens`, 'success');
        
        goToStepSilent(5);
        
        // ===== 步骤6: 完成 =====
        updateAutoStep('export', 'completed', '全部完成！');
        addAutoLog('自动执行完成！', 'success');
        
        // 更新标题
        const titleEl = document.querySelector('.auto-progress-title');
        titleEl.innerHTML = '<span>自动执行完成</span>';
        
        // 显示结果视图
        setTimeout(() => {
            showAutoResultView();
        }, 800);
        
    } catch (error) {
        addAutoLog(`错误: ${error.message}`, 'error');
        const titleEl = document.querySelector('.auto-progress-title');
        titleEl.innerHTML = '<span>执行出错</span>';
        
        // 标记当前步骤为错误
        document.querySelectorAll('.auto-step.active').forEach(el => {
            el.classList.remove('active');
            el.classList.add('error');
        });
        
        showToast('自动执行出错: ' + error.message);
    } finally {
        autoRunning = false;
        document.getElementById('autoRunBtn').disabled = false;
        startParseBtn.disabled = false;
    }
}

// 静默切换步骤（只更新指示器，不显示面板）
function goToStepSilent(step) {
    document.querySelectorAll('.step').forEach((el, idx) => {
        el.classList.remove('active', 'completed');
        if (idx + 1 < step) el.classList.add('completed');
        if (idx + 1 === step) el.classList.add('active');
    });
    currentStep = step;
}

// 自动解析图片（根据设置选择并行或流式）
async function autoParseImages(multimodalModel) {
    const parseMode = document.getElementById('parseMode')?.value || 'parallel';
    
    if (parseMode === 'parallel') {
        return autoParseImagesParallel(multimodalModel);
    } else {
        return autoParseImagesStream(multimodalModel);
    }
}

// 并行解析图片（快速模式）
async function autoParseImagesParallel(multimodalModel) {
    return new Promise(async (resolve) => {
        try {
            // 使用并行解析API
            const response = await fetch('/api/knowledge-agent/parse-parallel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId, multimodal_model: multimodalModel, prompt: PROMPTS.parse })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let imageResponses = {};
            let buffer = '';
            let stepTokens = 0;
            let imageCount = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') addAutoLog(data.message, 'info');
                                else if (data.type === 'image_done') {
                                    imageResponses[data.image] = data.response;
                                    imageCount++;
                                    addAutoLog(`图片 ${data.image} 解析完成`, 'success');
                                }
                                else if (data.type === 'usage') {
                                    const usage = data.usage || {};
                                    stepTokens += usage.total_tokens || 0;
                                    totalTokenUsage.prompt_tokens += usage.prompt_tokens || 0;
                                    totalTokenUsage.completion_tokens += usage.completion_tokens || 0;
                                    totalTokenUsage.total_tokens += usage.total_tokens || 0;
                                    updateTokenDisplay();
                                }
                                else if (data.type === 'done') {
                                    // 并行解析完成
                                    addAutoLog('所有图片并行解析完成', 'success');
                                }
                                else if (data.type === 'error') addAutoLog(`图片解析错误: ${data.error}`, 'error');
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            resolve({ success: Object.keys(imageResponses).length > 0, imageResponses, imageCount: Object.keys(imageResponses).length, tokens: stepTokens });
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}

// 流式解析图片（实时模式）
async function autoParseImagesStream(multimodalModel) {
    return new Promise(async (resolve) => {
        try {
            const response = await fetch('/api/knowledge-agent/parse-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId, multimodal_model: multimodalModel, prompt: PROMPTS.parse })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let imageResponses = {};
            let buffer = '';
            let stepTokens = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') addAutoLog(data.message, 'info');
                                else if (data.type === 'image_done') {
                                    imageResponses[data.image] = data.response;
                                    addAutoLog(`图片 ${data.image} 解析完成`, 'success');
                                }
                                else if (data.type === 'usage') {
                                    const usage = data.usage || {};
                                    stepTokens += usage.total_tokens || 0;
                                    totalTokenUsage.prompt_tokens += usage.prompt_tokens || 0;
                                    totalTokenUsage.completion_tokens += usage.completion_tokens || 0;
                                    totalTokenUsage.total_tokens += usage.total_tokens || 0;
                                    updateTokenDisplay();
                                }
                                else if (data.type === 'done') {
                                    addAutoLog('流式解析完成', 'success');
                                }
                                else if (data.type === 'error') addAutoLog(`图片解析错误: ${data.error}`, 'error');
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            resolve({ success: Object.keys(imageResponses).length > 0, imageResponses, imageCount: Object.keys(imageResponses).length, tokens: stepTokens });
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}

// 自动提取知识点
async function autoExtractKnowledge(textModel, imageResponses) {
    return new Promise(async (resolve) => {
        try {
            let questions = [];
            
            for (const [image, response] of Object.entries(imageResponses)) {
                try {
                    const jsonMatch = response.match(/\[[\s\S]*\]/);
                    if (jsonMatch) {
                        const parsed = safeJsonParse(jsonMatch[0]);
                        if (Array.isArray(parsed)) {
                            parsed.forEach(q => questions.push({ ...q, image_source: image, knowledge_points: [] }));
                        }
                    } else {
                        const objMatch = response.match(/\{[\s\S]*\}/);
                        if (objMatch) {
                            const parsed = safeJsonParse(objMatch[0]);
                            questions.push({ ...parsed, image_source: image, knowledge_points: [] });
                        }
                    }
                } catch (e) {
                    questions.push({ content: response, subject: '', question_type: '简答题', difficulty: '中等', image_source: image, knowledge_points: [] });
                }
            }
            
            if (questions.length === 0) {
                resolve({ success: false, error: '未识别到题目' });
                return;
            }
            
            const response = await fetch('/api/knowledge-agent/extract-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId, text_model: textModel, prompt: PROMPTS.extract, questions: questions })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let questionResponses = {};
            let buffer = '';
            let stepTokens = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') addAutoLog(data.message, 'info');
                                else if (data.type === 'question_done') {
                                    questionResponses[data.question_idx] = data.response;
                                    addAutoLog(`题目 ${parseInt(data.question_idx) + 1} 知识点提取完成`, 'success');
                                }
                                else if (data.type === 'usage') {
                                    const usage = data.usage || {};
                                    stepTokens += usage.total_tokens || 0;
                                    totalTokenUsage.prompt_tokens += usage.prompt_tokens || 0;
                                    totalTokenUsage.completion_tokens += usage.completion_tokens || 0;
                                    totalTokenUsage.total_tokens += usage.total_tokens || 0;
                                    updateTokenDisplay();
                                }
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            // 解析知识点
            for (const [idx, resp] of Object.entries(questionResponses)) {
                try {
                    const objMatch = resp.match(/\{[\s\S]*\}/);
                    if (objMatch) {
                        const kp = safeJsonParse(objMatch[0]);
                        questions[idx].knowledge_points = [{
                            id: generateId(),
                            primary: (kp.primary || '').substring(0, 10),
                            secondary: kp.secondary || '',
                            analysis: kp.solution_approach || kp.analysis || ''
                        }];
                    }
                } catch (e) {
                    questions[idx].knowledge_points = [{ id: generateId(), primary: '解析失败', secondary: '', analysis: e.message }];
                }
            }
            
            questions = questions.map(q => ({ id: generateId(), ...q }));
            resolve({ success: true, questions, tokens: stepTokens });
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}

// 去重相关变量
let dedupeOriginalKps = [];
let dedupeMergeGroups = [];
let dedupeUniquePoints = [];

// 自动去重（流式版本）
async function autoDedupeKnowledge(threshold) {
    return new Promise(async (resolve) => {
        try {
            const response = await fetch('/api/knowledge-agent/dedupe-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let stepTokens = 0;
            let result = { success: false };
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') {
                                    addAutoLog(data.message, 'info');
                                }
                                else if (data.type === 'prompt') {
                                    addAutoLog('去重提示词已生成', 'info');
                                }
                                else if (data.type === 'original_kps') {
                                    dedupeOriginalKps = data.knowledge_points;
                                    addAutoLog(`原始知识点: ${dedupeOriginalKps.length} 个`, 'info');
                                }
                                else if (data.type === 'chunk') {
                                    // 流式输出，可以显示在日志中
                                }
                                else if (data.type === 'usage') {
                                    const usage = data.usage || {};
                                    stepTokens = usage.total_tokens || 0;
                                    totalTokenUsage.prompt_tokens += usage.prompt_tokens || 0;
                                    totalTokenUsage.completion_tokens += usage.completion_tokens || 0;
                                    totalTokenUsage.total_tokens += usage.total_tokens || 0;
                                    updateTokenDisplay();
                                }
                                else if (data.type === 'done') {
                                    dedupeUniquePoints = data.unique_points || [];
                                    dedupeMergeGroups = data.merge_groups || [];
                                    result = {
                                        success: true,
                                        unique_points: dedupeUniquePoints,
                                        merge_groups: dedupeMergeGroups,
                                        original_count: data.original_count,
                                        final_count: data.final_count,
                                        tokens: stepTokens
                                    };
                                    addAutoLog(`去重完成: ${data.original_count} → ${data.final_count} 个知识点`, 'success');
                                }
                                else if (data.type === 'error') {
                                    addAutoLog(`去重错误: ${data.error}`, 'error');
                                    result = { success: false, error: data.error };
                                }
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            resolve(result);
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}

// 自动生成类题
async function autoGenerateSimilar(textModel, count) {
    return new Promise(async (resolve) => {
        try {
            const kpData = uniqueKnowledgePoints.map(kp => {
                let difficulty = '中等', questionType = '简答题';
                for (const q of parsedQuestions) {
                    for (const qkp of (q.knowledge_points || [])) {
                        if (qkp.id === kp.id) { difficulty = q.difficulty; questionType = q.question_type; break; }
                    }
                }
                return { id: kp.id, primary: kp.primary, secondary: kp.secondary, analysis: kp.analysis, difficulty, question_type: questionType };
            });
            
            const response = await fetch('/api/knowledge-agent/generate-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId, text_model: textModel, prompt: PROMPTS.generate, knowledge_points: kpData, count: count })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let kpResponses = {};
            let buffer = '';
            let questions = [];
            let stepTokens = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') addAutoLog(data.message, 'info');
                                else if (data.type === 'kp_done') {
                                    kpResponses[data.kp_idx] = { kp_name: data.kp_name, response: data.response };
                                    addAutoLog(`[${data.kp_name}] 类题生成完成`, 'success');
                                }
                                else if (data.type === 'error') {
                                    addAutoLog(`类题生成错误: ${data.error}`, 'error');
                                }
                                else if (data.type === 'done') {
                                    // 解析所有类题结果
                                    for (const [idx, resp] of Object.entries(kpResponses)) {
                                        const kp = kpData[idx];
                                        try {
                                            const jsonMatch = resp.response.match(/\[[\s\S]*\]/);
                                            if (jsonMatch) {
                                                const qs = safeJsonParse(jsonMatch[0]);
                                                qs.forEach(q => {
                                                    questions.push({
                                                        id: generateId(),
                                                        knowledge_point_id: kp.id,
                                                        primary: q.primary || kp.primary,
                                                        secondary: q.secondary || kp.secondary,
                                                        content: q.content || '',
                                                        answer: q.answer || '',
                                                        solution_steps: q.solution_steps || '',
                                                        difficulty: kp.difficulty,
                                                        question_type: kp.question_type
                                                    });
                                                });
                                            }
                                        } catch (e) {
                                            questions.push({ id: generateId(), knowledge_point_id: kp.id, primary: kp.primary, secondary: kp.secondary, content: '生成失败', answer: '', solution_steps: '', difficulty: kp.difficulty, question_type: kp.question_type });
                                        }
                                    }
                                }
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            resolve({ success: questions.length > 0, questions, tokens: stepTokens });
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}

// 自动校验
async function autoVerifyQuestions() {
    return new Promise(async (resolve) => {
        try {
            const response = await fetch('/api/knowledge-agent/verify-stream', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ task_id: currentTaskId, prompt: PROMPTS.verify, questions: similarQuestions })
            });
            
            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';
            let fixedCount = 0;
            let stepTokens = 0;
            
            while (true) {
                const { done, value } = await reader.read();
                if (value) {
                    buffer += decoder.decode(value, { stream: true });
                    const lines = buffer.split('\n');
                    buffer = lines.pop() || '';
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            try {
                                const data = JSON.parse(line.slice(6));
                                if (data.type === 'progress') addAutoLog(data.message, 'info');
                                else if (data.type === 'question_verified') {
                                    const idx = data.question_idx;
                                    if (data.result && similarQuestions[idx]) {
                                        if (data.result.is_correct === false) fixedCount++;
                                        similarQuestions[idx].content = data.result.content || similarQuestions[idx].content;
                                        similarQuestions[idx].answer = data.result.answer || similarQuestions[idx].answer;
                                        similarQuestions[idx].solution_steps = data.result.solution_steps || similarQuestions[idx].solution_steps;
                                        similarQuestions[idx].is_correct = data.result.is_correct;
                                        similarQuestions[idx].issues = data.result.issues || [];
                                    }
                                    addAutoLog(`类题 ${idx + 1} 校验完成`, 'success');
                                }
                                else if (data.type === 'usage') {
                                    const usage = data.usage || {};
                                    stepTokens += usage.total_tokens || 0;
                                    totalTokenUsage.prompt_tokens += usage.prompt_tokens || 0;
                                    totalTokenUsage.completion_tokens += usage.completion_tokens || 0;
                                    totalTokenUsage.total_tokens += usage.total_tokens || 0;
                                    updateTokenDisplay();
                                }
                            } catch (e) {}
                        }
                    }
                }
                if (done) break;
            }
            
            resolve({ success: true, questions: similarQuestions, fixedCount, tokens: stepTokens });
        } catch (error) {
            resolve({ success: false, error: error.message });
        }
    });
}


// ========== 自动执行结果视图 ==========
function showAutoResultView() {
    // 移除进度面板
    const progressPanel = document.getElementById('autoProgressPanel');
    if (progressPanel) {
        progressPanel.style.display = 'none';
    }
    
    // 创建结果视图
    const contentArea = document.querySelector('.content-area');
    const existingResult = document.getElementById('autoResultView');
    if (existingResult) existingResult.remove();
    
    const totalTime = ((Date.now() - autoStartTime) / 1000).toFixed(1);
    const fixedCount = similarQuestions.filter(q => q.is_correct === false).length;
    
    const resultView = document.createElement('div');
    resultView.id = 'autoResultView';
    resultView.className = 'auto-result-view';
    resultView.innerHTML = `
        <div class="result-summary">
            <div class="summary-header">
                <h2>处理完成</h2>
                <span class="summary-time">耗时 ${totalTime}s</span>
            </div>
            <div class="summary-stats">
                <div class="stat-item">
                    <div class="stat-value">${parsedQuestions.length}</div>
                    <div class="stat-label">识别题目</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${uniqueKnowledgePoints.length}</div>
                    <div class="stat-label">知识点</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${similarQuestions.length}</div>
                    <div class="stat-label">生成类题</div>
                </div>
                <div class="stat-item">
                    <div class="stat-value">${fixedCount}</div>
                    <div class="stat-label">已修正</div>
                </div>
                <div class="stat-item stat-tokens">
                    <div class="stat-value">${totalTokenUsage.total_tokens.toLocaleString()}</div>
                    <div class="stat-label">Token消耗</div>
                </div>
            </div>
        </div>
        
        <div class="result-tabs">
            <button class="result-tab active" data-tab="questions">原题解析</button>
            <button class="result-tab" data-tab="knowledge">知识点</button>
            <button class="result-tab" data-tab="similar">类题练习</button>
        </div>
        
        <div class="result-content">
            <div class="result-panel active" id="panel-questions">
                ${renderQuestionsPanel()}
            </div>
            <div class="result-panel" id="panel-knowledge">
                ${renderKnowledgePanel()}
            </div>
            <div class="result-panel" id="panel-similar">
                ${renderSimilarPanel()}
            </div>
        </div>
        
        <div class="result-actions">
            <button class="btn-secondary" onclick="hideAutoResultView()">返回编辑</button>
            <button class="btn-secondary" onclick="exportResult('full_result')">导出完整结果</button>
            <button class="btn-primary" onclick="startNewTask()">开始新任务</button>
        </div>
    `;
    
    contentArea.insertBefore(resultView, contentArea.firstChild);
    
    // 绑定标签切换事件
    resultView.querySelectorAll('.result-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            resultView.querySelectorAll('.result-tab').forEach(t => t.classList.remove('active'));
            resultView.querySelectorAll('.result-panel').forEach(p => p.classList.remove('active'));
            tab.classList.add('active');
            document.getElementById(`panel-${tab.dataset.tab}`).classList.add('active');
        });
    });
    
    // 隐藏步骤面板
    document.querySelectorAll('.step-panel').forEach(p => p.classList.remove('active'));
    
    // 更新步骤指示器
    document.querySelectorAll('.step').forEach((el, idx) => {
        el.classList.remove('active');
        el.classList.add('completed');
    });
}

function renderQuestionsPanel() {
    if (!parsedQuestions.length) return '<div class="empty-state">暂无数据</div>';
    
    return parsedQuestions.map((q, idx) => `
        <div class="question-card">
            <div class="question-header">
                <span class="question-num">题目 ${idx + 1}</span>
                <span class="question-meta">${q.subject || '未知学科'} · ${q.question_type || '未知题型'} · ${q.difficulty || '中等'}</span>
            </div>
            <div class="question-content">${escapeHtml(q.content)}</div>
            <div class="question-kp">
                ${(q.knowledge_points || []).map(kp => `
                    <div class="kp-tag">
                        <span class="kp-name">${escapeHtml(kp.primary)}</span>
                        ${kp.secondary ? `<span class="kp-detail">${escapeHtml(kp.secondary)}</span>` : ''}
                    </div>
                `).join('')}
            </div>
            ${(q.knowledge_points || []).some(kp => kp.analysis) ? `
                <div class="question-analysis">
                    <div class="analysis-title">解题思路</div>
                    <div class="analysis-content">${escapeHtml((q.knowledge_points[0] || {}).analysis || '')}</div>
                </div>
            ` : ''}
        </div>
    `).join('');
}

function renderKnowledgePanel() {
    if (!uniqueKnowledgePoints.length) return '<div class="empty-state">暂无数据</div>';
    
    return `
        <div class="knowledge-grid">
            ${uniqueKnowledgePoints.map((kp, idx) => `
                <div class="knowledge-card">
                    <div class="knowledge-num">${idx + 1}</div>
                    <div class="knowledge-info">
                        <div class="knowledge-primary">${escapeHtml(kp.primary)}</div>
                        ${kp.secondary ? `<div class="knowledge-secondary">${escapeHtml(kp.secondary)}</div>` : ''}
                        ${kp.analysis ? `<div class="knowledge-analysis">${escapeHtml(kp.analysis)}</div>` : ''}
                    </div>
                </div>
            `).join('')}
        </div>
    `;
}

function renderSimilarPanel() {
    if (!similarQuestions.length) return '<div class="empty-state">暂无数据</div>';
    
    return similarQuestions.map((sq, idx) => `
        <div class="similar-result-card ${sq.is_correct === false ? 'was-fixed' : ''}" data-sq-id="${sq.id}">
            <div class="similar-result-header">
                <span class="similar-result-num">类题 ${idx + 1}</span>
                <span class="similar-result-kp">${escapeHtml(sq.primary || '')}</span>
                ${sq.is_correct === false ? '<span class="fixed-badge">已修正</span>' : ''}
                <button class="edit-sq-btn" onclick="toggleEditSimilar('${sq.id}')">编辑</button>
            </div>
            <div class="similar-result-section">
                <div class="section-label">题目</div>
                <div class="section-content" data-field="content">${escapeHtml(sq.content)}</div>
                <textarea class="edit-textarea" data-field="content" style="display:none">${escapeHtml(sq.content)}</textarea>
            </div>
            <div class="similar-result-section">
                <div class="section-label">答案</div>
                <div class="section-content answer" data-field="answer">${escapeHtml(sq.answer)}</div>
                <textarea class="edit-textarea" data-field="answer" style="display:none">${escapeHtml(sq.answer)}</textarea>
            </div>
            <div class="similar-result-section">
                <div class="section-label">解题步骤</div>
                <div class="section-content steps" data-field="solution_steps">${escapeHtml(sq.solution_steps)}</div>
                <textarea class="edit-textarea tall" data-field="solution_steps" style="display:none">${escapeHtml(sq.solution_steps)}</textarea>
            </div>
            <div class="edit-actions" style="display:none">
                <button class="btn-secondary" onclick="cancelEditSimilar('${sq.id}')">取消</button>
                <button class="btn-primary" onclick="saveEditSimilar('${sq.id}')">保存</button>
            </div>
            ${sq.issues && sq.issues.length > 0 ? `
                <div class="similar-result-issues">
                    <span class="issues-label">修正说明：</span>${sq.issues.join('；')}
                </div>
            ` : ''}
        </div>
    `).join('');
}

// 切换编辑模式
function toggleEditSimilar(sqId) {
    const card = document.querySelector(`.similar-result-card[data-sq-id="${sqId}"]`);
    if (!card) return;
    
    const isEditing = card.classList.contains('editing');
    
    if (isEditing) {
        cancelEditSimilar(sqId);
    } else {
        card.classList.add('editing');
        card.querySelectorAll('.section-content').forEach(el => el.style.display = 'none');
        card.querySelectorAll('.edit-textarea').forEach(el => el.style.display = 'block');
        card.querySelector('.edit-actions').style.display = 'flex';
        card.querySelector('.edit-sq-btn').textContent = '取消';
    }
}

// 取消编辑
function cancelEditSimilar(sqId) {
    const card = document.querySelector(`.similar-result-card[data-sq-id="${sqId}"]`);
    if (!card) return;
    
    card.classList.remove('editing');
    card.querySelectorAll('.section-content').forEach(el => el.style.display = 'block');
    card.querySelectorAll('.edit-textarea').forEach(el => el.style.display = 'none');
    card.querySelector('.edit-actions').style.display = 'none';
    card.querySelector('.edit-sq-btn').textContent = '编辑';
    
    // 恢复原始值
    const sq = similarQuestions.find(s => s.id === sqId);
    if (sq) {
        card.querySelector('.edit-textarea[data-field="content"]').value = sq.content;
        card.querySelector('.edit-textarea[data-field="answer"]').value = sq.answer;
        card.querySelector('.edit-textarea[data-field="solution_steps"]').value = sq.solution_steps;
    }
}

// 保存编辑
async function saveEditSimilar(sqId) {
    const card = document.querySelector(`.similar-result-card[data-sq-id="${sqId}"]`);
    if (!card) return;
    
    const content = card.querySelector('.edit-textarea[data-field="content"]').value;
    const answer = card.querySelector('.edit-textarea[data-field="answer"]').value;
    const solution_steps = card.querySelector('.edit-textarea[data-field="solution_steps"]').value;
    
    // 更新本地数据
    const sqIdx = similarQuestions.findIndex(s => s.id === sqId);
    if (sqIdx !== -1) {
        similarQuestions[sqIdx].content = content;
        similarQuestions[sqIdx].answer = answer;
        similarQuestions[sqIdx].solution_steps = solution_steps;
    }
    
    // 更新显示
    card.querySelector('.section-content[data-field="content"]').textContent = content;
    card.querySelector('.section-content[data-field="answer"]').textContent = answer;
    card.querySelector('.section-content[data-field="solution_steps"]').textContent = solution_steps;
    
    // 保存到后端
    try {
        await fetch('/api/knowledge-agent/edit', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: currentTaskId,
                question_id: sqId,
                updates: { content, answer, solution_steps }
            })
        });
        showToast('保存成功');
    } catch (e) {
        showToast('保存失败');
    }
    
    cancelEditSimilar(sqId);
}

function hideAutoResultView() {
    const resultView = document.getElementById('autoResultView');
    if (resultView) resultView.remove();
    
    const progressPanel = document.getElementById('autoProgressPanel');
    if (progressPanel) progressPanel.remove();
    
    // 显示导出步骤
    goToStep(6);
}


// ========== 去重详情显示 ==========
function showDedupeDetails(dedupeResult) {
    const progressPanel = document.getElementById('autoProgressPanel');
    if (!progressPanel) return;
    
    // 移除已有的去重详情
    const existingDetails = document.getElementById('dedupeDetails');
    if (existingDetails) existingDetails.remove();
    
    const detailsDiv = document.createElement('div');
    detailsDiv.id = 'dedupeDetails';
    detailsDiv.className = 'dedupe-details';
    
    const mergeGroups = dedupeResult.merge_groups || [];
    const uniquePoints = dedupeResult.unique_points || [];
    
    detailsDiv.innerHTML = `
        <div class="dedupe-details-header">
            <span class="dedupe-details-title">去重详情</span>
            <span class="dedupe-details-summary">${dedupeResult.original_count} → ${dedupeResult.final_count} 个知识点</span>
            <button class="dedupe-toggle-btn" onclick="toggleDedupeDetails()">收起</button>
        </div>
        <div class="dedupe-details-content" id="dedupeDetailsContent">
            ${mergeGroups.length > 0 ? `
                <div class="dedupe-section">
                    <div class="dedupe-section-title">合并的知识点组 (${mergeGroups.length}组)</div>
                    ${mergeGroups.map((group, idx) => `
                        <div class="merge-group" data-group="${idx}">
                            <div class="merge-target">
                                <span class="merge-label">保留</span>
                                <span class="merge-kp-name">${escapeHtml(group.target.primary)}</span>
                                <span class="merge-kp-detail">${escapeHtml(group.target.secondary || '')}</span>
                            </div>
                            <div class="merge-arrow">←</div>
                            <div class="merged-items">
                                ${group.merged.map(m => `
                                    <div class="merged-item" data-id="${m.id}">
                                        <span class="merged-kp-name">${escapeHtml(m.primary)}</span>
                                        <button class="restore-btn" onclick="restoreMergedKp('${m.id}', ${idx})" title="恢复此知识点">恢复</button>
                                    </div>
                                `).join('')}
                            </div>
                        </div>
                    `).join('')}
                </div>
            ` : ''}
            <div class="dedupe-section">
                <div class="dedupe-section-title">最终保留的知识点 (${uniquePoints.length}个)</div>
                <div class="final-kps">
                    ${uniquePoints.map((kp, idx) => `
                        <div class="final-kp-item ${kp.merged_from && kp.merged_from.length > 0 ? 'has-merged' : ''}">
                            <span class="final-kp-num">${idx + 1}</span>
                            <span class="final-kp-name">${escapeHtml(kp.primary)}</span>
                            ${kp.merged_from && kp.merged_from.length > 0 ? 
                                `<span class="merged-count">合并了${kp.merged_from.length}个</span>` : ''}
                        </div>
                    `).join('')}
                </div>
            </div>
        </div>
    `;
    
    // 插入到日志之前
    const autoLog = document.getElementById('autoLog');
    if (autoLog) {
        progressPanel.insertBefore(detailsDiv, autoLog);
    } else {
        progressPanel.appendChild(detailsDiv);
    }
}

function toggleDedupeDetails() {
    const content = document.getElementById('dedupeDetailsContent');
    const btn = document.querySelector('.dedupe-toggle-btn');
    if (content && btn) {
        if (content.style.display === 'none') {
            content.style.display = 'block';
            btn.textContent = '收起';
        } else {
            content.style.display = 'none';
            btn.textContent = '展开';
        }
    }
}

function restoreMergedKp(kpId, groupIdx) {
    // 从原始知识点中找到被合并的知识点
    const kp = dedupeOriginalKps.find(k => k.id === kpId);
    if (!kp) return;
    
    // 添加到uniqueKnowledgePoints
    uniqueKnowledgePoints.push({
        id: kp.id,
        primary: kp.primary,
        secondary: kp.secondary,
        analysis: kp.analysis,
        merged_from: [],
        is_kept: true,
        restored: true
    });
    
    // 从合并组中移除
    if (dedupeMergeGroups[groupIdx]) {
        dedupeMergeGroups[groupIdx].merged = dedupeMergeGroups[groupIdx].merged.filter(m => m.id !== kpId);
        
        // 如果合并组为空，移除整个组
        if (dedupeMergeGroups[groupIdx].merged.length === 0) {
            dedupeMergeGroups.splice(groupIdx, 1);
        }
    }
    
    // 更新UI
    const mergedItem = document.querySelector(`.merged-item[data-id="${kpId}"]`);
    if (mergedItem) {
        mergedItem.classList.add('restored');
        mergedItem.innerHTML = `
            <span class="merged-kp-name">${escapeHtml(kp.primary)}</span>
            <span class="restored-label">已恢复</span>
        `;
    }
    
    // 更新统计
    const summary = document.querySelector('.dedupe-details-summary');
    if (summary) {
        summary.textContent = `${dedupeOriginalKps.length} → ${uniqueKnowledgePoints.length} 个知识点`;
    }
    
    addAutoLog(`已恢复知识点: ${kp.primary}`, 'success');
}


// ========== 历史任务功能 ==========
async function showHistoryModal() {
    document.getElementById('historyModal').classList.add('show');
    await loadHistoryTasks();
}

function hideHistoryModal() {
    document.getElementById('historyModal').classList.remove('show');
}

async function loadHistoryTasks() {
    const listEl = document.getElementById('historyList');
    listEl.innerHTML = '<div class="loading-state">加载中...</div>';
    
    try {
        const response = await fetch('/api/knowledge-agent/history');
        const result = await response.json();
        
        if (result.success && result.tasks.length > 0) {
            listEl.innerHTML = result.tasks.map(task => `
                <div class="history-item" data-task-id="${task.task_id}">
                    <div class="history-item-info">
                        <div class="history-item-title">
                            ${task.first_image || '任务 ' + task.task_id}
                        </div>
                        <div class="history-item-meta">
                            ${task.image_count} 张图片 · ${task.question_count} 道题 · ${task.similar_count} 道类题
                        </div>
                        <div class="history-item-status ${task.status}">${getStatusText(task.status)}</div>
                    </div>
                    <div class="history-item-actions">
                        <button class="btn-small" onclick="loadHistoryTask('${task.task_id}')">继续</button>
                        <button class="btn-small danger" onclick="deleteHistoryTask('${task.task_id}')">删除</button>
                    </div>
                </div>
            `).join('');
        } else {
            listEl.innerHTML = '<div class="empty-state">暂无历史任务</div>';
        }
    } catch (error) {
        listEl.innerHTML = '<div class="error-state">加载失败</div>';
    }
}

function getStatusText(status) {
    const statusMap = {
        'created': '已创建',
        'parsed': '已解析',
        'completed': '已完成'
    };
    return statusMap[status] || status;
}

async function loadHistoryTask(taskId) {
    try {
        showToast('正在加载任务...');
        const response = await fetch(`/api/knowledge-agent/history/${taskId}`);
        const result = await response.json();
        
        if (result.success) {
            // 恢复任务数据
            currentTaskId = result.task_id;
            parsedQuestions = result.parsed_questions || [];
            similarQuestions = result.similar_questions || [];
            
            // 恢复知识点数据
            uniqueKnowledgePoints = result.unique_points || [];
            if (uniqueKnowledgePoints.length === 0 && parsedQuestions.length > 0) {
                // 从解析结果中提取知识点
                const kpMap = {};
                for (const q of parsedQuestions) {
                    for (const kp of (q.knowledge_points || [])) {
                        if (!kpMap[kp.id]) {
                            kpMap[kp.id] = kp;
                        }
                    }
                }
                uniqueKnowledgePoints = Object.values(kpMap);
            }
            
            // 显示图片预览
            if (result.images && result.images.length > 0) {
                displayPreviews(result.images);
                startParseBtn.disabled = false;
                document.getElementById('autoRunBtn').disabled = false;
            }
            
            hideHistoryModal();
            
            // 根据状态跳转到对应步骤
            if (result.status === 'completed' && similarQuestions.length > 0) {
                // 设置自动执行的时间和token（用于结果视图显示）
                autoStartTime = Date.now();
                totalTokenUsage = { prompt_tokens: 0, completion_tokens: 0, total_tokens: 0 };
                showAutoResultView();
                showToast('已加载历史任务，显示结果');
            } else if (result.status === 'parsed' && parsedQuestions.length > 0) {
                displayParseResults(parsedQuestions);
                document.getElementById('parseResultSection').style.display = 'block';
                confirmParseBtn.disabled = false;
                goToStep(2);
                showToast('已加载历史任务，可继续处理');
            } else {
                goToStep(1);
                showToast('已加载历史任务');
            }
        } else {
            showToast('加载失败: ' + result.error);
        }
    } catch (error) {
        showToast('加载失败: ' + error.message);
    }
}

async function deleteHistoryTask(taskId) {
    if (!confirm('确定要删除这个任务吗？')) return;
    
    try {
        const response = await fetch(`/api/knowledge-agent/history/${taskId}`, {
            method: 'DELETE'
        });
        const result = await response.json();
        
        if (result.success) {
            // 从列表中移除
            const item = document.querySelector(`.history-item[data-task-id="${taskId}"]`);
            if (item) item.remove();
            showToast('已删除');
        }
    } catch (error) {
        showToast('删除失败');
    }
}

// 点击弹窗外部关闭
document.addEventListener('click', (e) => {
    const historyModal = document.getElementById('historyModal');
    if (e.target === historyModal) hideHistoryModal();
});
