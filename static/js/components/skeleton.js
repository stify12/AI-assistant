/**
 * 骨架屏组件
 */
const Skeleton = {
    templates: {
        card: `
            <div class="skeleton skeleton-card" style="height: 120px; border-radius: 8px;"></div>
        `,
        text: {
            short: '<div class="skeleton skeleton-text" style="width: 40%; height: 16px; margin-bottom: 8px;"></div>',
            medium: '<div class="skeleton skeleton-text" style="width: 70%; height: 16px; margin-bottom: 8px;"></div>',
            long: '<div class="skeleton skeleton-text" style="width: 100%; height: 16px; margin-bottom: 8px;"></div>'
        },
        chart: `
            <div class="skeleton skeleton-chart" style="width: 100%; height: 300px; border-radius: 8px;"></div>
        `,
        list: `
            <div class="skeleton-list">
                <div class="skeleton" style="height: 60px; margin-bottom: 8px; border-radius: 6px;"></div>
                <div class="skeleton" style="height: 60px; margin-bottom: 8px; border-radius: 6px;"></div>
                <div class="skeleton" style="height: 60px; margin-bottom: 8px; border-radius: 6px;"></div>
            </div>
        `,
        table: `
            <div class="skeleton-table">
                <div class="skeleton" style="height: 40px; margin-bottom: 4px; border-radius: 4px;"></div>
                <div class="skeleton" style="height: 36px; margin-bottom: 4px; border-radius: 4px;"></div>
                <div class="skeleton" style="height: 36px; margin-bottom: 4px; border-radius: 4px;"></div>
                <div class="skeleton" style="height: 36px; margin-bottom: 4px; border-radius: 4px;"></div>
                <div class="skeleton" style="height: 36px; border-radius: 4px;"></div>
            </div>
        `
    },

    show(containerId, type = 'card', count = 1) {
        const container = document.getElementById(containerId);
        if (!container) return;
        
        let html = '';
        const template = this.templates[type] || this.templates.card;
        
        if (typeof template === 'object') {
            // text 类型有子类型
            html = Object.values(template).join('');
        } else {
            for (let i = 0; i < count; i++) {
                html += template;
            }
        }
        
        container.innerHTML = html;
    },

    hide(containerId) {
        const container = document.getElementById(containerId);
        if (container) {
            container.innerHTML = '';
        }
    },

    // 添加骨架屏样式
    injectStyles() {
        if (document.getElementById('skeleton-styles')) return;
        
        const style = document.createElement('style');
        style.id = 'skeleton-styles';
        style.textContent = `
            .skeleton {
                background: linear-gradient(90deg, #f0f0f2 25%, #e8e8ea 50%, #f0f0f2 75%);
                background-size: 200% 100%;
                animation: skeleton-shimmer 1.5s infinite;
            }
            @keyframes skeleton-shimmer {
                0% { background-position: 200% 0; }
                100% { background-position: -200% 0; }
            }
        `;
        document.head.appendChild(style);
    }
};

// 自动注入样式
Skeleton.injectStyles();

window.Skeleton = Skeleton;
