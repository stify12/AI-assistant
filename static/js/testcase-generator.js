/**
 * 测试用例生成器
 * AI 自动生成基准效果
 */

// ========== LaTeX 转可读文本 ==========
const LATEX_TO_UNICODE = {
    // 希腊字母
    '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ', '\\delta': 'δ',
    '\\epsilon': 'ε', '\\theta': 'θ', '\\lambda': 'λ', '\\mu': 'μ',
    '\\pi': 'π', '\\sigma': 'σ', '\\phi': 'φ', '\\omega': 'ω',
    '\\Gamma': 'Γ', '\\Delta': 'Δ', '\\Theta': 'Θ', '\\Sigma': 'Σ', '\\Omega': 'Ω',
    // 关系符号
    '\\in': '∈', '\\notin': '∉', '\\subset': '⊂', '\\supset': '⊃',
    '\\subseteq': '⊆', '\\supseteq': '⊇', '\\cap': '∩', '\\cup': '∪',
    '\\emptyset': '∅', '\\varnothing': '∅',
    // 比较符号（长命令在前）
    '\\geqslant': '≥', '\\leqslant': '≤',
    '\\leq': '≤', '\\le': '≤', '\\geq': '≥', '\\ge': '≥',
    '\\neq': '≠', '\\ne': '≠', '\\approx': '≈', '\\equiv': '≡',
    // 运算符号
    '\\times': '×', '\\div': '÷', '\\pm': '±', '\\cdot': '·',
    // 箭头
    '\\to': '→', '\\rightarrow': '→', '\\leftarrow': '←',
    '\\Rightarrow': '⇒', '\\Leftarrow': '⇐', '\\Leftrightarrow': '⇔',
    // 其他数学符号
    '\\infty': '∞', '\\partial': '∂', '\\forall': '∀', '\\exists': '∃',
    '\\angle': '∠', '\\perp': '⊥', '\\parallel': '∥', '\\triangle': '△',
    '\\therefore': '∴', '\\because': '∵',
    '\\sqrt': '√', '\\sum': '∑', '\\int': '∫',
    // 集合
    '\\mathbb{R}': 'ℝ', '\\mathbb{N}': 'ℕ', '\\mathbb{Z}': 'ℤ',
    '\\R': 'ℝ', '\\N': 'ℕ', '\\Z': 'ℤ',
    // 括号和点号
    '\\ldots': '…', '\\cdots': '⋯', '\\dots': '…',
    '\\mid': '|', '\\vert': '|',
    // 空格
    '\\quad': ' ', '\\qquad': '  ', '\\,': '', '\\;': '', '\\:': '', '\\ ': ' '
};

// 需要移除的格式命令
const LATEX_COMMANDS_TO_REMOVE = [
    '\\mathbf', '\\mathit', '\\mathrm', '\\mathsf', '\\mathcal', '\\mathbb',
    '\\textbf', '\\textit', '\\textrm', '\\bf', '\\it', '\\rm',
    '\\boldsymbol', '\\bm', '\\left', '\\right', '\\big', '\\Big',
    '\\displaystyle', '\\textstyle'
];

/**
 * 将 LaTeX 转换为可读文本
 * 支持集合、分数、根号、上下标等常见数学公式
 */
function latexToReadable(text) {
    if (!text) return '';
    text = String(text);
    
    // 1. 移除 $...$ 数学环境标记
    text = text.replace(/\$\$([^$]+)\$\$/g, '$1');
    text = text.replace(/\$([^$]+)\$/g, '$1');
    text = text.replace(/\\\(([^)]+)\\\)/g, '$1');
    // 注意：不处理 \[...\]，因为可能是区间表示如 \[0,3\]
    
    // 1.5 处理 cases 环境
    text = text.replace(/\\begin\{cases\}/g, '');
    text = text.replace(/\\end\{cases\}/g, '');
    text = text.replace(/\\\\/g, '; ');  // LaTeX 换行符 -> 分号
    
    // 2. 优先处理转义括号 \{ \} \[ \] -> 实际括号
    text = text.replace(/\\\[/g, '[');
    text = text.replace(/\\\]/g, ']');
    text = text.replace(/\\{/g, '⟨LBRACE⟩');
    text = text.replace(/\\}/g, '⟨RBRACE⟩');
    
    // 3. 处理 \mid（集合竖线）-> |
    text = text.replace(/\\mid\b/g, ' | ');
    text = text.replace(/\\vert\b/g, '|');
    
    // 4. 处理分数 \frac{a}{b} 或 \dfrac{a}{b} -> (a)/(b)
    text = text.replace(/\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, '($1)/($2)');
    
    // 5. 处理根号 \sqrt[n]{x} -> n√(x), \sqrt{x} -> √(x)
    text = text.replace(/\\sqrt\s*\[([^\]]*)\]\s*\{([^{}]*)\}/g, '$1√($2)');
    text = text.replace(/\\sqrt\s*\{([^{}]*)\}/g, '√($1)');
    
    // 6. 处理上下标 ^{...} _{...}
    text = text.replace(/\^{([^{}]*)}/g, '^($1)');
    text = text.replace(/_{([^{}]*)}/g, '_($1)');
    
    // 7. 移除格式命令（保留内容）
    LATEX_COMMANDS_TO_REMOVE.forEach(cmd => {
        const escaped = cmd.replace(/\\/g, '\\\\');
        text = text.replace(new RegExp(escaped + '\\s*\\{([^{}]*)\\}', 'g'), '$1');
        text = text.replace(new RegExp(escaped + '(?=[A-Za-z])', 'g'), '');
    });
    
    // 8. 替换 LaTeX 符号为 Unicode（按长度降序，避免短命令误匹配）
    const sortedEntries = Object.entries(LATEX_TO_UNICODE)
        .filter(([k]) => k !== '\\{' && k !== '\\}' && k !== '\\mid' && k !== '\\vert')
        .sort((a, b) => b[0].length - a[0].length);
    for (const [latex, unicode] of sortedEntries) {
        const escaped = latex.replace(/\\/g, '\\\\').replace(/\{/g, '\\{').replace(/\}/g, '\\}');
        text = text.replace(new RegExp(escaped, 'g'), unicode);
    }
    
    // 9. 清理残留的反斜杠命令
    text = text.replace(/\\[a-zA-Z]+/g, '');
    
    // 10. 还原集合花括号
    text = text.replace(/⟨LBRACE⟩/g, '{');
    text = text.replace(/⟨RBRACE⟩/g, '}');
    
    // 11. 清理多余空格
    text = text.replace(/\s+/g, ' ').trim();
    
    return text;
}

// ========== 状态管理 ==========
const state = {
    books: [],
    currentBook: null,
    pageNum: null,
    questions: [],
    templates: {},
    combinations: {},
    selectedTemplates: [],
    generatedEffects: [],
    subjectId: 2,
    fromUrl: false,
    picPath: ''  // 电子版图片路径
};

// ========== 初始化 ==========
function init() {
    const params = new URLSearchParams(window.location.search);
    const bookId = params.get('book_id');
    const bookName = params.get('book_name');
    const subjectId = params.get('subject_id');
    
    if (bookId && bookName) {
        state.fromUrl = true;
        state.currentBook = { book_id: bookId, book_name: bookName };
        state.subjectId = parseInt(subjectId) || 2;
        document.getElementById('subjectSelect').value = state.subjectId;
        document.getElementById('bookInfo').style.display = 'block';
        document.getElementById('bookSelector').style.display = 'none';
        document.getElementById('currentBookName').textContent = bookName;
    }
    
    loadTemplates();
    if (!state.fromUrl) {
        loadBooks();
    }
}

if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
} else {
    init();
}

// ========== API 调用 ==========
async function apiCall(url, options = {}) {
    const res = await fetch(url, {
        headers: { 'Content-Type': 'application/json' },
        ...options
    });
    const result = await res.json();
    if (!result.success) throw new Error(result.error || '请求失败');
    return result.data;
}


// ========== 加载模板配置 ==========
async function loadTemplates() {
    try {
        const data = await apiCall('/api/testcase/templates');
        state.templates = data.templates || {};
        state.combinations = data.combinations || {};
        renderTemplateList();
        selectCombination('quick_test');
    } catch (e) {
        console.error('加载模板失败:', e);
    }
}

// ========== 加载书本列表 ==========
async function loadBooks() {
    const subjectId = document.getElementById('subjectSelect').value;
    state.subjectId = parseInt(subjectId);
    
    try {
        const data = await apiCall(`/api/batch/books?subject_id=${subjectId}`);
        // 后端返回按学科分组的对象 { "2": [...], "3": [...] }
        // 提取当前学科的书本列表
        state.books = data[subjectId] || [];
        renderBookSelect();
    } catch (e) {
        console.error('加载书本失败:', e);
        state.books = [];
        renderBookSelect();
    }
}

function renderBookSelect() {
    const select = document.getElementById('bookSelect');
    if (!select) return;
    select.innerHTML = '<option value="">请选择书本</option>';
    state.books.forEach(book => {
        const opt = document.createElement('option');
        opt.value = book.book_id;
        opt.textContent = book.book_name;
        select.appendChild(opt);
    });
}

function onBookChange() {
    const bookId = document.getElementById('bookSelect').value;
    state.currentBook = bookId ? state.books.find(b => b.book_id === bookId) : null;
    state.questions = [];
    document.getElementById('questionsInfo').style.display = 'none';
    updateGenerateButton();
}

function changeBook() {
    state.fromUrl = false;
    state.currentBook = null;
    document.getElementById('bookInfo').style.display = 'none';
    document.getElementById('bookSelector').style.display = 'block';
    loadBooks();
}

// ========== 加载题目 ==========
async function loadQuestions() {
    const pageNum = parseInt(document.getElementById('pageInput').value);
    
    if (!state.currentBook && !state.fromUrl) {
        const bookId = document.getElementById('bookSelect').value;
        if (!bookId) { alert('请先选择书本'); return; }
        state.currentBook = state.books.find(b => b.book_id === bookId);
    }
    
    if (!state.currentBook) { alert('请先选择书本'); return; }
    if (!pageNum || pageNum < 1) { alert('请输入有效页码'); return; }
    
    showLoading('加载题目中...');
    
    try {
        const data = await apiCall(`/api/testcase/questions?book_id=${state.currentBook.book_id}&page_num=${pageNum}`);
        state.questions = data.questions || [];
        state.pageNum = pageNum;
        state.picPath = data.picPath || '';  // 电子版图片
        if (data.book_name) state.currentBook.book_name = data.book_name;
        
        document.getElementById('questionCount').textContent = state.questions.length + ' 道';
        document.getElementById('questionStatus').textContent = '已加载';
        document.getElementById('questionsInfo').style.display = 'block';
        
        // 渲染题目详情
        renderQuestionDetail();
        updateGenerateButton();
    } catch (e) {
        alert('加载题目失败: ' + e.message);
        state.questions = [];
        document.getElementById('questionsInfo').style.display = 'none';
        document.getElementById('questionDetailSection').style.display = 'none';
    } finally {
        hideLoading();
    }
}

// ========== 渲染题目详情 ==========
function renderQuestionDetail() {
    const section = document.getElementById('questionDetailSection');
    if (!section) return;
    
    if (state.questions.length === 0) {
        section.style.display = 'none';
        return;
    }
    
    section.style.display = 'block';
    
    // 渲染电子版图片（单张）
    const imageContainer = document.getElementById('pageImages');
    if (imageContainer && state.picPath) {
        imageContainer.innerHTML = `
            <div class="page-image-item">
                <img src="${escapeHtml(state.picPath)}" alt="电子版图片" onclick="showImageModal('${escapeHtml(state.picPath)}')" />
            </div>
        `;
    } else if (imageContainer) {
        imageContainer.innerHTML = '<div class="empty-hint">暂无电子版图片</div>';
    }
    
    // 渲染题目列表
    const listContainer = document.getElementById('questionList');
    if (listContainer) {
        listContainer.innerHTML = state.questions.map((q, idx) => {
            const typeLabel = getQuestionTypeLabel(q.bvalue);
            return `
                <div class="question-item">
                    <div class="question-header">
                        <span class="question-index">第 ${escapeHtml(q.index || (idx + 1))} 题</span>
                        <span class="question-type">${typeLabel}</span>
                    </div>
                    <div class="question-content">${escapeHtml(q.content || '暂无题目内容')}</div>
                    <div class="question-answer">
                        <span class="answer-label">标准答案:</span>
                        <span class="answer-value">${escapeHtml(q.answer || '-')}</span>
                    </div>
                </div>
            `;
        }).join('');
    }
}

function getQuestionTypeLabel(bvalue) {
    const types = { '1': '单选', '2': '多选', '3': '判断', '4': '填空', '5': '主观' };
    return types[bvalue] || '其他';
}

// ========== 图片弹窗 ==========
function showImageModal(src) {
    const modal = document.getElementById('imageModal');
    const img = document.getElementById('modalImage');
    if (modal && img) {
        img.src = src;
        modal.classList.add('show');
    }
}

function hideImageModal(event) {
    if (event && event.target !== event.currentTarget) return;
    const modal = document.getElementById('imageModal');
    if (modal) modal.classList.remove('show');
}


// ========== 渲染模板列表 ==========
function renderTemplateList() {
    const container = document.getElementById('templateList');
    container.innerHTML = '';
    
    Object.entries(state.templates).forEach(([id, tpl]) => {
        const div = document.createElement('div');
        div.className = 'template-item' + (state.selectedTemplates.includes(id) ? ' selected' : '');
        div.dataset.id = id;
        div.onclick = () => toggleTemplate(id);
        
        const expectText = tpl.correct === 'yes' ? '预期正确' : (tpl.correct === 'no' ? '预期错误' : '部分正确');
        const expectClass = tpl.correct === 'yes' ? 'expect-correct' : (tpl.correct === 'no' ? 'expect-wrong' : 'expect-partial');
        
        div.innerHTML = `
            <input type="checkbox" ${state.selectedTemplates.includes(id) ? 'checked' : ''} onclick="event.stopPropagation()">
            <div class="template-content">
                <div class="template-header">
                    <span class="template-name">${escapeHtml(tpl.name)}</span>
                    <span class="template-expect ${expectClass}">${expectText}</span>
                </div>
                <div class="template-hint">${escapeHtml(tpl.prompt_hint || '')}</div>
            </div>
        `;
        container.appendChild(div);
    });
    updateSelectedCount();
}

function toggleTemplate(id) {
    const idx = state.selectedTemplates.indexOf(id);
    if (idx >= 0) {
        state.selectedTemplates.splice(idx, 1);
    } else {
        state.selectedTemplates.push(id);
    }
    
    const item = document.querySelector(`.template-item[data-id="${id}"]`);
    if (item) {
        item.classList.toggle('selected', state.selectedTemplates.includes(id));
        const checkbox = item.querySelector('input[type="checkbox"]');
        if (checkbox) checkbox.checked = state.selectedTemplates.includes(id);
    }
    
    document.querySelectorAll('.combo-item').forEach(el => el.classList.remove('active'));
    updateSelectedCount();
    updateGenerateButton();
}

function selectCombination(comboId) {
    const combo = state.combinations[comboId];
    if (!combo) return;
    
    state.selectedTemplates = [...(combo.templates || [])];
    document.querySelectorAll('.combo-item').forEach(el => {
        el.classList.toggle('active', el.dataset.combo === comboId);
    });
    renderTemplateList();
    updateGenerateButton();
}

function updateSelectedCount() {
    document.getElementById('selectedCount').textContent = state.selectedTemplates.length;
}

function updateGenerateButton() {
    document.getElementById('generateBtn').disabled = state.questions.length === 0 || state.selectedTemplates.length === 0;
}


// ========== 生成基准效果 ==========
async function generateTestcases() {
    if (state.questions.length === 0) { alert('请先加载题目'); return; }
    if (state.selectedTemplates.length === 0) { alert('请选择测试场景'); return; }
    
    showLoading('AI 生成中，请稍候...');
    
    try {
        const data = await apiCall('/api/testcase/generate', {
            method: 'POST',
            body: JSON.stringify({
                questions: state.questions,
                selected_templates: state.selectedTemplates,
                template_ratios: {}
            })
        });
        state.generatedEffects = data.base_effects || [];
        renderResults(data);
    } catch (e) {
        alert('生成失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

function renderResults(data) {
    const effects = data.base_effects || [];
    const summary = data.summary || {};
    
    if (effects.length === 0) {
        document.getElementById('resultEmpty').style.display = 'flex';
        document.getElementById('resultSummary').style.display = 'none';
        document.getElementById('resultTableContainer').style.display = 'none';
        document.getElementById('resultActions').style.display = 'none';
        document.getElementById('datasetNameSection').style.display = 'none';
        return;
    }
    
    document.getElementById('resultEmpty').style.display = 'none';
    document.getElementById('resultActions').style.display = 'flex';
    document.getElementById('totalCount').textContent = effects.length;
    document.getElementById('correctCount').textContent = summary.by_correct?.yes || 0;
    document.getElementById('wrongCount').textContent = (summary.by_correct?.no || 0) + (summary.by_correct?.partial || 0);
    document.getElementById('resultSummary').style.display = 'flex';
    
    // 显示数据集名称编辑区
    const bookName = state.currentBook?.book_name || '未知书本';
    document.getElementById('datasetNameInline').value = `${bookName}P${state.pageNum}-AI生成测试`;
    document.getElementById('datasetNameSection').style.display = 'block';
    
    const tbody = document.getElementById('resultTableBody');
    tbody.innerHTML = '';
    effects.forEach((item, idx) => {
        const tr = document.createElement('tr');
        tr.dataset.idx = idx;
        // 将 LaTeX 转换为可读文本显示
        const readableAnswer = latexToReadable(item.answer || '-');
        const readableUserAnswer = latexToReadable(item.userAnswer || '');
        tr.innerHTML = `
            <td class="cell-index">${escapeHtml(item.index || '-')}</td>
            <td>
                <select class="edit-select" onchange="updateEffect(${idx}, 'correct', this.value)">
                    <option value="yes" ${item.correct === 'yes' ? 'selected' : ''}>正确</option>
                    <option value="no" ${item.correct === 'no' ? 'selected' : ''}>错误</option>
                    <option value="partial" ${item.correct === 'partial' ? 'selected' : ''}>部分</option>
                </select>
            </td>
            <td class="cell-answer" title="${escapeHtml(item.answer || '-')}">${escapeHtml(readableAnswer)}</td>
            <td class="cell-user-answer">
                <textarea class="edit-textarea" rows="3"
                       onchange="updateEffect(${idx}, 'userAnswer', this.value)" placeholder="应填答案">${escapeHtml(readableUserAnswer)}</textarea>
            </td>
            <td>
                <input type="text" class="edit-input" value="${escapeHtml((item.tags || []).join(', '))}" 
                       onchange="updateEffectTags(${idx}, this.value)" placeholder="标签，逗号分隔">
            </td>
            <td>
                <input type="text" class="edit-input edit-input-wide" value="${escapeHtml(item.fillGuide || '')}" 
                       onchange="updateEffect(${idx}, 'fillGuide', this.value)" placeholder="填写指导">
            </td>
        `;
        tbody.appendChild(tr);
    });
    document.getElementById('resultTableContainer').style.display = 'block';
}

// 渲染对错状态
function renderCorrectStatus(correct) {
    const statusMap = {
        'yes': { label: '正确', class: 'status-correct' },
        'no': { label: '错误', class: 'status-wrong' },
        'partial': { label: '部分', class: 'status-partial' }
    };
    const status = statusMap[correct] || statusMap['no'];
    return `<span class="correct-status ${status.class}">${status.label}</span>`;
}

// 更新单个字段
function updateEffect(idx, field, value) {
    if (state.generatedEffects[idx]) {
        state.generatedEffects[idx][field] = value;
    }
}

// 更新标签（逗号分隔转数组）
function updateEffectTags(idx, value) {
    if (state.generatedEffects[idx]) {
        const tags = value.split(/[,，]/).map(t => t.trim()).filter(t => t);
        state.generatedEffects[idx].tags = tags;
    }
}

function getCorrectLabel(correct) {
    return { yes: '正确', no: '错误', partial: '部分' }[correct] || correct;
}


// ========== JSON 查看弹窗 ==========
function showJsonModal() {
    if (state.generatedEffects.length === 0) { alert('暂无数据'); return; }
    const jsonStr = JSON.stringify(state.generatedEffects, null, 2);
    document.getElementById('jsonPreview').textContent = jsonStr;
    document.getElementById('jsonModal').classList.add('show');
}

function hideJsonModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('jsonModal').classList.remove('show');
}

function copyJson() {
    const jsonStr = JSON.stringify(state.generatedEffects, null, 2);
    navigator.clipboard.writeText(jsonStr).then(() => {
        alert('已复制到剪贴板');
    }).catch(() => {
        // 降级方案
        const textarea = document.createElement('textarea');
        textarea.value = jsonStr;
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        document.body.removeChild(textarea);
        alert('已复制到剪贴板');
    });
}


// ========== 保存数据集 ==========
async function saveDataset() {
    if (state.generatedEffects.length === 0) { alert('请先生成基准效果'); return; }
    
    const name = document.getElementById('datasetNameInline').value.trim();
    if (!name) { alert('请输入数据集名称'); return; }
    
    // 获取是否保存评分的开关状态
    const saveScore = document.getElementById('saveScoreToggle')?.checked || false;
    
    // 根据开关状态处理数据
    let effectsToSave = state.generatedEffects;
    if (!saveScore) {
        // 不保存评分时，移除 score 和 maxScore 字段
        effectsToSave = state.generatedEffects.map(item => {
            const { score, maxScore, ...rest } = item;
            return rest;
        });
    }
    
    showLoading('保存中...');
    try {
        const data = await apiCall('/api/testcase/save', {
            method: 'POST',
            body: JSON.stringify({
                book_id: state.currentBook?.book_id,
                book_name: state.currentBook?.book_name,
                subject_id: state.subjectId,
                page_num: state.pageNum,
                base_effects: effectsToSave,
                dataset_name: name,
                description: '',
                save_score: saveScore
            })
        });
        alert(`保存成功！数据集ID: ${data.dataset_id}`);
    } catch (e) {
        alert('保存失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

// ========== 导出 Excel ==========
async function exportExcel() {
    if (state.generatedEffects.length === 0) { alert('请先生成基准效果'); return; }
    
    showLoading('导出中...');
    try {
        const headers = ['题号', '标准答案', '应填答案', '预期结果', '标签', '填写指导'];
        const rows = state.generatedEffects.map(item => [
            item.index || '', item.answer || '', item.userAnswer || '',
            getCorrectLabel(item.correct), (item.tags || []).join(', '), item.fillGuide || ''
        ]);
        
        const csvContent = [headers, ...rows]
            .map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))
            .join('\n');
        
        const blob = new Blob(['\ufeff' + csvContent], { type: 'text/csv;charset=utf-8;' });
        const a = document.createElement('a');
        a.href = URL.createObjectURL(blob);
        a.download = `测试用例_${state.pageNum || 'unknown'}.csv`;
        a.click();
        URL.revokeObjectURL(a.href);
    } catch (e) {
        alert('导出失败: ' + e.message);
    } finally {
        hideLoading();
    }
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (text === null || text === undefined) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function showLoading(text = '处理中...') {
    document.getElementById('loadingText').textContent = text;
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function goBack() {
    if (document.referrer && document.referrer.includes(location.host)) {
        history.back();
    } else {
        location.href = '/dataset-manage';
    }
}
