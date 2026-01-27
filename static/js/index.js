/**
 * 测试计划看板 - 主入口文件（模块化版本）
 * @description 模块化架构，导入各功能模块并初始化
 * 更新日志 2026-01-24: 优化数据加载，删除冗余代码
 */

// ========== 模块导入 ==========
import { DashboardAPI, clearCache } from './modules/dashboard-api.js';
import {
    SUBJECT_MAP, SUBJECT_COLORS, STATUS_MAP,
    formatDateTime, formatTime, formatNumber,
    escapeHtml, showToast, toggleSkeleton, debounce,
    navigateTo, toggleSidebar, restoreSidebarState
} from './modules/dashboard-utils.js';
import { LineChart, animateNumber } from './modules/dashboard-charts.js';
import { exportSubjectReport } from './modules/dashboard-subjects.js';
import {
    initAIPlanModule, openAIPlanModal, closeAIPlanModal, onAIPlanModalBackdropClick,
    generateAIPlan, backToAIPlanForm, saveAIPlan
} from './modules/dashboard-ai-plan.js';

// ========== 全局状态 ==========
let dashboardData = { overview: null, plans: [], datasets: null };
let currentPlanStatus = 'all';
let currentTaskRange = 'today';
let pieChart = null;

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', () => {
    initDashboard();
    setupEventListeners();
    restoreSidebarState();
});

/**
 * 初始化看板
 */
async function initDashboard() {
    showAllSkeletons();
    await loadDashboard();
    initAIPlanModule();
}

/**
 * 设置事件监听器
 */
function setupEventListeners() {
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
        searchInput.addEventListener('input', debounce((e) => performSearch(e.target.value), 300));
        document.addEventListener('keydown', (e) => {
            if (e.key === '/' && document.activeElement.tagName !== 'INPUT') {
                e.preventDefault();
                searchInput.focus();
            }
        });
        document.addEventListener('click', (e) => {
            if (!e.target.closest('.search-box')) {
                document.getElementById('searchResults').style.display = 'none';
            }
        });
    }
}

/**
 * 显示所有骨架屏
 */
function showAllSkeletons() {
    ['dataset', 'task', 'question', 'accuracy'].forEach(id => {
        toggleSkeleton(`${id}Skeleton`, `${id}Content`, true);
    });
    toggleSkeleton('planListSkeleton', 'planListContent', true);
    toggleSkeleton('subjectSkeleton', 'subjectContent', true);
}

// ========== 数据加载 ==========

/**
 * 加载看板所有数据 - 优化版：并行加载，统一数据源
 */
async function loadDashboard() {
    try {
        // 并行加载核心数据
        const [overviewRes, datasetsRes, plansRes] = await Promise.all([
            DashboardAPI.getOverview(currentTaskRange),
            DashboardAPI.getDatasets(),
            DashboardAPI.getPlans(currentPlanStatus)
        ]);
        
        // 处理概览数据
        if (overviewRes.success) {
            dashboardData.overview = overviewRes.data;
        }
        
        // 处理数据集数据 - 统一数据源
        if (datasetsRes.success) {
            dashboardData.datasets = datasetsRes.data;
        }
        
        // 渲染统计卡片（合并数据源）
        renderStatCards(dashboardData.overview, dashboardData.datasets);
        
        // 渲染数据集概览
        if (dashboardData.datasets) {
            renderDatasetOverview(dashboardData.datasets);
        }
        
        // 处理测试计划
        if (plansRes.success) {
            dashboardData.plans = plansRes.data?.items || plansRes.data || [];
            renderPlanList(dashboardData.plans);
        }
        toggleSkeleton('planListSkeleton', 'planListContent', false);
        
        // 独立加载学科分析（从批量评估任务获取）
        loadSubjectAnalysis();
        
        // 加载热点图、日报、趋势分析（以评估数据为底座）
        loadHeatmap();
        loadDailyReports();
        loadTrends();
        
        updateSyncTime();
        
    } catch (error) {
        console.error('[Dashboard] 加载数据失败:', error);
        showToast('数据加载失败，请稍后重试', 'error');
    }
}

/**
 * 刷新看板数据
 */
async function refreshDashboard() {
    const btn = document.getElementById('refreshBtn');
    btn.disabled = true;
    btn.classList.add('loading');
    
    try {
        clearCache();
        const syncRes = await DashboardAPI.sync();
        if (!syncRes.success) throw new Error(syncRes.error || '同步失败');
        
        await loadDashboard();
        showToast('数据刷新成功', 'success');
    } catch (error) {
        console.error('[Dashboard] 刷新失败:', error);
        showToast('刷新失败，请稍后重试', 'error');
    } finally {
        btn.disabled = false;
        btn.classList.remove('loading');
    }
}

/**
 * 更新同步时间
 */
function updateSyncTime() {
    const el = document.getElementById('lastSyncTime');
    if (el) el.textContent = formatDateTime(new Date());
}

// ========== 统计卡片渲染 ==========

/**
 * 渲染统计卡片 - 合并数据源确保一致性
 * 更新：错误率卡片移到第一位，数据集卡片移到最后并优化显示
 */
function renderStatCards(overview, datasets) {
    // 隐藏骨架屏 - 更新ID列表
    ['errorRate', 'task', 'question', 'dataset'].forEach(id => {
        toggleSkeleton(`${id}Skeleton`, `${id}Content`, false);
    });
    
    // 1. 整体错误率（第一位）
    const errorRateEl = document.getElementById('errorRateValue');
    const errorTrendEl = document.getElementById('errorRateTrend');
    const errorCompareEl = document.getElementById('errorRateCompare');
    const errorSourceEl = document.getElementById('errorRateSource');
    
    if (errorRateEl && overview?.accuracy) {
        // 错误率 = 100% - 准确率
        const accuracy = overview.accuracy.current || 0;
        const errorRate = (1 - accuracy) * 100;
        animateNumber(errorRateEl, errorRate, { duration: 800, decimals: 1, suffix: '%' });
        
        // 趋势箭头逻辑反转：错误率下降为好（绿色），上升为差（红色）
        if (errorTrendEl) {
            errorTrendEl.className = 'trend-arrow';
            // 注意：trend 是准确率的趋势，错误率趋势相反
            if (overview.accuracy.trend === 'up') errorTrendEl.classList.add('down'); // 准确率上升 = 错误率下降
            else if (overview.accuracy.trend === 'down') errorTrendEl.classList.add('up'); // 准确率下降 = 错误率上升
        }
        
        // 与昨日对比
        if (errorCompareEl && overview.accuracy.yesterday !== undefined) {
            const yesterdayErrorRate = (1 - overview.accuracy.yesterday) * 100;
            const diff = (errorRate - yesterdayErrorRate).toFixed(1);
            const sign = diff >= 0 ? '+' : '';
            errorCompareEl.textContent = `与昨日对比 ${sign}${diff}%`;
        } else if (errorCompareEl && overview.accuracy.previous !== undefined) {
            // 兼容旧数据：使用 previous（上周）
            const prevErrorRate = (1 - overview.accuracy.previous) * 100;
            const diff = (errorRate - prevErrorRate).toFixed(1);
            const sign = diff >= 0 ? '+' : '';
            errorCompareEl.textContent = `与昨日对比 ${sign}${diff}%`;
        }
        
        // 显示数据来源：错误题数/总题数
        if (errorSourceEl) {
            const correct = overview.accuracy.correct_count || 0;
            const tested = overview.questions?.tested || 0;
            const errorCount = tested - correct;
            errorSourceEl.textContent = `${formatNumber(errorCount)}/${formatNumber(tested)} 题`;
        }
    }
    
    // 2. 任务数
    const taskEl = document.getElementById('taskTotal');
    if (taskEl && overview?.tasks) {
        animateNumber(taskEl, overview.tasks[currentTaskRange] || overview.tasks.today || 0, { duration: 800 });
    }
    
    // 3. 题目数 - 从 datasets 聚合
    const questionEl = document.getElementById('questionTotal');
    const questionDetail = document.getElementById('questionDetail');
    const datasetList = datasets?.datasets || [];
    const totalQuestions = datasetList.reduce((sum, ds) => sum + (ds.question_count || 0), 0);
    
    if (questionEl) {
        const tested = overview?.questions?.tested || totalQuestions;
        animateNumber(questionEl, tested, { duration: 800 });
        if (questionDetail) {
            questionDetail.textContent = `已测试 ${formatNumber(tested)} / 总计 ${formatNumber(overview?.questions?.total || totalQuestions)}`;
        }
    }
    
    // 4. 数据集总数（最后一位，优化显示）
    const datasetTotal = datasets?.total || overview?.datasets?.total || 0;
    const datasetEl = document.getElementById('datasetTotal');
    const datasetBySubjectEl = document.getElementById('datasetBySubject');
    const datasetWeekNewEl = document.getElementById('datasetWeekNew');
    
    if (datasetEl) {
        animateNumber(datasetEl, datasetTotal, { duration: 800 });
    }
    
    // 显示学科分布摘要（取前3个学科）
    if (datasetBySubjectEl && datasets?.by_subject) {
        const bySubject = datasets.by_subject;
        const subjectEntries = Object.entries(bySubject)
            .map(([id, count]) => ({ id, count, name: SUBJECT_MAP[id] || '未知' }))
            .sort((a, b) => b.count - a.count)
            .slice(0, 3);
        
        if (subjectEntries.length > 0) {
            datasetBySubjectEl.textContent = subjectEntries
                .map(s => `${s.name} ${s.count}`)
                .join(' · ');
        } else {
            datasetBySubjectEl.textContent = '--';
        }
    }
    
    // 显示本周新增数量
    if (datasetWeekNewEl) {
        const weekNew = datasets?.week_new || overview?.datasets?.week_new || 0;
        datasetWeekNewEl.textContent = weekNew > 0 ? `本周新增 ${weekNew}` : '';
    }
}

/**
 * 切换任务时间范围
 */
function switchTaskRange(range) {
    currentTaskRange = range;
    document.querySelectorAll('.time-filter').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.range === range);
    });
    
    DashboardAPI.getOverview(range).then(res => {
        if (res.success) {
            dashboardData.overview = res.data;
            const taskTotal = document.getElementById('taskTotal');
            if (taskTotal && res.data.tasks) {
                taskTotal.textContent = res.data.tasks[range] || 0;
            }
        }
    });
}

// ========== 测试计划列表 ==========

/**
 * 加载测试计划列表
 */
async function loadTestPlans() {
    toggleSkeleton('planListSkeleton', 'planListContent', true);
    
    try {
        const res = await DashboardAPI.getPlans(currentPlanStatus);
        if (res.success) {
            const plans = res.data?.items || res.data || [];
            dashboardData.plans = plans;
            renderPlanList(plans);
        }
    } catch (error) {
        console.error('[Dashboard] 加载计划失败:', error);
    }
    
    toggleSkeleton('planListSkeleton', 'planListContent', false);
}

/**
 * 渲染计划列表
 */
function renderPlanList(plans) {
    const container = document.getElementById('planListContent');
    if (!container) return;
    
    if (!plans || plans.length === 0) {
        container.innerHTML = `
            <div class="empty-state">
                <div class="empty-state-icon">
                    <svg viewBox="0 0 24 24" width="48" height="48">
                        <path fill="#86868b" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l4.59-4.58L18 11l-6 6z"/>
                    </svg>
                </div>
                <div class="empty-state-text">暂无测试计划</div>
                <div class="empty-state-hint">点击「新建计划」或「AI生成计划」创建</div>
            </div>
        `;
        return;
    }
    
    container.innerHTML = plans.map(plan => {
        const statusClass = plan.status || 'draft';
        const statusText = STATUS_MAP[plan.status] || '草稿';
        const progress = plan.progress || 0;
        // 处理 subject_ids 数组，取第一个学科显示
        const subjectIds = plan.subject_ids || [];
        const subjectName = subjectIds.length > 0 ? SUBJECT_MAP[subjectIds[0]] || '--' : '--';
        
        return `
            <div class="plan-card" data-id="${plan.plan_id}" onclick="togglePlanCard(this)">
                <div class="plan-card-header">
                    <div class="plan-card-info">
                        <div class="plan-card-name">${escapeHtml(plan.name || '未命名计划')}</div>
                        <div class="plan-card-meta">
                            <span>${subjectName}</span>
                            <span>${plan.target_count || 0}题</span>
                            <span>${formatTime(plan.created_at)}</span>
                        </div>
                    </div>
                    <span class="status-tag ${statusClass}">${statusText}</span>
                </div>
                <div class="plan-card-body">
                    <div class="plan-progress">
                        <div style="display:flex;justify-content:space-between;font-size:12px;color:var(--text-muted);">
                            <span>执行进度</span>
                            <span>${progress}%</span>
                        </div>
                        <div class="progress-bar-container">
                            <div class="progress-bar" style="width:${progress}%"></div>
                        </div>
                    </div>
                    <div class="plan-actions">
                        <button class="btn btn-sm btn-secondary" onclick="event.stopPropagation();viewPlanDetail('${plan.plan_id}')">查看详情</button>
                        ${plan.status === 'draft' ? `<button class="btn btn-sm btn-primary" onclick="event.stopPropagation();executePlan('${plan.plan_id}')">开始执行</button>` : ''}
                        <button class="btn btn-sm btn-danger" onclick="event.stopPropagation();deletePlan('${plan.plan_id}', '${escapeHtml(plan.name || '')}')">删除</button>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 切换计划卡片展开状态
 */
function togglePlanCard(card) {
    const wasExpanded = card.classList.contains('expanded');
    document.querySelectorAll('.plan-card.expanded').forEach(c => c.classList.remove('expanded'));
    if (!wasExpanded) card.classList.add('expanded');
}

/**
 * 筛选计划
 */
function filterPlans() {
    currentPlanStatus = document.getElementById('planStatusFilter')?.value || 'all';
    loadTestPlans();
}

/**
 * 查看计划详情 - 打开工作流详情弹窗
 */
async function viewPlanDetail(planId) {
    await openWorkflowDetailModal(planId);
}

/**
 * 执行计划 - 执行工作流并显示进度
 */
async function executePlan(planId) {
    try {
        showToast('正在执行...', 'info');
        const res = await DashboardAPI.executePlan(planId);
        if (res.success) {
            const data = res.data;
            // 显示执行结果
            if (data.can_proceed === false) {
                showToast(data.next_action || '等待中...', 'warning');
            } else {
                showToast('执行成功', 'success');
            }
            // 刷新计划列表
            loadTestPlans();
            // 如果工作流弹窗已打开，刷新它
            if (currentWorkflowPlanId === planId) {
                await refreshWorkflowDetail();
            }
        } else {
            throw new Error(res.error || '执行失败');
        }
    } catch (error) {
        showToast('执行失败: ' + error.message, 'error');
    }
}

// ========== 工作流详情弹窗 ==========
let currentWorkflowPlanId = null;
let currentWorkflowData = null;

/**
 * 打开工作流详情弹窗
 */
async function openWorkflowDetailModal(planId) {
    currentWorkflowPlanId = planId;
    const modal = document.getElementById('workflowNodeModal');
    const titleEl = document.getElementById('workflowNodeTitle');
    const contentEl = document.getElementById('workflowNodeContent');
    const footerEl = document.getElementById('workflowNodeFooter');
    
    if (!modal) return;
    
    // 显示加载状态
    titleEl.textContent = '加载中...';
    contentEl.innerHTML = '<div class="loading-spinner"></div>';
    footerEl.innerHTML = '<button class="btn btn-secondary" onclick="closeWorkflowNodeModal()">关闭</button>';
    modal.style.display = 'flex';
    
    try {
        // 获取计划详情
        const res = await DashboardAPI.getPlan(planId);
        if (!res.success) throw new Error(res.error || '获取计划失败');
        
        currentWorkflowData = res.data;
        renderWorkflowDetail(res.data);
    } catch (error) {
        contentEl.innerHTML = `<div class="error-message">加载失败: ${error.message}</div>`;
    }
}

/**
 * 渲染工作流详情 - 简约高级版
 */
function renderWorkflowDetail(plan) {
    const titleEl = document.getElementById('workflowNodeTitle');
    const contentEl = document.getElementById('workflowNodeContent');
    const footerEl = document.getElementById('workflowNodeFooter');
    
    titleEl.textContent = plan.name || '测试计划';
    
    const workflow = plan.workflow_status || {};
    const datasetStatus = workflow.dataset || {};
    const matchStatus = workflow.homework_match || {};
    const evalStatus = workflow.evaluation || {};
    const reportStatus = workflow.report || {};
    
    // 计算整体进度
    let completedSteps = 0;
    if (datasetStatus.status === 'completed') completedSteps++;
    if (matchStatus.status === 'completed') completedSteps++;
    if (evalStatus.status === 'completed') completedSteps++;
    if (reportStatus.status === 'completed') completedSteps++;
    const progressPercent = Math.round(completedSteps / 4 * 100);
    
    // 获取步骤状态class
    const getStepClass = (status) => {
        if (status === 'completed') return 'completed';
        if (status === 'in_progress') return 'in_progress';
        if (status === 'failed') return 'failed';
        return '';
    };
    
    contentEl.innerHTML = `
        <div class="workflow-detail">
            <!-- 顶部信息 - 横向紧凑 -->
            <div class="workflow-info">
                <div class="info-row">
                    <span class="info-label">关键字</span>
                    <span class="info-value">${plan.task_keyword || '-'}</span>
                </div>
                <div class="info-row">
                    <span class="info-label">目标</span>
                    <span class="info-value">${plan.target_count || 0} 题</span>
                </div>
            </div>
            
            <!-- 进度条 -->
            <div class="workflow-progress">
                <div class="progress-header">
                    <span>执行进度</span>
                    <span>${progressPercent}%</span>
                </div>
                <div class="progress-bar-container">
                    <div class="progress-bar" style="width:${progressPercent}%"></div>
                </div>
            </div>
            
            <!-- 步骤时间线 -->
            <div class="workflow-steps">
                <!-- 步骤1: 数据集 -->
                <div class="workflow-step ${getStepClass(datasetStatus.status)}">
                    <div class="step-header">
                        <span class="step-title">数据集配置</span>
                        <button class="step-action-btn" onclick="openDatasetSelector('${plan.plan_id}')">
                            ${datasetStatus.dataset_name ? '更换' : '选择'}
                        </button>
                    </div>
                    <div class="step-content">
                        ${datasetStatus.dataset_name 
                            ? `<div class="step-info">${datasetStatus.dataset_name}<br>${datasetStatus.question_count || 0} 题</div>`
                            : '<div class="step-info warning">请选择数据集</div>'
                        }
                    </div>
                </div>
                
                <!-- 步骤2: 作业匹配 -->
                <div class="workflow-step ${getStepClass(matchStatus.status)}">
                    <div class="step-header">
                        <span class="step-title">作业匹配</span>
                    </div>
                    <div class="step-content">
                        ${matchStatus.matched_publish && matchStatus.matched_publish.length > 0
                            ? `<div class="step-info">
                                ${matchStatus.matched_publish.length} 个发布 · ${matchStatus.total_homework || 0} 份作业
                               </div>
                               <div class="grading-progress">
                                   批改 ${matchStatus.grading_progress || 0}% (${matchStatus.total_graded || 0}/${matchStatus.total_homework || 0})
                               </div>`
                            : '<div class="step-info">等待匹配</div>'
                        }
                    </div>
                </div>
                
                <!-- 步骤3: 批量评估 -->
                <div class="workflow-step ${getStepClass(evalStatus.status)}">
                    <div class="step-header">
                        <span class="step-title">批量评估</span>
                    </div>
                    <div class="step-content">
                        ${evalStatus.task_id
                            ? `<div class="step-info">
                                ${evalStatus.accuracy !== null ? `准确率 ${(evalStatus.accuracy * 100).toFixed(1)}%` : '评估中...'}
                               </div>`
                            : '<div class="step-info">等待执行</div>'
                        }
                    </div>
                </div>
                
                <!-- 步骤4: 测试报告 -->
                <div class="workflow-step ${getStepClass(reportStatus.status)}">
                    <div class="step-header">
                        <span class="step-title">测试报告</span>
                    </div>
                    <div class="step-content">
                        ${reportStatus.report_id
                            ? '<div class="step-info">报告已生成</div>'
                            : '<div class="step-info">等待生成</div>'
                        }
                    </div>
                </div>
            </div>
        </div>
    `;
    
    // 底部按钮
    const canExecute = plan.status === 'draft' || plan.status === 'active';
    const hasTask = evalStatus.task_id;
    
    footerEl.innerHTML = `
        <button class="btn btn-secondary" onclick="closeWorkflowNodeModal()">关闭</button>
        <button class="btn btn-secondary" onclick="refreshWorkflowDetail()">刷新状态</button>
        ${canExecute ? `<button class="btn btn-primary" onclick="executePlan('${plan.plan_id}')">执行下一步</button>` : ''}
        ${hasTask ? `<button class="btn btn-secondary" onclick="navigateTo('/batch-evaluation?task_id=${evalStatus.task_id}')">查看评估任务</button>` : ''}
    `;
}

/**
 * 刷新工作流详情
 */
async function refreshWorkflowDetail() {
    if (!currentWorkflowPlanId) return;
    await openWorkflowDetailModal(currentWorkflowPlanId);
}

/**
 * 关闭工作流详情弹窗
 */
function closeWorkflowNodeModal() {
    const modal = document.getElementById('workflowNodeModal');
    if (modal) modal.style.display = 'none';
    currentWorkflowPlanId = null;
    currentWorkflowData = null;
}

/**
 * 工作流弹窗背景点击
 */
function onWorkflowNodeModalBackdropClick(event) {
    if (event.target.id === 'workflowNodeModal') {
        closeWorkflowNodeModal();
    }
}

// ========== 数据集选择器 ==========

/**
 * 打开数据集选择器
 */
async function openDatasetSelector(planId) {
    const contentEl = document.getElementById('workflowNodeContent');
    if (!contentEl) return;
    
    // 保存当前内容以便取消时恢复
    const originalContent = contentEl.innerHTML;
    
    // 显示加载状态
    contentEl.innerHTML = `
        <div class="dataset-selector">
            <div class="selector-header">
                <h4>选择数据集</h4>
                <button class="btn btn-sm btn-secondary" onclick="refreshWorkflowDetail()">取消</button>
            </div>
            <div class="selector-loading">
                <div class="loading-spinner"></div>
                <span>加载数据集列表...</span>
            </div>
        </div>
    `;
    
    try {
        // 获取数据集列表
        const res = await DashboardAPI.getDatasets();
        if (!res.success) throw new Error(res.error || '获取数据集失败');
        
        const datasets = res.data?.datasets || [];
        
        if (datasets.length === 0) {
            contentEl.innerHTML = `
                <div class="dataset-selector">
                    <div class="selector-header">
                        <h4>选择数据集</h4>
                        <button class="btn btn-sm btn-secondary" onclick="refreshWorkflowDetail()">返回</button>
                    </div>
                    <div class="selector-empty">
                        <p>暂无可用数据集</p>
                        <p class="hint">请先在数据集管理页面创建数据集</p>
                        <button class="btn btn-primary" onclick="navigateTo('/dataset-manage')">前往创建</button>
                    </div>
                </div>
            `;
            return;
        }
        
        // 渲染数据集列表
        const datasetListHtml = datasets.map(ds => `
            <div class="dataset-item" onclick="selectDatasetForPlan('${planId}', '${ds.dataset_id}')">
                <div class="dataset-item-main">
                    <span class="dataset-name">${escapeHtml(ds.name || '未命名')}</span>
                    <span class="dataset-book">${escapeHtml(ds.book_name || '')}</span>
                </div>
                <div class="dataset-item-meta">
                    <span class="dataset-subject">${SUBJECT_MAP[ds.subject_id] || '未知学科'}</span>
                    <span class="dataset-count">${ds.question_count || 0} 题</span>
                </div>
            </div>
        `).join('');
        
        contentEl.innerHTML = `
            <div class="dataset-selector">
                <div class="selector-header">
                    <h4>选择数据集</h4>
                    <button class="btn btn-sm btn-secondary" onclick="refreshWorkflowDetail()">取消</button>
                </div>
                <div class="selector-list">
                    ${datasetListHtml}
                </div>
            </div>
        `;
        
    } catch (error) {
        contentEl.innerHTML = `
            <div class="dataset-selector">
                <div class="selector-header">
                    <h4>选择数据集</h4>
                    <button class="btn btn-sm btn-secondary" onclick="refreshWorkflowDetail()">返回</button>
                </div>
                <div class="selector-error">
                    <p>加载失败: ${error.message}</p>
                    <button class="btn btn-secondary" onclick="openDatasetSelector('${planId}')">重试</button>
                </div>
            </div>
        `;
    }
}

/**
 * 为测试计划选择数据集
 */
async function selectDatasetForPlan(planId, datasetId) {
    try {
        showToast('正在设置数据集...', 'info');
        
        const res = await fetch(`/api/test-plans/${planId}/update-dataset`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ dataset_id: datasetId })
        });
        
        const data = await res.json();
        
        if (data.success) {
            showToast(`已选择数据集: ${data.data.dataset_name}`, 'success');
            // 刷新工作流详情
            await refreshWorkflowDetail();
        } else {
            throw new Error(data.error || '设置失败');
        }
    } catch (error) {
        showToast('设置数据集失败: ' + error.message, 'error');
    }
}

/**
 * 删除测试计划
 */
async function deletePlan(planId, planName) {
    if (!confirm(`确定要删除测试计划「${planName || planId}」吗？此操作不可恢复。`)) {
        return;
    }
    
    try {
        const res = await DashboardAPI.deletePlan(planId);
        if (res.success) {
            showToast('测试计划已删除', 'success');
            loadTestPlans();
        } else {
            throw new Error(res.error || '删除失败');
        }
    } catch (error) {
        showToast('删除失败: ' + error.message, 'error');
    }
}

// ========== 创建计划弹窗 ==========

function openCreatePlanModal() {
    const modal = document.getElementById('createPlanModal');
    if (modal) {
        modal.style.display = 'flex';
        document.getElementById('createPlanName').value = '';
        document.getElementById('createPlanDescription').value = '';
        document.getElementById('createPlanKeyword').value = '';
        const matchPreview = document.getElementById('matchPreviewContainer');
        if (matchPreview) matchPreview.style.display = 'none';
    }
}

function closeCreatePlanModal() {
    const modal = document.getElementById('createPlanModal');
    if (modal) modal.style.display = 'none';
}

function onCreatePlanModalBackdropClick(event) {
    if (event.target.id === 'createPlanModal') closeCreatePlanModal();
}

async function previewKeywordMatch() {
    const keyword = document.getElementById('createPlanKeyword')?.value?.trim();
    const subjectId = document.getElementById('createPlanSubject')?.value;
    const matchType = document.getElementById('createPlanMatchType')?.value || 'fuzzy';
    
    if (!keyword) {
        showToast('请输入任务关键字', 'warning');
        return;
    }
    
    if (!subjectId) {
        showToast('请先选择目标学科', 'warning');
        return;
    }
    
    const btn = document.getElementById('previewMatchBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> 查询中...';
    }
    
    try {
        const res = await DashboardAPI.previewMatch(keyword, {
            subject_id: parseInt(subjectId),
            match_type: matchType
        });
        
        if (res.success && res.data) {
            const container = document.getElementById('matchPreviewContainer');
            const list = document.getElementById('matchPreviewList');
            const count = document.getElementById('matchPreviewCount');
            const statsContainer = document.getElementById('matchPreviewStats');
            
            const data = res.data;
            const matches = data.matches || [];
            
            // 更新统计信息
            count.textContent = `${data.matched_count || 0} 条匹配`;
            
            // 更新统计数据
            const totalHomeworkEl = document.getElementById('matchTotalHomework');
            const totalGradedEl = document.getElementById('matchTotalGraded');
            const gradingProgressEl = document.getElementById('matchGradingProgress');
            
            if (totalHomeworkEl) totalHomeworkEl.textContent = data.total_homework || 0;
            if (totalGradedEl) totalGradedEl.textContent = data.total_graded || 0;
            if (gradingProgressEl) {
                const progress = data.total_homework > 0 
                    ? Math.round(data.total_graded / data.total_homework * 100) 
                    : 0;
                gradingProgressEl.textContent = `${progress}%`;
            }
            
            if (statsContainer) statsContainer.style.display = 'flex';
            
            if (matches.length === 0) {
                list.innerHTML = '<div class="match-preview-empty">未找到匹配的作业发布</div>';
            } else {
                // 渲染匹配结果，显示完成状态
                list.innerHTML = matches.slice(0, 15).map(m => {
                    const statusClass = m.is_completed ? 'completed' : 'pending';
                    const statusText = m.is_completed ? '已完成' : '批改中';
                    const statusIcon = m.is_completed 
                        ? '<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>'
                        : '<svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M12 4V1L8 5l4 4V6c3.31 0 6 2.69 6 6 0 1.01-.25 1.97-.7 2.8l1.46 1.46C19.54 15.03 20 13.57 20 12c0-4.42-3.58-8-8-8zm0 14c-3.31 0-6-2.69-6-6 0-1.01.25-1.97.7-2.8L5.24 7.74C4.46 8.97 4 10.43 4 12c0 4.42 3.58 8 8 8v3l4-4-4-4v3z"/></svg>';
                    
                    return `
                        <div class="match-preview-item ${statusClass}">
                            <div class="match-item-main">
                                <span class="match-item-content">${escapeHtml(m.content || '')}</span>
                                <span class="match-item-book">${escapeHtml(m.book_name || '')}</span>
                            </div>
                            <div class="match-item-meta">
                                <span class="match-item-homework">${m.total_homework || 0}份作业</span>
                                <span class="match-item-status ${statusClass}">${statusIcon} ${statusText}</span>
                            </div>
                        </div>
                    `;
                }).join('');
                
                // 显示完成状态摘要
                const completedCount = data.completed_count || 0;
                const allCompleted = data.all_completed || false;
                
                if (allCompleted) {
                    list.innerHTML += `
                        <div class="match-preview-summary success">
                            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/></svg>
                            全部 ${matches.length} 个任务已完成批改，可以创建评估任务
                        </div>
                    `;
                } else {
                    list.innerHTML += `
                        <div class="match-preview-summary warning">
                            <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                            ${completedCount}/${matches.length} 个任务已完成，等待全部完成后可创建评估任务
                        </div>
                    `;
                }
            }
            
            container.style.display = 'block';
        } else {
            showToast(res.error || '查询失败', 'error');
        }
    } catch (error) {
        console.error('[PreviewMatch] 预览失败:', error);
        showToast('预览失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="14" height="14"><path fill="currentColor" d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                预览匹配
            `;
        }
    }
}

async function createTestPlan() {
    const name = document.getElementById('createPlanName')?.value?.trim();
    const description = document.getElementById('createPlanDescription')?.value?.trim();
    const subjectId = document.getElementById('createPlanSubject')?.value;
    const targetCount = parseInt(document.getElementById('createPlanTarget')?.value) || 30;
    const keyword = document.getElementById('createPlanKeyword')?.value?.trim();
    
    if (!name) {
        showToast('请输入计划名称', 'warning');
        return;
    }
    
    if (!keyword) {
        showToast('请输入任务关键字', 'warning');
        return;
    }
    
    try {
        const res = await DashboardAPI.createPlan({
            name,
            description,
            subject_ids: subjectId ? [parseInt(subjectId)] : [],
            target_count: targetCount,
            task_keyword: keyword
        });
        
        if (res.success) {
            showToast('测试计划创建成功', 'success');
            closeCreatePlanModal();
            loadTestPlans();
        } else {
            throw new Error(res.error || '创建失败');
        }
    } catch (error) {
        showToast('创建失败: ' + error.message, 'error');
    }
}

/**
 * 检查并合并作业创建批量评估任务
 * 检查匹配的 publish 是否全部完成（status=2），完成后自动合并创建批量评估任务
 */
async function checkAndMergeHomework() {
    const keyword = document.getElementById('createPlanKeyword')?.value?.trim();
    const subjectId = document.getElementById('createPlanSubject')?.value;
    const matchType = document.getElementById('createPlanMatchType')?.value || 'fuzzy';
    
    if (!keyword) {
        showToast('请输入任务关键字', 'warning');
        return;
    }
    
    if (!subjectId) {
        showToast('请先选择目标学科', 'warning');
        return;
    }
    
    const btn = document.getElementById('autoMergeBtn');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="loading-spinner"></span> 检查中...';
    }
    
    try {
        const res = await DashboardAPI.checkAndMerge(keyword, parseInt(subjectId), {
            match_type: matchType,
            auto_match_dataset: true,
            force_create: false
        });
        
        if (res.success && res.data) {
            const data = res.data;
            
            if (data.status === 'no_match') {
                showToast('未找到匹配的作业发布', 'warning');
            } else if (data.status === 'waiting') {
                // 未全部完成，显示等待状态
                showToast(`等待批改完成：${data.completed_count}/${data.matched_count} 个任务已完成`, 'info');
                
                // 更新预览区域显示
                const container = document.getElementById('matchPreviewContainer');
                const list = document.getElementById('matchPreviewList');
                
                if (container && list) {
                    // 添加等待提示
                    const existingSummary = list.querySelector('.match-preview-summary');
                    if (existingSummary) {
                        existingSummary.outerHTML = `
                            <div class="match-preview-summary warning">
                                <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg>
                                ${data.completed_count}/${data.matched_count} 个任务已完成，等待全部完成后可创建评估任务
                            </div>
                        `;
                    }
                    container.style.display = 'block';
                }
            } else if (data.status === 'completed') {
                // 全部完成，任务已创建
                showToast(`批量评估任务已创建：${data.task_name}`, 'success');
                
                // 关闭弹窗并跳转到批量评估页面
                closeCreatePlanModal();
                
                // 跳转到批量评估页面查看新创建的任务
                setTimeout(() => {
                    navigateTo(`/batch-evaluation?task_id=${data.task_id}`);
                }, 500);
            }
        } else {
            showToast(res.error || '操作失败', 'error');
        }
    } catch (error) {
        console.error('[CheckAndMerge] 操作失败:', error);
        showToast('操作失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = `
                <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M17 3H7c-1.1 0-2 .9-2 2v16l7-3 7 3V5c0-1.1-.9-2-2-2z"/></svg>
                自动合并创建任务
            `;
        }
    }
}

// ========== 搜索功能 ==========

async function performSearch(query) {
    const resultsEl = document.getElementById('searchResults');
    if (!query || query.length < 2) {
        resultsEl.style.display = 'none';
        return;
    }
    
    try {
        const res = await DashboardAPI.search(query);
        if (res.success) {
            renderSearchResults(res.data || {});
        }
    } catch (error) {
        console.error('[Search] 搜索失败:', error);
    }
}

function renderSearchResults(data) {
    const resultsEl = document.getElementById('searchResults');
    const tasks = data.tasks || [];
    const datasets = data.datasets || [];
    
    if (tasks.length === 0 && datasets.length === 0) {
        resultsEl.innerHTML = '<div class="empty-text">未找到匹配结果</div>';
        resultsEl.style.display = 'block';
        return;
    }
    
    let html = '';
    
    if (tasks.length > 0) {
        html += '<div class="search-group-title" style="padding:8px 12px;font-size:11px;color:var(--text-muted);font-weight:600;">任务</div>';
        html += tasks.slice(0, 5).map(t => `
            <div class="search-result-item" onclick="navigateTo('/batch-evaluation?task_id=${t.task_id}')">
                <div style="font-size:13px;color:var(--text-primary);">${escapeHtml(t.name || t.task_id)}</div>
                <div style="font-size:11px;color:var(--text-muted);">${formatTime(t.created_at)}</div>
            </div>
        `).join('');
    }
    
    if (datasets.length > 0) {
        html += '<div class="search-group-title" style="padding:8px 12px;font-size:11px;color:var(--text-muted);font-weight:600;">数据集</div>';
        html += datasets.slice(0, 5).map(d => `
            <div class="search-result-item" onclick="navigateTo('/dataset-manage?dataset_id=${d.dataset_id}')">
                <div style="font-size:13px;color:var(--text-primary);">${escapeHtml(d.name)}</div>
                <div style="font-size:11px;color:var(--text-muted);">${SUBJECT_MAP[d.subject_id] || '--'} · ${d.question_count || 0}题</div>
            </div>
        `).join('');
    }
    
    resultsEl.innerHTML = html;
    resultsEl.style.display = 'block';
}

// ========== 数据集概览渲染 ==========

/**
 * 渲染数据集概览 - 内联实现，不依赖外部模块
 */
function renderDatasetOverview(data) {
    const datasets = data?.datasets || [];
    const bySubject = data?.by_subject || {};
    
    // 渲染统计卡片
    const totalEl = document.getElementById('datasetTotalValue');
    if (totalEl) animateNumber(totalEl, data?.total || 0, { duration: 800 });
    
    const questionEl = document.getElementById('datasetQuestionValue');
    if (questionEl) {
        const total = datasets.reduce((sum, ds) => sum + (ds.question_count || 0), 0);
        animateNumber(questionEl, total, { duration: 800 });
    }
    
    const accuracyEl = document.getElementById('datasetAccuracyValue');
    if (accuracyEl) {
        const valid = datasets.filter(ds => ds.history_accuracy != null);
        const avg = valid.length > 0 
            ? valid.reduce((sum, ds) => sum + ds.history_accuracy, 0) / valid.length * 100 
            : 0;
        animateNumber(accuracyEl, avg, { duration: 800, decimals: 1, suffix: '%' });
    }
    
    const usageEl = document.getElementById('datasetUsageValue');
    if (usageEl) {
        const usage = datasets.reduce((sum, ds) => sum + (ds.week_usage || 0), 0);
        animateNumber(usageEl, usage, { duration: 800 });
    }
    
    // 渲染学科分布饼图
    renderSubjectPieChart(bySubject);
    
    // 渲染最近数据集列表
    renderRecentDatasets(datasets);
}

/**
 * 渲染学科分布饼图 - 使用 Chart.js 动态饼图
 */
function renderSubjectPieChart(distribution) {
    const canvas = document.getElementById('datasetPieChart');
    if (!canvas) return;
    
    const entries = Object.entries(distribution).filter(([, count]) => count > 0);
    const total = entries.reduce((sum, [, count]) => sum + count, 0);
    
    // 销毁旧图表
    if (pieChart) {
        pieChart.destroy();
        pieChart = null;
    }
    
    if (total === 0) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.font = '14px -apple-system, sans-serif';
        ctx.fillStyle = '#86868b';
        ctx.textAlign = 'center';
        ctx.fillText('暂无数据', canvas.width / 2, canvas.height / 2);
        return;
    }
    
    const labels = entries.map(([subjectId]) => SUBJECT_MAP[subjectId] || '未知');
    const data = entries.map(([, count]) => count);
    const colors = entries.map(([subjectId]) => SUBJECT_COLORS[subjectId] || '#d1d5db');
    
    pieChart = new Chart(canvas, {
        type: 'doughnut',
        data: {
            labels: labels,
            datasets: [{
                data: data,
                backgroundColor: colors,
                borderWidth: 2,
                borderColor: '#fff'
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            cutout: '60%',
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed || 0;
                            const percentage = ((value / total) * 100).toFixed(1);
                            return `${context.label}: ${value}个 (${percentage}%)`;
                        }
                    }
                }
            }
        },
        plugins: [{
            id: 'centerText',
            afterDraw: function(chart) {
                const ctx = chart.ctx;
                const centerX = (chart.chartArea.left + chart.chartArea.right) / 2;
                const centerY = (chart.chartArea.top + chart.chartArea.bottom) / 2;
                
                ctx.save();
                ctx.fillStyle = '#1d1d1f';
                ctx.font = 'bold 20px -apple-system, sans-serif';
                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillText(total.toString(), centerX, centerY - 8);
                
                ctx.font = '11px -apple-system, sans-serif';
                ctx.fillStyle = '#86868b';
                ctx.fillText('数据集', centerX, centerY + 12);
                ctx.restore();
            }
        }]
    });
    
    // 渲染图例 - 紧凑网格布局
    const legend = document.getElementById('datasetPieLegend');
    if (legend) {
        legend.innerHTML = entries.map(([subjectId, count]) => `
            <div class="legend-item-compact">
                <span class="legend-dot" style="background: ${SUBJECT_COLORS[subjectId] || '#d1d5db'}"></span>
                <span class="legend-text" title="${escapeHtml(SUBJECT_MAP[subjectId] || '未知')}">${escapeHtml(SUBJECT_MAP[subjectId] || '未知')}</span>
                <span class="legend-val">${count}</span>
            </div>
        `).join('');
    }
}

/**
 * 渲染最近数据集列表
 */
function renderRecentDatasets(datasets) {
    const container = document.getElementById('datasetRecentList');
    if (!container) return;

    if (!datasets || datasets.length === 0) {
        container.innerHTML = '<div class="empty-text" style="padding:10px;text-align:center;color:var(--text-muted);font-size:12px;">暂无数据集</div>';
        return;
    }

    // 按更新时间倒序排列取前5
    const sorted = [...datasets].sort((a, b) => {
        const t1 = new Date(b.updated_at || b.created_at || 0).getTime();
        const t2 = new Date(a.updated_at || a.created_at || 0).getTime();
        return t1 - t2;
    }).slice(0, 5);

    container.innerHTML = sorted.map(ds => {
        const date = formatDateTime(ds.updated_at || ds.created_at).split(' ')[0];
        const subject = SUBJECT_MAP[ds.subject_id] || '未知';
        
        return `
            <div class="recent-item" onclick="navigateTo('/dataset-manage?dataset_id=${ds.dataset_id}')">
                <div class="recent-info">
                    <div class="recent-name" title="${escapeHtml(ds.name)}">${escapeHtml(ds.name)}</div>
                    <div class="recent-meta">
                        <span>${subject}</span>
                        <span class="recent-meta-divider"></span>
                        <span>${ds.question_count || 0}题</span>
                        <span class="recent-meta-divider"></span>
                        <span>${date}</span>
                    </div>
                </div>
                <div class="recent-action">
                    <svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/></svg>
                </div>
            </div>
        `;
    }).join('');
}

// ========== 学科分析渲染 ==========

/**
 * 加载并渲染学科分析 - 从批量评估任务获取数据
 */
async function loadSubjectAnalysis() {
    toggleSkeleton('subjectSkeleton', 'subjectContent', true);
    
    try {
        const res = await DashboardAPI.getSubjects();
        if (res.success) {
            renderSubjectAnalysis(res.data || []);
        } else {
            console.error('[Subjects] 加载失败:', res.error);
        }
    } catch (error) {
        console.error('[Subjects] 加载失败:', error);
    }
    
    toggleSkeleton('subjectSkeleton', 'subjectContent', false);
}

/**
 * 渲染学科分析 - 显示批量评估任务中的学科统计
 * 更新：适配主区域布局，添加统计摘要
 */
function renderSubjectAnalysis(subjects) {
    const container = document.getElementById('subjectList');
    if (!container) return;
    
    if (!subjects || subjects.length === 0) {
        container.innerHTML = '<div class="empty-state-sm"><div class="empty-state-text">暂无评估数据，请先执行批量评估</div></div>';
        return;
    }
    
    // 更新统计摘要
    const totalCount = subjects.length;
    const totalTasks = subjects.reduce((sum, s) => sum + (s.task_count || 0), 0);
    const totalQuestions = subjects.reduce((sum, s) => sum + (s.question_count || 0), 0);
    const avgAccuracy = subjects.length > 0 
        ? subjects.reduce((sum, s) => sum + (s.accuracy || 0), 0) / subjects.length * 100 
        : 0;
    
    const summaryEls = {
        count: document.getElementById('subjectTotalCount'),
        tasks: document.getElementById('subjectTaskCount'),
        questions: document.getElementById('subjectQuestionCount'),
        accuracy: document.getElementById('subjectAvgAccuracy')
    };
    
    if (summaryEls.count) summaryEls.count.textContent = totalCount;
    if (summaryEls.tasks) summaryEls.tasks.textContent = formatNumber(totalTasks);
    if (summaryEls.questions) summaryEls.questions.textContent = formatNumber(totalQuestions);
    if (summaryEls.accuracy) summaryEls.accuracy.textContent = avgAccuracy.toFixed(1) + '%';
    
    // 渲染学科卡片列表
    container.innerHTML = subjects.map((s, index) => {
        const acc = s.accuracy != null ? (s.accuracy * 100) : 0;
        const color = SUBJECT_COLORS[s.subject_id] || SUBJECT_COLORS[index % SUBJECT_COLORS.length] || '#86868b';
        
        // 状态判定
        let statusClass = 'low';
        if (acc >= 80) statusClass = 'high';
        else if (acc >= 60) statusClass = 'medium';
        
        // 进度条颜色
        const progressColorClass = acc >= 80 ? '' : acc >= 60 ? 'warning' : 'danger';
        
        return `
            <div class="subject-item">
                <div class="subject-item-left">
                    <span class="subject-dot" style="background: ${color}"></span>
                    <span class="subject-name">${escapeHtml(s.subject_name)}</span>
                </div>
                <div class="subject-item-right">
                    <div class="subject-stats">
                        <span class="subject-stat-value">${s.task_count || 0}</span>
                        <span class="subject-stat-label">任务</span>
                    </div>
                    <div class="subject-stats">
                        <span class="subject-stat-value">${formatNumber(s.question_count || 0)}</span>
                        <span class="subject-stat-label">题目</span>
                    </div>
                    <div class="subject-score-badge ${statusClass}">
                        ${acc.toFixed(1)}%
                    </div>
                </div>
                <div class="subject-item-progress">
                    <div class="subject-item-progress-bar ${progressColorClass}" style="width: ${acc}%"></div>
                </div>
            </div>
        `;
    }).join('');
}

// ========== 高级设置折叠 ==========

function toggleAdvancedSettings() {
    const content = document.getElementById('advancedSettingsContent');
    const icon = document.getElementById('advancedSettingsIcon');
    if (content && icon) {
        const isHidden = content.style.display === 'none';
        content.style.display = isHidden ? 'block' : 'none';
        icon.style.transform = isHidden ? 'rotate(180deg)' : 'rotate(0deg)';
    }
}

// ========== 热点图 (US-11) ==========

let heatmapData = null;

/**
 * 加载热点图数据
 */
async function loadHeatmap() {
    const subjectId = document.getElementById('heatmapSubjectFilter')?.value || '';
    const days = document.getElementById('heatmapDaysFilter')?.value || '7';
    
    toggleSkeleton('heatmapSkeleton', 'heatmapContent', true);
    
    try {
        const res = await DashboardAPI.getHeatmap(subjectId, parseInt(days));
        if (res.success) {
            heatmapData = res.data;
            renderHeatmap(res.data);
            renderHeatmapSummary(res.data);
        } else {
            console.error('[Heatmap] 加载失败:', res.error);
            renderHeatmapEmpty('加载失败');
        }
    } catch (error) {
        console.error('[Heatmap] 加载失败:', error);
        renderHeatmapEmpty('加载失败');
    }
    
    toggleSkeleton('heatmapSkeleton', 'heatmapContent', false);
}

/**
 * 渲染热点图摘要
 */
function renderHeatmapSummary(data) {
    const summary = document.getElementById('heatmapSummary');
    if (!summary) return;
    
    const totalErrors = data?.total_errors || 0;
    const bookCount = data?.book_count || 0;
    const timeRange = data?.time_range || '--';
    
    document.getElementById('heatmapTotalErrors').textContent = formatNumber(totalErrors);
    document.getElementById('heatmapBookCount').textContent = bookCount;
    document.getElementById('heatmapTimeRange').textContent = timeRange;
    
    summary.style.display = totalErrors > 0 ? 'flex' : 'none';
}

/**
 * 渲染热点图
 */
function renderHeatmap(data) {
    const container = document.getElementById('heatmapContent');
    if (!container) return;
    
    const items = data?.items || [];
    
    if (items.length === 0) {
        renderHeatmapEmpty('暂无错误数据，请先执行批量评估');
        return;
    }
    
    // 按书本分组
    const grouped = {};
    items.forEach(item => {
        const bookName = item.book_name || '未知书本';
        if (!grouped[bookName]) grouped[bookName] = [];
        grouped[bookName].push(item);
    });
    
    container.innerHTML = Object.entries(grouped).map(([bookName, bookItems]) => {
        const sortedItems = bookItems.sort((a, b) => (b.error_count || 0) - (a.error_count || 0));
        
        return `
            <div class="heatmap-book-group">
                <div class="heatmap-book-title">${escapeHtml(bookName)}</div>
                <div class="heatmap-cells">
                    ${sortedItems.map(item => {
                        const count = item.error_count || 0;
                        const level = count >= 10 ? 'critical' : count >= 5 ? 'high' : count >= 2 ? 'medium' : 'low';
                        const pageInfo = item.page_num ? `P${item.page_num}` : '';
                        const questionInfo = item.question_index ? `Q${item.question_index}` : '';
                        const label = [pageInfo, questionInfo].filter(Boolean).join('-') || '--';
                        
                        return `
                            <div class="heatmap-cell ${level}" 
                                 title="${escapeHtml(item.error_type || '错误')}: ${count}次"
                                 onclick="showHeatmapDetail('${item.id || ''}', '${escapeHtml(label)}', ${count})">
                                <span class="heatmap-cell-label">${label}</span>
                                <span class="heatmap-cell-count">${count}</span>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 渲染热点图空状态
 */
function renderHeatmapEmpty(message) {
    const container = document.getElementById('heatmapContent');
    if (container) {
        container.innerHTML = `<div class="empty-state-sm"><div class="empty-state-text">${escapeHtml(message)}</div></div>`;
    }
    const summary = document.getElementById('heatmapSummary');
    if (summary) summary.style.display = 'none';
}

/**
 * 筛选热点图
 */
function filterHeatmap() {
    loadHeatmap();
}

/**
 * 显示热点图详情
 */
async function showHeatmapDetail(itemId, label, count) {
    const modal = document.getElementById('heatmapDetailModal');
    if (!modal) return;
    
    document.getElementById('heatmapDetailTitle').textContent = label;
    document.getElementById('heatmapDetailBadge').textContent = `${count} 次错误`;
    document.getElementById('heatmapErrorList').innerHTML = '<div class="loading-text">加载中...</div>';
    
    modal.style.display = 'flex';
    
    // 如果有详情 API，可以调用获取更多信息
    // 这里简单显示基本信息
    document.getElementById('heatmapErrorList').innerHTML = `
        <div class="heatmap-error-item">
            <div class="heatmap-error-info">
                <span class="heatmap-error-label">错误次数</span>
                <span class="heatmap-error-value">${count}</span>
            </div>
        </div>
    `;
}

function closeHeatmapDetailModal() {
    const modal = document.getElementById('heatmapDetailModal');
    if (modal) modal.style.display = 'none';
}

function onHeatmapDetailModalBackdropClick(event) {
    if (event.target.id === 'heatmapDetailModal') closeHeatmapDetailModal();
}

// ========== 日报 (US-14) ==========

let reportsPage = 1;
let reportsTotalPages = 1;
let currentReportId = null;

/**
 * 加载日报列表
 */
async function loadDailyReports(page = 1) {
    toggleSkeleton('reportsListSkeleton', 'reportsListContent', true);
    
    try {
        const res = await DashboardAPI.getDailyReports(page, 10);
        if (res.success) {
            reportsPage = page;
            reportsTotalPages = res.data?.total_pages || 1;
            renderDailyReports(res.data?.items || []);
            updateReportsPagination();
        } else {
            console.error('[Reports] 加载失败:', res.error);
            renderDailyReportsEmpty('加载失败');
        }
    } catch (error) {
        console.error('[Reports] 加载失败:', error);
        renderDailyReportsEmpty('加载失败');
    }
    
    toggleSkeleton('reportsListSkeleton', 'reportsListContent', false);
}

/**
 * 渲染日报列表
 */
function renderDailyReports(reports) {
    const container = document.getElementById('reportsListContent');
    if (!container) return;
    
    if (!reports || reports.length === 0) {
        renderDailyReportsEmpty('暂无日报，点击「生成今日日报」创建');
        return;
    }
    
    container.innerHTML = reports.map(report => {
        const date = report.date || '--';
        const accuracy = report.accuracy != null ? (report.accuracy * 100).toFixed(1) + '%' : '--';
        const taskCount = report.task_count || 0;
        const status = report.status || 'completed';
        
        return `
            <div class="report-item" onclick="viewReportDetail('${report.report_id}')">
                <div class="report-item-left">
                    <div class="report-item-date">${escapeHtml(date)}</div>
                    <div class="report-item-meta">
                        <span>${taskCount} 个任务</span>
                        <span>准确率 ${accuracy}</span>
                    </div>
                </div>
                <div class="report-item-right">
                    <span class="status-tag ${status}">${status === 'completed' ? '已完成' : '生成中'}</span>
                    <svg class="report-item-arrow" viewBox="0 0 24 24" width="16" height="16">
                        <path fill="currentColor" d="M8.59 16.59L13.17 12 8.59 7.41 10 6l6 6-6 6-1.41-1.41z"/>
                    </svg>
                </div>
            </div>
        `;
    }).join('');
}

/**
 * 渲染日报空状态
 */
function renderDailyReportsEmpty(message) {
    const container = document.getElementById('reportsListContent');
    if (container) {
        container.innerHTML = `<div class="empty-state-sm"><div class="empty-state-text">${escapeHtml(message)}</div></div>`;
    }
}

/**
 * 更新日报分页
 */
function updateReportsPagination() {
    const pagination = document.getElementById('reportsPagination');
    const prevBtn = document.getElementById('reportsPrevBtn');
    const nextBtn = document.getElementById('reportsNextBtn');
    const info = document.getElementById('reportsPaginationInfo');
    
    if (pagination) {
        pagination.style.display = reportsTotalPages > 1 ? 'flex' : 'none';
    }
    if (prevBtn) prevBtn.disabled = reportsPage <= 1;
    if (nextBtn) nextBtn.disabled = reportsPage >= reportsTotalPages;
    if (info) info.textContent = `${reportsPage} / ${reportsTotalPages}`;
}

/**
 * 日报分页
 */
function loadReportsPage(direction) {
    if (direction === 'prev' && reportsPage > 1) {
        loadDailyReports(reportsPage - 1);
    } else if (direction === 'next' && reportsPage < reportsTotalPages) {
        loadDailyReports(reportsPage + 1);
    }
}

/**
 * 生成今日日报
 */
async function generateDailyReport() {
    const btn = document.querySelector('.reports-controls .btn-primary');
    if (btn) {
        btn.disabled = true;
        btn.innerHTML = '<span class="btn-loading"></span> 生成中...';
    }
    
    try {
        const res = await DashboardAPI.generateDailyReport();
        if (res.success) {
            showToast('日报生成成功', 'success');
            loadDailyReports();
        } else {
            throw new Error(res.error || '生成失败');
        }
    } catch (error) {
        console.error('[Reports] 生成失败:', error);
        showToast('生成失败: ' + error.message, 'error');
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerHTML = '<svg viewBox="0 0 24 24" width="16" height="16"><path fill="currentColor" d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/></svg><span>生成今日日报</span>';
        }
    }
}

/**
 * 查看日报详情
 */
async function viewReportDetail(reportId) {
    currentReportId = reportId;
    const modal = document.getElementById('reportDetailModal');
    if (!modal) return;
    
    modal.style.display = 'flex';
    
    try {
        const res = await DashboardAPI.getDailyReport(reportId);
        if (res.success) {
            renderReportDetail(res.data);
        } else {
            showToast('加载日报详情失败', 'error');
        }
    } catch (error) {
        console.error('[Reports] 加载详情失败:', error);
        showToast('加载失败', 'error');
    }
}

/**
 * 渲染日报详情
 */
function renderReportDetail(report) {
    document.getElementById('reportDetailDate').textContent = report.date || '--';
    document.getElementById('reportDetailBadge').textContent = report.status === 'completed' ? '已完成' : '生成中';
    document.getElementById('reportDetailSummary').textContent = report.ai_summary || '暂无AI总结';
    document.getElementById('reportDetailCompleted').textContent = report.completed_count || 0;
    document.getElementById('reportDetailPlanned').textContent = report.planned_count || 0;
    
    const accuracy = report.accuracy != null ? (report.accuracy * 100).toFixed(1) + '%' : '--';
    document.getElementById('reportDetailAccuracy').textContent = accuracy;
    
    const change = report.accuracy_change != null ? (report.accuracy_change * 100).toFixed(1) : null;
    const changeText = change != null ? (change >= 0 ? '+' + change + '%' : change + '%') : '--';
    document.getElementById('reportDetailChange').textContent = changeText;
    
    // 错误类型
    const errorsEl = document.getElementById('reportDetailErrors');
    const errors = report.top_errors || [];
    if (errorsEl) {
        errorsEl.innerHTML = errors.length > 0 
            ? errors.map(e => `<div class="report-error-item"><span>${escapeHtml(e.type)}</span><span>${e.count}次</span></div>`).join('')
            : '<div class="empty-text">暂无错误数据</div>';
    }
}

function closeReportDetailModal() {
    const modal = document.getElementById('reportDetailModal');
    if (modal) modal.style.display = 'none';
}

function onReportDetailModalBackdropClick(event) {
    if (event.target.id === 'reportDetailModal') closeReportDetailModal();
}

/**
 * 导出日报
 */
function exportDailyReport() {
    if (!currentReportId) return;
    window.open(DashboardAPI.exportDailyReport(currentReportId, 'docx'), '_blank');
}

// ========== 趋势分析 (US-15) ==========

let trendsChart = null;

/**
 * 加载趋势数据
 */
async function loadTrends() {
    const days = document.getElementById('trendsDaysFilter')?.value || '7';
    const subjectId = document.getElementById('trendsSubjectFilter')?.value || '';
    
    toggleSkeleton('trendsSkeleton', 'trendsContent', true);
    
    try {
        const trendsRes = await DashboardAPI.getTrends(parseInt(days), subjectId);
        
        if (trendsRes.success) {
            renderTrendsChart(trendsRes.data);
        } else {
            console.error('[Trends] 加载失败:', trendsRes.error);
            renderTrendsEmpty('加载失败');
        }
    } catch (error) {
        console.error('[Trends] 加载失败:', error);
        renderTrendsEmpty('加载失败');
    }
    
    toggleSkeleton('trendsSkeleton', 'trendsContent', false);
}

/**
 * 渲染趋势图
 */
function renderTrendsChart(data) {
    const canvas = document.getElementById('trendsCanvas');
    if (!canvas) return;
    
    const labels = data?.labels || [];
    const datasets = data?.datasets || [];
    
    if (labels.length === 0) {
        renderTrendsEmpty('暂无趋势数据，请先执行批量评估');
        return;
    }
    
    // 转换数据格式
    const chartDatasets = datasets.map((ds, i) => ({
        label: ds.label || `数据${i + 1}`,
        values: ds.data || [],
        color: SUBJECT_COLORS[ds.subject_id] || SUBJECT_COLORS[i] || '#5b8def'
    }));
    
    if (!trendsChart) {
        trendsChart = new LineChart(canvas, {
            duration: 1000,
            padding: { top: 20, right: 30, bottom: 40, left: 50 },
            showGrid: true,
            showDots: true,
            smooth: true
        });
    }
    
    trendsChart.setData(labels, chartDatasets);
}

/**
 * 渲染趋势空状态
 */
function renderTrendsEmpty(message) {
    const container = document.getElementById('trendsContent');
    if (container) {
        container.innerHTML = `<div class="empty-state-sm"><div class="empty-state-text">${escapeHtml(message)}</div></div>`;
    }
}

/**
 * 筛选趋势
 */
function filterTrends() {
    loadTrends();
}

/**
 * 导出趋势数据
 */
function exportTrends() {
    const days = document.getElementById('trendsDaysFilter')?.value || '30';
    window.open(DashboardAPI.exportTrends(parseInt(days)), '_blank');
}

// ========== 全局函数导出 ==========

// 导出到 window 供 HTML 调用
window.navigateTo = navigateTo;
window.toggleSidebar = toggleSidebar;
window.refreshDashboard = refreshDashboard;
window.filterPlans = filterPlans;
window.togglePlanCard = togglePlanCard;
window.viewPlanDetail = viewPlanDetail;
window.executePlan = executePlan;
window.deletePlan = deletePlan;
window.loadTestPlans = loadTestPlans;
window.switchTaskRange = switchTaskRange;

// 工作流详情弹窗
window.openWorkflowDetailModal = openWorkflowDetailModal;
window.closeWorkflowNodeModal = closeWorkflowNodeModal;
window.onWorkflowNodeModalBackdropClick = onWorkflowNodeModalBackdropClick;
window.refreshWorkflowDetail = refreshWorkflowDetail;
window.openDatasetSelector = openDatasetSelector;
window.selectDatasetForPlan = selectDatasetForPlan;

// 创建计划弹窗
window.openCreatePlanModal = openCreatePlanModal;
window.closeCreatePlanModal = closeCreatePlanModal;
window.onCreatePlanModalBackdropClick = onCreatePlanModalBackdropClick;
window.previewKeywordMatch = previewKeywordMatch;
window.createTestPlan = createTestPlan;
window.toggleAdvancedSettings = toggleAdvancedSettings;
window.checkAndMergeHomework = checkAndMergeHomework;

// AI 计划弹窗
window.openAIPlanModal = openAIPlanModal;
window.closeAIPlanModal = closeAIPlanModal;
window.onAIPlanModalBackdropClick = onAIPlanModalBackdropClick;
window.generateAIPlan = generateAIPlan;
window.backToAIPlanForm = backToAIPlanForm;
window.saveAIPlan = saveAIPlan;

// 学科分析
window.exportSubjectReport = exportSubjectReport;

// 搜索
window.performSearch = performSearch;

// 热点图
window.filterHeatmap = filterHeatmap;
window.showHeatmapDetail = showHeatmapDetail;
window.closeHeatmapDetailModal = closeHeatmapDetailModal;
window.onHeatmapDetailModalBackdropClick = onHeatmapDetailModalBackdropClick;

// 日报
window.generateDailyReport = generateDailyReport;
window.loadReportsPage = loadReportsPage;
window.viewReportDetail = viewReportDetail;
window.closeReportDetailModal = closeReportDetailModal;
window.onReportDetailModalBackdropClick = onReportDetailModalBackdropClick;
window.exportDailyReport = exportDailyReport;

// 趋势分析
window.filterTrends = filterTrends;
window.exportTrends = exportTrends;

// ========== 高级分析工具 ==========

// 高级工具状态
let advancedToolsData = {
    errorSamples: [],
    anomalies: [],
    clusters: [],
    suggestions: [],
    batchTasks: [],
    drilldownDimension: 'subject',
    drilldownParentId: null
};

/**
 * 加载高级工具统计数据
 */
async function loadAdvancedToolsStats() {
    try {
        const res = await fetch('/api/dashboard/advanced-tools/stats').then(r => r.json());
        
        if (res.success && res.data) {
            const data = res.data;
            
            // 更新错误样本徽章
            const errorBadge = document.getElementById('errorSampleCount');
            if (errorBadge) errorBadge.textContent = data.error_samples?.total || 0;
            
            // 更新异常徽章
            const anomalyBadge = document.getElementById('anomalyCount');
            if (anomalyBadge) {
                const count = data.anomalies?.unconfirmed || 0;
                anomalyBadge.textContent = count;
                if (count > 0) anomalyBadge.classList.add('warning');
            }
            
            // 更新聚类徽章
            const clusterBadge = document.getElementById('clusterCount');
            if (clusterBadge) clusterBadge.textContent = data.clusters?.total || 0;
            
            // 更新建议徽章
            const suggestionBadge = document.getElementById('suggestionCount');
            if (suggestionBadge) suggestionBadge.textContent = data.suggestions?.pending || 0;
        }
    } catch (e) {
        console.warn('[AdvancedTools] 加载统计失败:', e);
    }
}

// ========== 错误样本库弹窗 ==========
async function openErrorSamplesModal() {
    document.getElementById('errorSamplesModal').style.display = 'flex';
    await loadErrorSamples();
}

function closeErrorSamplesModal() {
    document.getElementById('errorSamplesModal').style.display = 'none';
}

function onErrorSamplesModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeErrorSamplesModal();
}

async function loadErrorSamples() {
    try {
        const res = await fetch('/api/dashboard/advanced-tools/stats').then(r => r.json());
        if (res.success && res.data) {
            const stats = res.data.error_samples;
            document.getElementById('errorSampleTotal').textContent = stats.total || 0;
            document.getElementById('errorSamplePending').textContent = stats.pending || 0;
            document.getElementById('errorSampleAnalyzed').textContent = stats.analyzed || 0;
            document.getElementById('errorSampleFixed').textContent = stats.fixed || 0;
        }
        
        // 加载样本列表（从批量评估任务中提取）
        const tasksRes = await fetch('/api/dashboard/tasks?page_size=50').then(r => r.json());
        if (tasksRes.success) {
            renderErrorSampleList(tasksRes.data?.tasks || []);
        }
    } catch (e) {
        console.error('[ErrorSamples] 加载失败:', e);
        showToast('加载错误样本失败', 'error');
    }
}

function renderErrorSampleList(tasks) {
    const container = document.getElementById('errorSampleList');
    if (!tasks.length) {
        container.innerHTML = '<div class="empty-state">暂无错误样本数据</div>';
        return;
    }
    
    // 从任务中提取有错误的样本
    let html = '';
    tasks.forEach(task => {
        if (task.accuracy < 1) {
            html += `
                <div class="sample-item" onclick="navigateTo('/batch-evaluation?task=${task.task_id}')">
                    <div class="sample-info">
                        <span class="sample-name">${escapeHtml(task.name)}</span>
                        <span class="sample-meta">${task.formatted_time || ''}</span>
                    </div>
                    <div class="sample-stats">
                        <span class="sample-accuracy ${task.accuracy < 0.8 ? 'low' : ''}">${(task.accuracy * 100).toFixed(1)}%</span>
                        <span class="sample-errors">${task.total_questions - task.correct_questions} 错误</span>
                    </div>
                </div>
            `;
        }
    });
    
    container.innerHTML = html || '<div class="empty-state">暂无错误样本数据</div>';
}

function filterErrorSamples() {
    loadErrorSamples();
}

// ========== 异常检测弹窗 ==========
async function openAnomalyModal() {
    document.getElementById('anomalyModal').style.display = 'flex';
    await loadAnomalies();
}

function closeAnomalyModal() {
    document.getElementById('anomalyModal').style.display = 'none';
}

function onAnomalyModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeAnomalyModal();
}

async function loadAnomalies() {
    try {
        const res = await fetch('/api/dashboard/advanced-tools/stats').then(r => r.json());
        if (res.success && res.data) {
            const stats = res.data.anomalies;
            document.getElementById('anomalyTotal').textContent = stats.total || 0;
            document.getElementById('anomalyUnconfirmed').textContent = stats.unconfirmed || 0;
            document.getElementById('anomalyToday').textContent = stats.today || 0;
            
            // 渲染异常列表
            const container = document.getElementById('anomalyList');
            if (stats.total === 0) {
                container.innerHTML = '<div class="empty-state">暂无异常记录</div>';
            } else {
                container.innerHTML = `
                    <div class="anomaly-item">
                        <div class="anomaly-icon warning">!</div>
                        <div class="anomaly-info">
                            <div class="anomaly-title">检测到 ${stats.total} 个评分异常</div>
                            <div class="anomaly-desc">其中 ${stats.unconfirmed} 个未确认，今日新增 ${stats.today} 个</div>
                        </div>
                    </div>
                `;
            }
        }
    } catch (e) {
        console.error('[Anomaly] 加载失败:', e);
        showToast('加载异常数据失败', 'error');
    }
}

// ========== 错误聚类弹窗 ==========
async function openClusteringModal() {
    document.getElementById('clusteringModal').style.display = 'flex';
    await loadClusters();
}

function closeClusteringModal() {
    document.getElementById('clusteringModal').style.display = 'none';
}

function onClusteringModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeClusteringModal();
}

async function loadClusters() {
    try {
        const res = await fetch('/api/dashboard/drilldown?dimension=question_type').then(r => r.json());
        const container = document.getElementById('clusterList');
        
        if (res.success && res.data?.items?.length) {
            let html = '';
            res.data.items.forEach(item => {
                html += `
                    <div class="cluster-item">
                        <div class="cluster-name">${escapeHtml(item.name)}</div>
                        <div class="cluster-count">${item.error_count} 个错误</div>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="empty-state">暂无聚类数据，请先进行批量评估</div>';
        }
    } catch (e) {
        console.error('[Clustering] 加载失败:', e);
        showToast('加载聚类数据失败', 'error');
    }
}

// ========== 优化建议弹窗 ==========
async function openOptimizationModal() {
    document.getElementById('optimizationModal').style.display = 'flex';
    await loadSuggestions();
}

function closeOptimizationModal() {
    document.getElementById('optimizationModal').style.display = 'none';
}

function onOptimizationModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeOptimizationModal();
}

async function loadSuggestions() {
    try {
        const res = await fetch('/api/dashboard/drilldown?dimension=question_type').then(r => r.json());
        const container = document.getElementById('suggestionList');
        
        if (res.success && res.data?.items?.length) {
            let html = '';
            res.data.items.slice(0, 5).forEach((item, idx) => {
                html += `
                    <div class="suggestion-item">
                        <div class="suggestion-priority ${idx === 0 ? 'high' : 'medium'}">P${idx + 1}</div>
                        <div class="suggestion-content">
                            <div class="suggestion-title">优化「${escapeHtml(item.name)}」类型错误</div>
                            <div class="suggestion-desc">当前有 ${item.error_count} 个此类错误，建议检查相关评分规则</div>
                        </div>
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="empty-state">暂无优化建议</div>';
        }
    } catch (e) {
        console.error('[Suggestions] 加载失败:', e);
        showToast('加载优化建议失败', 'error');
    }
}

// ========== 批次对比弹窗 ==========
async function openBatchCompareModal() {
    document.getElementById('batchCompareModal').style.display = 'flex';
    document.getElementById('compareResult').style.display = 'none';
    document.getElementById('compareEmpty').style.display = 'block';
    await loadBatchTasksForCompare();
}

function closeBatchCompareModal() {
    document.getElementById('batchCompareModal').style.display = 'none';
}

function onBatchCompareModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeBatchCompareModal();
}

async function loadBatchTasksForCompare() {
    try {
        const res = await fetch('/api/dashboard/batch-tasks').then(r => r.json());
        if (res.success) {
            advancedToolsData.batchTasks = res.data || [];
            const options = advancedToolsData.batchTasks.map(t => 
                `<option value="${t.task_id}">${escapeHtml(t.name)} (${(t.accuracy * 100).toFixed(1)}%)</option>`
            ).join('');
            
            document.getElementById('compareTaskA').innerHTML = '<option value="">选择批量评估任务</option>' + options;
            document.getElementById('compareTaskB').innerHTML = '<option value="">选择批量评估任务</option>' + options;
        }
    } catch (e) {
        console.error('[BatchCompare] 加载任务列表失败:', e);
    }
}

async function onCompareTaskChange() {
    const taskA = document.getElementById('compareTaskA').value;
    const taskB = document.getElementById('compareTaskB').value;
    
    if (!taskA || !taskB) {
        document.getElementById('compareResult').style.display = 'none';
        document.getElementById('compareEmpty').style.display = 'block';
        return;
    }
    
    if (taskA === taskB) {
        showToast('请选择不同的任务进行对比', 'warning');
        return;
    }
    
    try {
        const res = await fetch(`/api/dashboard/batch-compare?task_id_1=${taskA}&task_id_2=${taskB}`).then(r => r.json());
        if (res.success) {
            renderCompareResult(res.data);
        } else {
            showToast(res.error || '对比失败', 'error');
        }
    } catch (e) {
        console.error('[BatchCompare] 对比失败:', e);
        showToast('对比失败', 'error');
    }
}

function renderCompareResult(data) {
    document.getElementById('compareEmpty').style.display = 'none';
    document.getElementById('compareResult').style.display = 'block';
    
    // 准确率
    document.getElementById('compareAccA').textContent = (data.task1.accuracy * 100).toFixed(1) + '%';
    document.getElementById('compareAccB').textContent = (data.task2.accuracy * 100).toFixed(1) + '%';
    
    // 差值
    const diff = data.comparison.accuracy_diff;
    const diffEl = document.getElementById('compareDiffValue');
    const arrowEl = document.getElementById('compareDiffArrow');
    
    diffEl.textContent = (Math.abs(diff) * 100).toFixed(1) + '%';
    if (diff > 0) {
        arrowEl.textContent = '+';
        arrowEl.className = 'diff-arrow up';
    } else if (diff < 0) {
        arrowEl.textContent = '-';
        arrowEl.className = 'diff-arrow down';
    } else {
        arrowEl.textContent = '=';
        arrowEl.className = 'diff-arrow';
    }
    
    // 详情
    let detailsHtml = '<div class="compare-error-changes"><h4>错误类型变化</h4>';
    for (const [type, change] of Object.entries(data.comparison.error_changes || {})) {
        const changeClass = change < 0 ? 'improved' : change > 0 ? 'worsened' : '';
        const changeText = change > 0 ? `+${change}` : change.toString();
        detailsHtml += `
            <div class="error-change-item ${changeClass}">
                <span class="error-type">${escapeHtml(type)}</span>
                <span class="error-change">${changeText}</span>
            </div>
        `;
    }
    detailsHtml += '</div>';
    document.getElementById('compareDetails').innerHTML = detailsHtml;
}

// ========== 数据下钻弹窗 ==========
async function openDrilldownModal() {
    document.getElementById('drilldownModal').style.display = 'flex';
    advancedToolsData.drilldownDimension = 'subject';
    advancedToolsData.drilldownParentId = null;
    updateDrilldownNav();
    await loadDrilldownData();
}

function closeDrilldownModal() {
    document.getElementById('drilldownModal').style.display = 'none';
}

function onDrilldownModalBackdropClick(e) {
    if (e.target === e.currentTarget) closeDrilldownModal();
}

function switchDrilldownDimension(dimension) {
    advancedToolsData.drilldownDimension = dimension;
    advancedToolsData.drilldownParentId = null;
    updateDrilldownNav();
    loadDrilldownData();
}

function updateDrilldownNav() {
    document.querySelectorAll('.drilldown-nav-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.dimension === advancedToolsData.drilldownDimension);
    });
    document.getElementById('drilldownBreadcrumb').innerHTML = '<span class="breadcrumb-item active">全部</span>';
}

async function loadDrilldownData() {
    const container = document.getElementById('drilldownList');
    container.innerHTML = '<div class="empty-state">加载中...</div>';
    
    try {
        let url = `/api/dashboard/drilldown?dimension=${advancedToolsData.drilldownDimension}`;
        if (advancedToolsData.drilldownParentId) {
            url += `&parent_id=${advancedToolsData.drilldownParentId}`;
        }
        
        const res = await fetch(url).then(r => r.json());
        if (res.success && res.data?.items?.length) {
            let html = '';
            res.data.items.forEach(item => {
                const accClass = item.accuracy < 0.8 ? 'low' : item.accuracy < 0.9 ? 'medium' : 'high';
                html += `
                    <div class="drilldown-item" ${item.has_children ? `onclick="drilldownTo('${item.id}')"` : ''}>
                        <div class="drilldown-name">${escapeHtml(item.name)}</div>
                        <div class="drilldown-stats">
                            <span class="drilldown-accuracy ${accClass}">${(item.accuracy * 100).toFixed(1)}%</span>
                            <span class="drilldown-count">${item.total_questions} 题</span>
                            <span class="drilldown-errors">${item.error_count} 错误</span>
                        </div>
                        ${item.has_children ? '<span class="drilldown-arrow">></span>' : ''}
                    </div>
                `;
            });
            container.innerHTML = html;
        } else {
            container.innerHTML = '<div class="empty-state">暂无数据</div>';
        }
    } catch (e) {
        console.error('[Drilldown] 加载失败:', e);
        container.innerHTML = '<div class="empty-state">加载失败</div>';
    }
}

function drilldownTo(parentId) {
    advancedToolsData.drilldownParentId = parentId;
    
    // 更新面包屑
    const breadcrumb = document.getElementById('drilldownBreadcrumb');
    breadcrumb.innerHTML += ` > <span class="breadcrumb-item active">${escapeHtml(parentId)}</span>`;
    
    // 切换到下一级维度
    const dimensions = ['subject', 'book', 'page'];
    const currentIdx = dimensions.indexOf(advancedToolsData.drilldownDimension);
    if (currentIdx < dimensions.length - 1) {
        advancedToolsData.drilldownDimension = dimensions[currentIdx + 1];
    }
    
    loadDrilldownData();
}

// 最佳实践弹窗
function openBestPracticeModal() {
    showToast('最佳实践功能开发中...', 'info');
}

// 保存筛选弹窗
function openSavedFiltersModal() {
    showToast('保存筛选功能开发中...', 'info');
}

// 导出高级工具函数到 window
window.openErrorSamplesModal = openErrorSamplesModal;
window.closeErrorSamplesModal = closeErrorSamplesModal;
window.onErrorSamplesModalBackdropClick = onErrorSamplesModalBackdropClick;
window.filterErrorSamples = filterErrorSamples;

window.openAnomalyModal = openAnomalyModal;
window.closeAnomalyModal = closeAnomalyModal;
window.onAnomalyModalBackdropClick = onAnomalyModalBackdropClick;

window.openClusteringModal = openClusteringModal;
window.closeClusteringModal = closeClusteringModal;
window.onClusteringModalBackdropClick = onClusteringModalBackdropClick;

window.openOptimizationModal = openOptimizationModal;
window.closeOptimizationModal = closeOptimizationModal;
window.onOptimizationModalBackdropClick = onOptimizationModalBackdropClick;

window.openBatchCompareModal = openBatchCompareModal;
window.closeBatchCompareModal = closeBatchCompareModal;
window.onBatchCompareModalBackdropClick = onBatchCompareModalBackdropClick;
window.onCompareTaskChange = onCompareTaskChange;

window.openDrilldownModal = openDrilldownModal;
window.closeDrilldownModal = closeDrilldownModal;
window.onDrilldownModalBackdropClick = onDrilldownModalBackdropClick;
window.switchDrilldownDimension = switchDrilldownDimension;
window.drilldownTo = drilldownTo;

window.openBestPracticeModal = openBestPracticeModal;
window.openSavedFiltersModal = openSavedFiltersModal;

// ========== AI 分析报告 ==========
let currentAnalysisTaskId = null;

function openAnalysisReportModal(taskId) {
    currentAnalysisTaskId = taskId;
    document.getElementById('analysisReportModal').style.display = 'flex';
    document.getElementById('analysisReportStatus').style.display = 'flex';
    document.getElementById('analysisReportContent').style.display = 'none';
    loadAnalysisReport(taskId);
}

function closeAnalysisReportModal() {
    document.getElementById('analysisReportModal').style.display = 'none';
    currentAnalysisTaskId = null;
}

function onAnalysisReportModalBackdropClick(event) {
    if (event.target.id === 'analysisReportModal') {
        closeAnalysisReportModal();
    }
}

async function loadAnalysisReport(taskId) {
    try {
        const response = await fetch(`/api/analysis/report/${taskId}`);
        const data = await response.json();
        
        if (!data.success) {
            showAnalysisError(data.error || '加载失败');
            return;
        }
        
        if (!data.report) {
            document.getElementById('analysisReportStatus').innerHTML = `
                <div class="empty-state">
                    <p>暂无分析报告</p>
                    <button class="btn btn-primary" onclick="triggerAnalysis()">开始分析</button>
                </div>
            `;
            return;
        }
        
        renderAnalysisReport(data.report);
    } catch (error) {
        console.error('加载分析报告失败:', error);
        showAnalysisError('网络错误');
    }
}

function showAnalysisError(message) {
    document.getElementById('analysisReportStatus').innerHTML = `
        <div class="error-state">
            <p>${message}</p>
            <button class="btn btn-secondary" onclick="loadAnalysisReport(currentAnalysisTaskId)">重试</button>
        </div>
    `;
}

function renderAnalysisReport(report) {
    document.getElementById('analysisReportStatus').style.display = 'none';
    document.getElementById('analysisReportContent').style.display = 'block';
    
    const summary = report.summary || {};
    document.getElementById('summaryTotalErrors').textContent = summary.total_errors || 0;
    document.getElementById('summaryErrorRate').textContent = ((summary.error_rate || 0) * 100).toFixed(1) + '%';
    document.getElementById('summaryFocusCount').textContent = summary.focus_count || 0;
    
    // 渲染层级分析
    renderDrilldownData(report.drill_down_data);
    
    // 渲染错误模式
    renderErrorPatterns(report.error_patterns || []);
    
    // 渲染根因分析
    renderRootCauses(report.root_causes || []);
    
    // 渲染优化建议
    renderSuggestions(report.suggestions || []);
}

function renderDrilldownData(drillDownData) {
    const container = document.getElementById('analysisDrilldownContent');
    const bySubject = drillDownData?.by_subject || [];
    
    if (bySubject.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无数据</div>';
        return;
    }
    
    let html = '<div class="drilldown-list">';
    bySubject.forEach(item => {
        const isFocus = item.is_focus ? 'focus' : '';
        html += `
            <div class="drilldown-item ${isFocus}">
                <div class="item-name">${item.name || item.subject || '--'}</div>
                <div class="item-stats">
                    <span class="stat-error">${item.error_count || 0} 错误</span>
                    <span class="stat-rate">${((item.error_rate || 0) * 100).toFixed(1)}%</span>
                </div>
                ${item.is_focus ? '<span class="focus-tag">重点关注</span>' : ''}
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function switchAnalysisLevel(level) {
    document.querySelectorAll('.drilldown-tab').forEach(tab => {
        tab.classList.toggle('active', tab.dataset.level === level);
    });
    // TODO: 加载对应层级数据
}

function renderErrorPatterns(patterns) {
    const container = document.getElementById('analysisErrorPatterns');
    
    if (patterns.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无错误模式数据</div>';
        return;
    }
    
    let html = '';
    patterns.forEach(pattern => {
        const severityClass = pattern.severity === 'high' ? 'severity-high' : 
                             pattern.severity === 'medium' ? 'severity-medium' : 'severity-low';
        html += `
            <div class="pattern-card ${severityClass}">
                <div class="pattern-header">
                    <span class="pattern-type">${pattern.type || '--'}</span>
                    <span class="pattern-count">${pattern.count || 0} 次</span>
                </div>
                <div class="pattern-rate">${((pattern.rate || 0) * 100).toFixed(1)}%</div>
            </div>
        `;
    });
    container.innerHTML = html;
}

function renderRootCauses(causes) {
    const container = document.getElementById('analysisRootCauses');
    
    if (causes.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无根因分析数据</div>';
        return;
    }
    
    let html = '<div class="causes-list">';
    causes.forEach(cause => {
        const isPrimary = cause.is_primary ? 'primary' : '';
        html += `
            <div class="cause-item ${isPrimary}">
                <div class="cause-name">${cause.name || cause.type || '--'}</div>
                <div class="cause-stats">
                    <span class="cause-count">${cause.count || 0} 个</span>
                    <span class="cause-rate">${((cause.percentage || 0)).toFixed(1)}%</span>
                </div>
                ${cause.is_primary ? '<span class="primary-tag">主要问题</span>' : ''}
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

function renderSuggestions(suggestions) {
    const container = document.getElementById('analysisSuggestions');
    
    if (suggestions.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无优化建议</div>';
        return;
    }
    
    let html = '<div class="suggestions-list">';
    suggestions.forEach((suggestion, index) => {
        const priorityClass = suggestion.priority === 'high' ? 'priority-high' : 
                             suggestion.priority === 'medium' ? 'priority-medium' : 'priority-low';
        html += `
            <div class="suggestion-card ${priorityClass}">
                <div class="suggestion-header">
                    <span class="suggestion-index">${index + 1}</span>
                    <span class="suggestion-title">${suggestion.title || '--'}</span>
                    <span class="suggestion-priority">${suggestion.priority || 'low'}</span>
                </div>
                <div class="suggestion-desc">${suggestion.description || ''}</div>
                ${suggestion.expected_effect ? `<div class="suggestion-effect">预期效果: ${suggestion.expected_effect}</div>` : ''}
            </div>
        `;
    });
    html += '</div>';
    container.innerHTML = html;
}

async function triggerAnalysis() {
    if (!currentAnalysisTaskId) return;
    
    const btn = document.getElementById('triggerAnalysisBtn');
    btn.disabled = true;
    btn.textContent = '分析中...';
    
    try {
        const response = await fetch(`/api/analysis/trigger/${currentAnalysisTaskId}`, {
            method: 'POST'
        });
        const data = await response.json();
        
        if (data.success) {
            document.getElementById('analysisReportStatus').innerHTML = `
                <div class="loading-spinner"></div>
                <span>分析任务已加入队列，位置 ${data.position}</span>
            `;
            document.getElementById('analysisReportStatus').style.display = 'flex';
            document.getElementById('analysisReportContent').style.display = 'none';
            
            // 轮询检查状态
            pollAnalysisStatus();
        } else {
            alert(data.error || '触发分析失败');
        }
    } catch (error) {
        console.error('触发分析失败:', error);
        alert('网络错误');
    } finally {
        btn.disabled = false;
        btn.textContent = '重新分析';
    }
}

async function pollAnalysisStatus() {
    if (!currentAnalysisTaskId) return;
    
    try {
        const response = await fetch(`/api/analysis/status/${currentAnalysisTaskId}`);
        const data = await response.json();
        
        if (data.success && data.status) {
            if (data.status.status === 'completed') {
                loadAnalysisReport(currentAnalysisTaskId);
            } else if (data.status.status === 'failed') {
                showAnalysisError(data.status.message || '分析失败');
            } else {
                // 继续轮询
                setTimeout(pollAnalysisStatus, 3000);
            }
        }
    } catch (error) {
        console.error('检查分析状态失败:', error);
    }
}

// ========== 自动化管理 ==========
function openAutomationModal() {
    document.getElementById('automationModal').style.display = 'flex';
    loadAutomationTasks();
    loadQueueStatus();
}

function closeAutomationModal() {
    document.getElementById('automationModal').style.display = 'none';
}

function onAutomationModalBackdropClick(event) {
    if (event.target.id === 'automationModal') {
        closeAutomationModal();
    }
}

async function loadAutomationTasks() {
    const container = document.getElementById('automationTaskList');
    container.innerHTML = '<div class="loading">加载中...</div>';
    
    try {
        const response = await fetch('/api/automation/tasks');
        const data = await response.json();
        
        if (!data.success) {
            container.innerHTML = `<div class="error-state">${data.error || '加载失败'}</div>`;
            return;
        }
        
        renderAutomationTasks(data.tasks || []);
    } catch (error) {
        console.error('加载自动化任务失败:', error);
        container.innerHTML = '<div class="error-state">网络错误</div>';
    }
}

function renderAutomationTasks(tasks) {
    const container = document.getElementById('automationTaskList');
    
    if (tasks.length === 0) {
        container.innerHTML = '<div class="empty-state">暂无自动化任务</div>';
        return;
    }
    
    let html = '';
    tasks.forEach(task => {
        const statusClass = task.enabled ? 'enabled' : 'disabled';
        html += `
            <div class="automation-task-item ${statusClass}">
                <div class="task-info">
                    <span class="task-name">${task.name || task.task_type}</span>
                    <span class="task-desc">${task.description || ''}</span>
                </div>
                <div class="task-controls">
                    <label class="switch">
                        <input type="checkbox" ${task.enabled ? 'checked' : ''} 
                               onchange="toggleAutomationTask('${task.task_type}', this.checked)">
                        <span class="slider"></span>
                    </label>
                </div>
            </div>
        `;
    });
    container.innerHTML = html;
}

async function loadQueueStatus() {
    try {
        const response = await fetch('/api/automation/queue');
        const data = await response.json();
        
        if (data.success && data.queue) {
            document.getElementById('queueWaiting').textContent = data.queue.waiting || 0;
            document.getElementById('queueRunning').textContent = (data.queue.running || []).length;
            
            // 更新暂停/恢复按钮状态
            const isPaused = data.queue.paused;
            document.getElementById('pauseAllBtn').disabled = isPaused;
            document.getElementById('resumeAllBtn').disabled = !isPaused;
        }
    } catch (error) {
        console.error('加载队列状态失败:', error);
    }
}

async function toggleAutomationTask(taskType, enabled) {
    try {
        const response = await fetch(`/api/automation/tasks/${taskType}/config`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ enabled })
        });
        const data = await response.json();
        
        if (!data.success) {
            alert(data.error || '更新失败');
            loadAutomationTasks(); // 刷新
        }
    } catch (error) {
        console.error('更新任务配置失败:', error);
        alert('网络错误');
    }
}

async function pauseAllAutomation() {
    try {
        const response = await fetch('/api/automation/pause', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            loadQueueStatus();
        } else {
            alert(data.error || '暂停失败');
        }
    } catch (error) {
        console.error('暂停失败:', error);
        alert('网络错误');
    }
}

async function resumeAllAutomation() {
    try {
        const response = await fetch('/api/automation/resume', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            loadQueueStatus();
        } else {
            alert(data.error || '恢复失败');
        }
    } catch (error) {
        console.error('恢复失败:', error);
        alert('网络错误');
    }
}

async function clearAutomationQueue() {
    if (!confirm('确定要清空队列吗？')) return;
    
    try {
        const response = await fetch('/api/automation/queue/clear', { method: 'POST' });
        const data = await response.json();
        
        if (data.success) {
            loadQueueStatus();
        } else {
            alert(data.error || '清空失败');
        }
    } catch (error) {
        console.error('清空队列失败:', error);
        alert('网络错误');
    }
}

// 导出 AI 分析函数
window.openAnalysisReportModal = openAnalysisReportModal;
window.closeAnalysisReportModal = closeAnalysisReportModal;
window.onAnalysisReportModalBackdropClick = onAnalysisReportModalBackdropClick;
window.triggerAnalysis = triggerAnalysis;
window.switchAnalysisLevel = switchAnalysisLevel;

// 导出自动化管理函数
window.openAutomationModal = openAutomationModal;
window.closeAutomationModal = closeAutomationModal;
window.onAutomationModalBackdropClick = onAutomationModalBackdropClick;
window.pauseAllAutomation = pauseAllAutomation;
window.resumeAllAutomation = resumeAllAutomation;
window.clearAutomationQueue = clearAutomationQueue;

// ========== 优化日志功能 ==========
let optLogs = [];

// 加载优化日志（从API获取，与聊天页面共享）
async function loadOptLogs() {
    const logsList = document.getElementById('optLogsList');
    if (!logsList) return;
    
    try {
        const res = await fetch('/api/optimization-logs');
        if (res.ok) {
            optLogs = await res.json();
            renderOptLogs();
        } else {
            logsList.innerHTML = '<div class="opt-logs-empty">暂无日志</div>';
        }
    } catch (e) {
        console.error('加载优化日志失败:', e);
        logsList.innerHTML = '<div class="opt-logs-empty">加载失败</div>';
    }
}

// 渲染优化日志列表
function renderOptLogs() {
    const logsList = document.getElementById('optLogsList');
    if (!logsList) return;
    
    if (!optLogs || optLogs.length === 0) {
        logsList.innerHTML = '<div class="opt-logs-empty">暂无日志</div>';
        return;
    }
    
    logsList.innerHTML = optLogs.map(log => {
        const items = (log.content || '').split('\n').filter(s => s.trim());
        const itemsHtml = items.map((item, i) => 
            `<span class="log-item"><span class="log-num">${i + 1}.</span> ${escapeHtml(item)}</span>`
        ).join('');
        
        return `
            <div class="opt-log-item" data-category="${log.category || 'general'}" data-id="${log.id}">
                <div class="opt-log-header">
                    <span class="opt-log-date">${formatOptLogDate(log.created_at || log.date)}</span>
                </div>
                <div class="opt-log-content">${itemsHtml}</div>
                <button class="opt-log-delete" onclick="deleteOptLog(${log.id}, event)" title="删除">x</button>
            </div>
        `;
    }).join('');
}

// 格式化日期
function formatOptLogDate(dateStr) {
    if (!dateStr) return '';
    const date = new Date(dateStr);
    const month = String(date.getMonth() + 1).padStart(2, '0');
    const day = String(date.getDate()).padStart(2, '0');
    const hours = String(date.getHours()).padStart(2, '0');
    const minutes = String(date.getMinutes()).padStart(2, '0');
    return `${month}/${day} ${hours}:${minutes}`;
}

// 显示添加日志弹窗
function showAddOptLogModal() {
    document.getElementById('addOptLogModal').style.display = 'flex';
    document.getElementById('optLogContent').value = '';
    document.getElementById('optLogCategory').value = 'general';
    document.getElementById('optLogContent').focus();
}

// 关闭添加日志弹窗
function closeAddOptLogModal() {
    document.getElementById('addOptLogModal').style.display = 'none';
}

function onAddOptLogModalBackdropClick(event) {
    if (event.target.id === 'addOptLogModal') {
        closeAddOptLogModal();
    }
}

// 保存优化日志
async function saveOptLog() {
    const content = document.getElementById('optLogContent').value.trim();
    const category = document.getElementById('optLogCategory').value;
    
    if (!content) {
        showToast('请输入日志内容');
        return;
    }
    
    try {
        const res = await fetch('/api/optimization-logs', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ content, category })
        });
        
        if (res.ok) {
            closeAddOptLogModal();
            loadOptLogs();
            showToast('日志已添加');
        } else {
            const data = await res.json();
            showToast(data.error || '保存失败');
        }
    } catch (e) {
        console.error('保存日志失败:', e);
        showToast('保存失败');
    }
}

// 删除优化日志
async function deleteOptLog(id, event) {
    event.stopPropagation();
    
    try {
        const res = await fetch(`/api/optimization-logs/${id}`, {
            method: 'DELETE'
        });
        
        if (res.ok) {
            loadOptLogs();
        }
    } catch (e) {
        console.error('删除日志失败:', e);
    }
}

// 导出优化日志函数
window.showAddOptLogModal = showAddOptLogModal;
window.closeAddOptLogModal = closeAddOptLogModal;
window.onAddOptLogModalBackdropClick = onAddOptLogModalBackdropClick;
window.saveOptLog = saveOptLog;
window.deleteOptLog = deleteOptLog;

// 页面加载时加载优化日志
setTimeout(loadOptLogs, 500);

// ========== 全局设置弹窗 ==========
let globalSettings = {
    visionModel: 'doubao-seed-1-8-251228',
    textModel: 'deepseek-v3.2',
    notifyComplete: true,
    notifyError: true,
    refreshInterval: 60
};

function openGlobalSettingsModal() {
    document.getElementById('globalSettingsModal').style.display = 'flex';
    loadGlobalSettings();
}

function closeGlobalSettingsModal() {
    document.getElementById('globalSettingsModal').style.display = 'none';
}

function onGlobalSettingsModalBackdropClick(event) {
    if (event.target.id === 'globalSettingsModal') {
        closeGlobalSettingsModal();
    }
}

function loadGlobalSettings() {
    // 从 localStorage 加载设置
    const saved = localStorage.getItem('globalSettings');
    if (saved) {
        try {
            globalSettings = { ...globalSettings, ...JSON.parse(saved) };
        } catch (e) {}
    }
    
    // 更新 UI
    document.getElementById('settingsVisionModel').value = globalSettings.visionModel;
    document.getElementById('settingsTextModel').value = globalSettings.textModel;
    document.getElementById('settingsRefreshInterval').value = globalSettings.refreshInterval;
    
    document.getElementById('settingsNotifyComplete').classList.toggle('active', globalSettings.notifyComplete);
    document.getElementById('settingsNotifyError').classList.toggle('active', globalSettings.notifyError);
}

function toggleGlobalSetting(key) {
    const toggleKey = 'settings' + key.charAt(0).toUpperCase() + key.slice(1);
    const toggle = document.getElementById(toggleKey);
    toggle.classList.toggle('active');
    globalSettings[key] = toggle.classList.contains('active');
}

function saveGlobalSettings() {
    globalSettings.visionModel = document.getElementById('settingsVisionModel').value;
    globalSettings.textModel = document.getElementById('settingsTextModel').value;
    globalSettings.refreshInterval = parseInt(document.getElementById('settingsRefreshInterval').value);
    
    // 保存到 localStorage
    localStorage.setItem('globalSettings', JSON.stringify(globalSettings));
    
    closeGlobalSettingsModal();
    showToast('设置已保存');
}

// 导出全局设置函数
window.openGlobalSettingsModal = openGlobalSettingsModal;
window.closeGlobalSettingsModal = closeGlobalSettingsModal;
window.onGlobalSettingsModalBackdropClick = onGlobalSettingsModalBackdropClick;
window.toggleGlobalSetting = toggleGlobalSetting;
window.saveGlobalSettings = saveGlobalSettings;

// 页面加载后延迟加载高级工具统计
setTimeout(loadAdvancedToolsStats, 2000);

console.log('[Dashboard] 模块化看板初始化完成 v20260127');

// ========== RFID查询弹窗功能 ==========
let currentRfidData = null;

function openRfidQueryModal() {
    document.getElementById('rfidQueryModal').style.display = 'flex';
    document.getElementById('rfidInput').focus();
    // 重置状态
    document.getElementById('rfidResultSection').style.display = 'none';
    document.getElementById('rfidClassmatesSection').style.display = 'none';
    document.getElementById('rfidNotFound').style.display = 'none';
    document.getElementById('rfidLoading').style.display = 'none';
    document.getElementById('rfidEmptyState').style.display = 'flex';
}

function closeRfidQueryModal(event) {
    if (event && event.target !== event.currentTarget) return;
    document.getElementById('rfidQueryModal').style.display = 'none';
    document.getElementById('rfidInput').value = '';
    currentRfidData = null;
}

async function queryRFID() {
    const rfidInput = document.getElementById('rfidInput');
    const rfidNo = rfidInput.value.trim();
    
    if (!rfidNo) {
        showToast('请输入RFID卡号');
        rfidInput.focus();
        return;
    }
    
    // 显示加载状态
    document.getElementById('rfidEmptyState').style.display = 'none';
    document.getElementById('rfidResultSection').style.display = 'none';
    document.getElementById('rfidClassmatesSection').style.display = 'none';
    document.getElementById('rfidNotFound').style.display = 'none';
    document.getElementById('rfidLoading').style.display = 'flex';
    
    try {
        const response = await fetch(`/api/rfid/query?rfid_no=${encodeURIComponent(rfidNo)}`);
        const result = await response.json();
        
        document.getElementById('rfidLoading').style.display = 'none';
        
        if (!result.success) {
            showToast(result.error || '查询失败');
            document.getElementById('rfidEmptyState').style.display = 'flex';
            return;
        }
        
        if (!result.found) {
            document.getElementById('rfidNotFoundNo').textContent = rfidNo;
            document.getElementById('rfidNotFound').style.display = 'flex';
            return;
        }
        
        currentRfidData = result.data;
        renderRfidResult(result.data);
        
    } catch (error) {
        console.error('RFID query error:', error);
        document.getElementById('rfidLoading').style.display = 'none';
        document.getElementById('rfidEmptyState').style.display = 'flex';
        showToast('查询失败，请稍后重试');
    }
}

function renderRfidResult(data) {
    // 渲染基础信息
    renderRfidBasicInfo(data.basic_info);
    // 渲染绑定信息
    renderRfidBindInfo(data.bind_info);
    // 渲染学生信息
    renderRfidStudentInfo(data.student_info);
    // 渲染书本信息
    renderRfidBookInfo(data.book_info);
    // 渲染老师信息
    renderRfidTeacherInfo(data.teacher_info);
    
    document.getElementById('rfidResultSection').style.display = 'block';
}

function renderRfidBasicInfo(info) {
    const body = document.getElementById('rfidBasicInfo');
    const badge = document.getElementById('rfidStatusBadge');
    
    if (!info) {
        body.innerHTML = '<div class="rfid-no-data">未找到RFID基础信息</div>';
        badge.textContent = '';
        badge.className = 'rfid-status-badge';
        return;
    }
    
    badge.textContent = info.valid_status_text;
    badge.className = `rfid-status-badge ${info.valid_status === 1 ? 'valid' : 'invalid'}`;
    
    body.innerHTML = `
        <div class="rfid-info-row">
            <span class="rfid-info-label">RFID卡号</span>
            <span class="rfid-info-value highlight">${info.rfid_no}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">所属学校</span>
            <span class="rfid-info-value">${info.school_name || '--'}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">创建时间</span>
            <span class="rfid-info-value">${info.create_time || '--'}</span>
        </div>
    `;
}

function renderRfidBindInfo(info) {
    const body = document.getElementById('rfidBindInfo');
    const badge = document.getElementById('rfidTypeBadge');
    
    if (!info) {
        body.innerHTML = '<div class="rfid-no-data">该RFID卡未绑定</div>';
        badge.textContent = '';
        badge.className = 'rfid-type-badge';
        return;
    }
    
    badge.textContent = info.rfid_type_text;
    badge.className = `rfid-type-badge ${info.rfid_type === 'H' ? 'homework' : 'error-book'}`;
    
    body.innerHTML = `
        <div class="rfid-info-row">
            <span class="rfid-info-label">标签类型</span>
            <span class="rfid-info-value highlight">${info.rfid_type_text}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">学科</span>
            <span class="rfid-info-value">${info.subject_name}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">年级</span>
            <span class="rfid-info-value">${info.grade_name}</span>
        </div>
    `;
}

function renderRfidStudentInfo(info) {
    const body = document.getElementById('rfidStudentInfo');
    const btn = document.getElementById('viewClassmatesBtn');
    
    if (!info) {
        body.innerHTML = '<div class="rfid-no-data">未绑定学生</div>';
        btn.style.display = 'none';
        return;
    }
    
    btn.style.display = 'inline-block';
    
    body.innerHTML = `
        <div class="rfid-info-row">
            <span class="rfid-info-label">学生姓名</span>
            <span class="rfid-info-value highlight">${info.name}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">性别</span>
            <span class="rfid-info-value">${info.sex}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">班级</span>
            <span class="rfid-info-value">${info.class_name || '--'}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">学号</span>
            <span class="rfid-info-value">${info.stu_num || '--'}</span>
        </div>
    `;
}

function renderRfidBookInfo(info) {
    const body = document.getElementById('rfidBookInfo');
    
    if (!info) {
        body.innerHTML = '<div class="rfid-no-data">未绑定书本</div>';
        return;
    }
    
    body.innerHTML = `
        <div class="rfid-info-row">
            <span class="rfid-info-label">书本名称</span>
            <span class="rfid-info-value highlight">${info.book_name}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">学科</span>
            <span class="rfid-info-value">${info.subject_name}</span>
        </div>
        <div class="rfid-info-row">
            <span class="rfid-info-label">出版社</span>
            <span class="rfid-info-value">${info.publishing || '--'}</span>
        </div>
    `;
}

function renderRfidTeacherInfo(info) {
    const body = document.getElementById('rfidTeacherInfo');
    
    if (!info || info.length === 0) {
        body.innerHTML = '<div class="rfid-no-data">未关联老师</div>';
        return;
    }
    
    const html = info.map(t => `
        <div class="rfid-teacher-item">
            <span class="rfid-teacher-name">${t.name}</span>
            ${t.account ? `<span class="rfid-teacher-account">${t.account}</span>` : ''}
            <span class="rfid-teacher-subject">${t.subject_name}</span>
        </div>
    `).join('');
    
    body.innerHTML = `<div class="rfid-teacher-list">${html}</div>`;
}

async function viewClassmates() {
    if (!currentRfidData || !currentRfidData.student_info) {
        showToast('无学生信息');
        return;
    }
    
    const classId = currentRfidData.student_info.class_id;
    const className = currentRfidData.student_info.class_name || '班级';
    
    document.getElementById('rfidResultSection').style.display = 'none';
    document.getElementById('rfidClassmatesTitle').textContent = className + ' - 全班同学';
    document.getElementById('rfidClassmatesList').innerHTML = '<div class="rfid-loading"><div class="rfid-spinner"></div></div>';
    document.getElementById('rfidClassmatesSection').style.display = 'block';
    
    try {
        const response = await fetch(`/api/rfid/classmates?class_id=${encodeURIComponent(classId)}`);
        const result = await response.json();
        
        if (!result.success) {
            document.getElementById('rfidClassmatesList').innerHTML = `<div class="rfid-no-data">${result.error || '加载失败'}</div>`;
            return;
        }
        
        document.getElementById('rfidClassmatesCount').textContent = `共 ${result.total} 人`;
        
        if (result.data.length === 0) {
            document.getElementById('rfidClassmatesList').innerHTML = '<div class="rfid-no-data">暂无同学信息</div>';
            return;
        }
        
        const html = result.data.map(s => `
            <div class="rfid-classmate-item">
                <div class="rfid-classmate-avatar">${s.name.charAt(0)}</div>
                <div class="rfid-classmate-info">
                    <div class="rfid-classmate-name">${s.name}</div>
                    <div class="rfid-classmate-num">${s.stu_num || '--'}</div>
                </div>
            </div>
        `).join('');
        
        document.getElementById('rfidClassmatesList').innerHTML = html;
        
    } catch (error) {
        console.error('Load classmates error:', error);
        document.getElementById('rfidClassmatesList').innerHTML = '<div class="rfid-no-data">加载失败</div>';
    }
}

function hideClassmates() {
    document.getElementById('rfidClassmatesSection').style.display = 'none';
    document.getElementById('rfidResultSection').style.display = 'block';
}

// 导出RFID查询函数
window.openRfidQueryModal = openRfidQueryModal;
window.closeRfidQueryModal = closeRfidQueryModal;
window.queryRFID = queryRFID;
window.viewClassmates = viewClassmates;
window.hideClassmates = hideClassmates;
