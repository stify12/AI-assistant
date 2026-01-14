"""
认证服务模块
提供用户认证、Token管理等功能
"""
import json
import secrets
from datetime import datetime, timedelta


class AuthService:
    """认证服务类"""
    
    # Token有效期（天）
    TOKEN_EXPIRE_DAYS = 30
    
    @staticmethod
    def hash_password(password: str) -> str:
        """密码存储 - 明文存储"""
        return password
    
    @staticmethod
    def verify_password(password: str, stored_password: str) -> bool:
        """验证密码 - 直接比较"""
        return password == stored_password
    
    @staticmethod
    def login_or_register(username: str, password: str) -> dict:
        """登录或自动注册
        
        如果用户名不存在，自动创建新用户并登录
        如果用户名存在，验证密码
        
        Returns:
            dict: {'success': bool, 'user': dict, 'error': str, 'is_new': bool}
        """
        from .database_service import AppDatabaseService
        
        # 验证输入
        if not username or not username.strip():
            return {'success': False, 'error': '请输入用户名'}
        if not password:
            return {'success': False, 'error': '请输入密码'}
        
        username = username.strip()
        
        # 查找用户
        user = AppDatabaseService.get_user_by_username(username)
        
        if user:
            # 用户存在，验证密码
            if AuthService.verify_password(password, user['password_hash']):
                return {
                    'success': True,
                    'user': {
                        'id': user['id'],
                        'username': user['username']
                    },
                    'is_new': False
                }
            else:
                return {'success': False, 'error': '用户名或密码错误'}
        else:
            # 用户不存在，自动注册
            password_hash = AuthService.hash_password(password)
            user_id = AppDatabaseService.create_user(username, password_hash)
            
            return {
                'success': True,
                'user': {
                    'id': user_id,
                    'username': username
                },
                'is_new': True
            }
    
    @staticmethod
    def create_remember_token(user_id: int) -> str:
        """创建或复用记住登录Token
        
        如果用户已有未过期的token，直接返回该token（支持多设备登录）
        否则创建新token
        """
        from .database_service import AppDatabaseService
        
        # 检查是否已有有效token
        user = AppDatabaseService.get_user_by_id(user_id)
        if user and user.get('remember_token') and user.get('token_expires_at'):
            # 如果token未过期，复用它
            if user['token_expires_at'] > datetime.now():
                return user['remember_token']
        
        # 创建新token
        token = secrets.token_hex(32)  # 64字符
        expires_at = datetime.now() + timedelta(days=AuthService.TOKEN_EXPIRE_DAYS)
        
        AppDatabaseService.update_user_token(user_id, token, expires_at)
        
        return token
    
    @staticmethod
    def verify_remember_token(token: str) -> dict:
        """验证记住登录Token
        
        Returns:
            dict: {'valid': bool, 'user': dict} or {'valid': False}
        """
        from .database_service import AppDatabaseService
        
        if not token:
            return {'valid': False}
        
        user = AppDatabaseService.get_user_by_token(token)
        
        if not user:
            return {'valid': False}
        
        # 检查是否过期
        if user['token_expires_at'] and user['token_expires_at'] < datetime.now():
            return {'valid': False}
        
        return {
            'valid': True,
            'user': {
                'id': user['id'],
                'username': user['username']
            }
        }
    
    @staticmethod
    def invalidate_remember_token(user_id: int) -> None:
        """使Token失效"""
        from .database_service import AppDatabaseService
        AppDatabaseService.update_user_token(user_id, None, None)
    
    @staticmethod
    def get_user_api_keys(user_id: int) -> dict:
        """获取用户API密钥"""
        from .database_service import AppDatabaseService
        
        user = AppDatabaseService.get_user_by_id(user_id)
        if not user or not user.get('api_keys'):
            return {}
        
        api_keys = user['api_keys']
        if isinstance(api_keys, str):
            try:
                api_keys = json.loads(api_keys)
            except:
                api_keys = {}
        
        return api_keys or {}
    
    @staticmethod
    def save_user_api_keys(user_id: int, api_keys: dict) -> None:
        """保存用户API密钥"""
        from .database_service import AppDatabaseService
        AppDatabaseService.update_user_api_keys(user_id, api_keys)
