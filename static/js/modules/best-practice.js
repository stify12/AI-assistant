/**
 * 最佳实践库模块 (US-16)
 */
const BestPracticeModule = {
    practices: [],
    currentCategory: null,
    
    async load(category = null, starredOnly = false) {
        const container = document.getElementById('best-practice-container');
        if (!container) return;
        
        container.innerHTML = '<div class="loading-spinner">加载中...</div>';
        
        try {
            let url = '/api/best-practices?';
            if (category) url += `category=${encodeURIComponent(category)}&`;
            if (starredOnly) url += 'starred=true&';
            
            const resp = await fetch(url);
            const result = await resp.json();
            
            if (!result.success) {
                throw new Error(result.error || '加载失败');
            }
            
            this.practices = result.data || [];
            this.currentCategory = category;
            this.render(container);
        } catch (err) {
            container.innerHTML = `<div class="error-message">加载失败: ${err.message}</div>`;
        }
    },
    
    render(container) {
        if (this.practices.length === 0) {
            container.innerHTML = `
                <div class="empty-state">
                    <div class="empty-text">暂无最佳实践</div>
                    <button class="btn btn-primary" onclick="BestPracticeModule.showAddModal()">添加实践</button>
                </div>
            `;
            return;
        }
        
        let html = '<div class="practice-list">';
        
        for (const p of this.practices) {
            const starClass = p.is_starred ? 'starred' : '';
            const tags = (p.tags || []).map(t => `<span class="tag">${this.escapeHtml(t)}</span>`).join('');
            
            html += `
                <div class="practice-card" data-id="${p.id}">
                    <div class="practice-header">
                        <div class="practice-title">
                            <span class="practice-name">${this.escapeHtml(p.name)}</span>
                            <span class="practice-category">${this.escapeHtml(p.category)}</span>
                        </div>
                        <button class="star-btn ${starClass}" onclick="BestPracticeModule.toggleStar('${p.id}')">
                            <svg viewBox="0 0 24 24" width="18" height="18">
                                <path fill="currentColor" d="M12 17.27L18.18 21l-1.64-7.03L22 9.24l-7.19-.61L12 2 9.19 8.63 2 9.24l5.46 4.73L5.82 21z"/>
                            </svg>
                        </button>
                    </div>
                    <div class="practice-desc">${this.escapeHtml(p.description || '暂无描述')}</div>
                    <div class="practice-tags">${tags}</div>
                    <div class="practice-footer">
                        <span class="practice-meta">v${p.version} · 使用 ${p.usage_count || 0} 次</span>
                        <div class="practice-actions">
                            <button class="btn btn-sm btn-secondary" onclick="BestPracticeModule.viewDetail('${p.id}')">查看</button>
                            <button class="btn btn-sm btn-primary" onclick="BestPracticeModule.usePractice('${p.id}')">使用</button>
                        </div>
                    </div>
                </div>
            `;
        }
        
        html += '</div>';
        container.innerHTML = html;
    },
    
    async toggleStar(id) {
        try {
            const resp = await fetch(`/api/best-practices/${id}/star`, { method: 'POST' });
            const result = await resp.json();
            
            if (result.success) {
                // 更新本地状态
                const p = this.practices.find(x => x.id === id);
                if (p) p.is_starred = result.is_starred;
                
                // 更新UI
                const card = document.querySelector(`.practice-card[data-id="${id}"]`);
                if (card) {
                    const btn = card.querySelector('.star-btn');
                    btn.classList.toggle('starred', result.is_starred);
                }
            }
        } catch (err) {
            console.error('切换星标失败:', err);
        }
    },
    
    async usePractice(id) {
        try {
            await fetch(`/api/best-practices/${id}/use`, { method: 'POST' });
            
            const p = this.practices.find(x => x.id === id);
            if (p && p.prompt_content) {
                // 复制到剪贴板
                await navigator.clipboard.writeText(p.prompt_content);
                this.showToast('Prompt已复制到剪贴板');
            }
        } catch (err) {
            console.error('使用实践失败:', err);
        }
    },
    
    async viewDetail(id) {
        try {
            const resp = await fetch(`/api/best-practices/${id}`);
            const result = await resp.json();
            
            if (result.success) {
                this.showDetailModal(result.data);
            }
        } catch (err) {
            console.error('获取详情失败:', err);
        }
    },
    
    showDetailModal(practice) {
        const modal = document.getElementById('practiceDetailModal');
        if (!modal) return;
        
        document.getElementById('practiceDetailName').textContent = practice.name;
        document.getElementById('practiceDetailCategory').textContent = practice.category;
        document.getElementById('practiceDetailDesc').textContent = practice.description || '暂无描述';
        document.getElementById('practiceDetailPrompt').textContent = practice.prompt_content;
        document.getElementById('practiceDetailVersion').textContent = `v${practice.version}`;
        document.getElementById('practiceDetailUsage').textContent = `${practice.usage_count || 0} 次`;
        
        modal.style.display = 'flex';
    },
    
    closeDetailModal() {
        const modal = document.getElementById('practiceDetailModal');
        if (modal) modal.style.display = 'none';
    },
    
    showAddModal() {
        const modal = document.getElementById('practiceAddModal');
        if (modal) {
            modal.style.display = 'flex';
            document.getElementById('addPracticeName').value = '';
            document.getElementById('addPracticeCategory').value = '';
            document.getElementById('addPracticePrompt').value = '';
            document.getElementById('addPracticeDesc').value = '';
        }
    },
    
    closeAddModal() {
        const modal = document.getElementById('practiceAddModal');
        if (modal) modal.style.display = 'none';
    },
    
    async savePractice() {
        const name = document.getElementById('addPracticeName')?.value?.trim();
        const category = document.getElementById('addPracticeCategory')?.value?.trim() || '通用';
        const prompt_content = document.getElementById('addPracticePrompt')?.value?.trim();
        const description = document.getElementById('addPracticeDesc')?.value?.trim();
        
        if (!name || !prompt_content) {
            this.showToast('请填写名称和Prompt内容', 'error');
            return;
        }
        
        try {
            const resp = await fetch('/api/best-practices', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, category, prompt_content, description })
            });
            
            const result = await resp.json();
            
            if (result.success) {
                this.showToast('添加成功');
                this.closeAddModal();
                this.load(this.currentCategory);
            } else {
                throw new Error(result.error);
            }
        } catch (err) {
            this.showToast('添加失败: ' + err.message, 'error');
        }
    },
    
    showToast(message, type = 'success') {
        if (window.showToast) {
            window.showToast(message, type);
        } else {
            alert(message);
        }
    },
    
    escapeHtml(str) {
        if (!str) return '';
        return str.replace(/[&<>"']/g, m => ({
            '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'
        }[m]));
    }
};

window.BestPracticeModule = BestPracticeModule;
