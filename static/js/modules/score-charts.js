/**
 * 分数相关图表模块
 * 包含：题型分数准确率对比、判分准确率
 */

// 图表实例存储
const scoreChartInstances = {
    questionTypeAccuracy: null
};

/**
 * 渲染分数相关图表
 * @param {Object} report - 评估报告（包含 by_question_type 等统计数据）
 * @param {Array} completedItems - 已完成的作业项
 */
function renderScoreCharts(report, completedItems) {
    const newChartsGrid = document.getElementById('newChartsGrid');
    if (!newChartsGrid) return;
    
    // 检查是否有分数数据（使用后端返回的 has_score 字段）
    const hasScoreData = report?.has_score || checkHasScoreDataFromItems(completedItems);
    if (!hasScoreData) {
        newChartsGrid.style.display = 'none';
        return;
    }
    
    newChartsGrid.style.display = 'grid';
    destroyScoreCharts();
    
    // 1. 题型分数准确率对比
    renderQuestionTypeScoreChart(report, completedItems);
    
    // 2. 判分准确率图表（使用新模块）
    if (window.ScoreAccuracy) {
        window.ScoreAccuracy.render(report, completedItems);
    }
}

/**
 * 销毁图表实例
 */
function destroyScoreCharts() {
    Object.keys(scoreChartInstances).forEach(key => {
        if (scoreChartInstances[key]) {
            scoreChartInstances[key].destroy();
            scoreChartInstances[key] = null;
        }
    });
    // 销毁判分准确率图表
    if (window.ScoreAccuracy) {
        window.ScoreAccuracy.destroy();
    }
}

/**
 * 渲染题型分数准确率对比（水平柱状图）
 * 使用后端计算的 by_question_type.score_accuracy 数据
 */
function renderQuestionTypeScoreChart(report, completedItems) {
    const canvas = document.getElementById('questionTypeAccuracyChart');
    if (!canvas) return;
    
    const typeNames = { choice: '选择题', objective_fill: '客观填空', subjective: '主观题' };
    const labels = [];
    const accuracyData = [];
    const totalData = [];
    
    // 优先使用后端返回的 by_question_type 统计数据
    const byQuestionType = report?.by_question_type;
    
    console.log('[ScoreCharts] report.by_question_type:', byQuestionType);
    console.log('[ScoreCharts] report.has_score:', report?.has_score);
    
    if (byQuestionType && Object.keys(byQuestionType).length > 0) {
        // 使用后端数据 - 优先使用分数准确率
        ['choice', 'objective_fill', 'subjective'].forEach(type => {
            const stats = byQuestionType[type];
            // 只显示有分数数据的题型
            if (stats && stats.score_total > 0) {
                labels.push(typeNames[type]);
                // 使用分数准确率（score_accuracy）
                const accuracy = (stats.score_accuracy * 100).toFixed(1);
                accuracyData.push(accuracy);
                totalData.push(stats.score_total);
            }
        });
        console.log('[ScoreCharts] 使用分数准确率数据, labels:', labels, 'accuracyData:', accuracyData);
    } else {
        // 降级：从 completedItems 计算（仅用于兼容旧数据）
        const scoreData = collectScoreDataByType(completedItems);
        ['choice', 'objective_fill', 'subjective'].forEach(type => {
            const stats = scoreData[type];
            if (stats && stats.total > 0) {
                labels.push(typeNames[type]);
                const accuracy = (stats.correct / stats.total * 100).toFixed(1);
                accuracyData.push(accuracy);
                totalData.push(stats.total);
            }
        });
        console.log('[ScoreCharts] 降级计算, labels:', labels, 'accuracyData:', accuracyData);
    }
    
    if (labels.length === 0) {
        showEmptyChart(canvas, '暂无题型分数数据');
        return;
    }
    
    const colors = ['#3b82f6', '#10b981', '#f59e0b'];
    const backgroundColors = labels.map((_, i) => colors[i % colors.length]);
    
    scoreChartInstances.questionTypeAccuracy = new Chart(canvas, {
        type: 'bar',
        data: {
            labels: labels,
            datasets: [{
                label: '分数准确率',
                data: accuracyData,
                backgroundColor: backgroundColors,
                borderRadius: 6,
                barThickness: 32
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            indexAxis: 'y',
            scales: {
                x: {
                    beginAtZero: true,
                    max: 100,
                    ticks: { 
                        font: { size: 11 }, 
                        color: '#86868b',
                        callback: v => v + '%'
                    },
                    grid: { color: '#f0f0f2' }
                },
                y: {
                    ticks: { font: { size: 13, weight: 500 }, color: '#1d1d1f' },
                    grid: { display: false }
                }
            },
            plugins: {
                legend: { display: false },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            const total = totalData[context.dataIndex];
                            return `分数准确率: ${context.parsed.x}% (共${total}题)`;
                        }
                    }
                }
            }
        }
    });
}

// ========== 辅助函数 ==========

/**
 * 显示空图表提示
 */
function showEmptyChart(canvas, message) {
    const ctx = canvas.getContext('2d');
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    ctx.font = '14px sans-serif';
    ctx.fillStyle = '#86868b';
    ctx.textAlign = 'center';
    ctx.fillText(message, canvas.width / 2, canvas.height / 2);
}

/**
 * 检查是否有分数数据（从 items 检查）
 * 优先检查 homework_result 和 data_value 中的分数字段
 */
function checkHasScoreDataFromItems(completedItems) {
    for (const item of completedItems) {
        // 优先从 homework_result 和 data_value 检查
        try {
            const aiResults = typeof item.homework_result === 'string' 
                ? JSON.parse(item.homework_result) 
                : (item.homework_result || []);
            const baseData = typeof item.data_value === 'string' 
                ? JSON.parse(item.data_value) 
                : (item.data_value || []);
            
            // 检查是否有分数数据
            for (const q of aiResults) {
                if (q.score !== undefined && q.score !== null) {
                    return true;
                }
            }
            for (const q of baseData) {
                if (q.score !== undefined && q.score !== null) {
                    return true;
                }
            }
        } catch (e) {
            // 解析失败，继续检查 errors
        }
        
        // 降级：检查 errors
        const errors = item.evaluation?.errors || [];
        for (const err of errors) {
            if (err.base_effect?.score !== undefined && err.base_effect?.score !== null) {
                return true;
            }
        }
    }
    return false;
}

/**
 * 从 completedItems 收集分数数据（降级方案）
 */
function collectScoreDataByType(completedItems) {
    const typeStats = {
        choice: { total: 0, correct: 0 },
        objective_fill: { total: 0, correct: 0 },
        subjective: { total: 0, correct: 0 }
    };
    
    completedItems.forEach(item => {
        const errors = item.evaluation?.errors || [];
        errors.forEach(err => {
            const baseEffect = err.base_effect || {};
            const aiResult = err.ai_result || {};
            
            if (baseEffect.score !== undefined && baseEffect.score !== null) {
                const baseScore = parseFloat(baseEffect.score) || 0;
                const aiScore = aiResult.score !== undefined && aiResult.score !== null 
                    ? parseFloat(aiResult.score) : null;
                
                const questionType = classifyQuestionTypeForScore(baseEffect, err.question_category);
                
                if (typeStats[questionType]) {
                    typeStats[questionType].total++;
                    if (aiScore !== null && Math.abs(aiScore - baseScore) < 0.01) {
                        typeStats[questionType].correct++;
                    }
                }
            }
        });
    });
    
    return typeStats;
}

/**
 * 判断题型分类
 */
function classifyQuestionTypeForScore(baseEffect, questionCategory) {
    if (questionCategory) {
        if (questionCategory.is_choice) return 'choice';
        if (questionCategory.is_fill) return 'objective_fill';
        if (questionCategory.is_subjective) return 'subjective';
    }
    
    const bvalue = String(baseEffect?.bvalue || '');
    const qtype = baseEffect?.questionType || '';
    
    if (['1', '2', '3'].includes(bvalue)) return 'choice';
    if (qtype === 'objective' && bvalue === '4') return 'objective_fill';
    return 'subjective';
}

// 导出供外部使用
window.ScoreCharts = {
    render: renderScoreCharts,
    destroy: destroyScoreCharts
};
