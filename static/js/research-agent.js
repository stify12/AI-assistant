/**
 * AI调研员 - 前端交互逻辑
 * 
 * 功能：
 * - 任务管理（创建、切换、删除）
 * - 全流程自动执行（SSE流式）
 * - 分步手动执行
 * - 报告预览与导出
 * - 迭代修改
 * - 文件上传
 */

// ============ 全局状态 ============

const state = {
    currentTaskId: null,
    currentTask: null,
    isRunning: false,
    selectedModels: [],
    eventSource: null
};

// ============ DOM 元素缓存 ============

const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

// ============ 初始化 ============

document.addEventListener('DOMContentLoaded', () => {
    initEventListeners();
    loadTaskList();
});

function initEventListeners() {
    // 新建任务
    $('#btnNewTask').addEventListener('click', showWelcomeView);
    
    // 开始全流程调研
    $('#btnStartResearch').addEventListener('click', startFullResearch);
    
    // 分步执行
    $('#btnStepByStep').addEventListener('click', startStepByStep);
    
    // 分步按钮
    $('#btnNextCollect')?.addEventListener('click', () => runStep('collect'));
    $('#btnNextClean')?.addEventListener('click', () => runStep('clean'));
    $('#btnNextAnalyze')?.addEventListener('click', () => runStep('analyze'));
    $('#btnNextReport')?.addEventListener('click', () => runStep('generate'));
    
    // 文件上传
    $('#fileUpload')?.addEventListener('change', handleFileUpload);
    
    // 导出
    $('#btnExportMd')?.addEventListener('click', () => exportReport('markdown'));
    $('#btnExportWord')?.addEventListener('click', () => exportReport('word'));
    $('#btnExportPpt')?.addEventListener('click', () => exportReport('ppt_outline'));
    
    // 迭代修改
    $('#btnIterate')?.addEventListener('click', submitIteration);
    $('#feedbackInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            submitIteration();
        }
    });
    
    // 清空日志
    $('#btnClearLog')?.addEventListener('click', () => {
        $('#logContent').innerHTML = '';
    });
    
    // Enter键快速开始
    $('#queryInput')?.addEventListener('keydown', (e) => {
        if (e.key === 'Enter' && e.ctrlKey) {
            e.preventDefault();
            startFullResearch();
        }
    });
}

// ============ 视图切换 ============

function showWelcomeView() {
    $('#welcomeView').style.display = '';
    $('#taskView').style.display = 'none';
    state.currentTaskId = null;
    
    // 取消侧边栏选中
    $$('.task-item').forEach(el => el.classList.remove('active'));
}

function showTaskView() {
    $('#welcomeView').style.display = 'none';
    $('#taskView').style.display = '';
}

// ============ 任务管理 ============

async function loadTaskList() {
    try {
        const resp = await fetch('/api/research-agent/tasks');
        const data = await resp.json();
        
        if (data.success && data.tasks.length > 0) {
            renderTaskList(data.tasks);
        } else {
            $('#taskList').innerHTML = '<div class="task-list-empty">暂无调研任务</div>';
        }
    } catch (e) {
        console.error('加载任务列表失败:', e);
    }
}

function renderTaskList(tasks) {
    const html = tasks.map(task => {
        const statusMap = {
            'created': '已创建',
            'parsing': '解析中',
            'collecting': '采集中',
            'cleaning': '清洗中',
            'analyzing': '分析中',
            'generating': '生成中',
            'completed': '已完成',
            'iterating': '迭代中',
            'failed': '失败'
        };
        const statusClass = task.status === 'completed' ? 'completed' : 
                           task.status === 'failed' ? 'failed' : '';
        
        return `
            <div class="task-item ${state.currentTaskId === task.task_id ? 'active' : ''}" 
                 data-task-id="${task.task_id}" 
                 onclick="loadTask('${task.task_id}')">
                <div class="task-item-title">${escapeHtml(task.query || '未命名调研')}</div>
                <div class="task-item-meta">
                    <span class="task-item-status ${statusClass}">${statusMap[task.status] || task.status}</span>
                    <span>${task.updated_at || ''}</span>
                </div>
            </div>
        `;
    }).join('');
    
    $('#taskList').innerHTML = html;
}

async function loadTask(taskId) {
    try {
        const resp = await fetch(`/api/research-agent/tasks/${taskId}`);
        const data = await resp.json();
        
        if (!data.success) {
            addLog('加载任务失败: ' + data.error, 'error');
            return;
        }
        
        state.currentTaskId = taskId;
        state.currentTask = data.task;
        
        // 更新侧边栏选中状态
        $$('.task-item').forEach(el => {
            el.classList.toggle('active', el.dataset.taskId === taskId);
        });
        
        showTaskView();
        renderTaskState(data.task);
        
    } catch (e) {
        addLog('加载任务异常: ' + e.message, 'error');
    }
}

function renderTaskState(task) {
    // 更新标题
    $('#taskTitle').textContent = task.outline?.title || task.query || '调研任务';
    
    // 更新状态
    const statusEl = $('#taskStatus');
    const statusMap = {
        'created': '已创建', 'parsing': '解析中', 'collecting': '采集中',
        'cleaning': '清洗中', 'analyzing': '分析中', 'generating': '生成中',
        'completed': '已完成', 'iterating': '迭代中', 'failed': '失败'
    };
    statusEl.textContent = statusMap[task.status] || task.status;
    statusEl.className = 'task-status ' + (task.status === 'completed' ? 'completed' : 
                                           task.status === 'failed' ? 'failed' : '');
    
    // 更新Token
    $('#taskTokens').textContent = `Token: ${(task.total_tokens_used || 0).toLocaleString()}`;
    
    // 更新进度步骤
    updateProgressSteps(task);
    
    // 根据状态渲染各面板
    hideAllPanels();
    
    if (task.outline) {
        renderOutline(task.outline);
        showPanel('panelOutline');
    }
    
    if (task.collected_data && task.collected_data.length > 0) {
        renderCollectedData(task.collected_data);
        showPanel('panelCollect');
    }
    
    if (task.cleaned_data && task.cleaned_data.length > 0) {
        renderCleanedData(task.cleaned_data);
        showPanel('panelClean');
    }
    
    if (task.analysis_results && task.analysis_results.length > 0) {
        renderAnalysis(task.analysis_results);
        showPanel('panelAnalyze');
    }
    
    if (task.report) {
        renderReport(task.report);
        showPanel('panelReport');
    }
    
    // 始终显示日志
    showPanel('panelLog');
}

function updateProgressSteps(task) {
    const steps = ['parse', 'collect', 'clean', 'analyze', 'generate'];
    const stepOrder = {
        'created': -1, 'parsing': 0, 'collecting': 1, 'cleaning': 2,
        'analyzing': 3, 'generating': 4, 'completed': 5, 'iterating': 5, 'failed': -1
    };
    
    const currentIdx = stepOrder[task.status] ?? -1;
    
    // 检查各步骤是否已完成
    const completedSteps = new Set();
    if (task.outline) completedSteps.add('parse');
    if (task.collected_data?.length > 0) completedSteps.add('collect');
    if (task.cleaned_data?.length > 0) completedSteps.add('clean');
    if (task.analysis_results?.length > 0) completedSteps.add('analyze');
    if (task.report) completedSteps.add('generate');
    
    const stepElements = $$('.step');
    const lineElements = $$('.step-line');
    
    stepElements.forEach((el, i) => {
        const stepName = steps[i];
        el.classList.remove('active', 'done');
        
        if (completedSteps.has(stepName)) {
            el.classList.add('done');
        } else if (i === currentIdx) {
            el.classList.add('active');
        }
    });
    
    lineElements.forEach((el, i) => {
        el.classList.toggle('done', completedSteps.has(steps[i]));
    });
}

// ============ 全流程执行 ============

async function startFullResearch() {
    const query = $('#queryInput').value.trim();
    if (!query) {
        alert('请输入调研需求');
        return;
    }
    
    if (state.isRunning) return;
    
    const industry = $('#industryInput').value.trim();
    const scope = $('#scopeInput').value.trim();
    const model = $('#modelSelect').value;
    
    // 创建任务
    try {
        const resp = await fetch('/api/research-agent/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, industry, scope, llm_model: model })
        });
        const data = await resp.json();
        
        if (!data.success) {
            alert('创建任务失败: ' + data.error);
            return;
        }
        
        state.currentTaskId = data.task.task_id;
        state.currentTask = data.task;
        
        // 切换到任务视图
        showTaskView();
        renderTaskState(data.task);
        loadTaskList();
        
        addLog('调研任务已创建，开始全流程执行...', 'info');
        
        // 启动全流程SSE
        runPipeline(data.task.task_id);
        
    } catch (e) {
        alert('创建任务异常: ' + e.message);
    }
}

function runPipeline(taskId) {
    if (state.eventSource) {
        state.eventSource.close();
    }
    
    state.isRunning = true;
    disableButtons(true);
    showToast('全流程调研已启动', 'info');
    
    // 使用fetch + ReadableStream实现SSE（POST请求）
    fetch('/api/research-agent/run-pipeline', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ 
            task_id: taskId,
            model_types: state.selectedModels.length > 0 ? state.selectedModels : []
        })
    }).then(response => {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        function read() {
            reader.read().then(({ done, value }) => {
                if (done) {
                    state.isRunning = false;
                    disableButtons(false);
                    return;
                }
                
                buffer += decoder.decode(value, { stream: true });
                const lines = buffer.split('\n');
                buffer = lines.pop() || '';
                
                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        try {
                            const event = JSON.parse(line.slice(6));
                            handlePipelineEvent(event);
                        } catch (e) {
                            // 忽略解析错误
                        }
                    }
                }
                
                read();
            }).catch(err => {
                addLog('连接断开: ' + err.message, 'error');
                state.isRunning = false;
                disableButtons(false);
            });
        }
        
        read();
    }).catch(err => {
        addLog('请求失败: ' + err.message, 'error');
        state.isRunning = false;
        disableButtons(false);
    });
}

function handlePipelineEvent(event) {
    switch (event.type) {
        case 'stage':
            addLog(`▶ ${event.message}`, 'info');
            // 更新进度步骤
            const stepEl = $(`.step[data-step="${event.stage}"]`);
            if (stepEl) {
                $$('.step').forEach(el => el.classList.remove('active'));
                stepEl.classList.add('active');
            }
            break;
            
        case 'stage_done':
            addLog(`✓ ${event.message}`, 'success');
            
            // 标记完成
            const doneStep = $(`.step[data-step="${event.stage}"]`);
            if (doneStep) {
                doneStep.classList.remove('active');
                doneStep.classList.add('done');
            }
            
            // 渲染结果
            if (event.stage === 'parsing' && event.result) {
                renderOutline(event.result);
                showPanel('panelOutline');
            } else if (event.stage === 'collecting' && event.result) {
                // 重新加载任务获取完整数据
                reloadCurrentTask();
            } else if (event.stage === 'cleaning' && event.result) {
                reloadCurrentTask();
            } else if (event.stage === 'analyzing' && event.result) {
                renderAnalysis(event.result);
                showPanel('panelAnalyze');
            } else if (event.stage === 'generating' && event.result) {
                renderReport(event.result);
                showPanel('panelReport');
            }
            break;
            
        case 'done':
            addLog(`🎉 ${event.message}（消耗Token: ${(event.total_tokens || 0).toLocaleString()}）`, 'success');
            showToast('调研全流程完成！', 'success', 5000);
            state.isRunning = false;
            disableButtons(false);
            reloadCurrentTask();
            loadTaskList();
            break;
            
        case 'error':
            addLog(`✗ ${event.message}`, 'error');
            showToast(event.message, 'error', 5000);
            state.isRunning = false;
            disableButtons(false);
            break;
    }
}

// ============ 分步执行 ============

async function startStepByStep() {
    const query = $('#queryInput').value.trim();
    if (!query) {
        alert('请输入调研需求');
        return;
    }
    
    const industry = $('#industryInput').value.trim();
    const scope = $('#scopeInput').value.trim();
    const model = $('#modelSelect').value;
    
    try {
        const resp = await fetch('/api/research-agent/tasks', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ query, industry, scope, llm_model: model })
        });
        const data = await resp.json();
        
        if (!data.success) {
            alert('创建任务失败: ' + data.error);
            return;
        }
        
        state.currentTaskId = data.task.task_id;
        state.currentTask = data.task;
        
        showTaskView();
        renderTaskState(data.task);
        loadTaskList();
        
        addLog('任务已创建，开始分步执行...', 'info');
        
        // 先执行第一步：需求解析
        runStep('parse');
        
    } catch (e) {
        alert('创建任务异常: ' + e.message);
    }
}

async function runStep(step) {
    if (state.isRunning || !state.currentTaskId) return;
    
    state.isRunning = true;
    disableButtons(true);
    
    const stepNames = {
        'parse': '需求解析', 'collect': '数据采集', 'clean': '数据清洗',
        'analyze': '智能分析', 'generate': '报告生成'
    };
    
    addLog(`▶ 开始${stepNames[step]}...`, 'info');
    
    // 更新进度步骤
    const stepEl = $(`.step[data-step="${step}"]`);
    if (stepEl) {
        $$('.step').forEach(el => el.classList.remove('active'));
        stepEl.classList.add('active');
    }
    
    try {
        // 使用SSE流式请求
        const resp = await fetch('/api/research-agent/step-stream', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                task_id: state.currentTaskId,
                step: step,
                model_types: state.selectedModels
            })
        });
        
        const reader = resp.body.getReader();
        const decoder = new TextDecoder();
        let buffer = '';
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split('\n');
            buffer = lines.pop() || '';
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const event = JSON.parse(line.slice(6));
                        handleStepEvent(event, step);
                    } catch (e) {
                        // 忽略
                    }
                }
            }
        }
        
    } catch (e) {
        addLog(`✗ ${stepNames[step]}失败: ${e.message}`, 'error');
    }
    
    state.isRunning = false;
    disableButtons(false);
}

function handleStepEvent(event, step) {
    if (event.type === 'result') {
        addLog(`✓ ${step}完成`, 'success');
        
        const stepEl = $(`.step[data-step="${step}"]`);
        if (stepEl) {
            stepEl.classList.remove('active');
            stepEl.classList.add('done');
        }
        
        if (step === 'parse' && event.outline) {
            renderOutline(event.outline);
            showPanel('panelOutline');
            
            // 渲染推荐模型
            if (event.recommended_models) {
                renderModelSelector(event.recommended_models);
            }
        } else if (step === 'collect') {
            reloadCurrentTask();
        } else if (step === 'clean') {
            reloadCurrentTask();
        } else if (step === 'analyze' && event.results) {
            renderAnalysis(event.results);
            showPanel('panelAnalyze');
        } else if (step === 'generate' && event.report) {
            renderReport(event.report);
            showPanel('panelReport');
        }
        
        // 更新Token
        reloadCurrentTask();
        loadTaskList();
        
    } else if (event.type === 'error') {
        addLog(`✗ 错误: ${event.message}`, 'error');
    } else if (event.type === 'done') {
        addLog(`✓ 步骤完成`, 'success');
    }
}

// ============ 渲染函数 ============

function renderOutline(outline) {
    let html = '';
    
    // 标题和元信息
    html += `<div class="outline-section">`;
    html += `<div class="outline-title">${escapeHtml(outline.title || '')}</div>`;
    html += `<div class="outline-meta">`;
    if (outline.objective) html += `<strong>调研目标：</strong>${escapeHtml(outline.objective)}<br>`;
    if (outline.scope) html += `<strong>调研范围：</strong>${escapeHtml(outline.scope)}<br>`;
    if (outline.methodology) html += `<strong>调研方法：</strong>${escapeHtml(outline.methodology)}`;
    html += `</div>`;
    
    // 提纲项
    html += `<ul class="outline-items">`;
    (outline.items || []).forEach((item, i) => {
        html += `<li class="outline-item">`;
        html += `<h4>${escapeHtml(item.title || '')}</h4>`;
        if (item.description) html += `<p>${escapeHtml(item.description)}</p>`;
        
        // 数据需求标签
        if (item.data_requirements?.length > 0) {
            html += `<div class="tags">`;
            item.data_requirements.forEach(req => {
                html += `<span class="tag">${escapeHtml(req)}</span>`;
            });
            html += `</div>`;
        }
        
        // 子项
        if (item.sub_items?.length > 0) {
            html += `<ul class="outline-items" style="margin-top:8px;">`;
            item.sub_items.forEach(sub => {
                html += `<li class="outline-item" style="border-left-color:#a5b4fc;">`;
                html += `<h4 style="font-size:13px;">${escapeHtml(sub.title || '')}</h4>`;
                if (sub.description) html += `<p>${escapeHtml(sub.description)}</p>`;
                html += `</li>`;
            });
            html += `</ul>`;
        }
        
        html += `</li>`;
    });
    html += `</ul>`;
    
    // 采集计划
    if (outline.collection_plan?.length > 0) {
        html += `<h4 style="margin-top:16px;margin-bottom:8px;">数据采集计划</h4>`;
        html += `<div style="overflow-x:auto;"><table style="width:100%;font-size:12px;border-collapse:collapse;">`;
        html += `<tr><th style="padding:6px 10px;background:#f1f5f9;border:1px solid #e2e8f0;">数据维度</th>
                     <th style="padding:6px 10px;background:#f1f5f9;border:1px solid #e2e8f0;">数据来源</th>
                     <th style="padding:6px 10px;background:#f1f5f9;border:1px solid #e2e8f0;">采集方法</th>
                     <th style="padding:6px 10px;background:#f1f5f9;border:1px solid #e2e8f0;">优先级</th></tr>`;
        outline.collection_plan.forEach(plan => {
            html += `<tr>
                <td style="padding:6px 10px;border:1px solid #e2e8f0;">${escapeHtml(plan.dimension || '')}</td>
                <td style="padding:6px 10px;border:1px solid #e2e8f0;">${escapeHtml(plan.sources || '')}</td>
                <td style="padding:6px 10px;border:1px solid #e2e8f0;">${escapeHtml(plan.method || '')}</td>
                <td style="padding:6px 10px;border:1px solid #e2e8f0;">${escapeHtml(plan.priority || '')}</td>
            </tr>`;
        });
        html += `</table></div>`;
    }
    
    html += `</div>`;
    
    $('#outlineContent').innerHTML = html;
}

function renderCollectedData(data) {
    let html = '';
    
    // 统计
    const total = data.length;
    const highCredibility = data.filter(d => d.source?.credibility === 'high').length;
    const conflicts = data.filter(d => d.is_conflicting).length;
    
    html += `<div class="data-stats">
        <div class="stat-item"><div class="stat-value">${total}</div><div class="stat-label">采集总量</div></div>
        <div class="stat-item"><div class="stat-value">${highCredibility}</div><div class="stat-label">高可信度</div></div>
        <div class="stat-item"><div class="stat-value">${conflicts}</div><div class="stat-label">数据冲突</div></div>
    </div>`;
    
    // 数据列表
    html += `<ul class="data-list">`;
    data.slice(0, 50).forEach(item => {
        const credClass = item.source?.credibility || 'unverified';
        const credLabel = { high: '高可信', medium: '中等', low: '低可信', unverified: '未验证', no_source: '无来源' };
        
        html += `<li class="data-item ${item.is_conflicting ? 'conflicting' : ''}">`;
        html += `<div class="data-item-header">`;
        html += `<span class="data-item-title">${escapeHtml(item.title || '无标题')}</span>`;
        html += `<span class="credibility-badge ${credClass}">${credLabel[credClass] || credClass}</span>`;
        html += `</div>`;
        html += `<div class="data-item-content">${escapeHtml((item.content || '').substring(0, 200))}...</div>`;
        
        if (item.source?.url) {
            html += `<div class="data-item-source">来源: <a href="${escapeHtml(item.source.url)}" target="_blank">${escapeHtml(item.source.name || item.source.url)}</a></div>`;
        } else if (item.source?.name) {
            html += `<div class="data-item-source">来源: ${escapeHtml(item.source.name)}</div>`;
        }
        
        if (item.is_conflicting && item.conflict_note) {
            html += `<div class="confidence-note">数据冲突：${escapeHtml(item.conflict_note)}</div>`;
        }
        
        html += `</li>`;
    });
    html += `</ul>`;
    
    $('#collectContent').innerHTML = html;
}

function renderCleanedData(data) {
    // 复用采集数据的渲染，加上清洗统计
    renderCollectedData(data);
    
    // 更新面板标题
    const statsHtml = `<div class="data-stats">
        <div class="stat-item"><div class="stat-value">${data.length}</div><div class="stat-label">有效数据</div></div>
        <div class="stat-item"><div class="stat-value">${data.filter(d => d.is_verified).length}</div><div class="stat-label">已校验</div></div>
        <div class="stat-item"><div class="stat-value">${data.filter(d => d.source?.credibility === 'high').length}</div><div class="stat-label">高可信度</div></div>
    </div>`;
    
    // 替换cleanContent的统计区
    const cleanContent = $('#cleanContent');
    cleanContent.innerHTML = statsHtml + cleanContent.innerHTML.replace(/<div class="data-stats">[\s\S]*?<\/div>\s*<\/div>\s*<\/div>/, '');
}

function renderAnalysis(results) {
    let html = '';
    
    const modelIcons = {
        'swot': '', 'porter_five': '', 'pest': '',
        'user_segmentation': '', 'market_size': '', 'competitive': ''
    };
    
    (Array.isArray(results) ? results : []).forEach((result, i) => {
        const icon = modelIcons[result.model_type] || '';
        
        html += `<div class="analysis-card">`;
        html += `<div class="analysis-card-header" onclick="this.nextElementSibling.style.display=this.nextElementSibling.style.display==='none'?'':'none'">`;
        html += `<span class="icon">${icon}</span>`;
        html += `<h4>${escapeHtml(result.title || '')}</h4>`;
        html += `<svg viewBox="0 0 24 24" width="18" height="18" style="color:#94a3b8"><path fill="currentColor" d="M7.41 8.59L12 13.17l4.59-4.58L18 10l-6 6-6-6 1.41-1.41z"/></svg>`;
        html += `</div>`;
        
        html += `<div class="analysis-card-body">`;
        
        // 渲染Markdown内容
        if (result.content) {
            html += `<div class="markdown-content">${renderMarkdown(result.content)}</div>`;
        }
        
        // 来源引用
        if (result.source_citations?.length > 0) {
            html += `<div style="margin-top:12px;"><h5 style="font-size:12px;color:#64748b;margin-bottom:6px;">数据来源</h5>`;
            result.source_citations.forEach(cite => {
                html += `<div style="font-size:11px;color:#94a3b8;margin-bottom:2px;">• ${escapeHtml(cite.claim || '')} — ${escapeHtml(cite.source || '')}`;
                if (cite.url) html += ` <a href="${escapeHtml(cite.url)}" target="_blank" style="color:#3b82f6;">[链接]</a>`;
                html += `</div>`;
            });
            html += `</div>`;
        }
        
        // 图表建议
        if (result.chart_suggestions?.length > 0) {
            html += `<div style="margin-top:12px;"><h5 style="font-size:12px;color:#64748b;margin-bottom:6px;">推荐图表</h5>`;
            result.chart_suggestions.forEach(chart => {
                html += `<span class="tag" style="margin-right:4px;margin-bottom:4px;display:inline-block;">${chart.type}: ${escapeHtml(chart.title || '')}</span>`;
            });
            html += `</div>`;
        }
        
        // 可信度说明
        if (result.confidence_note) {
            html += `<div class="confidence-note">${escapeHtml(result.confidence_note)}</div>`;
        }
        
        html += `</div></div>`;
    });
    
    $('#analyzeContent').innerHTML = html;
}

function renderReport(report) {
    let html = '';
    
    if (report.content) {
        html = `<div class="report-content">${renderMarkdown(report.content)}</div>`;
    } else {
        // 从sections构建
        html = '<div class="report-content">';
        html += `<h1>${escapeHtml(report.title || '')}</h1>`;
        
        if (report.summary) {
            html += `<blockquote>${renderMarkdown(report.summary)}</blockquote>`;
        }
        
        (report.sections || []).forEach(section => {
            html += `<h2>${escapeHtml(section.title || '')}</h2>`;
            html += renderMarkdown(section.content || '');
        });
        
        if (report.appendix?.length > 0) {
            html += '<hr>';
            html += '<h2>附录</h2>';
            report.appendix.forEach(item => {
                html += `<h3>${escapeHtml(item.title || '')}</h3>`;
                html += renderMarkdown(item.content || '');
            });
        }
        
        html += `<div style="text-align:center;color:#94a3b8;font-size:12px;margin-top:24px;padding:12px;">`;
        html += `版本: v${report.version || 1} | 生成时间: ${report.created_at || ''}`;
        html += `</div>`;
        
        html += '</div>';
    }
    
    $('#reportContent').innerHTML = html;
}

function renderModelSelector(recommendations) {
    const allModels = [
        { model_type: 'swot', name: 'SWOT分析', icon: '' },
        { model_type: 'porter_five', name: '波特五力', icon: '' },
        { model_type: 'pest', name: 'PEST分析', icon: '' },
        { model_type: 'user_segmentation', name: '用户分层', icon: '' },
        { model_type: 'market_size', name: '市场规模', icon: '' },
        { model_type: 'competitive', name: '竞争格局', icon: '' }
    ];
    
    const recommendedTypes = new Set((recommendations || []).map(r => r.model_type));
    
    // 默认选中推荐的模型
    state.selectedModels = Array.from(recommendedTypes);
    
    const html = allModels.map(m => {
        const selected = recommendedTypes.has(m.model_type);
        return `<span class="model-chip ${selected ? 'selected' : ''}" 
                      data-model="${m.model_type}"
                      onclick="toggleModel(this, '${m.model_type}')">
                    ${m.icon} ${m.name}
                </span>`;
    }).join('');
    
    $('#modelSelector').innerHTML = html;
}

function toggleModel(el, modelType) {
    el.classList.toggle('selected');
    
    if (el.classList.contains('selected')) {
        if (!state.selectedModels.includes(modelType)) {
            state.selectedModels.push(modelType);
        }
    } else {
        state.selectedModels = state.selectedModels.filter(m => m !== modelType);
    }
}

// ============ 文件上传 ============

async function handleFileUpload(e) {
    const file = e.target.files[0];
    if (!file || !state.currentTaskId) return;
    
    addLog(`上传文件: ${file.name}`, 'info');
    
    const formData = new FormData();
    formData.append('file', file);
    formData.append('task_id', state.currentTaskId);
    
    try {
        const resp = await fetch('/api/research-agent/upload', {
            method: 'POST',
            body: formData
        });
        const data = await resp.json();
        
        if (data.success) {
            addLog(`✓ 文件解析完成，提取 ${data.extracted_count} 条数据`, 'success');
            reloadCurrentTask();
        } else {
            addLog(`✗ 文件上传失败: ${data.error}`, 'error');
        }
    } catch (e) {
        addLog(`✗ 文件上传异常: ${e.message}`, 'error');
    }
    
    // 重置input
    e.target.value = '';
}

// ============ 报告导出 ============

async function exportReport(format) {
    if (!state.currentTaskId) return;
    
    addLog(`导出报告: ${format}`, 'info');
    
    try {
        const resp = await fetch('/api/research-agent/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: state.currentTaskId, format })
        });
        
        if (resp.ok) {
            const blob = await resp.blob();
            const url = URL.createObjectURL(blob);
            const a = document.createElement('a');
            
            const ext = { markdown: 'md', word: 'docx', ppt_outline: 'md' };
            a.href = url;
            a.download = `research_report.${ext[format] || 'md'}`;
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            URL.revokeObjectURL(url);
            
            addLog(`✓ 报告导出成功`, 'success');
        } else {
            const data = await resp.json();
            addLog(`✗ 导出失败: ${data.error}`, 'error');
        }
    } catch (e) {
        addLog(`✗ 导出异常: ${e.message}`, 'error');
    }
}

// ============ 迭代修改 ============

async function submitIteration() {
    const feedback = $('#feedbackInput').value.trim();
    if (!feedback || !state.currentTaskId || state.isRunning) return;
    
    state.isRunning = true;
    disableButtons(true);
    addLog(`提交修改意见: ${feedback}`, 'info');
    
    try {
        const resp = await fetch('/api/research-agent/iterate', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: state.currentTaskId, feedback })
        });
        const data = await resp.json();
        
        if (data.success) {
            addLog(`✓ 报告已更新至 v${data.version}`, 'success');
            renderReport(data.report);
            $('#feedbackInput').value = '';
            reloadCurrentTask();
        } else {
            addLog(`✗ 修改失败: ${data.error}`, 'error');
        }
    } catch (e) {
        addLog(`✗ 修改异常: ${e.message}`, 'error');
    }
    
    state.isRunning = false;
    disableButtons(false);
}

// ============ 工具函数 ============

function showPanel(panelId) {
    const panel = $(`#${panelId}`);
    if (panel) panel.style.display = '';
}

function hideAllPanels() {
    $$('.panel').forEach(el => el.style.display = 'none');
}

function disableButtons(disabled) {
    $$('.btn-primary, .btn-secondary').forEach(btn => {
        btn.disabled = disabled;
    });
}

async function reloadCurrentTask() {
    if (!state.currentTaskId) return;
    try {
        const resp = await fetch(`/api/research-agent/tasks/${state.currentTaskId}`);
        const data = await resp.json();
        if (data.success) {
            state.currentTask = data.task;
            renderTaskState(data.task);
        }
    } catch (e) {
        // 静默失败
    }
}

function addLog(message, type = '') {
    const logEl = $('#logContent');
    if (!logEl) return;
    
    const now = new Date();
    const time = `${now.getHours().toString().padStart(2, '0')}:${now.getMinutes().toString().padStart(2, '0')}:${now.getSeconds().toString().padStart(2, '0')}`;
    
    const entry = document.createElement('div');
    entry.className = `log-entry ${type ? 'log-' + type : ''}`;
    entry.innerHTML = `<span class="log-time">${time}</span>${escapeHtml(message)}`;
    
    logEl.appendChild(entry);
    logEl.scrollTop = logEl.scrollHeight;
}

function escapeHtml(str) {
    if (!str) return '';
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

function renderMarkdown(text) {
    if (!text) return '';
    if (typeof marked !== 'undefined') {
        try {
            return marked.parse(text);
        } catch (e) {
            return escapeHtml(text).replace(/\n/g, '<br>');
        }
    }
    // marked未加载时的简单渲染
    return escapeHtml(text).replace(/\n/g, '<br>');
}

// ============ Toast通知系统 ============

function showToast(message, type = 'info', duration = 3000) {
    let container = document.querySelector('.toast-container');
    if (!container) {
        container = document.createElement('div');
        container.className = 'toast-container';
        document.body.appendChild(container);
    }
    
    const icons = { success: '✓', error: '✗', info: 'ℹ' };
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.innerHTML = `<span>${icons[type] || ''}</span> ${escapeHtml(message)}`;
    container.appendChild(toast);
    
    setTimeout(() => {
        toast.style.opacity = '0';
        toast.style.transition = 'opacity 0.3s';
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// 全局暴露
window.loadTask = loadTask;
window.toggleModel = toggleModel;
window.showToast = showToast;
