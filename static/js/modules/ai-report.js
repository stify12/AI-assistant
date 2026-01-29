/**
 * AI 分析报告模块
 * 独立模块化管理，支持典型案例展示和原因分析
 */

// 模块状态
const AIReport = {
    currentReport: null,
    taskId: null,
    isLoading: false
};

/**
 * 显示 AI 报告弹窗
 */
function showAIReportModal() {
    const modal = document.getElementById('aiReportModal');
    if (modal) {
        modal.classList.add('show');
        document.body.style.overflow = 'hidden';
    }
}

/**
 * 隐藏 AI 报告弹窗
 */
function hideAIReportModal() {
    const modal = document.getElementById('aiReportModal');
    if (modal) {
        modal.classList.remove('show');
        document.body.style.overflow = '';
    }
}

/**
 * 生成 AI 分析报告
 */
async function generateAIReport(forceRegenerate = false) {
    if (!selectedTask) return;
    
    AIReport.taskId = selectedTask.task_id;
    AIReport.isLoading = true;
    
    showAIReportModal();
    renderLoadingState(forceRegenerate);
    
    try {
        const res = await fetch(`/api/batch/tasks/${selectedTask.task_id}/ai-report`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ force: forceRegenerate })
        });
        const data = await res.json();
        
        if (data.success) {
            AIReport.currentReport = data.report;
            renderAIReport(data.report, data.cached);
            
            if (!selectedTask.overall_report) selectedTask.overall_report = {};
            selectedTask.overall_report.ai_analysis = data.report;
        } else {
            renderErrorState(data.error || '生成报告失败');
        }
    } catch (e) {
        console.error('[AIReport] 请求失败:', e);
        renderErrorState(e.message);
    } finally {
        AIReport.isLoading = false;
    }
}

/**
 * 重新生成报告
 */
function regenerateAIReport() {
    generateAIReport(true);
}

/**
 * 渲染加载状态
 */
function renderLoadingState(isRegenerating) {
    const body = document.getElementById('aiReportModalBody');
    if (!body) return;
    
    body.innerHTML = `
        <div class="report-loading">
            <div class="spinner"></div>
            <div class="loading-title">${isRegenerating ? '正在重新分析数据...' : '正在加载分析报告...'}</div>
            <div class="loading-hint">预计需要 10-20 秒</div>
        </div>
    `;
    updateGeneratedTime('');
}

/**
 * 渲染错误状态
 */
function renderErrorState(errorMsg) {
    const body = document.getElementById('aiReportModalBody');
    if (!body) return;
    
    body.innerHTML = `
        <div class="report-error">
            <div class="error-icon">!</div>
            <div class="error-title">分析报告生成失败</div>
            <div class="error-text">${escapeHtml(errorMsg)}</div>
            <button class="btn btn-primary" onclick="regenerateAIReport()">重新生成</button>
        </div>
    `;
}

/**
 * 渲染 AI 分析报告（主函数）
 */
function renderAIReport(report, cached) {
    if (!report) return;
    
    const body = document.getElementById('aiReportModalBody');
    if (!body) return;
    
    const overview = report.overview || {};
    const scores = report.capability_scores || {};
    const topIssues = report.top_issues || [];
    const errorCases = report.error_case_analysis || [];
    const errorDist = report.error_distribution || [];
    const recommendations = report.recommendations || [];
    const conclusion = report.conclusion || '';
    
    let html = '';
    
    // 1. 核心指标卡片
    html += renderMetricsSection(overview, scores);
    
    // 2. 数据概览条
    html += renderOverviewBar(overview);
    
    // 3. 错误分布图（可视化条形图）
    if (errorDist.length > 0) {
        html += renderErrorDistribution(errorDist);
    }
    
    // 4. 典型案例分析（核心亮点）
    if (errorCases.length > 0) {
        html += renderCaseAnalysis(errorCases);
    }
    
    // 5. 主要问题列表
    if (topIssues.length > 0) {
        html += renderIssuesList(topIssues);
    }
    
    // 6. 改进建议
    if (recommendations.length > 0) {
        html += renderRecommendations(recommendations);
    }
    
    // 7. 总体结论
    if (conclusion) {
        html += renderConclusion(conclusion);
    }
    
    body.innerHTML = html;
    
    // 更新生成时间
    const generatedAt = report.generated_at || '';
    const cacheText = cached ? '(缓存)' : '(新生成)';
    updateGeneratedTime(generatedAt ? `${generatedAt} ${cacheText}` : '');
    
    // 动画效果
    setTimeout(() => animateBarCharts(), 100);
}

/**
 * 渲染核心指标卡片
 */
function renderMetricsSection(overview, scores) {
    const passRate = overview.pass_rate || 0;
    const recognition = scores.recognition || 0;
    const judgment = scores.judgment || 0;
    const overall = scores.overall || 0;
    
    return `
        <div class="report-metrics">
            <div class="metric-card primary">
                <div class="metric-value">${passRate}%</div>
                <div class="metric-label">总准确率</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${recognition}</div>
                <div class="metric-label">识别能力</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${judgment}</div>
                <div class="metric-label">判断能力</div>
            </div>
            <div class="metric-card">
                <div class="metric-value">${overall}</div>
                <div class="metric-label">综合评分</div>
            </div>
        </div>
    `;
}

/**
 * 渲染数据概览条
 */
function renderOverviewBar(overview) {
    return `
        <div class="report-overview-bar">
            <div class="overview-item">
                <span>总题目</span>
                <strong>${overview.total || 0}</strong>
            </div>
            <div class="overview-divider"></div>
            <div class="overview-item">
                <span>正确</span>
                <strong>${overview.passed || 0}</strong>
            </div>
            <div class="overview-divider"></div>
            <div class="overview-item">
                <span>错误</span>
                <strong>${overview.failed || 0}</strong>
            </div>
            <div class="overview-divider"></div>
            <div class="overview-item">
                <span>作业数</span>
                <strong>${overview.homework_count || 0}</strong>
            </div>
        </div>
    `;
}

/**
 * 渲染错误分布图（水平条形图）
 */
function renderErrorDistribution(distribution) {
    if (!distribution || distribution.length === 0) return '';
    
    const totalErrors = distribution.reduce((sum, d) => sum + (d.count || 0), 0);
    if (totalErrors === 0) return '';
    
    const barsHtml = distribution.slice(0, 5).map((item, idx) => {
        const percent = item.percent || Math.round((item.count / totalErrors) * 100);
        const colorClass = idx === 0 ? 'bar-primary' : idx === 1 ? 'bar-secondary' : 'bar-tertiary';
        
        return `
            <div class="dist-bar-item">
                <div class="dist-bar-label">${escapeHtml(item.type || '未知')}</div>
                <div class="dist-bar-track">
                    <div class="dist-bar-fill ${colorClass}" data-width="${percent}%" style="width: 0%"></div>
                </div>
                <div class="dist-bar-value">${item.count}例 (${percent}%)</div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="report-section">
            <div class="section-header">
                <div class="section-title">错误分布</div>
                <span class="section-badge">共 ${totalErrors} 个错误</span>
            </div>
            <div class="dist-bars">
                ${barsHtml}
            </div>
        </div>
    `;
}

/**
 * 渲染典型案例分析
 */
function renderCaseAnalysis(cases) {
    if (!cases || cases.length === 0) return '';
    
    const casesHtml = cases.slice(0, 4).map((c, i) => {
        const errorType = c.error_type || '未分类错误';
        const index = c.index || '?';
        const baseAnswer = c.base_answer || '-';
        const aiAnswer = c.ai_answer || '-';
        const standardAnswer = c.standard_answer || '';
        const rootCause = c.root_cause || c.explanation || '需要进一步分析';
        
        const isMismatch = baseAnswer !== aiAnswer;
        const errorTypeClass = errorType.includes('识别') ? 'type-recognition' : 
                              errorType.includes('判断') ? 'type-judgment' : 'type-other';
        
        return `
            <div class="case-card">
                <div class="case-header">
                    <div class="case-title">
                        <span class="case-number">${i + 1}</span>
                        <span class="case-index">第 ${escapeHtml(String(index))} 题</span>
                    </div>
                    <span class="case-type-tag ${errorTypeClass}">${escapeHtml(errorType)}</span>
                </div>
                <div class="case-content">
                    <div class="case-comparison">
                        <div class="comparison-item">
                            <div class="comparison-label">基准答案</div>
                            <div class="comparison-value">${escapeHtml(String(baseAnswer))}</div>
                        </div>
                        <div class="comparison-item ${isMismatch ? 'error' : ''}">
                            <div class="comparison-label">AI 识别</div>
                            <div class="comparison-value ${isMismatch ? 'mismatch' : ''}">${escapeHtml(String(aiAnswer))}</div>
                        </div>
                        ${standardAnswer ? `
                        <div class="comparison-item highlight">
                            <div class="comparison-label">标准答案</div>
                            <div class="comparison-value">${escapeHtml(String(standardAnswer))}</div>
                        </div>
                        ` : `
                        <div class="comparison-item">
                            <div class="comparison-label">判断对比</div>
                            <div class="comparison-value">基准=${c.base_correct || '-'}, AI=${c.ai_correct || '-'}</div>
                        </div>
                        `}
                    </div>
                    <div class="case-analysis">
                        <div class="analysis-label">原因分析</div>
                        <div class="analysis-text">${escapeHtml(rootCause)}</div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="report-section">
            <div class="section-header">
                <div class="section-title">典型案例分析</div>
                <span class="section-badge">共 ${cases.length} 个案例</span>
            </div>
            <div class="case-cards">
                ${casesHtml}
            </div>
        </div>
    `;
}

/**
 * 渲染主要问题列表
 */
function renderIssuesList(issues) {
    const issuesHtml = issues.slice(0, 5).map((issue, i) => {
        const count = issue.count || 0;
        const severity = issue.severity || 'medium';
        const severityText = { high: '高', medium: '中', low: '低' }[severity] || '中';
        
        return `
            <div class="issue-item">
                <span class="issue-rank ${i < 2 ? 'top' : ''}">${i + 1}</span>
                <div class="issue-content">
                    <div class="issue-text">${escapeHtml(issue.issue || '')}</div>
                    <div class="issue-meta">
                        <span class="issue-count">${count} 次</span>
                        <span class="issue-severity ${severity}">${severityText}</span>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="report-section">
            <div class="section-header">
                <div class="section-title">主要问题</div>
            </div>
            <div class="issues-list">
                ${issuesHtml}
            </div>
        </div>
    `;
}

/**
 * 渲染改进建议
 */
function renderRecommendations(recommendations) {
    const recsHtml = recommendations.map((rec, i) => {
        if (typeof rec === 'string') {
            return `
                <div class="recommendation-item">
                    <span class="recommendation-icon">✓</span>
                    <div class="recommendation-content">
                        <div class="recommendation-detail">${escapeHtml(rec)}</div>
                    </div>
                </div>
            `;
        }
        return `
            <div class="recommendation-item">
                <span class="recommendation-icon">✓</span>
                <div class="recommendation-content">
                    <div class="recommendation-title">${escapeHtml(rec.title || '')}</div>
                    <div class="recommendation-detail">${escapeHtml(rec.detail || '')}</div>
                </div>
            </div>
        `;
    }).join('');
    
    return `
        <div class="report-section">
            <div class="section-header">
                <div class="section-title">改进建议</div>
            </div>
            <div class="recommendations-list">
                ${recsHtml}
            </div>
        </div>
    `;
}

/**
 * 渲染总体结论
 */
function renderConclusion(conclusion) {
    return `
        <div class="report-section">
            <div class="section-header">
                <div class="section-title">总体结论</div>
            </div>
            <div class="conclusion-box">
                <div class="conclusion-text">${escapeHtml(conclusion)}</div>
            </div>
        </div>
    `;
}

/**
 * 更新生成时间显示
 */
function updateGeneratedTime(text) {
    const el = document.getElementById('reportGeneratedTime');
    if (el) {
        el.textContent = text || '';
    }
}

/**
 * 条形图动画
 */
function animateBarCharts() {
    const bars = document.querySelectorAll('.dist-bar-fill[data-width]');
    bars.forEach(bar => {
        const width = bar.getAttribute('data-width');
        bar.style.width = width;
    });
}

/**
 * HTML 转义
 */
function escapeHtml(text) {
    if (!text) return '';
    const div = document.createElement('div');
    div.textContent = String(text);
    return div.innerHTML;
}

/**
 * 下载报告截图
 */
async function downloadReportScreenshot() {
    if (!AIReport.currentReport) {
        alert('没有可下载的报告');
        return;
    }
    
    const modalBody = document.getElementById('aiReportModalBody');
    if (!modalBody) return;
    
    const btn = event.target;
    const originalText = btn.textContent;
    btn.textContent = '生成中...';
    btn.disabled = true;
    
    try {
        const canvas = await html2canvas(modalBody, {
            backgroundColor: '#ffffff',
            scale: 2,
            useCORS: true
        });
        
        const link = document.createElement('a');
        const taskName = selectedTask?.name || 'AI分析报告';
        const timestamp = new Date().toISOString().slice(0, 10);
        link.download = `${taskName}_${timestamp}.png`;
        link.href = canvas.toDataURL('image/png');
        link.click();
    } catch (e) {
        console.error('[AIReport] 截图失败:', e);
        alert('截图生成失败');
    } finally {
        btn.textContent = originalText;
        btn.disabled = false;
    }
}

/**
 * 复制报告文本
 */
function copyAIReport() {
    if (!AIReport.currentReport) {
        alert('没有可复制的报告');
        return;
    }
    
    const report = AIReport.currentReport;
    const overview = report.overview || {};
    const scores = report.capability_scores || {};
    const topIssues = report.top_issues || [];
    const errorCases = report.error_case_analysis || [];
    const recommendations = report.recommendations || [];
    const conclusion = report.conclusion || '';
    
    let text = `AI 批改效果分析报告\n${'='.repeat(40)}\n\n`;
    text += `【数据概览】\n`;
    text += `总准确率: ${overview.pass_rate || 0}%\n`;
    text += `总题目: ${overview.total || 0} | 正确: ${overview.passed || 0} | 错误: ${overview.failed || 0}\n\n`;
    
    text += `【能力评分】\n`;
    text += `识别: ${scores.recognition || 0} | 判断: ${scores.judgment || 0} | 综合: ${scores.overall || 0}\n\n`;
    
    if (topIssues.length > 0) {
        text += `【主要问题】\n`;
        topIssues.forEach((issue, i) => {
            text += `${i + 1}. ${issue.issue || ''} (${issue.count || 0}次)\n`;
        });
        text += '\n';
    }
    
    if (errorCases.length > 0) {
        text += `【典型案例】\n`;
        errorCases.slice(0, 3).forEach((c, i) => {
            text += `案例${i + 1}: 第${c.index || '?'}题 - ${c.error_type || ''}\n`;
            text += `  基准: ${c.base_answer || '-'} | AI: ${c.ai_answer || '-'}\n`;
            text += `  原因: ${c.root_cause || c.explanation || '暂无'}\n\n`;
        });
    }
    
    if (recommendations.length > 0) {
        text += `【改进建议】\n`;
        recommendations.forEach((rec, i) => {
            const content = typeof rec === 'string' ? rec : `${rec.title}: ${rec.detail}`;
            text += `${i + 1}. ${content}\n`;
        });
        text += '\n';
    }
    
    if (conclusion) {
        text += `【总体结论】\n${conclusion}\n`;
    }
    
    navigator.clipboard.writeText(text).then(() => {
        if (typeof showToast === 'function') {
            showToast('报告已复制到剪贴板');
        } else {
            alert('已复制');
        }
    }).catch(() => {
        alert('复制失败');
    });
}

// 导出到全局
window.AIReport = AIReport;
window.showAIReportModal = showAIReportModal;
window.hideAIReportModal = hideAIReportModal;
window.generateAIReport = generateAIReport;
window.regenerateAIReport = regenerateAIReport;
window.downloadReportScreenshot = downloadReportScreenshot;
window.copyAIReport = copyAIReport;
