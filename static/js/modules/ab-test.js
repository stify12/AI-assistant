/**
 * A/B测试对比分析模块 (US-17)
 */
const ABTestModule = {
    async compare(taskId1, taskId2) {
        const container = document.getElementById('ab-test-container');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">对比分析中...</div>';
        
        try {
            const resp = await fetch(`/api/analysis/ab-compare?task1=${taskId1}&task2=${taskId2}`);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error || '对比失败');
            }
            
            this.render(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">对比失败: ${err.message}</div>`;
        }
    },
    
    render(container, data) {
        const t1 = data.task1 || {};
        const t2 = data.task2 || {};
        const diff = data.diff || {};
        
        const winnerClass = diff.accuracy_diff > 0 ? 'winner-right' : diff.accuracy_diff < 0 ? 'winner-left' : '';
        
        let html = `
            <div class="ab-compare-header">
                <div class="ab-task ${diff.accuracy_diff < 0 ? 'winner' : ''}">
                    <div class="task-label">任务 A</div>
                    <div class="task-name">${this.escapeHtml(t1.name || t1.task_id)}</div>
                    <div class="task-accuracy">${((t1.accuracy || 0) * 100).toFixed(1)}%</div>
                    <div class="task-meta">${t1.total_questions || 0} 题</div>
                </div>
                <div class="ab-vs">VS</div>
                <div class="ab-task ${diff.accuracy_diff > 0 ? 'winner' : ''}">
                    <div class="task-label">任务 B</div>
                    <div class="task-name">${this.escapeHtml(t2.name || t2.task_id)}</div>
                    <div class="task-accuracy">${((t2.accuracy || 0) * 100).toFixed(1)}%</div>
                    <div class="task-meta">${t2.total_questions || 0} 题</div>
                </div>
            </div>
            
            <div class="ab-diff-summary">
                <div class="diff-item">
                    <span class="diff-label">准确率差异</span>
                    <span class="diff-value ${diff.accuracy_diff >= 0 ? 'positive' : 'negative'}">
                        ${diff.accuracy_diff >= 0 ? '+' : ''}${(diff.accuracy_diff * 100).toFixed(2)}%
                    </span>
                </div>
                <div class="diff-item">
                    <span class="diff-label">共同题目</span>
                    <span class="diff-value">${diff.common_questions || 0}</span>
                </div>
                <div class="diff-item">
                    <span class="diff-label">结果一致</span>
                    <span class="diff-value">${diff.same_results || 0}</span>
                </div>
            </div>
        `;
        
        // 差异详情
        if (diff.differences && diff.differences.length > 0) {
            html += `
                <div class="ab-diff-details">
                    <div class="section-title">结果差异 (${diff.differences.length})</div>
                    <div class="diff-list">
            `;
            
            for (const d of diff.differences.slice(0, 20)) {
                const aCorrect = d.task1_correct;
                const bCorrect = d.task2_correct;
                
                html += `
                    <div class="diff-row">
                        <span class="diff-question">${this.escapeHtml(d.question || d.question_number)}</span>
                        <span class="diff-result ${aCorrect ? 'correct' : 'wrong'}">${aCorrect ? '正确' : '错误'}</span>
                        <span class="diff-arrow">→</span>
                        <span class="diff-result ${bCorrect ? 'correct' : 'wrong'}">${bCorrect ? '正确' : '错误'}</span>
                    </div>
                `;
            }
            
            if (diff.differences.length > 20) {
                html += `<div class="more-hint">还有 ${diff.differences.length - 20} 项差异...</div>`;
            }
            
            html += '</div></div>';
        }
        
        container.innerHTML = html;
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[m]));
    }
};

window.ABTestModule = ABTestModule;
