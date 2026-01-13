"""
认证路由模块
提供用户登录、登出、状态检查等API
"""
from functools import wraps
from flask import Blueprint, request, jsonify, session, make_response

from services.auth_service import AuthService

auth_bp = Blueprint('auth', __name__)


def login_required(f):
    """需要登录的路由装饰器"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not session.get('logged_in'):
            return jsonify({'error': '请先登录'}), 401
        return f(*args, **kwargs)
    return decorated_function


def get_current_user():
    """获取当前登录用户"""
    if session.get('logged_in'):
        return {
            'id': session.get('user_id'),
            'username': session.get('username')
        }
    return None


def get_current_user_id():
    """获取当前登录用户ID"""
    return session.get('user_id')


@auth_bp.route('/api/auth/login', methods=['POST'])
def login():
    """登录/自动注册"""
    data = request.json or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')
    remember = data.get('remember', False)
    
    result = AuthService.login_or_register(username, password)
    
    if result['success']:
        user = result['user']
        # 设置session
        session['logged_in'] = True
        session['user_id'] = user['id']
        session['username'] = user['username']
        session.permanent = True
        
        response_data = {
            'success': True,
            'user': user,
            'is_new': result.get('is_new', False)
        }
        
        response = make_response(jsonify(response_data))
        
        # 如果选择记住登录，创建持久化Token
        if remember:
            token = AuthService.create_remember_token(user['id'])
            response.set_cookie(
                'remember_token',
                token,
                max_age=30*24*60*60,  # 30天
                httponly=True,
                samesite='Lax'
            )
        
        return response
    else:
        return jsonify({'success': False, 'error': result['error']}), 401


@auth_bp.route('/api/auth/logout', methods=['POST'])
def logout():
    """登出"""
    user_id = session.get('user_id')
    
    # 使Token失效
    if user_id:
        AuthService.invalidate_remember_token(user_id)
    
    # 清除session
    session.clear()
    
    response = make_response(jsonify({'success': True}))
    # 清除cookie
    response.delete_cookie('remember_token')
    
    return response


@auth_bp.route('/api/auth/status', methods=['GET'])
def status():
    """获取登录状态"""
    # 先检查session
    if session.get('logged_in'):
        return jsonify({
            'logged_in': True,
            'user': {
                'id': session.get('user_id'),
                'username': session.get('username')
            }
        })
    
    # 检查记住登录Token
    token = request.cookies.get('remember_token')
    if token:
        result = AuthService.verify_remember_token(token)
        if result['valid']:
            user = result['user']
            # 恢复session
            session['logged_in'] = True
            session['user_id'] = user['id']
            session['username'] = user['username']
            session.permanent = True
            
            return jsonify({
                'logged_in': True,
                'user': user
            })
    
    return jsonify({'logged_in': False})


@auth_bp.route('/api/auth/api-keys', methods=['GET', 'POST'])
@login_required
def api_keys():
    """API密钥管理"""
    user_id = session.get('user_id')
    
    if request.method == 'GET':
        keys = AuthService.get_user_api_keys(user_id)
        return jsonify(keys)
    else:
        data = request.json or {}
        AuthService.save_user_api_keys(user_id, data)
        return jsonify({'success': True})

