/**
 * AI学科批改评估 - 统计卡片优化模块
 * 提供更高信息密度的统计展示
 */

// ========== 统计卡片渲染器 ==========
const StatsRenderer = {
    
    // 渲染优化后的统计卡片
    render(evaluation, container) {
        if (!container || !evaluation) return;
        
        const accuracy = evaluation.accuracy * 100;
        const precision = evaluation.precision * 100;
        const recall = evaluation.recall * 100;
        const f1 = evaluation.f1_score * 100;
        const hallucinationRate = evaluation.hallucination_rate ? evaluation.hallucination_rate * 100 : 
            (typeof calculateHallucinationRate === 'function' ? calculateHallucinationRate(evaluation) : 0);
        
        // 计算能力维度
        const dimensions = this.calculateDimensions(evaluation);
        
        container.innerHTML = `
            <!-- 核心指标卡片 -->
            <div class="stats-main-card">
                <div class="stats-main-left">
                    <div class="stats-accuracy-ring" data-value="${accuracy}">
                        <svg viewBox="0 0 100 100">
                            <circle class="ring-bg" cx="50" cy="50" r="45"/>
                            <circle class="ring-progress ${this.getAccuracyClass(accuracy)}" 
                                    cx="50" cy="50" r="45"
                                    stroke-dasharray="${accuracy * 2.83} 283"/>
                        </svg>
                        <div class="ring-value">
                            <span class="ring-number">${accuracy.toFixed(1)}</span>
                            <span class="ring-unit">%</span>
                        </div>
                        <div class="ring-label">准确率</div>
                    </div>
                </div>
                <div class="stats-main-right">
                    <div class="stats-row">
                        <div class="stats-metric">
                            <span class="stats-metric-value">${evaluation.correct_count}</span>
                            <span class="stats-metric-label">正确</span>
                        </div>
                        <div class="stats-metric">
                            <span class="stats-metric-value text-error">${evaluation.error_count}</span>
                            <span class="stats-metric-label">错误</span>
                        </div>
                        <div class="stats-metric">
                            <span class="stats-metric-value">${evaluation.total_questions}</span>
                            <span class="stats-metric-label">总题数</span>
                        </div>
                    </div>
                    <div class="stats-divider"></div>
                    <div class="stats-row">
                        <div class="stats-mini">
                            <span class="stats-mini-label">精确率</span>
                            <span class="stats-mini-value">${precision.toFixed(1)}%</span>
                        </div>
                        <div class="stats-mini">
                            <span class="stats-mini-label">召回率</span>
                            <span class="stats-mini-value">${recall.toFixed(1)}%</span>
                        </div>
                        <div class="stats-mini">
                            <span class="stats-mini-label">F1值</span>
                            <span class="stats-mini-value">${f1.toFixed(1)}%</span>
                        </div>
                        <div class="stats-mini ${hallucinationRate > 10 ? 'warning' : ''}">
                            <span class="stats-mini-label">幻觉率</span>
                            <span class="stats-mini-value">${hallucinationRate.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <!-- 能力维度条形图 -->
            <div class="stats-dimensions-card">
                <div class="stats-card-title">能力维度分析</div>
                <div class="stats-dimensions">
                    ${this.renderDimensionBar('识别能力', dimensions.recognition, '#3b82f6')}
                    ${this.renderDimensionBar('判断能力', dimensions.judgment, '#10b981')}
                    ${this.renderDimensionBar('格式规范', dimensions.format, '#f59e0b')}
                    ${this.renderDimensionBar('完整性', dimensions.completeness, '#8b5cf6')}
                    ${this.renderDimensionBar('抗幻觉', dimensions.antiHallucination, '#ef4444')}
                </div>
            </div>
            
            <!-- 错误分布卡片 -->
            ${this.renderErrorDistribution(evaluation)}
        `;
    },
    
    // 渲染维度条形图
    renderDimensionBar(label, value, color) {
        const width = Math.max(0, Math.min(100, value));
        return `
            <div class="dimension-item">
                <div class="dimension-header">
                    <span class="dimension-label">${label}</span>
                    <span class="dimension-value">${value.toFixed(0)}%</span>
                </div>
                <div class="dimension-bar">
                    <div class="dimension-bar-fill" style="width: ${width}%; background: ${color};"></div>
                </div>
            </div>
        `;
    },
    
    // 渲染错误分布
    renderErrorDistribution(evaluation) {
        const dist = evaluation.error_distribution || {};
        const total = Object.values(dist).reduce((a, b) => a + b, 0);
        
        if (total === 0) {
            return `
                <div class="stats-error-card">
                    <div class="stats-card-title">错误分布</div>
                    <div class="stats-no-error">
                        <span class="no-error-icon">✓</span>
                        <span class="no-error-text">无错误，表现完美！</span>
                    </div>
                </div>
            `;
        }
        
        const colorMap = {
            '识别错误-判断正确': '#3b82f6',
            '识别错误-判断错误': '#ef4444',
            '识别正确-判断错误': '#f59e0b',
            '格式差异': '#10b981',
            '缺失题目': '#6b7280',
            'AI幻觉': '#8b5cf6',
            '标准答案不一致': '#ec4899'
        };
        
        const items = Object.entries(dist)
            .filter(([_, count]) => count > 0)
            .sort((a, b) => b[1] - a[1]);
        
        return `
            <div class="stats-error-card">
                <div class="stats-card-title">错误分布 <span class="stats-card-subtitle">(共 ${total} 个错误)</span></div>
                <div class="stats-error-bars">
                    ${items.map(([type, count]) => {
                        const percent = (count / total * 100).toFixed(0);
                        const color = colorMap[type] || '#6b7280';
                        return `
                            <div class="error-bar-item">
                                <div class="error-bar-header">
                                    <span class="error-bar-dot" style="background: ${color};"></span>
                                    <span class="error-bar-label">${type}</span>
                                    <span class="error-bar-count">${count} (${percent}%)</span>
                                </div>
                                <div class="error-bar-track">
                                    <div class="error-bar-fill" style="width: ${percent}%; background: ${color};"></div>
                                </div>
                            </div>
                        `;
                    }).join('')}
                </div>
            </div>
        `;
    },
    
    // 计算能力维度
    calculateDimensions(evaluation) {
        const dist = evaluation.error_distribution || {};
        const total = evaluation.total_questions || 1;
        
        const recognitionErrors = (dist['识别错误-判断正确'] || 0) + (dist['识别错误-判断错误'] || 0);
        const judgmentErrors = (dist['识别正确-判断错误'] || 0) + (dist['识别错误-判断错误'] || 0);
        const formatErrors = dist['格式差异'] || 0;
        const missingErrors = dist['缺失题目'] || 0;
        const hallucinationErrors = dist['AI幻觉'] || 0;
        
        return {
            recognition: Math.max(0, 100 - (recognitionErrors / total * 100)),
            judgment: Math.max(0, 100 - (judgmentErrors / total * 100)),
            format: Math.max(0, 100 - (formatErrors / total * 100)),
            completeness: Math.max(0, 100 - (missingErrors / total * 100)),
            antiHallucination: Math.max(0, 100 - (hallucinationErrors / total * 100))
        };
    },
    
    // 获取准确率样式类
    getAccuracyClass(accuracy) {
        if (accuracy >= 90) return 'excellent';
        if (accuracy >= 80) return 'good';
        if (accuracy >= 60) return 'medium';
        return 'poor';
    }
};

// 导出到全局
window.StatsRenderer = StatsRenderer;
