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
        
        container.innerHTML = `
            <!-- 核心指标卡片 -->
            <div class="eval-stats-card">
                <div class="eval-stats-header">
                    <div class="eval-stats-title">评估概览</div>
                    <div class="eval-stats-badge ${this.getAccuracyClass(accuracy)}">${this.getAccuracyLabel(accuracy)}</div>
                </div>
                <div class="eval-stats-body">
                    <div class="eval-stats-main">
                        <div class="eval-accuracy-display">
                            <div class="eval-accuracy-value">${accuracy.toFixed(1)}<span class="eval-accuracy-unit">%</span></div>
                            <div class="eval-accuracy-label">准确率</div>
                        </div>
                        <div class="eval-stats-counts">
                            <div class="eval-count-item">
                                <span class="eval-count-value success">${evaluation.correct_count}</span>
                                <span class="eval-count-label">正确</span>
                            </div>
                            <div class="eval-count-item">
                                <span class="eval-count-value error">${evaluation.error_count}</span>
                                <span class="eval-count-label">错误</span>
                            </div>
                            <div class="eval-count-item">
                                <span class="eval-count-value">${evaluation.total_questions}</span>
                                <span class="eval-count-label">总题数</span>
                            </div>
                        </div>
                    </div>
                    <div class="eval-stats-metrics">
                        <div class="eval-metric-item">
                            <span class="eval-metric-label">精确率</span>
                            <span class="eval-metric-value">${precision.toFixed(1)}%</span>
                        </div>
                        <div class="eval-metric-item">
                            <span class="eval-metric-label">召回率</span>
                            <span class="eval-metric-value">${recall.toFixed(1)}%</span>
                        </div>
                        <div class="eval-metric-item">
                            <span class="eval-metric-label">F1值</span>
                            <span class="eval-metric-value">${f1.toFixed(1)}%</span>
                        </div>
                        <div class="eval-metric-item ${hallucinationRate > 10 ? 'warning' : ''}">
                            <span class="eval-metric-label">幻觉率</span>
                            <span class="eval-metric-value">${hallucinationRate.toFixed(1)}%</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },
    
    // 获取准确率样式类
    getAccuracyClass(accuracy) {
        if (accuracy >= 90) return 'excellent';
        if (accuracy >= 80) return 'good';
        if (accuracy >= 60) return 'medium';
        return 'poor';
    },
    
    // 获取准确率标签
    getAccuracyLabel(accuracy) {
        if (accuracy >= 90) return '优秀';
        if (accuracy >= 80) return '良好';
        if (accuracy >= 60) return '一般';
        return '较差';
    }
};

// 导出到全局
window.StatsRenderer = StatsRenderer;
