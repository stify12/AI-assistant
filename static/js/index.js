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
import { PieChart, LineChart, animateNumber } from './modules/dashboard-charts.js';
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
 */
function renderStatCards(overview, datasets) {
    // 隐藏骨架屏
    ['dataset', 'task', 'question', 'accuracy'].forEach(id => {
        toggleSkeleton(`${id}Skeleton`, `${id}Content`, false);
    });
    
    // 数据集总数 - 优先使用 datasets 数据
    const datasetTotal = datasets?.total || overview?.datasets?.total || 0;
    const datasetEl = document.getElementById('datasetTotal');
    if (datasetEl) {
        animateNumber(datasetEl, datasetTotal, { duration: 800 });
    }
    
    // 任务数
    const taskEl = document.getElementById('taskTotal');
    if (taskEl && overview?.tasks) {
        animateNumber(taskEl, overview.tasks[currentTaskRange] || overview.tasks.today || 0, { duration: 800 });
    }
    
    // 题目数 - 从 datasets 聚合
    const questionEl = document.getElementById('questionTotal');
    const questionDetail = document.getElementById('questionDetail');
    const datasetList = datasets?.datasets || [];
    const totalQuestions = datasetList.reduce((sum, ds) => sum + (ds.question_count || 0), 0);
    
    if (questionEl) {
        const tested = overview?.questions?.tested || totalQuestions;
        animateNumber(questionEl, tested, { duration: 800 });
        if (questionDetail) {
            questionDetail.textContent = `已测试 ${tested} / 总计 ${overview?.questions?.total || totalQuestions}`;
        }
    }
    
    // 准确率
    const accuracyEl = document.getElementById('accuracyValue');
    const trendEl = document.getElementById('accuracyTrend');
    const compareEl = document.getElementById('accuracyCompare');
    const sourceEl = document.getElementById('accuracySource');
    if (accuracyEl && overview?.accuracy) {
        const accuracy = (overview.accuracy.current || 0) * 100;
        animateNumber(accuracyEl, accuracy, { duration: 800, decimals: 1, suffix: '%' });
        
        if (trendEl) {
            trendEl.className = 'trend-arrow';
            if (overview.accuracy.trend === 'up') trendEl.classList.add('up');
            else if (overview.accuracy.trend === 'down') trendEl.classList.add('down');
        }
        
        if (compareEl && overview.accuracy.previous !== undefined) {
            const diff = ((overview.accuracy.current - overview.accuracy.previous) * 100).toFixed(1);
            const sign = diff >= 0 ? '+' : '';
            compareEl.textContent = `与上周对比 ${sign}${diff}%`;
        }
        
        // 显示数据来源：正确题数/总题数
        if (sourceEl) {
            const correct = overview.accuracy.correct_count || 0;
            const tested = overview.questions?.tested || 0;
            sourceEl.textContent = `${formatNumber(correct)}/${formatNumber(tested)} 题`;
        }
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
        const subjectName = SUBJECT_MAP[plan.subject_id] || '--';
        
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
 * 查看计划详情
 */
function viewPlanDetail(planId) {
    navigateTo(`/batch-evaluation?plan_id=${planId}`);
}

/**
 * 执行计划
 */
async function executePlan(planId) {
    try {
        const res = await DashboardAPI.executePlan(planId);
        if (res.success) {
            showToast('计划开始执行', 'success');
            loadTestPlans();
        } else {
            throw new Error(res.error || '执行失败');
        }
    } catch (error) {
        showToast('执行失败: ' + error.message, 'error');
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
    if (!keyword) {
        showToast('请输入任务关键字', 'warning');
        return;
    }
    
    try {
        const res = await DashboardAPI.previewMatch(keyword);
        if (res.success) {
            const container = document.getElementById('matchPreviewContainer');
            const list = document.getElementById('matchPreviewList');
            const count = document.getElementById('matchPreviewCount');
            
            const matches = res.data || [];
            count.textContent = `${matches.length} 条`;
            
            if (matches.length === 0) {
                list.innerHTML = '<div class="match-preview-item">未找到匹配的任务</div>';
            } else {
                list.innerHTML = matches.slice(0, 10).map(m => 
                    `<div class="match-preview-item">${escapeHtml(m.name || m.task_id)}</div>`
                ).join('');
            }
            
            container.style.display = 'block';
        }
    } catch (error) {
        showToast('预览失败', 'error');
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
            subject_id: subjectId ? parseInt(subjectId) : null,
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
    
    // 渲染准确率 Top5
    renderAccuracyTop5(datasets);
}

/**
 * 渲染学科分布饼图
 */
function renderSubjectPieChart(distribution) {
    const canvas = document.getElementById('datasetPieChart');
    if (!canvas) return;
    
    const entries = Object.entries(distribution);
    const total = entries.reduce((sum, [, count]) => sum + count, 0);
    
    if (total === 0) {
        const ctx = canvas.getContext('2d');
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.fillStyle = '#f5f5f7';
        ctx.beginPath();
        ctx.arc(canvas.width / 2, canvas.height / 2, 60, 0, 2 * Math.PI);
        ctx.fill();
        return;
    }
    
    const data = entries.map(([subjectId, count]) => ({
        label: SUBJECT_MAP[subjectId] || '未知',
        value: count,
        color: SUBJECT_COLORS[subjectId] || '#86868b'
    }));
    
    if (!pieChart) {
        pieChart = new PieChart(canvas, { innerRadius: 0.6, duration: 1000 });
    }
    pieChart.setData(data, { title: total.toString(), subtitle: '数据集' });
    
    // 渲染图例
    const legend = document.getElementById('datasetPieLegend');
    if (legend) {
        legend.innerHTML = data.map((item, i) => `
            <div class="pie-legend-item" data-index="${i}">
                <span class="pie-legend-color" style="background: ${item.color}"></span>
                <span class="pie-legend-label">${escapeHtml(item.label)}</span>
                <span class="pie-legend-value">${item.value}</span>
            </div>
        `).join('');
    }
}

/**
 * 渲染准确率 Top5
 */
function renderAccuracyTop5(datasets) {
    const container = document.getElementById('datasetUsageTop5');
    if (!container) return;
    
    const valid = datasets.filter(ds => ds.history_accuracy != null);
    const top5 = [...valid].sort((a, b) => (b.history_accuracy || 0) - (a.history_accuracy || 0)).slice(0, 5);
    
    if (top5.length === 0) {
        container.innerHTML = '<div class="empty-text">暂无准确率数据</div>';
        return;
    }
    
    container.innerHTML = top5.map((ds, i) => {
        const acc = (ds.history_accuracy || 0) * 100;
        const color = acc >= 80 ? '#10b981' : acc >= 60 ? '#f59e0b' : '#ef4444';
        const name = ds.name?.length > 20 ? ds.name.slice(0, 17) + '...' : ds.name;
        
        return `
            <div class="usage-bar-item" onclick="navigateTo('/dataset-manage?dataset_id=${ds.dataset_id}')">
                <div class="usage-bar-rank">${i + 1}</div>
                <div class="usage-bar-info">
                    <div class="usage-bar-name" title="${escapeHtml(ds.name)}">${escapeHtml(name)}</div>
                    <div class="usage-bar-track">
                        <div class="usage-bar-fill" style="width: ${acc}%; background: ${color}"></div>
                    </div>
                </div>
                <div class="usage-bar-count">${acc.toFixed(1)}%</div>
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
 */
function renderSubjectAnalysis(subjects) {
    const container = document.getElementById('subjectList');
    if (!container) return;
    
    if (!subjects || subjects.length === 0) {
        container.innerHTML = '<div class="empty-state-sm"><div class="empty-state-text">暂无评估数据，请先执行批量评估</div></div>';
        return;
    }
    
    container.innerHTML = subjects.map(s => {
        const acc = s.accuracy != null ? (s.accuracy * 100) : null;
        const color = SUBJECT_COLORS[s.subject_id] || '#86868b';
        const accColor = acc == null ? '#86868b' : acc >= 80 ? '#50a060' : acc >= 60 ? '#d0a050' : '#d07070';
        const warning = s.warning ? 'subject-item-warning' : '';
        
        return `
            <div class="subject-item ${warning}">
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
                    <div class="subject-accuracy" style="color: ${accColor}">
                        ${acc != null ? acc.toFixed(1) + '%' : '--'}
                    </div>
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
window.loadTestPlans = loadTestPlans;
window.switchTaskRange = switchTaskRange;

// 创建计划弹窗
window.openCreatePlanModal = openCreatePlanModal;
window.closeCreatePlanModal = closeCreatePlanModal;
window.onCreatePlanModalBackdropClick = onCreatePlanModalBackdropClick;
window.previewKeywordMatch = previewKeywordMatch;
window.createTestPlan = createTestPlan;
window.toggleAdvancedSettings = toggleAdvancedSettings;

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

// 页面加载后延迟加载高级工具统计
setTimeout(loadAdvancedToolsStats, 2000);

console.log('[Dashboard] 模块化看板初始化完成 v20260124');
