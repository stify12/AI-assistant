/**
 * 模拟手写 - 前端交互逻辑
 * 支持背景图上传、框选区域、手写生成与预览
 */

// ============ 状态管理 ============
const state = {
    fonts: [],
    backgroundImage: null,       // 原始背景图 Image 对象
    backgroundBase64: '',        // 背景图 base64
    _uploadedFileKey: '',        // 上传文件标识（用于框选记忆）
    generatedImages: [],         // 生成结果 base64 数组
    currentPage: 0,
    isGenerating: false,
    // 框选区域（相对于原始图片的坐标）
    selection: null,             // { x, y, width, height }
    // 框选交互状态
    isSelecting: false,
    selectionEnabled: false,
    dragStart: null,
    // canvas 显示比例
    displayScale: 1,
    imageNaturalWidth: 0,
    imageNaturalHeight: 0,
    // 小题模块与热区
    modules: [],                 // [{id, label, content, regions: [{id, x, y, w, h}]}]
    activeModuleId: null,
    isParsing: false,
    // 热区拖拽状态
    hotzoneDrag: null,           // {regionId, moduleId, startX, startY, origX, origY, origW, origH, mode}
};

// ============ 初始化 ============
document.addEventListener('DOMContentLoaded', () => {
    loadFonts();
    loadSavedSettings();
    setupEventListeners();
});

function setupEventListeners() {
    // 文字计数
    const textInput = document.getElementById('textInput');
    textInput.addEventListener('input', () => {
        document.getElementById('charCount').textContent = textInput.value.length + ' 字';
    });

    // 折叠面板通用处理
    function setupToggle(toggleId, panelId) {
        const toggle = document.getElementById(toggleId);
        if (!toggle) return;
        toggle.addEventListener('click', () => {
            const panel = document.getElementById(panelId);
            const icon = toggle.querySelector('.hw-toggle-icon');
            if (panel.style.display === 'none') {
                panel.style.display = 'block';
                if (icon) icon.classList.add('open');
            } else {
                panel.style.display = 'none';
                if (icon) icon.classList.remove('open');
            }
        });
    }
    setupToggle('layoutToggle', 'layoutPanel');
    setupToggle('advancedToggle', 'advancedPanel');

    // 框选交互
    const container = document.getElementById('previewContainer');
    container.addEventListener('mousedown', onSelectionMouseDown);
    document.addEventListener('mousemove', onSelectionMouseMove);
    document.addEventListener('mouseup', onSelectionMouseUp);
}

// ============ 字体加载 ============
async function loadFonts() {
    try {
        const resp = await fetch('/api/handwriting/fonts');
        const data = await resp.json();
        if (data.status === 'success') {
            state.fonts = data.fonts;
            const select = document.getElementById('fontSelect');
            select.innerHTML = '';
            if (data.fonts.length === 0) {
                select.innerHTML = '<option value="">暂无可用字体</option>';
            } else {
                data.fonts.forEach(f => {
                    const opt = document.createElement('option');
                    opt.value = f.filename;
                    opt.textContent = f.name;
                    select.appendChild(opt);
                });
            }
            if (!data.handright_available) {
                showToast('handright 库未安装，生成功能暂不可用', 'error');
            }
        }
    } catch (e) {
        console.error('加载字体列表出错:', e);
        showToast('加载字体列表时出了点问题', 'error');
    }
}

// ============ 框选区域记忆 ============
const SELECTION_STORE_KEY = 'hw_selection_regions';

function getBackgroundKey() {
    if (state.backgroundImageUrl) return state.backgroundImageUrl;
    if (state._uploadedFileKey) return state._uploadedFileKey;
    return null;
}

function saveSelectionForBackground() {
    const key = getBackgroundKey();
    if (!key) return;
    // 至少要有 selection 或 modules 才保存
    if (!state.selection && (!state.modules || state.modules.length === 0)) return;
    try {
        const store = JSON.parse(localStorage.getItem(SELECTION_STORE_KEY) || '{}');
        const entry = { timestamp: Date.now() };
        if (state.selection) entry.selection = state.selection;
        if (state.modules && state.modules.length > 0) {
            entry.modules = state.modules.map(m => ({
                id: m.id, label: m.label, content: m.content,
                answer: m.answer || '', maxScore: m.maxScore,
                regions: (m.regions || []).map(r => ({ id: r.id, x: r.x, y: r.y, w: r.w, h: r.h }))
            }));
        }
        store[key] = entry;
        localStorage.setItem(SELECTION_STORE_KEY, JSON.stringify(store));
    } catch (e) { /* ignore */ }
}

function removeSelectionForBackground() {
    const key = getBackgroundKey();
    if (!key) return;
    try {
        const store = JSON.parse(localStorage.getItem(SELECTION_STORE_KEY) || '{}');
        delete store[key];
        localStorage.setItem(SELECTION_STORE_KEY, JSON.stringify(store));
    } catch (e) { /* ignore */ }
}

function restoreSelectionForBackground() {
    const key = getBackgroundKey();
    if (!key) return;
    try {
        const store = JSON.parse(localStorage.getItem(SELECTION_STORE_KEY) || '{}');
        const entry = store[key];
        if (!entry) return;
        const msgs = [];
        if (entry.selection) {
            state.selection = entry.selection;
            state.selectionEnabled = true;
            document.getElementById('enableSelection').checked = true;
            showSavedSelection();
            msgs.push('框选区域');
        }
        if (entry.modules && entry.modules.length > 0) {
            state.modules = entry.modules;
            state.activeModuleId = null;
            if (typeof renderModules === 'function') renderModules();
            if (typeof renderHotzones === 'function') renderHotzones();
            const modulesCard = document.getElementById('modulesCard');
            if (modulesCard) modulesCard.style.display = 'block';
            const genBtn = document.getElementById('generateAnswersBtn');
            if (genBtn) genBtn.style.display = 'inline-flex';
            msgs.push(entry.modules.length + '道小题');
        }
        if (msgs.length > 0) {
            showToast('已恢复: ' + msgs.join(' + '), 'success');
        }
    } catch (e) { /* ignore */ }
}

function showSavedSelection() {
    if (!state.selection || !state.backgroundImage) return;
    const scale = state.displayScale || 1;
    const canvas = document.getElementById('previewCanvas');
    const containerRect = canvas.parentElement.getBoundingClientRect();
    const canvasRect = canvas.getBoundingClientRect();

    const left = state.selection.x * scale;
    const top = state.selection.y * scale;
    const width = state.selection.width * scale;
    const height = state.selection.height * scale;

    const overlay = document.getElementById('selectionOverlay');
    overlay.style.display = 'block';
    overlay.style.left = (canvasRect.left - containerRect.left + left) + 'px';
    overlay.style.top = (canvasRect.top - containerRect.top + top) + 'px';
    overlay.style.width = width + 'px';
    overlay.style.height = height + 'px';
    overlay.innerHTML = `
        <div class="hw-resize-handle nw"></div>
        <div class="hw-resize-handle ne"></div>
        <div class="hw-resize-handle sw"></div>
        <div class="hw-resize-handle se"></div>
    `;

    document.getElementById('clearSelectionBtn').style.display = 'inline-flex';
    document.getElementById('selectionInfo').textContent =
        `区域: ${state.selection.x}, ${state.selection.y} | ${state.selection.width} x ${state.selection.height} px (已恢复)`;
}

// ============ 设置保存/恢复 ============
const SETTINGS_KEY = 'hw_settings';
const SETTING_FIELDS = [
    'textInput', 'fontSelect', 'fontSize', 'lineSpacing', 'wordSpacing',
    'topMargin', 'bottomMargin', 'leftMargin', 'rightMargin', 'showLines',
    'canvasWidth', 'canvasHeight',
    'lineSpacingSigma', 'fontSizeSigma', 'wordSpacingSigma',
    'perturbXSigma', 'perturbYSigma', 'perturbThetaSigma'
];

function saveSettings() {
    const settings = {};
    SETTING_FIELDS.forEach(id => {
        const el = document.getElementById(id);
        if (!el) return;
        if (el.type === 'checkbox') {
            settings[id] = el.checked;
        } else {
            settings[id] = el.value;
        }
    });
    try {
        localStorage.setItem(SETTINGS_KEY, JSON.stringify(settings));
    } catch (e) { /* ignore */ }
}

function loadSavedSettings() {
    try {
        const raw = localStorage.getItem(SETTINGS_KEY);
        if (!raw) return;
        const settings = JSON.parse(raw);
        SETTING_FIELDS.forEach(id => {
            const el = document.getElementById(id);
            if (!el || settings[id] === undefined) return;
            if (el.type === 'checkbox') {
                el.checked = settings[id];
            } else {
                el.value = settings[id];
            }
        });
        // 更新字数
        const textInput = document.getElementById('textInput');
        document.getElementById('charCount').textContent = textInput.value.length + ' 字';
    } catch (e) { /* ignore */ }
}

function resetSettings() {
    const defaults = {
        fontSize: 80, lineSpacing: 120, wordSpacing: 1,
        topMargin: 50, bottomMargin: 50, leftMargin: 50, rightMargin: 50,
        canvasWidth: 2481, canvasHeight: 3507,
        lineSpacingSigma: 0, fontSizeSigma: 2, wordSpacingSigma: 2,
        perturbXSigma: 3, perturbYSigma: 3, perturbThetaSigma: 0.05
    };
    Object.entries(defaults).forEach(([id, val]) => {
        const el = document.getElementById(id);
        if (el) el.value = val;
    });
    document.getElementById('showLines').checked = true;
    showToast('参数已重置');
}

// ============ 背景图上传 ============
function onBackgroundUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    const reader = new FileReader();
    reader.onload = (e) => {
        const base64 = e.target.result;
        state.backgroundBase64 = base64;
        state._uploadedFileKey = 'upload:' + file.name + ':' + file.size;

        const img = new Image();
        img.onload = () => {
            state.backgroundImage = img;
            state.imageNaturalWidth = img.naturalWidth;
            state.imageNaturalHeight = img.naturalHeight;
            drawBackgroundToCanvas(img);
            const bgHint1 = document.getElementById('bgHint');
            if (bgHint1) bgHint1.style.display = 'none';
            document.getElementById('clearBgBtn').style.display = 'inline-flex';
            document.getElementById('canvasWidth').disabled = true;
            document.getElementById('canvasHeight').disabled = true;
            showToast('背景图已加载');
            restoreSelectionForBackground();
        };
        img.src = base64;
    };
    reader.readAsDataURL(file);
}

function drawBackgroundToCanvas(img) {
    const canvas = document.getElementById('previewCanvas');
    const dpr = window.devicePixelRatio || 1;

    // 以视口高度为基准，让图片像独立图片一样大
    const targetH = window.innerHeight - 120;
    const scale = targetH / img.naturalHeight;
    state.displayScale = scale;

    const cssW = Math.round(img.naturalWidth * scale);
    const cssH = Math.round(img.naturalHeight * scale);

    // canvas 物理像素 = CSS尺寸 × devicePixelRatio（高清渲染）
    canvas.width = cssW * dpr;
    canvas.height = cssH * dpr;
    canvas.style.width = cssW + 'px';
    canvas.style.height = cssH + 'px';

    const ctx = canvas.getContext('2d');
    ctx.scale(dpr, dpr);
    ctx.drawImage(img, 0, 0, cssW, cssH);

    canvas.style.display = 'block';
    document.getElementById('previewPlaceholder').style.display = 'none';
    // 解析按钮仅在选了书本页码时显示（需要 book_id + page_num）
    const hasBookPage = document.getElementById('bookSelect').value && document.getElementById('pageSelect').value;
    document.getElementById('aiParseBtn').style.display = hasBookPage ? 'flex' : 'none';
    // 重新渲染热区（画布尺寸可能变了）
    if (state.modules.length > 0) renderHotzones();
}

function clearBackground() {
    state.backgroundImage = null;
    state.backgroundBase64 = '';
    state.backgroundImageUrl = '';
    state._uploadedFileKey = '';
    state.selection = null;

    const canvas = document.getElementById('previewCanvas');
    canvas.style.display = 'none';
    document.getElementById('previewPlaceholder').style.display = 'flex';
    const bgHint2 = document.getElementById('bgHint');
    if (bgHint2) bgHint2.style.display = 'flex';
    document.getElementById('clearBgBtn').style.display = 'none';
    document.getElementById('bgImageInput').value = '';
    document.getElementById('canvasWidth').disabled = false;
    document.getElementById('canvasHeight').disabled = false;
    document.getElementById('selectionOverlay').style.display = 'none';
    document.getElementById('selectionInfo').textContent = '';
    document.getElementById('enableSelection').checked = false;
    state.selectionEnabled = false;
    document.getElementById('aiParseBtn').style.display = 'none';
    // 清除模块和热区
    state.modules = [];
    state.activeModuleId = null;
    document.getElementById('modulesCard').style.display = 'none';
    document.getElementById('hotzonesLayer').innerHTML = '';
    showToast('背景图已清除');
}

// ============ 科目/书本/页码选择 ============
async function onSubjectChange() {
    const subjectId = document.getElementById('subjectSelect').value;
    const bookSel = document.getElementById('bookSelect');
    const pageSel = document.getElementById('pageSelect');
    bookSel.innerHTML = '<option value="">加载中...</option>';
    pageSel.innerHTML = '<option value="">请先选择书本</option>';

    if (!subjectId) {
        bookSel.innerHTML = '<option value="">请先选择学科</option>';
        return;
    }
    try {
        const res = await fetch(`/api/handwriting/books?subject_id=${subjectId}`);
        const data = await res.json();
        if (data.success) {
            const books = data.data[subjectId] || [];
            bookSel.innerHTML = '<option value="">请选择书本</option>';
            books.forEach(b => {
                const o = document.createElement('option');
                o.value = b.book_id;
                o.textContent = `${b.book_name} (${b.page_count}页)`;
                bookSel.appendChild(o);
            });
            state._books = books;
        } else {
            bookSel.innerHTML = '<option value="">加载失败</option>';
        }
    } catch (e) {
        console.error('加载书本失败:', e);
        bookSel.innerHTML = '<option value="">加载失败</option>';
    }
}

async function onBookChange() {
    const bookId = document.getElementById('bookSelect').value;
    const pageSel = document.getElementById('pageSelect');
    pageSel.innerHTML = '<option value="">加载中...</option>';

    if (!bookId) {
        pageSel.innerHTML = '<option value="">请先选择书本</option>';
        return;
    }
    try {
        const res = await fetch(`/api/handwriting/books/${bookId}/pages`);
        const data = await res.json();
        if (data.success) {
            const pages = data.data.pages || [];
            pageSel.innerHTML = '<option value="">请选择页码</option>';
            pages.forEach(p => {
                const o = document.createElement('option');
                o.value = p.pic_path || '';
                o.textContent = `第 ${p.page_num} 页`;
                o.dataset.pageNum = p.page_num;
                pageSel.appendChild(o);
            });
            state._pages = pages;
        } else {
            pageSel.innerHTML = '<option value="">加载失败</option>';
        }
    } catch (e) {
        console.error('加载页码失败:', e);
        pageSel.innerHTML = '<option value="">加载失败</option>';
    }
}

function onPageChange() {
    const pageSel = document.getElementById('pageSelect');
    const picPath = pageSel.value;
    if (!picPath) return;

    showToast('正在加载页面图片...');
    const img = new Image();
    img.onload = () => {
        // Store URL for backend to download (avoids CORS taint)
        state.backgroundImageUrl = picPath;
        state.backgroundBase64 = '';
        state._uploadedFileKey = '';
        state.backgroundImage = img;
        state.imageNaturalWidth = img.naturalWidth;
        state.imageNaturalHeight = img.naturalHeight;
        drawBackgroundToCanvas(img);
        const bgHint3 = document.getElementById('bgHint');
        if (bgHint3) bgHint3.style.display = 'none';
        document.getElementById('clearBgBtn').style.display = 'inline-flex';
        document.getElementById('canvasWidth').disabled = true;
        document.getElementById('canvasHeight').disabled = true;
        showToast('页面图片已加载');
        restoreSelectionForBackground();
    };
    img.onerror = () => {
        showToast('图片加载失败，请检查网络或换一页', 'error');
    };
    img.src = picPath;
}

// ============ 框选区域 ============
function toggleSelection() {
    state.selectionEnabled = document.getElementById('enableSelection').checked;
    if (!state.selectionEnabled) {
        clearSelection();
    } else if (!state.backgroundImage && state.generatedImages.length === 0) {
        showToast('请先上传背景图片或生成预览图');
        document.getElementById('enableSelection').checked = false;
        state.selectionEnabled = false;
    }
}

function clearSelection() {
    removeSelectionForBackground();
    state.selection = null;
    document.getElementById('selectionOverlay').style.display = 'none';
    document.getElementById('clearSelectionBtn').style.display = 'none';
    document.getElementById('selectionInfo').textContent = '';
    // 重绘背景（清除框选）
    if (state.backgroundImage) {
        drawBackgroundToCanvas(state.backgroundImage);
    }
}

function onSelectionMouseDown(e) {
    if (!state.selectionEnabled) return;
    const canvas = document.getElementById('previewCanvas');
    if (canvas.style.display === 'none') return;

    const rect = canvas.getBoundingClientRect();
    const x = e.clientX - rect.left;
    const y = e.clientY - rect.top;

    if (x < 0 || y < 0 || x > canvas.width || y > canvas.height) return;

    state.isSelecting = true;
    state.dragStart = { x, y };

    const overlay = document.getElementById('selectionOverlay');
    overlay.style.display = 'block';
    overlay.style.left = (rect.left - canvas.parentElement.getBoundingClientRect().left + x) + 'px';
    overlay.style.top = (rect.top - canvas.parentElement.getBoundingClientRect().top + y) + 'px';
    overlay.style.width = '0px';
    overlay.style.height = '0px';

    e.preventDefault();
}

function onSelectionMouseMove(e) {
    if (!state.isSelecting || !state.dragStart) return;

    const canvas = document.getElementById('previewCanvas');
    const rect = canvas.getBoundingClientRect();
    const containerRect = canvas.parentElement.getBoundingClientRect();

    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;
    x = Math.max(0, Math.min(x, canvas.width));
    y = Math.max(0, Math.min(y, canvas.height));

    const left = Math.min(state.dragStart.x, x);
    const top = Math.min(state.dragStart.y, y);
    const width = Math.abs(x - state.dragStart.x);
    const height = Math.abs(y - state.dragStart.y);

    const overlay = document.getElementById('selectionOverlay');
    overlay.style.left = (rect.left - containerRect.left + left) + 'px';
    overlay.style.top = (rect.top - containerRect.top + top) + 'px';
    overlay.style.width = width + 'px';
    overlay.style.height = height + 'px';

    // 实时显示框选信息（转换为原始图片坐标）
    const scale = state.displayScale || 1;
    const realX = Math.round(left / scale);
    const realY = Math.round(top / scale);
    const realW = Math.round(width / scale);
    const realH = Math.round(height / scale);
    document.getElementById('selectionInfo').textContent =
        `区域: ${realX}, ${realY} | ${realW} x ${realH} px`;
}

function onSelectionMouseUp(e) {
    if (!state.isSelecting) return;
    state.isSelecting = false;

    const canvas = document.getElementById('previewCanvas');
    const rect = canvas.getBoundingClientRect();

    let x = e.clientX - rect.left;
    let y = e.clientY - rect.top;
    x = Math.max(0, Math.min(x, canvas.width));
    y = Math.max(0, Math.min(y, canvas.height));

    const left = Math.min(state.dragStart.x, x);
    const top = Math.min(state.dragStart.y, y);
    const width = Math.abs(x - state.dragStart.x);
    const height = Math.abs(y - state.dragStart.y);

    // 最小选区
    if (width < 10 || height < 10) {
        clearSelection();
        return;
    }

    const scale = state.displayScale || 1;
    state.selection = {
        x: Math.round(left / scale),
        y: Math.round(top / scale),
        width: Math.round(width / scale),
        height: Math.round(height / scale)
    };

    document.getElementById('clearSelectionBtn').style.display = 'inline-flex';
    saveSelectionForBackground();

    // 添加调整手柄
    const overlay = document.getElementById('selectionOverlay');
    overlay.innerHTML = `
        <div class="hw-resize-handle nw"></div>
        <div class="hw-resize-handle ne"></div>
        <div class="hw-resize-handle sw"></div>
        <div class="hw-resize-handle se"></div>
    `;
}

// ============ 生成手写 ============
async function generateHandwriting() {
    const text = document.getElementById('textInput').value.trim();
    console.log('[HW] generateHandwriting called, text:', text?.length, 'modules:', state.modules?.length);

    // 如果有小题模块且存在答案，自动走热区渲染路径
    if (!text && state.modules && state.modules.length > 0) {
        const withAnswer = state.modules.filter(m => m.answer && m.answer.trim());
        console.log('[HW] modules with answer:', withAnswer.length);
        if (withAnswer.length > 0) {
            return generateAnswersOnRegions();
        }
    }

    if (!text) {
        showToast('请输入要生成的文字');
        return;
    }

    if (state.isGenerating) {
        showToast('正在生成中，请稍候...');
        return;
    }

    state.isGenerating = true;
    document.getElementById('generateBtn').disabled = true;
    document.getElementById('loadingOverlay').style.display = 'flex';

    // 保存设置
    saveSettings();
    // 保存框选区域记忆（点击生成时才记录）
    saveSelectionForBackground();

    const params = {
        text: text,
        font_name: document.getElementById('fontSelect').value,
        font_size: parseInt(document.getElementById('fontSize').value) || 80,
        line_spacing: parseInt(document.getElementById('lineSpacing').value) || 120,
        word_spacing: parseInt(document.getElementById('wordSpacing').value) || 1,
        top_margin: parseInt(document.getElementById('topMargin').value) || 50,
        bottom_margin: parseInt(document.getElementById('bottomMargin').value) || 50,
        left_margin: parseInt(document.getElementById('leftMargin').value) || 50,
        right_margin: parseInt(document.getElementById('rightMargin').value) || 50,
        show_lines: document.getElementById('showLines').checked,
        width: parseInt(document.getElementById('canvasWidth').value) || 2481,
        height: parseInt(document.getElementById('canvasHeight').value) || 3507,
        // sigma
        line_spacing_sigma: parseInt(document.getElementById('lineSpacingSigma').value) || 0,
        font_size_sigma: parseInt(document.getElementById('fontSizeSigma').value) || 2,
        word_spacing_sigma: parseInt(document.getElementById('wordSpacingSigma').value) || 2,
        perturb_x_sigma: parseInt(document.getElementById('perturbXSigma').value) || 3,
        perturb_y_sigma: parseInt(document.getElementById('perturbYSigma').value) || 3,
        perturb_theta_sigma: parseFloat(document.getElementById('perturbThetaSigma').value) || 0.05,
    };

    // 背景图
    if (state.backgroundBase64) {
        params.background_image_base64 = state.backgroundBase64;
    } else if (state.backgroundImageUrl) {
        params.background_image_url = state.backgroundImageUrl;
    }

    // 框选区域
    if (state.selection && (state.backgroundBase64 || state.backgroundImageUrl)) {
        params.render_region = state.selection;
    }

    try {
        const resp = await fetch('/api/handwriting/generate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });

        const data = await resp.json();

        if (data.status === 'success' && data.images && data.images.length > 0) {
            state.generatedImages = data.images.map(b64 => 'data:image/png;base64,' + b64);
            state.currentPage = 0;
            displayPage(0);
            showToast(data.message || '生成完成', 'success');

            // 显示翻页和下载
            if (data.images.length > 1) {
                document.getElementById('pageNav').style.display = 'flex';
            } else {
                document.getElementById('pageNav').style.display = 'none';
            }
            document.getElementById('downloadBar').style.display = 'flex';
            updatePageNav();
        } else {
            showToast(data.message || '生成时遇到了问题', 'error');
        }
    } catch (e) {
        console.error('生成请求出错:', e);
        showToast('网络请求出了点问题，请检查服务器状态', 'error');
    } finally {
        state.isGenerating = false;
        document.getElementById('generateBtn').disabled = false;
        document.getElementById('loadingOverlay').style.display = 'none';
    }
}

// ============ 预览与翻页 ============
function displayPage(index) {
    if (index < 0 || index >= state.generatedImages.length) return;
    state.currentPage = index;

    const canvas = document.getElementById('previewCanvas');
    const container = document.getElementById('previewContainer');
    const img = new Image();
    img.onload = () => {
        const containerW = container.clientWidth - 34;
        const containerH = container.clientHeight - 34 || (window.innerHeight - 180);
        const scaleW = containerW / img.naturalWidth;
        const scaleH = containerH / img.naturalHeight;
        const scale = Math.min(scaleW, scaleH);
        state.displayScale = scale;
        state.imageNaturalWidth = img.naturalWidth;
        state.imageNaturalHeight = img.naturalHeight;

        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);

        const ctx = canvas.getContext('2d');
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);

        canvas.style.display = 'block';
        document.getElementById('previewPlaceholder').style.display = 'none';
    };
    img.src = state.generatedImages[index];
    updatePageNav();
}

// ============ 灯箱（点击放大） ============
function openLightbox() {
    if (state.generatedImages.length === 0) return;
    const overlay = document.createElement('div');
    overlay.className = 'hw-lightbox';
    overlay.id = 'hwLightbox';

    const img = document.createElement('img');
    img.src = state.generatedImages[state.currentPage];

    const closeBtn = document.createElement('button');
    closeBtn.className = 'hw-lightbox-close';
    closeBtn.innerHTML = '✕';
    closeBtn.onclick = closeLightbox;

    const total = state.generatedImages.length;

    if (total > 1) {
        const prevBtn = document.createElement('button');
        prevBtn.className = 'hw-lightbox-nav prev';
        prevBtn.innerHTML = '‹';
        prevBtn.disabled = state.currentPage === 0;
        prevBtn.onclick = (e) => { e.stopPropagation(); lightboxNav(-1); };

        const nextBtn = document.createElement('button');
        nextBtn.className = 'hw-lightbox-nav next';
        nextBtn.innerHTML = '›';
        nextBtn.disabled = state.currentPage === total - 1;
        nextBtn.onclick = (e) => { e.stopPropagation(); lightboxNav(1); };

        overlay.appendChild(prevBtn);
        overlay.appendChild(nextBtn);
    }

    const info = document.createElement('div');
    info.className = 'hw-lightbox-info';
    info.id = 'lightboxInfo';
    info.textContent = total > 1 ? `${state.currentPage + 1} / ${total}` : '';

    overlay.appendChild(img);
    overlay.appendChild(closeBtn);
    overlay.appendChild(info);

    // Delay attaching close handler to prevent immediate close from canvas click bubbling
    setTimeout(() => {
        overlay.onclick = (e) => { if (e.target === overlay) closeLightbox(); };
    }, 100);

    document.addEventListener('keydown', lightboxKeyHandler);
    document.body.appendChild(overlay);
}

function closeLightbox() {
    const lb = document.getElementById('hwLightbox');
    if (lb) {
        lb.style.animation = 'hwToastOut 0.2s ease forwards';
        setTimeout(() => { if (lb.parentNode) lb.parentNode.removeChild(lb); }, 200);
    }
    document.removeEventListener('keydown', lightboxKeyHandler);
}

function lightboxNav(dir) {
    const newIndex = state.currentPage + dir;
    if (newIndex < 0 || newIndex >= state.generatedImages.length) return;
    displayPage(newIndex);
    const lb = document.getElementById('hwLightbox');
    if (lb) {
        const img = lb.querySelector('img');
        if (img) img.src = state.generatedImages[state.currentPage];
        const info = document.getElementById('lightboxInfo');
        if (info) info.textContent = `${state.currentPage + 1} / ${state.generatedImages.length}`;
        const prevBtn = lb.querySelector('.hw-lightbox-nav.prev');
        const nextBtn = lb.querySelector('.hw-lightbox-nav.next');
        if (prevBtn) prevBtn.disabled = state.currentPage === 0;
        if (nextBtn) nextBtn.disabled = state.currentPage === state.generatedImages.length - 1;
    }
}

function lightboxKeyHandler(e) {
    if (e.key === 'Escape') closeLightbox();
    if (e.key === 'ArrowLeft') lightboxNav(-1);
    if (e.key === 'ArrowRight') lightboxNav(1);
}

function prevPage() {
    if (state.currentPage > 0) {
        displayPage(state.currentPage - 1);
    }
}

function nextPage() {
    if (state.currentPage < state.generatedImages.length - 1) {
        displayPage(state.currentPage + 1);
    }
}

function updatePageNav() {
    const total = state.generatedImages.length;
    const current = state.currentPage;
    document.getElementById('pageInfo').textContent = `${current + 1} / ${total}`;
    document.getElementById('prevPageBtn').disabled = current === 0;
    document.getElementById('nextPageBtn').disabled = current === total - 1;
}

// ============ 下载 ============
function downloadCurrentImage() {
    if (state.generatedImages.length === 0) return;
    const link = document.createElement('a');
    link.download = `handwriting_page_${state.currentPage + 1}.png`;
    link.href = state.generatedImages[state.currentPage];
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    showToast('已开始下载');
}

function downloadAllImages() {
    if (state.generatedImages.length === 0) return;
    state.generatedImages.forEach((src, i) => {
        setTimeout(() => {
            const link = document.createElement('a');
            link.download = `handwriting_page_${i + 1}.png`;
            link.href = src;
            document.body.appendChild(link);
            link.click();
            document.body.removeChild(link);
        }, i * 200);
    });
    showToast(`正在下载 ${state.generatedImages.length} 张图片`);
}

// ============ 解析小题（从数据库 data_value） ============
async function aiParseQuestions() {
    if (state.isParsing) return;

    // 需要已选择书本和页码
    const bookId = document.getElementById('bookSelect').value;
    const pageSel = document.getElementById('pageSelect');
    const pageOpt = pageSel.options[pageSel.selectedIndex];
    const pageNum = pageOpt ? pageOpt.dataset.pageNum : '';

    if (!bookId || !pageNum) {
        showToast('请先选择书本和页码', 'error');
        return;
    }

    state.isParsing = true;
    const btn = document.getElementById('aiParseBtn');
    btn.disabled = true;
    btn.textContent = '解析中...';
    showToast('正在解析小题...');

    try {
        const resp = await fetch('/api/handwriting/parse-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ book_id: bookId, page_num: parseInt(pageNum) })
        });
        const data = await resp.json();

        if (data.success && data.questions && data.questions.length > 0) {
            state.modules = data.questions.map((q, i) => ({
                id: 'mod_' + (i + 1),
                label: q.label || ('第' + q.id + '题'),
                content: q.content || '',
                answer: q.answer || '',
                maxScore: q.maxScore,
                expanded: true,
                regions: (q.regions || []).map((r, ri) => ({
                    id: 'reg_' + (i + 1) + '_' + (ri + 1),
                    x: r.x, y: r.y, w: r.w, h: r.h
                }))
            }));
            state.activeModuleId = state.modules[0]?.id || null;
            renderModules();
            renderHotzones();
            document.getElementById('modulesCard').style.display = 'block';
            saveSelectionForBackground();
            showToast(`解析完成，识别到 ${data.total} 道小题`, 'success');
        } else {
            showToast(data.error || '该页未找到小题数据', 'error');
        }
    } catch (e) {
        console.error('解析失败:', e);
        showToast('解析请求失败: ' + e.message, 'error');
    } finally {
        state.isParsing = false;
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg> 解析小题';
    }
}

// ============ 生成手写答案到热区 ============
async function generateAnswersOnRegions() {
    console.log('[HW] generateAnswersOnRegions called, modules:', state.modules?.length,
        'bgUrl:', state.backgroundImageUrl, 'bgB64:', !!state.backgroundBase64, 'bgImg:', !!state.backgroundImage);
    if (!state.modules || state.modules.length === 0) {
        showToast('请先解析小题', 'error');
        return;
    }
    if (!state.backgroundImage && !state.backgroundImageUrl && !state.backgroundBase64) {
        showToast('请先加载背景图片', 'error');
        return;
    }

    // 保存框选/热区记忆
    saveSelectionForBackground();

    // 检查是否有答案
    const withAnswer = state.modules.filter(m => m.answer && m.answer.trim());
    if (withAnswer.length === 0) {
        showToast('没有可渲染的答案', 'error');
        return;
    }

    // 统计热区总数
    const totalRegions = withAnswer.reduce((sum, m) => sum + (m.regions ? m.regions.length : 0), 0);

    const btn = document.getElementById('generateAnswersBtn');
    btn.disabled = true;
    btn.textContent = '生成中...';
    document.getElementById('loadingOverlay').style.display = 'flex';
    const loadingText = document.querySelector('.hw-loading-text');
    if (loadingText) loadingText.textContent = `正在生成 ${withAnswer.length} 道小题、${totalRegions} 个热区的手写答案...`;
    showToast(`正在生成 ${withAnswer.length} 道小题的手写答案...`);

    const params = {
        font_name: document.getElementById('fontSelect').value,
        font_size: parseInt(document.getElementById('fontSize').value) || 60,
        line_spacing: parseInt(document.getElementById('lineSpacing').value) || 80,
        word_spacing: parseInt(document.getElementById('wordSpacing').value) || 1,
        top_margin: 8,
        bottom_margin: 8,
        left_margin: 8,
        right_margin: 8,
        show_lines: false,
        font_size_sigma: parseInt(document.getElementById('fontSizeSigma').value) || 2,
        word_spacing_sigma: parseInt(document.getElementById('wordSpacingSigma').value) || 2,
        perturb_x_sigma: parseInt(document.getElementById('perturbXSigma').value) || 3,
        perturb_y_sigma: parseInt(document.getElementById('perturbYSigma').value) || 3,
        perturb_theta_sigma: parseFloat(document.getElementById('perturbThetaSigma').value) || 0.05,
        modules: state.modules.map(m => ({
            answer: m.answer || '',
            regions: m.regions.map(r => ({ x: r.x, y: r.y, w: r.w, h: r.h }))
        }))
    };

    // 背景图
    if (state.backgroundBase64) {
        params.background_image_base64 = state.backgroundBase64;
    } else if (state.backgroundImageUrl) {
        params.background_image_url = state.backgroundImageUrl;
    }

    try {
        const resp = await fetch('/api/handwriting/generate-answers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(params)
        });
        const data = await resp.json();

        if (data.status === 'success' && data.image) {
            // 用合成后的图片更新预览
            const imgSrc = 'data:image/png;base64,' + data.image;
            state.generatedImages = [imgSrc];
            state.currentPage = 0;

            const img = new Image();
            img.onload = () => {
                state.backgroundImage = img;
                state.imageNaturalWidth = img.naturalWidth;
                state.imageNaturalHeight = img.naturalHeight;
                drawBackgroundToCanvas(img);
                showToast(data.message || '生成完成', 'success');
                // 显示下载栏
                document.getElementById('downloadBar').style.display = 'flex';
                document.getElementById('pageNav').style.display = 'none';
            };
            img.src = imgSrc;
        } else {
            showToast(data.message || '生成失败', 'error');
        }
    } catch (e) {
        console.error('生成手写答案失败:', e);
        showToast('生成请求失败: ' + e.message, 'error');
    } finally {
        btn.disabled = false;
        btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/></svg> 生成手写答案';
        document.getElementById('loadingOverlay').style.display = 'none';
        const lt = document.querySelector('.hw-loading-text');
        if (lt) lt.textContent = '正在生成手写效果，请稍候...';
    }
}

// ============ 模块列表渲染 ============
function renderModules() {
    const list = document.getElementById('modulesList');
    list.innerHTML = '';
    state.modules.forEach((mod, idx) => {
        const item = document.createElement('div');
        item.className = 'hw-module-item' + (mod.id === state.activeModuleId ? ' active' : '');
        item.dataset.moduleId = mod.id;
        item.onclick = () => toggleModuleActive(mod.id);

        // ---- 顶部行：序号 + 标题 + 分值 + 删除 ----
        const topRow = document.createElement('div');
        topRow.className = 'hw-module-top';

        const numBadge = document.createElement('span');
        numBadge.className = 'hw-module-num';
        numBadge.textContent = idx + 1;

        const title = document.createElement('span');
        title.className = 'hw-module-title';
        title.textContent = mod.label;

        const metaWrap = document.createElement('div');
        metaWrap.className = 'hw-module-meta';

        if (mod.maxScore != null) {
            const scoreBadge = document.createElement('span');
            scoreBadge.className = 'hw-module-score';
            scoreBadge.textContent = mod.maxScore + '分';
            metaWrap.appendChild(scoreBadge);
        }

        const badge = document.createElement('span');
        badge.className = 'hw-module-badge';
        badge.textContent = mod.regions.length + '区';
        metaWrap.appendChild(badge);

        const delBtn = document.createElement('button');
        delBtn.className = 'hw-module-del';
        delBtn.title = '删除';
        delBtn.textContent = '✕';
        delBtn.onclick = (e) => { e.stopPropagation(); deleteModule(mod.id); };
        metaWrap.appendChild(delBtn);

        topRow.append(numBadge, title, metaWrap);
        item.appendChild(topRow);

        // ---- 题目内容 ----
        if (mod.content) {
            const contentDiv = document.createElement('div');
            contentDiv.className = 'hw-module-content';
            contentDiv.textContent = mod.content;
            item.appendChild(contentDiv);
        }

        // ---- 答案 ----
        if (mod.answer) {
            const ansDiv = document.createElement('div');
            ansDiv.className = 'hw-module-answer';
            ansDiv.innerHTML = '<span class="hw-ans-label">答案</span>' + mod.answer;
            item.appendChild(ansDiv);
        }

        // ---- 热区标签行 ----
        if (mod.regions.length > 0) {
            const regionsDiv = document.createElement('div');
            regionsDiv.className = 'hw-module-regions';
            mod.regions.forEach((r, ri) => {
                const tag = document.createElement('span');
                tag.className = 'hw-module-region-tag';
                tag.textContent = '区域' + (ri + 1);
                tag.onclick = (e) => { e.stopPropagation(); focusHotzone(mod.id, r.id); };
                regionsDiv.appendChild(tag);
            });
            const addBtn = document.createElement('button');
            addBtn.className = 'hw-module-region-add';
            addBtn.textContent = '+';
            addBtn.onclick = (e) => { e.stopPropagation(); addRegionToModule(mod.id); };
            regionsDiv.appendChild(addBtn);
            item.appendChild(regionsDiv);
        }

        list.appendChild(item);
    });
}

function toggleModuleActive(moduleId) {
    state.activeModuleId = state.activeModuleId === moduleId ? null : moduleId;
    renderModules();
    highlightHotzones();
}

function toggleModuleExpand(moduleId) {
    const mod = state.modules.find(m => m.id === moduleId);
    if (mod) {
        mod.expanded = !mod.expanded;
        renderModules();
    }
}

function deleteModule(moduleId) {
    state.modules = state.modules.filter(m => m.id !== moduleId);
    if (state.activeModuleId === moduleId) state.activeModuleId = null;
    renderModules();
    renderHotzones();
    saveSelectionForBackground();
    if (state.modules.length === 0) {
        document.getElementById('modulesCard').style.display = 'none';
    }
}

function addModule() {
    const nextNum = state.modules.length + 1;
    const mod = {
        id: 'mod_' + Date.now(),
        label: '第' + nextNum + '题',
        content: '',
        expanded: true,
        regions: [{
            id: 'reg_' + Date.now(),
            x: 0.1, y: 0.1 + (nextNum - 1) * 0.1, w: 0.3, h: 0.06
        }]
    };
    state.modules.push(mod);
    state.activeModuleId = mod.id;
    renderModules();
    renderHotzones();
    saveSelectionForBackground();
}

function addRegionToModule(moduleId) {
    const mod = state.modules.find(m => m.id === moduleId);
    if (!mod) return;
    const lastR = mod.regions[mod.regions.length - 1];
    const newY = lastR ? Math.min(lastR.y + lastR.h + 0.02, 0.9) : 0.2;
    mod.regions.push({
        id: 'reg_' + Date.now(),
        x: lastR ? lastR.x : 0.1,
        y: newY,
        w: lastR ? lastR.w : 0.3,
        h: lastR ? lastR.h : 0.06
    });
    renderModules();
    renderHotzones();
    saveSelectionForBackground();
}

function clearAllModules() {
    state.modules = [];
    state.activeModuleId = null;
    renderModules();
    renderHotzones();
    removeSelectionForBackground();
    document.getElementById('modulesCard').style.display = 'none';
}

// ============ 热区渲染 ============
function renderHotzones() {
    const layer = document.getElementById('hotzonesLayer');
    layer.innerHTML = '';
    const canvas = document.getElementById('previewCanvas');
    if (!canvas || canvas.style.display === 'none') return;

    const cw = canvas.clientWidth || canvas.width;
    const ch = canvas.clientHeight || canvas.height;

    state.modules.forEach(mod => {
        mod.regions.forEach(reg => {
            const hz = document.createElement('div');
            hz.className = 'hw-hotzone' + (mod.id === state.activeModuleId ? ' active' : '');
            hz.dataset.moduleId = mod.id;
            hz.dataset.regionId = reg.id;
            hz.style.left = (reg.x * cw) + 'px';
            hz.style.top = (reg.y * ch) + 'px';
            hz.style.width = (reg.w * cw) + 'px';
            hz.style.height = (reg.h * ch) + 'px';

            // 题号标签
            const label = document.createElement('span');
            label.className = 'hw-hotzone-label';
            label.textContent = mod.label;
            hz.appendChild(label);

            // 删除按钮
            const del = document.createElement('button');
            del.className = 'hw-hotzone-delete';
            del.textContent = '✕';
            del.onclick = (e) => { e.stopPropagation(); deleteRegion(mod.id, reg.id); };
            hz.appendChild(del);

            // 缩放手柄
            ['se', 'sw', 'ne', 'nw'].forEach(dir => {
                const handle = document.createElement('div');
                handle.className = 'hw-hotzone-resize ' + dir;
                handle.dataset.dir = dir;
                hz.appendChild(handle);
            });

            // 拖拽/缩放事件
            hz.addEventListener('mousedown', (e) => onHotzoneMouseDown(e, mod.id, reg.id));
            hz.addEventListener('click', (e) => {
                e.stopPropagation();
                state.activeModuleId = mod.id;
                renderModules();
                highlightHotzones();
            });

            layer.appendChild(hz);
        });
    });
}

function highlightHotzones() {
    document.querySelectorAll('.hw-hotzone').forEach(hz => {
        if (hz.dataset.moduleId === state.activeModuleId) {
            hz.classList.add('active');
        } else {
            hz.classList.remove('active');
        }
    });
}

function focusHotzone(moduleId, regionId) {
    state.activeModuleId = moduleId;
    renderModules();
    highlightHotzones();
    const hz = document.querySelector(`.hw-hotzone[data-region-id="${regionId}"]`);
    if (hz) hz.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

function deleteRegion(moduleId, regionId) {
    const mod = state.modules.find(m => m.id === moduleId);
    if (!mod) return;
    mod.regions = mod.regions.filter(r => r.id !== regionId);
    renderModules();
    renderHotzones();
    saveSelectionForBackground();
}

// ============ 热区拖拽与缩放 ============
function onHotzoneMouseDown(e, moduleId, regionId) {
    e.preventDefault();
    e.stopPropagation();

    const canvas = document.getElementById('previewCanvas');
    const cw = canvas.clientWidth || canvas.width;
    const ch = canvas.clientHeight || canvas.height;

    const mod = state.modules.find(m => m.id === moduleId);
    const reg = mod?.regions.find(r => r.id === regionId);
    if (!reg) return;

    // 判断是缩放手柄还是拖拽
    const handle = e.target.closest('.hw-hotzone-resize');
    const mode = handle ? handle.dataset.dir : 'move';

    state.hotzoneDrag = {
        regionId, moduleId, mode,
        startX: e.clientX,
        startY: e.clientY,
        origX: reg.x,
        origY: reg.y,
        origW: reg.w,
        origH: reg.h,
        cw, ch
    };

    document.addEventListener('mousemove', onHotzoneMouseMove);
    document.addEventListener('mouseup', onHotzoneMouseUp);
}

function onHotzoneMouseMove(e) {
    const d = state.hotzoneDrag;
    if (!d) return;

    const dx = (e.clientX - d.startX) / d.cw;
    const dy = (e.clientY - d.startY) / d.ch;

    const mod = state.modules.find(m => m.id === d.moduleId);
    const reg = mod?.regions.find(r => r.id === d.regionId);
    if (!reg) return;

    if (d.mode === 'move') {
        reg.x = Math.max(0, Math.min(1 - d.origW, d.origX + dx));
        reg.y = Math.max(0, Math.min(1 - d.origH, d.origY + dy));
    } else if (d.mode === 'se') {
        reg.w = Math.max(0.02, Math.min(1 - d.origX, d.origW + dx));
        reg.h = Math.max(0.02, Math.min(1 - d.origY, d.origH + dy));
    } else if (d.mode === 'sw') {
        const newW = Math.max(0.02, d.origW - dx);
        reg.x = d.origX + d.origW - newW;
        reg.w = newW;
        reg.h = Math.max(0.02, Math.min(1 - d.origY, d.origH + dy));
    } else if (d.mode === 'ne') {
        reg.w = Math.max(0.02, Math.min(1 - d.origX, d.origW + dx));
        const newH = Math.max(0.02, d.origH - dy);
        reg.y = d.origY + d.origH - newH;
        reg.h = newH;
    } else if (d.mode === 'nw') {
        const newW = Math.max(0.02, d.origW - dx);
        reg.x = d.origX + d.origW - newW;
        reg.w = newW;
        const newH = Math.max(0.02, d.origH - dy);
        reg.y = d.origY + d.origH - newH;
        reg.h = newH;
    }

    // 直接更新DOM位置（比重新渲染更流畅）
    const hz = document.querySelector(`.hw-hotzone[data-region-id="${d.regionId}"]`);
    if (hz) {
        hz.style.left = (reg.x * d.cw) + 'px';
        hz.style.top = (reg.y * d.ch) + 'px';
        hz.style.width = (reg.w * d.cw) + 'px';
        hz.style.height = (reg.h * d.ch) + 'px';
    }
}

function onHotzoneMouseUp() {
    state.hotzoneDrag = null;
    document.removeEventListener('mousemove', onHotzoneMouseMove);
    document.removeEventListener('mouseup', onHotzoneMouseUp);
    saveSelectionForBackground();
}

// ============ Toast 提示 ============
function showToast(message, type = 'info') {
    const container = document.getElementById('toastContainer');
    const toast = document.createElement('div');
    toast.className = `hw-toast ${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.style.animation = 'hwToastOut 0.3s ease forwards';
        setTimeout(() => {
            if (toast.parentNode) toast.parentNode.removeChild(toast);
        }, 300);
    }, 3000);
}
