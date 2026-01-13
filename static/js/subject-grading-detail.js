/**
 * AI学科批改评估 - 详细分析视图模块
 * 展示 detailed_analysis 数据的完整视图
 */

// ========== 详细分析视图 ==========
const DetailedAnalysis = {
    currentData: null,
    currentFilter: 'all',
    currentSort: { column: 'index', order: 'asc' },
    
    // 设置数据
    setData(evaluation) {
        this.currentData = evaluation?.detailed_analysis || evaluation?.errors || [];
        this.currentFilter = 'all';
    },
    
    // 渲染详细分析视图
    render(container) {
        if (!container) return;
        
        const data = this.getFilteredData();
        
        if (!data || data.length === 0) {
            container.innerHTML = `
                <div class="detail-empty">
                    <div class="detail-empty-icon">📋</div>
                    <div class="detail-empty-text">暂无详细分析数据</div>
                </div>
            `;
            return;
        }
        
        container.innerHTML = `
            <div class="detail-toolbar">
                <div class="detail-filters">
                    <button class="detail-filter-btn ${this.currentFilter === 'all' ? 'active' : ''}" 
                            onclick="DetailedAnalysis.filter('all')">全部 (${this.currentData.length})</button>
                    <button class="detail-filter-btn ${this.currentFilter === 'correct' ? 'active' : ''}" 
                            onclick="DetailedAnalysis.filter('correct')">正确</button>
                    <button class="detail-filter-btn ${this.currentFilter === 'error' ? 'active' : ''}" 
                            onclick="DetailedAnalysis.filter('error')">错误</button>
                    <button class="detail-filter-btn ${this.currentFilter === 'high' ? 'active' : ''}" 
                            onclick="DetailedAnalysis.filter('high')">高严重</button>
                </div>
                <div class="detail-actions">
                    <button class="btn btn-small" onclick="DetailedAnalysis.expandAll()">展开全部</button>
                    <button class="btn btn-small" onclick="DetailedAnalysis.collapseAll()">收起全部</button>
                </div>
            </div>
            <div class="detail-list" id="detailList">
                ${data.map((item, idx) => this.renderItem(item, idx)).join('')}
            </div>
        `;
    },
    
    // 渲染单个分析项
    renderItem(item, idx) {
        const isCorrect = item.is_correct !== false && !item.error_type;
        const severityClass = this.getSeverityClass(item.severity_code || item.severity);
        const statusIcon = isCorrect ? '✓' : '✗';
        const statusClass = isCorrect ? 'correct' : 'error';
        
        // 基准效果数据
        const base = item.base_effect || {};
        const ai = item.ai_result || {};
        const analysis = item.analysis || {};
        
        return `
            <div class="detail-item ${statusClass}" data-index="${idx}">
                <div class="detail-item-header" onclick="DetailedAnalysis.toggleItem(${idx})">
                    <div class="detail-item-left">
                        <span class="detail-item-status ${statusClass}">${statusIcon}</span>
                        <span class="detail-item-index">第 ${item.index || idx + 1} 题</span>
                        ${!isCorrect ? `<span class="detail-item-type tag tag-${this.getErrorTypeClass(item.error_type)}">${item.error_type || '错误'}</span>` : ''}
                        ${!isCorrect ? `<span class="detail-item-severity severity-${severityClass}">${item.severity || '中'}</span>` : ''}
                    </div>
                    <div class="detail-item-right">
                        <span class="detail-item-toggle">▼</span>
                    </div>
                </div>
                <div class="detail-item-body" style="display: none;">
                    <div class="detail-compare-grid">
                        <div class="detail-compare-col">
                            <div class="detail-compare-title">基准效果</div>
                            <div class="detail-compare-content">
                                <div class="detail-field">
                                    <span class="detail-field-label">标准答案</span>
                                    <span class="detail-field-value">${escapeHtml(base.answer || '-')}</span>
                                </div>
                                <div class="detail-field">
                                    <span class="detail-field-label">用户答案</span>
                                    <span class="detail-field-value highlight">${escapeHtml(base.userAnswer || '-')}</span>
                                </div>
                                <div class="detail-field">
                                    <span class="detail-field-label">判断结果</span>
                                    <span class="detail-field-value ${base.correct === 'yes' ? 'text-success' : 'text-error'}">
                                        ${base.correct === 'yes' ? '✓ 正确' : base.correct === 'no' ? '✗ 错误' : '-'}
                                    </span>
                                </div>
                            </div>
                        </div>
                        <div class="detail-compare-arrow">→</div>
                        <div class="detail-compare-col">
                            <div class="detail-compare-title">AI批改结果</div>
                            <div class="detail-compare-content">
                                <div class="detail-field">
                                    <span class="detail-field-label">标准答案</span>
                                    <span class="detail-field-value ${ai.answer !== base.answer ? 'text-warning' : ''}">${escapeHtml(ai.answer || '-')}</span>
                                </div>
                                <div class="detail-field">
                                    <span class="detail-field-label">用户答案</span>
                                    <span class="detail-field-value highlight ${ai.userAnswer !== base.userAnswer ? 'text-error' : ''}">${escapeHtml(ai.userAnswer || '-')}</span>
                                </div>
                                <div class="detail-field">
                                    <span class="detail-field-label">判断结果</span>
                                    <span class="detail-field-value ${ai.correct === 'yes' ? 'text-success' : 'text-error'} ${ai.correct !== base.correct ? 'text-warning' : ''}">
                                        ${ai.correct === 'yes' ? '✓ 正确' : ai.correct === 'no' ? '✗ 错误' : '-'}
                                    </span>
                                </div>
                            </div>
                        </div>
                    </div>
                    
                    ${!isCorrect ? `
                    <div class="detail-analysis-section">
                        <div class="detail-analysis-title">分析结果</div>
                        <div class="detail-analysis-badges">
                            ${analysis.recognition_match !== undefined ? `
                                <span class="analysis-badge ${analysis.recognition_match ? 'badge-success' : 'badge-error'}">
                                    识别 ${analysis.recognition_match ? '✓ 一致' : '✗ 不一致'}
                                </span>
                            ` : ''}
                            ${analysis.judgment_match !== undefined ? `
                                <span class="analysis-badge ${analysis.judgment_match ? 'badge-success' : 'badge-error'}">
                                    判断 ${analysis.judgment_match ? '✓ 一致' : '✗ 不一致'}
                                </span>
                            ` : ''}
                            ${analysis.is_hallucination ? `
                                <span class="analysis-badge badge-warning">⚠ AI幻觉</span>
                            ` : ''}
                        </div>
                        ${item.explanation ? `
                            <div class="detail-explanation">
                                <strong>说明：</strong>${escapeHtml(item.explanation)}
                            </div>
                        ` : ''}
                        ${item.suggestion ? `
                            <div class="detail-suggestion">
                                <strong>💡 建议：</strong>${escapeHtml(item.suggestion)}
                            </div>
                        ` : ''}
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    },
    
    // 获取筛选后的数据
    getFilteredData() {
        if (!this.currentData) return [];
        
        switch (this.currentFilter) {
            case 'correct':
                return this.currentData.filter(item => item.is_correct !== false && !item.error_type);
            case 'error':
                return this.currentData.filter(item => item.is_correct === false || item.error_type);
            case 'high':
                return this.currentData.filter(item => 
                    (item.severity_code === 'high' || item.severity === '高') && 
                    (item.is_correct === false || item.error_type)
                );
            default:
                return this.currentData;
        }
    },
    
    // 筛选
    filter(type) {
        this.currentFilter = type;
        const container = document.getElementById('detailedAnalysisContainer');
        if (container) this.render(container);
    },
    
    // 切换展开/收起
    toggleItem(idx) {
        const item = document.querySelector(`.detail-item[data-index="${idx}"]`);
        if (!item) return;
        
        const body = item.querySelector('.detail-item-body');
        const toggle = item.querySelector('.detail-item-toggle');
        
        if (body.style.display === 'none') {
            body.style.display = 'block';
            toggle.textContent = '▲';
            item.classList.add('expanded');
        } else {
            body.style.display = 'none';
            toggle.textContent = '▼';
            item.classList.remove('expanded');
        }
    },
    
    // 展开全部
    expandAll() {
        document.querySelectorAll('.detail-item').forEach(item => {
            const body = item.querySelector('.detail-item-body');
            const toggle = item.querySelector('.detail-item-toggle');
            if (body) body.style.display = 'block';
            if (toggle) toggle.textContent = '▲';
            item.classList.add('expanded');
        });
    },
    
    // 收起全部
    collapseAll() {
        document.querySelectorAll('.detail-item').forEach(item => {
            const body = item.querySelector('.detail-item-body');
            const toggle = item.querySelector('.detail-item-toggle');
            if (body) body.style.display = 'none';
            if (toggle) toggle.textContent = '▼';
            item.classList.remove('expanded');
        });
    },
    
    // 获取严重程度样式类
    getSeverityClass(severity) {
        const map = {
            'high': 'high', 'medium': 'medium', 'low': 'low',
            '高': 'high', '中': 'medium', '低': 'low'
        };
        return map[severity] || 'medium';
    },
    
    // 获取错误类型样式类
    getErrorTypeClass(errorType) {
        const typeMap = {
            '识别错误-判断正确': 'info',
            '识别错误-判断错误': 'error',
            '识别正确-判断错误': 'warning',
            '格式差异': 'success',
            '缺失题目': 'default',
            'AI幻觉': 'purple',
            '标准答案不一致': 'orange'
        };
        return typeMap[errorType] || 'default';
    }
};

// 导出到全局
window.DetailedAnalysis = DetailedAnalysis;
