"""
通用路由模块
包含首页、配置、会话管理等通用路由
"""
import uuid
import io
from datetime import datetime
from flask import Blueprint, render_template, request, jsonify, send_file
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side

from services.config_service import ConfigService
from services.session_service import SessionService
from routes.auth import get_current_user_id

common_bp = Blueprint('common', __name__)


# ========== 页面路由 ==========

@common_bp.route('/')
def index():
    return render_template('index.html')


@common_bp.route('/index-new')
def index_new():
    """优化版首页（模块化架构）"""
    return render_template('index-new.html')


@common_bp.route('/chat')
def chat():
    """AI 对话页面 (原首页功能迁移)"""
    return render_template('chat.html')


@common_bp.route('/subject-grading')
def subject_grading():
    return render_template('subject-grading.html')


@common_bp.route('/batch-evaluation')
def batch_evaluation():
    return render_template('batch-evaluation.html')


# ========== 配置 API ==========

@common_bp.route('/api/config', methods=['GET', 'POST'])
def config():
    user_id = get_current_user_id()
    
    if request.method == 'GET':
        # 获取配置时从数据库加载用户配置
        config_data = ConfigService.load_config(apply_headers=False, user_id=user_id)
        # 移除敏感信息（不返回完整密钥，只返回是否已配置）
        safe_config = {
            'api_url': config_data.get('api_url', ''),
            'gpt_api_url': config_data.get('gpt_api_url', 'https://api.gpt.ge/v1/chat/completions'),
            'mysql': config_data.get('mysql', {}),
            'app_mysql': config_data.get('app_mysql', {}),
            'prompts': config_data.get('prompts', {}),
            'use_ai_compare': config_data.get('use_ai_compare', False),
            # 返回API密钥配置状态（是否已配置）
            'has_api_key': bool(config_data.get('api_key')),
            'has_gpt_api_key': bool(config_data.get('gpt_api_key')),
            'has_deepseek_api_key': bool(config_data.get('deepseek_api_key')),
            'has_qwen_api_key': bool(config_data.get('qwen_api_key'))
        }
        return jsonify(safe_config)
    else:
        # 保存配置
        data = request.json
        
        # 如果已登录，保存API密钥到数据库（用户级别）
        if user_id:
            from services.database_service import AppDatabaseService
            api_keys = {}
            if 'api_key' in data:
                api_keys['api_key'] = data['api_key']
                api_keys['doubao_key'] = data['api_key']  # 兼容旧字段名
            if 'gpt_api_key' in data:
                api_keys['gpt_api_key'] = data['gpt_api_key']
                api_keys['gpt_key'] = data['gpt_api_key']  # 兼容旧字段名
            if 'deepseek_api_key' in data:
                api_keys['deepseek_api_key'] = data['deepseek_api_key']
                api_keys['deepseek_key'] = data['deepseek_api_key']  # 兼容旧字段名
            if 'qwen_api_key' in data:
                api_keys['qwen_api_key'] = data['qwen_api_key']
                api_keys['qwen_key'] = data['qwen_api_key']  # 兼容旧字段名
            if 'api_url' in data:
                api_keys['api_url'] = data['api_url']
            if 'gpt_api_url' in data:
                api_keys['gpt_api_url'] = data['gpt_api_url']
            
            if api_keys:
                AppDatabaseService().update_user_api_keys(user_id, api_keys)
        
        # 保存非敏感配置到服务器文件
        config_data = ConfigService.load_config(apply_headers=False)
        if 'mysql' in data:
            config_data['mysql'] = data['mysql']
        if 'app_mysql' in data:
            config_data['app_mysql'] = data['app_mysql']
        if 'use_ai_compare' in data:
            config_data['use_ai_compare'] = data['use_ai_compare']
        
        ConfigService.save_config(config_data)
        return jsonify({'success': True})


@common_bp.route('/api/validate-api-key', methods=['POST'])
def validate_api_key():
    """验证API密钥是否有效"""
    import requests as http_requests
    
    data = request.json
    key_type = data.get('type')  # doubao, deepseek, qwen
    api_key = data.get('api_key')
    
    if not key_type or not api_key:
        return jsonify({'valid': False, 'error': '缺少参数'})
    
    try:
        if key_type == 'doubao':
            # 验证豆包API
            url = 'https://ark.cn-beijing.volces.com/api/v3/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            payload = {
                'model': 'doubao-1-5-vision-pro-32k-250115',
                'messages': [{'role': 'user', 'content': 'hi'}],
                'max_tokens': 1
            }
            res = http_requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200 or 'choices' in res.json():
                return jsonify({'valid': True})
            else:
                error = res.json().get('error', {}).get('message', '验证失败')
                return jsonify({'valid': False, 'error': error})
                
        elif key_type == 'deepseek':
            # 验证DeepSeek API
            url = 'https://api.deepseek.com/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            payload = {
                'model': 'deepseek-chat',
                'messages': [{'role': 'user', 'content': 'hi'}],
                'max_tokens': 1
            }
            res = http_requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200 or 'choices' in res.json():
                return jsonify({'valid': True})
            else:
                error = res.json().get('error', {}).get('message', '验证失败')
                return jsonify({'valid': False, 'error': error})
                
        elif key_type == 'qwen':
            # 验证通义千问API
            url = 'https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions'
            headers = {
                'Content-Type': 'application/json',
                'Authorization': f'Bearer {api_key}'
            }
            payload = {
                'model': 'qwen-turbo',
                'messages': [{'role': 'user', 'content': 'hi'}],
                'max_tokens': 1
            }
            res = http_requests.post(url, json=payload, headers=headers, timeout=10)
            if res.status_code == 200 or 'choices' in res.json():
                return jsonify({'valid': True})
            else:
                error = res.json().get('error', {}).get('message', '验证失败')
                return jsonify({'valid': False, 'error': error})
        else:
            return jsonify({'valid': False, 'error': '未知的API类型'})
            
    except http_requests.Timeout:
        return jsonify({'valid': False, 'error': '请求超时'})
    except Exception as e:
        return jsonify({'valid': False, 'error': str(e)})


# ========== 会话管理 API ==========

@common_bp.route('/api/session', methods=['POST', 'DELETE'])
def session_api():
    """会话管理API"""
    user_id = get_current_user_id()
    if request.method == 'POST':
        # 创建新会话
        session_id = str(uuid.uuid4())[:8]
        SessionService.save_session(session_id, {'messages': [], 'created_at': datetime.now().isoformat()}, user_id=user_id)
        return jsonify({'session_id': session_id})
    else:
        # 清除会话
        session_id = request.json.get('session_id')
        if session_id:
            SessionService.clear_session(session_id)
        return jsonify({'success': True})


@common_bp.route('/api/session/<session_id>', methods=['GET'])
def get_session(session_id):
    """获取会话历史"""
    session_data = SessionService.load_session(session_id)
    return jsonify(session_data)


@common_bp.route('/api/all-sessions', methods=['GET'])
def get_all_sessions():
    """获取所有会话列表"""
    user_id = get_current_user_id()
    sessions = SessionService.get_all_sessions(user_id=user_id)
    return jsonify(sessions)


@common_bp.route('/api/session/<session_id>/rename', methods=['POST'])
def rename_session(session_id):
    """重命名会话"""
    data = request.json
    new_title = data.get('title', '新对话')
    SessionService.rename_session(session_id, new_title)
    return jsonify({'success': True})


@common_bp.route('/api/session/save-parallel', methods=['POST'])
def save_parallel_result():
    """保存并行处理结果到会话"""
    data = request.json
    session_id = data.get('session_id')
    user_message = data.get('user_message', '')
    has_image = data.get('has_image', False)
    assistant_message = data.get('assistant_message', '')
    model = data.get('model', '')
    
    if not session_id:
        return jsonify({'error': '缺少session_id'}), 400
    
    user_id = get_current_user_id()
    session_data = SessionService.load_session(session_id)
    
    # 添加用户消息
    user_msg = {'role': 'user', 'content': user_message}
    if has_image:
        user_msg['has_image'] = True
    session_data['messages'].append(user_msg)
    
    # 添加助手消息
    session_data['messages'].append({
        'role': 'assistant',
        'content': assistant_message,
        'model': model
    })
    
    SessionService.save_session(session_id, session_data, user_id=user_id)
    return jsonify({'success': True})



# ========== 学科配置 API ==========

@common_bp.route('/api/subjects', methods=['GET', 'POST', 'PUT'])
def subjects_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_subjects())
    elif request.method == 'POST':
        subjects = ConfigService.load_subjects()
        data = request.json
        subjects[data['id']] = data['config']
        ConfigService.save_subjects(subjects)
        return jsonify({'success': True})
    else:  # PUT
        ConfigService.save_subjects(request.json)
        return jsonify({'success': True})


# ========== 自定义模型配置 API ==========

@common_bp.route('/api/models', methods=['GET', 'POST', 'PUT', 'DELETE'])
def models_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_custom_models())
    elif request.method == 'POST':
        models = ConfigService.load_custom_models()
        data = request.json
        data['id'] = str(uuid.uuid4())[:8]
        models.append(data)
        ConfigService.save_custom_models(models)
        return jsonify({'success': True, 'id': data['id']})
    elif request.method == 'PUT':
        models = ConfigService.load_custom_models()
        data = request.json
        for i, m in enumerate(models):
            if m['id'] == data['id']:
                models[i] = data
                break
        ConfigService.save_custom_models(models)
        return jsonify({'success': True})
    else:  # DELETE
        models = ConfigService.load_custom_models()
        model_id = request.json.get('id')
        models = [m for m in models if m['id'] != model_id]
        ConfigService.save_custom_models(models)
        return jsonify({'success': True})


# ========== 评估配置 API ==========

@common_bp.route('/api/eval-config', methods=['GET', 'POST'])
def eval_config_api():
    if request.method == 'GET':
        return jsonify(ConfigService.load_eval_config())
    else:
        ConfigService.save_eval_config(request.json)
        return jsonify({'success': True})


# ========== 数据库连接测试 API ==========

# ========== 优化日志 API ==========

@common_bp.route('/api/optimization-logs', methods=['GET'])
def get_optimization_logs():
    """获取优化日志列表"""
    from services.database_service import AppDatabaseService
    try:
        logs = AppDatabaseService.execute_query(
            "SELECT id, log_date, content, category, created_at FROM optimization_logs ORDER BY log_date DESC, id DESC LIMIT 50"
        )
        return jsonify([{
            'id': log['id'],
            'log_date': log['log_date'].strftime('%m/%d %H:%M') if log['log_date'] else '',
            'content': log['content'],
            'category': log['category'],
            'created_at': log['created_at'].isoformat() if log['created_at'] else ''
        } for log in logs])
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/api/optimization-logs', methods=['POST'])
def add_optimization_log():
    """添加优化日志"""
    from services.database_service import AppDatabaseService
    data = request.json
    log_date = data.get('log_date')
    content = data.get('content', '').strip()
    category = data.get('category', 'general')
    
    if not content:
        return jsonify({'error': '内容不能为空'}), 400
    
    try:
        AppDatabaseService.execute_update(
            "INSERT INTO optimization_logs (log_date, content, category) VALUES (%s, %s, %s)",
            (log_date, content, category)
        )
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/api/optimization-logs/<int:log_id>', methods=['DELETE'])
def delete_optimization_log(log_id):
    """删除优化日志"""
    from services.database_service import AppDatabaseService
    try:
        AppDatabaseService.execute_update("DELETE FROM optimization_logs WHERE id = %s", (log_id,))
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@common_bp.route('/api/test-database', methods=['POST'])
def test_database_connection():
    """测试数据库连接"""
    data = request.json
    db_type = data.get('type', 'main')  # main 或 app
    
    try:
        import pymysql
        
        if db_type == 'main':
            host = data.get('host') or data.get('mysql', {}).get('host', '')
            port = int(data.get('port') or data.get('mysql', {}).get('port', 3306))
            user = data.get('user') or data.get('mysql', {}).get('user', '')
            password = data.get('password') or data.get('mysql', {}).get('password', '')
            database = data.get('database') or data.get('mysql', {}).get('database', '')
        else:
            host = data.get('host') or data.get('app_mysql', {}).get('host', '')
            port = int(data.get('port') or data.get('app_mysql', {}).get('port', 3306))
            user = data.get('user') or data.get('app_mysql', {}).get('user', '')
            password = data.get('password') or data.get('app_mysql', {}).get('password', '')
            database = data.get('database') or data.get('app_mysql', {}).get('database', '')
        
        if not host or not user or not database:
            return jsonify({'success': False, 'error': '请填写完整的数据库配置'})
        
        # 尝试连接
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            connect_timeout=5
        )
        conn.close()
        
        return jsonify({'success': True, 'message': '连接成功'})
    
    except pymysql.err.OperationalError as e:
        error_msg = str(e)
        if 'Access denied' in error_msg:
            return jsonify({'success': False, 'error': '用户名或密码错误'})
        elif 'Unknown database' in error_msg:
            return jsonify({'success': False, 'error': '数据库不存在'})
        elif 'connect' in error_msg.lower():
            return jsonify({'success': False, 'error': '无法连接到数据库服务器，请检查地址和端口'})
        else:
            return jsonify({'success': False, 'error': error_msg})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})
