/**
 * AI 助手 - 主页 JavaScript
 */

// ========== 全局状态 ==========
let currentImage = null;
let currentSessionId = null;
let selectedModel = 'doubao-1-5-vision-pro-32k-250115';
let reasoningLevel = 'medium'; // 思考程度
let chatHistory = []; // 当前对话历史
let allSessions = []; // 所有会话列表
let prompts = [];
let extractImage = null;
let extractedQuestions = [];
let optimizedPromptText = '';
let mcpTools = {}; // MCP工具配置
let useTools = true; // 是否启用工具调用

const VISION_MODELS = [
    'doubao-1-5-vision-pro-32k-250115',
    'doubao-seed-1-6-vision-250815',
    'doubao-seed-1-6-251015',
    'doubao-seed-1-8-251228',
    'doubao-seed-1-6-thinking-250715',
    'qwen-vl-plus'
];

// 支持思考程度调节的模型
const REASONING_MODELS = [
    'doubao-seed-1-6-251015',
    'doubao-seed-1-8-251228',
    'doubao-seed-1-6-thinking-250715'
];

const CHAT_MODELS = [
    'gpt-5-chat-latest',
    'gpt-5.2',
    'gpt-5.1',
    'gpt-5-mini',
    'gpt-4.1',
    'grok-4',
    'gemini-3-pro-preview',
    'gemini-3-flash-preview',
    'gemini-3-flash-preview-nothinking',
    'gemini-3-flash-preview-thinking',
    'deepseek-v3.2'
];

// ========== 初始化 ==========
document.addEventListener('DOMContentLoaded', async () => {
    await loadAllSessions();
    loadPrompts();
    loadConfig();
    loadMcpTools();
    loadMcpServers();
    setupInputHandlers();
    setupExtractUpload();
    
    // 如果有历史对话，加载最近的一个；否则显示欢迎界面
    if (allSessions.length > 0) {
        loadSession(allSessions[0].id);
    } else {
        // 显示欢迎界面，不创建新会话
        document.getElementById('chatWelcome').style.display = '';
        document.getElementById('chatMessages').innerHTML = '';
    }
});

// ========== 会话管理 ==========
async function loadAllSessions() {
    try {
        const res = await fetch('/api/all-sessions');
        allSessions = await res.json();
        renderHistoryList();
    } catch (e) {
        console.error('Load sessions error:', e);
        allSessions = [];
    }
}

function renderHistoryList() {
    const list = document.getElementById('historyList');
    if (allSessions.length === 0) {
        list.innerHTML = '<div style="padding:20px;text-align:center;color:#999;font-size:12px;">暂无对话记录</div>';
        return;
    }
    
    list.innerHTML = allSessions.map(s => `
        <div class="history-item ${s.id === currentSessionId ? 'active' : ''}" onclick="loadSession('${s.id}')">
            <div class="history-item-title">${escapeHtml(s.title || '新对话')}</div>
            <div class="history-item-meta">
                <span class="history-item-time">${formatTime(s.updated_at)}</span>
                <div class="history-item-actions">
                    <button onclick="event.stopPropagation();renameSession('${s.id}')">重命名</button>
                    <button class="delete" onclick="event.stopPropagation();deleteSession('${s.id}')">删除</button>
                </div>
            </div>
        </div>
    `).join('');
}

function filterHistory() {
    const keyword = document.getElementById('historySearch').value.toLowerCase();
    const items = document.querySelectorAll('.history-item');
    items.forEach(item => {
        const title = item.querySelector('.history-item-title').textContent.toLowerCase();
        item.style.display = title.includes(keyword) ? '' : 'none';
    });
}

async function startNewChat() {
    try {
        const res = await fetch('/api/session', { method: 'POST' });
        const data = await res.json();
        currentSessionId = data.session_id;
        chatHistory = [];
        
        // 添加到列表顶部
        allSessions.unshift({
            id: currentSessionId,
            title: '新对话',
            updated_at: new Date().toISOString()
        });
        renderHistoryList();
        
        // 清空对话区域，显示欢迎界面
        document.getElementById('chatWelcome').style.display = '';
        document.getElementById('chatMessages').innerHTML = '';
        
        // 清空输入框
        document.getElementById('promptInput').value = '';
        removeInputImage();
    } catch (e) {
        console.error('Start new chat error:', e);
    }
}

async function loadSession(sessionId) {
    try {
        const res = await fetch(`/api/session/${sessionId}`);
        const data = await res.json();
        
        currentSessionId = sessionId;
        chatHistory = data.messages || [];
        
        renderHistoryList();
        renderChatMessages();
    } catch (e) {
        console.error('Load session error:', e);
    }
}

async function renameSession(sessionId) {
    const session = allSessions.find(s => s.id === sessionId);
    const newTitle = prompt('输入新名称:', session?.title || '新对话');
    if (!newTitle) return;
    
    try {
        await fetch(`/api/session/${sessionId}/rename`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ title: newTitle })
        });
        
        if (session) session.title = newTitle;
        renderHistoryList();
    } catch (e) {
        console.error('Rename error:', e);
    }
}

async function deleteSession(sessionId) {
    if (!confirm('确定删除此对话？')) return;
    
    try {
        await fetch('/api/session', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ session_id: sessionId })
        });
        
        allSessions = allSessions.filter(s => s.id !== sessionId);
        
        if (sessionId === currentSessionId) {
            if (allSessions.length > 0) {
                loadSession(allSessions[0].id);
            } else {
                startNewChat();
            }
        } else {
            renderHistoryList();
        }
    } catch (e) {
        console.error('Delete error:', e);
    }
}

// ========== 对话渲染 ==========
function renderChatMessages() {
    const container = document.getElementById('chatMessages');
    const welcome = document.getElementById('chatWelcome');
    
    if (chatHistory.length === 0) {
        welcome.style.display = '';
        container.innerHTML = '';
        return;
    }
    
    welcome.style.display = 'none';
    container.innerHTML = chatHistory.map(msg => renderMessage(msg)).join('');
    
    // 滚动到底部
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}


function getModelDisplayName(modelId) {
    const modelNames = {
        'doubao-1-5-vision-pro-32k-250115': 'Vision Pro',
        'doubao-seed-1-6-vision-250815': 'Seed Vision',
        'doubao-seed-1-6-251015': 'Seed 1.6',
        'doubao-seed-1-8-251228': 'Seed 1.8',
        'doubao-seed-1-6-thinking-250715': 'Seed Thinking',
        'qwen-vl-plus': 'Qwen VL',
        'gpt-5-chat-latest': 'GPT-5',
        'gpt-5.2': 'GPT-5.2',
        'gpt-5.1': 'GPT-5.1',
        'gpt-5-mini': 'GPT-5 Mini',
        'gpt-4.1': 'GPT-4.1',
        'grok-4': 'Grok-4',
        'gemini-3-pro-preview': 'Gemini 3 Pro',
        'gemini-3-flash-preview': 'Gemini 3 Flash',
        'gemini-3-flash-preview-nothinking': 'Gemini Flash NT',
        'gemini-3-flash-preview-thinking': 'Gemini Flash T',
        'deepseek-v3.2': 'DeepSeek V3.2'
    };
    return modelNames[modelId] || modelId || 'AI';
}

function renderMessage(msg) {
    const isUser = msg.role === 'user';
    const avatar = isUser ? 'U' : getModelDisplayName(msg.model).slice(0, 2).toUpperCase();
    const role = isUser ? '你' : getModelDisplayName(msg.model);
    
    let content = '';
    if (msg.image) {
        content += `<img src="${msg.image}" onclick="showImageModal(this.src)">`;
    }
    if (typeof msg.content === 'string') {
        content += isUser ? escapeHtml(msg.content) : marked.parse(msg.content);
    }
    
    return `
        <div class="message ${msg.role}">
            <div class="message-header">
                <div class="message-avatar">${avatar}</div>
                <div class="message-role">${role}</div>
            </div>
            <div class="message-content">${content}</div>
        </div>
    `;
}

function addMessageToUI(role, content, image = null, model = null) {
    const container = document.getElementById('chatMessages');
    const welcome = document.getElementById('chatWelcome');
    welcome.style.display = 'none';
    
    const msg = { role, content, image, model };
    // 不再在这里添加到chatHistory，由后端统一保存
    
    container.innerHTML += renderMessage(msg);
    
    const chatContainer = document.getElementById('chatContainer');
    chatContainer.scrollTop = chatContainer.scrollHeight;
}

// ========== 发送消息 ==========
function setupInputHandlers() {
    const textarea = document.getElementById('promptInput');
    
    textarea.addEventListener('input', function() {
        this.style.height = 'auto';
        this.style.height = Math.min(this.scrollHeight, 150) + 'px';
    });
    
    textarea.addEventListener('keydown', function(e) {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault();
            sendMessage();
        }
    });
    
    document.getElementById('fileInput').addEventListener('change', e => {
        if (e.target.files[0]) handleImageUpload(e.target.files[0]);
    });
}

function handleImageUpload(file) {
    const reader = new FileReader();
    reader.onload = e => {
        currentImage = e.target.result;
        document.getElementById('inputPreviewImg').src = currentImage;
        document.getElementById('inputPreview').style.display = 'block';
    };
    reader.readAsDataURL(file);
}

function removeInputImage() {
    currentImage = null;
    document.getElementById('inputPreview').style.display = 'none';
    document.getElementById('fileInput').value = '';
}

async function sendMessage() {
    const input = document.getElementById('promptInput');
    const prompt = input.value.trim();
    
    if (!prompt && !currentImage) return;
    
    const btn = document.getElementById('sendBtn');
    btn.disabled = true;
    
    // 获取并行数量
    const parallelCount = parseInt(document.getElementById('parallelCount').value) || 1;
    
    // 如果没有当前会话，先创建一个
    if (!currentSessionId) {
        try {
            const res = await fetch('/api/session', { method: 'POST' });
            const data = await res.json();
            currentSessionId = data.session_id;
            chatHistory = [];
            allSessions.unshift({
                id: currentSessionId,
                title: '新对话',
                updated_at: new Date().toISOString()
            });
            renderHistoryList();
        } catch (e) {
            console.error('Create session error:', e);
            btn.disabled = false;
            return;
        }
    }
    
    // 添加用户消息到UI
    addMessageToUI('user', prompt, currentImage);
    
    // 清空输入
    const imageToSend = currentImage;
    input.value = '';
    input.style.height = 'auto';
    removeInputImage();
    
    const model = document.getElementById('currentModelSelect').value;
    const modelName = getModelDisplayName(model);
    const modelAvatar = modelName.slice(0, 2).toUpperCase();
    const container = document.getElementById('chatMessages');
    const chatContainer = document.getElementById('chatContainer');
    
    // 并行处理
    if (parallelCount > 1) {
        await sendParallelMessages(prompt, imageToSend, model, modelName, modelAvatar, parallelCount, container, chatContainer);
    } else {
        await sendSingleMessage(prompt, imageToSend, model, modelName, modelAvatar, container, chatContainer);
    }
    
    btn.disabled = false;
}

// 单次消息发送（流式）
async function sendSingleMessage(prompt, imageToSend, model, modelName, modelAvatar, container, chatContainer) {
    // 添加加载状态
    const loadingId = 'loading-' + Date.now();
    
    container.innerHTML += `
        <div class="message assistant loading" id="${loadingId}">
            <div class="message-header">
                <div class="message-avatar">${modelAvatar}</div>
                <div class="message-role">${modelName}</div>
            </div>
            <div class="message-content">思考中</div>
        </div>
    `;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        const isChat = CHAT_MODELS.includes(model);
        const apiUrl = isChat ? '/api/chat' : '/api/analyze';
        
        // 构建请求参数
        const requestBody = {
            prompt,
            image: imageToSend,
            model,
            session_id: currentSessionId,
            use_context: true,
            stream: true,
            use_tools: useTools && CHAT_MODELS.includes(model)
        };
        
        // 如果是支持思考程度的模型，添加reasoning_effort参数
        if (REASONING_MODELS.includes(model)) {
            requestBody.reasoning_effort = reasoningLevel;
        }
        
        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestBody)
        });
        
        // 移除加载状态
        document.getElementById(loadingId)?.remove();
        
        // 流式处理响应
        let fullText = '';
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        
        // 添加AI消息占位
        const msgId = 'msg-' + Date.now();
        container.innerHTML += `
            <div class="message assistant" id="${msgId}">
                <div class="message-header">
                    <div class="message-avatar">${modelAvatar}</div>
                    <div class="message-role">${modelName}</div>
                </div>
                <div class="message-content" id="${msgId}-content"></div>
            </div>
        `;
        const contentEl = document.getElementById(`${msgId}-content`);
        let toolIndicator = null;
        let reasoningEl = null;
        let isInReasoning = false;
        
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;
            
            const chunk = decoder.decode(value);
            const lines = chunk.split('\n');
            
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    const data = line.slice(6);
                    if (data === '[DONE]') break;
                    try {
                        const parsed = JSON.parse(data);
                        
                        // 处理思考开始
                        if (parsed.reasoning_start) {
                            isInReasoning = true;
                            reasoningEl = document.createElement('div');
                            reasoningEl.className = 'reasoning-block';
                            reasoningEl.innerHTML = '<div class="reasoning-header">思考过程</div><div class="reasoning-content"></div>';
                            contentEl.appendChild(reasoningEl);
                        }
                        
                        // 处理思考内容
                        if (parsed.reasoning && reasoningEl) {
                            const reasoningContent = reasoningEl.querySelector('.reasoning-content');
                            reasoningContent.textContent += parsed.reasoning;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        
                        // 处理思考结束
                        if (parsed.reasoning_end) {
                            isInReasoning = false;
                            if (reasoningEl) {
                                reasoningEl.classList.add('collapsed');
                                reasoningEl.querySelector('.reasoning-header').onclick = () => {
                                    reasoningEl.classList.toggle('collapsed');
                                };
                            }
                        }
                        
                        if (parsed.content) {
                            fullText += parsed.content;
                            // 在思考块之后添加正常内容
                            let mainContent = contentEl.querySelector('.main-content');
                            if (!mainContent) {
                                mainContent = document.createElement('div');
                                mainContent.className = 'main-content';
                                contentEl.appendChild(mainContent);
                            }
                            mainContent.innerHTML = marked.parse(fullText);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        if (parsed.tool_call) {
                            const toolName = mcpTools[parsed.tool_call.name]?.display_name || parsed.tool_call.name;
                            toolIndicator = showToolCallIndicator(contentEl, toolName, true);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        if (parsed.tool_result) {
                            if (toolIndicator) {
                                toolIndicator.classList.remove('loading');
                            }
                            showToolResult(contentEl, parsed.tool_result.name, parsed.tool_result.result);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        if (parsed.error) {
                            contentEl.textContent = '错误: ' + parsed.error;
                        }
                    } catch (e) {}
                }
            }
        }
        
        // 请求完成后，重新加载会话以同步历史
        if (currentSessionId && fullText) {
            try {
                const sessionRes = await fetch(`/api/session/${currentSessionId}`);
                const sessionData = await sessionRes.json();
                chatHistory = sessionData.messages || [];
                
                // 更新会话标题（如果是第一轮对话）
                if (chatHistory.length === 2) {
                    const title = prompt.slice(0, 10);
                    const session = allSessions.find(s => s.id === currentSessionId);
                    if (session) {
                        session.title = title;
                        renderHistoryList();
                    }
                    fetch(`/api/session/${currentSessionId}/rename`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title })
                    });
                }
            } catch (e) {
                console.error('Sync session error:', e);
            }
        }
        
    } catch (e) {
        document.getElementById(loadingId)?.remove();
        addMessageToUI('assistant', '请求失败: ' + e.message);
    }
}

// 并行消息发送
async function sendParallelMessages(prompt, imageToSend, model, modelName, modelAvatar, count, container, chatContainer) {
    // 创建并行结果容器
    const parallelId = 'parallel-' + Date.now();
    container.innerHTML += `
        <div class="parallel-results" id="${parallelId}">
            <div class="parallel-header">
                <span class="parallel-title">并行处理 (${count}次)</span>
                <span class="parallel-progress" id="${parallelId}-progress">0/${count} 完成</span>
            </div>
            <div class="parallel-items" id="${parallelId}-items"></div>
        </div>
    `;
    
    const itemsContainer = document.getElementById(`${parallelId}-items`);
    const progressEl = document.getElementById(`${parallelId}-progress`);
    
    // 创建所有结果占位
    for (let i = 0; i < count; i++) {
        itemsContainer.innerHTML += `
            <div class="parallel-item" id="${parallelId}-item-${i}">
                <div class="parallel-item-header">
                    <span class="parallel-item-index">#${i + 1}</span>
                    <span class="parallel-item-status loading">处理中...</span>
                </div>
                <div class="parallel-item-content" id="${parallelId}-content-${i}">
                    <div class="loading-dots">思考中</div>
                </div>
            </div>
        `;
    }
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // 并行发送请求
    let completed = 0;
    const promises = [];
    
    for (let i = 0; i < count; i++) {
        const promise = (async (index) => {
            try {
                const isChat = CHAT_MODELS.includes(model);
                const apiUrl = isChat ? '/api/chat' : '/api/analyze';
                
                const requestBody = {
                    prompt,
                    image: imageToSend,
                    model,
                    session_id: null, // 并行请求不保存到会话
                    use_context: false,
                    stream: true,
                    use_tools: useTools && CHAT_MODELS.includes(model)
                };
                
                if (REASONING_MODELS.includes(model)) {
                    requestBody.reasoning_effort = reasoningLevel;
                }
                
                const res = await fetch(apiUrl, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(requestBody)
                });
                
                const contentEl = document.getElementById(`${parallelId}-content-${index}`);
                const statusEl = document.querySelector(`#${parallelId}-item-${index} .parallel-item-status`);
                contentEl.innerHTML = '';
                
                let fullText = '';
                const reader = res.body.getReader();
                const decoder = new TextDecoder();
                let reasoningEl = null;
                
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;
                    
                    const chunk = decoder.decode(value);
                    const lines = chunk.split('\n');
                    
                    for (const line of lines) {
                        if (line.startsWith('data: ')) {
                            const data = line.slice(6);
                            if (data === '[DONE]') break;
                            try {
                                const parsed = JSON.parse(data);
                                
                                if (parsed.reasoning_start) {
                                    reasoningEl = document.createElement('div');
                                    reasoningEl.className = 'reasoning-block collapsed';
                                    reasoningEl.innerHTML = '<div class="reasoning-header">思考</div><div class="reasoning-content"></div>';
                                    contentEl.appendChild(reasoningEl);
                                    reasoningEl.querySelector('.reasoning-header').onclick = () => {
                                        reasoningEl.classList.toggle('collapsed');
                                    };
                                }
                                
                                if (parsed.reasoning && reasoningEl) {
                                    reasoningEl.querySelector('.reasoning-content').textContent += parsed.reasoning;
                                }
                                
                                if (parsed.content) {
                                    fullText += parsed.content;
                                    let mainContent = contentEl.querySelector('.main-content');
                                    if (!mainContent) {
                                        mainContent = document.createElement('div');
                                        mainContent.className = 'main-content';
                                        contentEl.appendChild(mainContent);
                                    }
                                    mainContent.innerHTML = marked.parse(fullText);
                                }
                                
                                if (parsed.error) {
                                    contentEl.innerHTML = `<div class="error-text">错误: ${parsed.error}</div>`;
                                }
                            } catch (e) {}
                        }
                    }
                }
                
                statusEl.textContent = '完成';
                statusEl.classList.remove('loading');
                statusEl.classList.add('done');
                
                completed++;
                progressEl.textContent = `${completed}/${count} 完成`;
                
                return fullText;
            } catch (e) {
                const contentEl = document.getElementById(`${parallelId}-content-${index}`);
                const statusEl = document.querySelector(`#${parallelId}-item-${index} .parallel-item-status`);
                contentEl.innerHTML = `<div class="error-text">请求失败: ${e.message}</div>`;
                statusEl.textContent = '失败';
                statusEl.classList.remove('loading');
                statusEl.classList.add('error');
                
                completed++;
                progressEl.textContent = `${completed}/${count} 完成`;
                
                return null;
            }
        })(i);
        
        promises.push(promise);
    }
    
    // 等待所有请求完成
    const results = await Promise.all(promises);
    
    // 并行处理完成后，手动保存到会话
    const firstResult = results.find(r => r);
    if (firstResult && currentSessionId) {
        // 调用后端保存并行结果
        try {
            await fetch('/api/session/save-parallel', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    session_id: currentSessionId,
                    user_message: prompt,
                    has_image: !!imageToSend,
                    assistant_message: `[并行处理 ${count}次]\n\n${firstResult}`,
                    model: model
                })
            });
            
            // 重新加载会话以同步历史
            const sessionRes = await fetch(`/api/session/${currentSessionId}`);
            const sessionData = await sessionRes.json();
            chatHistory = sessionData.messages || [];
            
            // 更新会话标题
            if (chatHistory.length === 2) {
                const title = prompt.slice(0, 10);
                const session = allSessions.find(s => s.id === currentSessionId);
                if (session) {
                    session.title = title;
                    renderHistoryList();
                }
                fetch(`/api/session/${currentSessionId}/rename`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ title })
                });
            }
        } catch (e) {
            console.error('Save parallel result error:', e);
        }
    }
}

// ========== 模型选择 ==========
function onModelSelectChange() {
    selectedModel = document.getElementById('currentModelSelect').value;
    updateReasoningSelector();
}

function updateReasoningSelector() {
    const selector = document.getElementById('reasoningSelector');
    if (REASONING_MODELS.includes(selectedModel)) {
        selector.style.display = 'flex';
    } else {
        selector.style.display = 'none';
    }
}

function setReasoningLevel(level) {
    reasoningLevel = level;
    document.querySelectorAll('.reasoning-btn').forEach(btn => {
        btn.classList.toggle('active', btn.dataset.level === level);
    });
}

// ========== 侧边栏切换 ==========
function toggleHistorySidebar() {
    document.getElementById('historySidebar').classList.toggle('collapsed');
}

function toggleToolsSidebar() {
    document.getElementById('toolsSidebar').classList.toggle('show');
}

// ========== 图片弹窗 ==========
function showImageModal(src) {
    document.getElementById('modalImg').src = src;
    document.getElementById('imageModal').classList.add('show');
}

function hideImageModal() {
    document.getElementById('imageModal').classList.remove('show');
}

// ========== 设置 ==========
async function loadConfig() {
    try {
        const res = await fetch('/api/config');
        const config = await res.json();
        document.getElementById('apiKey').value = config.api_key || '';
        document.getElementById('apiUrl').value = config.api_url || '';
        document.getElementById('qwenApiKey').value = config.qwen_api_key || '';
        document.getElementById('deepseekApiKey').value = config.deepseek_api_key || '';
    } catch (e) {}
}

function showSettings() {
    document.getElementById('settingsModal').classList.add('show');
}

function hideSettings() {
    document.getElementById('settingsModal').classList.remove('show');
}

async function saveSettings() {
    await fetch('/api/config', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            api_key: document.getElementById('apiKey').value,
            api_url: document.getElementById('apiUrl').value,
            qwen_api_key: document.getElementById('qwenApiKey').value,
            deepseek_api_key: document.getElementById('deepseekApiKey').value
        })
    });
    hideSettings();
}

// ========== 提示词管理 ==========
async function loadPrompts() {
    try {
        const res = await fetch('/api/prompts');
        prompts = await res.json();
        renderPrompts();
    } catch (e) {}
}

function renderPrompts() {
    const list = document.getElementById('promptList');
    list.innerHTML = prompts.map((p, i) => `
        <div class="tools-prompt-item" onclick="usePrompt(${i})">
            <span>${escapeHtml(p.name)}</span>
            <button class="delete-btn" onclick="event.stopPropagation();deletePrompt('${p.name}')">×</button>
        </div>
    `).join('');
}

function usePrompt(index) {
    const textarea = document.getElementById('promptInput');
    textarea.value = prompts[index].content;
    textarea.style.height = 'auto';
    textarea.style.height = Math.min(textarea.scrollHeight, 150) + 'px';
    toggleToolsSidebar();
}

function showAddPrompt() {
    document.getElementById('promptModal').dataset.editIndex = '';
    document.getElementById('newPromptName').value = '';
    document.getElementById('newPromptContent').value = '';
    document.getElementById('promptModalTitle').textContent = '添加提示词模板';
    document.getElementById('optimizeResult').style.display = 'none';
    document.getElementById('promptModal').classList.add('show');
}

function hideAddPrompt() {
    document.getElementById('promptModal').classList.remove('show');
}

async function savePrompt() {
    const name = document.getElementById('newPromptName').value.trim();
    const content = document.getElementById('newPromptContent').value.trim();
    
    if (!name || !content) return alert('请填写完整');
    
    await fetch('/api/prompts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, content })
    });
    
    hideAddPrompt();
    loadPrompts();
}

async function deletePrompt(name) {
    if (!confirm('确定删除？')) return;
    await fetch('/api/prompts', {
        method: 'DELETE',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    });
    loadPrompts();
}

async function optimizePrompt() {
    const content = document.getElementById('newPromptContent').value.trim();
    if (!content) return alert('请先输入提示词');
    
    const btn = document.getElementById('optimizeBtn');
    btn.disabled = true;
    btn.textContent = '优化中...';
    
    try {
        const res = await fetch('/api/optimize-prompt', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt: content })
        });
        const data = await res.json();
        
        if (data.error) {
            alert('优化失败: ' + data.error);
        } else {
            optimizedPromptText = data.optimized_prompt || data.result || '';
            let html = '';
            if (data.analysis) html += `<div><b>分析:</b> ${escapeHtml(data.analysis)}</div>`;
            if (data.suggestions) html += `<div><b>建议:</b> ${escapeHtml(data.suggestions)}</div>`;
            if (optimizedPromptText) html += `<div style="margin-top:8px;padding:8px;background:#fff;border-radius:4px;">${escapeHtml(optimizedPromptText)}</div>`;
            
            document.getElementById('optimizeContent').innerHTML = html || '暂无建议';
            document.getElementById('optimizeResult').style.display = 'block';
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
    
    btn.disabled = false;
    btn.textContent = 'AI优化';
}

function applyOptimizedPrompt() {
    if (optimizedPromptText) {
        document.getElementById('newPromptContent').value = optimizedPromptText;
        document.getElementById('optimizeResult').style.display = 'none';
    }
}

// ========== 题号识别 ==========
function setupExtractUpload() {
    document.getElementById('extractFileInput').addEventListener('change', e => {
        if (e.target.files[0]) {
            const reader = new FileReader();
            reader.onload = ev => {
                extractImage = ev.target.result;
                document.getElementById('extractPreviewImg').src = extractImage;
                document.getElementById('extractUploadZone').style.display = 'none';
                document.getElementById('extractPreview').style.display = 'block';
                document.getElementById('startExtractBtn').disabled = false;
            };
            reader.readAsDataURL(e.target.files[0]);
        }
    });
}

function removeExtractImage() {
    extractImage = null;
    document.getElementById('extractFileInput').value = '';
    document.getElementById('extractUploadZone').style.display = '';
    document.getElementById('extractPreview').style.display = 'none';
    document.getElementById('startExtractBtn').disabled = true;
}

async function startExtract() {
    if (!extractImage) return;
    
    const btn = document.getElementById('startExtractBtn');
    const resultDiv = document.getElementById('questionsResult');
    
    btn.disabled = true;
    btn.textContent = '识别中...';
    resultDiv.innerHTML = '<div style="color:#999;padding:10px;">处理中...</div>';
    
    try {
        const res = await fetch('/api/extract-questions', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image: extractImage,
                prompt: document.getElementById('extractPrompt').value
            })
        });
        const data = await res.json();
        
        if (data.error) {
            resultDiv.innerHTML = `<div style="color:#d73a49;">${data.error}</div>`;
        } else {
            try {
                const match = data.result.match(/\[[\s\S]*\]/);
                if (match) {
                    extractedQuestions = JSON.parse(match[0]);
                    resultDiv.innerHTML = extractedQuestions.map(q => `
                        <div class="question-item">
                            <span class="question-index">${q.index}</span>
                            <span class="question-content">${q.content}</span>
                        </div>
                    `).join('');
                } else {
                    resultDiv.innerHTML = `<div style="white-space:pre-wrap;font-size:11px;">${data.result}</div>`;
                }
            } catch (e) {
                resultDiv.innerHTML = `<div style="white-space:pre-wrap;font-size:11px;">${data.result}</div>`;
            }
        }
    } catch (e) {
        resultDiv.innerHTML = `<div style="color:#d73a49;">错误: ${e.message}</div>`;
    }
    
    btn.disabled = false;
    btn.textContent = '开始识别';
}

// ========== 工具函数 ==========
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(isoString) {
    if (!isoString) return '';
    const date = new Date(isoString);
    const now = new Date();
    const diff = now - date;
    
    if (diff < 60000) return '刚刚';
    if (diff < 3600000) return Math.floor(diff / 60000) + '分钟前';
    if (diff < 86400000) return Math.floor(diff / 3600000) + '小时前';
    if (diff < 604800000) return Math.floor(diff / 86400000) + '天前';
    
    return date.toLocaleDateString();
}

// ========== MCP 工具管理 ==========
async function loadMcpTools() {
    try {
        const res = await fetch('/api/mcp-tools');
        mcpTools = await res.json();
        renderMcpTools();
    } catch (e) {
        console.error('Load MCP tools error:', e);
    }
}

function renderMcpTools() {
    const list = document.getElementById('mcpToolsList');
    if (!list) return;
    
    const toolsArray = Object.entries(mcpTools);
    if (toolsArray.length === 0) {
        list.innerHTML = '<div style="color:#999;font-size:12px;padding:8px;">暂无工具</div>';
        return;
    }
    
    list.innerHTML = toolsArray.map(([id, tool]) => `
        <div class="mcp-tool-item">
            <div class="mcp-tool-info">
                <div class="mcp-tool-icon ${tool.builtin ? 'builtin' : 'custom'}">
                    ${tool.builtin ? '⚡' : '⚙'}
                </div>
                <span class="mcp-tool-name">${escapeHtml(tool.display_name || tool.name)}</span>
            </div>
            <div class="mcp-tool-actions">
                <label class="toggle-switch">
                    <input type="checkbox" ${tool.enabled ? 'checked' : ''} onchange="toggleMcpTool('${id}', this.checked)">
                    <span class="toggle-slider"></span>
                </label>
                ${!tool.builtin ? `<button class="mcp-tool-delete" onclick="deleteMcpTool('${id}')">×</button>` : ''}
            </div>
        </div>
    `).join('');
}

function toggleUseTools() {
    useTools = document.getElementById('useToolsToggle').checked;
}

async function toggleMcpTool(toolId, enabled) {
    try {
        await fetch('/api/mcp-tools', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_id: toolId, enabled })
        });
        mcpTools[toolId].enabled = enabled;
    } catch (e) {
        console.error('Toggle tool error:', e);
    }
}

async function deleteMcpTool(toolId) {
    if (!confirm('确定删除此工具？')) return;
    try {
        await fetch('/api/mcp-tools', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ tool_id: toolId })
        });
        delete mcpTools[toolId];
        renderMcpTools();
    } catch (e) {
        console.error('Delete tool error:', e);
    }
}

function showAddMcpTool() {
    document.getElementById('mcpToolName').value = '';
    document.getElementById('mcpToolDesc').value = '';
    document.getElementById('mcpToolUrl').value = '';
    document.getElementById('mcpToolMethod').value = 'GET';
    document.getElementById('mcpToolModal').classList.add('show');
}

function hideMcpToolModal() {
    document.getElementById('mcpToolModal').classList.remove('show');
}

async function saveMcpTool() {
    const name = document.getElementById('mcpToolName').value.trim();
    const desc = document.getElementById('mcpToolDesc').value.trim();
    const url = document.getElementById('mcpToolUrl').value.trim();
    const method = document.getElementById('mcpToolMethod').value;
    
    if (!name || !url) {
        alert('请填写工具名称和API地址');
        return;
    }
    
    try {
        const res = await fetch('/api/mcp-tools', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                display_name: name,
                description: desc,
                api_url: url,
                method: method
            })
        });
        const data = await res.json();
        if (data.success) {
            hideMcpToolModal();
            loadMcpTools();
        } else {
            alert('添加失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

// 工具调用状态显示
function showToolCallIndicator(container, toolName, isLoading = true) {
    const indicator = document.createElement('div');
    indicator.className = `tool-call-indicator ${isLoading ? 'loading' : ''}`;
    indicator.innerHTML = `
        <span class="tool-icon"></span>
        <span>${isLoading ? '正在调用' : '已调用'}: ${escapeHtml(toolName)}</span>
    `;
    container.appendChild(indicator);
    return indicator;
}

function showToolResult(container, toolName, result) {
    const preview = document.createElement('div');
    preview.className = 'tool-result-preview';
    
    let content = '';
    if (result.results && Array.isArray(result.results)) {
        content = result.results.map(r => `• ${r.title || r.snippet || ''}`).join('\n');
    } else if (result.content) {
        content = result.content.slice(0, 200) + '...';
    } else if (result.message) {
        content = result.message;
    } else {
        content = JSON.stringify(result).slice(0, 200);
    }
    
    preview.textContent = content;
    container.appendChild(preview);
}


// ========== MCP 服务器管理 ==========
let mcpServers = {};

async function loadMcpServers() {
    try {
        const res = await fetch('/api/mcp-servers');
        const data = await res.json();
        mcpServers = data.mcpServers || {};
        renderMcpServers();
    } catch (e) {
        console.error('Load MCP servers error:', e);
    }
}

function renderMcpServers() {
    const list = document.getElementById('mcpServersList');
    if (!list) return;
    
    const servers = Object.entries(mcpServers);
    if (servers.length === 0) {
        list.innerHTML = '<div style="color:#999;font-size:12px;padding:8px;">暂无MCP服务器</div>';
        return;
    }
    
    list.innerHTML = servers.map(([name, config]) => `
        <div class="mcp-server-item">
            <div class="mcp-server-header">
                <span class="mcp-server-name">${escapeHtml(name)}</span>
                <span class="mcp-server-status ${config.running ? 'running' : ''}">${config.running ? '运行中' : '已停止'}</span>
            </div>
            <div class="mcp-server-actions">
                ${config.running 
                    ? `<button class="mcp-server-btn stop" onclick="stopMcpServer('${name}')">停止</button>`
                    : `<button class="mcp-server-btn start" onclick="startMcpServer('${name}')">启动</button>`
                }
                <button class="mcp-server-btn delete" onclick="deleteMcpServer('${name}')">删除</button>
            </div>
        </div>
    `).join('');
}

async function startMcpServer(name) {
    try {
        const res = await fetch('/api/mcp-servers', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, action: 'start' })
        });
        const data = await res.json();
        if (data.success) {
            loadMcpServers();
        } else {
            alert('启动失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}

async function stopMcpServer(name) {
    try {
        const res = await fetch('/api/mcp-servers', {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, action: 'stop' })
        });
        const data = await res.json();
        if (data.success) {
            loadMcpServers();
        }
    } catch (e) {
        console.error('Stop server error:', e);
    }
}

async function deleteMcpServer(name) {
    if (!confirm(`确定删除服务器 "${name}"？`)) return;
    try {
        const res = await fetch('/api/mcp-servers', {
            method: 'DELETE',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name })
        });
        const data = await res.json();
        if (data.success) {
            loadMcpServers();
        }
    } catch (e) {
        console.error('Delete server error:', e);
    }
}

function showAddMcpServer() {
    document.getElementById('mcpServerName').value = '';
    document.getElementById('mcpServerCommand').value = 'npx';
    document.getElementById('mcpServerArgs').value = '';
    document.getElementById('mcpServerEnv').value = '';
    document.getElementById('mcpServerModal').classList.add('show');
}

function hideMcpServerModal() {
    document.getElementById('mcpServerModal').classList.remove('show');
}

async function saveMcpServer() {
    const name = document.getElementById('mcpServerName').value.trim();
    const command = document.getElementById('mcpServerCommand').value.trim();
    const argsText = document.getElementById('mcpServerArgs').value.trim();
    const envText = document.getElementById('mcpServerEnv').value.trim();
    
    if (!name) {
        alert('请输入服务器名称');
        return;
    }
    
    // 解析参数（每行一个）
    const args = argsText ? argsText.split('\n').map(s => s.trim()).filter(s => s) : [];
    
    // 解析环境变量
    let env = {};
    if (envText) {
        try {
            env = JSON.parse(envText);
        } catch (e) {
            alert('环境变量格式错误，请使用JSON格式');
            return;
        }
    }
    
    try {
        const res = await fetch('/api/mcp-servers', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name, command, args, env })
        });
        const data = await res.json();
        if (data.success) {
            hideMcpServerModal();
            loadMcpServers();
        } else {
            alert('添加失败: ' + (data.error || '未知错误'));
        }
    } catch (e) {
        alert('请求失败: ' + e.message);
    }
}
