/**
 * 图片预处理工具 - 页面逻辑
 * 负责图片上传、步骤配置、参数调节、处理调用、结果渲染
 */

// ========== 状态变量 ==========
let currentImageBase64 = null;   // 当前上传的图片 base64（含 data URI 前缀）
let processedImageBase64 = null; // 处理后的图片 base64（不含前缀）
let stepResults = [];            // 步骤中间结果数组

// 步骤与参数面板的映射
const STEP_PARAM_MAP = {
    super_resolution: 'params_super_resolution',
    denoise: 'params_denoise',
    background_clean: 'params_background_clean',
    levels: 'params_levels',
    sharpen: 'params_sharpen',
    contrast: 'params_contrast',
    binarize: 'params_binarize',
};

// 滑块 ID 与显示值 ID 的映射
const SLIDER_VALUE_MAP = {
    param_super_resolution_sharpen_strength: 'value_super_resolution_sharpen_strength',
    param_denoise_kernel_size: 'value_denoise_kernel_size',
    param_background_clean_morph_size: 'value_background_clean_morph_size',
    param_background_clean_strength: 'value_background_clean_strength',
    param_levels_black_point: 'value_levels_black_point',
    param_levels_white_point: 'value_levels_white_point',
    param_levels_gamma: 'value_levels_gamma',
    param_sharpen_amount: 'value_sharpen_amount',
    param_sharpen_radius: 'value_sharpen_radius',
    param_sharpen_threshold: 'value_sharpen_threshold',
    param_contrast_clip_limit: 'value_contrast_clip_limit',
    param_contrast_tile_grid_size: 'value_contrast_tile_grid_size',
    param_binarize_block_size: 'value_binarize_block_size',
    param_binarize_constant_c: 'value_binarize_constant_c',
};

// 最大文件大小 10MB
const MAX_FILE_SIZE = 10 * 1024 * 1024;

// 允许的文件类型
const ALLOWED_TYPES = ['image/jpeg', 'image/png'];

// ========== 页面初始化 ==========
function initPage() {
    const uploadArea = document.getElementById('uploadArea');
    const fileInput = document.getElementById('imageUploadInput');

    // 点击上传区域触发文件选择
    uploadArea.addEventListener('click', function () {
        fileInput.click();
    });

    // 文件选择事件
    fileInput.addEventListener('change', handleImageUpload);

    // 拖拽事件
    uploadArea.addEventListener('dragover', handleDragOver);
    uploadArea.addEventListener('dragleave', handleDragLeave);
    uploadArea.addEventListener('drop', handleDrop);

    // 步骤开关事件 - 控制参数面板显隐
    var toggleIds = [
        'toggle_super_resolution', 'toggle_grayscale', 'toggle_denoise',
        'toggle_background_clean', 'toggle_levels', 'toggle_sharpen',
        'toggle_contrast', 'toggle_deskew', 'toggle_binarize', 'toggle_crop'
    ];
    toggleIds.forEach(function (id) {
        var el = document.getElementById(id);
        if (el) el.addEventListener('change', updateParamVisibility);
    });

    // 参数滑块事件 - 实时更新显示值
    Object.keys(SLIDER_VALUE_MAP).forEach(function (sliderId) {
        var slider = document.getElementById(sliderId);
        if (slider) {
            slider.addEventListener('input', function () {
                var valueEl = document.getElementById(SLIDER_VALUE_MAP[sliderId]);
                if (valueEl) valueEl.textContent = slider.value;
            });
        }
    });

    // 按钮事件
    document.getElementById('processBtn').addEventListener('click', processImage);
    document.getElementById('recognizeBtn').addEventListener('click', recognizeTest);

    // 图片点击放大 - lightbox
    initLightbox();

    // 初始化参数面板显隐状态
    updateParamVisibility();
}

// ========== 图片上传 ==========
function handleImageUpload(event) {
    var file = event.target.files[0];
    if (file) processFile(file);
}

function handleDragOver(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').classList.add('drag-over');
}

function handleDragLeave(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').classList.remove('drag-over');
}

function handleDrop(event) {
    event.preventDefault();
    event.stopPropagation();
    document.getElementById('uploadArea').classList.remove('drag-over');
    var file = event.dataTransfer.files[0];
    if (file) processFile(file);
}

function processFile(file) {
    // 校验文件格式
    if (ALLOWED_TYPES.indexOf(file.type) === -1) {
        alert('仅支持 JPG/PNG 格式图片');
        return;
    }

    // 校验文件大小
    if (file.size > MAX_FILE_SIZE) {
        alert('文件大小不能超过 10MB');
        return;
    }

    var reader = new FileReader();
    reader.onload = function (e) {
        currentImageBase64 = e.target.result; // data:image/...;base64,...

        // 显示上传预览
        var preview = document.getElementById('uploadPreview');
        var placeholder = document.getElementById('uploadPlaceholder');
        preview.src = currentImageBase64;
        preview.style.display = '';
        placeholder.style.display = 'none';

        // 显示原始图片
        var originalImg = document.getElementById('originalImage');
        var originalPlaceholder = document.getElementById('originalPlaceholder');
        originalImg.src = currentImageBase64;
        originalImg.style.display = '';
        originalPlaceholder.style.display = 'none';

        // 重置处理结果
        resetProcessedState();
    };
    reader.readAsDataURL(file);
}

// ========== 重置处理状态 ==========
function resetProcessedState() {
    processedImageBase64 = null;
    stepResults = [];

    // 隐藏处理后图片
    var processedImg = document.getElementById('processedImage');
    var processedPlaceholder = document.getElementById('processedPlaceholder');
    processedImg.style.display = 'none';
    processedImg.src = '';
    processedPlaceholder.style.display = '';

    // 重置步骤缩略图
    document.getElementById('stepThumbnails').innerHTML =
        '<div class="step-thumb-empty">处理后将在此展示每个步骤的中间结果</div>';

    // 隐藏识别结果和警告
    document.getElementById('recognizeSection').style.display = 'none';
    document.getElementById('warningsSection').style.display = 'none';

    // 禁用识别按钮
    document.getElementById('recognizeBtn').disabled = true;
}

// ========== 步骤配置 ==========
function buildStepsConfig() {
    return {
        super_resolution: document.getElementById('toggle_super_resolution').checked,
        grayscale: document.getElementById('toggle_grayscale').checked,
        denoise: document.getElementById('toggle_denoise').checked,
        background_clean: document.getElementById('toggle_background_clean').checked,
        levels: document.getElementById('toggle_levels').checked,
        sharpen: document.getElementById('toggle_sharpen').checked,
        contrast: document.getElementById('toggle_contrast').checked,
        deskew: document.getElementById('toggle_deskew').checked,
        binarize: document.getElementById('toggle_binarize').checked,
        crop: document.getElementById('toggle_crop').checked,
    };
}

function buildParamsConfig() {
    return {
        super_resolution: {
            scale: parseInt(document.querySelector('input[name="param_super_resolution_scale"]:checked').value),
            sharpen_strength: parseFloat(document.getElementById('param_super_resolution_sharpen_strength').value),
        },
        denoise: {
            kernel_size: parseInt(document.getElementById('param_denoise_kernel_size').value),
        },
        background_clean: {
            morph_size: parseInt(document.getElementById('param_background_clean_morph_size').value),
            strength: parseFloat(document.getElementById('param_background_clean_strength').value),
        },
        levels: {
            black_point: parseInt(document.getElementById('param_levels_black_point').value),
            white_point: parseInt(document.getElementById('param_levels_white_point').value),
            gamma: parseFloat(document.getElementById('param_levels_gamma').value),
        },
        sharpen: {
            amount: parseFloat(document.getElementById('param_sharpen_amount').value),
            radius: parseInt(document.getElementById('param_sharpen_radius').value),
            threshold: parseInt(document.getElementById('param_sharpen_threshold').value),
        },
        contrast: {
            clip_limit: parseFloat(document.getElementById('param_contrast_clip_limit').value),
            tile_grid_size: parseInt(document.getElementById('param_contrast_tile_grid_size').value),
        },
        binarize: {
            block_size: parseInt(document.getElementById('param_binarize_block_size').value),
            constant_c: parseInt(document.getElementById('param_binarize_constant_c').value),
        },
    };
}

// ========== 步骤开关联动参数面板 ==========
function updateParamVisibility() {
    var anyVisible = false;

    for (var step in STEP_PARAM_MAP) {
        var toggle = document.getElementById('toggle_' + step);
        var paramGroup = document.getElementById(STEP_PARAM_MAP[step]);
        if (toggle && paramGroup) {
            var show = toggle.checked;
            paramGroup.style.display = show ? '' : 'none';
            if (show) anyVisible = true;
        }
    }

    // 无可调参数时显示提示
    var paramEmpty = document.getElementById('paramEmpty');
    if (paramEmpty) {
        paramEmpty.style.display = anyVisible ? 'none' : '';
    }
}

// ========== 处理图片 ==========
async function processImage() {
    if (!currentImageBase64) {
        alert('请先上传图片');
        return;
    }

    showLoading('正在处理图片...');

    try {
        var response = await fetch('/api/image-preprocess/process', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: currentImageBase64,
                steps: buildStepsConfig(),
                params: buildParamsConfig(),
            }),
        });

        var result = await response.json();

        if (!result.success) {
            alert(result.error || '处理失败');
            return;
        }

        // 更新状态
        processedImageBase64 = result.data.processed_image;
        stepResults = result.data.step_results || [];

        // 渲染处理后图片
        renderProcessedImage(processedImageBase64);

        // 渲染步骤缩略图
        renderStepResults(stepResults);

        // 渲染警告信息
        renderWarnings(result.data.warnings, result.data.param_corrections);

        // 启用识别按钮
        document.getElementById('recognizeBtn').disabled = false;

    } catch (error) {
        alert('处理请求失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

// ========== 渲染处理结果 ==========
function renderProcessedImage(base64) {
    var img = document.getElementById('processedImage');
    var placeholder = document.getElementById('processedPlaceholder');
    img.src = 'data:image/png;base64,' + base64;
    img.style.display = '';
    placeholder.style.display = 'none';
}

function renderStepResults(results) {
    var container = document.getElementById('stepThumbnails');

    if (!results || results.length === 0) {
        container.innerHTML = '<div class="step-thumb-empty">无处理步骤结果</div>';
        return;
    }

    container.innerHTML = '';
    results.forEach(function (step, index) {
        var thumb = document.createElement('div');
        thumb.className = 'step-thumb' + (index === results.length - 1 ? ' active' : '');
        thumb.innerHTML =
            '<img src="data:image/png;base64,' + step.image + '" alt="' + escapeHtml(step.label) + '">' +
            '<div class="step-thumb-label">' + escapeHtml(step.label) + '</div>';
        // 单击切换预览，双击放大
        thumb.onclick = (function (i) {
            return function () { selectStepPreview(i); };
        })(index);
        thumb.ondblclick = (function (imgData) {
            return function (e) {
                e.stopPropagation();
                openLightbox('data:image/png;base64,' + imgData);
            };
        })(step.image);
        container.appendChild(thumb);
    });
}

function selectStepPreview(index) {
    if (!stepResults[index]) return;

    // 更新处理后图片为该步骤的结果
    var img = document.getElementById('processedImage');
    img.src = 'data:image/png;base64,' + stepResults[index].image;

    // 更新缩略图激活状态
    var thumbs = document.querySelectorAll('.step-thumb');
    thumbs.forEach(function (thumb, i) {
        thumb.classList.toggle('active', i === index);
    });
}

function renderWarnings(warnings, corrections) {
    var section = document.getElementById('warningsSection');
    var list = document.getElementById('warningsList');

    var allMessages = (warnings || []).concat(corrections || []);

    if (allMessages.length === 0) {
        section.style.display = 'none';
        return;
    }

    list.innerHTML = allMessages.map(function (msg) {
        return '<div class="warning-item">' + escapeHtml(msg) + '</div>';
    }).join('');
    section.style.display = '';
}

// ========== 识别测试 ==========
async function recognizeTest() {
    if (!currentImageBase64 || !processedImageBase64) {
        alert('请先上传并处理图片');
        return;
    }

    showLoading('正在调用 LLM 视觉模型识别...');

    try {
        var response = await fetch('/api/image-preprocess/recognize', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                original_image: currentImageBase64,
                processed_image: processedImageBase64,
                prompt: '请识别图片中的作业内容，包括题目和答案',
            }),
        });

        var result = await response.json();

        if (!result.success) {
            alert(result.error || '识别失败');
            return;
        }

        renderRecognizeResults(result.data);

    } catch (error) {
        alert('识别请求失败: ' + error.message);
    } finally {
        hideLoading();
    }
}

function renderRecognizeResults(data) {
    var section = document.getElementById('recognizeSection');
    document.getElementById('originalResult').textContent = data.original_result || '无结果';
    document.getElementById('processedResult').textContent = data.processed_result || '无结果';
    section.style.display = '';
}

// ========== 工具函数 ==========
function showLoading(text) {
    document.getElementById('loadingText').textContent = text || '处理中...';
    document.getElementById('loadingOverlay').classList.add('show');
}

function hideLoading() {
    document.getElementById('loadingOverlay').classList.remove('show');
}

function escapeHtml(text) {
    var div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// ========== 图片放大 Lightbox ==========
function initLightbox() {
    // 使用新的图片灯箱组件（支持滚动缩放、拖拽等功能）
    
    // 原始图片点击放大
    const originalImg = document.getElementById('originalImage');
    originalImg.style.cursor = 'zoom-in';
    originalImg.addEventListener('click', function () {
        if (this.src && window.imageLightbox) {
            window.imageLightbox.open(this.src, '原始图片');
        }
    });

    // 处理后图片点击放大
    const processedImg = document.getElementById('processedImage');
    processedImg.style.cursor = 'zoom-in';
    processedImg.addEventListener('click', function () {
        if (this.src && window.imageLightbox) {
            window.imageLightbox.open(this.src, '处理后图片');
        }
    });
    
    // 步骤缩略图点击放大
    document.addEventListener('click', function(e) {
        if (e.target.classList.contains('step-thumb-img')) {
            if (window.imageLightbox) {
                const stepName = e.target.alt || '步骤预览';
                window.imageLightbox.open(e.target.src, stepName);
            }
        }
    });
}

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', initPage);
