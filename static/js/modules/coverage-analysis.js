/**
 * AI测试覆盖率分析模块 (US-12)
 */
const CoverageAnalysisModule = {
    data: null,
    
    async load() {
        const container = document.getElementById('coverage-container');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">加载中...</div>';
        
        try {
            const resp = await fetch('/api/analysis/coverage');
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error || '加载失败');
            }
            
            this.data = result;
            this.render(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">加载失败: ${err.message}</div>`;
        }
    },
    
    render(container, data) {
        const coverage = data.coverage || {};
        const bySubject = data.by_subject || [];
        const uncovered = data.uncovered || [];
        
        let html = `
            <div class="coverage-summary">
                <div class="coverage-stat">
                    <div class="stat-value">${(coverage.overall * 100).toFixed(1)}%</div>
                    <div class="stat-label">总体覆盖率</div>
                </div>
                <div class="coverage-stat">
                    <div class="stat-value">${coverage.tested_count || 0}</div>
                    <div class="stat-label">已测试题目</div>
                </div>
                <div class="coverage-stat">
                    <div class="stat-value">${coverage.total_count || 0}</div>
                    <div class="stat-label">总题目数</div>
                </div>
            </div>
            
            <div class="coverage-section">
                <div class="section-title">学科覆盖率</div>
                <div class="coverage-bars">
        `;
        
        for (const subject of bySubject) {
            const pct = (subject.coverage * 100).toFixed(1);
            const barClass = subject.coverage >= 0.8 ? 'high' : subject.coverage >= 0.5 ? 'medium' : 'low';
            
            html += `
                <div class="coverage-bar-item">
                    <div class="bar-label">${this.escapeHtml(subject.name)}</div>
                    <div class="bar-track">
                        <div class="bar-fill ${barClass}" style="width: ${pct}%"></div>
                    </div>
                    <div class="bar-value">${pct}%</div>
                </div>
            `;
        }
        
        html += `
                </div>
            </div>
        `;
        
        // 未覆盖区域
        if (uncovered.length > 0) {
            html += `
                <div class="coverage-section">
                    <div class="section-title">未覆盖区域 (${uncovered.length})</div>
                    <div class="uncovered-list">
            `;
            
            for (const item of uncovered.slice(0, 10)) {
                html += `
                    <div class="uncovered-item">
                        <span class="item-name">${this.escapeHtml(item.name || item.book_name)}</span>
                        <span class="item-count">${item.question_count || 0} 题未测试</span>
                    </div>
                `;
            }
            
            if (uncovered.length > 10) {
                html += `<div class="more-hint">还有 ${uncovered.length - 10} 项...</div>`;
            }
            
            html += `
                    </div>
                </div>
            `;
        }
        
        container.innerHTML = html;
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }
};

window.CoverageAnalysisModule = CoverageAnalysisModule;
