/**
 * 判分准确率图表模块
 * 展示：准确率、偏高/偏低统计
 * 数据来源：后端 overall_report.score_accuracy_stats
 */

// 图表实例
let scoreAccuracyChartInstance = null;

/**
 * 渲染判分准确率图表
 * @param {Object} report - 评估报告（包含 score_accuracy_stats）
 * @param {Array} completedItems - 已完成的作业项（备用）
 */
function renderScoreAccuracyChart(report, completedItems) {
    const container = document.getElementById('scoreAccuracyChartContainer');
    if (!container) return;
    
    // 检查是否有分数数据
    const hasScoreData = report?.has_score || false;
    if (!hasScoreData) {
        container.style.display = 'none';
        return;
    }
    
    container.style.display = 'block';
    destroyScoreAccuracyChart();
    
    // 优先从 report.score_accuracy_stats 获取后端计算的统计数据
    let stats = report?.score_accuracy_stats;
    
    // 如果后端没有统计数据，尝试从 completedItems 计算（兼容旧数据）
    if (!stats || stats.total === 0) {
        stats = calculateScoreAccuracyStats(completedItems);
    }
    
    // 补充计算派生字段
    stats = enrichStats(stats);
    
    if (stats.total === 0) {
        showEmptyScoreChart('暂无判分数据');
        return;
    }
    
    renderAccuracyDoughnutChart(stats);
    renderScoreDeviationSummary(stats);
}

/**
 * 补充计算派生字段（准确率、平均分差等）
 */
function enrichStats(stats) {
    if (!stats) return { total: 0, accurate: 0, higher: 0, lower: 0 };
    
    const total = stats.total || 0;
    const accurate = stats.accurate || 0;
    const higher = stats.higher || 0;
    const lower = stats.lower || 0;
    const higherSum = stats.higher_sum || 0;
    const lowerSum = stats.lower_sum || 0;
    
    return {
        ...stats,
        total,
        accurate,
        higher,
        lower,
        accuracyRate: total > 0 ? (accurate / total * 100) : 0,
        higherRate: total > 0 ? (higher / total * 100) : 0,
        lowerRate: total > 0 ? (lower / total * 100) : 0,
        avgHigherDiff: higher > 0 ? (higherSum / higher) : 0,
        avgLowerDiff: lower > 0 ? (lowerSum / lower) : 0
    };
}

/**
 * 计算判分准确率统计（兼容旧数据，从 completedItems 计算）
 * 从 homework_result 和 data_value 中获取所有题目的分数进行比对
 */
function calculateScoreAccuracyStats(completedItems) {
    let total = 0;
    let accurate = 0;
    let higher = 0;
    let lower = 0;
    let higherSum = 0;
    let lowerSum = 0;
    
    if (!completedItems || !Array.isArray(completedItems)) {
        return { total, accurate, higher, lower, higher_sum: higherSum, lower_sum: lowerSum };
    }
    
    completedItems.forEach(item => {
        // 从 evaluation.score_accuracy_stats 获取（如果有）
        const evaluation = item.evaluation || {};
        const scoreStats = evaluation.score_accuracy_stats;
        
        if (scoreStats && scoreStats.total > 0) {
            total += scoreStats.total || 0;
            accurate += scoreStats.accurate || 0;
            higher += scoreStats.higher || 0;
            lower += scoreStats.lower || 0;
            higherSum += scoreStats.higher_sum || 0;
            lowerSum += scoreStats.lower_sum || 0;
        }
    });
    
    return { total, accurate, higher, lower, higher_sum: higherSum, lower_sum: lowerSum };
}

/**
 * 渲染准确率环形图
 */
function renderAccuracyDoughnutChart(stats) {
    const canvas = document.getElementById('scoreAccuracyChart');
    if (!canvas) return;
    
    const data = [stats.accurate, stats.higher, stats.lower];
    const labels = ['分数一致', '偏高', '偏低'];
    const colors = ['#10b981', '#f59e0b', '#ef4444'];
    
    scoreAccuracyChartInstance = new Chart(canvas, {
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
            maintainAspectRatio: false,
            cutout: '60%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { 
                        padding: 12, 
                        font: { size: 12 }, 
                        color: '#1d1d1f', 
                        boxWidth: 12 
                    }
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const value = context.parsed || 0;
                            const percentage = ((value / stats.total) * 100).toFixed(1);
                            return `${context.label}: ${value}题 (${percentage}%)`;
                        }
                    }
                }
            }
        }
    });
}

/**
 * 渲染分差摘要信息（右侧统计区域）
 */
function renderScoreDeviationSummary(stats) {
    const summaryEl = document.getElementById('scoreAccuracySummary');
    if (!summaryEl) return;
    
    summaryEl.innerHTML = `
        <div class="accuracy-summary">
            <div class="accuracy-main">
                <span class="accuracy-value">${stats.accuracyRate.toFixed(1)}%</span>
                <span class="accuracy-label">判分准确率</span>
            </div>
            <div class="accuracy-details">
                <div class="detail-item">
                    <span class="detail-label">总题数</span>
                    <span class="detail-value">${stats.total}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">一致</span>
                    <span class="detail-value">${stats.accurate}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">偏高</span>
                    <span class="detail-value">${stats.higher}</span>
                    ${stats.higher > 0 ? `<span class="detail-sub">平均+${stats.avgHigherDiff.toFixed(1)}分</span>` : ''}
                </div>
                <div class="detail-item">
                    <span class="detail-label">偏低</span>
                    <span class="detail-value">${stats.lower}</span>
                    ${stats.lower > 0 ? `<span class="detail-sub">平均-${stats.avgLowerDiff.toFixed(1)}分</span>` : ''}
                </div>
            </div>
        </div>
    `;
}

/**
 * 显示空图表提示
 */
function showEmptyScoreChart(message) {
    const canvas = document.getElementById('scoreAccuracyChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = '14px sans-serif';
    ctx.fillStyle = '#86868b';
    ctx.textAlign = 'center';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

/**
 * 销毁图表实例
 */
function destroyScoreAccuracyChart() {
    if (scoreAccuracyChartInstance) {
        scoreAccuracyChartInstance.destroy();
        scoreAccuracyChartInstance = null;
    }
}

// 导出供外部使用
window.ScoreAccuracy = {
    render: renderScoreAccuracyChart,
    destroy: destroyScoreAccuracyChart,
    calculateStats: calculateScoreAccuracyStats
};
