/**
 * AI学科批改评估 - 批量评估模块
 * 支持多选记录进行批量评估
 */

// ========== 批量评估状态 ==========
const BatchEvaluation = {
    enabled: false,
    selectedItems: new Set(),
    results: [],
    
    // 切换批量模式
    toggle() {
        this.enabled = !this.enabled;
        this.selectedItems.clear();
        this.results = [];
        this.updateUI();
        renderHomeworkList();
    },
    
    // 更新UI状态
    updateUI() {
        const batchBar = document.getElementById('batchActionBar');
        const toggleBtn = document.getElementById('batchModeBtn');
        
        if (this.enabled) {
            toggleBtn.classList.add('active');
            toggleBtn.textContent = '退出多次';
            batchBar.style.display = 'flex';
        } else {
            toggleBtn.classList.remove('active');
            toggleBtn.textContent = '多次评估';
            batchBar.style.display = 'none';
        }
        
        this.updateSelectedCount();
    },
    
    // 更新选中数量
    updateSelectedCount() {
        const countEl = document.getElementById('batchSelectedCount');
        if (countEl) {
            countEl.textContent = `已选 ${this.selectedItems.size} 条`;
        }
        
        const evalBtn = document.getElementById('batchEvaluateBtn');
        if (evalBtn) {
            evalBtn.disabled = this.selectedItems.size === 0;
        }
    },
    
    // 切换选中状态
    toggleItem(index) {
        if (this.selectedItems.has(index)) {
            this.selectedItems.delete(index);
        } else {
            this.selectedItems.add(index);
        }
        this.updateSelectedCount();
        this.updateItemUI(index);
    },
    
    // 更新单项UI
    updateItemUI(index) {
        const item = document.querySelector(`.data-item[data-index="${index}"]`);
        if (item) {
            const checkbox = item.querySelector('.batch-checkbox');
            if (checkbox) {
                checkbox.checked = this.selectedItems.has(index);
            }
            item.classList.toggle('batch-selected', this.selectedItems.has(index));
        }
    },
    
    // 全选/取消全选
    toggleAll() {
        if (this.selectedItems.size === homeworkList.length) {
            this.selectedItems.clear();
        } else {
            homeworkList.forEach((_, i) => this.selectedItems.add(i));
        }
        this.updateSelectedCount();
        document.querySelectorAll('.data-item').forEach((item, i) => {
            const checkbox = item.querySelector('.batch-checkbox');
            if (checkbox) checkbox.checked = this.selectedItems.has(i);
            item.classList.toggle('batch-selected', this.selectedItems.has(i));
        });
    },
    
    // 执行批量评估
    async evaluate() {
        if (this.selectedItems.size === 0) {
            showToast('请先选择要评估的记录', 'warning');
            return;
        }
        
        const selectedList = Array.from(this.selectedItems).map(i => homeworkList[i]);
        this.results = [];
        
        showLoading(`正在多次评估 0/${selectedList.length}...`);
        
        let successCount = 0;
        let failCount = 0;
        
        for (let i = 0; i < selectedList.length; i++) {
            const homework = selectedList[i];
            document.getElementById('loadingText').textContent = 
                `正在多次评估 ${i + 1}/${selectedList.length}...`;
            
            try {
                // 加载基准效果
                const baselineRes = await fetch('/api/grading/load-baseline', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        homework_name: homework.homework_name || '',
                        page_num: homework.page_num || '',
                        book_id: homework.book_id || ''
                    })
                });
                const baselineData = await baselineRes.json();
                
                if (!baselineData.success || !baselineData.base_effect?.length) {
                    this.results.push({
                        homework,
                        success: false,
                        error: '未找到基准效果'
                    });
                    failCount++;
                    continue;
                }
                
                // 执行评估
                let homeworkResult = [];
                try {
                    homeworkResult = JSON.parse(homework.homework_result || '[]');
                } catch (e) {}
                
                const evalRes = await fetch('/api/grading/evaluate', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        base_effect: baselineData.base_effect,
                        homework_result: homeworkResult,
                        subject_id: currentSubject,
                        use_ai_compare: false
                    })
                });
                const evalData = await evalRes.json();
                
                if (evalData.success) {
                    this.results.push({
                        homework,
                        success: true,
                        evaluation: evalData.evaluation,
                        base_effect: baselineData.base_effect
                    });
                    successCount++;
                } else {
                    this.results.push({
                        homework,
                        success: false,
                        error: evalData.error || '评估失败'
                    });
                    failCount++;
                }
            } catch (e) {
                this.results.push({
                    homework,
                    success: false,
                    error: e.message
                });
                failCount++;
            }
        }
        
        hideLoading();
        showToast(`多次评估完成: ${successCount} 成功, ${failCount} 失败`, 
            failCount > 0 ? 'warning' : 'success');
        
        this.showResults();
    },
    
    // 显示批量评估结果
    showResults() {
        const modal = document.getElementById('batchResultModal');
        const body = document.getElementById('batchResultBody');
        
        if (!modal || !body) return;
        
        // 计算汇总统计
        const successResults = this.results.filter(r => r.success);
        const summary = this.calculateSummary(successResults);
        
        let html = `
            <div class="batch-summary-section">
                <div class="batch-summary-title">汇总统计</div>
                <div class="batch-summary-grid">
                    <div class="batch-summary-item">
                        <div class="batch-summary-value">${this.results.length}</div>
                        <div class="batch-summary-label">总记录数</div>
                    </div>
                    <div class="batch-summary-item success">
                        <div class="batch-summary-value">${successResults.length}</div>
                        <div class="batch-summary-label">评估成功</div>
                    </div>
                    <div class="batch-summary-item ${summary.avgAccuracy >= 80 ? 'success' : summary.avgAccuracy >= 60 ? 'warning' : 'error'}">
                        <div class="batch-summary-value">${summary.avgAccuracy.toFixed(1)}%</div>
                        <div class="batch-summary-label">平均准确率</div>
                    </div>
                    <div class="batch-summary-item">
                        <div class="batch-summary-value">${summary.totalQuestions}</div>
                        <div class="batch-summary-label">总题数</div>
                    </div>
                    <div class="batch-summary-item error">
                        <div class="batch-summary-value">${summary.totalErrors}</div>
                        <div class="batch-summary-label">总错误数</div>
                    </div>
                </div>
            </div>
            
            <div class="batch-results-list">
                <div class="batch-results-title">详细结果</div>
                <table class="batch-results-table">
                    <thead>
                        <tr>
                            <th>作业</th>
                            <th>学生</th>
                            <th>页码</th>
                            <th>题数</th>
                            <th>准确率</th>
                            <th>错误数</th>
                            <th>状态</th>
                            <th>操作</th>
                        </tr>
                    </thead>
                    <tbody>
        `;
        
        this.results.forEach((result, index) => {
            const hw = result.homework;
            if (result.success) {
                const eval_ = result.evaluation;
                const accuracy = (eval_.accuracy * 100).toFixed(1);
                const accuracyClass = eval_.accuracy >= 0.8 ? 'success' : eval_.accuracy >= 0.6 ? 'warning' : 'error';
                
                html += `
                    <tr>
                        <td>${escapeHtml(hw.homework_name || '-')}</td>
                        <td>${escapeHtml(hw.student_name || hw.student_id || '-')}</td>
                        <td>${hw.page_num || '-'}</td>
                        <td>${eval_.total_questions}</td>
                        <td class="text-${accuracyClass}">${accuracy}%</td>
                        <td class="text-error">${eval_.error_count}</td>
                        <td><span class="tag tag-success">成功</span></td>
                        <td>
                            <button class="btn btn-small" onclick="BatchEvaluation.viewDetail(${index})">详情</button>
                        </td>
                    </tr>
                `;
            } else {
                html += `
                    <tr class="row-error">
                        <td>${escapeHtml(hw.homework_name || '-')}</td>
                        <td>${escapeHtml(hw.student_name || hw.student_id || '-')}</td>
                        <td>${hw.page_num || '-'}</td>
                        <td>-</td>
                        <td>-</td>
                        <td>-</td>
                        <td><span class="tag tag-error">失败</span></td>
                        <td><span class="text-muted">${escapeHtml(result.error)}</span></td>
                    </tr>
                `;
            }
        });
        
        html += `
                    </tbody>
                </table>
            </div>
        `;
        
        body.innerHTML = html;
        modal.style.display = 'flex';
    },
    
    // 计算汇总统计
    calculateSummary(successResults) {
        if (successResults.length === 0) {
            return { avgAccuracy: 0, totalQuestions: 0, totalErrors: 0 };
        }
        
        let totalAccuracy = 0;
        let totalQuestions = 0;
        let totalErrors = 0;
        
        successResults.forEach(r => {
            totalAccuracy += r.evaluation.accuracy;
            totalQuestions += r.evaluation.total_questions;
            totalErrors += r.evaluation.error_count;
        });
        
        return {
            avgAccuracy: (totalAccuracy / successResults.length) * 100,
            totalQuestions,
            totalErrors
        };
    },
    
    // 查看单条详情
    viewDetail(index) {
        const result = this.results[index];
        if (!result || !result.success) return;
        
        // 设置当前选中的作业和评估结果
        selectedHomework = result.homework;
        baseEffect = result.base_effect;
        evaluationResult = result.evaluation;
        
        // 关闭批量结果弹窗
        this.hideResultModal();
        
        // 渲染详情
        renderSelectedData();
        renderQuestionCards();
        renderEvaluationResult();
        
        document.getElementById('selectedDataSection').style.display = 'block';
        document.getElementById('emptyRightPanel').style.display = 'none';
        document.getElementById('baseEffectSection').style.display = 'block';
        document.getElementById('evaluateSection').style.display = 'block';
    },
    
    // 隐藏结果弹窗
    hideResultModal(event) {
        if (event && event.target !== event.currentTarget) return;
        document.getElementById('batchResultModal').style.display = 'none';
    },
    
    // 导出批量结果
    exportResults() {
        if (this.results.length === 0) {
            showToast('没有可导出的结果', 'warning');
            return;
        }
        
        const exportData = this.results.map(r => {
            const hw = r.homework;
            if (r.success) {
                return {
                    homework_name: hw.homework_name,
                    student_name: hw.student_name || hw.student_id,
                    page_num: hw.page_num,
                    total_questions: r.evaluation.total_questions,
                    correct_count: r.evaluation.correct_count,
                    error_count: r.evaluation.error_count,
                    accuracy: (r.evaluation.accuracy * 100).toFixed(1) + '%',
                    precision: (r.evaluation.precision * 100).toFixed(1) + '%',
                    recall: (r.evaluation.recall * 100).toFixed(1) + '%',
                    f1_score: (r.evaluation.f1_score * 100).toFixed(1) + '%',
                    status: '成功'
                };
            } else {
                return {
                    homework_name: hw.homework_name,
                    student_name: hw.student_name || hw.student_id,
                    page_num: hw.page_num,
                    status: '失败',
                    error: r.error
                };
            }
        });
        
        const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `batch_evaluation_${new Date().toISOString().slice(0, 10)}.json`;
        a.click();
        URL.revokeObjectURL(url);
        
        showToast('导出成功', 'success');
    }
};

// 导出到全局
window.BatchEvaluation = BatchEvaluation;
