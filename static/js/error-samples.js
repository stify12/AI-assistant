/**
 * 错误样本库页面脚本
 */

let taskId = null;
let samples = [];
let selectedSampleId = null;
let selectedSampleIds = new Set();
let currentFilter = 'all';
let currentPage = 1;
let pageSize = 50;
let totalSamples = 0;
let searchFilter = null;

document.addEventListener('DOMContentLoaded', function() {
    const params = new URLSearchParams(window.location.search);
    taskId = params.get('task_id');
    
    if (!taskId) {
        toast.error('缺少 task_id 参数');
        return;
    }
    
    initSearchFilter();
    loadSamples();
    bindEvents();
});

function initSearchFilter() {
    searchFilter = new SearchFilter('searchInput', {
        placeholder: '搜索样本...',
        storageKey: `errorSamplesSearch_${taskId}`,
        syntaxHelp: [
            { syntax: 'book:数学', description: '按书本筛选' },
            { syntax: 'status:pending', description: '按状态筛选' },
            { syntax: 'page:10-20', description: '按页码范围筛选' }
        ],
        onSearch: (query) => {
            currentPage = 1;
            loadSamples(query);
        }
    });
}

function bindEvents() {
    document.querySelectorAll('.filter-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            document.querySelectorAll('.filter-btn').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
            currentFilter = this.dataset.status;
            currentPage = 1;
            loadSamples();
        });
    });

    document.getElementById('loadMoreBtn').addEventListener('click', function() {
        currentPage++;
        loadSamples(null, true);
    });
    
    document.querySelectorAll('.status-actions .status-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            if (selectedSampleId) {
                updateSampleStatus(selectedSampleId, this.dataset.status);
            }
        });
    });
    
    document.getElementById('saveNoteBtn').addEventListener('click', function() {
        if (selectedSampleId) {
            const note = document.getElementById('sampleNote').value;
            updateSampleStatus(selectedSampleId, null, note);
        }
    });
    
    document.getElementById('batchMarkBtn').addEventListener('click', showBatchModal);
    document.getElementById('cancelBatch').addEventListener('click', hideBatchModal);
    
    document.querySelectorAll('.batch-status-options .status-btn').forEach(btn => {
        btn.addEventListener('click', function() {
            batchUpdateStatus(this.dataset.status);
        });
    });
    
    document.getElementById('exportSamplesBtn').addEventListener('click', exportSamples);
    document.getElementById('toggleRightPanel').addEventListener('click', toggleRightPanel);
    
    initResizers();
    document.addEventListener('keydown', handleKeyNavigation);
}

async function loadSamples(searchQuery = null, append = false) {
    const container = document.getElementById('samplesList');
    if (!append) {
        container.innerHTML = '<div class="loading-placeholder">加载中...</div>';
    }
    
    try {
        let url = `/api/analysis/samples?task_id=${taskId}&page=${currentPage}&page_size=${pageSize}`;
        if (currentFilter !== 'all') url += `&status=${currentFilter}`;
        if (searchQuery) url += `&q=${encodeURIComponent(searchQuery)}`;
        
        const response = await fetch(url);
        const result = await response.json();
        
        if (!result.success) {
            container.innerHTML = `<div class="loading-placeholder">${result.error || '加载失败'}</div>`;
            return;
        }
        
        const newSamples = result.data.items || [];
        totalSamples = result.data.total || 0;
        samples = append ? samples.concat(newSamples) : newSamples;
        
        renderSamplesList();
        document.getElementById('totalCount').textContent = `共 ${totalSamples} 条`;
        document.getElementById('loadMoreBtn').style.display = samples.length < totalSamples ? 'block' : 'none';
    } catch (error) {
        console.error('加载样本失败:', error);
        container.innerHTML = '<div class="loading-placeholder">加载失败</div>';
    }
}

function renderSamplesList() {
    const container = document.getElementById('samplesList');
    if (samples.length === 0) {
        EmptyState.render('samplesList', 'noSamples');
        return;
    }
    
    let html = '';
    samples.forEach(sample => {
        const sampleId = sample.sample_id;
        const isSelected = sampleId === selectedSampleId;
        const status = sample.status || 'pending';
        html += `<div class="sample-card ${isSelected ? 'selected' : ''}" data-sample-id="${sampleId}" onclick="selectSample('${sampleId}')">
            <div class="sample-card-header">
                <span class="sample-card-title">${sample.book_name || '未知'} P${sample.page_num || 0}</span>
                <span class="sample-card-tag ${status}">${getStatusText(status)}</span>
            </div>
            <div class="sample-card-meta">题${sample.question_index || 0} · ${sample.error_type || '未知错误'}</div>
            <div class="sample-card-preview">AI: ${(sample.ai_answer || '-').substring(0, 30)}...</div>
        </div>`;
    });
    container.innerHTML = html;
}

function getStatusText(status) {
    return { pending: '待处理', confirmed: '已确认', fixed: '已修复', ignored: '已忽略' }[status] || status;
}

async function selectSample(sampleId) {
    selectedSampleId = sampleId;
    document.querySelectorAll('.sample-card').forEach(card => {
        card.classList.toggle('selected', card.dataset.sampleId === sampleId);
    });
    
    document.getElementById('emptyState').style.display = 'none';
    document.getElementById('sampleDetail').style.display = 'block';
    
    try {
        const response = await fetch(`/api/analysis/samples/${sampleId}?task_id=${taskId}`);
        const result = await response.json();
        if (!result.success) {
            toast.error(result.error || '加载详情失败');
            return;
        }
        renderSampleDetail(result.data);
    } catch (error) {
        console.error('加载样本详情失败:', error);
        toast.error('加载详情失败');
    }
}

function renderSampleDetail(data) {
    const sample = data.sample || {};
    const cluster = data.cluster || {};
    const llmInsight = data.llm_insight;
    const status = sample.status || 'pending';
    
    document.getElementById('detailHomeworkId').textContent = sample.homework_id || '-';
    document.getElementById('detailBookName').textContent = sample.book_name || '-';
    document.getElementById('detailPageNum').textContent = sample.page_num || '-';
    document.getElementById('detailQuestionIndex').textContent = sample.question_index || '-';
    document.getElementById('detailErrorType').textContent = sample.error_type || '-';
    document.getElementById('detailExpectedAnswer').textContent = sample.expected_answer || '-';
    document.getElementById('detailAiAnswer').textContent = sample.ai_answer || '-';
    
    document.querySelectorAll('.status-actions .status-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.status === status);
    });
    document.getElementById('sampleNote').value = sample.note || '';
    
    const llmContainer = document.getElementById('llmInsight');
    llmContainer.innerHTML = llmInsight ? `<p>${llmInsight.summary || llmInsight}</p>` : '<p class="text-muted">暂无 AI 分析结果</p>';
    
    const clusterContainer = document.getElementById('clusterInfo');
    if (cluster.cluster_key) {
        clusterContainer.innerHTML = `<div onclick="viewCluster('${cluster.cluster_key}')" style="cursor:pointer;">
            <div style="font-weight:500;margin-bottom:4px;">${cluster.error_type} - ${cluster.book_name}</div>
            <div style="font-size:12px;color:var(--text-secondary);">页码范围: ${cluster.page_range} · ${cluster.sample_count} 个样本</div>
        </div>`;
    } else {
        clusterContainer.innerHTML = '<p class="text-muted">-</p>';
    }
    document.getElementById('similarSamples').innerHTML = '<p class="text-muted">暂无相似样本</p>';
}

async function updateSampleStatus(sampleId, status, note = null) {
    try {
        const body = {};
        if (status) body.status = status;
        if (note !== null) body.note = note;
        
        const response = await fetch(`/api/analysis/samples/${sampleId}/status`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(body)
        });
        const result = await response.json();
        
        if (result.success) {
            const sample = samples.find(s => s.sample_id === sampleId);
            if (sample && status) sample.status = status;
            
            if (status) {
                document.querySelectorAll('.status-actions .status-btn').forEach(btn => {
                    btn.classList.toggle('active', btn.dataset.status === status);
                });
                const card = document.querySelector(`.sample-card[data-sample-id="${sampleId}"]`);
                if (card) {
                    const tag = card.querySelector('.sample-card-tag');
                    tag.className = `sample-card-tag ${status}`;
                    tag.textContent = getStatusText(status);
                }
            }
            toast.success('更新成功');
        } else {
            toast.error(result.error || '更新失败');
        }
    } catch (error) {
        console.error('更新状态失败:', error);
        toast.error('更新失败');
    }
}

async function batchUpdateStatus(status) {
    if (selectedSampleIds.size === 0) {
        toast.warning('请先选择样本');
        return;
    }
    
    confirmDialog.show({
        title: '批量更新状态',
        message: `确定要将 ${selectedSampleIds.size} 个样本标记为"${getStatusText(status)}"吗？`,
        onConfirm: async () => {
            try {
                const response = await fetch('/api/analysis/samples/batch-status', {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ sample_ids: Array.from(selectedSampleIds), status })
                });
                const result = await response.json();
                
                if (result.success) {
                    hideBatchModal();
                    selectedSampleIds.clear();
                    updateBatchButton();
                    loadSamples();
                    toast.success(`成功更新 ${result.data.updated_count || selectedSampleIds.size} 个样本`);
                } else {
                    toast.error(result.error || '批量更新失败');
                }
            } catch (error) {
                console.error('批量更新失败:', error);
                toast.error('批量更新失败');
            }
        }
    });
}

async function exportSamples() {
    try {
        const response = await fetch('/api/analysis/export', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_id: taskId, format: 'excel', sections: ['samples'] })
        });
        const result = await response.json();
        
        if (result.success) {
            toast.success('导出成功，正在下载...');
            window.location.href = `/api/analysis/export/download/${result.data.export_id}`;
        } else {
            toast.error(result.error || '导出失败');
        }
    } catch (error) {
        console.error('导出失败:', error);
        toast.error('导出失败');
    }
}

function showBatchModal() {
    document.getElementById('selectedCount').textContent = selectedSampleIds.size;
    document.getElementById('batchModal').style.display = 'flex';
}

function hideBatchModal() {
    document.getElementById('batchModal').style.display = 'none';
}

function updateBatchButton() {
    document.getElementById('batchMarkBtn').disabled = selectedSampleIds.size === 0;
}

function toggleRightPanel() {
    const panel = document.getElementById('rightPanel');
    const icon = document.querySelector('#toggleRightPanel .icon');
    panel.classList.toggle('collapsed');
    icon.textContent = panel.classList.contains('collapsed') ? '\u25B6' : '\u25C0';
}

function initResizers() {
    const leftResizer = document.getElementById('leftResizer');
    const rightResizer = document.getElementById('rightResizer');
    const leftPanel = document.getElementById('leftPanel');
    const rightPanel = document.getElementById('rightPanel');
    
    let isResizing = false;
    let currentResizer = null;
    
    function startResize(e, resizer) {
        isResizing = true;
        currentResizer = resizer;
        document.body.style.cursor = 'col-resize';
        document.body.style.userSelect = 'none';
    }
    
    function doResize(e) {
        if (!isResizing) return;
        if (currentResizer === leftResizer) {
            const newWidth = e.clientX;
            if (newWidth >= 250 && newWidth <= 500) leftPanel.style.width = newWidth + 'px';
        } else if (currentResizer === rightResizer) {
            const newWidth = window.innerWidth - e.clientX;
            if (newWidth >= 280 && newWidth <= 500) rightPanel.style.width = newWidth + 'px';
        }
    }
    
    function stopResize() {
        isResizing = false;
        currentResizer = null;
        document.body.style.cursor = '';
        document.body.style.userSelect = '';
    }
    
    leftResizer.addEventListener('mousedown', (e) => startResize(e, leftResizer));
    rightResizer.addEventListener('mousedown', (e) => startResize(e, rightResizer));
    document.addEventListener('mousemove', doResize);
    document.addEventListener('mouseup', stopResize);
}

function handleKeyNavigation(e) {
    if (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA') return;
    const currentIndex = samples.findIndex(s => s.sample_id === selectedSampleId);
    
    if (e.key === 'ArrowUp' && currentIndex > 0) {
        e.preventDefault();
        selectSample(samples[currentIndex - 1].sample_id);
    } else if (e.key === 'ArrowDown' && currentIndex < samples.length - 1) {
        e.preventDefault();
        selectSample(samples[currentIndex + 1].sample_id);
    }
}

function viewCluster(clusterId) {
    window.location.href = `/cluster-detail/${encodeURIComponent(clusterId)}?task_id=${taskId}`;
}
