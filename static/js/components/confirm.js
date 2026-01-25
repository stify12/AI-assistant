/**
 * 确认弹窗组件
 */
class ConfirmDialog {
    constructor() {
        this.modal = null;
        this.dontShowAgainKeys = new Set(
            JSON.parse(localStorage.getItem('confirmDontShowAgain') || '[]')
        );
    }

    show(options) {
        const {
            title = '确认操作',
            message = '确定要执行此操作吗？',
            description = '',
            impact = '',
            confirmText = '确认',
            cancelText = '取消',
            confirmType = 'primary', // primary, danger
            showDontShowAgain = false,
            dontShowAgainKey = null,
            onConfirm = () => {},
            onCancel = () => {}
        } = options;

        // 检查是否跳过
        if (dontShowAgainKey && this.dontShowAgainKeys.has(dontShowAgainKey)) {
            onConfirm();
            return;
        }

        // 创建弹窗
        this.modal = document.createElement('div');
        this.modal.className = 'confirm-modal';
        this.modal.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            display: flex;
            align-items: center;
            justify-content: center;
            z-index: 10001;
            opacity: 0;
            transition: opacity 0.2s ease;
        `;

        const confirmBtnStyle = confirmType === 'danger' 
            ? 'background: #d73a49; color: #fff;'
            : 'background: #1d1d1f; color: #fff;';

        this.modal.innerHTML = `
            <div class="confirm-content" style="
                background: #fff;
                border-radius: 16px;
                padding: 24px;
                max-width: 400px;
                width: 90%;
                transform: scale(0.9);
                transition: transform 0.2s ease;
            ">
                <h3 style="margin: 0 0 12px 0; font-size: 18px; font-weight: 600;">${title}</h3>
                <p style="margin: 0 0 8px 0; color: #1d1d1f; font-size: 14px;">${message}</p>
                ${description ? `<p style="margin: 0 0 8px 0; color: #86868b; font-size: 13px;">${description}</p>` : ''}
                ${impact ? `<div style="margin: 12px 0; padding: 12px; background: #ffeef0; border-radius: 8px; font-size: 13px; color: #d73a49;">${impact}</div>` : ''}
                ${showDontShowAgain ? `
                    <label style="display: flex; align-items: center; gap: 8px; margin: 16px 0; font-size: 13px; color: #86868b; cursor: pointer;">
                        <input type="checkbox" id="dontShowAgain" style="cursor: pointer;">
                        不再提示
                    </label>
                ` : ''}
                <div style="display: flex; gap: 12px; justify-content: flex-end; margin-top: 20px;">
                    <button class="confirm-cancel-btn" style="
                        padding: 10px 20px;
                        border: 1px solid #d2d2d7;
                        background: #fff;
                        border-radius: 8px;
                        font-size: 14px;
                        cursor: pointer;
                    ">${cancelText}</button>
                    <button class="confirm-ok-btn" style="
                        padding: 10px 20px;
                        border: none;
                        ${confirmBtnStyle}
                        border-radius: 8px;
                        font-size: 14px;
                        cursor: pointer;
                    ">${confirmText}</button>
                </div>
            </div>
        `;

        document.body.appendChild(this.modal);

        // 动画
        requestAnimationFrame(() => {
            this.modal.style.opacity = '1';
            this.modal.querySelector('.confirm-content').style.transform = 'scale(1)';
        });

        // 事件绑定
        const cancelBtn = this.modal.querySelector('.confirm-cancel-btn');
        const okBtn = this.modal.querySelector('.confirm-ok-btn');
        const checkbox = this.modal.querySelector('#dontShowAgain');

        cancelBtn.addEventListener('click', () => {
            this.hide();
            onCancel();
        });

        okBtn.addEventListener('click', () => {
            if (checkbox && checkbox.checked && dontShowAgainKey) {
                this.dontShowAgainKeys.add(dontShowAgainKey);
                localStorage.setItem('confirmDontShowAgain', 
                    JSON.stringify([...this.dontShowAgainKeys]));
            }
            this.hide();
            onConfirm();
        });

        // 点击遮罩关闭
        this.modal.addEventListener('click', (e) => {
            if (e.target === this.modal) {
                this.hide();
                onCancel();
            }
        });

        // ESC 关闭
        const escHandler = (e) => {
            if (e.key === 'Escape') {
                this.hide();
                onCancel();
                document.removeEventListener('keydown', escHandler);
            }
        };
        document.addEventListener('keydown', escHandler);
    }

    hide() {
        if (!this.modal) return;
        
        this.modal.style.opacity = '0';
        this.modal.querySelector('.confirm-content').style.transform = 'scale(0.9)';
        
        setTimeout(() => {
            if (this.modal && this.modal.parentNode) {
                this.modal.parentNode.removeChild(this.modal);
            }
            this.modal = null;
        }, 200);
    }

    // 快捷方法
    confirm(message, onConfirm) {
        this.show({ message, onConfirm });
    }

    danger(message, onConfirm) {
        this.show({ 
            title: '危险操作',
            message, 
            confirmType: 'danger',
            confirmText: '确认删除',
            onConfirm 
        });
    }
}

window.confirmDialog = new ConfirmDialog();
