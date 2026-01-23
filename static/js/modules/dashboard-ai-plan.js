/**
 * AI 生成测试计划模块
 * @module dashboard-ai-plan
 */

import { DashboardAPI } from './dashboard-api.js';
import { 
    SUBJECT_MAP, 
    escapeHtml, showToast, formatNumber
} from './dashboard-utils.js';

// ========== 状态 ==========

let selectedDatasets = new Set();
let generatedPlan = null;
let currentStep = 1;
let isGenerating = false;

// ========== 初始化 ==========

/**
 * 初始化 AI 计划模块
 */
export function initAIPlanModule() {
    setupStepIndicator();
}

/**
 * 设置步骤指示器
 */
function setupStepIndicator() {
    const steps = document.querySelectorAll('.ai-plan-step');
    steps.forEach((step, index) => {
        step.addEventListener('click', () => {
            if (index + 1 < currentStep) {
                goToStep(index + 1);
            }
        });
    });
}

// ========== 弹窗控制 ==========

/**
 * 打开 AI 生成计划弹窗
 */
export async function openAIPlanModal() {
    const modal = document.getElementById('aiPlanModal');
    if (!modal) return;
    
    // 重置状态
    selectedDatasets.clear();
    generatedPlan = null;
    currentStep = 1;
    isGenerating = false;
    
    // 显示弹窗
    modal.style.display = 'flex';
    
    // 加载数据集列表
    await loadDatasetList();
    
    // 更新 UI
    updateStepUI();
}

/**
 * 关闭 AI 生成计划弹窗
 */
export function closeAIPlanModal() {
    const modal = document.getElementById('aiPlanModal');
    if (modal) modal.style.display = 'none';
}

/**
 * 弹窗背景点击
 */
export function onAIPlanModalBackdropClick(event) {
    if (event.target.id === 'aiPlanModal') {
        closeAIPlanModal();
    }
}


// ========== 步骤控制 ==========

/**
 * 跳转到指定步骤
 * @param {number} step - 步骤号 (1-4)
 */
function goToStep(step) {
    currentStep = step;
    updateStepUI();
}

/**
 * 更新步骤 UI
 */
function updateStepUI() {
    // 更新步骤指示器
    const steps = document.querySelectorAll('.ai-plan-step');
    steps.forEach((stepEl, index) => {
        const stepNum = index + 1;
        stepEl.classList.remove('active', 'completed');
        if (stepNum === currentStep) {
            stepEl.classList.add('active');
        } else if (stepNum < currentStep) {
            stepEl.classList.add('completed');
        }
    });
    
    // 显示/隐藏内容区域
    document.getElementById('aiPlanStep1')?.classList.toggle('hidden', currentStep !== 1);
    document.getElementById('aiPlanStep2')?.classList.toggle('hidden', currentStep !== 2);
    document.getElementById('aiPlanStep3')?.classList.toggle('hidden', currentStep !== 3);
    document.getElementById('aiPlanStep4')?.classList.toggle('hidden', currentStep !== 4);
    
    // 更新按钮状态
    updateButtonState();
}

/**
 * 更新按钮状态
 */
function updateButtonState() {
    const generateBtn = document.getElementById('aiPlanGenerateBtn');
    const saveBtn = document.getElementById('aiPlanSaveBtn');
    const backBtn = document.getElementById('aiPlanBackBtn');
    
    if (generateBtn) {
        generateBtn.style.display = currentStep === 1 ? 'inline-flex' : 'none';
        generateBtn.disabled = selectedDatasets.size === 0 || isGenerating;
    }
    
    if (saveBtn) {
        saveBtn.style.display = currentStep === 3 ? 'inline-flex' : 'none';
    }
    
    if (backBtn) {
        backBtn.style.display = currentStep > 1 ? 'inline-flex' : 'none';
    }
}

// ========== 数据集选择 ==========

/**
 * 加载数据集列表
 */
async function loadDatasetList() {
    const container = document.getElementById('aiPlanDatasetGrid');
    if (!container) return;
    
    container.innerHTML = '<div class="loading-text">加载数据集...</div>';
    
    try {
        const res = await DashboardAPI.getDatasets();
        if (res.success) {
            renderDatasetCards(res.data.datasets || []);
        } else {
            container.innerHTML = '<div class="error-text">加载失败</div>';
        }
    } catch (error) {
        console.error('[AIPlan] 加载数据集失败:', error);
        container.innerHTML = '<div class="error-text">加载失败</div>';
    }
}

/**
 * 渲染数据集卡片
 * @param {Array} datasets - 数据集列表
 */
function renderDatasetCards(datasets) {
    const container = document.getElementById('aiPlanDatasetGrid');
    if (!container) return;
    
    if (datasets.length === 0) {
        container.innerHTML = '<div class="empty-text">暂无数据集，请先创建数据集</div>';
        return;
    }
    
    // 按学科分组
    const grouped = {};
    datasets.forEach(ds => {
        const subjectId = ds.subject_id || 'unknown';
        if (!grouped[subjectId]) grouped[subjectId] = [];
        grouped[subjectId].push(ds);
    });
    
    container.innerHTML = Object.entries(grouped).map(([subjectId, dsList]) => {
        const subjectName = SUBJECT_MAP[subjectId] || '其他';
        
        return `
            <div class="dataset-group">
                <div class="dataset-group-title">${escapeHtml(subjectName)}</div>
                <div class="dataset-cards">
                    ${dsList.map(ds => renderDatasetCard(ds)).join('')}
                </div>
            </div>
        `;
    }).join('');
    
    // 绑定点击事件
    container.querySelectorAll('.dataset-card').forEach(card => {
        card.addEventListener('click', () => toggleDatasetSelection(card));
    });
}

/**
 * 渲染单个数据集卡片
 * @param {Object} ds - 数据集
 * @returns {string} HTML
 */
function renderDatasetCard(ds) {
    const isSelected = selectedDatasets.has(ds.dataset_id);
    const accuracy = ds.history_accuracy !== null && ds.history_accuracy !== undefined
        ? (ds.history_accuracy * 100).toFixed(0) + '%'
        : '--';
    
    return `
        <div class="dataset-card ${isSelected ? 'selected' : ''}" data-id="${ds.dataset_id}">
            <div class="dataset-card-check">
                <svg viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
            </div>
            <div class="dataset-card-name">${escapeHtml(truncateName(ds.name, 18))}</div>
            <div class="dataset-card-meta">
                <span>${ds.question_count || 0}题</span>
                <span>准确率 ${accuracy}</span>
            </div>
        </div>
    `;
}

/**
 * 切换数据集选择
 * @param {HTMLElement} card - 卡片元素
 */
function toggleDatasetSelection(card) {
    const datasetId = card.dataset.id;
    
    if (selectedDatasets.has(datasetId)) {
        selectedDatasets.delete(datasetId);
        card.classList.remove('selected');
    } else {
        selectedDatasets.add(datasetId);
        card.classList.add('selected');
    }
    
    // 更新选中计数
    updateSelectionCount();
    updateButtonState();
}

/**
 * 更新选中计数
 */
function updateSelectionCount() {
    const countEl = document.getElementById('aiPlanSelectedCount');
    if (countEl) {
        countEl.textContent = `已选择 ${selectedDatasets.size} 个数据集`;
    }
}

/**
 * 截断名称
 */
function truncateName(name, maxLen) {
    if (!name) return '';
    if (name.length <= maxLen) return name;
    return name.slice(0, maxLen - 3) + '...';
}


// ========== AI 生成 ==========

/**
 * 开始生成测试计划
 */
export async function generateAIPlan() {
    if (selectedDatasets.size === 0) {
        showToast('请至少选择一个数据集', 'warning');
        return;
    }
    
    if (isGenerating) return;
    
    isGenerating = true;
    goToStep(2);
    
    // 显示进度
    updateProgress(0, '正在分析数据集...');
    
    try {
        const sampleCount = parseInt(document.getElementById('aiPlanSampleCount')?.value) || 30;
        const subjectId = document.getElementById('aiPlanSubject')?.value || null;
        
        // 模拟进度更新
        const progressInterval = setInterval(() => {
            const currentProgress = parseFloat(document.getElementById('aiPlanProgressBar')?.style.width) || 0;
            if (currentProgress < 90) {
                updateProgress(currentProgress + Math.random() * 10, getProgressText(currentProgress));
            }
        }, 500);
        
        // 调用 API
        const res = await DashboardAPI.generateAIPlan(
            Array.from(selectedDatasets),
            sampleCount,
            subjectId ? parseInt(subjectId) : null
        );
        
        clearInterval(progressInterval);
        
        if (res.success) {
            updateProgress(100, '生成完成');
            generatedPlan = res.data;
            
            // 延迟跳转到预览步骤
            setTimeout(() => {
                goToStep(3);
                renderPlanPreview(generatedPlan);
            }, 500);
        } else {
            throw new Error(res.error || '生成失败');
        }
        
    } catch (error) {
        console.error('[AIPlan] 生成失败:', error);
        showToast('生成测试计划失败: ' + error.message, 'error');
        goToStep(1);
    } finally {
        isGenerating = false;
    }
}

/**
 * 更新进度条
 * @param {number} percent - 百分比
 * @param {string} text - 进度文本
 */
function updateProgress(percent, text) {
    const bar = document.getElementById('aiPlanProgressBar');
    const textEl = document.getElementById('aiPlanProgressText');
    const percentEl = document.getElementById('aiPlanProgressPercent');
    
    if (bar) bar.style.width = percent + '%';
    if (textEl) textEl.textContent = text;
    if (percentEl) percentEl.textContent = Math.round(percent) + '%';
}

/**
 * 获取进度文本
 * @param {number} progress - 当前进度
 * @returns {string}
 */
function getProgressText(progress) {
    if (progress < 20) return '正在分析数据集...';
    if (progress < 40) return '正在识别题型分布...';
    if (progress < 60) return '正在生成测试目标...';
    if (progress < 80) return '正在制定验收标准...';
    return '正在整理计划内容...';
}

// ========== 预览和编辑 ==========

/**
 * 渲染计划预览
 * @param {Object} plan - 生成的计划
 */
function renderPlanPreview(plan) {
    // 计划名称
    const nameInput = document.getElementById('aiPlanNameInput');
    if (nameInput) nameInput.value = plan.name || '';
    
    // 计划描述
    const descInput = document.getElementById('aiPlanDescInput');
    if (descInput) descInput.value = plan.description || '';
    
    // 测试目标
    const objectivesList = document.getElementById('aiPlanObjectivesList');
    if (objectivesList && plan.objectives) {
        objectivesList.innerHTML = plan.objectives.map((obj, i) => `
            <li class="objective-item">
                <span class="objective-number">${i + 1}</span>
                <input type="text" class="objective-input" value="${escapeHtml(obj)}" data-index="${i}">
                <button class="objective-remove" onclick="removeObjective(${i})">
                    <svg viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            </li>
        `).join('');
    }
    
    // 测试步骤
    const stepsList = document.getElementById('aiPlanStepsList');
    if (stepsList && plan.steps) {
        stepsList.innerHTML = plan.steps.map((step, i) => `
            <li class="step-item">
                <span class="step-number">${i + 1}</span>
                <input type="text" class="step-input" value="${escapeHtml(step)}" data-index="${i}">
            </li>
        `).join('');
    }
    
    // 预期时长
    const durationEl = document.getElementById('aiPlanDurationValue');
    if (durationEl) durationEl.textContent = plan.expected_duration || '--';
    
    // 验收标准
    const criteriaList = document.getElementById('aiPlanCriteriaList');
    if (criteriaList && plan.acceptance_criteria) {
        criteriaList.innerHTML = plan.acceptance_criteria.map((c, i) => `
            <li class="criteria-item">
                <svg viewBox="0 0 24 24" width="16" height="16">
                    <path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                </svg>
                <input type="text" class="criteria-input" value="${escapeHtml(c)}" data-index="${i}">
            </li>
        `).join('');
    }
}

/**
 * 返回上一步
 */
export function backToAIPlanForm() {
    if (currentStep > 1) {
        goToStep(currentStep - 1);
    }
}

/**
 * 重新生成
 */
export function regenerateAIPlan() {
    goToStep(1);
}


// ========== 保存计划 ==========

/**
 * 保存 AI 生成的计划
 */
export async function saveAIPlan() {
    // 收集编辑后的数据
    const name = document.getElementById('aiPlanNameInput')?.value?.trim();
    const description = document.getElementById('aiPlanDescInput')?.value?.trim();
    
    if (!name) {
        showToast('请输入计划名称', 'warning');
        return;
    }
    
    // 收集目标
    const objectives = [];
    document.querySelectorAll('.objective-input').forEach(input => {
        const value = input.value.trim();
        if (value) objectives.push(value);
    });
    
    // 收集步骤
    const steps = [];
    document.querySelectorAll('.step-input').forEach(input => {
        const value = input.value.trim();
        if (value) steps.push(value);
    });
    
    // 收集验收标准
    const criteria = [];
    document.querySelectorAll('.criteria-input').forEach(input => {
        const value = input.value.trim();
        if (value) criteria.push(value);
    });
    
    const saveBtn = document.getElementById('aiPlanSaveBtn');
    if (saveBtn) {
        saveBtn.disabled = true;
        saveBtn.innerHTML = '<span class="btn-loading"></span> 保存中...';
    }
    
    try {
        const planData = {
            name,
            description,
            ai_generated: true,
            dataset_ids: Array.from(selectedDatasets),
            objectives,
            steps,
            acceptance_criteria: criteria,
            expected_duration: generatedPlan?.expected_duration
        };
        
        const res = await DashboardAPI.createPlan(planData);
        
        if (res.success) {
            showToast('测试计划创建成功', 'success');
            goToStep(4);
            
            // 显示成功信息
            renderSuccessStep(res.data);
            
            // 刷新计划列表
            if (window.loadTestPlans) {
                window.loadTestPlans();
            }
        } else {
            throw new Error(res.error || '保存失败');
        }
        
    } catch (error) {
        console.error('[AIPlan] 保存失败:', error);
        showToast('保存失败: ' + error.message, 'error');
    } finally {
        if (saveBtn) {
            saveBtn.disabled = false;
            saveBtn.innerHTML = '保存计划';
        }
    }
}

/**
 * 渲染成功步骤
 * @param {Object} plan - 创建的计划
 */
function renderSuccessStep(plan) {
    const container = document.getElementById('aiPlanStep4');
    if (!container) return;
    
    container.innerHTML = `
        <div class="ai-plan-success">
            <div class="success-icon">
                <svg viewBox="0 0 24 24" width="64" height="64">
                    <path fill="#10b981" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
            </div>
            <h3 class="success-title">测试计划创建成功</h3>
            <p class="success-desc">计划「${escapeHtml(plan.name)}」已创建，可在计划列表中查看</p>
            <div class="success-actions">
                <button class="btn btn-secondary" onclick="closeAIPlanModal()">关闭</button>
                <button class="btn btn-primary" onclick="viewPlanDetail('${plan.plan_id}')">查看详情</button>
            </div>
        </div>
    `;
}

/**
 * 查看计划详情
 * @param {string} planId - 计划ID
 */
export function viewPlanDetail(planId) {
    closeAIPlanModal();
    // 触发计划详情展开
    if (window.expandPlanCard) {
        window.expandPlanCard(planId);
    }
}

// ========== 导出 ==========

export default {
    initAIPlanModule,
    openAIPlanModal,
    closeAIPlanModal,
    onAIPlanModalBackdropClick,
    generateAIPlan,
    backToAIPlanForm,
    regenerateAIPlan,
    saveAIPlan,
    viewPlanDetail
};
