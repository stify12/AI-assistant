/**
 * 多维度数据下钻模块 (US-21)
 */
const DrilldownModule = {
    currentLevel: 'overall',
    currentParentId: null,
    breadcrumb: [],
    
    init() {
        this.bindEvents();
    },
    
    bindEvents() {
        // 面包屑点击
        document.addEventListener('click', (e) => {
            if (e.target.closest('.drilldown-breadcrumb-item')) {
                const item = e.target.closest('.drilldown-breadcrumb-item');
                const level = item.dataset.level;
                const id = item.dataset.id || null;
                this.navigateTo(level, id);
            }
            // 下钻项点击
            if (e.target.closest('.drilldown-item')) {
                const item = e.target.closest('.drilldown-item');
                const nextLevel = item.dataset.nextLevel;
                const id = item.dataset.id;
                if (nextLevel) {
                    this.navigateTo(nextLevel, id);
                }
            }
        });
    },
    
    async load(level = 'overall', parentId = null) {
        const container = document.getElementById('drilldown-container');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">加载中...</div>';
        
        try {
            let url = `/api/drilldown/data?level=${level}`;
            if (parentId) url += `&parent_id=${encodeURIComponent(parentId)}`;
            
            const resp = await fetch(url);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error || '加载失败');
            }
            
            this.currentLevel = result.level;
            this.currentParentId = result.parent_id;
            this.breadcrumb = result.breadcrumb;
            
            this.render(container, result);
        } catch (err) {
            container.innerHTML = `<div class="error-message">加载失败: ${err.message}</div>`;
        }
    },
    
    navigateTo(level, parentId) {
        this.load(level, parentId);
    },
    
    render(container, data) {
        const levelNames = {
            overall: '总览',
            subject: '学科',
            book: '书本',
            page: '页码',
            question: '题目'
        };
        const nextLevelMap = {
            overall: 'subject',
            subject: 'book',
            book: 'page',
            page: 'question',
            question: null
        };
        
        let html = `
            <div class="drilldown-header">
                <div class="drilldown-breadcrumb">
                    ${data.breadcrumb.map((b, i) => `
                        <span class="drilldown-breadcrumb-item ${i === data.breadcrumb.length - 1 ? 'active' : ''}" 
                              data-level="${b.level}" data-id="${b.id || ''}">
                            ${b.name}
                        </span>
                        ${i < data.breadcrumb.length - 1 ? '<span class="breadcrumb-sep">/</span>' : ''}
                    `).join('')}
                </div>
                <div class="drilldown-summary">
                    <span class="summary-item">
                        <span class="label">总题数</span>
                        <span class="value">${data.summary.total_questions || 0}</span>
                    </span>
                    <span class="summary-item">
                        <span class="label">准确率</span>
                        <span class="value">${((data.summary.total_accuracy || 0) * 100).toFixed(1)}%</span>
                    </span>
                </div>
            </div>
        `;
        
        if (data.level === 'question' && data.data) {
            // 题目详情视图
            const q = data.data;
            html += `
                <div class="question-detail-card">
                    <div class="detail-row">
                        <span class="detail-label">题号</span>
                        <span class="detail-value">${q.question_number}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">状态</span>
                        <span class="detail-value">
                            <span class="tag ${q.is_correct ? 'tag-success' : 'tag-error'}">
                                ${q.is_correct ? '正确' : '错误'}
                            </span>
                        </span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">AI答案</span>
                        <span class="detail-value">${q.ai_answer || '-'}</span>
                    </div>
                    <div class="detail-row">
                        <span class="detail-label">预期答案</span>
                        <span class="detail-value">${q.expected_answer || '-'}</span>
                    </div>
                    ${q.error_type ? `
                    <div class="detail-row">
                        <span class="detail-label">错误类型</span>
                        <span class="detail-value">${q.error_type}</span>
                    </div>
                    ` : ''}
                    ${q.image_url ? `
                    <div class="detail-row">
                        <span class="detail-label">原图</span>
                        <img src="${q.image_url}" class="question-image" alt="题目图片">
                    </div>
                    ` : ''}
                </div>
            `;
        } else {
            // 列表视图
            const nextLevel = nextLevelMap[data.level];
            html += `<div class="drilldown-list">`;
            
            if (!data.data || data.data.length === 0) {
                html += '<div class="empty-state">暂无数据</div>';
            } else {
                for (const item of data.data) {
                    const accuracy = ((item.accuracy || 0) * 100).toFixed(1);
                    const accuracyClass = item.accuracy >= 0.9 ? 'high' : item.accuracy >= 0.7 ? 'medium' : 'low';
                    
                    if (data.level === 'page') {
                        // 题目列表
                        html += `
                            <div class="drilldown-item question-item" data-next-level="${nextLevel}" data-id="${item.id}">
                                <div class="item-main">
                                    <span class="item-name">${item.name}</span>
                                    <span class="tag ${item.is_correct ? 'tag-success' : 'tag-error'}">
                                        ${item.is_correct ? '正确' : '错误'}
                                    </span>
                                </div>
                                <div class="item-answers">
                                    <span class="answer-label">AI:</span> ${item.ai_answer || '-'}
                                    <span class="answer-sep">|</span>
                                    <span class="answer-label">预期:</span> ${item.expected_answer || '-'}
                                </div>
                            </div>
                        `;
                    } else {
                        html += `
                            <div class="drilldown-item" data-next-level="${nextLevel}" data-id="${item.id}">
                                <div class="item-main">
                                    <span class="item-name">${item.name}</span>
                                    <span class="item-count">${item.question_count || 0} 题</span>
                                </div>
                                <div class="item-stats">
                                    <div class="accuracy-bar">
                                        <div class="accuracy-fill ${accuracyClass}" style="width: ${accuracy}%"></div>
                                    </div>
                                    <span class="accuracy-text">${accuracy}%</span>
                                </div>
                            </div>
                        `;
                    }
                }
            }
            html += '</div>';
        }
        
        container.innerHTML = html;
    }
};

// 导出
window.DrilldownModule = DrilldownModule;
