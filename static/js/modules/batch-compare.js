/**
 * 批次对比分析模块 (US-18, US-33)
 */
const BatchCompareModule = {
    trendChart: null,
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        // 时间范围选择
        document.addEventListener('change', (e) => {
            if (e.target.id === 'trend-days-select') {
                this.loadTrend(parseInt(e.target.value));
            }
        });
        
        // 对比按钮
        document.addEventListener('click', (e) => {
            if (e.target.id === 'compare-periods-btn') {
                this.comparePeriods();
            }
            if (e.target.id === 'compare-baseline-btn') {
                this.compareBaseline();
            }
        });
    },
    
    async loadTrend(days = 30, subjectId = null) {
        const container = document.getElementById('trend-chart-container');
        if (!container) return;
        
        try {
            let url = `/api/batch-compare/trend?days=${days}`;
            if (subjectId !== null) url += `&subject_id=${subjectId}`;
            
            const resp = await fetch(url);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error);
            }
            
            this.renderTrendChart(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">加载失败: ${err.message}</div>`;
        }
    },
    
    renderTrendChart(container, data) {
        // 简单的SVG折线图
        const width = container.clientWidth || 600;
        const height = 200;
        const padding = 40;
        
        if (!data.dates || data.dates.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无趋势数据</div>';
            return;
        }
        
        const maxAcc = Math.max(...data.accuracy_data, 100);
        const minAcc = Math.min(...data.accuracy_data, 0);
        const range = maxAcc - minAcc || 1;
        
        const xStep = (width - padding * 2) / Math.max(data.dates.length - 1, 1);
        
        const points = data.accuracy_data.map((acc, i) => {
            const x = padding + i * xStep;
            const y = height - padding - ((acc - minAcc) / range) * (height - padding * 2);
            return `${x},${y}`;
        }).join(' ');
        
        let html = `
            <svg width="${width}" height="${height}" class="trend-chart">
                <polyline points="${points}" fill="none" stroke="#1d1d1f" stroke-width="2"/>
        `;
        
        // 数据点
        data.accuracy_data.forEach((acc, i) => {
            const x = padding + i * xStep;
            const y = height - padding - ((acc - minAcc) / range) * (height - padding * 2);
            html += `<circle cx="${x}" cy="${y}" r="4" fill="#1d1d1f"/>`;
        });
        
        // X轴标签（只显示部分）
        const labelStep = Math.ceil(data.dates.length / 5);
        data.dates.forEach((date, i) => {
            if (i % labelStep === 0 || i === data.dates.length - 1) {
                const x = padding + i * xStep;
                html += `<text x="${x}" y="${height - 10}" text-anchor="middle" font-size="10" fill="#86868b">${date.slice(5)}</text>`;
            }
        });
        
        html += '</svg>';
        
        // 统计摘要
        const avgAcc = data.accuracy_data.reduce((a, b) => a + b, 0) / data.accuracy_data.length;
        const latestAcc = data.accuracy_data[data.accuracy_data.length - 1];
        const firstAcc = data.accuracy_data[0];
        const change = latestAcc - firstAcc;
        
        html += `
            <div class="trend-summary">
                <div class="summary-item">
                    <span class="label">平均准确率</span>
                    <span class="value">${avgAcc.toFixed(1)}%</span>
                </div>
                <div class="summary-item">
                    <span class="label">最新准确率</span>
                    <span class="value">${latestAcc.toFixed(1)}%</span>
                </div>
                <div class="summary-item">
                    <span class="label">变化</span>
                    <span class="value ${change >= 0 ? 'positive' : 'negative'}">
                        ${change >= 0 ? '+' : ''}${change.toFixed(1)}%
                    </span>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    },
    
    async comparePeriods() {
        const p1Start = document.getElementById('period1-start')?.value;
        const p1End = document.getElementById('period1-end')?.value;
        const p2Start = document.getElementById('period2-start')?.value;
        const p2End = document.getElementById('period2-end')?.value;
        
        if (!p1Start || !p1End || !p2Start || !p2End) {
            alert('请选择完整的时间段');
            return;
        }
        
        const container = document.getElementById('period-compare-result');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">对比中...</div>';
        
        try {
            const url = `/api/batch-compare/periods?period1_start=${p1Start}&period1_end=${p1End}&period2_start=${p2Start}&period2_end=${p2End}`;
            const resp = await fetch(url);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error);
            }
            
            this.renderPeriodCompare(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">对比失败: ${err.message}</div>`;
        }
    },
    
    renderPeriodCompare(container, data) {
        const changeClass = data.change >= 0 ? 'positive' : 'negative';
        const changeIcon = data.change >= 0 ? '↑' : '↓';
        
        container.innerHTML = `
            <div class="period-compare-cards">
                <div class="period-card">
                    <div class="period-label">时间段1</div>
                    <div class="period-dates">${data.period1.start} ~ ${data.period1.end}</div>
                    <div class="period-accuracy">${(data.period1.accuracy * 100).toFixed(1)}%</div>
                    <div class="period-meta">${data.period1.task_count} 个任务 / ${data.period1.total_questions} 题</div>
                </div>
                <div class="period-change ${changeClass}">
                    <span class="change-icon">${changeIcon}</span>
                    <span class="change-value">${Math.abs(data.change).toFixed(1)}%</span>
                    <span class="change-percent">(${data.change_percent >= 0 ? '+' : ''}${data.change_percent.toFixed(1)}%)</span>
                </div>
                <div class="period-card">
                    <div class="period-label">时间段2</div>
                    <div class="period-dates">${data.period2.start} ~ ${data.period2.end}</div>
                    <div class="period-accuracy">${(data.period2.accuracy * 100).toFixed(1)}%</div>
                    <div class="period-meta">${data.period2.task_count} 个任务 / ${data.period2.total_questions} 题</div>
                </div>
            </div>
        `;
    },
    
    async compareBaseline() {
        const taskId = document.getElementById('baseline-task-id')?.value;
        const baselineId = document.getElementById('baseline-compare-id')?.value;
        
        if (!taskId) {
            alert('请输入任务ID');
            return;
        }
        
        const container = document.getElementById('baseline-compare-result');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">对比中...</div>';
        
        try {
            let url = `/api/batch-compare/baseline?task_id=${taskId}`;
            if (baselineId) url += `&baseline_task_id=${baselineId}`;
            
            const resp = await fetch(url);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error);
            }
            
            this.renderBaselineCompare(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">对比失败: ${err.message}</div>`;
        }
    },
    
    renderBaselineCompare(container, data) {
        const changeClass = data.change >= 0 ? 'positive' : 'negative';
        
        let html = `
            <div class="baseline-compare-header">
                <div class="compare-item">
                    <div class="item-label">基线</div>
                    <div class="item-accuracy">${data.baseline.accuracy}%</div>
                    <div class="item-meta">${data.baseline.total_questions} 题</div>
                </div>
                <div class="compare-arrow">→</div>
                <div class="compare-item">
                    <div class="item-label">当前</div>
                    <div class="item-accuracy">${data.current.accuracy}%</div>
                    <div class="item-meta">${data.current.total_questions} 题</div>
                </div>
                <div class="compare-change ${changeClass}">
                    ${data.change >= 0 ? '+' : ''}${data.change}%
                </div>
            </div>
            <div class="baseline-compare-details">
                <div class="detail-section improvements">
                    <div class="section-title">改进 (${data.improvement_count})</div>
                    <div class="detail-list">
                        ${data.improvements.slice(0, 10).map(item => `
                            <div class="detail-item">
                                <span class="item-loc">P${item.page} Q${item.question}</span>
                                <span class="item-change">${item.baseline_answer} → ${item.current_answer}</span>
                            </div>
                        `).join('')}
                        ${data.improvement_count > 10 ? `<div class="more-hint">还有 ${data.improvement_count - 10} 项...</div>` : ''}
                    </div>
                </div>
                <div class="detail-section regressions">
                    <div class="section-title">退化 (${data.regression_count})</div>
                    <div class="detail-list">
                        ${data.regressions.slice(0, 10).map(item => `
                            <div class="detail-item">
                                <span class="item-loc">P${item.page} Q${item.question}</span>
                                <span class="item-change">${item.baseline_answer} → ${item.current_answer}</span>
                            </div>
                        `).join('')}
                        ${data.regression_count > 10 ? `<div class="more-hint">还有 ${data.regression_count - 10} 项...</div>` : ''}
                    </div>
                </div>
            </div>
        `;
        
        container.innerHTML = html;
    },
    
    async loadModelComparison(days = 30) {
        const container = document.getElementById('model-compare-container');
        if (!container) return;
        
        try {
            const resp = await fetch(`/api/batch-compare/models?days=${days}`);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error);
            }
            
            this.renderModelComparison(container, result.models);
        } catch (err) {
            container.innerHTML = `<div class="error-message">加载失败: ${err.message}</div>`;
        }
    },
    
    renderModelComparison(container, models) {
        if (!models || models.length === 0) {
            container.innerHTML = '<div class="empty-state">暂无模型数据</div>';
            return;
        }
        
        let html = '<div class="model-compare-list">';
        
        for (const model of models) {
            const trendClass = model.trend >= 0 ? 'positive' : 'negative';
            const trendIcon = model.trend >= 0 ? '↑' : '↓';
            
            html += `
                <div class="model-compare-item">
                    <div class="model-name">${model.name}</div>
                    <div class="model-stats">
                        <span class="stat-accuracy">${model.accuracy}%</span>
                        <span class="stat-count">${model.task_count} 任务</span>
                        <span class="stat-trend ${trendClass}">${trendIcon} ${Math.abs(model.trend)}%</span>
                    </div>
                    <div class="model-bar">
                        <div class="bar-fill" style="width: ${model.accuracy}%"></div>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    }
};

window.BatchCompareModule = BatchCompareModule;
