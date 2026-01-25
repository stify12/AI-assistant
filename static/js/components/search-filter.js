/**
 * 搜索筛选组件
 */
class SearchFilter {
    constructor(inputId, options = {}) {
        this.input = document.getElementById(inputId);
        this.options = {
            debounceDelay: options.debounceDelay || 300,
            onSearch: options.onSearch || (() => {}),
            placeholder: options.placeholder || '搜索...',
            showHistory: options.showHistory !== false,
            maxHistory: options.maxHistory || 10,
            storageKey: options.storageKey || 'searchHistory',
            syntaxHelp: options.syntaxHelp || [],
            ...options
        };
        
        this.history = this.loadHistory();
        this.debounceTimer = null;
        this.dropdown = null;
        
        this.init();
    }

    init() {
        if (!this.input) return;
        
        this.input.placeholder = this.options.placeholder;
        this.createDropdown();
        this.bindEvents();
    }

    createDropdown() {
        this.dropdown = document.createElement('div');
        this.dropdown.className = 'search-dropdown';
        this.dropdown.style.cssText = `
            position: absolute;
            top: 100%;
            left: 0;
            right: 0;
            background: #fff;
            border: 1px solid #d2d2d7;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.1);
            display: none;
            z-index: 100;
            max-height: 300px;
            overflow-y: auto;
        `;
        
        // 确保父元素有相对定位
        const parent = this.input.parentElement;
        if (getComputedStyle(parent).position === 'static') {
            parent.style.position = 'relative';
        }
        parent.appendChild(this.dropdown);
    }

    bindEvents() {
        // 输入事件（防抖）
        this.input.addEventListener('input', () => {
            clearTimeout(this.debounceTimer);
            this.debounceTimer = setTimeout(() => {
                this.options.onSearch(this.input.value);
            }, this.options.debounceDelay);
        });

        // 聚焦显示下拉
        this.input.addEventListener('focus', () => {
            this.showDropdown();
        });

        // 失焦隐藏下拉
        this.input.addEventListener('blur', () => {
            setTimeout(() => this.hideDropdown(), 200);
        });

        // 回车搜索
        this.input.addEventListener('keydown', (e) => {
            if (e.key === 'Enter') {
                e.preventDefault();
                this.search();
            } else if (e.key === 'Escape') {
                this.hideDropdown();
            }
        });
    }

    showDropdown() {
        let html = '';
        
        // 语法提示
        if (this.options.syntaxHelp.length > 0 && !this.input.value) {
            html += '<div class="search-section">';
            html += '<div class="search-section-title" style="padding: 8px 12px; font-size: 12px; color: #86868b;">搜索语法</div>';
            this.options.syntaxHelp.forEach(item => {
                html += `
                    <div class="search-syntax-item" style="padding: 8px 12px; font-size: 13px; cursor: pointer;" 
                         data-syntax="${item.syntax}">
                        <code style="background: #f5f5f7; padding: 2px 6px; border-radius: 4px; margin-right: 8px;">${item.syntax}</code>
                        <span style="color: #86868b;">${item.description}</span>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        // 搜索历史
        if (this.options.showHistory && this.history.length > 0) {
            html += '<div class="search-section">';
            html += `
                <div class="search-section-title" style="padding: 8px 12px; font-size: 12px; color: #86868b; display: flex; justify-content: space-between;">
                    <span>搜索历史</span>
                    <span class="clear-history" style="cursor: pointer; color: #1565c0;">清空</span>
                </div>
            `;
            this.history.forEach((item, index) => {
                html += `
                    <div class="search-history-item" style="padding: 8px 12px; font-size: 13px; cursor: pointer; display: flex; justify-content: space-between; align-items: center;" 
                         data-query="${item}">
                        <span>${item}</span>
                        <span class="remove-history" data-index="${index}" style="color: #aeaeb2; font-size: 16px;">&times;</span>
                    </div>
                `;
            });
            html += '</div>';
        }
        
        if (!html) {
            this.hideDropdown();
            return;
        }
        
        this.dropdown.innerHTML = html;
        this.dropdown.style.display = 'block';
        
        // 绑定下拉项事件
        this.dropdown.querySelectorAll('.search-syntax-item').forEach(item => {
            item.addEventListener('click', () => {
                this.input.value = item.dataset.syntax;
                this.input.focus();
            });
            item.addEventListener('mouseenter', () => {
                item.style.background = '#f5f5f7';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = '';
            });
        });
        
        this.dropdown.querySelectorAll('.search-history-item').forEach(item => {
            item.addEventListener('click', (e) => {
                if (!e.target.classList.contains('remove-history')) {
                    this.input.value = item.dataset.query;
                    this.search();
                }
            });
            item.addEventListener('mouseenter', () => {
                item.style.background = '#f5f5f7';
            });
            item.addEventListener('mouseleave', () => {
                item.style.background = '';
            });
        });
        
        this.dropdown.querySelectorAll('.remove-history').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.removeHistory(parseInt(btn.dataset.index));
            });
        });
        
        const clearBtn = this.dropdown.querySelector('.clear-history');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => this.clearHistory());
        }
    }

    hideDropdown() {
        if (this.dropdown) {
            this.dropdown.style.display = 'none';
        }
    }

    search() {
        const query = this.input.value.trim();
        if (query) {
            this.addHistory(query);
        }
        this.hideDropdown();
        this.options.onSearch(query);
    }

    loadHistory() {
        try {
            return JSON.parse(localStorage.getItem(this.options.storageKey) || '[]');
        } catch {
            return [];
        }
    }

    saveHistory() {
        localStorage.setItem(this.options.storageKey, JSON.stringify(this.history));
    }

    addHistory(query) {
        // 移除重复项
        this.history = this.history.filter(h => h !== query);
        // 添加到开头
        this.history.unshift(query);
        // 限制数量
        this.history = this.history.slice(0, this.options.maxHistory);
        this.saveHistory();
    }

    removeHistory(index) {
        this.history.splice(index, 1);
        this.saveHistory();
        this.showDropdown();
    }

    clearHistory() {
        this.history = [];
        this.saveHistory();
        this.hideDropdown();
    }

    setValue(value) {
        this.input.value = value;
    }

    getValue() {
        return this.input.value;
    }

    clear() {
        this.input.value = '';
        this.options.onSearch('');
    }
}

/**
 * 高亮关键词
 */
function highlightKeywords(text, keywords) {
    if (!keywords || keywords.length === 0) return text;
    
    const keywordArray = Array.isArray(keywords) ? keywords : [keywords];
    let result = text;
    
    keywordArray.forEach(keyword => {
        if (!keyword) return;
        const regex = new RegExp(`(${keyword.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')})`, 'gi');
        result = result.replace(regex, '<mark style="background: #fff3cd; padding: 0 2px;">$1</mark>');
    });
    
    return result;
}

window.SearchFilter = SearchFilter;
window.highlightKeywords = highlightKeywords;
