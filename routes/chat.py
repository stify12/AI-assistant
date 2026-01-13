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
