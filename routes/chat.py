"""
聊天与 MCP 工具路由模块
提供聊天 API、MCP 服务器和工具管理功能
"""
import os
import json
import uuid
import time
import requests
import subprocess
from datetime import datetime
from flask import Blueprint, request, jsonify, Response

from services.config_service import ConfigService
from services.session_service import SessionService
from routes.auth import get_current_user_id

chat_bp = Blueprint('chat', __name__)

# MCP 配置文件
MCP_SERVERS_FILE = 'mcp_servers.json'
MCP_TOOLS_FILE = 'mcp_tools.json'

# MCP 服务器进程管理
_mcp_server_processes = {}

# 必应搜索缓存
_bing_search_cache = {}

# 热点来源配置
TRENDING_SOURCES = {
    'weibo': {'name': '微博热搜'},
    'zhihu': {'name': '知乎热榜'},
    'toutiao': {'name': '今日头条'},
    'douyin': {'name': '抖音热搜'},
    'bilibili': {'name': 'B站热门'},
    'douban': {'name': '豆瓣热门'},
    '36kr': {'name': '36氪热榜'},
    'juejin': {'name': '掘金热榜'},
    'baidu': {'name': '百度热搜'}
}

# 默认 MCP 工具
DEFAULT_MCP_TOOLS = {
    'bing_search': {
        'name': 'bing_search',
        'display_name': '必应搜索',
        'description': '搜索互联网获取最新信息',
        'enabled': True,
        'builtin': True,
        'parameters': {
            'type': 'object',
            'properties': {
                'query': {'type': 'string', 'description': '搜索关键词'},
                'num_results': {'type': 'integer', 'description': '返回结果数量', 'default': 5}
            },
            'required': ['query']
        }
    },
    'fetch_url': {
        'name': 'fetch_url',
        'display_name': '网页抓取',
        'description': '抓取指定URL的网页内容',
        'enabled': True,
        'builtin': True,
        'parameters': {
            'type': 'object',
            'properties': {
                'url': {'type': 'string', 'description': '要抓取的网页URL'},
                'max_length': {'type': 'integer', 'description': '最大返回字符数', 'default': 5000}
            },
            'required': ['url']
        }
    },
    'get_trending': {
        'name': 'get_trending',
        'display_name': '热点新闻',
        'description': '获取各平台热点新闻',
        'enabled': True,
        'builtin': True,
        'parameters': {
            'type': 'object',
            'properties': {
                'source': {'type': 'string', 'description': '来源平台', 'enum': list(TRENDING_SOURCES.keys())},
                'limit': {'type': 'integer', 'description': '返回数量', 'default': 10}
            }
        }
    }
}


def load_mcp_servers():
    """加载MCP服务器配置"""
    if os.path.exists(MCP_SERVERS_FILE):
        with open(MCP_SERVERS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {'mcpServers': {}}


def save_mcp_servers(config):
    """保存MCP服务器配置"""
    with open(MCP_SERVERS_FILE, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=2)


def load_mcp_tools():
    """加载MCP工具配置"""
    if os.path.exists(MCP_TOOLS_FILE):
        with open(MCP_TOOLS_FILE, 'r', encoding='utf-8') as f:
            tools = json.load(f)
            # 合并默认工具
            for key, tool in DEFAULT_MCP_TOOLS.items():
                if key not in tools:
                    tools[key] = tool
                else:
                    enabled = tools[key].get('enabled', True)
                    tools[key] = {**tool, 'enabled': enabled}
            return tools
    return DEFAULT_MCP_TOOLS.copy()


def save_mcp_tools(tools):
    """保存MCP工具配置"""
    with open(MCP_TOOLS_FILE, 'w', encoding='utf-8') as f:
        json.dump(tools, f, ensure_ascii=False, indent=2)


def get_enabled_tools():
    """获取已启用的工具列表（OpenAI function格式）"""
    tools = load_mcp_tools()
    enabled = []
    
    for key, tool in tools.items():
        if tool.get('enabled', True):
            enabled.append({
                'type': 'function',
                'function': {
                    'name': tool['name'],
                    'description': tool['description'],
                    'parameters': tool.get('parameters', {'type': 'object', 'properties': {}})
                }
            })
    
    return enabled


# ========== 聊天会话 API ==========

@chat_bp.route('/api/chat-session', methods=['POST', 'DELETE'])
def chat_session_api():
    """聊天会话管理API"""
    user_id = get_current_user_id()
    if request.method == 'POST':
        session_id = str(uuid.uuid4())[:8]
        SessionService.save_chat_session(session_id, {'messages': [], 'created_at': datetime.now().isoformat()}, user_id=user_id)
        return jsonify({'session_id': session_id})
    else:
        session_id = request.json.get('session_id')
        if session_id:
            SessionService.clear_chat_session(session_id)
        return jsonify({'success': True})


@chat_bp.route('/api/chat-session/<session_id>', methods=['GET'])
def get_chat_session(session_id):
    """获取聊天会话历史"""
    session_data = SessionService.load_chat_session(session_id)
    return jsonify(session_data)


# ========== 聊天 API ==========

@chat_bp.route('/api/analyze', methods=['POST'])
def analyze():
    """分析API - 处理豆包视觉模型请求"""
    start_time = time.time()
    user_id = get_current_user_id()
    
    data = request.json
    prompt = data.get('prompt', '')
    image_data = data.get('image')
    model = data.get('model', 'doubao-1-5-vision-pro-32k-250115')
    stream = data.get('stream', True)
    reasoning_effort = data.get('reasoning_effort', 'medium')
    
    if not prompt and not image_data:
        return jsonify({'error': '请输入消息或上传图片'}), 400
    
    config = ConfigService.load_config(user_id=user_id)
    api_url = config.get('api_url', 'https://ark.cn-beijing.volces.com/api/v3/chat/completions')
    api_key = config.get('api_key', '')
    
    if not api_key:
        return jsonify({'error': '请先配置豆包 API Key'}), 400
    
    # 构建消息
    if image_data:
        user_content = []
        if prompt:
            user_content.append({'type': 'text', 'text': prompt})
        user_content.append({
            'type': 'image_url',
            'image_url': {'url': image_data}
        })
        messages = [{'role': 'user', 'content': user_content}]
    else:
        messages = [{'role': 'user', 'content': prompt}]
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    payload = {
        'model': model,
        'messages': messages,
        'stream': stream
    }
    
    # Seed 1.8 模型支持 reasoning_effort 参数
    if 'seed-1-8' in model:
        payload['reasoning_effort'] = reasoning_effort
    
    if stream:
        def generate():
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=180, stream=True)
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                yield f"data: {json.dumps({'done': True})}\n\n"
                                break
                            try:
                                chunk = json.loads(data_str)
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    content = delta.get('content', '')
                                    if content:
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                                    
                                    # 检查是否结束
                                    if chunk['choices'][0].get('finish_reason'):
                                        usage = chunk.get('usage', {})
                                        yield f"data: {json.dumps({'done': True, 'usage': usage})}\n\n"
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    else:
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=180)
            result = response.json()
            
            if 'error' in result:
                return jsonify({'error': result['error'].get('message', '请求失败')}), 500
            
            if 'choices' in result:
                content = result['choices'][0]['message'].get('content', '')
                return jsonify({
                    'content': content,
                    'usage': result.get('usage', {}),
                    'time': round(time.time() - start_time, 2)
                })
            
            return jsonify({'error': '未获取到响应'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500


@chat_bp.route('/api/chat', methods=['POST'])
def chat():
    """聊天API - 支持Function Calling和MCP工具"""
    start_time = time.time()
    user_id = get_current_user_id()
    
    data = request.json
    prompt = data.get('prompt', '')
    image_data = data.get('image')
    model = data.get('model', 'gpt-5-chat-latest')
    session_id = data.get('session_id')
    stream = data.get('stream', True)
    use_tools = data.get('use_tools', True)
    
    print(f"[Chat] user_id={user_id}, model={model}, prompt={prompt[:50] if prompt else 'None'}")
    
    if not prompt and not image_data:
        return jsonify({'error': '请输入消息'}), 400
    
    config = ConfigService.load_config(user_id=user_id)
    is_deepseek = 'deepseek' in model.lower()
    
    if is_deepseek:
        api_url = 'https://api.deepseek.com/chat/completions'
        api_key = config.get('deepseek_api_key', '')
        print(f"[Chat] DeepSeek API Key: {'已配置' if api_key else '未配置'}")
        if not api_key:
            return jsonify({'error': '请先配置 DeepSeek API Key'}), 400
        if model == 'deepseek-v3.2':
            model = 'deepseek-chat'
    else:
        api_url = config.get('gpt_api_url', 'https://api.gpt.ge/v1/chat/completions')
        api_key = config.get('gpt_api_key', '')
        print(f"[Chat] GPT API URL: {api_url}")
        print(f"[Chat] GPT API Key: {'已配置' if api_key else '未配置'}")
        if not api_key:
            return jsonify({'error': '请先配置 GPT API Key'}), 400
    
    # 构建消息列表
    messages = []
    if session_id:
        session_data = SessionService.load_session(session_id)
        history = session_data.get('messages', [])[-20:]
        messages.extend(history)
    
    # 构建当前用户消息
    if image_data:
        user_content = []
        if prompt:
            user_content.append({'type': 'text', 'text': prompt})
        user_content.append({
            'type': 'image_url',
            'image_url': {'url': image_data}
        })
        messages.append({'role': 'user', 'content': user_content})
    else:
        messages.append({'role': 'user', 'content': prompt})
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    if not is_deepseek:
        headers['x-foo'] = 'true'
    
    tools = get_enabled_tools() if use_tools else []
    
    def call_api_with_tools(msgs, is_stream=False):
        payload = {
            'model': model,
            'messages': msgs,
            'stream': is_stream
        }
        if tools:
            payload['tools'] = tools
            payload['tool_choice'] = 'auto'
        return requests.post(api_url, json=payload, headers=headers, timeout=180, stream=is_stream)
    
    if stream:
        def generate():
            full_response = ''
            try:
                response = call_api_with_tools(messages, is_stream=False)
                result = response.json()
                
                if 'error' in result:
                    yield f"data: {json.dumps({'error': result['error'].get('message', '请求失败')})}\n\n"
                    return
                
                if 'choices' not in result or len(result['choices']) == 0:
                    yield f"data: {json.dumps({'error': '未获取到响应'})}\n\n"
                    return
                
                message = result['choices'][0]['message']
                content = message.get('content', '')
                
                if content:
                    full_response = content
                    for char in content:
                        yield f"data: {json.dumps({'content': char})}\n\n"
                
                yield f"data: {json.dumps({'done': True, 'usage': result.get('usage', {})})}\n\n"
                
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    else:
        try:
            response = call_api_with_tools(messages, is_stream=False)
            result = response.json()
            
            if 'error' in result:
                return jsonify({'error': result['error'].get('message', '请求失败')}), 500
            
            if 'choices' in result:
                content = result['choices'][0]['message'].get('content', '')
                return jsonify({
                    'content': content,
                    'usage': result.get('usage', {}),
                    'time': round(time.time() - start_time, 2)
                })
            
            return jsonify({'error': '未获取到响应'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500


# ========== MCP 服务器管理 API ==========

@chat_bp.route('/api/mcp-servers', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mcp_servers_api():
    """MCP服务器管理API"""
    if request.method == 'GET':
        config = load_mcp_servers()
        servers = config.get('mcpServers', {})
        result = {}
        for name, server_config in servers.items():
            result[name] = {
                **server_config,
                'running': name in _mcp_server_processes
            }
        return jsonify({'mcpServers': result})
    
    elif request.method == 'POST':
        data = request.json
        server_name = data.get('name')
        server_config = data.get('config', {})
        
        config = load_mcp_servers()
        config['mcpServers'][server_name] = server_config
        save_mcp_servers(config)
        
        return jsonify({'success': True})
    
    elif request.method == 'PUT':
        data = request.json
        server_name = data.get('name')
        action = data.get('action')
        
        if action == 'start':
            config = load_mcp_servers()
            server_config = config.get('mcpServers', {}).get(server_name)
            if server_config:
                return jsonify({'success': True, 'message': '服务器启动中'})
            return jsonify({'error': '服务器配置不存在'}), 404
        
        elif action == 'stop':
            if server_name in _mcp_server_processes:
                del _mcp_server_processes[server_name]
            return jsonify({'success': True})
        
        return jsonify({'error': '未知操作'}), 400
    
    else:  # DELETE
        data = request.json
        server_name = data.get('name')
        
        config = load_mcp_servers()
        if server_name in config.get('mcpServers', {}):
            del config['mcpServers'][server_name]
            save_mcp_servers(config)
            
            if server_name in _mcp_server_processes:
                del _mcp_server_processes[server_name]
            
            return jsonify({'success': True})
        
        return jsonify({'error': '服务器不存在'}), 404


# ========== MCP 工具管理 API ==========

@chat_bp.route('/api/mcp-tools', methods=['GET', 'POST', 'PUT', 'DELETE'])
def mcp_tools_api():
    """MCP工具管理API"""
    if request.method == 'GET':
        tools = load_mcp_tools()
        return jsonify(tools)
    
    elif request.method == 'POST':
        data = request.json
        tools = load_mcp_tools()
        tool_id = f"custom_{uuid.uuid4().hex[:8]}"
        tools[tool_id] = {
            'name': tool_id,
            'display_name': data.get('display_name', '自定义工具'),
            'description': data.get('description', ''),
            'enabled': True,
            'builtin': False,
            'api_url': data.get('api_url', ''),
            'method': data.get('method', 'GET'),
            'headers': data.get('headers', {}),
            'parameters': data.get('parameters', {'type': 'object', 'properties': {}})
        }
        save_mcp_tools(tools)
        return jsonify({'success': True, 'tool_id': tool_id})
    
    elif request.method == 'PUT':
        data = request.json
        tool_id = data.get('tool_id')
        tools = load_mcp_tools()
        if tool_id in tools:
            if 'enabled' in data:
                tools[tool_id]['enabled'] = data['enabled']
            if 'display_name' in data:
                tools[tool_id]['display_name'] = data['display_name']
            if 'description' in data:
                tools[tool_id]['description'] = data['description']
            if 'api_url' in data:
                tools[tool_id]['api_url'] = data['api_url']
            save_mcp_tools(tools)
            return jsonify({'success': True})
        return jsonify({'error': '工具不存在'}), 404
    
    else:  # DELETE
        data = request.json
        tool_id = data.get('tool_id')
        tools = load_mcp_tools()
        if tool_id in tools and not tools[tool_id].get('builtin'):
            del tools[tool_id]
            save_mcp_tools(tools)
            return jsonify({'success': True})
        return jsonify({'error': '无法删除内置工具'}), 400


@chat_bp.route('/api/debug/tools', methods=['GET'])
def debug_tools():
    """调试：查看所有已启用的工具"""
    return jsonify({
        'enabled_tools': get_enabled_tools(),
        'mcp_servers': {
            name: {
                'running': True,
                'tools': info.get('tools', [])
            }
            for name, info in _mcp_server_processes.items()
        }
    })


# ========== 第一性原理分析 API ==========

# 第一性原理分析系统提示词
FIRST_PRINCIPLES_SYSTEM_PROMPT = """# 能力与角色

你是一位顶级的思考者，你的思维模型融合了物理学家（如理查德·费曼）的严谨、顶尖工程师（如埃隆·马斯克）的务实和哲学家（如亚里士多德）的深刻。你的核心能力是运用「第一性原理」来分析和解决任何问题。你不依赖类比、传统或经验，而是致力于将任何复杂问题拆解至最基本、最不容置疑的组成部分（物理定律、人性本质、数学公理等），然后从这些基石出发，重新构建解决方案。

# 洞察与背景

在充满不确定性和复杂性的世界里，大多数人和组织习惯于类比思维，即复制他人的做法或在现有基础上进行微小改良。这种思维方式难以带来颠覆性创新或找到问题的根本解。我们的目标是打破常规，通过回归事物最本质的原理，共同探索出一条独特的、根本性的创新路径。你的提问和分析过程，本身就是帮助用户深度思考的价值所在。

# 陈述任务

你的任务是一个动态的、苏格拉底式的对话流程，具体如下：

1. **接收初始问题**：用户会提出一个【问题或需求】。

2. **启动提问循环**：你的任务不是立即给出答案。相反，你将启动「第一性原理」分析流程，通过一系列深刻的反问，来挑战用户陈述中的每一个假设、每一个术语和每一个既定目标。

3. **多轮反问**：你可能会反问多次。每一轮提问都旨在剥离一层表象，直击更深层次的本质。你的问题可能包括但不限于：
   - "我们真正想要达成的最终目标是什么？这个目标是否可以被进一步分解？"
   - "我们认为『必须』要做某件事，这个『必须』是基于一个不可动摇的物理定律，还是仅仅是一个行业惯例或过去的假设？"
   - "描述一下这个问题的基本组成部分有哪些？哪些是事实，哪些是我们的推断？"
   - "如果我们从零开始，没有任何历史包袱和现有资源的限制，我们会怎么来做来解决这个问题？"

4. **判断与确认**：当你判断对话已经将问题分解到最基本的、不容置疑的"事实"或"公理"层面时，你需要向用户进行确认。例如："似乎已经触及了问题的核心：[概括总结出的核心原理]。基于这些基本原理，您希望我为您构建最终的结论或解决方案了吗？"

5. **输出最终结论**：在用户确认后，基于共同确认的第一性原理，系统地、逻辑清晰地构建并输出一个创新的、根本性的最终结论或解决方案。

# 个性

在整个对话过程中，你的个性应该是：
- **冷静的探究者**：语气始终保持客观、中立、不带偏见
- **深刻的怀疑论者**：对所有未经检验的假设都保持健康的怀疑
- **谦逊的引导者**：你的提问不是为了炫耀知识，而是为了引导用户进行更深层次的思考
- **极度好奇**：展现出对问题本质的强烈、纯粹的好奇心

# 实验与探索

在输出【最终结论】时，你必须进行以下探索，以确保结论的严谨性和可追溯性：

**展示推理路径**：你不能只给出答案。你需要清晰地展示你的推理路径。首先以列表形式列出我们共同确认的【第一性原理清单】（即我们分解出的核心事实与公理），然后展示你是如何一步步从这些原理推导出你的最终结论的。这种透明的推理过程至关重要。

# 输出格式要求

为了便于阅读和交互，请使用以下模块化格式输出：

## 当进行提问时，使用：

【当前阶段】探索层级 X（X为1-5的数字，表示分析深度）

【分析要点】
- 对用户回答的关键洞察
- 发现的隐含假设或值得深挖的点

【问题组】
1. 问题1（关于目标/动机）
2. 问题2（关于假设/约束）
3. 问题3（关于本质/原理）
（每轮必须提出2-4个相关联的问题，从不同角度探索）

【思考提示】简短的思考方向提示，帮助用户更好地回答上述问题

## 当给出最终结论时，使用：

【分析完成】

【第一性原理清单】
1. 原理1
2. 原理2
3. ...

【推理路径】
步骤1 → 步骤2 → 步骤3 → 结论

【最终方案】
具体的解决方案内容

【创新点】
- 创新点1
- 创新点2

# 重要规则

- 每轮必须提出2-4个问题，绝对不能只问1个问题
- 问题要具体、可回答，避免过于抽象
- 问题之间要有逻辑关联，形成追问链条
- 保持对话推进感，不要原地打转
- 通过3-5轮对话逐步深入到问题本质"""


@chat_bp.route('/api/first-principles', methods=['POST'])
def first_principles_analysis():
    """第一性原理分析API - 使用DeepSeek V3.2模型"""
    user_id = get_current_user_id()
    
    data = request.json
    prompt = data.get('prompt', '')
    history = data.get('history', [])
    stream = data.get('stream', True)
    
    if not prompt:
        return jsonify({'error': '请输入问题或需求'}), 400
    
    config = ConfigService.load_config(user_id=user_id)
    api_key = config.get('deepseek_api_key', '')
    
    if not api_key:
        return jsonify({'error': '请先配置 DeepSeek API Key'}), 400
    
    api_url = 'https://api.deepseek.com/chat/completions'
    
    # 构建消息列表 - deepseek-reasoner不支持system角色
    messages = []
    
    # 添加历史对话
    for i, msg in enumerate(history):
        messages.append({
            'role': msg.get('role', 'user'),
            'content': msg.get('content', '')
        })
    
    # 只有第一轮（无历史）时合并提示词
    if len(history) == 0:
        combined_prompt = f"""请按照以下角色和规则来回答：

{FIRST_PRINCIPLES_SYSTEM_PROMPT}

---

用户问题：{prompt}"""
        messages.append({'role': 'user', 'content': combined_prompt})
    else:
        messages.append({'role': 'user', 'content': prompt})
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Bearer {api_key}'
    }
    
    # deepseek-reasoner不支持temperature参数
    payload = {
        'model': 'deepseek-reasoner',
        'messages': messages,
        'stream': stream,
        'max_tokens': 8192
    }
    
    # 保存请求内容用于调试（不包含API key）
    request_debug = {
        'model': payload['model'],
        'messages': payload['messages'],
        'stream': payload['stream'],
        'max_tokens': payload['max_tokens']
    }
    
    if stream:
        def generate():
            # 先发送请求内容用于调试
            yield f"data: {json.dumps({'request_debug': request_debug})}\n\n"
            
            try:
                response = requests.post(api_url, json=payload, headers=headers, timeout=300, stream=True)
                
                reasoning_started = False
                
                for line in response.iter_lines():
                    if line:
                        line_str = line.decode('utf-8')
                        # 调试：打印原始响应
                        print(f"[FP Debug] Raw line: {line_str[:200]}")
                        
                        if line_str.startswith('data: '):
                            data_str = line_str[6:]
                            if data_str == '[DONE]':
                                yield f"data: [DONE]\n\n"
                                break
                            try:
                                chunk = json.loads(data_str)
                                # 调试：打印解析后的chunk
                                print(f"[FP Debug] Chunk keys: {chunk.keys() if isinstance(chunk, dict) else 'not dict'}")
                                
                                if 'choices' in chunk and len(chunk['choices']) > 0:
                                    delta = chunk['choices'][0].get('delta', {})
                                    # 调试：打印delta内容
                                    print(f"[FP Debug] Delta: {delta}")
                                    
                                    # 处理推理内容 (reasoning_content)
                                    reasoning_content = delta.get('reasoning_content', '')
                                    if reasoning_content:
                                        if not reasoning_started:
                                            reasoning_started = True
                                            yield f"data: {json.dumps({'reasoning_start': True})}\n\n"
                                        yield f"data: {json.dumps({'reasoning': reasoning_content})}\n\n"
                                    
                                    # 处理正常内容
                                    content = delta.get('content', '')
                                    if content:
                                        if reasoning_started:
                                            reasoning_started = False
                                            yield f"data: {json.dumps({'reasoning_end': True})}\n\n"
                                        yield f"data: {json.dumps({'content': content})}\n\n"
                                    
                                    # 检查是否结束
                                    if chunk['choices'][0].get('finish_reason'):
                                        if reasoning_started:
                                            yield f"data: {json.dumps({'reasoning_end': True})}\n\n"
                                        usage = chunk.get('usage', {})
                                        yield f"data: {json.dumps({'done': True, 'usage': usage})}\n\n"
                            except json.JSONDecodeError:
                                pass
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"
        
        return Response(generate(), mimetype='text/event-stream')
    else:
        try:
            response = requests.post(api_url, json=payload, headers=headers, timeout=180)
            result = response.json()
            
            if 'error' in result:
                return jsonify({'error': result['error'].get('message', '请求失败')}), 500
            
            if 'choices' in result:
                content = result['choices'][0]['message'].get('content', '')
                return jsonify({
                    'content': content,
                    'usage': result.get('usage', {})
                })
            
            return jsonify({'error': '未获取到响应'}), 500
        except Exception as e:
            return jsonify({'error': str(e)}), 500
