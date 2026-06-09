/**
 * 测试用例生成器
 * AI 自动生成基准效果 - 支持多页并行、增量生成、按页分组
 */

// ========== LaTeX 转可读文本 ==========
const LATEX_TO_UNICODE = {
    '\\alpha': 'α', '\\beta': 'β', '\\gamma': 'γ', '\\delta': 'δ',
    '\\epsilon': 'ε', '\\theta': 'θ', '\\lambda': 'λ', '\\mu': 'μ',
    '\\pi': 'π', '\\sigma': 'σ', '\\phi': 'φ', '\\omega': 'ω',
    '\\Gamma': 'Γ', '\\Delta': 'Δ', '\\Theta': 'Θ', '\\Sigma': 'Σ', '\\Omega': 'Ω',
    '\\in': '∈', '\\notin': '∉', '\\subset': '⊂', '\\supset': '⊃',
    '\\subseteq': '⊆', '\\supseteq': '⊇', '\\cap': '∩', '\\cup': '∪',
    '\\emptyset': '∅', '\\varnothing': '∅',
    '\\geqslant': '≥', '\\leqslant': '≤',
    '\\leq': '≤', '\\le': '≤', '\\geq': '≥', '\\ge': '≥',
    '\\neq': '≠', '\\ne': '≠', '\\approx': '≈', '\\equiv': '≡',
    '\\times': '×', '\\div': '÷', '\\pm': '±', '\\cdot': '·',
    '\\to': '→', '\\rightarrow': '→', '\\leftarrow': '←',
    '\\Rightarrow': '⇒', '\\Leftarrow': '⇐', '\\Leftrightarrow': '⇔',
    '\\infty': '∞', '\\partial': '∂', '\\forall': '∀', '\\exists': '∃',
    '\\angle': '∠', '\\perp': '⊥', '\\parallel': '∥', '\\triangle': '△',
    '\\therefore': '∴', '\\because': '∵',
    '\\sqrt': '√', '\\sum': '∑', '\\int': '∫',
    '\\mathbb{R}': 'ℝ', '\\mathbb{N}': 'ℕ', '\\mathbb{Z}': 'ℤ',
    '\\R': 'ℝ', '\\N': 'ℕ', '\\Z': 'ℤ',
    '\\ldots': '…', '\\cdots': '⋯', '\\dots': '…',
    '\\mid': '|', '\\vert': '|',
    '\\quad': ' ', '\\qquad': '  ', '\\,': '', '\\;': '', '\\:': '', '\\ ': ' '
};
const LATEX_COMMANDS_TO_REMOVE = [
    '\\mathbf', '\\mathit', '\\mathrm', '\\mathsf', '\\mathcal', '\\mathbb',
    '\\textbf', '\\textit', '\\textrm', '\\bf', '\\it', '\\rm',
    '\\boldsymbol', '\\bm', '\\left', '\\right', '\\big', '\\Big',
    '\\displaystyle', '\\textstyle'
];
function latexToReadable(text) {
    if (!text) return '';
    text = String(text);
    text = text.replace(/\$\$([^$]+)\$\$/g, '$1').replace(/\$([^$]+)\$/g, '$1');
    text = text.replace(/\\\(([^)]+)\\\)/g, '$1');
    text = text.replace(/\\begin\{cases\}/g, '').replace(/\\end\{cases\}/g, '');
    text = text.replace(/\\\\/g, '; ');
    text = text.replace(/\\\[/g, '[').replace(/\\\]/g, ']');
    text = text.replace(/\\{/g, '⟨LB⟩').replace(/\\}/g, '⟨RB⟩');
    text = text.replace(/\\mid\b/g, ' | ').replace(/\\vert\b/g, '|');
    text = text.replace(/\\d?frac\s*\{([^{}]*)\}\s*\{([^{}]*)\}/g, '($1)/($2)');
    text = text.replace(/\\sqrt\s*\[([^\]]*)\]\s*\{([^{}]*)\}/g, '$1√($2)');
    text = text.replace(/\\sqrt\s*\{([^{}]*)\}/g, '√($1)');
    text = text.replace(/\^{([^{}]*)}/g, '^($1)').replace(/_{([^{}]*)}/g, '_($1)');
    LATEX_COMMANDS_TO_REMOVE.forEach(cmd => {
        const e = cmd.replace(/\\/g, '\\\\');
        text = text.replace(new RegExp(e + '\\s*\\{([^{}]*)\\}', 'g'), '$1');
        text = text.replace(new RegExp(e + '(?=[A-Za-z])', 'g'), '');
    });
    Object.entries(LATEX_TO_UNICODE)
        .filter(([k]) => !['\\{','\\}','\\mid','\\vert'].includes(k))
        .sort((a, b) => b[0].length - a[0].length)
        .forEach(([latex, unicode]) => {
            const e = latex.replace(/\\/g, '\\\\').replace(/\{/g, '\\{').replace(/\}/g, '\\}');
            text = text.replace(new RegExp(e, 'g'), unicode);
        });
    text = text.replace(/\\[a-zA-Z]+/g, '');
    text = text.replace(/⟨LB⟩/g, '{').replace(/⟨RB⟩/g, '}');
    return text.replace(/\s+/g, ' ').trim();
}

// ========== 状态管理 ==========
const state = {
    books: [],
    currentBook: null,
    pageNums: [],
    pageNum: null,
    questions: [],
    templates: {},
    combinations: {},
    selectedTemplates: [],
    // 增量生成：按页码存储结果 { pageNum: [effect, ...] }
    pageEffects: {},
    subjectId: 2,
    fromUrl: false,
    picPath: '',
    // 多页模式：按页码存储题目和图片 { pageNum: { questions: [], picPath: '' } }
    pageData: {},
    // 失败页记录 { pageNum: { error: '错误信息' } }
    failedPages: {}
};

// ========== 页码解析 ==========
function parsePageInput(input) {
    if (!input || !input.trim()) return [];
    const pages = new Set();
    input.split(/[,，\s]+/).filter(Boolean).forEach(part => {
        if (part.includes('-')) {
            const [s, e] = part.split('-').map(Number);
            if (s > 0 && e >= s && e <= 999) for (let i = s; i <= e; i++) pages.add(i);
        } else {
            const n = parseInt(part);
            if (n > 0 && n <= 999) pages.add(n);
        }
    });
    return [...pages].sort((a, b) => a - b);
}

/** 获取所有 effects 的扁平数组 */
function getAllEffects() {
    const all = [];
    Object.keys(state.pageEffects).sort((a, b) => a - b).forEach(p => {
        (state.pageEffects[p] || []).forEach(e => all.push(e));
    });
    return all;
}

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
    if (!state.fromUrl) loadBooks();
}
if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', init);
else init();

// ========== API ==========
async function apiCall(url, options = {}) {
    const res = await fetch(url, { headers: { 'Content-Type': 'application/json' }, ...options });
    const result = await res.json();
    if (!result.success) throw new Error(result.error || '请求失败');
    return result.data;
}

// ========== 加载模板 ==========
async function loadTemplates() {
    try {
        const data = await apiCall('/api/testcase/templates');
        state.templates = data.templates || {};
        state.combinations = data.combinations || {};
        renderTemplateList();
        selectCombination('quick_test');
    } catch (e) { console.error('加载模板失败:', e); }
}

// ========== 加载书本 ==========
async function loadBooks() {
    const subjectId = document.getElementById('subjectSelect').value;
    state.subjectId = parseInt(subjectId);
    try {
        const data = await apiCall(`/api/batch/books?subject_id=${subjectId}`);
        state.books = data[subjectId] || [];
        renderBookSelect();
    } catch (e) { state.books = []; renderBookSelect(); }
}
function renderBookSelect() {
    const sel = document.getElementById('bookSelect');
    if (!sel) return;
    sel.innerHTML = '<option value="">请选择书本</option>';
    state.books.forEach(b => {
        const o = document.createElement('option');
        o.value = b.book_id; o.textContent = b.book_name;
        sel.appendChild(o);
    });
}
function onBookChange() {
    const id = document.getElementById('bookSelect').value;
    state.currentBook = id ? state.books.find(b => b.book_id === id) : null;
    state.questions = []; state.pageNums = [];
    document.getElementById('questionsInfo').style.display = 'none';
    updateGenerateButton();
}
function changeBook() {
    state.fromUrl = false; state.currentBook = null;
    document.getElementById('bookInfo').style.display = 'none';
    document.getElementById('bookSelector').style.display = 'block';
    loadBooks();
}

// ========== 加载题目（支持多页） ==========
async function loadQuestions() {
    const input = document.getElementById('pageInput').value;
    const pageNums = parsePageInput(input);
    if (!pageNums.length) { showToast('请输入有效页码', 'error'); return; }
    if (!state.currentBook && !state.fromUrl) {
        const id = document.getElementById('bookSelect').value;
        if (!id) { showToast('请先选择书本', 'error'); return; }
        state.currentBook = state.books.find(b => b.book_id === id);
    }
    if (!state.currentBook) { showToast('请先选择书本', 'error'); return; }

    showLoading('加载题目中...');
    state.pageNums = pageNums;
    state.pageNum = pageNums[0];

    try {
        if (pageNums.length === 1) {
            const data = await apiCall(`/api/testcase/questions?book_id=${state.currentBook.book_id}&page_num=${pageNums[0]}`);
            state.questions = data.questions || [];
            state.picPath = data.picPath || '';
            if (data.book_name) state.currentBook.book_name = data.book_name;
            document.getElementById('questionCount').textContent = state.questions.length + ' 道';
            document.getElementById('questionStatus').textContent = '已加载 (P' + pageNums[0] + ')';
        } else {
            const results = await Promise.all(pageNums.map(p =>
                apiCall(`/api/testcase/questions?book_id=${state.currentBook.book_id}&page_num=${p}`)
                    .then(d => ({ page: p, success: true, data: d }))
                    .catch(e => ({ page: p, success: false, error: e.message }))
            ));
            let total = 0, ok = [], fail = [];
            state.questions = [];
            state.pageData = {};
            results.forEach(r => {
                if (r.success && r.data.questions) {
                    const qs = r.data.questions;
                    total += qs.length; ok.push(r.page);
                    // 按页存储题目和图片
                    state.pageData[r.page] = {
                        questions: qs,
                        picPath: r.data.picPath || ''
                    };
                    state.questions.push(...qs);
                    if (!state.picPath && r.data.picPath) state.picPath = r.data.picPath;
                    if (r.data.book_name) state.currentBook.book_name = r.data.book_name;
                } else fail.push(r.page);
            });
            document.getElementById('questionCount').textContent = total + ' 道';
            let status = `已加载 ${ok.length} 页 (${ok.map(p => 'P' + p).join(', ')})`;
            if (fail.length) { status += `，${fail.length} 页失败`; showToast(`页码 ${fail.join(',')} 加载失败`, 'error'); }
            document.getElementById('questionStatus').textContent = status;
        }
        document.getElementById('questionsInfo').style.display = 'block';
        renderQuestionDetail();
        updateGenerateButton();
    } catch (e) {
        showToast('加载题目失败: ' + e.message, 'error');
        state.questions = [];
        document.getElementById('questionsInfo').style.display = 'none';
        document.getElementById('questionDetailSection').style.display = 'none';
    } finally { hideLoading(); }
}

// ========== 渲染题目详情 ==========
function renderQuestionDetail() {
    const section = document.getElementById('questionDetailSection');
    if (!section || !state.questions.length) { if (section) section.style.display = 'none'; return; }
    section.style.display = 'block';
    const imgC = document.getElementById('pageImages');
    const listC = document.getElementById('questionList');

    if (state.pageNums.length > 1) {
        // 多页模式：按页分组渲染图片和题目
        const pages = Object.keys(state.pageData).map(Number).sort((a, b) => a - b);

        // 渲染每页图片
        if (imgC) {
            if (pages.some(p => state.pageData[p]?.picPath)) {
                imgC.innerHTML = pages.map(p => {
                    const pd = state.pageData[p];
                    if (!pd || !pd.picPath) return '';
                    return `<div class="page-image-item">
                        <div class="page-image-label">P${p}</div>
                        <img src="${escapeHtml(pd.picPath)}" alt="P${p} 电子版图片" onclick="showImageModal('${escapeHtml(pd.picPath)}')" />
                    </div>`;
                }).filter(Boolean).join('');
            } else {
                imgC.innerHTML = '<div class="empty-hint">暂无电子版图片</div>';
            }
        }

        // 渲染每页题目列表
        if (listC) {
            listC.innerHTML = pages.map(p => {
                const pd = state.pageData[p];
                if (!pd || !pd.questions.length) return '';
                const header = `<div class="page-group-label">P${p}（${pd.questions.length} 题）</div>`;
                const items = pd.questions.filter(Boolean).map((q, i) => {
                    const t = { '1': '单选', '2': '多选', '3': '判断', '4': '填空', '5': '主观' }[q.bvalue] || '其他';
                    return `<div class="question-item">
                        <div class="question-header"><span class="question-index">第 ${escapeHtml(q.index || (i+1))} 题</span><span class="question-type">${t}</span></div>
                        <div class="question-content">${escapeHtml(q.content || '暂无题目内容')}</div>
                        <div class="question-answer"><span class="answer-label">标准答案:</span><span class="answer-value">${escapeHtml(q.answer || '-')}</span></div>
                    </div>`;
                }).join('');
                return header + items;
            }).filter(Boolean).join('');
        }
    } else {
        // 单页模式
        if (imgC && state.picPath) {
            imgC.innerHTML = `<div class="page-image-item"><img src="${escapeHtml(state.picPath)}" alt="电子版图片" onclick="showImageModal('${escapeHtml(state.picPath)}')" /></div>`;
        } else if (imgC) imgC.innerHTML = '<div class="empty-hint">暂无电子版图片</div>';

        if (listC) {
            listC.innerHTML = state.questions.filter(Boolean).map((q, i) => {
                const t = { '1': '单选', '2': '多选', '3': '判断', '4': '填空', '5': '主观' }[q.bvalue] || '其他';
                return `<div class="question-item">
                    <div class="question-header"><span class="question-index">第 ${escapeHtml(q.index || (i+1))} 题</span><span class="question-type">${t}</span></div>
                    <div class="question-content">${escapeHtml(q.content || '暂无题目内容')}</div>
                    <div class="question-answer"><span class="answer-label">标准答案:</span><span class="answer-value">${escapeHtml(q.answer || '-')}</span></div>
                </div>`;
            }).join('');
        }
    }
}

function showImageModal(src) {
    const m = document.getElementById('imageModal'), img = document.getElementById('modalImage');
    if (m && img) { img.src = src; m.classList.add('show'); }
}
function hideImageModal(e) { if (e && e.target !== e.currentTarget) return; document.getElementById('imageModal').classList.remove('show'); }

// ========== 模板选择 ==========
function renderTemplateList() {
    const c = document.getElementById('templateList');
    c.innerHTML = '';
    Object.entries(state.templates).forEach(([id, tpl]) => {
        const div = document.createElement('div');
        div.className = 'template-item' + (state.selectedTemplates.includes(id) ? ' selected' : '');
        div.dataset.id = id;
        div.onclick = () => toggleTemplate(id);
        const et = tpl.correct === 'yes' ? '预期正确' : (tpl.correct === 'no' ? '预期错误' : '部分正确');
        const ec = tpl.correct === 'yes' ? 'expect-correct' : (tpl.correct === 'no' ? 'expect-wrong' : 'expect-partial');
        div.innerHTML = `<input type="checkbox" ${state.selectedTemplates.includes(id)?'checked':''} onclick="event.stopPropagation()">
            <div class="template-content"><div class="template-header"><span class="template-name">${escapeHtml(tpl.name)}</span><span class="template-expect ${ec}">${et}</span></div>
            <div class="template-hint">${escapeHtml(tpl.prompt_hint || '')}</div></div>`;
        c.appendChild(div);
    });
    updateSelectedCount();
}
function toggleTemplate(id) {
    const i = state.selectedTemplates.indexOf(id);
    if (i >= 0) state.selectedTemplates.splice(i, 1); else state.selectedTemplates.push(id);
    const item = document.querySelector(`.template-item[data-id="${id}"]`);
    if (item) { item.classList.toggle('selected', state.selectedTemplates.includes(id)); const cb = item.querySelector('input[type="checkbox"]'); if (cb) cb.checked = state.selectedTemplates.includes(id); }
    document.querySelectorAll('.combo-item').forEach(el => el.classList.remove('active'));
    updateSelectedCount(); updateGenerateButton();
}
function selectCombination(comboId) {
    const combo = state.combinations[comboId]; if (!combo) return;
    state.selectedTemplates = [...(combo.templates || [])];
    document.querySelectorAll('.combo-item').forEach(el => el.classList.toggle('active', el.dataset.combo === comboId));
    renderTemplateList(); updateGenerateButton();
}
function updateSelectedCount() { document.getElementById('selectedCount').textContent = state.selectedTemplates.length; }
function updateGenerateButton() { document.getElementById('generateBtn').disabled = state.questions.length === 0 || state.selectedTemplates.length === 0; }

// ========== 生成（增量累加） ==========
async function generateTestcases() {
    if (!state.questions.length) { showToast('请先加载题目', 'error'); return; }
    if (!state.selectedTemplates.length) { showToast('请选择测试场景', 'error'); return; }

    const isMulti = state.pageNums.length > 1;

    if (isMulti) {
        showLoadingWithProgress('多页并行生成中...', 0, `共 ${state.pageNums.length} 页`);
        try {
            const data = await apiCall('/api/testcase/generate-batch', {
                method: 'POST',
                body: JSON.stringify({ book_id: state.currentBook.book_id, page_nums: state.pageNums, selected_templates: state.selectedTemplates, template_ratios: {} })
            });
            // 增量累加：按 pageNum 分组存入 state.pageEffects
            (data.base_effects || []).forEach(e => {
                const p = e.pageNum || state.pageNums[0];
                if (!state.pageEffects[p]) state.pageEffects[p] = [];
                state.pageEffects[p].push(e);
                // 成功生成的页，清除失败记录
                delete state.failedPages[p];
            });
            // 记录失败页
            const pd = data.page_detail || {};
            Object.entries(pd).forEach(([p, detail]) => {
                const pNum = Number(p);
                if (!detail.success) {
                    state.failedPages[pNum] = { error: detail.error || '生成失败' };
                }
            });
            renderGroupedResults();
            const s = data.summary || {};
            if (s.failed_pages > 0) showToast(`${s.success_pages} 页成功，${s.failed_pages} 页失败`, 'warning');
            else showToast(`${s.success_pages} 页全部完成，共 ${data.base_effects.length} 条用例`, 'success');
        } catch (e) { showToast('生成失败: ' + e.message, 'error'); }
        finally { hideLoading(); }
    } else {
        showLoading('AI 生成中，每题并行处理...');
        try {
            const data = await apiCall('/api/testcase/generate', {
                method: 'POST',
                body: JSON.stringify({ questions: state.questions, selected_templates: state.selectedTemplates, template_ratios: {} })
            });
            const p = state.pageNums[0] || 0;
            const effects = (data.base_effects || []).map(e => ({ ...e, pageNum: p }));
            // 增量累加
            if (!state.pageEffects[p]) state.pageEffects[p] = [];
            state.pageEffects[p].push(...effects);
            renderGroupedResults();
            showToast(`生成完成，共 ${effects.length} 条用例（已累加）`, 'success');
        } catch (e) { showToast('生成失败: ' + e.message, 'error'); }
        finally { hideLoading(); }
    }
}

// ========== 按页分组渲染结果 ==========
function renderGroupedResults() {
    const container = document.getElementById('resultGroupContainer');
    const emptyEl = document.getElementById('resultEmpty');
    const summaryEl = document.getElementById('resultSummary');
    const actionsEl = document.getElementById('resultActions');

    const pages = Object.keys(state.pageEffects).map(Number).sort((a, b) => a - b);
    const failedPages = Object.keys(state.failedPages).map(Number).sort((a, b) => a - b);
    const allEffects = getAllEffects();

    if (!allEffects.length && !failedPages.length) {
        emptyEl.style.display = 'flex';
        summaryEl.style.display = 'none';
        container.style.display = 'none';
        actionsEl.style.display = 'none';
        return;
    }

    emptyEl.style.display = 'none';
    actionsEl.style.display = 'flex';

    // 总统计
    let yesCount = 0, noCount = 0;
    allEffects.forEach(e => {
        if (e.correct === 'yes') yesCount++;
        else noCount++;
    });
    document.getElementById('totalCount').textContent = allEffects.length;
    document.getElementById('correctCount').textContent = yesCount;
    document.getElementById('wrongCount').textContent = noCount;
    summaryEl.style.display = 'flex';

    // 按页渲染分组卡片
    container.style.display = 'block';
    container.innerHTML = '';

    pages.forEach(pageNum => {
        const effects = state.pageEffects[pageNum] || [];
        if (!effects.length) return;

        const card = document.createElement('div');
        card.className = 'page-group-card';
        card.dataset.page = pageNum;

        // 页头
        const header = document.createElement('div');
        header.className = 'page-group-header';
        header.innerHTML = `
            <div class="page-group-title">
                <span class="page-group-badge">P${pageNum}</span>
                <span class="page-group-count">${effects.length} 条用例</span>
            </div>
            <div class="page-group-actions">
                <button class="btn btn-secondary btn-small" onclick="clearPageEffects(${pageNum})">清空本页</button>
                <button class="btn btn-primary btn-small" onclick="savePageDataset(${pageNum})">保存本页</button>
            </div>
        `;
        card.appendChild(header);

        // 表格
        const showScore = document.getElementById('saveScoreToggle')?.checked || false;
        const tableWrap = document.createElement('div');
        tableWrap.className = 'page-group-table';
        const scoreHeaders = showScore
            ? '<th style="width:70px;">满分</th><th style="width:70px;">得分</th>'
            : '';
        tableWrap.innerHTML = `
            <table class="result-table">
                <thead><tr>
                    <th style="width:50px;">题号</th>
                    <th style="width:60px;">对错</th>
                    <th style="width:120px;">标准答案</th>
                    <th style="width:140px;">应填答案</th>
                    ${scoreHeaders}
                    <th style="width:160px;">标签</th>
                    <th>填写指导</th>
                    <th style="width:70px;"></th>
                </tr></thead>
                <tbody></tbody>
            </table>
        `;
        const tbody = tableWrap.querySelector('tbody');

        effects.forEach((item, idx) => {
            const tr = document.createElement('tr');
            const ra = latexToReadable(item.answer || '-');
            const ru = latexToReadable(item.userAnswer || '');
            const scoreCells = showScore ? `
                <td class="cell-score">
                    <input type="number" class="edit-input edit-input-score" value="${item.maxScore != null ? item.maxScore : ''}"
                           onchange="updatePageEffect(${pageNum}, ${idx}, 'maxScore', this.value === '' ? null : Number(this.value))" placeholder="-">
                </td>
                <td class="cell-score">
                    <input type="number" class="edit-input edit-input-score" value="${item.score != null ? item.score : ''}"
                           onchange="updatePageEffect(${pageNum}, ${idx}, 'score', this.value === '' ? null : Number(this.value))" placeholder="-">
                </td>` : '';
            tr.innerHTML = `
                <td class="cell-index">${escapeHtml(item.index || '-')}</td>
                <td>
                    <select class="edit-select" onchange="updatePageEffect(${pageNum}, ${idx}, 'correct', this.value)">
                        <option value="yes" ${item.correct==='yes'?'selected':''}>正确</option>
                        <option value="no" ${item.correct==='no'?'selected':''}>错误</option>
                    </select>
                </td>
                <td class="cell-answer" title="${escapeHtml(item.answer || '-')}">${escapeHtml(ra)}</td>
                <td class="cell-user-answer">
                    <textarea class="edit-textarea" rows="2" onchange="updatePageEffect(${pageNum}, ${idx}, 'userAnswer', this.value)" placeholder="应填答案">${escapeHtml(ru)}</textarea>
                </td>
                ${scoreCells}
                <td>
                    <input type="text" class="edit-input" value="${escapeHtml((item.tags||[]).join(', '))}"
                           onchange="updatePageEffectTags(${pageNum}, ${idx}, this.value)" placeholder="标签">
                </td>
                <td>
                    <input type="text" class="edit-input" value="${escapeHtml(item.fillGuide || '')}"
                           onchange="updatePageEffect(${pageNum}, ${idx}, 'fillGuide', this.value)" placeholder="填写指导">
                </td>
                <td class="cell-actions">
                    <button class="btn-regen" onclick="regenerateEffect(${pageNum}, ${idx})" title="重新生成此题">⟳</button>
                    <button class="btn-delete" onclick="deleteEffect(${pageNum}, ${idx})" title="删除此条">✕</button>
                </td>
            `;
            tbody.appendChild(tr);
        });

        card.appendChild(tableWrap);
        container.appendChild(card);
    });

    // 渲染失败页卡片
    failedPages.forEach(pageNum => {
        // 已有成功结果的页不再显示失败卡片
        if (state.pageEffects[pageNum] && state.pageEffects[pageNum].length) return;
        const info = state.failedPages[pageNum];
        const card = document.createElement('div');
        card.className = 'page-group-card page-group-failed';
        card.dataset.page = pageNum;
        card.innerHTML = `
            <div class="page-group-header">
                <div class="page-group-title">
                    <span class="page-group-badge badge-failed">P${pageNum}</span>
                    <span class="page-failed-msg">生成失败：${escapeHtml(info.error || '未知错误')}</span>
                </div>
                <div class="page-group-actions">
                    <button class="btn btn-primary btn-small" onclick="retryPageGenerate(${pageNum})">重新生成</button>
                </div>
            </div>
        `;
        container.appendChild(card);
    });
}

// ========== 单题重新生成 ==========
async function regenerateEffect(pageNum, idx) {
    const effects = state.pageEffects[pageNum];
    if (!effects || !effects[idx]) return;
    
    const item = effects[idx];
    const question = item._question;
    const templateId = item._templateId;
    
    if (!question || !templateId) {
        showToast('缺少原始题目信息，无法重新生成', 'error');
        return;
    }
    
    // 给该行加 loading 样式
    const row = document.querySelector(`.page-group-card[data-page="${pageNum}"] tbody tr:nth-child(${idx + 1})`);
    if (row) row.classList.add('row-loading');
    
    try {
        const data = await apiCall('/api/testcase/regenerate-single', {
            method: 'POST',
            body: JSON.stringify({ question, template_id: templateId })
        });
        // 替换该条 effect，保留 pageNum
        data.pageNum = pageNum;
        state.pageEffects[pageNum][idx] = data;
        renderGroupedResults();
        showToast('已重新生成', 'success', 2000);
    } catch (e) {
        showToast('重新生成失败: ' + e.message, 'error');
    } finally {
        if (row) row.classList.remove('row-loading');
    }
}

// ========== 评分字段开关 ==========
function onScoreToggleChange() {
    renderGroupedResults();
}

// ========== 编辑/删除操作 ==========
function updatePageEffect(pageNum, idx, field, value) {
    if (state.pageEffects[pageNum] && state.pageEffects[pageNum][idx]) {
        state.pageEffects[pageNum][idx][field] = value;
    }
}
function updatePageEffectTags(pageNum, idx, value) {
    if (state.pageEffects[pageNum] && state.pageEffects[pageNum][idx]) {
        state.pageEffects[pageNum][idx].tags = value.split(/[,，]/).map(t => t.trim()).filter(Boolean);
    }
}
function deleteEffect(pageNum, idx) {
    if (!state.pageEffects[pageNum]) return;
    state.pageEffects[pageNum].splice(idx, 1);
    // 如果该页已空，移除整个 key
    if (!state.pageEffects[pageNum].length) delete state.pageEffects[pageNum];
    renderGroupedResults();
    showToast('已删除', 'info', 2000);
}
function clearPageEffects(pageNum) {
    if (!confirm(`确定清空 P${pageNum} 的所有用例？`)) return;
    delete state.pageEffects[pageNum];
    renderGroupedResults();
    showToast(`P${pageNum} 已清空`, 'info', 2000);
}

// ========== 单页重新生成（失败页重试） ==========
async function retryPageGenerate(pageNum) {
    if (!state.currentBook) { showToast('缺少书本信息', 'error'); return; }
    if (!state.selectedTemplates.length) { showToast('请选择测试场景', 'error'); return; }

    // 给失败卡片加 loading 状态
    const card = document.querySelector(`.page-group-failed[data-page="${pageNum}"]`);
    if (card) card.classList.add('retrying');

    showLoading(`P${pageNum} 重新生成中...`);
    try {
        const data = await apiCall('/api/testcase/generate-batch', {
            method: 'POST',
            body: JSON.stringify({
                book_id: state.currentBook.book_id,
                page_nums: [pageNum],
                selected_templates: state.selectedTemplates,
                template_ratios: {}
            })
        });
        const effects = data.base_effects || [];
        if (effects.length) {
            if (!state.pageEffects[pageNum]) state.pageEffects[pageNum] = [];
            state.pageEffects[pageNum].push(...effects);
            delete state.failedPages[pageNum];
            showToast(`P${pageNum} 生成成功，${effects.length} 条用例`, 'success');
        } else {
            // 仍然失败
            const pd = data.page_detail || {};
            const detail = pd[pageNum] || {};
            state.failedPages[pageNum] = { error: detail.error || '生成失败，未返回结果' };
            showToast(`P${pageNum} 仍然失败`, 'error');
        }
        renderGroupedResults();
    } catch (e) {
        state.failedPages[pageNum] = { error: e.message };
        renderGroupedResults();
        showToast(`P${pageNum} 重新生成失败: ${e.message}`, 'error');
    } finally {
        hideLoading();
    }
}

// ========== 每页独立保存 ==========
async function savePageDataset(pageNum) {
    const effects = state.pageEffects[pageNum];
    if (!effects || !effects.length) { showToast('该页无数据', 'error'); return; }

    const bookName = state.currentBook?.book_name || '未知书本';
    const defaultName = `${bookName}P${pageNum}-AI生成测试`;
    const name = prompt('数据集名称', defaultName);
    if (!name) return;

    const saveScore = document.getElementById('saveScoreToggle')?.checked || false;
    let toSave = effects;
    if (!saveScore) toSave = effects.map(({ score, maxScore, ...rest }) => rest);

    showLoading('保存中...');
    try {
        const data = await apiCall('/api/testcase/save', {
            method: 'POST',
            body: JSON.stringify({
                book_id: state.currentBook?.book_id,
                book_name: bookName,
                subject_id: state.subjectId,
                page_num: pageNum,
                base_effects: toSave,
                dataset_name: name,
                description: '',
                save_score: saveScore
            })
        });
        hideLoading();
        showToast(`P${pageNum} 保存成功 — ${escapeHtml(data.name)}，${data.question_count} 条`, 'success', 6000,
            { text: '查看数据集', url: '/dataset-manage' });
    } catch (e) {
        hideLoading();
        showToast('保存失败: ' + e.message, 'error');
    }
}

// ========== 全部保存（合并所有页） ==========
async function saveAllDataset() {
    const allEffects = getAllEffects();
    if (!allEffects.length) { showToast('请先生成基准效果', 'error'); return; }

    const pages = Object.keys(state.pageEffects).map(Number).sort((a, b) => a - b);
    const bookName = state.currentBook?.book_name || '未知书本';
    const pageLabel = pages.length > 1 ? 'P' + pages.join('_') : 'P' + pages[0];
    const defaultName = `${bookName}${pageLabel}-AI生成测试`;

    const nameEl = document.getElementById('datasetNameInline');
    if (nameEl && !nameEl.value.trim()) nameEl.value = defaultName;
    const name = nameEl ? nameEl.value.trim() : defaultName;
    if (!name) { showToast('请输入数据集名称', 'error'); return; }

    const saveScore = document.getElementById('saveScoreToggle')?.checked || false;
    let toSave = allEffects;
    if (!saveScore) toSave = allEffects.map(({ score, maxScore, ...rest }) => rest);

    showLoading('保存中...');
    try {
        const data = await apiCall('/api/testcase/save', {
            method: 'POST',
            body: JSON.stringify({
                book_id: state.currentBook?.book_id,
                book_name: bookName,
                subject_id: state.subjectId,
                page_num: pages.length === 1 ? pages[0] : null,
                pages: pages.length > 1 ? pages : null,
                base_effects: toSave,
                dataset_name: name,
                description: '',
                save_score: saveScore
            })
        });
        hideLoading();
        showToast(`保存成功 — ${escapeHtml(data.name)}，共 ${data.question_count} 条`, 'success', 8000,
            { text: '查看数据集', url: '/dataset-manage' });
    } catch (e) {
        hideLoading();
        showToast('保存失败: ' + e.message, 'error');
    }
}

// ========== JSON / 导出 ==========
function showJsonModal() {
    const all = getAllEffects();
    if (!all.length) { showToast('暂无数据', 'error'); return; }
    document.getElementById('jsonPreview').textContent = JSON.stringify(all, null, 2);
    document.getElementById('jsonModal').classList.add('show');
}
function hideJsonModal(e) { if (e && e.target !== e.currentTarget) return; document.getElementById('jsonModal').classList.remove('show'); }
function copyJson() {
    const s = JSON.stringify(getAllEffects(), null, 2);
    navigator.clipboard.writeText(s).then(() => showToast('已复制', 'success', 2000)).catch(() => {
        const t = document.createElement('textarea'); t.value = s; document.body.appendChild(t); t.select(); document.execCommand('copy'); document.body.removeChild(t);
        showToast('已复制', 'success', 2000);
    });
}
function getCorrectLabel(c) { return { yes: '正确', no: '错误', partial: '部分' }[c] || c; }

async function exportExcel() {
    const all = getAllEffects();
    if (!all.length) { showToast('请先生成基准效果', 'error'); return; }
    try {
        const hasMulti = Object.keys(state.pageEffects).length > 1;
        const headers = hasMulti ? ['页码','题号','标准答案','应填答案','预期结果','标签','填写指导'] : ['题号','标准答案','应填答案','预期结果','标签','填写指导'];
        const rows = all.map(item => {
            const base = [item.index||'', item.answer||'', item.userAnswer||'', getCorrectLabel(item.correct), (item.tags||[]).join(', '), item.fillGuide||''];
            return hasMulti ? [item.pageNum||'', ...base] : base;
        });
        const csv = [headers, ...rows].map(r => r.map(c => `"${String(c).replace(/"/g,'""')}"`).join(',')).join('\n');
        const blob = new Blob(['\ufeff' + csv], { type: 'text/csv;charset=utf-8;' });
        const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
        const pages = Object.keys(state.pageEffects).sort((a,b)=>a-b);
        a.download = `测试用例_P${pages.join('_')}.csv`;
        a.click(); URL.revokeObjectURL(a.href);
        showToast('导出成功', 'success');
    } catch (e) { showToast('导出失败: ' + e.message, 'error'); }
}


// ========== Toast 提示 ==========
function showToast(message, type = 'info', duration = 4000, action = null) {
    const container = document.getElementById('toastContainer');
    if (!container) return;
    const icons = { success: '✓', error: '✕', warning: '!', info: 'i' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    let html = `<span class="toast-icon">${icons[type] || 'i'}</span><span class="toast-message">${message}</span>`;
    if (action && action.url) html += `<a class="toast-action" href="${action.url}">${escapeHtml(action.text || '查看')}</a>`;
    html += `<button class="toast-close" onclick="this.parentElement.remove()">×</button>`;
    toast.innerHTML = html;
    container.appendChild(toast);
    requestAnimationFrame(() => toast.classList.add('show'));
    setTimeout(() => { toast.classList.remove('show'); setTimeout(() => toast.remove(), 300); }, duration);
}

// ========== 加载遮罩 ==========
function showLoading(text = '处理中...') {
    const overlay = document.getElementById('loadingOverlay');
    const textEl = document.getElementById('loadingText');
    const progressEl = document.getElementById('loadingProgress');
    if (textEl) textEl.textContent = text;
    if (progressEl) progressEl.style.display = 'none';
    if (overlay) overlay.classList.add('show');
}

function showLoadingWithProgress(text, percent, detail) {
    const overlay = document.getElementById('loadingOverlay');
    const textEl = document.getElementById('loadingText');
    const progressEl = document.getElementById('loadingProgress');
    const fillEl = document.getElementById('progressFill');
    const detailEl = document.getElementById('progressDetail');
    if (textEl) textEl.textContent = text;
    if (progressEl) progressEl.style.display = 'block';
    if (fillEl && percent > 0) { fillEl.style.width = percent + '%'; fillEl.style.animation = 'none'; }
    else if (fillEl) { fillEl.style.width = ''; fillEl.style.animation = ''; }
    if (detailEl) detailEl.textContent = detail || '';
    if (overlay) overlay.classList.add('show');
}

function hideLoading() {
    const overlay = document.getElementById('loadingOverlay');
    if (overlay) overlay.classList.remove('show');
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

function goBack() {
    if (document.referrer && document.referrer.includes(window.location.host)) {
        window.history.back();
    } else {
        window.location.href = '/';
    }
}
