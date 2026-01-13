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
let firstPrinciplesMode = false; // 第一性原理分析模式
let fpConversationHistory = []; // 第一性原理对话历史

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

// 第一性原理分析系统提示词
const FIRST_PRINCIPLES_SYSTEM_PROMPT = `你是一位顶级的思考者，你的思维模型融合了物理学家（如理查德·费曼）的严谨、顶尖工程师（如埃隆·马斯克）的务实和哲学家（如亚里士多德）的深刻。你的核心能力是运用「第一性原理」来分析和解决任何问题。你不依赖类比、传统或经验，而是致力于将任何复杂问题拆解至最基本、最不容置疑的组成部分（物理定律、人性本质、数学公理等），然后从这些基石出发，重新构建解决方案。

在充满不确定性和复杂性的世界里，大多数人和组织习惯于类比思维，即复制他人的做法或在现有基础上进行微小改良。这种思维方式难以带来颠覆性创新或找到问题的根本解。我们的目标是打破常规，通过回归事物最本质的原理，共同探索出一条独特的、根本性的创新路径。你的提问和分析过程，本身就是帮助用户深度思考的价值所在。

你的任务是一个动态的、苏格拉底式的对话流程：

1. 接收初始问题：用户会提出一个问题或需求。

2. 启动提问循环：你的任务不是立即给出答案。相反，你将启动「第一性原理」分析流程，通过一系列深刻的反问，来挑战用户陈述中的每一个假设、每一个术语和每一个既定目标。

3. 多轮反问：你可能会反问多次。每一轮提问都旨在剥离一层表象，直击更深层次的本质。你的问题可能包括但不限于：
   - "我们真正想要达成的最终目标是什么？这个目标是否可以被进一步分解？"
   - "我们认为『必须』要做某件事，这个『必须』是基于一个不可动摇的物理定律，还是仅仅是一个行业惯例或过去的假设？"
   - "描述一下这个问题的基本组成部分有哪些？哪些是事实，哪些是我们的推断？"
   - "如果我们从零开始，没有任何历史包袱和现有资源的限制，我们会怎么来做来解决这个问题？"

4. 判断与确认：当你判断对话已经将问题分解到最基本的、不容置疑的"事实"或"公理"层面时，你需要向用户进行确认。例如："似乎已经触及了问题的核心：[概括总结出的核心原理]。基于这些基本原理，您希望我为您构建最终的结论或解决方案了吗？"

5. 输出最终结论：在用户确认后，基于共同确认的第一性原理，系统地、逻辑清晰地构建并输出一个创新的、根本性的最终结论或解决方案。

在整个对话过程中，你的个性应该是：
- 冷静的探究者：语气始终保持客观、中立、不带偏见
- 深刻的怀疑论者：对所有未经检验的假设都保持健康的怀疑
- 谦逊的引导者：你的提问不是为了炫耀知识，而是为了引导用户进行更深层次的思考
- 极度好奇：展现出对问题本质的强烈、纯粹的好奇心

在输出最终结论时，你必须：
- 展示推理路径：不能只给出答案，需要清晰地展示推理路径
- 首先以列表形式列出共同确认的【第一性原理清单】（即分解出的核心事实与公理）
- 然后展示如何一步步从这些原理推导出最终结论`;

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

// ========== 会话管理（本地存储） ==========
const SESSIONS_STORAGE_KEY = 'ai_chat_sessions';

function loadAllSessions() {
    try {
        const stored = localStorage.getItem(SESSIONS_STORAGE_KEY);
        allSessions = stored ? JSON.parse(stored) : [];
        renderHistoryList();
    } catch (e) {
        console.error('Load sessions error:', e);
        allSessions = [];
    }
}

function saveAllSessionsToLocal() {
    try {
        localStorage.setItem(SESSIONS_STORAGE_KEY, JSON.stringify(allSessions));
    } catch (e) {
        console.error('Save sessions error:', e);
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

function startNewChat() {
    currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    chatHistory = [];
    
    // 添加到列表顶部
    allSessions.unshift({
        id: currentSessionId,
        title: '新对话',
        messages: [],
        updated_at: new Date().toISOString()
    });
    saveAllSessionsToLocal();
    renderHistoryList();
    
    // 清空对话区域，显示欢迎界面
    document.getElementById('chatWelcome').style.display = '';
    document.getElementById('chatMessages').innerHTML = '';
    
    // 清空输入框
    document.getElementById('promptInput').value = '';
    removeInputImage();
}

function loadSession(sessionId) {
    const session = allSessions.find(s => s.id === sessionId);
    if (session) {
        currentSessionId = sessionId;
        chatHistory = session.messages || [];
        
        renderHistoryList();
        renderChatMessages();
    }
}

function renameSession(sessionId) {
    const session = allSessions.find(s => s.id === sessionId);
    const newTitle = prompt('输入新名称:', session?.title || '新对话');
    if (!newTitle) return;
    
    if (session) {
        session.title = newTitle;
        saveAllSessionsToLocal();
        renderHistoryList();
    }
}

function deleteSession(sessionId) {
    if (!confirm('确定删除此对话？')) return;
    
    allSessions = allSessions.filter(s => s.id !== sessionId);
    saveAllSessionsToLocal();
    
    if (sessionId === currentSessionId) {
        if (allSessions.length > 0) {
            loadSession(allSessions[0].id);
        } else {
            currentSessionId = null;
            chatHistory = [];
            document.getElementById('chatWelcome').style.display = '';
            document.getElementById('chatMessages').innerHTML = '';
        }
    } else {
        renderHistoryList();
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
    // 检查是否已登录
    if (!currentUser) {
        showLoginModal();
        return;
    }
    
    const input = document.getElementById('promptInput');
    const prompt = input.value.trim();
    
    if (!prompt && !currentImage) return;
    
    const btn = document.getElementById('sendBtn');
    btn.disabled = true;
    
    // 清空输入
    input.value = '';
    input.style.height = 'auto';
    
    // 如果是第一性原理模式，使用专门的处理函数
    if (firstPrinciplesMode) {
        await sendFirstPrinciplesMessage(prompt);
        btn.disabled = false;
        return;
    }
    
    // 获取并行数量
    const parallelCount = parseInt(document.getElementById('parallelCount').value) || 1;
    
    // 如果没有当前会话，先创建一个（本地）
    if (!currentSessionId) {
        currentSessionId = 'session_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        chatHistory = [];
        allSessions.unshift({
            id: currentSessionId,
            title: '新对话',
            messages: [],
            updated_at: new Date().toISOString()
        });
        saveAllSessionsToLocal();
        renderHistoryList();
    }
    
    // 添加用户消息到UI
    addMessageToUI('user', prompt, currentImage);
    
    // 清空输入
    const imageToSend = currentImage;
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
            session_id: null,  // 不使用服务器端会话存储
            use_context: false,
            stream: true,
            use_tools: useTools && CHAT_MODELS.includes(model)
        };
        
        // 如果是支持思考程度的模型，添加reasoning_effort参数
        if (REASONING_MODELS.includes(model)) {
            requestBody.reasoning_effort = reasoningLevel;
        }
        
        const res = await fetch(apiUrl, {
            method: 'POST',
            headers: getApiHeaders(),
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
        
        // 请求完成后，保存到本地存储
        if (currentSessionId && fullText) {
            // 添加用户消息和AI回复到历史
            const userMsg = { role: 'user', content: prompt, image: imageToSend };
            const assistantMsg = { role: 'assistant', content: fullText, model: model };
            chatHistory.push(userMsg, assistantMsg);
            
            // 更新会话
            const session = allSessions.find(s => s.id === currentSessionId);
            if (session) {
                session.messages = chatHistory;
                session.updated_at = new Date().toISOString();
                
                // 更新会话标题（如果是第一轮对话）
                if (chatHistory.length === 2) {
                    session.title = prompt.slice(0, 10);
                }
                
                // 移到列表顶部
                allSessions = allSessions.filter(s => s.id !== currentSessionId);
                allSessions.unshift(session);
                
                saveAllSessionsToLocal();
                renderHistoryList();
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
                    headers: getApiHeaders(),
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
    
    // 并行处理完成后，保存到本地存储
    const firstResult = results.find(r => r);
    if (firstResult && currentSessionId) {
        // 添加用户消息和AI回复到历史
        const userMsg = { role: 'user', content: prompt, image: imageToSend };
        const assistantMsg = { role: 'assistant', content: `[并行处理 ${count}次]\n\n${firstResult}`, model: model };
        chatHistory.push(userMsg, assistantMsg);
        
        // 更新会话
        const session = allSessions.find(s => s.id === currentSessionId);
        if (session) {
            session.messages = chatHistory;
            session.updated_at = new Date().toISOString();
            
            // 更新会话标题（如果是第一轮对话）
            if (chatHistory.length === 2) {
                session.title = prompt.slice(0, 10);
            }
            
            // 移到列表顶部
            allSessions = allSessions.filter(s => s.id !== currentSessionId);
            allSessions.unshift(session);
            
            saveAllSessionsToLocal();
            renderHistoryList();
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
        // 从localStorage加载API密钥
        const savedKeys = JSON.parse(localStorage.getItem('ai_api_keys') || '{}');
        document.getElementById('apiKey').value = savedKeys.doubao || '';
        document.getElementById('gptApiKey').value = savedKeys.gpt || '';
        document.getElementById('deepseekApiKey').value = savedKeys.deepseek || '';
        document.getElementById('qwenApiKey').value = savedKeys.qwen || '';
        
        // 从服务器加载其他配置
        const res = await fetch('/api/config');
        const config = await res.json();
        document.getElementById('apiUrl').value = config.api_url || '';
        document.getElementById('gptApiUrl').value = config.gpt_api_url || 'https://api.gpt.ge/v1/chat/completions';
        
        // 加载数据库配置
        if (config.mysql) {
            document.getElementById('mysqlHost').value = config.mysql.host || '';
            document.getElementById('mysqlPort').value = config.mysql.port || 3306;
            document.getElementById('mysqlUser').value = config.mysql.user || '';
            document.getElementById('mysqlPassword').value = config.mysql.password || '';
            document.getElementById('mysqlDatabase').value = config.mysql.database || '';
        }
        if (config.app_mysql) {
            document.getElementById('appMysqlHost').value = config.app_mysql.host || '';
            document.getElementById('appMysqlPort').value = config.app_mysql.port || 3306;
            document.getElementById('appMysqlUser').value = config.app_mysql.user || '';
            document.getElementById('appMysqlPassword').value = config.app_mysql.password || '';
            document.getElementById('appMysqlDatabase').value = config.app_mysql.database || '';
        }
    } catch (e) {}
}

function showSettings() {
    document.getElementById('settingsModal').classList.add('show');
    switchSettingsTab('api');
}

function hideSettings() {
    document.getElementById('settingsModal').classList.remove('show');
    document.getElementById('settingsStatus').textContent = '';
}

function switchSettingsTab(tab) {
    // 更新标签页状态
    document.querySelectorAll('.settings-tab').forEach(t => {
        t.classList.toggle('active', t.textContent.includes(tab === 'api' ? 'API' : '数据库'));
    });
    
    // 显示对应面板
    document.getElementById('settingsPanel_api').style.display = tab === 'api' ? 'block' : 'none';
    document.getElementById('settingsPanel_database').style.display = tab === 'database' ? 'block' : 'none';
}

async function validateApiKey(type) {
    const statusEl = document.getElementById('settingsStatus');
    const inputMap = {
        'doubao': 'apiKey',
        'deepseek': 'deepseekApiKey',
        'qwen': 'qwenApiKey'
    };
    const apiKey = document.getElementById(inputMap[type]).value;
    
    if (!apiKey) {
        statusEl.textContent = '请先输入API密钥';
        statusEl.className = 'settings-status error';
        return;
    }
    
    statusEl.textContent = '正在验证...';
    statusEl.className = 'settings-status';
    
    try {
        const res = await fetch('/api/validate-api-key', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ type, api_key: apiKey })
        });
        const result = await res.json();
        
        if (result.valid) {
            statusEl.textContent = '验证成功';
            statusEl.className = 'settings-status success';
        } else {
            statusEl.textContent = '验证失败: ' + (result.error || '未知错误');
            statusEl.className = 'settings-status error';
        }
    } catch (e) {
        statusEl.textContent = '验证请求失败: ' + e.message;
        statusEl.className = 'settings-status error';
    }
    
    setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'settings-status';
    }, 3000);
}

async function testDatabaseConnection(type) {
    const statusEl = document.getElementById('settingsStatus');
    statusEl.textContent = '正在测试连接...';
    statusEl.className = 'settings-status';
    
    let data = { type };
    
    if (type === 'main') {
        data.host = document.getElementById('mysqlHost').value;
        data.port = document.getElementById('mysqlPort').value;
        data.user = document.getElementById('mysqlUser').value;
        data.password = document.getElementById('mysqlPassword').value;
        data.database = document.getElementById('mysqlDatabase').value;
    } else {
        data.host = document.getElementById('appMysqlHost').value;
        data.port = document.getElementById('appMysqlPort').value;
        data.user = document.getElementById('appMysqlUser').value;
        data.password = document.getElementById('appMysqlPassword').value;
        data.database = document.getElementById('appMysqlDatabase').value;
    }
    
    try {
        const res = await fetch('/api/test-database', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(data)
        });
        const result = await res.json();
        
        if (result.success) {
            statusEl.textContent = '连接成功';
            statusEl.className = 'settings-status success';
        } else {
            statusEl.textContent = result.error || '连接失败';
            statusEl.className = 'settings-status error';
        }
    } catch (e) {
        statusEl.textContent = '请求失败: ' + e.message;
        statusEl.className = 'settings-status error';
    }
    
    setTimeout(() => {
        statusEl.textContent = '';
        statusEl.className = 'settings-status';
    }, 5000);
}

async function saveSettings() {
    const statusEl = document.getElementById('settingsStatus');
    statusEl.textContent = '正在保存...';
    
    // 保存API密钥到localStorage
    const apiKeys = {
        doubao: document.getElementById('apiKey').value,
        gpt: document.getElementById('gptApiKey').value,
        deepseek: document.getElementById('deepseekApiKey').value,
        qwen: document.getElementById('qwenApiKey').value
    };
    localStorage.setItem('ai_api_keys', JSON.stringify(apiKeys));
    
    // 保存配置到服务器（包含API密钥）
    const config = {
        api_key: apiKeys.doubao,
        gpt_api_key: apiKeys.gpt,
        deepseek_api_key: apiKeys.deepseek,
        qwen_api_key: apiKeys.qwen,
        api_url: document.getElementById('apiUrl').value,
        gpt_api_url: document.getElementById('gptApiUrl').value,
        mysql: {
            host: document.getElementById('mysqlHost').value,
            port: parseInt(document.getElementById('mysqlPort').value) || 3306,
            user: document.getElementById('mysqlUser').value,
            password: document.getElementById('mysqlPassword').value,
            database: document.getElementById('mysqlDatabase').value
        },
        app_mysql: {
            host: document.getElementById('appMysqlHost').value,
            port: parseInt(document.getElementById('appMysqlPort').value) || 3306,
            user: document.getElementById('appMysqlUser').value,
            password: document.getElementById('appMysqlPassword').value,
            database: document.getElementById('appMysqlDatabase').value
        }
    };
    
    try {
        await fetch('/api/config', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(config)
        });
        statusEl.textContent = '保存成功';
        statusEl.className = 'settings-status success';
        setTimeout(() => hideSettings(), 1500);
    } catch (e) {
        statusEl.textContent = '保存失败: ' + e.message;
        statusEl.className = 'settings-status error';
    }
}

// 获取API请求头（包含localStorage中的API密钥）
function getApiHeaders() {
    const headers = { 'Content-Type': 'application/json' };
    const savedKeys = JSON.parse(localStorage.getItem('ai_api_keys') || '{}');
    
    if (savedKeys.doubao) headers['X-Doubao-Api-Key'] = savedKeys.doubao;
    if (savedKeys.gpt) headers['X-Gpt-Api-Key'] = savedKeys.gpt;
    if (savedKeys.deepseek) headers['X-Deepseek-Api-Key'] = savedKeys.deepseek;
    if (savedKeys.qwen) headers['X-Qwen-Api-Key'] = savedKeys.qwen;
    
    return headers;
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
            headers: getApiHeaders(),
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
            headers: getApiHeaders(),
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

// ========== 用户认证 ==========
let currentUser = null;

// 检查登录状态
async function checkAuthStatus() {
    try {
        const res = await fetch('/api/auth/status');
        const data = await res.json();
        if (data.logged_in) {
            currentUser = data.user;
            updateUserUI(true);
            // 加载用户的API密钥
            loadUserApiKeys();
        } else {
            currentUser = null;
            updateUserUI(false);
        }
    } catch (e) {
        console.error('Check auth status error:', e);
        currentUser = null;
        updateUserUI(false);
    }
}

// 更新用户界面
function updateUserUI(loggedIn) {
    const avatarBtn = document.getElementById('userAvatarBtn');
    const avatarIcon = document.getElementById('avatarIcon');
    const avatarLetter = document.getElementById('avatarLetter');
    const dropdownHeader = document.getElementById('userDropdownHeader');
    
    if (loggedIn && currentUser) {
        avatarBtn.classList.add('logged-in');
        avatarIcon.style.display = 'none';
        avatarLetter.style.display = '';
        avatarLetter.textContent = currentUser.username.charAt(0).toUpperCase();
        dropdownHeader.textContent = currentUser.username;
    } else {
        avatarBtn.classList.remove('logged-in');
        avatarIcon.style.display = '';
        avatarLetter.style.display = 'none';
        dropdownHeader.textContent = '';
    }
}

// 切换用户菜单
function toggleUserMenu() {
    if (!currentUser) {
        showLoginModal();
        return;
    }
    
    const dropdown = document.getElementById('userDropdown');
    dropdown.classList.toggle('show');
    
    // 点击外部关闭
    if (dropdown.classList.contains('show')) {
        setTimeout(() => {
            document.addEventListener('click', closeUserMenuOnClickOutside);
        }, 0);
    }
}

function closeUserMenuOnClickOutside(e) {
    const wrapper = document.getElementById('userAvatarWrapper');
    if (!wrapper.contains(e.target)) {
        document.getElementById('userDropdown').classList.remove('show');
        document.removeEventListener('click', closeUserMenuOnClickOutside);
    }
}

// 显示登录弹窗
function showLoginModal() {
    document.getElementById('loginUsername').value = '';
    document.getElementById('loginPassword').value = '';
    document.getElementById('loginRemember').checked = true;
    document.getElementById('loginError').style.display = 'none';
    document.getElementById('loginModal').classList.add('show');
    document.getElementById('loginUsername').focus();
}

// 隐藏登录弹窗
function hideLoginModal() {
    document.getElementById('loginModal').classList.remove('show');
}

// 处理登录
async function handleLogin() {
    const username = document.getElementById('loginUsername').value.trim();
    const password = document.getElementById('loginPassword').value;
    const remember = document.getElementById('loginRemember').checked;
    const errorEl = document.getElementById('loginError');
    const loginBtn = document.getElementById('loginBtn');
    
    if (!username) {
        errorEl.textContent = '请输入用户名';
        errorEl.style.display = '';
        return;
    }
    if (!password) {
        errorEl.textContent = '请输入密码';
        errorEl.style.display = '';
        return;
    }
    
    loginBtn.disabled = true;
    loginBtn.textContent = '登录中...';
    errorEl.style.display = 'none';
    
    try {
        const res = await fetch('/api/auth/login', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ username, password, remember })
        });
        const data = await res.json();
        
        if (data.success) {
            currentUser = data.user;
            updateUserUI(true);
            hideLoginModal();
            // 加载用户的API密钥
            loadUserApiKeys();
            // 刷新会话列表
            loadAllSessions();
        } else {
            errorEl.textContent = data.error || '登录失败';
            errorEl.style.display = '';
        }
    } catch (e) {
        errorEl.textContent = '网络错误，请重试';
        errorEl.style.display = '';
    } finally {
        loginBtn.disabled = false;
        loginBtn.textContent = '登录';
    }
}

// 处理登出
async function handleLogout() {
    try {
        await fetch('/api/auth/logout', { method: 'POST' });
    } catch (e) {
        console.error('Logout error:', e);
    }
    
    currentUser = null;
    updateUserUI(false);
    document.getElementById('userDropdown').classList.remove('show');
}

// 加载用户API密钥
async function loadUserApiKeys() {
    if (!currentUser) return;
    
    try {
        const res = await fetch('/api/auth/api-keys');
        const keys = await res.json();
        
        // 如果用户有保存的密钥，更新到localStorage并刷新输入框
        if (keys.doubao_key || keys.deepseek_key || keys.qwen_key || keys.gpt_key) {
            const apiKeys = {
                doubao: keys.doubao_key || '',
                gpt: keys.gpt_key || '',
                deepseek: keys.deepseek_key || '',
                qwen: keys.qwen_key || ''
            };
            localStorage.setItem('ai_api_keys', JSON.stringify(apiKeys));
            
            // 刷新输入框显示
            document.getElementById('apiKey').value = apiKeys.doubao;
            document.getElementById('gptApiKey').value = apiKeys.gpt;
            document.getElementById('deepseekApiKey').value = apiKeys.deepseek;
            document.getElementById('qwenApiKey').value = apiKeys.qwen;
        }
    } catch (e) {
        console.error('Load user API keys error:', e);
    }
}

// 保存用户API密钥
async function saveUserApiKeys() {
    if (!currentUser) return;
    
    const savedKeys = JSON.parse(localStorage.getItem('ai_api_keys') || '{}');
    const keys = {
        doubao_key: savedKeys.doubao || '',
        gpt_key: savedKeys.gpt || '',
        deepseek_key: savedKeys.deepseek || '',
        qwen_key: savedKeys.qwen || ''
    };
    
    try {
        await fetch('/api/auth/api-keys', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(keys)
        });
    } catch (e) {
        console.error('Save user API keys error:', e);
    }
}

// 登录弹窗键盘事件
document.addEventListener('keydown', (e) => {
    const loginModal = document.getElementById('loginModal');
    if (loginModal.classList.contains('show')) {
        if (e.key === 'Escape') {
            hideLoginModal();
        } else if (e.key === 'Enter') {
            handleLogin();
        }
    }
});

// 点击弹窗外部关闭
document.getElementById('loginModal')?.addEventListener('click', (e) => {
    if (e.target.id === 'loginModal') {
        hideLoginModal();
    }
});

// 页面加载时检查登录状态
document.addEventListener('DOMContentLoaded', () => {
    checkAuthStatus();
});


// ========== 第一性原理分析模式 ==========
function toggleFirstPrinciplesMode() {
    firstPrinciplesMode = !firstPrinciplesMode;
    const btn = document.getElementById('firstPrinciplesBtn');
    const welcome = document.getElementById('chatWelcome');
    const welcomeTitle = document.getElementById('welcomeTitle');
    const welcomeDesc = document.getElementById('welcomeDesc');
    const inputArea = document.querySelector('.input-area');
    const mainWrapper = document.getElementById('mainWrapper');
    const modelSelector = document.querySelector('.model-selector');
    
    if (firstPrinciplesMode) {
        // 进入第一性原理模式
        btn.classList.add('active');
        mainWrapper.classList.add('first-principles-mode-active');
        
        // 清空当前对话，开始新的第一性原理分析
        fpConversationHistory = [];
        chatHistory = [];
        currentSessionId = null;
        
        // 更新欢迎界面
        welcome.style.display = '';
        welcome.classList.add('first-principles-mode');
        welcomeTitle.textContent = '第一性原理分析';
        welcomeDesc.textContent = '输入你想要分析的问题或需求，我将通过苏格拉底式的对话，帮助你剥离表象、回归本质，从最基本的原理出发重新构建解决方案。';
        
        // 输入框居中
        inputArea.classList.add('first-principles-centered');
        
        // 清空消息区域
        document.getElementById('chatMessages').innerHTML = '';
        
        // 隐藏模型选择器（固定使用DeepSeek V3.2）
        modelSelector.style.display = 'none';
        
        // 更新输入框placeholder
        document.getElementById('promptInput').placeholder = '输入你想要分析的问题或需求...';
    } else {
        // 退出第一性原理模式
        btn.classList.remove('active');
        mainWrapper.classList.remove('first-principles-mode-active');
        
        // 恢复欢迎界面
        welcome.classList.remove('first-principles-mode');
        welcomeTitle.textContent = 'AI 助手';
        welcomeDesc.textContent = '选择模型开始对话，支持图片识别与日常聊天';
        
        // 恢复输入框位置
        inputArea.classList.remove('first-principles-centered');
        
        // 显示模型选择器
        modelSelector.style.display = '';
        
        // 恢复输入框placeholder
        document.getElementById('promptInput').placeholder = '输入消息...';
        
        // 清空第一性原理对话历史
        fpConversationHistory = [];
        
        // 如果有历史对话，加载最近的一个
        if (allSessions.length > 0) {
            loadSession(allSessions[0].id);
        }
    }
}

// 发送第一性原理分析消息
async function sendFirstPrinciplesMessage(prompt) {
    const container = document.getElementById('chatMessages');
    const chatContainer = document.getElementById('chatContainer');
    const welcome = document.getElementById('chatWelcome');
    const inputArea = document.querySelector('.input-area');
    
    // 隐藏欢迎界面，恢复输入框位置
    welcome.style.display = 'none';
    inputArea.classList.remove('first-principles-centered');
    
    // 添加用户消息到UI
    container.innerHTML += renderFpUserMessage(prompt);
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    // 添加到对话历史
    fpConversationHistory.push({ role: 'user', content: prompt });
    
    // 添加加载状态
    const loadingId = 'loading-' + Date.now();
    container.innerHTML += `
        <div class="message assistant loading" id="${loadingId}">
            <div class="message-header">
                <div class="message-avatar">FP</div>
                <div class="message-role">第一性原理分析</div>
            </div>
            <div class="message-content">深度思考中...</div>
        </div>
    `;
    chatContainer.scrollTop = chatContainer.scrollHeight;
    
    try {
        const res = await fetch('/api/first-principles', {
            method: 'POST',
            headers: getApiHeaders(),
            body: JSON.stringify({
                prompt: prompt,
                history: fpConversationHistory.slice(0, -1),
                stream: true
            })
        });
        
        // 移除加载状态
        document.getElementById(loadingId)?.remove();
        
        // 流式处理响应
        let fullText = '';
        let reasoningText = '';
        let usageData = null;
        let requestDebug = null;
        let isInReasoning = false;
        const reader = res.body.getReader();
        const decoder = new TextDecoder();
        
        // 添加AI消息占位
        const msgId = 'fp-msg-' + Date.now();
        container.innerHTML += `
            <div class="message assistant fp-message" id="${msgId}">
                <div class="message-header">
                    <div class="message-avatar">FP</div>
                    <div class="message-role">第一性原理分析</div>
                    <div class="fp-token-stats" id="${msgId}-tokens" style="display: none;"></div>
                    <button class="fp-raw-btn" onclick="toggleFpRawData('${msgId}')" title="查看原始数据">RAW</button>
                </div>
                <div class="message-content" id="${msgId}-content"></div>
                <div class="fp-raw-data" id="${msgId}-raw" style="display: none;"></div>
            </div>
        `;
        const contentEl = document.getElementById(`${msgId}-content`);
        const tokensEl = document.getElementById(`${msgId}-tokens`);
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
                        
                        // 处理请求调试信息
                        if (parsed.request_debug) {
                            requestDebug = parsed.request_debug;
                        }
                        
                        // 处理推理开始
                        if (parsed.reasoning_start) {
                            isInReasoning = true;
                            reasoningEl = document.createElement('div');
                            reasoningEl.className = 'fp-reasoning-block';
                            reasoningEl.innerHTML = '<div class="fp-reasoning-header"><span class="fp-reasoning-icon">&#9881;</span>深度推理中...</div><div class="fp-reasoning-content"></div>';
                            contentEl.appendChild(reasoningEl);
                        }
                        
                        // 处理推理内容
                        if (parsed.reasoning && reasoningEl) {
                            reasoningText += parsed.reasoning;
                            const reasoningContent = reasoningEl.querySelector('.fp-reasoning-content');
                            reasoningContent.textContent = reasoningText;
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        
                        // 处理推理结束
                        if (parsed.reasoning_end && reasoningEl) {
                            isInReasoning = false;
                            // 更新标题并折叠
                            const header = reasoningEl.querySelector('.fp-reasoning-header');
                            header.innerHTML = '<span class="fp-reasoning-icon">&#9881;</span>深度推理过程 <span class="fp-reasoning-toggle">展开</span>';
                            reasoningEl.classList.add('collapsed');
                            header.onclick = () => {
                                reasoningEl.classList.toggle('collapsed');
                                const toggle = header.querySelector('.fp-reasoning-toggle');
                                toggle.textContent = reasoningEl.classList.contains('collapsed') ? '展开' : '收起';
                            };
                        }
                        
                        // 处理正常内容
                        if (parsed.content) {
                            fullText += parsed.content;
                            // 在推理块之后添加正常内容
                            let mainContent = contentEl.querySelector('.fp-main-content');
                            if (!mainContent) {
                                mainContent = document.createElement('div');
                                mainContent.className = 'fp-main-content';
                                contentEl.appendChild(mainContent);
                            }
                            mainContent.innerHTML = renderFpContent(fullText);
                            chatContainer.scrollTop = chatContainer.scrollHeight;
                        }
                        
                        if (parsed.usage) {
                            usageData = parsed.usage;
                        }
                        if (parsed.error) {
                            contentEl.textContent = '错误: ' + parsed.error;
                        }
                    } catch (e) {}
                }
            }
        }
        
        // 显示token统计
        if (usageData && tokensEl) {
            const promptTokens = usageData.prompt_tokens || 0;
            const completionTokens = usageData.completion_tokens || 0;
            const reasoningTokens = usageData.reasoning_tokens || usageData.completion_tokens_details?.reasoning_tokens || 0;
            const totalTokens = usageData.total_tokens || (promptTokens + completionTokens);
            
            let tokenText = `<span class="token-label">Token:</span> ${promptTokens} + ${completionTokens} = ${totalTokens}`;
            if (reasoningTokens > 0) {
                tokenText += ` <span class="token-reasoning">(推理: ${reasoningTokens})</span>`;
            }
            tokensEl.innerHTML = tokenText;
            tokensEl.style.display = '';
        }
        
        // 保存原始数据（包含用户提问和API请求）
        const rawEl = document.getElementById(`${msgId}-raw`);
        if (rawEl) {
            const rawData = {
                request: requestDebug,
                prompt: prompt,
                reasoning: reasoningText,
                content: fullText,
                usage: usageData
            };
            rawEl.textContent = JSON.stringify(rawData, null, 2);
        }
        
        // 添加到对话历史
        if (fullText) {
            fpConversationHistory.push({ role: 'assistant', content: fullText });
            
            // 检查是否包含问题组或核心问题，添加内联输入框
            if ((fullText.includes('【问题组】') || fullText.includes('【核心问题】')) && !fullText.includes('【分析完成】')) {
                addFpInlineInput(msgId);
            }
        }
        
        chatContainer.scrollTop = chatContainer.scrollHeight;
        
    } catch (e) {
        document.getElementById(loadingId)?.remove();
        container.innerHTML += `
            <div class="message assistant">
                <div class="message-header">
                    <div class="message-avatar">FP</div>
                    <div class="message-role">第一性原理分析</div>
                </div>
                <div class="message-content" style="color: var(--error-color);">请求失败: ${escapeHtml(e.message)}</div>
            </div>
        `;
    }
}

// 渲染第一性原理用户消息
function renderFpUserMessage(content) {
    return `
        <div class="message user">
            <div class="message-header">
                <div class="message-avatar">U</div>
                <div class="message-role">你</div>
            </div>
            <div class="message-content">${escapeHtml(content)}</div>
        </div>
    `;
}

// 渲染第一性原理内容（模块化格式）
function renderFpContent(text) {
    let html = marked.parse(text);
    
    // 美化【当前阶段】
    html = html.replace(/【当前阶段】([^<\n]+)/g, '<div class="fp-stage">$1</div>');
    
    // 美化【问题组】- 新增多问题支持
    html = html.replace(/【问题组】/g, '<div class="fp-question-group-label">问题组</div>');
    
    // 美化【核心问题】（保留兼容）
    html = html.replace(/【核心问题】/g, '<div class="fp-question-label">核心问题</div>');
    
    // 美化【分析要点】
    html = html.replace(/【分析要点】/g, '<div class="fp-section-title">分析要点</div>');
    
    // 美化【思考提示】
    html = html.replace(/【思考提示】([^<\n]+)/g, '<div class="fp-hint">$1</div>');
    
    // 美化【分析完成】
    html = html.replace(/【分析完成】/g, '<div class="fp-stage fp-stage-complete">分析完成</div>');
    
    // 美化【第一性原理清单】
    html = html.replace(/【第一性原理清单】/g, '<div class="fp-conclusion-title">第一性原理清单</div>');
    
    // 美化【推理路径】
    html = html.replace(/【推理路径】/g, '<div class="fp-conclusion-title">推理路径</div>');
    
    // 美化【最终方案】
    html = html.replace(/【最终方案】/g, '<div class="fp-conclusion-title">最终方案</div>');
    
    // 美化【创新点】
    html = html.replace(/【创新点】/g, '<div class="fp-conclusion-title">创新点</div>');
    
    // 美化引用块中的问题
    html = html.replace(/<blockquote>\s*<p>([^<]+)<\/p>\s*<\/blockquote>/g, 
        '<div class="fp-question-box"><div class="fp-question-text">$1</div></div>');
    
    return html;
}

// 添加内联输入框（支持多问题）
function addFpInlineInput(msgId) {
    const contentEl = document.getElementById(`${msgId}-content`);
    if (!contentEl) return;
    
    // 检查是否已经有输入框
    if (contentEl.querySelector('.fp-inline-input-group')) return;
    
    const inputGroupId = 'fp-input-group-' + Date.now();
    const inputHtml = `
        <div class="fp-inline-input-group" id="${inputGroupId}">
            <div class="fp-input-header">请回答上述问题</div>
            <textarea id="${inputGroupId}-textarea" class="fp-multi-input" placeholder="在这里输入你对上述问题的回答...&#10;可以逐一回答，也可以综合回答" rows="4"></textarea>
            <div class="fp-input-footer">
                <span class="fp-input-hint">按 Ctrl+Enter 发送</span>
                <button onclick="submitFpMultiAnswer('${inputGroupId}')">提交回答</button>
            </div>
        </div>
    `;
    
    contentEl.innerHTML += inputHtml;
    
    // 聚焦输入框并添加快捷键
    setTimeout(() => {
        const textarea = document.getElementById(`${inputGroupId}-textarea`);
        if (textarea) {
            textarea.focus();
            textarea.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && e.ctrlKey) {
                    e.preventDefault();
                    submitFpMultiAnswer(inputGroupId);
                }
            });
        }
    }, 100);
}

// 提交多问题回答
async function submitFpMultiAnswer(inputGroupId) {
    const textarea = document.getElementById(`${inputGroupId}-textarea`);
    if (!textarea) return;
    
    const answer = textarea.value.trim();
    if (!answer) return;
    
    // 禁用输入框和按钮
    textarea.disabled = true;
    const btn = textarea.closest('.fp-inline-input-group').querySelector('button');
    if (btn) {
        btn.disabled = true;
        btn.textContent = '发送中...';
    }
    
    // 发送回答
    await sendFirstPrinciplesMessage(answer);
    
    // 移除已使用的输入框
    const inputGroup = document.getElementById(inputGroupId);
    if (inputGroup) {
        inputGroup.remove();
    }
}

// 切换原始数据显示
function toggleFpRawData(msgId) {
    const rawEl = document.getElementById(`${msgId}-raw`);
    if (rawEl) {
        const isHidden = rawEl.style.display === 'none';
        rawEl.style.display = isHidden ? 'block' : 'none';
    }
}

// 处理内联输入框键盘事件（保留兼容）
function handleFpInputKeydown(event, inputId) {
    if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault();
        submitFpInlineAnswer(inputId);
    }
}

// 提交内联回答（保留兼容）
async function submitFpInlineAnswer(inputId) {
    const input = document.getElementById(inputId);
    if (!input) return;
    
    const answer = input.value.trim();
    if (!answer) return;
    
    // 禁用输入框和按钮
    input.disabled = true;
    const btn = input.nextElementSibling;
    if (btn) {
        btn.disabled = true;
        btn.textContent = '发送中...';
    }
    
    // 发送回答
    await sendFirstPrinciplesMessage(answer);
    
    // 移除已使用的输入框
    const inputWrapper = input.closest('.fp-inline-input');
    if (inputWrapper) {
        inputWrapper.remove();
    }
}

