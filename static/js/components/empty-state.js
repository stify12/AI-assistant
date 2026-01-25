/**
 * 空状态组件
 */
const EmptyState = {
    templates: {
        noData: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"/>
            </svg>`,
            title: '暂无数据',
            description: '当前没有可显示的内容'
        },
        noSamples: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>
            </svg>`,
            title: '没有错误样本',
            description: '当前任务没有发现错误样本'
        },
        noSearchResults: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"/>
            </svg>`,
            title: '未找到结果',
            description: '没有匹配的搜索结果，请尝试其他关键词'
        },
        noFilterResults: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2.586a1 1 0 01-.293.707l-6.414 6.414a1 1 0 00-.293.707V17l-4 4v-6.586a1 1 0 00-.293-.707L3.293 7.293A1 1 0 013 6.586V4z"/>
            </svg>`,
            title: '筛选无结果',
            description: '当前筛选条件下没有数据，请调整筛选条件'
        },
        analysisNotStarted: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z"/>
            </svg>`,
            title: '尚未分析',
            description: '点击"刷新分析"开始 AI 智能分析'
        },
        analysisFailed: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>
            </svg>`,
            title: '分析失败',
            description: '分析过程中出现错误，请重试'
        },
        selectItem: {
            icon: `<svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                <path d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5M7.188 2.239l.777 2.897M5.136 7.965l-2.898-.777M13.95 4.05l-2.122 2.122m-5.657 5.656l-2.12 2.122"/>
            </svg>`,
            title: '选择一个项目',
            description: '从左侧列表中选择一个项目查看详情'
        }
    },

    render(containerId, type = 'noData', options = {}) {
        const container = document.getElementById(containerId);
        if (!container) return;

        const template = this.templates[type] || this.templates.noData;
        const { 
            title = template.title, 
            description = template.description,
            actionText = null,
            onAction = null
        } = options;

        container.innerHTML = `
            <div class="empty-state" style="
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                padding: 40px 20px;
                color: #aeaeb2;
                text-align: center;
            ">
                <div class="empty-icon" style="margin-bottom: 16px; opacity: 0.5;">
                    ${template.icon}
                </div>
                <h4 style="margin: 0 0 8px 0; font-size: 16px; font-weight: 500; color: #86868b;">
                    ${title}
                </h4>
                <p style="margin: 0; font-size: 14px; color: #aeaeb2; max-width: 300px;">
                    ${description}
                </p>
                ${actionText ? `
                    <button class="empty-action-btn" style="
                        margin-top: 16px;
                        padding: 10px 20px;
                        background: #1d1d1f;
                        color: #fff;
                        border: none;
                        border-radius: 8px;
                        font-size: 14px;
                        cursor: pointer;
                    ">${actionText}</button>
                ` : ''}
            </div>
        `;

        if (actionText && onAction) {
            container.querySelector('.empty-action-btn').addEventListener('click', onAction);
        }
    }
};

window.EmptyState = EmptyState;
