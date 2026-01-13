/**
 * AI学科批改评估 - 增强功能
 * 包含：数据摘要、表格筛选排序、图表交互、幻觉率计算等
 */

// 全局变量
let currentErrorData = [];
let currentSortColumn = '';
let currentSortOrder = 'asc';
let accuracyHistory = []; // 准确率历史记录

// ========== 生成数据摘要（黑白简洁风格） ==========
function generateSummary(evaluation) {
    const accuracy = (evaluation.accuracy * 100).toFixed(1);
    const total = evaluation.total_questions;
    const correct = evaluation.correct_count;
    const errors = evaluation.error_count;
    
    // 计算幻觉率
    const hallucinationRate = calculateHallucinationRate(evaluation);
    
    // 获取最大错误类型
    const errorDist = evaluation.error_distribution || {};
    let maxErrorType = '';
    let maxErrorCount = 0;
    Object.keys(errorDist).forEach(type => {
        if (errorDist[type] > maxErrorCount) {
            maxErrorType = type;
            maxErrorCount = errorDist[type];
        }
    });
    
    // 简洁的摘要文本
    let summary = `共 ${total} 题 | 正确 ${correct} | 错误 ${errors} | 准确率 ${accuracy}%`;
    
    if (hallucinationRate > 0) {
        summary += ` | 幻觉率 ${hallucinationRate.toFixed(1)}%`;
    }
    
    if (maxErrorCount > 0) {
        summary += ` | 主要问题: ${maxErrorType} (${maxErrorCount}题)`;
    }
    
    return summary;
}

// ========== 计算幻觉率 ==========
// 幻觉率：实际手写答案错误，但AI自己推理出来正确答案的比例
// 即：基准效果中userAnswer错误(correct=no)，但AI识别的userAnswer与标准答案一致
function calculateHallucinationRate(evaluation) {
    if (!evaluation.errors || evaluation.errors.length === 0) return 0;
    
    let hallucinationCount = 0;
    let totalWrongAnswers = 0;
    
    evaluation.errors.forEach(err => {
        const baseEffect = err.base_effect || {};
        const aiResult = err.ai_result || {};
        
        // 基准效果中用户答案是错误的
        if (baseEffect.correct === 'no') {
            totalWrongAnswers++;
            
            // AI识别的答案与标准答案一致（AI产生了幻觉，自己推理出了正确答案）
            const standardAnswer = normalizeAnswer(baseEffect.answer || '');
            const aiUserAnswer = normalizeAnswer(aiResult.userAnswer || '');
            
            if (standardAnswer && aiUserAnswer && standardAnswer === aiUserAnswer) {
                hallucinationCount++;
            }
        }
    });
    
    // 也检查正确的题目中是否有幻觉（需要从完整数据中获取）
    // 这里只能从错误列表中计算，完整计算需要后端支持
    
    if (totalWrongAnswers === 0) return 0;
    return (hallucinationCount / totalWrongAnswers) * 100;
}

// ========== 标准化答案用于比较 ==========
function normalizeAnswer(answer) {
    if (!answer) return '';
    return String(answer).trim().toLowerCase().replace(/\s+/g, '');
}

// ========== 生成关键发现（已废弃，保留空函数） ==========
function generateInsights(evaluation) {
    return [];
}

// ========== 渲染数据摘要（黑白简洁风格） ==========
function renderSummary(evaluation) {
    const summaryCard = document.getElementById('summaryCard');
    const summaryContent = document.getElementById('summaryContent');
    
    if (!summaryCard || !summaryContent) return;
    
    const summary = generateSummary(evaluation);
    summaryContent.innerHTML = summary;
    summaryCard.style.display = 'flex';
}

// ========== 关键发现已删除，保留空函数以兼容 ==========
function renderInsights(evaluation) {
    const container = document.getElementById('insightsContainer');
    if (container) {
        container.style.display = 'none';
    }
}

// ========== 填充错误类型筛选器 ==========
function populateErrorTypeFilter(errors) {
    const select = document.getElementById('errorTypeFilter');
    if (!select) return;
    
    // 获取所有错误类型
    const types = new Set();
    errors.forEach(err => {
        if (err.error_type) {
            types.add(err.error_type);
        }
    });
    
    // 清空并重新填充
    select.innerHTML = '<option value="">全部错误类型</option>';
    Array.from(types).sort().forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = type;
        select.appendChild(option);
    });
}

// ========== 筛选错误表格 ==========
function filterErrorTable() {
    const typeFilter = document.getElementById('errorTypeFilter')?.value || '';
    const searchText = document.getElementById('errorSearchInput')?.value.toLowerCase() || '';
    
    const tbody = document.getElementById('errorTableBody');
    if (!tbody) return;
    
    const rows = tbody.getElementsByTagName('tr');
    
    for (let row of rows) {
        const errorType = row.getAttribute('data-error-type') || '';
        const index = row.getAttribute('data-index') || '';
        
        const typeMatch = !typeFilter || errorType === typeFilter;
        const searchMatch = !searchText || index.toLowerCase().includes(searchText);
        
        row.style.display = (typeMatch && searchMatch) ? '' : 'none';
    }
}

// ========== 排序错误表格 ==========
function sortErrorTable(column) {
    const tbody = document.getElementById('errorTableBody');
    if (!tbody) return;
    
    // 切换排序顺序
    if (currentSortColumn === column) {
        currentSortOrder = currentSortOrder === 'asc' ? 'desc' : 'asc';
    } else {
        currentSortColumn = column;
        currentSortOrder = 'asc';
    }
    
    // 获取所有行
    const rows = Array.from(tbody.getElementsByTagName('tr'));
    
    // 排序
    rows.sort((a, b) => {
        let aVal, bVal;
        
        if (column === 'index') {
            aVal = parseInt(a.getAttribute('data-index')) || 0;
            bVal = parseInt(b.getAttribute('data-index')) || 0;
        } else if (column === 'type') {
            aVal = a.getAttribute('data-error-type') || '';
            bVal = b.getAttribute('data-error-type') || '';
        }
        
        if (currentSortOrder === 'asc') {
            return aVal > bVal ? 1 : -1;
        } else {
            return aVal < bVal ? 1 : -1;
        }
    });
    
    // 重新插入
    rows.forEach(row => tbody.appendChild(row));
}

// ========== 饼图点击筛选 ==========
function setupPieChartFilter(chartInstance) {
    if (!chartInstance) return;
    
    const canvas = document.getElementById('errorPieChart');
    if (!canvas) return;
    
    canvas.onclick = function(evt) {
        const points = chartInstance.getElementsAtEventForMode(evt, 'nearest', { intersect: true }, true);
        
        if (points.length) {
            const firstPoint = points[0];
            const label = chartInstance.data.labels[firstPoint.index];
            
            // 提取错误类型（去除数量和百分比）
            const errorType = label.split('(')[0].trim();
            
            // 设置筛选器
            const select = document.getElementById('errorTypeFilter');
            if (select) {
                select.value = errorType;
                filterErrorTable();
                
                // 滚动到错误表格
                document.getElementById('errorTableContainer')?.scrollIntoView({ behavior: 'smooth' });
            }
        }
    };
    
    // 添加鼠标样式
    canvas.style.cursor = 'pointer';
}

// 导出函数供全局使用
window.renderSummary = renderSummary;
window.renderInsights = renderInsights;
window.populateErrorTypeFilter = populateErrorTypeFilter;
window.filterErrorTable = filterErrorTable;
window.sortErrorTable = sortErrorTable;
window.setupPieChartFilter = setupPieChartFilter;
window.calculateHallucinationRate = calculateHallucinationRate;
window.normalizeAnswer = normalizeAnswer;
