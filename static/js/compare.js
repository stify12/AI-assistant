/**
 * AI 输出对比分析页面 JavaScript
 */

// ========== 全局状态 ==========
let currentTab = 0;
let singleImage = null;
let consistImage = null;
let multiModelImage = null;
let batchData = null;
let excelData = null;
let evalConfigStatus = { qwen_configured: false, deepseek_configured: false, joint_available: false };
let lastTestResults = null;

// 测试控制
let isTestRunning = false;
let abortController = null;

// 图表实例管理（防止内存泄漏）
let chartInstances = {
    single: [],
    consist: [],
    excel: [],
    multi: []
};

// 模型配置
const MODELS = {
    'doubao-1-5-vision-pro-32k-250115': { name: 'Vision Pro 1.5', short: 'VP1.5' },
    'doubao-seed-1-6-vision-250815': { name: 'Seed Vision 1.6', short: 'SV1.6' },
    'doubao-seed-1-6-251015': { name: 'Seed 1.6', short: 'S1.6' },
    'doubao-seed-1-6-thinking-250715': { name: 'Seed Thinking', short: 'ST' },
    'qwen-vl-plus': { name: 'Qwen VL', short: 'Qwen' }
};

// 输入验证配置
const VALIDATION = {
    maxPromptLength: 5000,
    maxBaseAnswerLength: 10000,
    maxRepeatCount: 30,
    minRepeatCount: 1
};

// ========== 提示词持久化 ==========
const PROMPT_STORAGE_KEY = 'compare_prompts';

function loadSavedPrompts() {
    try {
        const saved = localStorage.getItem(PROMPT_STORAGE_KEY);
        if (saved) {
            const prompts = JSON.parse(saved);
            // 恢复各个提示词
            if (prompts.singlePrompt) {
                const el = document.getElementById('singlePrompt');
                if (el) el.value = prompts.singlePrompt;
            }
            if (prompts.consistPrompt) {
                const el = document.getElementById('consistPrompt');
                if (el) el.value = prompts.consistPrompt;
            }
            if (prompts.multiModelPrompt) {
                const el = document.getElementById('multiModelPrompt');
                if (el) el.value = prompts.multiModelPrompt;
            }
        }
    } catch (e) {
        console.error('加载保存的提示词失败:', e);
    }
}

function savePromptToStorage(textareaId, value) {
    try {
        const saved = localStorage.getItem(PROMPT_STORAGE_KEY);
        const prompts = saved ? JSON.parse(saved) : {};
        prompts[textareaId] = value;
        localStorage.setItem(PROMPT_STORAGE_KEY, JSON.stringify(prompts));
    } catch (e) {
        console.error('保存提示词失败:', e);
    }
}

// ========== 提示词优化 ==========
async function optimizePrompt(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;
    
    const originalPrompt = textarea.value.trim();
    if (!originalPrompt) {
        alert('请先输入提示词');
        return;
    }
    
    // 获取按钮并禁用
    const btn = textarea.parentElement.querySelector('.optimize-btn');
    const originalText = btn.textContent;
    btn.disabled = true;
    btn.textContent = '优化中...';
    
    try {
        const res = await fetch('/api/optimize-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ 
                prompt: originalPrompt,
                task_type: '图片识别与答案提取'
            })
        });
        
        const data = await res.json();
        
        if (data.error) {
            alert('优化失败: ' + data.error);
        } else if (data.result) {
            // 显示优化结果确认
            const confirmed = confirm('优化后的提示词：\n\n' + data.result + '\n\n是否应用此优化？');
            if (confirmed) {
                textarea.value = data.result;
                // 保存到 localStorage
                savePromptToStorage(textareaId, data.result);
            }
        }
    } catch (e) {
        alert('优化请求失败: ' + e.message);
    } finally {
        btn.disabled = false;
        btn.textContent = originalText;
    }
}

// ========== 图片预览功能 ==========
function showImageModal(src) {
    if (!src) return;
    const modal = document.getElementById('imageModal');
    const img = document.getElementById('modalImg');
    img.src = src;
    modal.classList.add('show');
}

function hideImageModal() {
    document.getElementById('imageModal').classList.remove('show');
}

function togglePreviewPanel(src) {
    const panel = document.getElementById('imagePreviewPanel');
    const img = document.getElementById('previewPanelImg');
    
    if (src) {
        img.src = src;
        panel.classList.add('show');
        document.body.classList.add('preview-panel-open');
    } else {
        panel.classList.toggle('show');
        document.body.classList.toggle('preview-panel-open');
    }
}

// ESC 键关闭弹窗
document.addEventListener('keydown', (e) => {
    if (e.key === 'Escape') {
        hideImageModal();
    }
});

// ========== 工具函数 ==========
function switchTab(i) {
    currentTab = i;
    document.querySelectorAll('.tab').forEach((t, j) => t.classList.toggle('active', j === i));
    document.querySelectorAll('.tab-content').forEach((c, j) => c.classList.toggle('active', j === i));
    if (i === 4) refreshHistory();
    if (i === 5) updateRecommendation();
}

function showLoading(t, showCancel = false) {
    document.getElementById('loadingText').textContent = t || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
    
    // 显示/隐藏取消按钮
    let cancelBtn = document.getElementById('cancelTestBtn');
    if (!cancelBtn) {
        cancelBtn = document.createElement('button');
        cancelBtn.id = 'cancelTestBtn';
        cancelBtn.className = 'btn';
        cancelBtn.style.cssText = 'margin-top:16px;background:#d73a49;';
        cancelBtn.textContent = '取消测试';
        cancelBtn.onclick = cancelTest;
        document.getElementById('loadingOverlay').appendChild(cancelBtn);
    }
    cancelBtn.style.display = showCancel ? 'inline-block' : 'none';
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
    isTestRunning = false;
}

function cancelTest() {
    if (abortController) {
        abortController.abort();
        abortController = null;
    }
    isTestRunning = false;
    hideLoading();
    alert('测试已取消');
}

// 销毁图表实例（防止内存泄漏）
function destroyCharts(category) {
    if (chartInstances[category]) {
        chartInstances[category].forEach(chart => {
            if (chart && typeof chart.destroy === 'function') {
                chart.destroy();
            }
        });
        chartInstances[category] = [];
    }
}

// 输入验证
function validateInput(type, value) {
    switch (type) {
        case 'prompt':
            if (!value || !value.trim()) return { valid: false, msg: '请输入提示词' };
            if (value.length > VALIDATION.maxPromptLength) return { valid: false, msg: `提示词不能超过${VALIDATION.maxPromptLength}字符` };
            return { valid: true };
        case 'baseAnswer':
            if (value && value.length > VALIDATION.maxBaseAnswerLength) return { valid: false, msg: `基准答案不能超过${VALIDATION.maxBaseAnswerLength}字符` };
            return { valid: true };
        case 'repeatCount':
            const n = parseInt(value);
            if (isNaN(n) || n < VALIDATION.minRepeatCount || n > VALIDATION.maxRepeatCount) {
                return { valid: false, msg: `重复次数需在${VALIDATION.minRepeatCount}-${VALIDATION.maxRepeatCount}之间` };
            }
            return { valid: true };
        default:
            return { valid: true };
    }
}

function escapeHtml(t) {
    const d = document.createElement('div');
    d.textContent = t;
    return d.innerHTML;
}

function renderStats(s) {
    return '<div class="stats-grid">' + s.map(x =>
        '<div class="stat-card' + (x.highlight ? ' highlight' : '') + '">' +
        '<div class="stat-value">' + x.value + '</div>' +
        '<div class="stat-label">' + x.label + '</div></div>'
    ).join('') + '</div>';
}

// ========== 文件上传 ==========
function setupUpload(inputId, previewId, areaId, cb) {
    document.getElementById(inputId).addEventListener('change', e => {
        if (e.target.files[0]) {
            const r = new FileReader();
            r.onload = ev => {
                cb(ev.target.result);
                const p = document.getElementById(previewId);
                if (p) {
                    p.src = ev.target.result;
                    p.style.display = 'block';
                }
                document.getElementById(areaId).classList.add('has-file');
                // 显示预览框
                const boxId = 'previewBox' + previewId.replace('preview', '');
                const box = document.getElementById(boxId);
                if (box) box.style.display = 'block';
            };
            r.readAsDataURL(e.target.files[0]);
        }
    });
}

// 保存当前提示词
function saveCurrentPrompt(textareaId) {
    const textarea = document.getElementById(textareaId);
    if (!textarea) return;
    
    const value = textarea.value.trim();
    if (!value) {
        alert('提示词不能为空');
        return;
    }
    
    savePromptToStorage(textareaId, value);
    alert('提示词已保存');
}

// 下载Excel模板
function downloadTemplate() {
    window.location.href = '/api/download-template';
}

function setupExcelUpload() {
    document.getElementById('excelFile').addEventListener('change', e => {
        if (e.target.files[0]) {
            const f = e.target.files[0], r = new FileReader();
            r.onload = ev => {
                try {
                    const wb = XLSX.read(ev.target.result, { type: 'array' });
                    const ws = wb.Sheets[wb.SheetNames[0]];
                    const data = XLSX.utils.sheet_to_json(ws, { header: 1 });
                    if (data.length < 2) { alert('Excel数据不足'); return; }
                    const headers = data[0];
                    const rows = data.slice(1).filter(row => row.length > 0 && row[0]);
                    
                    // 检测Excel格式：新格式（模型+批次+学科+题型+JSON数组）或旧格式（题号+基准+批改结果）
                    const isNewFormat = detectExcelFormat(headers, rows);
                    
                    if (isNewFormat) {
                        // 新格式：解析JSON数组
                        excelData = parseNewFormatExcel(headers, rows);
                        const totalQuestions = excelData.rows.reduce((sum, row) => {
                            const jsonData = row.json_data || [];
                            return sum + (Array.isArray(jsonData) ? jsonData.length : 0);
                        }, 0);
                        document.getElementById('excelFileName').textContent = f.name + ' (新格式: ' + excelData.rows.length + '批次, ' + totalQuestions + '题)';
                    } else {
                        // 旧格式：保持原有逻辑
                        excelData = { headers, rows, isNewFormat: false };
                        document.getElementById('excelFileName').textContent = f.name + ' (' + rows.length + '题, ' + (headers.length - 2) + '次批改)';
                    }
                    
                    document.getElementById('uploadAreaExcel').classList.add('has-file');
                    document.getElementById('excelBtn').disabled = false;
                    
                    // 预览
                    let preview = '<div class="result-card" style="margin-top:12px;"><div class="result-header">数据预览 ' + (isNewFormat ? '(新格式)' : '(旧格式)') + '</div><div class="result-body" style="overflow-x:auto;"><table class="data-table"><thead><tr>';
                    headers.forEach(h => preview += '<th>' + escapeHtml(String(h || '')) + '</th>');
                    preview += '</tr></thead><tbody>';
                    rows.slice(0, 3).forEach(row => { 
                        preview += '<tr>'; 
                        headers.forEach((_, i) => {
                            let cellContent = String(row[i] || '');
                            // 截断JSON数组显示
                            if (cellContent.startsWith('[') && cellContent.length > 50) {
                                cellContent = cellContent.substring(0, 50) + '...';
                            }
                            preview += '<td>' + escapeHtml(cellContent) + '</td>'; 
                        }); 
                        preview += '</tr>'; 
                    });
                    if (rows.length > 3) preview += '<tr><td colspan="' + headers.length + '" style="text-align:center;color:#666;">... 共 ' + rows.length + ' 行</td></tr>';
                    preview += '</tbody></table></div></div>';
                    document.getElementById('excelPreview').innerHTML = preview;
                } catch (err) { alert('Excel解析错误: ' + err.message); }
            };
            r.readAsArrayBuffer(f);
        }
    });
}

// 检测Excel格式
function detectExcelFormat(headers, rows) {
    // 新格式特征：第一列是模型名，最后一列包含JSON数组
    if (headers.length >= 3) {
        const firstHeader = String(headers[0] || '').toLowerCase();
        const lastHeader = String(headers[headers.length - 1] || '').toLowerCase();
        // 检查是否包含"模型"或"json"关键词
        if (firstHeader.includes('模型') || lastHeader.includes('json')) {
            return true;
        }
        // 检查第一行数据的最后一列是否是JSON数组
        if (rows.length > 0) {
            const lastCell = String(rows[0][rows[0].length - 1] || '').trim();
            if (lastCell.startsWith('[') && lastCell.includes('"index"')) {
                return true;
            }
        }
    }
    return false;
}

// 解析新格式Excel（模型+批次+JSON数组，无学科和题型）
function parseNewFormatExcel(headers, rows) {
    const parsedRows = rows.map(row => {
        const model = String(row[0] || '').trim();
        const batch = String(row[1] || '').trim();
        // JSON数组在最后一列
        const jsonStr = String(row[row.length - 1] || '').trim();
        
        let jsonData = [];
        try {
            if (jsonStr.startsWith('[')) {
                jsonData = JSON.parse(jsonStr);
            }
        } catch (e) {
            console.warn('JSON解析失败:', e);
        }
        
        return {
            model,
            batch,
            json_data: jsonData
        };
    });
    
    return {
        headers,
        rows: parsedRows,
        isNewFormat: true
    };
}

// 解析基准答案文本（支持JSON格式）
function parseBaseAnswerText(text) {
    if (!text || !text.trim()) return null;
    
    text = text.trim();
    
    // 尝试解析JSON数组格式
    if (text.startsWith('[')) {
        try {
            const arr = JSON.parse(text);
            const result = {};
            arr.forEach(item => {
                const index = String(item.index || '').trim();
                // 标准答案：优先取 answer，没有则取 mainAnswer
                const answer = String(item.answer || item.mainAnswer || '').trim();
                if (index) {
                    result[index] = answer;
                }
            });
            return result;
        } catch (e) {
            console.warn('JSON解析失败:', e);
        }
    }
    
    // 尝试解析简单格式：每行 "题号:答案" 或 "题号 答案"
    const lines = text.split('\n').filter(l => l.trim());
    const result = {};
    lines.forEach(line => {
        const parts = line.split(/[:：\t\s]+/);
        if (parts.length >= 2) {
            const index = parts[0].trim();
            const answer = parts.slice(1).join(' ').trim();
            if (index) {
                result[index] = answer;
            }
        }
    });
    
    return Object.keys(result).length > 0 ? result : null;
}

// AI评估（使用基准答案）
async function runAIEvalWithBaseAnswer() {
    if (!excelData || !excelData.isNewFormat) {
        return alert('请先上传AI批改结果Excel');
    }
    if (!evalConfigStatus.qwen_configured && !evalConfigStatus.deepseek_configured) {
        return alert('请先配置评估模型API Key');
    }
    
    // 从文本框获取基准答案
    const baseAnswerText = document.getElementById('baseAnswerText')?.value || '';
    const baseAnswerData = parseBaseAnswerText(baseAnswerText);
    
    showLoading('正在进行AI评估...');
    
    try {
        // 收集所有题目数据
        const questionsToEval = [];
        excelData.rows.forEach(row => {
            const jsonData = row.json_data || [];
            jsonData.forEach(item => {
                const index = String(item.index || '').trim();
                // 标准答案：优先取 answer，没有则取 mainAnswer
                const standardAnswer = item.answer || item.mainAnswer || '';
                const aiAnswer = item.mainAnswer || item.userAnswer || '';
                const isCorrect = String(item.correct || '').toLowerCase() === 'yes';
                
                questionsToEval.push({
                    model: row.model,
                    batch: row.batch,
                    index: index,
                    standard_answer: standardAnswer,
                    ai_answer: aiAnswer,
                    marked_correct: isCorrect
                });
            });
        });
        
        // 调用统一AI评估接口
        const res = await fetch('/api/ai-eval/unified', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                test_type: 'batch',
                eval_model: evalConfigStatus.joint_available ? 'joint' : (evalConfigStatus.deepseek_configured ? 'deepseek' : 'qwen3-max'),
                test_results: {
                    questions: questionsToEval,
                    total_questions: questionsToEval.length,
                    models: [...new Set(excelData.rows.map(r => r.model))]
                }
            })
        });
        
        const result = await res.json();
        
        if (result.error) {
            alert('AI评估失败: ' + result.error);
        } else {
            renderAIEvalWithBaseAnswerResult(result, questionsToEval);
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function renderAIEvalWithBaseAnswerResult(result, questions) {
    let html = '<div class="section" style="margin-top:24px;border:2px solid #1d6f8c;border-radius:12px;padding:20px;">';
    html += '<div class="section-title" style="color:#1d6f8c;">🤖 AI评估结果（基于基准答案）</div>';
    
    // 统计信息
    const totalQuestions = questions.length;
    const markedCorrect = questions.filter(q => q.marked_correct).length;
    
    html += '<div class="stats-grid">';
    html += '<div class="stat-card"><div class="stat-value">' + totalQuestions + '</div><div class="stat-label">总题数</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + markedCorrect + '</div><div class="stat-label">标记正确</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + (totalQuestions - markedCorrect) + '</div><div class="stat-label">标记错误</div></div>';
    html += '<div class="stat-card highlight"><div class="stat-value">' + Math.round(markedCorrect / totalQuestions * 100) + '%</div><div class="stat-label">正确率</div></div>';
    html += '</div>';
    
    // 宏观分析
    if (result.macro_analysis) {
        html += '<div style="margin-top:16px;padding:12px;background:#f5f5f7;border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">📊 宏观分析</div>';
        if (result.macro_analysis.summary) {
            html += '<p style="font-size:13px;">' + escapeHtml(result.macro_analysis.summary) + '</p>';
        }
        if (result.macro_analysis.raw) {
            html += '<pre style="font-size:11px;background:#fff;padding:8px;border-radius:4px;overflow-x:auto;">' + escapeHtml(result.macro_analysis.raw) + '</pre>';
        }
        html += '</div>';
    }
    
    // 微观评估
    if (result.micro_evaluation && result.micro_evaluation.per_question_results) {
        html += '<div style="margin-top:16px;padding:12px;background:#f5f5f7;border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">🔍 微观评估</div>';
        html += '<div style="max-height:300px;overflow-y:auto;">';
        html += '<table class="data-table" style="font-size:12px;"><thead><tr><th>题号</th><th>标准答案</th><th>AI答案</th><th>语义正确</th><th>说明</th></tr></thead><tbody>';
        
        result.micro_evaluation.per_question_results.forEach((r, i) => {
            const q = questions[i] || {};
            html += '<tr>';
            html += '<td>' + escapeHtml(r.question_id || q.index || '-') + '</td>';
            html += '<td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(q.standard_answer || '-') + '</td>';
            html += '<td style="max-width:150px;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(q.ai_answer || '-') + '</td>';
            html += '<td class="' + (r.semantic_correct ? 'cell-pass' : 'cell-fail') + '">' + (r.semantic_correct ? '✓' : '✗') + '</td>';
            html += '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(r.explanation || '-') + '</td>';
            html += '</tr>';
        });
        
        html += '</tbody></table></div></div>';
    }
    
    html += '</div>';
    
    document.getElementById('batchResult').innerHTML += html;
}

// ========== API 调用 ==========
async function callAPI(img, prompt, model, options = {}) {
    const { signal, retries = 2 } = options;
    
    for (let attempt = 0; attempt <= retries; attempt++) {
        try {
            const res = await fetch('/api/analyze', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ image: img, prompt, model, stream: false }),
                signal
            });
            const data = await res.json();
            if (data.error) throw new Error(data.error);
            return {
                result: data.result,
                time: data.time || 0,
                tokens: data.tokens || { input: 0, output: 0, total: 0 }
            };
        } catch (e) {
            if (e.name === 'AbortError') throw e;
            if (attempt === retries) throw e;
            // 等待后重试
            await new Promise(r => setTimeout(r, 1000 * (attempt + 1)));
        }
    }
}

// 并行API调用（带并发控制）
async function callAPIParallel(tasks, concurrency = 5) {
    const results = [];
    const executing = [];
    
    for (const task of tasks) {
        const p = task().then(r => {
            executing.splice(executing.indexOf(p), 1);
            return r;
        }).catch(e => ({ error: e.message }));
        
        results.push(p);
        executing.push(p);
        
        if (executing.length >= concurrency) {
            await Promise.race(executing);
        }
    }
    
    return Promise.all(results);
}

function calcAcc(result, base) {
    if (!base || !base.trim()) return null;
    try {
        const m = result.match(/\[[\s\S]*?\]/);
        if (!m) return null;
        const r = JSON.parse(m[0]), b = JSON.parse(base);
        let match = 0;
        r.forEach(item => {
            const x = b.find(y => String(y.index) === String(item.index));
            // 标准答案：优先取 answer，没有则取 mainAnswer
            const stdAnswer = x ? (x.answer || x.mainAnswer || '') : '';
            if (stdAnswer && (stdAnswer === item.userAnswer || stdAnswer === item.answer)) match++;
        });
        return b.length > 0 ? Math.round(match / b.length * 100) : null;
    } catch (e) { return null; }
}

// ========== 单图测试 ==========
async function runSingleTest() {
    if (!singleImage) return alert('请先上传图片');
    
    const prompt = document.getElementById('singlePrompt').value;
    const base = document.getElementById('singleBaseAnswer').value;
    const model = document.getElementById('singleModel').value;
    const n = parseInt(document.getElementById('repeatCount').value) || 5;
    const div = document.getElementById('singleResult');
    
    // 输入验证
    const promptCheck = validateInput('prompt', prompt);
    if (!promptCheck.valid) return alert(promptCheck.msg);
    const repeatCheck = validateInput('repeatCount', n);
    if (!repeatCheck.valid) return alert(repeatCheck.msg);
    
    if (isTestRunning) return alert('测试正在进行中，请等待完成或取消');
    isTestRunning = true;
    abortController = new AbortController();
    
    // 销毁旧图表
    destroyCharts('single');
    
    showLoading('正在执行 ' + n + ' 个并行请求...', true);
    
    try {
        // 并行执行请求
        const tasks = Array(n).fill(null).map(() => () => 
            callAPI(singleImage, prompt, model, { signal: abortController.signal })
        );
        const apiResults = await callAPIParallel(tasks, 5);
        
        // 处理结果
        const results = apiResults.map(r => r.error ? null : r.result);
        const times = apiResults.map(r => r.time || 0);
        const tokens = apiResults.map(r => r.tokens || { total: 0 });
        const successCount = results.filter(r => r !== null).length;
        
        const accs = results.map(r => r ? calcAcc(r, base) : null);
        const valid = accs.filter(a => a !== null);
        const avg = valid.length > 0 ? Math.round(valid.reduce((a, b) => a + b, 0) / valid.length) : null;
        
        const norm = results.filter(r => r).map(r => r.replace(/\s+/g, '').toLowerCase());
        const unique = new Set(norm).size;
        const cons = successCount > 0 ? Math.round((1 - (unique - 1) / successCount) * 100) : 0;
        
        const avgTime = times.filter(t => t > 0).length > 0 
            ? (times.filter(t => t > 0).reduce((a, b) => a + b, 0) / times.filter(t => t > 0).length).toFixed(2) 
            : '-';
        const totalTokens = tokens.reduce((sum, t) => sum + (t.total || 0), 0);
        
        // 渲染统计
        div.innerHTML = renderStats([
            { value: successCount + '/' + n, label: '成功/总数' },
            { value: unique, label: '不同结果' },
            { value: cons + '%', label: '一致性', highlight: cons >= 80 },
            { value: avg !== null ? avg + '%' : '-', label: '平均准确率' },
            { value: avgTime + 's', label: '平均耗时' },
            { value: totalTokens, label: '总Token' }
        ]) + '<div class="chart-grid"><div class="chart-box"><div class="chart-title">准确率分布</div><canvas id="singleChart1"></canvas></div><div class="chart-box"><div class="chart-title">响应耗时趋势</div><canvas id="singleChart2"></canvas></div></div>' +
        '<div class="chart-grid"><div class="chart-box"><div class="chart-title">Token 消耗</div><canvas id="singleChart3"></canvas></div><div class="chart-box"><div class="chart-title">输出长度变化</div><canvas id="singleChart4"></canvas></div></div>' +
        '<div class="section"><div class="section-title">各次结果详情</div>' +
        apiResults.map((r, i) => {
            const acc = accs[i];
            const hasError = r.error;
            return '<div class="result-card"><div class="result-header">第 ' + (i + 1) + ' 次 ' +
                (hasError ? '<span class="tag tag-error">失败</span>' : 
                '<span class="tag ' + (acc !== null ? (acc >= 80 ? 'tag-success' : 'tag-error') : 'tag-info') + '">' + (acc !== null ? acc + '%' : '-') + '</span>') +
                ' <span style="color:#666;font-size:11px;">' + (r.time ? r.time + 's' : '-') + ' | ' + (r.tokens?.total || 0) + 't</span>' +
                '</div><div class="result-body">' + escapeHtml(hasError ? '错误: ' + r.error : r.result) + '</div></div>';
        }).join('') + '</div>' +
        '<div style="display:flex;gap:8px;margin-top:16px;">' +
        '<button class="btn" onclick="exportSingleTestResults()">导出结果</button>' +
        '<button class="btn" onclick="saveToHistory(\'single\', window.lastSingleTestResults)">保存到历史</button>' +
        '</div>';
        
        // 保存结果
        window.lastSingleTestResults = {
            model, prompt, n, successCount, unique, consistency: cons, avgAccuracy: avg,
            avgTime: parseFloat(avgTime) || 0, totalTokens, results: apiResults,
            timestamp: new Date().toISOString()
        };
        
        // 绘制图表
        if (valid.length > 0) {
            chartInstances.single.push(new Chart(document.getElementById('singleChart1'), {
                type: 'bar',
                data: { labels: results.map((_, i) => '第' + (i + 1) + '次'), datasets: [{ label: '准确率', data: accs.map(a => a || 0), backgroundColor: '#111' }] },
                options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
            }));
        }
        
        chartInstances.single.push(new Chart(document.getElementById('singleChart2'), {
            type: 'line',
            data: { labels: results.map((_, i) => '第' + (i + 1) + '次'), datasets: [{ label: '耗时(s)', data: times, borderColor: '#2196f3', fill: true, backgroundColor: 'rgba(33,150,243,0.1)', tension: 0.3 }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        chartInstances.single.push(new Chart(document.getElementById('singleChart3'), {
            type: 'bar',
            data: { labels: results.map((_, i) => '第' + (i + 1) + '次'), datasets: [{ label: 'Token', data: tokens.map(t => t.total || 0), backgroundColor: '#ff9800' }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        chartInstances.single.push(new Chart(document.getElementById('singleChart4'), {
            type: 'line',
            data: { labels: results.map((_, i) => '' + (i + 1)), datasets: [{ label: '输出长度', data: results.map(r => r ? r.length : 0), borderColor: '#111', fill: true, backgroundColor: 'rgba(0,0,0,0.05)', tension: 0.3 }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        // 自动更新模型统计数据
        updateModelStatsAuto(model, avg, parseFloat(avgTime) || null, cons);
    } catch (e) {
        if (e.name === 'AbortError') {
            div.innerHTML = '<div class="section"><p style="color:#ff9800;">测试已取消</p></div>';
        } else {
            div.innerHTML = '<div class="section"><p style="color:#c62828;">错误: ' + e.message + '</p></div>';
        }
    }
    hideLoading();
}

function exportSingleTestResults() {
    if (window.lastSingleTestResults) {
        exportToJSON(window.lastSingleTestResults, 'single_test_' + new Date().toISOString().slice(0, 10) + '.json');
    }
}

// ========== Excel 批量对比 ==========
async function runExcelCompare() {
    if (!excelData) return alert('请上传Excel文件');
    const div = document.getElementById('batchResult');
    const useSemanticEval = document.getElementById('useSemanticEval').checked && evalConfigStatus.deepseek_configured;
    
    // 检测是新格式还是旧格式
    if (excelData.isNewFormat) {
        await runNewFormatCompare(div, useSemanticEval);
    } else {
        await runOldFormatCompare(div, useSemanticEval);
    }
}

// 新格式批量对比（模型+批次+JSON数组）
async function runNewFormatCompare(div, useSemanticEval) {
    showLoading('正在分析批量对比数据...');
    
    try {
        // 调用后端API进行分析
        const res = await fetch('/api/batch-compare/analyze', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ rows: excelData.rows })
        });
        const analysis = await res.json();
        
        if (analysis.error) {
            hideLoading();
            div.innerHTML = '<div class="error-msg">' + escapeHtml(analysis.error) + '</div>';
            return;
        }
        
        // 渲染分析结果
        let html = renderStats([
            { value: analysis.summary.total_models, label: '模型数' },
            { value: analysis.summary.total_questions, label: '总题数' },
            { value: analysis.summary.overall_accuracy + '%', label: '整体准确率', highlight: analysis.summary.pass_threshold },
            { value: analysis.summary.total_correct, label: '正确数' }
        ]);
        
        // 图表区域
        html += '<div class="chart-grid"><div class="chart-box"><div class="chart-title">各模型准确率</div><canvas id="modelAccChart"></canvas></div><div class="chart-box"><div class="chart-title">错误类型分布</div><canvas id="errorTypeChart"></canvas></div></div>';
        
        // 模型排名表
        html += '<div class="section"><div class="section-title">模型排名</div><table class="data-table"><thead><tr><th>排名</th><th>模型</th><th>总题数</th><th>正确数</th><th>准确率</th></tr></thead><tbody>';
        analysis.rankings.forEach((r, i) => {
            html += '<tr><td>' + (i + 1) + '</td><td>' + escapeHtml(r.model) + '</td><td>' + r.total_questions + '</td><td>' + r.correct_count + '</td><td class="' + (r.accuracy >= 80 ? 'cell-pass' : 'cell-fail') + '">' + r.accuracy + '%</td></tr>';
        });
        html += '</tbody></table></div>';
        
        // 错误类型统计
        if (Object.keys(analysis.error_types).length > 0) {
            html += '<div class="section"><div class="section-title">错误类型分布</div><table class="data-table"><thead><tr><th>错误类型</th><th>数量</th><th>占比</th></tr></thead><tbody>';
            const totalErrors = Object.values(analysis.error_types).reduce((a, b) => a + b, 0);
            Object.entries(analysis.error_types).forEach(([type, count]) => {
                html += '<tr><td>' + escapeHtml(type) + '</td><td>' + count + '</td><td>' + Math.round(count / totalErrors * 100) + '%</td></tr>';
            });
            html += '</tbody></table></div>';
        }
        
        // 问题题目列表
        if (analysis.problem_questions.length > 0) {
            html += '<div class="section"><div class="section-title">问题题目 (' + analysis.problem_questions.length + '个)</div><div style="max-height:300px;overflow-y:auto;"><table class="data-table"><thead><tr><th>模型</th><th>题号</th><th>标准答案</th><th>AI答案</th><th>错误类型</th></tr></thead><tbody>';
            analysis.problem_questions.slice(0, 50).forEach(q => {
                html += '<tr><td>' + escapeHtml(q.model) + '</td><td>' + escapeHtml(q.index) + '</td><td>' + escapeHtml(q.standard_answer) + '</td><td class="diff-highlight">' + escapeHtml(q.user_answer) + '</td><td>' + escapeHtml(q.error_type || '-') + '</td></tr>';
            });
            html += '</tbody></table></div></div>';
        }
        
        div.innerHTML = html;
        
        // 渲染图表
        new Chart(document.getElementById('modelAccChart'), {
            type: 'bar',
            data: { 
                labels: analysis.rankings.map(r => r.model), 
                datasets: [{ label: '准确率', data: analysis.rankings.map(r => r.accuracy), backgroundColor: '#1d6f8c' }] 
            },
            options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
        });
        
        if (Object.keys(analysis.error_types).length > 0) {
            new Chart(document.getElementById('errorTypeChart'), {
                type: 'doughnut',
                data: { 
                    labels: Object.keys(analysis.error_types), 
                    datasets: [{ data: Object.values(analysis.error_types), backgroundColor: ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'] }] 
                },
                options: { responsive: true }
            });
        }
        
        // 保存测试结果
        lastTestResults = {
            type: 'batch_compare_new',
            ...analysis
        };
        document.getElementById('jointReportBtn').disabled = !evalConfigStatus.joint_available;
        
        // 添加操作按钮
        let btnHtml = '<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;">';
        btnHtml += '<button class="btn" onclick="exportToJSON(lastTestResults, \'batch_analysis.json\')">导出JSON</button>';
        btnHtml += '<button class="btn" onclick="saveToHistory(\'batch\', lastTestResults)">保存到历史</button>';
        btnHtml += '<button class="btn" onclick="generateBatchReport()">生成评估报告</button>';
        if (useSemanticEval && analysis.problem_questions.length > 0) {
            btnHtml += '<button class="btn" style="background:#333;" onclick="runSemanticEvaluation()">DeepSeek语义评估</button>';
        }
        btnHtml += '</div>';
        div.innerHTML += btnHtml;
        
        hideLoading();
    } catch (e) {
        hideLoading();
        div.innerHTML = '<div class="error-msg">分析失败: ' + escapeHtml(e.message) + '</div>';
    }
}

// 旧格式批量对比（题号+基准+批改结果）
async function runOldFormatCompare(div, useSemanticEval) {
    const { headers, rows } = excelData;
    
    const resultCols = headers.slice(2);
    const numResults = resultCols.length;
    if (numResults < 1) return alert('Excel中没有批改结果列');
    
    // 计算每列准确率
    const colStats = resultCols.map((_, ci) => {
        let correct = 0;
        rows.forEach(row => {
            const base = String(row[1] || '').trim();
            const ans = String(row[ci + 2] || '').trim();
            if (base === ans) correct++;
        });
        return { name: resultCols[ci] || '批改' + (ci + 1), correct, acc: Math.round(correct / rows.length * 100) };
    });
    
    // 每题统计
    const rowStats = rows.map(row => {
        const idx = String(row[0] || '');
        const base = String(row[1] || '').trim();
        const answers = resultCols.map((_, ci) => String(row[ci + 2] || '').trim());
        const matches = answers.map(a => a === base);
        const correctCount = matches.filter(m => m).length;
        return { idx, base, answers, matches, correctCount, allCorrect: correctCount === numResults, allWrong: correctCount === 0 };
    });
    
    const avgAcc = Math.round(colStats.reduce((s, c) => s + c.acc, 0) / numResults);
    const allCorrectCount = rowStats.filter(r => r.allCorrect).length;
    const allWrongCount = rowStats.filter(r => r.allWrong).length;
    
    // 渲染
    let html = renderStats([
        { value: rows.length, label: '总题数' },
        { value: numResults, label: '批改次数' },
        { value: avgAcc + '%', label: '平均准确率', highlight: avgAcc >= 80 },
        { value: allCorrectCount, label: '全部正确' }
    ]);
    
    html += '<div class="chart-grid"><div class="chart-box"><div class="chart-title">各次批改准确率</div><canvas id="excelChart1"></canvas></div><div class="chart-box"><div class="chart-title">题目正确率分布</div><canvas id="excelChart2"></canvas></div></div>';
    
    // 各次批改准确率表
    html += '<div class="section"><div class="section-title">各次批改准确率</div><table class="data-table"><thead><tr><th>批改</th><th>正确数</th><th>准确率</th></tr></thead><tbody>';
    colStats.forEach(c => { html += '<tr><td>' + escapeHtml(c.name) + '</td><td>' + c.correct + '/' + rows.length + '</td><td class="' + (c.acc >= 80 ? 'cell-pass' : 'cell-fail') + '">' + c.acc + '%</td></tr>'; });
    html += '</tbody></table></div>';
    
    // 逐题对比
    html += '<div class="section"><div class="section-title">逐题对比</div><div style="overflow-x:auto;"><table class="data-table"><thead><tr><th>题号</th><th>基准</th>';
    resultCols.forEach(c => html += '<th>' + escapeHtml(String(c)) + '</th>');
    html += '<th>正确率</th></tr></thead><tbody>';
    rowStats.forEach(r => {
        html += '<tr class="' + (r.allCorrect ? 'match-row' : r.allWrong ? 'mismatch-row' : '') + '"><td>' + escapeHtml(r.idx) + '</td><td>' + escapeHtml(r.base) + '</td>';
        r.answers.forEach((a, i) => html += '<td' + (r.matches[i] ? '' : ' class="diff-highlight"') + '>' + escapeHtml(a) + '</td>');
        html += '<td>' + r.correctCount + '/' + numResults + '</td></tr>';
    });
    html += '</tbody></table></div></div>';
    
    div.innerHTML = html;
    
    // 图表
    new Chart(document.getElementById('excelChart1'), {
        type: 'bar',
        data: { labels: colStats.map(c => c.name), datasets: [{ label: '准确率', data: colStats.map(c => c.acc), backgroundColor: '#111' }] },
        options: { responsive: true, plugins: { legend: { display: false } }, scales: { y: { beginAtZero: true, max: 100 } } }
    });
    new Chart(document.getElementById('excelChart2'), {
        type: 'doughnut',
        data: { labels: ['全对', '部分对', '全错'], datasets: [{ data: [allCorrectCount, rows.length - allCorrectCount - allWrongCount, allWrongCount], backgroundColor: ['#111', '#999', '#e0e0e0'] }] },
        options: { responsive: true }
    });
    
    // 保存测试结果
    lastTestResults = {
        type: 'batch_compare',
        total_questions: rows.length,
        result_columns: numResults,
        avg_accuracy: avgAcc,
        all_correct_count: allCorrectCount,
        all_wrong_count: allWrongCount,
        col_stats: colStats,
        questions: rowStats.map(r => ({ id: r.idx, standard: r.base, answers: r.answers, correct_count: r.correctCount }))
    };
    document.getElementById('jointReportBtn').disabled = !evalConfigStatus.joint_available;
    
    // 添加导出按钮
    let btnHtml = '<div style="display:flex;gap:8px;margin-top:16px;">';
    btnHtml += '<button class="btn" onclick="exportToJSON(lastTestResults, \'batch_compare.json\')">导出JSON</button>';
    btnHtml += '<button class="btn" onclick="exportToCSV(lastTestResults.questions, \'batch_compare.csv\')">导出CSV</button>';
    btnHtml += '<button class="btn" onclick="saveToHistory(\'batch\', lastTestResults)">保存到历史</button>';
    btnHtml += '<button class="btn" onclick="addToFavorites(\'result\', lastTestResults)">收藏</button>';
    btnHtml += '</div>';
    div.innerHTML += btnHtml;
}

// DeepSeek语义评估
async function runSemanticEvaluation() {
    if (!lastTestResults || !lastTestResults.problem_questions) {
        return alert('请先执行批量对比分析');
    }
    if (!evalConfigStatus.deepseek_configured) {
        return alert('请先配置DeepSeek API Key');
    }
    
    showLoading('正在进行DeepSeek语义评估...');
    
    const problemQuestions = lastTestResults.problem_questions.slice(0, 10); // 限制最多10题
    const results = [];
    
    for (const q of problemQuestions) {
        try {
            const res = await fetch('/api/deepseek/semantic-eval', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    question: `题号${q.index}`,
                    standard_answer: q.standard_answer,
                    ai_answer: q.user_answer,
                    subject: q.subject || '通用',
                    question_type: q.question_type || '客观题'
                })
            });
            const evalResult = await res.json();
            results.push({
                ...q,
                semantic_eval: evalResult
            });
        } catch (e) {
            results.push({
                ...q,
                semantic_eval: { error: e.message }
            });
        }
    }
    
    hideLoading();
    
    // 显示语义评估结果
    let html = '<div class="section" style="margin-top:24px;"><div class="section-title">🔍 DeepSeek语义评估结果</div>';
    html += '<table class="data-table"><thead><tr><th>题号</th><th>标准答案</th><th>AI答案</th><th>语义正确</th><th>得分</th><th>错误类型</th><th>说明</th></tr></thead><tbody>';
    
    results.forEach(r => {
        const eval_ = r.semantic_eval || {};
        const isCorrect = eval_.semantic_correct;
        html += '<tr>';
        html += '<td>' + escapeHtml(r.index) + '</td>';
        html += '<td>' + escapeHtml(r.standard_answer) + '</td>';
        html += '<td>' + escapeHtml(r.user_answer) + '</td>';
        html += '<td class="' + (isCorrect ? 'cell-pass' : 'cell-fail') + '">' + (isCorrect ? '✓' : '✗') + '</td>';
        html += '<td>' + (eval_.score !== undefined ? (eval_.score * 100).toFixed(0) + '%' : '-') + '</td>';
        html += '<td>' + escapeHtml(eval_.error_type || '-') + '</td>';
        html += '<td style="max-width:200px;overflow:hidden;text-overflow:ellipsis;">' + escapeHtml(eval_.explanation || eval_.error || '-') + '</td>';
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    document.getElementById('batchResult').innerHTML += html;
}

// 生成批量对比评估报告
async function generateBatchReport() {
    if (!lastTestResults) return alert('请先执行批量对比分析');
    
    showLoading('正在生成评估报告...');
    
    try {
        const res = await fetch('/api/batch-compare/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                analysis_data: lastTestResults,
                include_ai_analysis: evalConfigStatus.qwen_configured
            })
        });
        const report = await res.json();
        
        hideLoading();
        
        // 显示报告预览
        let html = '<div class="section" style="margin-top:24px;border:2px solid #1d6f8c;border-radius:12px;padding:20px;">';
        html += '<div class="section-title" style="color:#1d6f8c;">📊 评估报告预览</div>';
        html += '<p><strong>报告ID:</strong> ' + report.report_id + '</p>';
        html += '<p><strong>生成时间:</strong> ' + report.generated_at + '</p>';
        html += '<p><strong>整体准确率:</strong> <span class="' + (report.core_data.pass_threshold ? 'cell-pass' : 'cell-fail') + '">' + report.core_data.overall_accuracy + '%</span></p>';
        
        if (report.ai_analysis && !report.ai_analysis.error) {
            html += '<div style="margin-top:16px;padding:12px;background:#f5f5f7;border-radius:8px;">';
            html += '<strong>AI分析:</strong><br>';
            if (report.ai_analysis.data_interpretation) {
                html += '<p>' + escapeHtml(report.ai_analysis.data_interpretation) + '</p>';
            }
            if (report.ai_analysis.optimization_suggestions) {
                html += '<p><strong>优化建议:</strong></p><ul>';
                report.ai_analysis.optimization_suggestions.forEach(s => {
                    html += '<li>' + escapeHtml(s) + '</li>';
                });
                html += '</ul>';
            }
            html += '</div>';
        }
        
        html += '<div style="margin-top:16px;display:flex;gap:8px;">';
        html += '<button class="btn" onclick="exportBatchReport()">导出HTML报告</button>';
        html += '</div>';
        html += '</div>';
        
        document.getElementById('batchResult').innerHTML += html;
        
        // 保存报告数据
        window.lastBatchReport = report;
    } catch (e) {
        hideLoading();
        alert('生成报告失败: ' + e.message);
    }
}

// 导出批量对比报告
async function exportBatchReport() {
    if (!window.lastBatchReport) return alert('请先生成报告');
    
    try {
        const res = await fetch('/api/batch-compare/export-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report: window.lastBatchReport })
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'evaluation_report_' + window.lastBatchReport.report_id + '.html';
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

// ========== 一致性测试 ==========
async function runConsistencyTest() {
    if (!consistImage) return alert('请先上传图片');
    
    const prompt = document.getElementById('consistPrompt').value;
    const model = document.getElementById('consistModel').value;
    const n = parseInt(document.getElementById('consistRepeat').value) || 10;
    const div = document.getElementById('consistResult');
    
    // 输入验证
    const promptCheck = validateInput('prompt', prompt);
    if (!promptCheck.valid) return alert(promptCheck.msg);
    const repeatCheck = validateInput('repeatCount', n);
    if (!repeatCheck.valid) return alert(repeatCheck.msg);
    
    if (isTestRunning) return alert('测试正在进行中，请等待完成或取消');
    isTestRunning = true;
    abortController = new AbortController();
    
    // 销毁旧图表
    destroyCharts('consist');
    
    showLoading('正在执行 ' + n + ' 个并行请求...', true);
    
    try {
        // 并行执行（比串行快很多）
        const tasks = Array(n).fill(null).map(() => () => 
            callAPI(consistImage, prompt, model, { signal: abortController.signal })
        );
        const apiResults = await callAPIParallel(tasks, 5);
        
        // 处理结果
        const results = apiResults.map(r => r.error ? null : r.result).filter(r => r);
        const times = apiResults.map(r => r.time || 0);
        const tokens = apiResults.map(r => r.tokens || { total: 0 });
        const successCount = results.length;
        const errorCount = n - successCount;
        
        if (successCount === 0) {
            div.innerHTML = '<div class="section"><p style="color:#c62828;">所有请求都失败了</p></div>';
            hideLoading();
            return;
        }
        
        const norm = results.map(r => r.replace(/\s+/g, '').toLowerCase());
        const counts = {};
        norm.forEach(r => counts[r] = (counts[r] || 0) + 1);
        const unique = Object.keys(counts).length;
        const max = Math.max(...Object.values(counts));
        const cons = Math.round(max / successCount * 100);
        
        const avgTime = times.filter(t => t > 0).length > 0 
            ? (times.filter(t => t > 0).reduce((a, b) => a + b, 0) / times.filter(t => t > 0).length).toFixed(2) 
            : '-';
        const totalTokens = tokens.reduce((sum, t) => sum + (t.total || 0), 0);
        
        const groups = [], seen = new Set();
        results.forEach((r, i) => {
            const x = norm[i];
            if (!seen.has(x)) {
                seen.add(x);
                const indices = [];
                norm.forEach((n2, j) => { if (n2 === x) indices.push(j + 1); });
                groups.push({ result: r, count: counts[x], indices, time: times[i] });
            }
        });
        groups.sort((a, b) => b.count - a.count);
        
        // 渲染统计
        div.innerHTML = renderStats([
            { value: cons + '%', label: '一致性', highlight: cons >= 80 },
            { value: unique, label: '不同输出' },
            { value: max + '/' + successCount, label: '最多/成功' },
            { value: successCount + '/' + n, label: '成功/总数' },
            { value: avgTime + 's', label: '平均耗时' },
            { value: totalTokens, label: '总Token' }
        ]) + '<div class="chart-grid"><div class="chart-box"><div class="chart-title">输出分布占比</div><canvas id="consistChart1"></canvas></div><div class="chart-box"><div class="chart-title">响应耗时趋势</div><canvas id="consistChart2"></canvas></div></div>' +
        '<div class="chart-grid"><div class="chart-box"><div class="chart-title">Token 消耗</div><canvas id="consistChart3"></canvas></div><div class="chart-box"><div class="chart-title">输出长度变化</div><canvas id="consistChart4"></canvas></div></div>' +
        '<div class="section"><div class="section-title">输出分组（共 ' + unique + ' 种不同输出）</div>' +
        groups.map((g, i) => '<div class="result-card"><div class="result-header">分组 ' + (i + 1) + ' <span class="tag ' + (i === 0 ? 'tag-success' : 'tag-info') + '">' + g.count + '次 (' + Math.round(g.count / successCount * 100) + '%)</span> <span style="color:#666;font-size:11px;">第 ' + g.indices.join(', ') + ' 次</span></div><div class="result-body">' + escapeHtml(g.result) + '</div></div>').join('') + '</div>' +
        (errorCount > 0 ? '<div class="section" style="background:#ffebee;"><div class="section-title" style="color:#c62828;">失败请求 (' + errorCount + '次)</div>' +
        apiResults.filter(r => r.error).map((r, i) => '<div style="padding:8px;font-size:12px;color:#c62828;">' + escapeHtml(r.error) + '</div>').join('') + '</div>' : '') +
        '<div style="display:flex;gap:8px;margin-top:16px;">' +
        '<button class="btn" onclick="exportConsistencyResults()">导出结果</button>' +
        '<button class="btn" onclick="saveToHistory(\'consistency\', window.lastConsistencyResults)">保存到历史</button>' +
        '</div>';
        
        // 保存结果
        window.lastConsistencyResults = {
            model, prompt, n, successCount, errorCount, unique, consistency: cons,
            avgTime: parseFloat(avgTime) || 0, totalTokens, groups,
            timestamp: new Date().toISOString()
        };
        
        // 绘制图表
        chartInstances.consist.push(new Chart(document.getElementById('consistChart1'), {
            type: 'doughnut',
            data: { labels: groups.map((_, i) => '分组' + (i + 1) + ' (' + groups[i].count + '次)'), datasets: [{ data: groups.map(g => g.count), backgroundColor: groups.map((_, i) => i === 0 ? '#111' : 'hsl(0,0%,' + (50 + i * 10) + '%)') }] },
            options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
        }));
        
        chartInstances.consist.push(new Chart(document.getElementById('consistChart2'), {
            type: 'line',
            data: { labels: apiResults.map((_, i) => '' + (i + 1)), datasets: [{ label: '耗时(s)', data: times, borderColor: '#2196f3', fill: true, backgroundColor: 'rgba(33,150,243,0.1)', tension: 0.3 }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        chartInstances.consist.push(new Chart(document.getElementById('consistChart3'), {
            type: 'bar',
            data: { labels: apiResults.map((_, i) => '' + (i + 1)), datasets: [{ label: 'Token', data: tokens.map(t => t.total || 0), backgroundColor: '#ff9800' }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        chartInstances.consist.push(new Chart(document.getElementById('consistChart4'), {
            type: 'line',
            data: { labels: results.map((_, i) => '' + (i + 1)), datasets: [{ label: '输出长度', data: results.map(r => r.length), borderColor: '#111', fill: true, backgroundColor: 'rgba(0,0,0,0.05)', tension: 0.3 }] },
            options: { responsive: true, plugins: { legend: { display: false } } }
        }));
        
        // 自动更新模型统计
        updateModelStatsAuto(model, null, parseFloat(avgTime) || null, cons);
    } catch (e) {
        if (e.name === 'AbortError') {
            div.innerHTML = '<div class="section"><p style="color:#ff9800;">测试已取消</p></div>';
        } else {
            div.innerHTML = '<div class="section"><p style="color:#c62828;">错误: ' + e.message + '</p></div>';
        }
    }
    hideLoading();
}

function exportConsistencyResults() {
    if (window.lastConsistencyResults) {
        exportToJSON(window.lastConsistencyResults, 'consistency_test_' + new Date().toISOString().slice(0, 10) + '.json');
    }
}


// ========== 多模型对比 ==========
async function runMultiModelCompare() {
    if (!multiModelImage) return alert('请先上传图片');
    const prompt = document.getElementById('multiModelPrompt').value;
    const base = document.getElementById('multiModelBaseAnswer').value;
    const repeat = parseInt(document.getElementById('multiModelRepeat').value) || 3;
    const div = document.getElementById('multiModelResult');
    
    // 获取选中的模型
    const selectedModels = [];
    document.querySelectorAll('#tab3 .checkbox-row input[type="checkbox"]:checked').forEach(cb => {
        selectedModels.push(cb.value);
    });
    if (selectedModels.length < 2) return alert('请至少选择2个模型进行对比');
    
    const totalRequests = selectedModels.length * repeat;
    showLoading('正在执行 ' + totalRequests + ' 个并行请求（' + selectedModels.length + '模型 × ' + repeat + '次）...');
    
    try {
        // 使用后端并行API
        const res = await fetch('/api/multi-model-compare', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: multiModelImage, prompt: prompt, models: selectedModels, repeat: repeat })
        });
        const apiResults = await res.json();
        
        if (apiResults.error) throw new Error(apiResults.error);
        
        const modelStats = {};
        
        // 计算每个模型的统计
        selectedModels.forEach(model => {
            const r = apiResults.results[model];
            const outputs = r.outputs || [];
            const accs = outputs.map(o => calcAcc(o, base));
            const validAccs = accs.filter(a => a !== null);
            const avgAcc = validAccs.length > 0 ? Math.round(validAccs.reduce((a, b) => a + b, 0) / validAccs.length) : null;
            
            modelStats[model] = {
                name: MODELS[model]?.name || model,
                short: MODELS[model]?.short || model.substring(0, 6),
                total: r.success_count + r.error_count,
                success: r.success_count,
                avgAcc,
                consistency: r.consistency,
                unique: r.unique_outputs,
                avgTime: r.avg_time,
                avgTokens: r.avg_tokens,
                outputs: outputs,
                errors: r.errors || []
            };
        });
        
        // 找出最佳模型
        let bestModel = null, bestScore = 0;
        selectedModels.forEach(model => {
            const s = modelStats[model];
            const score = (s.avgAcc || 0) * 0.5 + s.consistency * 0.3 + (s.success / s.total * 100) * 0.2;
            if (score > bestScore) { bestScore = score; bestModel = model; }
        });
        
        // 渲染结果
        let html = '<div class="stats-grid">';
        html += '<div class="stat-card highlight"><div class="stat-value">' + selectedModels.length + '</div><div class="stat-label">对比模型数</div></div>';
        html += '<div class="stat-card"><div class="stat-value">' + totalRequests + '</div><div class="stat-label">总请求数</div></div>';
        html += '<div class="stat-card"><div class="stat-value">' + (MODELS[bestModel]?.short || '-') + '</div><div class="stat-label">推荐模型</div></div>';
        const totalSuccess = selectedModels.reduce((s, m) => s + modelStats[m].success, 0);
        html += '<div class="stat-card"><div class="stat-value">' + totalSuccess + '/' + totalRequests + '</div><div class="stat-label">成功率</div></div>';
        html += '</div>';
        
        // 模型对比表格
        html += '<div class="section"><div class="section-title">模型性能对比</div>';
        html += '<table class="data-table"><thead><tr><th>模型</th><th>成功率</th><th>平均准确率</th><th>一致性</th><th>平均耗时</th><th>不同输出</th><th>推荐</th></tr></thead><tbody>';
        selectedModels.forEach(model => {
            const s = modelStats[model];
            const isBest = model === bestModel;
            html += '<tr' + (isBest ? ' class="match-row"' : '') + '>';
            html += '<td><strong>' + s.name + '</strong></td>';
            html += '<td>' + s.success + '/' + s.total + '</td>';
            html += '<td class="' + (s.avgAcc >= 80 ? 'cell-pass' : s.avgAcc >= 60 ? '' : 'cell-fail') + '">' + (s.avgAcc !== null ? s.avgAcc + '%' : '-') + '</td>';
            html += '<td class="' + (s.consistency >= 80 ? 'cell-pass' : s.consistency >= 60 ? '' : 'cell-fail') + '">' + s.consistency + '%</td>';
            html += '<td>' + s.avgTime + 's</td>';
            html += '<td>' + s.unique + '</td>';
            html += '<td>' + (isBest ? '<span class="tag tag-success">推荐</span>' : '') + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table></div>';
        
        // 图表
        html += '<div class="chart-grid"><div class="chart-box"><div class="chart-title">模型准确率对比</div><canvas id="multiChart1"></canvas></div><div class="chart-box"><div class="chart-title">模型能力雷达图</div><canvas id="multiChart2"></canvas></div></div>';
        
        // 各模型输出详情
        html += '<div class="section"><div class="section-title">输出详情对比</div>';
        selectedModels.forEach(model => {
            const s = modelStats[model];
            html += '<div class="result-card" style="margin-bottom:12px;"><div class="result-header">' + s.name + ' <span class="tag ' + (model === bestModel ? 'tag-success' : 'tag-info') + '">' + (s.avgAcc !== null ? '准确率 ' + s.avgAcc + '%' : '一致性 ' + s.consistency + '%') + '</span> <span style="color:#666;font-size:11px;">平均 ' + s.avgTime + 's</span></div>';
            if (s.outputs.length > 0) {
                s.outputs.forEach((out, i) => {
                    html += '<div class="result-body" style="border-top:1px solid #e0e0e0;max-height:150px;"><strong>第' + (i + 1) + '次:</strong><br>' + escapeHtml(out.substring(0, 500)) + (out.length > 500 ? '...' : '') + '</div>';
                });
            }
            if (s.errors.length > 0) {
                html += '<div class="result-body" style="border-top:1px solid #e0e0e0;background:#ffebee;"><strong>错误:</strong><br>' + s.errors.map(e => escapeHtml(e)).join('<br>') + '</div>';
            }
            html += '</div>';
        });
        html += '</div>';
        
        // 导出按钮
        html += '<div style="display:flex;gap:8px;margin-top:16px;flex-wrap:wrap;">';
        html += '<button class="btn" onclick="exportMultiModelResults()">导出JSON</button>';
        html += '<button class="btn" onclick="saveToHistory(\'multi_model\', lastMultiModelResults)">保存到历史</button>';
        if (evalConfigStatus.deepseek_configured) {
            html += '<button class="btn" style="background:#2196f3;" onclick="runAIJudge()">🔍 AI仲裁</button>';
        }
        if (evalConfigStatus.qwen_configured) {
            html += '<button class="btn" style="background:#333;" onclick="generateMultiModelReport()">📊 AI分析报告</button>';
        }
        if (evalConfigStatus.joint_available) {
            html += '<button class="btn" style="background:#1d6f8c;" onclick="generateMultiModelJointReport()">📋 联合评估</button>';
        }
        html += '</div>';
        
        div.innerHTML = html;
        
        // 保存结果
        window.lastMultiModelResults = { models: selectedModels, stats: modelStats, bestModel, prompt, base, timestamp: new Date().toISOString() };
        
        // 自动更新模型统计数据
        selectedModels.forEach(model => {
            const s = modelStats[model];
            if (s.success > 0) {
                updateModelStatsAuto(model, s.avgAcc, s.avgTime, s.consistency);
            }
        });
        
        // 绘制图表
        new Chart(document.getElementById('multiChart1'), {
            type: 'bar',
            data: {
                labels: selectedModels.map(m => MODELS[m]?.short || m),
                datasets: [
                    { label: '准确率', data: selectedModels.map(m => modelStats[m].avgAcc || 0), backgroundColor: '#111' },
                    { label: '一致性', data: selectedModels.map(m => modelStats[m].consistency), backgroundColor: '#666' }
                ]
            },
            options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true, max: 100 } } }
        });
        new Chart(document.getElementById('multiChart2'), {
            type: 'radar',
            data: {
                labels: ['准确率', '一致性', '成功率', '速度(反)'],
                datasets: selectedModels.map((m, i) => ({
                    label: MODELS[m]?.short || m,
                    data: [modelStats[m].avgAcc || 0, modelStats[m].consistency, modelStats[m].success / modelStats[m].total * 100, Math.max(0, 100 - modelStats[m].avgTime * 5)],
                    borderColor: 'hsl(' + (i * 60) + ',70%,50%)',
                    backgroundColor: 'hsla(' + (i * 60) + ',70%,50%,0.1)'
                }))
            },
            options: { responsive: true, scales: { r: { beginAtZero: true, max: 100 } } }
        });
        
    } catch (e) {
        div.innerHTML = '<div class="section"><p style="color:#c62828;">错误: ' + e.message + '</p></div>';
    }
    hideLoading();
}

async function generateMultiModelReport() {
    if (!window.lastMultiModelResults) return alert('请先执行多模型对比');
    showLoading('正在生成AI分析报告...');
    try {
        const res = await fetch('/api/qwen/macro-analysis', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_results: window.lastMultiModelResults, analysis_type: 'comparison' })
        });
        const report = await res.json();
        if (report.error) {
            alert('生成报告失败: ' + report.error);
        } else {
            let html = '<div class="summary-box" style="margin-top:24px;"><h4>🤖 AI分析报告</h4><div class="summary-content">';
            if (report.summary) html += report.summary + '\n\n';
            if (report.model_comparison) {
                const mc = report.model_comparison;
                if (mc.best_overall) html += '推荐模型: ' + mc.best_overall + '\n';
            }
            if (report.recommendations) {
                const rec = report.recommendations;
                if (rec.model_selection) html += '\n选型建议: ' + rec.model_selection;
                if (rec.prompt_optimization) html += '\n优化方向: ' + rec.prompt_optimization;
            }
            if (report.result) html += report.result;
            html += '</div></div>';
            document.getElementById('multiModelResult').innerHTML += html;
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function exportMultiModelResults() {
    if (window.lastMultiModelResults) {
        exportToJSON(window.lastMultiModelResults, 'multi_model_compare_' + new Date().toISOString().slice(0, 10) + '.json');
    }
}

// ========== 评估配置 ==========
async function checkEvalConfig() {
    try {
        const res = await fetch('/api/eval/config-status');
        evalConfigStatus = await res.json();
        updateEvalModeUI();
    } catch (e) {
        console.error('Failed to check eval config:', e);
    }
}

function updateEvalModeUI() {
    const statusDiv = document.getElementById('evalModeStatus');
    const semanticCheckbox = document.getElementById('useSemanticEval');
    const jointBtn = document.getElementById('jointReportBtn');
    
    if (statusDiv) {
        if (evalConfigStatus.joint_available) {
            statusDiv.innerHTML = '✅ 联合评估可用（Qwen宏观分析 + DeepSeek微观评估）';
        } else if (evalConfigStatus.qwen_configured) {
            statusDiv.innerHTML = '⚠️ 仅Qwen可用（宏观分析）- 请配置DeepSeek以启用语义评估';
        } else if (evalConfigStatus.deepseek_configured) {
            statusDiv.innerHTML = '⚠️ 仅DeepSeek可用（微观评估）- 请配置Qwen以启用宏观分析';
        } else {
            statusDiv.innerHTML = '❌ 未配置评估模型 - 请在主页设置中配置API Key';
        }
    }
    
    if (semanticCheckbox) semanticCheckbox.disabled = !evalConfigStatus.deepseek_configured;
    if (jointBtn) jointBtn.disabled = !evalConfigStatus.joint_available || !lastTestResults;
}

// ========== 联合报告 ==========
async function generateJointReport() {
    if (!lastTestResults) return alert('请先执行测试');
    if (!evalConfigStatus.joint_available) return alert('请配置Qwen和DeepSeek API Key');
    
    showLoading('正在生成联合评估报告...');
    
    try {
        const res = await fetch('/api/eval/joint-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_results: lastTestResults, questions: lastTestResults.questions || [] })
        });
        const report = await res.json();
        
        if (report.error) {
            alert('生成报告失败: ' + report.error);
            hideLoading();
            return;
        }
        
        showJointReport(report);
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function showJointReport(report) {
    const modal = document.getElementById('jointReportModal');
    const content = document.getElementById('jointReportContent');
    
    let html = '<div style="display:grid;gap:20px;">';
    
    // 报告头部
    html += '<div style="background:#f5f5f5;padding:16px;border-radius:8px;">';
    html += '<div style="font-size:12px;color:#666;">报告ID: ' + report.test_id + ' | 生成时间: ' + new Date(report.generated_at).toLocaleString() + '</div>';
    html += '<div style="font-size:12px;color:#666;margin-top:4px;">评估模式: ' + (report.final_conclusion.evaluation_mode === 'joint' ? '联合评估' : '单模型评估') + '</div>';
    html += '</div>';
    
    // Qwen宏观分析
    if (report.macro_analysis) {
        html += '<div style="border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">';
        html += '<div style="background:#111;color:#fff;padding:12px 16px;font-size:13px;font-weight:600;">📊 宏观分析（Qwen3-Max）</div>';
        html += '<div style="padding:16px;">';
        if (report.macro_analysis.summary) html += '<p style="margin-bottom:12px;">' + escapeHtml(report.macro_analysis.summary) + '</p>';
        if (report.macro_analysis.model_comparison) {
            const mc = report.macro_analysis.model_comparison;
            if (mc.best_overall) html += '<div style="background:#e8f5e9;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-size:13px;">🏆 推荐模型: <strong>' + escapeHtml(mc.best_overall) + '</strong></div>';
        }
        if (report.macro_analysis.recommendations) {
            const rec = report.macro_analysis.recommendations;
            html += '<div style="font-size:12px;color:#666;">';
            if (rec.model_selection) html += '<p>• 选型建议: ' + escapeHtml(rec.model_selection) + '</p>';
            if (rec.prompt_optimization) html += '<p>• 优化方向: ' + escapeHtml(rec.prompt_optimization) + '</p>';
            html += '</div>';
        }
        if (report.macro_analysis.raw) html += '<pre style="background:#f5f5f5;padding:12px;border-radius:4px;font-size:11px;overflow-x:auto;">' + escapeHtml(report.macro_analysis.raw) + '</pre>';
        html += '</div></div>';
    }
    
    // DeepSeek微观评估
    if (report.micro_evaluation && report.micro_evaluation.per_question_results) {
        html += '<div style="border:1px solid #e0e0e0;border-radius:8px;overflow:hidden;">';
        html += '<div style="background:#333;color:#fff;padding:12px 16px;font-size:13px;font-weight:600;">🔍 微观评估（DeepSeek）</div>';
        html += '<div style="padding:16px;max-height:300px;overflow-y:auto;">';
        report.micro_evaluation.per_question_results.forEach((r, i) => {
            const correct = r.semantic_correct;
            html += '<div style="padding:8px;border-bottom:1px solid #e0e0e0;font-size:12px;">';
            html += '<span style="display:inline-block;width:60px;">题目 ' + (r.question_id || (i + 1)) + '</span>';
            html += '<span class="tag ' + (correct ? 'tag-success' : 'tag-error') + '">' + (correct ? '正确' : '错误') + '</span>';
            if (r.score !== undefined) html += ' <span style="color:#666;">得分: ' + (r.score * 100).toFixed(0) + '%</span>';
            if (r.explanation) html += '<div style="color:#666;margin-top:4px;">' + escapeHtml(r.explanation) + '</div>';
            html += '</div>';
        });
        html += '</div></div>';
    }
    
    // 分歧点
    if (report.discrepancies && report.discrepancies.length > 0) {
        html += '<div style="border:1px solid #ff9800;border-radius:8px;overflow:hidden;">';
        html += '<div style="background:#ff9800;color:#fff;padding:12px 16px;font-size:13px;font-weight:600;">⚠️ 评估分歧</div>';
        html += '<div style="padding:16px;">';
        report.discrepancies.forEach(d => {
            html += '<div style="padding:8px;background:#fff3e0;border-radius:4px;margin-bottom:8px;font-size:12px;">';
            html += '<div><strong>题目 ' + d.question_id + '</strong></div>';
            html += '<div>Qwen观点: ' + escapeHtml(d.qwen_opinion || '-') + '</div>';
            html += '<div>DeepSeek观点: ' + escapeHtml(d.deepseek_opinion || '-') + '</div>';
            html += '</div>';
        });
        html += '</div></div>';
    }
    
    html += '</div>';
    
    content.innerHTML = html;
    modal.style.display = 'flex';
}

function closeJointReport() {
    document.getElementById('jointReportModal').style.display = 'none';
}

// ========== 历史记录 ==========
async function saveToHistory(testType, data) {
    try {
        await fetch('/api/history', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ testType, data, model: document.getElementById(testType === 'single' ? 'singleModel' : 'consistModel')?.value || '' })
        });
    } catch (e) { console.error('保存历史失败:', e); }
}

async function loadHistory() {
    try {
        const res = await fetch('/api/history');
        return await res.json();
    } catch (e) { return []; }
}

async function refreshHistory() {
    const list = document.getElementById('historyList');
    list.innerHTML = '<p style="color:#666;">加载中...</p>';
    const history = await loadHistory();
    if (!history.length) {
        list.innerHTML = '<p style="color:#666;">暂无历史记录</p>';
        return;
    }
    let html = '<div style="display:flex;flex-direction:column;gap:8px;">';
    history.forEach(h => {
        html += '<div class="result-card"><div class="result-header">';
        html += '<span>' + (h.testType || '测试') + ' - ' + (h.model || '未知模型') + '</span>';
        html += '<span style="color:#666;font-size:11px;">' + new Date(h.timestamp).toLocaleString() + '</span>';
        html += '</div><div class="result-body" style="max-height:100px;">';
        html += '<pre style="font-size:11px;">' + escapeHtml(JSON.stringify(h.data || {}, null, 2).substring(0, 500)) + '...</pre>';
        html += '</div><div style="padding:8px;display:flex;gap:8px;">';
        html += '<button class="btn-small" onclick="exportToJSON(' + JSON.stringify(h).replace(/"/g, '&quot;') + ', \'history_' + h.id + '.json\')">导出JSON</button>';
        html += '<button class="btn-small" onclick="deleteHistory(\'' + h.id + '\')">删除</button>';
        html += '</div></div>';
    });
    html += '</div>';
    list.innerHTML = html;
}

async function deleteHistory(id) {
    if (!confirm('确定删除此记录？')) return;
    await fetch('/api/history', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id }) });
    refreshHistory();
}

async function clearAllHistory() {
    if (!confirm('确定清空所有历史记录？')) return;
    await fetch('/api/history', { method: 'DELETE', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ id: 'all' }) });
    refreshHistory();
}

// ========== 导出功能 ==========
function exportToJSON(data, filename) {
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename || 'export.json';
    a.click(); URL.revokeObjectURL(url);
}

function exportToCSV(rows, filename) {
    if (!rows || !rows.length) return;
    const headers = Object.keys(rows[0]);
    let csv = headers.join(',') + '\n';
    rows.forEach(row => { csv += headers.map(h => '"' + String(row[h] || '').replace(/"/g, '""') + '"').join(',') + '\n'; });
    const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url; a.download = filename || 'export.csv';
    a.click(); URL.revokeObjectURL(url);
}

// ========== 收藏功能 ==========
async function addToFavorites(type, data) {
    try {
        const res = await fetch('/api/favorites', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, data })
        });
        if (res.ok) alert('已添加到收藏');
    } catch (e) { alert('收藏失败: ' + e.message); }
}

// ========== 模型推荐 ==========
let lastRecommendation = null;
let recommendChartInstances = {};

async function getModelRecommendation(scenario, useAI = false) {
    try {
        const subject = document.getElementById('recommendSubject')?.value || '';
        const res = await fetch('/api/recommend', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ scenario: scenario || 'balanced', use_ai: useAI, subject })
        });
        return await res.json();
    } catch (e) { return null; }
}

async function updateRecommendation() {
    const scenario = document.getElementById('recommendScenario').value;
    const div = document.getElementById('recommendResult');
    const statsDiv = document.getElementById('historyStatsOverview');
    
    div.innerHTML = '<p style="color:#666;text-align:center;padding:20px;">📊 分析中...</p>';
    
    const rec = await getModelRecommendation(scenario, false);
    if (!rec) { 
        div.innerHTML = '<p style="color:#c62828;">获取推荐失败</p>'; 
        return; 
    }
    
    lastRecommendation = rec;
    
    // 渲染历史数据统计概览
    renderHistoryStatsOverview(rec, statsDiv);
    
    // 渲染推荐结果
    renderRecommendationResult(rec, div);
    
    // 渲染图表
    renderRecommendationCharts(rec);
}

function renderHistoryStatsOverview(rec, container) {
    const hasData = rec.has_history_data;
    const totalTests = rec.rankings.reduce((sum, r) => sum + (r.total_tests || 0), 0);
    const modelsWithData = rec.rankings.filter(r => r.total_tests > 0).length;
    
    let html = '<div class="stats-grid">';
    html += '<div class="stat-card' + (hasData ? ' highlight' : '') + '"><div class="stat-value">' + (hasData ? '✓' : '✗') + '</div><div class="stat-label">历史数据</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + totalTests + '</div><div class="stat-label">总测试次数</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + modelsWithData + '/' + rec.rankings.length + '</div><div class="stat-label">有数据模型</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + rec.scenario_name + '</div><div class="stat-label">当前策略</div></div>';
    html += '</div>';
    
    if (!hasData) {
        html += '<div style="background:#fff3e0;padding:12px 16px;border-radius:8px;margin-top:12px;font-size:13px;color:#e65100;">';
        html += '⚠️ 暂无历史测试数据，当前推荐基于默认模型特性。建议先进行一些测试以获得更准确的推荐。';
        html += '</div>';
    }
    
    container.innerHTML = html;
}

function renderRecommendationResult(rec, container) {
    let html = '';
    
    // 推荐模型卡片
    if (rec.recommended) {
        const r = rec.recommended;
        html += '<div style="background:linear-gradient(135deg,#1d1d1f 0%,#2d2d2f 100%);color:#fff;padding:24px;border-radius:16px;margin-bottom:24px;">';
        html += '<div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:16px;">';
        html += '<div>';
        html += '<div style="font-size:12px;color:rgba(255,255,255,0.6);margin-bottom:4px;">🏆 推荐模型</div>';
        html += '<div style="font-size:24px;font-weight:700;">' + r.name + '</div>';
        html += '<div style="font-size:13px;color:rgba(255,255,255,0.8);margin-top:8px;">' + rec.reason + '</div>';
        html += '</div>';
        html += '<div style="text-align:right;">';
        html += '<div style="font-size:36px;font-weight:700;">' + r.score + '</div>';
        html += '<div style="font-size:11px;color:rgba(255,255,255,0.6);">综合评分</div>';
        html += '</div>';
        html += '</div>';
        
        // 指标条
        html += '<div style="display:grid;grid-template-columns:repeat(auto-fit,minmax(120px,1fr));gap:16px;margin-top:20px;padding-top:20px;border-top:1px solid rgba(255,255,255,0.1);">';
        html += renderMetricBar('准确率', r.accuracy, '#4caf50');
        html += renderMetricBar('速度', r.speed, '#2196f3');
        html += renderMetricBar('成本效益', r.cost, '#ff9800');
        if (r.avg_consistency) html += renderMetricBar('一致性', r.avg_consistency, '#9c27b0');
        html += '</div>';
        
        // 优势标签
        if (r.strengths && r.strengths.length > 0) {
            html += '<div style="margin-top:16px;display:flex;flex-wrap:wrap;gap:8px;">';
            r.strengths.forEach(s => {
                html += '<span style="background:rgba(255,255,255,0.15);padding:4px 12px;border-radius:20px;font-size:12px;">' + s + '</span>';
            });
            html += '</div>';
        }
        
        // 适用场景
        if (r.best_for && r.best_for.length > 0) {
            html += '<div style="margin-top:12px;font-size:12px;color:rgba(255,255,255,0.7);">适用场景: ' + r.best_for.join(' / ') + '</div>';
        }
        
        // 数据来源
        html += '<div style="margin-top:12px;font-size:11px;color:rgba(255,255,255,0.5);">';
        html += '数据来源: ' + r.data_source;
        if (r.total_tests > 0) html += ' | 测试次数: ' + r.total_tests;
        if (r.last_updated) html += ' | 更新: ' + new Date(r.last_updated).toLocaleDateString();
        html += '</div>';
        
        html += '</div>';
    }
    
    // 模型排名表格
    html += '<div style="margin-top:24px;">';
    html += '<div style="font-size:16px;font-weight:600;margin-bottom:16px;">📋 模型排名详情</div>';
    html += '<div style="overflow-x:auto;">';
    html += '<table class="data-table"><thead><tr>';
    html += '<th>排名</th><th>模型</th><th>综合分</th><th>准确率</th><th>速度</th><th>成本</th><th>测试次数</th><th>平均耗时</th><th>数据来源</th>';
    html += '</tr></thead><tbody>';
    
    rec.rankings.forEach((r, i) => {
        const isTop = i === 0;
        html += '<tr' + (isTop ? ' class="match-row"' : '') + '>';
        html += '<td><strong>' + (i + 1) + '</strong></td>';
        html += '<td><strong>' + r.name + '</strong></td>';
        html += '<td class="' + (r.score >= 80 ? 'cell-pass' : '') + '"><strong>' + r.score + '</strong></td>';
        html += '<td>' + r.accuracy + '%</td>';
        html += '<td>' + r.speed + '%</td>';
        html += '<td>' + r.cost + '%</td>';
        html += '<td>' + (r.total_tests || 0) + '</td>';
        html += '<td>' + (r.avg_time ? r.avg_time + 's' : '-') + '</td>';
        html += '<td><span class="tag ' + (r.data_source === '历史数据' ? 'tag-success' : 'tag-info') + '">' + r.data_source + '</span></td>';
        html += '</tr>';
    });
    
    html += '</tbody></table></div></div>';
    
    container.innerHTML = html;
}

function renderMetricBar(label, value, color) {
    return '<div>' +
        '<div style="display:flex;justify-content:space-between;font-size:11px;margin-bottom:4px;">' +
        '<span>' + label + '</span><span>' + value + '%</span></div>' +
        '<div style="height:6px;background:rgba(255,255,255,0.2);border-radius:3px;overflow:hidden;">' +
        '<div style="width:' + value + '%;height:100%;background:' + color + ';border-radius:3px;"></div>' +
        '</div></div>';
}

function renderRecommendationCharts(rec) {
    const chartsDiv = document.getElementById('recommendCharts');
    const chartsDiv2 = document.getElementById('recommendCharts2');
    
    if (!rec.rankings || rec.rankings.length === 0) {
        chartsDiv.style.display = 'none';
        chartsDiv2.style.display = 'none';
        return;
    }
    
    chartsDiv.style.display = 'grid';
    chartsDiv2.style.display = 'grid';
    
    // 销毁旧图表
    Object.values(recommendChartInstances).forEach(chart => chart?.destroy());
    recommendChartInstances = {};
    
    const labels = rec.rankings.map(r => r.name);
    const colors = ['#1d1d1f', '#666666', '#999999', '#cccccc', '#e0e0e0'];
    
    // 雷达图
    const radarCtx = document.getElementById('radarChart');
    if (radarCtx) {
        recommendChartInstances.radar = new Chart(radarCtx, {
            type: 'radar',
            data: {
                labels: ['准确率', '速度', '成本效益', '一致性', '成功率'],
                datasets: rec.rankings.slice(0, 5).map((r, i) => ({
                    label: r.name,
                    data: [r.accuracy, r.speed, r.cost, r.avg_consistency || 80, r.success_rate || 95],
                    borderColor: 'hsl(' + (i * 72) + ',60%,50%)',
                    backgroundColor: 'hsla(' + (i * 72) + ',60%,50%,0.1)',
                    borderWidth: 2
                }))
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                scales: { r: { beginAtZero: true, max: 100, ticks: { stepSize: 20 } } },
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } }
            }
        });
    }
    
    // 综合评分柱状图
    const barCtx = document.getElementById('scoreBarChart');
    if (barCtx) {
        recommendChartInstances.bar = new Chart(barCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '综合评分',
                    data: rec.rankings.map(r => r.score),
                    backgroundColor: rec.rankings.map((_, i) => i === 0 ? '#1d1d1f' : '#999'),
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { display: false } },
                scales: { y: { beginAtZero: true, max: 100 } }
            }
        });
    }
    
    // 响应时间图表
    const timeCtx = document.getElementById('timeChart');
    if (timeCtx) {
        recommendChartInstances.time = new Chart(timeCtx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: '平均耗时(秒)',
                    data: rec.rankings.map(r => r.avg_time || 0),
                    backgroundColor: '#2196f3',
                    borderRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                indexAxis: 'y',
                plugins: { legend: { display: false } }
            }
        });
    }
    
    // 测试次数图表
    const countCtx = document.getElementById('testCountChart');
    if (countCtx) {
        recommendChartInstances.count = new Chart(countCtx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: rec.rankings.map(r => r.total_tests || 0),
                    backgroundColor: rec.rankings.map((_, i) => 'hsl(' + (i * 72) + ',60%,60%)')
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: { legend: { position: 'bottom', labels: { boxWidth: 12, font: { size: 11 } } } }
            }
        });
    }
}

// AI深度分析
async function runAIAnalysis() {
    if (!lastRecommendation) {
        alert('请先获取推荐结果');
        return;
    }
    
    const btn = document.getElementById('aiAnalysisBtn');
    const resultDiv = document.getElementById('aiAnalysisResult');
    
    btn.disabled = true;
    btn.textContent = '分析中...';
    resultDiv.style.display = 'block';
    resultDiv.innerHTML = '<div style="text-align:center;padding:40px;color:#666;"><div class="spinner" style="margin:0 auto 16px;"></div>正在调用 Qwen3-Max 进行深度分析...</div>';
    
    try {
        const scenario = document.getElementById('recommendScenario').value;
        const rec = await getModelRecommendation(scenario, true);
        
        if (rec.error) {
            resultDiv.innerHTML = '<div style="background:#ffebee;padding:16px;border-radius:8px;color:#c62828;">❌ ' + rec.error + '</div>';
        } else if (rec.ai_analysis) {
            renderAIAnalysisResult(rec.ai_analysis, resultDiv);
        } else {
            resultDiv.innerHTML = '<div style="background:#fff3e0;padding:16px;border-radius:8px;color:#e65100;">⚠️ AI分析未返回结果，请确保已配置Qwen API Key且有足够的历史数据</div>';
        }
    } catch (e) {
        resultDiv.innerHTML = '<div style="background:#ffebee;padding:16px;border-radius:8px;color:#c62828;">❌ 错误: ' + e.message + '</div>';
    }
    
    btn.disabled = false;
    btn.textContent = 'AI深度分析';
}

function renderAIAnalysisResult(analysis, container) {
    let html = '<div class="summary-box" style="margin-top:24px;">';
    html += '<h4>🤖 Qwen3-Max 智能分析报告</h4>';
    html += '<div class="summary-content">';
    
    if (analysis.error) {
        html += '<p style="color:#ff6b6b;">分析出错: ' + analysis.error + '</p>';
    } else if (analysis.raw) {
        html += '<p>' + escapeHtml(analysis.raw) + '</p>';
    } else {
        // 数据分析
        if (analysis.data_analysis) {
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:8px;">📊 数据分析</div>';
            html += '<p style="font-size:14px;line-height:1.8;">' + escapeHtml(analysis.data_analysis) + '</p>';
            html += '</div>';
        }
        
        // 推荐理由
        if (analysis.recommendation_reason) {
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:8px;">💡 推荐理由</div>';
            html += '<p style="font-size:14px;line-height:1.8;">' + escapeHtml(analysis.recommendation_reason) + '</p>';
            html += '</div>';
        }
        
        // 使用建议
        if (analysis.usage_suggestions && analysis.usage_suggestions.length > 0) {
            html += '<div style="margin-bottom:16px;">';
            html += '<div style="font-size:13px;font-weight:600;color:rgba(255,255,255,0.9);margin-bottom:8px;">使用建议</div>';
            html += '<ul style="margin:0;padding-left:20px;">';
            analysis.usage_suggestions.forEach(s => {
                html += '<li style="margin-bottom:6px;font-size:14px;">' + escapeHtml(s) + '</li>';
            });
            html += '</ul></div>';
        }
        
        // 注意事项
        if (analysis.cautions && analysis.cautions.length > 0) {
            html += '<div>';
            html += '<div style="font-size:13px;font-weight:600;color:#ff9800;margin-bottom:8px;">⚠️ 注意事项</div>';
            html += '<ul style="margin:0;padding-left:20px;">';
            analysis.cautions.forEach(c => {
                html += '<li style="margin-bottom:6px;font-size:14px;color:rgba(255,255,255,0.8);">' + escapeHtml(c) + '</li>';
            });
            html += '</ul></div>';
        }
    }
    
    html += '</div></div>';
    container.innerHTML = html;
}

// 手动提交统计数据
async function submitManualStats() {
    const model = document.getElementById('manualModel').value;
    const accuracy = parseFloat(document.getElementById('manualAccuracy').value);
    const time = parseFloat(document.getElementById('manualTime').value);
    const consistency = parseFloat(document.getElementById('manualConsistency').value);
    
    if (isNaN(accuracy) && isNaN(time) && isNaN(consistency)) {
        alert('请至少填写一项数据');
        return;
    }
    
    try {
        const res = await fetch('/api/model-stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model_id: model,
                accuracy: isNaN(accuracy) ? null : accuracy,
                time: isNaN(time) ? null : time,
                consistency: isNaN(consistency) ? null : consistency,
                success: true
            })
        });
        
        if (res.ok) {
            alert('数据提交成功！');
            // 清空输入
            document.getElementById('manualAccuracy').value = '';
            document.getElementById('manualTime').value = '';
            document.getElementById('manualConsistency').value = '';
            // 刷新推荐
            updateRecommendation();
        } else {
            alert('提交失败');
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
}

// 重置统计数据
async function resetModelStats() {
    if (!confirm('确定要重置所有模型的统计数据吗？此操作不可恢复。')) return;
    
    try {
        const res = await fetch('/api/model-stats/reset', { method: 'POST' });
        if (res.ok) {
            alert('统计数据已重置');
            updateRecommendation();
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
}

// 导出统计数据
async function exportModelStats() {
    try {
        const res = await fetch('/api/model-stats');
        const data = await res.json();
        exportToJSON(data, 'model_stats_' + new Date().toISOString().slice(0, 10) + '.json');
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

// 自动更新模型统计（测试完成后调用）
async function updateModelStatsAuto(modelId, accuracy, time, consistency) {
    try {
        await fetch('/api/model-stats', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                model_id: modelId,
                accuracy: accuracy,
                time: time,
                consistency: consistency,
                success: true
            })
        });
        console.log('模型统计已更新:', modelId);
    } catch (e) {
        console.error('更新模型统计失败:', e);
    }
}

// ========== 快捷键和拖拽 ==========
document.addEventListener('keydown', e => {
    if (e.ctrlKey && e.key === 'Enter') {
        if (currentTab === 0) runSingleTest();
        else if (currentTab === 1) runExcelCompare();
        else if (currentTab === 2) runConsistencyTest();
        else if (currentTab === 3) runMultiModelCompare();
    }
    if (e.key === 'Escape') {
        closeJointReport();
        hideLoading();
    }
});

document.addEventListener('dragover', e => e.preventDefault());
document.addEventListener('drop', e => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (!file) return;
    if (file.type.startsWith('image/')) {
        const reader = new FileReader();
        reader.onload = ev => {
            if (currentTab === 0) { singleImage = ev.target.result; document.getElementById('preview0').src = singleImage; document.getElementById('preview0').style.display = 'block'; document.getElementById('uploadArea0').classList.add('has-file'); }
            else if (currentTab === 2) { consistImage = ev.target.result; document.getElementById('preview2').src = consistImage; document.getElementById('preview2').style.display = 'block'; document.getElementById('uploadArea2').classList.add('has-file'); }
            else if (currentTab === 3) { multiModelImage = ev.target.result; document.getElementById('preview3').src = multiModelImage; document.getElementById('preview3').style.display = 'block'; document.getElementById('uploadArea3').classList.add('has-file'); }
        };
        reader.readAsDataURL(file);
    } else if (file.name.endsWith('.xlsx') || file.name.endsWith('.xls')) {
        document.getElementById('excelFile').files = e.dataTransfer.files;
        document.getElementById('excelFile').dispatchEvent(new Event('change'));
    }
});

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    // 设置文件上传
    setupUpload('singleImg', 'preview0', 'uploadArea0', d => singleImage = d);
    setupUpload('consistImg', 'preview2', 'uploadArea2', d => consistImage = d);
    setupUpload('multiModelImg', 'preview3', 'uploadArea3', d => multiModelImage = d);
    setupExcelUpload();
    
    // 加载保存的提示词
    loadSavedPrompts();
    
    // 检查配置
    checkEvalConfig();
    
    // 初始化页面
    if (document.getElementById('historyList')) refreshHistory();
    if (document.getElementById('recommendResult')) updateRecommendation();
});

// ========== 返回导航 ==========
function goBack() {
    if (window.history.length > 1) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}


// ========== AI仲裁功能 ==========
async function runAIJudge() {
    if (!window.lastMultiModelResults) return alert('请先执行多模型对比');
    if (!evalConfigStatus.deepseek_configured) return alert('请先配置DeepSeek API Key');
    
    const { models, stats, prompt } = window.lastMultiModelResults;
    
    // 收集各模型的输出
    const modelOutputs = {};
    models.forEach(model => {
        const s = stats[model];
        if (s && s.outputs && s.outputs.length > 0) {
            modelOutputs[model] = {
                name: s.name,
                output: s.outputs[0], // 取第一个输出
                accuracy: s.avgAcc,
                consistency: s.consistency
            };
        }
    });
    
    if (Object.keys(modelOutputs).length < 2) {
        return alert('需要至少2个模型的有效输出才能进行仲裁');
    }
    
    showLoading('正在调用DeepSeek进行AI仲裁...');
    
    try {
        const res = await fetch('/api/deepseek/judge', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                question: prompt,
                model_outputs: modelOutputs
            })
        });
        const result = await res.json();
        
        if (result.error) {
            alert('AI仲裁失败: ' + result.error);
            hideLoading();
            return;
        }
        
        // 显示仲裁结果
        showAIJudgeResult(result);
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function showAIJudgeResult(result) {
    let html = '<div class="summary-box" style="margin-top:24px;border:2px solid #2196f3;">';
    html += '<h4>🔍 DeepSeek AI仲裁结果</h4>';
    html += '<div class="summary-content" style="background:#e3f2fd;">';
    
    // 推荐模型
    if (result.recommendation) {
        html += '<div style="background:#1976d2;color:#fff;padding:12px 16px;border-radius:8px;margin-bottom:16px;">';
        html += '<div style="font-size:12px;opacity:0.8;">🏆 推荐模型</div>';
        html += '<div style="font-size:20px;font-weight:700;">' + escapeHtml(result.recommendation) + '</div>';
        html += '</div>';
    }
    
    // 排名
    if (result.ranking && result.ranking.length > 0) {
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">📊 模型排名</div>';
        html += '<div style="display:flex;gap:8px;flex-wrap:wrap;">';
        result.ranking.forEach((model, i) => {
            const medal = i === 0 ? '🥇' : i === 1 ? '🥈' : i === 2 ? '🥉' : (i + 1) + '.';
            html += '<span style="background:#fff;padding:6px 12px;border-radius:20px;font-size:13px;">' + medal + ' ' + escapeHtml(model) + '</span>';
        });
        html += '</div></div>';
    }
    
    // 评估理由
    if (result.reason) {
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">💡 评估理由</div>';
        html += '<p style="font-size:14px;line-height:1.6;color:#333;">' + escapeHtml(result.reason) + '</p>';
        html += '</div>';
    }
    
    // 各维度评分
    if (result.dimensions) {
        html += '<div style="margin-bottom:16px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">📈 各维度评分</div>';
        html += '<table class="data-table" style="font-size:12px;"><thead><tr><th>模型</th>';
        const dims = Object.keys(result.dimensions);
        dims.forEach(dim => html += '<th>' + escapeHtml(dim) + '</th>');
        html += '</tr></thead><tbody>';
        
        // 获取所有模型
        const allModels = new Set();
        dims.forEach(dim => {
            Object.keys(result.dimensions[dim] || {}).forEach(m => allModels.add(m));
        });
        
        allModels.forEach(model => {
            html += '<tr><td><strong>' + escapeHtml(model) + '</strong></td>';
            dims.forEach(dim => {
                const score = result.dimensions[dim]?.[model];
                const scorePercent = score !== undefined ? (score * 100).toFixed(0) + '%' : '-';
                html += '<td class="' + (score >= 0.8 ? 'cell-pass' : score >= 0.6 ? '' : 'cell-fail') + '">' + scorePercent + '</td>';
            });
            html += '</tr>';
        });
        html += '</tbody></table></div>';
    }
    
    // 详细反馈
    if (result.detailed_feedback) {
        html += '<div>';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">📝 详细反馈</div>';
        html += '<pre style="background:#fff;padding:12px;border-radius:8px;font-size:11px;overflow-x:auto;white-space:pre-wrap;">' + escapeHtml(JSON.stringify(result.detailed_feedback, null, 2)) + '</pre>';
        html += '</div>';
    }
    
    html += '</div></div>';
    
    document.getElementById('multiModelResult').innerHTML += html;
}

// ========== 多模型联合评估 ==========
async function generateMultiModelJointReport() {
    if (!window.lastMultiModelResults) return alert('请先执行多模型对比');
    if (!evalConfigStatus.joint_available) return alert('请配置Qwen和DeepSeek API Key以启用联合评估');
    
    const { models, stats, prompt, base } = window.lastMultiModelResults;
    
    showLoading('正在生成联合评估报告（Qwen宏观分析 + DeepSeek微观评估）...');
    
    try {
        // 准备测试数据
        const testResults = {
            type: 'multi_model',
            models: models,
            model_stats: stats,
            prompt: prompt,
            base_answer: base,
            timestamp: new Date().toISOString()
        };
        
        // 准备问题列表（如果有基准答案）
        let questions = [];
        if (base) {
            try {
                const baseData = JSON.parse(base);
                questions = baseData.map(item => ({
                    index: item.index,
                    standard_answer: item.answer || item.mainAnswer || ''
                }));
            } catch (e) {
                console.warn('解析基准答案失败:', e);
            }
        }
        
        const res = await fetch('/api/eval/joint-report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                test_results: testResults,
                questions: questions
            })
        });
        const report = await res.json();
        
        if (report.error) {
            alert('生成报告失败: ' + report.error);
            hideLoading();
            return;
        }
        
        showJointReport(report);
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

// ========== 单模型降级提示 ==========
function showDegradedModeWarning(container, mode) {
    let html = '<div style="background:#fff3e0;border:1px solid #ff9800;border-radius:8px;padding:12px 16px;margin-bottom:16px;font-size:13px;">';
    html += '<div style="display:flex;align-items:center;gap:8px;">';
    html += '<span style="font-size:18px;">⚠️</span>';
    html += '<div>';
    
    if (mode === 'qwen_only') {
        html += '<strong>降级模式：仅Qwen宏观分析可用</strong>';
        html += '<p style="margin:4px 0 0;color:#666;">请配置DeepSeek API Key以启用语义评估和AI仲裁功能</p>';
    } else if (mode === 'deepseek_only') {
        html += '<strong>降级模式：仅DeepSeek微观评估可用</strong>';
        html += '<p style="margin:4px 0 0;color:#666;">请配置Qwen API Key以启用宏观分析和智能报告功能</p>';
    } else {
        html += '<strong>评估功能不可用</strong>';
        html += '<p style="margin:4px 0 0;color:#666;">请在主页设置中配置Qwen和DeepSeek API Key</p>';
    }
    
    html += '</div></div></div>';
    
    if (container) {
        container.insertAdjacentHTML('afterbegin', html);
    }
    return html;
}

// 检查并显示降级提示
function checkAndShowDegradedMode() {
    const containers = [
        document.getElementById('singleResult'),
        document.getElementById('batchResult'),
        document.getElementById('consistResult'),
        document.getElementById('multiModelResult')
    ];
    
    if (!evalConfigStatus.qwen_configured && !evalConfigStatus.deepseek_configured) {
        // 两个都没配置，不显示警告（在评估配置状态中已显示）
        return;
    }
    
    let mode = null;
    if (evalConfigStatus.qwen_configured && !evalConfigStatus.deepseek_configured) {
        mode = 'qwen_only';
    } else if (!evalConfigStatus.qwen_configured && evalConfigStatus.deepseek_configured) {
        mode = 'deepseek_only';
    }
    
    // 只在有降级情况时显示
    if (mode) {
        console.log('评估模式降级:', mode);
    }
}

// 更新checkEvalConfig以包含降级检查
const originalCheckEvalConfig = checkEvalConfig;
checkEvalConfig = async function() {
    await originalCheckEvalConfig();
    checkAndShowDegradedMode();
};


// ========== 统一AI评估功能 ==========

// 评估模型选择器
function showEvalModelSelector(testType, testResults, callback) {
    // 创建选择弹窗
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'evalModelSelectorModal';
    modal.style.display = 'flex';
    
    let options = '';
    if (evalConfigStatus.qwen_configured) {
        options += '<label style="display:flex;align-items:center;gap:8px;padding:12px;background:#f5f5f7;border-radius:8px;cursor:pointer;"><input type="radio" name="evalModel" value="qwen3-max"> <div><strong>Qwen3-Max 宏观分析</strong><br><span style="font-size:12px;color:#666;">整体趋势、模型对比、优化建议</span></div></label>';
    }
    if (evalConfigStatus.deepseek_configured) {
        options += '<label style="display:flex;align-items:center;gap:8px;padding:12px;background:#f5f5f7;border-radius:8px;cursor:pointer;"><input type="radio" name="evalModel" value="deepseek"> <div><strong>DeepSeek 微观评估</strong><br><span style="font-size:12px;color:#666;">逐题语义评估、错误分类、问题定位</span></div></label>';
    }
    if (evalConfigStatus.joint_available) {
        options += '<label style="display:flex;align-items:center;gap:8px;padding:12px;background:#e3f2fd;border-radius:8px;cursor:pointer;border:2px solid #2196f3;"><input type="radio" name="evalModel" value="joint" checked> <div><strong>联合评估（推荐）</strong><br><span style="font-size:12px;color:#666;">Qwen宏观分析 + DeepSeek微观评估</span></div></label>';
    }
    
    if (!options) {
        alert('请先配置评估模型API Key');
        return;
    }
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width:500px;">
            <div class="modal-header">
                <h3>选择评估模型</h3>
                <button class="modal-close" onclick="closeEvalModelSelector()">×</button>
            </div>
            <div style="padding:20px;display:flex;flex-direction:column;gap:12px;">
                ${options}
            </div>
            <div style="padding:0 20px 20px;display:flex;gap:12px;justify-content:flex-end;">
                <button class="btn btn-secondary" onclick="closeEvalModelSelector()">取消</button>
                <button class="btn" onclick="runUnifiedEval('${testType}')">开始评估</button>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 保存回调和数据
    window._evalCallback = callback;
    window._evalTestResults = testResults;
}

function closeEvalModelSelector() {
    const modal = document.getElementById('evalModelSelectorModal');
    if (modal) modal.remove();
}

async function runUnifiedEval(testType) {
    const selectedModel = document.querySelector('input[name="evalModel"]:checked')?.value;
    if (!selectedModel) {
        alert('请选择评估模型');
        return;
    }
    
    closeEvalModelSelector();
    showLoading('正在进行AI评估...');
    
    try {
        const res = await fetch('/api/ai-eval/unified', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                test_type: testType,
                eval_model: selectedModel,
                test_results: window._evalTestResults
            })
        });
        const result = await res.json();
        
        if (result.error) {
            alert('评估失败: ' + result.error);
        } else {
            renderUnifiedEvalResult(result, testType);
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function renderUnifiedEvalResult(result, testType) {
    let html = '<div class="summary-box" style="margin-top:24px;border:2px solid #1d6f8c;">';
    html += '<h4>🤖 AI评估结果</h4>';
    
    // 降级提示
    if (result.degraded) {
        html += '<div style="background:#fff3e0;padding:8px 12px;border-radius:4px;margin-bottom:12px;font-size:12px;color:#e65100;">⚠️ 已降级为单模型评估模式</div>';
    }
    
    html += '<div class="summary-content">';
    
    // 宏观分析
    if (result.macro_analysis) {
        html += '<div style="margin-bottom:16px;padding:12px;background:rgba(255,255,255,0.1);border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">📊 宏观分析（Qwen3-Max）</div>';
        if (result.macro_analysis.summary) {
            html += '<p style="margin-bottom:8px;">' + escapeHtml(result.macro_analysis.summary) + '</p>';
        }
        if (result.macro_analysis.key_findings) {
            html += '<ul style="margin:0;padding-left:20px;">';
            result.macro_analysis.key_findings.forEach(f => {
                html += '<li style="font-size:13px;">' + escapeHtml(f) + '</li>';
            });
            html += '</ul>';
        }
        if (result.macro_analysis.recommendations) {
            const rec = result.macro_analysis.recommendations;
            if (rec.model_selection) html += '<p style="font-size:12px;color:rgba(255,255,255,0.8);margin-top:8px;">选型建议: ' + escapeHtml(rec.model_selection) + '</p>';
            if (rec.prompt_optimization) html += '<p style="font-size:12px;color:rgba(255,255,255,0.8);">优化方向: ' + escapeHtml(rec.prompt_optimization) + '</p>';
        }
        if (result.macro_analysis.raw) {
            html += '<pre style="background:rgba(0,0,0,0.2);padding:8px;border-radius:4px;font-size:11px;overflow-x:auto;">' + escapeHtml(result.macro_analysis.raw) + '</pre>';
        }
        html += '</div>';
    }
    
    // 微观评估
    if (result.micro_evaluation && result.micro_evaluation.per_question_results) {
        html += '<div style="margin-bottom:16px;padding:12px;background:rgba(255,255,255,0.1);border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">🔍 微观评估（DeepSeek）</div>';
        
        const results = result.micro_evaluation.per_question_results;
        const correctCount = results.filter(r => r.semantic_correct).length;
        html += '<p style="font-size:13px;margin-bottom:8px;">语义正确率: ' + correctCount + '/' + results.length + ' (' + Math.round(correctCount / results.length * 100) + '%)</p>';
        
        html += '<div style="max-height:200px;overflow-y:auto;">';
        results.forEach(r => {
            const correct = r.semantic_correct;
            html += '<div style="padding:6px 8px;border-bottom:1px solid rgba(255,255,255,0.1);font-size:12px;">';
            html += '<span style="display:inline-block;width:50px;">题目 ' + r.question_id + '</span>';
            html += '<span class="tag ' + (correct ? 'tag-success' : 'tag-error') + '">' + (correct ? '✓' : '✗') + '</span>';
            if (r.score !== undefined) html += ' <span style="opacity:0.7;">' + (r.score * 100).toFixed(0) + '%</span>';
            if (r.error_type && r.error_type !== '无') html += ' <span style="opacity:0.7;">(' + r.error_type + ')</span>';
            html += '</div>';
        });
        html += '</div></div>';
    }
    
    // 分歧点
    if (result.discrepancies && result.discrepancies.length > 0) {
        html += '<div style="padding:12px;background:#ff9800;border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;color:#fff;">⚠️ 评估分歧</div>';
        result.discrepancies.forEach(d => {
            html += '<div style="font-size:12px;color:#fff;margin-bottom:4px;">';
            html += '<strong>' + (d.type || '分歧') + ':</strong> ';
            html += 'Qwen: ' + escapeHtml(d.qwen_opinion || '-') + ' | ';
            html += 'DeepSeek: ' + escapeHtml(d.deepseek_opinion || '-');
            html += '</div>';
        });
        html += '</div>';
    }
    
    html += '</div></div>';
    
    // 根据测试类型添加到对应的结果区域
    const containerMap = {
        'single': 'singleResult',
        'batch': 'batchResult',
        'consistency': 'consistResult',
        'multi_model': 'multiModelResult'
    };
    const container = document.getElementById(containerMap[testType]);
    if (container) {
        container.innerHTML += html;
    }
}

// 为各测试类型添加AI评估按钮
function addAIEvalButton(testType, testResults) {
    if (!evalConfigStatus.qwen_configured && !evalConfigStatus.deepseek_configured) {
        return ''; // 没有配置任何评估模型
    }
    
    return `<button class="btn" style="background:#1d6f8c;" onclick="showEvalModelSelector('${testType}', window.last${testType.charAt(0).toUpperCase() + testType.slice(1)}Results)">🤖 AI评估</button>`;
}

// 量化数据展示
async function showQuantifiedData(testResults) {
    showLoading('正在计算量化数据...');
    
    try {
        const res = await fetch('/api/ai-eval/quantify', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_results: testResults })
        });
        const data = await res.json();
        
        renderQuantifiedCards(data);
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function renderQuantifiedCards(data) {
    let html = '<div class="section" style="margin-top:24px;"><div class="section-title">📊 量化数据</div>';
    html += '<div class="stats-grid">';
    
    const dimensions = data.dimensions || {};
    const labels = {
        'accuracy': '准确率',
        'consistency': '一致性',
        'avg_time': '平均耗时',
        'token_cost': 'Token消耗'
    };
    const units = {
        'accuracy': '%',
        'consistency': '%',
        'avg_time': 's',
        'token_cost': ''
    };
    
    Object.entries(dimensions).forEach(([key, metric]) => {
        const pass = metric.pass;
        html += '<div class="stat-card' + (pass ? ' highlight' : '') + '">';
        html += '<div class="stat-value">' + metric.value + (units[key] || '') + '</div>';
        html += '<div class="stat-label">' + (labels[key] || key) + '</div>';
        html += '<div style="font-size:10px;margin-top:4px;color:' + (pass ? '#4caf50' : '#f44336') + ';">';
        html += (pass ? '✓ 达标' : '✗ 未达标') + ' (阈值: ' + metric.threshold + ')';
        html += '</div></div>';
    });
    
    html += '</div>';
    
    // 总体通过状态
    const comparison = data.threshold_comparison || {};
    html += '<div style="margin-top:16px;padding:12px;background:' + (comparison.overall_pass ? '#e8f5e9' : '#ffebee') + ';border-radius:8px;text-align:center;">';
    html += '<span style="font-size:14px;font-weight:600;color:' + (comparison.overall_pass ? '#2e7d32' : '#c62828') + ';">';
    html += (comparison.overall_pass ? '✓ 全部指标达标' : '✗ 部分指标未达标') + ' (' + comparison.pass_count + '/' + comparison.total_count + ')';
    html += '</span></div>';
    
    html += '</div>';
    
    return html;
}

// 问题定位功能
async function runProblemLocate(errorQuestions) {
    if (!evalConfigStatus.deepseek_configured) {
        return alert('请先配置DeepSeek API Key');
    }
    
    if (!errorQuestions || errorQuestions.length === 0) {
        return alert('无错误题目需要定位');
    }
    
    showLoading('正在进行问题定位分析...');
    
    try {
        const res = await fetch('/api/ai-eval/problem-locate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ error_questions: errorQuestions })
        });
        const result = await res.json();
        
        if (result.error) {
            alert('问题定位失败: ' + result.error);
        } else {
            renderProblemLocateResult(result);
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function renderProblemLocateResult(result) {
    let html = '<div class="section" style="margin-top:24px;border:2px solid #ff5722;border-radius:12px;padding:20px;">';
    html += '<div class="section-title" style="color:#ff5722;">🔍 问题定位分析</div>';
    
    // 错误类型分布
    if (result.error_types) {
        html += '<div style="margin-bottom:16px;"><strong>错误类型分布:</strong></div>';
        html += '<div style="display:flex;flex-wrap:wrap;gap:8px;margin-bottom:16px;">';
        Object.entries(result.error_types).forEach(([type, count]) => {
            if (count > 0) {
                html += '<span style="background:#ffebee;color:#c62828;padding:4px 12px;border-radius:20px;font-size:13px;">' + escapeHtml(type) + ': ' + count + '</span>';
            }
        });
        html += '</div>';
    }
    
    // 问题题目列表
    if (result.problem_questions && result.problem_questions.length > 0) {
        html += '<div style="margin-bottom:16px;"><strong>问题题目详情:</strong></div>';
        html += '<table class="data-table"><thead><tr><th>题号</th><th>错误类型</th><th>错误原因</th><th>修复建议</th></tr></thead><tbody>';
        result.problem_questions.forEach(q => {
            html += '<tr>';
            html += '<td>' + escapeHtml(q.index || '-') + '</td>';
            html += '<td><span class="tag tag-error">' + escapeHtml(q.error_type || '-') + '</span></td>';
            html += '<td style="max-width:200px;">' + escapeHtml(q.error_reason || '-') + '</td>';
            html += '<td style="max-width:200px;">' + escapeHtml(q.fix_suggestion || '-') + '</td>';
            html += '</tr>';
        });
        html += '</tbody></table>';
    }
    
    // 错误模式分析
    if (result.pattern_analysis) {
        html += '<div style="margin-top:16px;padding:12px;background:#fff3e0;border-radius:8px;">';
        html += '<strong>错误模式分析:</strong><br>';
        html += '<p style="margin:8px 0 0;font-size:13px;">' + escapeHtml(result.pattern_analysis) + '</p>';
        html += '</div>';
    }
    
    // 根本原因
    if (result.root_causes && result.root_causes.length > 0) {
        html += '<div style="margin-top:12px;padding:12px;background:#ffebee;border-radius:8px;">';
        html += '<strong>根本原因:</strong>';
        html += '<ul style="margin:8px 0 0;padding-left:20px;">';
        result.root_causes.forEach(cause => {
            html += '<li style="font-size:13px;">' + escapeHtml(cause) + '</li>';
        });
        html += '</ul></div>';
    }
    
    html += '</div>';
    
    document.getElementById('batchResult').innerHTML += html;
}


// ========== 可视化图表增强 ==========

// 图表数据生成函数
function generateMultiModelBarData(modelStats) {
    return {
        labels: Object.keys(modelStats),
        datasets: [
            {
                label: '准确率',
                data: Object.values(modelStats).map(s => s.avgAcc || 0),
                backgroundColor: '#1d6f8c'
            },
            {
                label: '一致性',
                data: Object.values(modelStats).map(s => s.consistency || 0),
                backgroundColor: '#2196f3'
            }
        ]
    };
}

function generateErrorTypePieData(errorTypes) {
    const colors = ['#ff6384', '#36a2eb', '#ffce56', '#4bc0c0', '#9966ff'];
    return {
        labels: Object.keys(errorTypes),
        datasets: [{
            data: Object.values(errorTypes),
            backgroundColor: colors.slice(0, Object.keys(errorTypes).length)
        }]
    };
}

function generateCapabilityRadarData(models, metrics) {
    const colors = ['#1d6f8c', '#2196f3', '#ff9800', '#4caf50'];
    return {
        labels: ['准确性', '一致性', '速度', '成本效益', '稳定性'],
        datasets: models.map((model, i) => ({
            label: model.name,
            data: [
                model.accuracy || 0,
                model.consistency || 0,
                Math.max(0, 100 - (model.avgTime || 0) * 10),
                Math.max(0, 100 - (model.tokenCost || 0) / 10),
                model.stability || 80
            ],
            borderColor: colors[i % colors.length],
            backgroundColor: colors[i % colors.length] + '20'
        }))
    };
}

// 获取图表数据
async function fetchChartData(testResults, chartTypes = ['all']) {
    try {
        const res = await fetch('/api/ai-eval/charts', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_results: testResults, chart_types: chartTypes })
        });
        return await res.json();
    } catch (e) {
        console.error('获取图表数据失败:', e);
        return null;
    }
}

// 渲染增强图表
async function renderEnhancedCharts(testResults, containerId) {
    const container = document.getElementById(containerId);
    if (!container) return;
    
    const chartData = await fetchChartData(testResults);
    if (!chartData || !chartData.charts) return;
    
    let html = '<div class="section" style="margin-top:24px;"><div class="section-title">📊 可视化图表</div>';
    html += '<div class="chart-grid">';
    
    const charts = chartData.charts;
    
    // 多模型对比柱状图
    if (charts.multi_model_bar) {
        html += '<div class="chart-box"><div class="chart-title">多模型对比</div><canvas id="enhancedBarChart"></canvas></div>';
    }
    
    // 错误类型饼图
    if (charts.error_type_pie) {
        html += '<div class="chart-box"><div class="chart-title">错误类型分布</div><canvas id="enhancedPieChart"></canvas></div>';
    }
    
    // 能力雷达图
    if (charts.capability_radar) {
        html += '<div class="chart-box"><div class="chart-title">模型能力雷达图</div><canvas id="enhancedRadarChart"></canvas></div>';
    }
    
    // 耗时折线图
    if (charts.batch_time_line) {
        html += '<div class="chart-box"><div class="chart-title">耗时趋势</div><canvas id="enhancedLineChart"></canvas></div>';
    }
    
    html += '</div>';
    
    // 图表操作按钮
    html += '<div style="margin-top:16px;display:flex;gap:8px;flex-wrap:wrap;">';
    html += '<button class="btn btn-secondary btn-small" onclick="exportAllCharts()">导出所有图表</button>';
    html += '</div>';
    
    html += '</div>';
    
    container.innerHTML += html;
    
    // 渲染图表
    setTimeout(() => {
        if (charts.multi_model_bar) {
            new Chart(document.getElementById('enhancedBarChart'), {
                type: 'bar',
                data: charts.multi_model_bar,
                options: { responsive: true, plugins: { legend: { position: 'top' } }, scales: { y: { beginAtZero: true, max: 100 } } }
            });
        }
        
        if (charts.error_type_pie) {
            new Chart(document.getElementById('enhancedPieChart'), {
                type: 'doughnut',
                data: charts.error_type_pie,
                options: { responsive: true, plugins: { legend: { position: 'bottom' } } }
            });
        }
        
        if (charts.capability_radar) {
            new Chart(document.getElementById('enhancedRadarChart'), {
                type: 'radar',
                data: charts.capability_radar,
                options: { responsive: true, scales: { r: { beginAtZero: true, max: 100 } } }
            });
        }
        
        if (charts.batch_time_line) {
            new Chart(document.getElementById('enhancedLineChart'), {
                type: 'line',
                data: charts.batch_time_line,
                options: { responsive: true, plugins: { legend: { display: false } } }
            });
        }
    }, 100);
}

// 导出图表为PNG
function exportChartAsPNG(chartId, filename) {
    const canvas = document.getElementById(chartId);
    if (!canvas) return;
    
    const link = document.createElement('a');
    link.download = filename || chartId + '.png';
    link.href = canvas.toDataURL('image/png');
    link.click();
}

// 导出所有图表
function exportAllCharts() {
    const chartIds = ['enhancedBarChart', 'enhancedPieChart', 'enhancedRadarChart', 'enhancedLineChart'];
    chartIds.forEach(id => {
        const canvas = document.getElementById(id);
        if (canvas) {
            exportChartAsPNG(id, id + '_' + new Date().toISOString().slice(0, 10) + '.png');
        }
    });
}

// ========== DeepSeek评估报告 ==========

async function generateDeepSeekReport(testResults) {
    if (!evalConfigStatus.deepseek_configured) {
        return alert('请先配置DeepSeek API Key');
    }
    
    showLoading('正在生成DeepSeek评估报告...');
    
    try {
        const res = await fetch('/api/deepseek/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ test_results: testResults })
        });
        const report = await res.json();
        
        if (report.error) {
            alert('生成报告失败: ' + report.error);
        } else {
            showDeepSeekReport(report);
        }
    } catch (e) {
        alert('错误: ' + e.message);
    }
    hideLoading();
}

function showDeepSeekReport(report) {
    let html = '<div class="section" style="margin-top:24px;border:2px solid #333;border-radius:12px;padding:20px;">';
    html += '<div class="section-title" style="color:#333;">📋 DeepSeek评估报告</div>';
    
    // 报告元信息
    html += '<div style="background:#f5f5f7;padding:12px;border-radius:8px;margin-bottom:16px;font-size:12px;color:#666;">';
    html += '报告ID: ' + report.report_id + ' | 生成时间: ' + new Date(report.generated_at).toLocaleString();
    html += '</div>';
    
    // 评估背景
    html += '<div style="margin-bottom:16px;">';
    html += '<strong>评估背景</strong>';
    html += '<p style="font-size:13px;color:#666;margin:8px 0;">目的: ' + (report.evaluation_background?.purpose || '-') + '</p>';
    html += '</div>';
    
    // 核心数据
    html += '<div style="margin-bottom:16px;">';
    html += '<strong>核心数据</strong>';
    html += '<div class="stats-grid" style="margin-top:8px;">';
    const core = report.core_data || {};
    html += '<div class="stat-card"><div class="stat-value">' + (core.accuracy || 0) + '%</div><div class="stat-label">准确率</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + (core.consistency || 0) + '%</div><div class="stat-label">一致性</div></div>';
    html += '<div class="stat-card"><div class="stat-value">' + (core.avg_time || 0) + 's</div><div class="stat-label">平均耗时</div></div>';
    html += '</div></div>';
    
    // 问题分析
    if (report.problem_analysis && Object.keys(report.problem_analysis).length > 0) {
        html += '<div style="margin-bottom:16px;">';
        html += '<strong>问题分析</strong>';
        html += '<pre style="background:#f5f5f7;padding:12px;border-radius:8px;font-size:11px;overflow-x:auto;margin-top:8px;">' + escapeHtml(JSON.stringify(report.problem_analysis, null, 2)) + '</pre>';
        html += '</div>';
    }
    
    // 优化建议
    if (report.optimization_suggestions && Object.keys(report.optimization_suggestions).length > 0) {
        html += '<div style="margin-bottom:16px;">';
        html += '<strong>优化建议</strong>';
        const suggestions = report.optimization_suggestions;
        if (suggestions.prompt_optimization) {
            html += '<div style="margin-top:8px;"><span style="font-size:12px;color:#666;">提示词优化:</span>';
            html += '<ul style="margin:4px 0 0;padding-left:20px;">';
            (Array.isArray(suggestions.prompt_optimization) ? suggestions.prompt_optimization : [suggestions.prompt_optimization]).forEach(s => {
                html += '<li style="font-size:13px;">' + escapeHtml(s) + '</li>';
            });
            html += '</ul></div>';
        }
        if (suggestions.model_selection) {
            html += '<p style="font-size:13px;margin-top:8px;"><span style="color:#666;">模型选择:</span> ' + escapeHtml(suggestions.model_selection) + '</p>';
        }
        html += '</div>';
    }
    
    // 导出按钮
    html += '<div style="display:flex;gap:8px;margin-top:16px;">';
    html += '<button class="btn btn-secondary btn-small" onclick="exportDeepSeekReport(\'html\')">导出HTML</button>';
    html += '<button class="btn btn-secondary btn-small" onclick="exportDeepSeekReport(\'markdown\')">导出Markdown</button>';
    html += '</div>';
    
    html += '</div>';
    
    // 保存报告数据
    window.lastDeepSeekReport = report;
    
    // 添加到结果区域
    const container = document.getElementById('batchResult') || document.getElementById('singleResult');
    if (container) {
        container.innerHTML += html;
    }
}

async function exportDeepSeekReport(format) {
    if (!window.lastDeepSeekReport) return alert('请先生成报告');
    
    try {
        const res = await fetch('/api/export/report', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ report: window.lastDeepSeekReport, format: format })
        });
        const blob = await res.blob();
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = 'report_' + window.lastDeepSeekReport.report_id + '.' + (format === 'markdown' ? 'md' : 'html');
        a.click();
        URL.revokeObjectURL(url);
    } catch (e) {
        alert('导出失败: ' + e.message);
    }
}

// ========== 自动题型识别 ==========

async function detectQuestionType(content, useAI = false) {
    try {
        const res = await fetch('/api/question-type/detect', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content: content, use_ai: useAI })
        });
        return await res.json();
    } catch (e) {
        console.error('题型识别失败:', e);
        return null;
    }
}

function renderTypeDetectionResult(result, containerId) {
    if (!result) return;
    
    const typeLabels = {
        'objective': '客观题',
        'subjective': '主观题',
        'calculation': '计算题',
        'essay': '作文题',
        'unknown': '未知'
    };
    
    const subTypeLabels = {
        'choice': '选择题',
        'fill_blank': '填空题',
        'short_answer': '简答题',
        'discussion': '论述题',
        'math': '数学计算',
        'composition': '作文'
    };
    
    let html = '<div style="background:#e3f2fd;padding:12px;border-radius:8px;margin-top:12px;">';
    html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">🔍 题型识别结果</div>';
    html += '<div style="display:flex;gap:16px;flex-wrap:wrap;font-size:13px;">';
    html += '<span>类型: <strong>' + (typeLabels[result.detected_type] || result.detected_type) + '</strong></span>';
    if (result.sub_type) {
        html += '<span>子类型: <strong>' + (subTypeLabels[result.sub_type] || result.sub_type) + '</strong></span>';
    }
    html += '<span>置信度: <strong>' + (result.confidence * 100).toFixed(0) + '%</strong></span>';
    html += '<span>识别方式: <strong>' + (result.detection_method === 'ai' ? 'AI识别' : '规则识别') + '</strong></span>';
    html += '</div>';
    html += '<div style="margin-top:8px;"><button class="btn-small" onclick="allowManualCorrection()">手动修正</button></div>';
    html += '</div>';
    
    const container = document.getElementById(containerId);
    if (container) {
        container.innerHTML += html;
    }
}

function allowManualCorrection() {
    const types = ['objective', 'subjective', 'calculation', 'essay'];
    const selected = prompt('请输入正确的题型 (objective/subjective/calculation/essay):');
    if (selected && types.includes(selected)) {
        alert('题型已修正为: ' + selected);
        // 这里可以保存修正结果
    }
}


// ========== 自定义评估配置面板 ==========

let currentEvalConfig = null;

async function loadEvalConfig() {
    try {
        const res = await fetch('/api/eval-config');
        currentEvalConfig = await res.json();
        return currentEvalConfig;
    } catch (e) {
        console.error('加载评估配置失败:', e);
        return null;
    }
}

async function saveEvalConfig(config) {
    try {
        const res = await fetch('/api/eval-config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        if (res.ok) {
            currentEvalConfig = config;
            return true;
        }
        return false;
    } catch (e) {
        console.error('保存评估配置失败:', e);
        return false;
    }
}

function showEvalConfigPanel() {
    // 创建配置面板弹窗
    const modal = document.createElement('div');
    modal.className = 'modal';
    modal.id = 'evalConfigModal';
    modal.style.display = 'flex';
    
    const config = currentEvalConfig || {
        dimensions: {
            accuracy_class: { enabled: true, metrics: ['accuracy', 'precision', 'recall', 'f1', 'consistency'] },
            efficiency_class: { enabled: true, metrics: ['single_time', 'batch_avg_time'] },
            resource_class: { enabled: true, metrics: ['token_usage', 'token_cost'] }
        },
        subject_rules: {
            math: { objective_ratio: 0.3, calculation_ratio: 0.5, subjective_ratio: 0.2 },
            chinese: { objective_ratio: 0.2, subjective_ratio: 0.5, essay_ratio: 0.3 }
        },
        eval_scope: 'single'
    };
    
    modal.innerHTML = `
        <div class="modal-content" style="max-width:700px;max-height:80vh;overflow-y:auto;">
            <div class="modal-header">
                <h3>⚙️ 评估配置</h3>
                <button class="modal-close" onclick="closeEvalConfigPanel()">×</button>
            </div>
            <div style="padding:20px;">
                <!-- 评估维度选择 -->
                <div style="margin-bottom:24px;">
                    <div style="font-size:14px;font-weight:600;margin-bottom:12px;">评估维度</div>
                    <div style="display:flex;flex-direction:column;gap:8px;">
                        <label style="display:flex;align-items:center;gap:8px;padding:12px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="checkbox" id="dim_accuracy" ${config.dimensions.accuracy_class?.enabled ? 'checked' : ''}>
                            <div>
                                <strong>准确性指标</strong>
                                <div style="font-size:12px;color:#666;">准确率、精确率、召回率、F1值、一致性</div>
                            </div>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;padding:12px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="checkbox" id="dim_efficiency" ${config.dimensions.efficiency_class?.enabled ? 'checked' : ''}>
                            <div>
                                <strong>效率指标</strong>
                                <div style="font-size:12px;color:#666;">单次耗时、批量平均耗时</div>
                            </div>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;padding:12px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="checkbox" id="dim_resource" ${config.dimensions.resource_class?.enabled ? 'checked' : ''}>
                            <div>
                                <strong>资源指标</strong>
                                <div style="font-size:12px;color:#666;">Token使用量、Token成本</div>
                            </div>
                        </label>
                    </div>
                </div>
                
                <!-- 学科评分规则 -->
                <div style="margin-bottom:24px;">
                    <div style="font-size:14px;font-weight:600;margin-bottom:12px;">学科评分规则</div>
                    
                    <!-- 数学 -->
                    <div style="background:#f5f5f7;padding:16px;border-radius:8px;margin-bottom:12px;">
                        <div style="font-size:13px;font-weight:600;margin-bottom:8px;">📐 数学</div>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                            <div>
                                <label style="font-size:12px;color:#666;">客观题权重</label>
                                <input type="number" id="math_objective" value="${(config.subject_rules.math?.objective_ratio || 0.3) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                            <div>
                                <label style="font-size:12px;color:#666;">计算题权重</label>
                                <input type="number" id="math_calculation" value="${(config.subject_rules.math?.calculation_ratio || 0.5) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                            <div>
                                <label style="font-size:12px;color:#666;">主观题权重</label>
                                <input type="number" id="math_subjective" value="${(config.subject_rules.math?.subjective_ratio || 0.2) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                        </div>
                        <div id="math_weight_sum" style="font-size:11px;color:#666;margin-top:8px;">权重总和: 100%</div>
                    </div>
                    
                    <!-- 语文 -->
                    <div style="background:#f5f5f7;padding:16px;border-radius:8px;">
                        <div style="font-size:13px;font-weight:600;margin-bottom:8px;">📖 语文</div>
                        <div style="display:grid;grid-template-columns:repeat(3,1fr);gap:12px;">
                            <div>
                                <label style="font-size:12px;color:#666;">客观题权重</label>
                                <input type="number" id="chinese_objective" value="${(config.subject_rules.chinese?.objective_ratio || 0.2) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                            <div>
                                <label style="font-size:12px;color:#666;">主观题权重</label>
                                <input type="number" id="chinese_subjective" value="${(config.subject_rules.chinese?.subjective_ratio || 0.5) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                            <div>
                                <label style="font-size:12px;color:#666;">作文权重</label>
                                <input type="number" id="chinese_essay" value="${(config.subject_rules.chinese?.essay_ratio || 0.3) * 100}" min="0" max="100" step="5" style="width:100%;padding:8px;border:1px solid #ddd;border-radius:4px;">
                            </div>
                        </div>
                        <div id="chinese_weight_sum" style="font-size:11px;color:#666;margin-top:8px;">权重总和: 100%</div>
                    </div>
                </div>
                
                <!-- 评估范围 -->
                <div style="margin-bottom:24px;">
                    <div style="font-size:14px;font-weight:600;margin-bottom:12px;">评估范围</div>
                    <div style="display:flex;gap:12px;flex-wrap:wrap;">
                        <label style="display:flex;align-items:center;gap:8px;padding:10px 16px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="radio" name="eval_scope" value="single" ${config.eval_scope === 'single' ? 'checked' : ''}>
                            <span>单模型评估</span>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;padding:10px 16px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="radio" name="eval_scope" value="multi_model" ${config.eval_scope === 'multi_model' ? 'checked' : ''}>
                            <span>多模型对比</span>
                        </label>
                        <label style="display:flex;align-items:center;gap:8px;padding:10px 16px;background:#f5f5f7;border-radius:8px;cursor:pointer;">
                            <input type="radio" name="eval_scope" value="version_compare" ${config.eval_scope === 'version_compare' ? 'checked' : ''}>
                            <span>版本对比</span>
                        </label>
                    </div>
                </div>
                
                <!-- 操作按钮 -->
                <div style="display:flex;gap:12px;justify-content:flex-end;padding-top:16px;border-top:1px solid #e5e5e5;">
                    <button class="btn btn-secondary" onclick="resetEvalConfig()">恢复默认</button>
                    <button class="btn" onclick="applyEvalConfig()">保存配置</button>
                </div>
            </div>
        </div>
    `;
    
    document.body.appendChild(modal);
    
    // 添加权重验证
    setupWeightValidation();
}

function setupWeightValidation() {
    const mathInputs = ['math_objective', 'math_calculation', 'math_subjective'];
    const chineseInputs = ['chinese_objective', 'chinese_subjective', 'chinese_essay'];
    
    mathInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => validateWeights('math', mathInputs));
        }
    });
    
    chineseInputs.forEach(id => {
        const el = document.getElementById(id);
        if (el) {
            el.addEventListener('input', () => validateWeights('chinese', chineseInputs));
        }
    });
}

function validateWeights(subject, inputIds) {
    const sum = inputIds.reduce((total, id) => {
        const el = document.getElementById(id);
        return total + (parseFloat(el?.value) || 0);
    }, 0);
    
    const sumEl = document.getElementById(subject + '_weight_sum');
    if (sumEl) {
        const isValid = Math.abs(sum - 100) < 0.01;
        sumEl.textContent = `权重总和: ${sum}%`;
        sumEl.style.color = isValid ? '#4caf50' : '#f44336';
    }
}

function closeEvalConfigPanel() {
    const modal = document.getElementById('evalConfigModal');
    if (modal) modal.remove();
}

async function applyEvalConfig() {
    // 收集配置
    const config = {
        dimensions: {
            accuracy_class: { 
                enabled: document.getElementById('dim_accuracy')?.checked || false,
                metrics: ['accuracy', 'precision', 'recall', 'f1', 'consistency']
            },
            efficiency_class: { 
                enabled: document.getElementById('dim_efficiency')?.checked || false,
                metrics: ['single_time', 'batch_avg_time']
            },
            resource_class: { 
                enabled: document.getElementById('dim_resource')?.checked || false,
                metrics: ['token_usage', 'token_cost']
            }
        },
        subject_rules: {
            math: {
                objective_ratio: (parseFloat(document.getElementById('math_objective')?.value) || 30) / 100,
                calculation_ratio: (parseFloat(document.getElementById('math_calculation')?.value) || 50) / 100,
                subjective_ratio: (parseFloat(document.getElementById('math_subjective')?.value) || 20) / 100
            },
            chinese: {
                objective_ratio: (parseFloat(document.getElementById('chinese_objective')?.value) || 20) / 100,
                subjective_ratio: (parseFloat(document.getElementById('chinese_subjective')?.value) || 50) / 100,
                essay_ratio: (parseFloat(document.getElementById('chinese_essay')?.value) || 30) / 100
            }
        },
        eval_scope: document.querySelector('input[name="eval_scope"]:checked')?.value || 'single'
    };
    
    // 验证权重
    const mathSum = config.subject_rules.math.objective_ratio + config.subject_rules.math.calculation_ratio + config.subject_rules.math.subjective_ratio;
    const chineseSum = config.subject_rules.chinese.objective_ratio + config.subject_rules.chinese.subjective_ratio + config.subject_rules.chinese.essay_ratio;
    
    if (Math.abs(mathSum - 1) > 0.01) {
        alert('数学学科权重总和必须为100%');
        return;
    }
    if (Math.abs(chineseSum - 1) > 0.01) {
        alert('语文学科权重总和必须为100%');
        return;
    }
    
    // 保存配置
    const success = await saveEvalConfig(config);
    if (success) {
        alert('配置已保存');
        closeEvalConfigPanel();
    } else {
        alert('保存失败，请重试');
    }
}

function resetEvalConfig() {
    if (!confirm('确定要恢复默认配置吗？')) return;
    
    // 恢复默认值
    document.getElementById('dim_accuracy').checked = true;
    document.getElementById('dim_efficiency').checked = true;
    document.getElementById('dim_resource').checked = true;
    
    document.getElementById('math_objective').value = 30;
    document.getElementById('math_calculation').value = 50;
    document.getElementById('math_subjective').value = 20;
    
    document.getElementById('chinese_objective').value = 20;
    document.getElementById('chinese_subjective').value = 50;
    document.getElementById('chinese_essay').value = 30;
    
    document.querySelector('input[name="eval_scope"][value="single"]').checked = true;
    
    validateWeights('math', ['math_objective', 'math_calculation', 'math_subjective']);
    validateWeights('chinese', ['chinese_objective', 'chinese_subjective', 'chinese_essay']);
}

// 在页面加载时加载评估配置
document.addEventListener('DOMContentLoaded', () => {
    loadEvalConfig();
});


// ========== 高级图表功能 ==========

// 评分偏差热力图（使用表格模拟）
function renderScoreDeviationHeatmap(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !data) return;
    
    const { models, questions, matrix } = data;
    if (!models || !questions || !matrix) return;
    
    let html = '<div class="section" style="margin-top:24px;">';
    html += '<div class="section-title">🔥 评分偏差热力图</div>';
    html += '<div style="overflow-x:auto;">';
    html += '<table class="data-table heatmap-table" style="font-size:12px;">';
    
    // 表头
    html += '<thead><tr><th>模型\\题目</th>';
    questions.forEach(q => {
        html += '<th style="text-align:center;">' + escapeHtml(q) + '</th>';
    });
    html += '</tr></thead><tbody>';
    
    // 数据行
    models.forEach(model => {
        html += '<tr><td><strong>' + escapeHtml(model) + '</strong></td>';
        questions.forEach(q => {
            const value = matrix[model]?.[q];
            const color = getHeatmapColor(value);
            html += '<td style="text-align:center;background:' + color + ';color:' + (value > 50 ? '#fff' : '#000') + ';">';
            html += value !== null && value !== undefined ? value + '%' : '-';
            html += '</td>';
        });
        html += '</tr>';
    });
    
    html += '</tbody></table></div>';
    
    // 图例
    html += '<div style="display:flex;align-items:center;gap:8px;margin-top:12px;font-size:11px;">';
    html += '<span>低</span>';
    html += '<div style="width:150px;height:12px;background:linear-gradient(to right, #ffebee, #f44336, #b71c1c);border-radius:4px;"></div>';
    html += '<span>高</span>';
    html += '</div>';
    
    html += '</div>';
    
    container.innerHTML += html;
}

function getHeatmapColor(value) {
    if (value === null || value === undefined) return '#f5f5f5';
    // 从绿色(高分)到红色(低分)
    if (value >= 90) return '#4caf50';
    if (value >= 80) return '#8bc34a';
    if (value >= 70) return '#cddc39';
    if (value >= 60) return '#ffeb3b';
    if (value >= 50) return '#ff9800';
    if (value >= 40) return '#ff5722';
    return '#f44336';
}

// 模型耗时箱线图（使用简化的统计展示）
function renderModelTimeBoxplot(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !data) return;
    
    let html = '<div class="section" style="margin-top:24px;">';
    html += '<div class="section-title">📊 模型耗时分布</div>';
    html += '<div style="display:flex;flex-direction:column;gap:16px;">';
    
    Object.entries(data).forEach(([model, stats]) => {
        const { min, q1, median, q3, max, avg } = stats;
        const range = max - min || 1;
        
        html += '<div style="background:#f5f5f7;padding:16px;border-radius:8px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:12px;">' + escapeHtml(model) + '</div>';
        
        // 箱线图可视化
        html += '<div style="position:relative;height:30px;background:#e0e0e0;border-radius:4px;margin-bottom:8px;">';
        
        // 最小值到Q1的线
        const minPos = 0;
        const q1Pos = ((q1 - min) / range) * 100;
        const medianPos = ((median - min) / range) * 100;
        const q3Pos = ((q3 - min) / range) * 100;
        const maxPos = 100;
        
        // 箱体 (Q1 to Q3)
        html += '<div style="position:absolute;left:' + q1Pos + '%;width:' + (q3Pos - q1Pos) + '%;height:100%;background:#1d6f8c;border-radius:4px;"></div>';
        
        // 中位数线
        html += '<div style="position:absolute;left:' + medianPos + '%;width:2px;height:100%;background:#fff;"></div>';
        
        // 最小值标记
        html += '<div style="position:absolute;left:0;top:50%;transform:translateY(-50%);width:8px;height:2px;background:#666;"></div>';
        
        // 最大值标记
        html += '<div style="position:absolute;right:0;top:50%;transform:translateY(-50%);width:8px;height:2px;background:#666;"></div>';
        
        html += '</div>';
        
        // 统计数据
        html += '<div style="display:flex;justify-content:space-between;font-size:11px;color:#666;">';
        html += '<span>最小: ' + min.toFixed(2) + 's</span>';
        html += '<span>Q1: ' + q1.toFixed(2) + 's</span>';
        html += '<span>中位数: ' + median.toFixed(2) + 's</span>';
        html += '<span>Q3: ' + q3.toFixed(2) + 's</span>';
        html += '<span>最大: ' + max.toFixed(2) + 's</span>';
        html += '</div>';
        
        html += '</div>';
    });
    
    html += '</div></div>';
    
    container.innerHTML += html;
}

// 计算箱线图统计数据
function calculateBoxplotStats(times) {
    if (!times || times.length === 0) return null;
    
    const sorted = [...times].sort((a, b) => a - b);
    const n = sorted.length;
    
    return {
        min: sorted[0],
        q1: sorted[Math.floor(n * 0.25)],
        median: sorted[Math.floor(n * 0.5)],
        q3: sorted[Math.floor(n * 0.75)],
        max: sorted[n - 1],
        avg: times.reduce((a, b) => a + b, 0) / n
    };
}

// 模型×学科×题型热力图
function renderModelSubjectTypeHeatmap(data, containerId) {
    const container = document.getElementById(containerId);
    if (!container || !data) return;
    
    const { models, subjects, question_types, matrix } = data;
    if (!models || !subjects || !matrix) return;
    
    let html = '<div class="section" style="margin-top:24px;">';
    html += '<div class="section-title">🗺️ 模型×学科×题型支持度</div>';
    
    // 为每个模型创建一个热力图
    models.forEach(model => {
        html += '<div style="margin-bottom:24px;">';
        html += '<div style="font-size:13px;font-weight:600;margin-bottom:8px;">' + escapeHtml(model) + '</div>';
        html += '<div style="overflow-x:auto;">';
        html += '<table class="data-table" style="font-size:11px;">';
        
        // 表头
        html += '<thead><tr><th>学科\\题型</th>';
        (question_types || ['客观题', '主观题', '计算题']).forEach(type => {
            html += '<th style="text-align:center;">' + escapeHtml(type) + '</th>';
        });
        html += '</tr></thead><tbody>';
        
        // 数据行
        subjects.forEach(subject => {
            html += '<tr><td><strong>' + escapeHtml(subject) + '</strong></td>';
            (question_types || ['客观题', '主观题', '计算题']).forEach(type => {
                const value = matrix[model]?.[subject]?.[type];
                const color = getHeatmapColor(value);
                html += '<td style="text-align:center;background:' + color + ';color:' + (value > 50 ? '#fff' : '#000') + ';padding:8px;">';
                html += value !== null && value !== undefined ? value + '%' : '-';
                html += '</td>';
            });
            html += '</tr>';
        });
        
        html += '</tbody></table></div></div>';
    });
    
    html += '</div>';
    
    container.innerHTML += html;
}

// 生成热力图数据
function generateHeatmapData(evaluationData) {
    const models = [...new Set(evaluationData.map(d => d.model))];
    const subjects = [...new Set(evaluationData.map(d => d.subject))];
    const types = [...new Set(evaluationData.map(d => d.questionType))];
    
    const matrix = {};
    models.forEach(model => {
        matrix[model] = {};
        subjects.forEach(subject => {
            matrix[model][subject] = {};
            types.forEach(type => {
                const filtered = evaluationData.filter(d => 
                    d.model === model && d.subject === subject && d.questionType === type
                );
                matrix[model][subject][type] = filtered.length > 0 
                    ? Math.round(filtered.reduce((sum, d) => sum + d.accuracy, 0) / filtered.length)
                    : null;
            });
        });
    });
    
    return { models, subjects, question_types: types, matrix };
}
