/**
 * 导出进度显示模块 (US-25)
 */
const ExportProgressModule = {
    currentExportId: null,
    progressInterval: null,
    
    async startExport(exportType, params = {}) {
        // 显示进度弹窗
        this.showProgressModal();
        this.updateProgress(0, '准备导出...');
        
        try {
            // 发起导出请求
            const resp = await fetch('/api/export/start', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ type: exportType, ...params })
            });
            
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error || '导出失败');
            }
            
            this.currentExportId = result.export_id;
            
            // 开始轮询进度
            this.startPolling();
            
        } catch (err) {
            this.updateProgress(0, `导出失败: ${err.message}`, true);
        }
    },
    
    startPolling() {
        this.progressInterval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/export/progress/${this.currentExportId}`);
                const result = await resp.json();
                
                if (result.success) {
                    const progress = result.progress || 0;
                    const status = result.status || 'processing';
                    const message = result.message || '处理中...';
                    
                    this.updateProgress(progress, message);
                    
                    if (status === 'completed') {
                        this.stopPolling();
                        this.showDownloadButton(result.download_url);
                    } else if (status === 'failed') {
                        this.stopPolling();
                        this.updateProgress(progress, `导出失败: ${result.error}`, true);
                    }
                }
            } catch (err) {
                console.error('获取进度失败:', err);
            }
        }, 1000);
    },
    
    stopPolling() {
        if (this.progressInterval) {
            clearInterval(this.progressInterval);
            this.progressInterval = null;
        }
    },
    
    showProgressModal() {
        let modal = document.getElementById('exportProgressModal');
        if (!modal) {
            modal = document.createElement('div');
            modal.id = 'exportProgressModal';
            modal.className = 'modal';
            modal.innerHTML = `
                <div class="modal-content export-progress-content">
                    <div class="modal-header">
                        <h3>导出进度</h3>
                        <button class="modal-close" onclick="ExportProgressModule.closeModal()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="progress-container">
                            <div class="progress-bar-wrapper">
                                <div class="progress-bar" id="exportProgressBar" style="width: 0%"></div>
                            </div>
                            <div class="progress-text" id="exportProgressText">准备中...</div>
                        </div>
                        <div class="progress-actions" id="exportProgressActions" style="display: none;">
                            <a id="exportDownloadLink" class="btn btn-primary" href="#" download>下载文件</a>
                        </div>
                    </div>
                </div>
            `;
            document.body.appendChild(modal);
        }
        
        modal.style.display = 'flex';
        document.getElementById('exportProgressActions').style.display = 'none';
    },
    
    updateProgress(percent, message, isError = false) {
        const bar = document.getElementById('exportProgressBar');
        const text = document.getElementById('exportProgressText');
        
        if (bar) {
            bar.style.width = `${percent}%`;
            bar.className = `progress-bar ${isError ? 'error' : ''}`;
        }
        if (text) {
            text.textContent = message;
            text.className = `progress-text ${isError ? 'error' : ''}`;
        }
    },
    
    showDownloadButton(url) {
        const actions = document.getElementById('exportProgressActions');
        const link = document.getElementById('exportDownloadLink');
        
        if (actions && link) {
            link.href = url;
            actions.style.display = 'block';
        }
        
        this.updateProgress(100, '导出完成');
    },
    
    closeModal() {
        this.stopPolling();
        const modal = document.getElementById('exportProgressModal');
        if (modal) {
            modal.style.display = 'none';
        }
    },
    
    // 快速导出（无进度，直接下载）
    quickExport(url) {
        window.open(url, '_blank');
    }
};

window.ExportProgressModule = ExportProgressModule;
