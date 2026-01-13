"""
会话服务模块
提供会话管理功能，支持普通会话和聊天会话
支持文件存储和数据库存储两种模式
"""
import os
import json
from datetime import datetime

# 是否使用数据库存储
USE_DB_STORAGE = os.environ.get('USE_DB_STORAGE', 'true').lower() == 'true'


class SessionService:
    """会话服务类"""
    
    SESSIONS_DIR = 'sessions'
    CHAT_SESSIONS_DIR = 'chat_sessions'
    
    @staticmethod
    def _ensure_dir(directory):
        """确保目录存在"""
        if not os.path.exists(directory):
            os.makedirs(directory)
    
    # ========== 普通会话管理 ==========
    
    @staticmethod
    def get_session_file(session_id):
        """获取会话文件路径"""
        SessionService._ensure_dir(SessionService.SESSIONS_DIR)
        return os.path.join(SessionService.SESSIONS_DIR, f'{session_id}.json')
    
    @staticmethod
    def load_session(session_id):
        """加载会话历史"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            row = AppDatabaseService.get_chat_session(session_id)
            if row:
                messages = row['messages']
                if isinstance(messages, str):
                    messages = json.loads(messages)
                return {
                    'messages': messages or [],
                    'title': row['title'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
                }
            return {'messages': [], 'created_at': datetime.now().isoformat()}
        
        session_file = SessionService.get_session_file(session_id)
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'messages': [], 'created_at': datetime.now().isoformat()}
    
    @staticmethod
    def save_session(session_id, session_data, user_id=None):
        """保存会话历史"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            if user_id:
                AppDatabaseService.save_chat_session_with_user(
                    session_id,
                    user_id,
                    session_type='session',
                    title=session_data.get('title', '新对话'),
                    messages=session_data.get('messages', [])
                )
            else:
                AppDatabaseService.save_chat_session(
                    session_id,
                    session_type='session',
                    title=session_data.get('title', '新对话'),
                    messages=session_data.get('messages', [])
                )
            return
        
        session_file = SessionService.get_session_file(session_id)
        session_data['updated_at'] = datetime.now().isoformat()
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def clear_session(session_id):
        """清除会话历史"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            AppDatabaseService.delete_chat_session(session_id)
            return
        
        session_file = SessionService.get_session_file(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
    
    @staticmethod
    def get_all_sessions(user_id=None):
        """获取所有会话列表"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            if user_id:
                rows = AppDatabaseService.get_chat_sessions_by_user(user_id, 'session')
            else:
                rows = AppDatabaseService.get_chat_sessions('session')
            return [{
                'id': row['session_id'],
                'title': row['title'],
                'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
            } for row in rows]
        
        sessions = []
        SessionService._ensure_dir(SessionService.SESSIONS_DIR)
        
        for filename in os.listdir(SessionService.SESSIONS_DIR):
            if filename.endswith('.json'):
                session_id = filename[:-5]
                try:
                    with open(os.path.join(SessionService.SESSIONS_DIR, filename), 'r', encoding='utf-8') as f:
                        data = json.load(f)
                        sessions.append({
                            'id': session_id,
                            'title': data.get('title', '新对话'),
                            'created_at': data.get('created_at', ''),
                            'updated_at': data.get('updated_at', data.get('created_at', ''))
                        })
                except:
                    pass
        
        sessions.sort(key=lambda x: x.get('updated_at', ''), reverse=True)
        return sessions
    
    @staticmethod
    def rename_session(session_id, new_title):
        """重命名会话"""
        session_data = SessionService.load_session(session_id)
        session_data['title'] = new_title
        SessionService.save_session(session_id, session_data)
    
    # ========== 聊天会话管理 ==========
    
    @staticmethod
    def get_chat_session_file(session_id):
        """获取聊天会话文件路径"""
        SessionService._ensure_dir(SessionService.CHAT_SESSIONS_DIR)
        return os.path.join(SessionService.CHAT_SESSIONS_DIR, f'{session_id}.json')
    
    @staticmethod
    def load_chat_session(session_id):
        """加载聊天会话"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            row = AppDatabaseService.get_chat_session(session_id)
            if row:
                messages = row['messages']
                if isinstance(messages, str):
                    messages = json.loads(messages)
                return {
                    'messages': messages or [],
                    'title': row['title'],
                    'created_at': row['created_at'].isoformat() if row['created_at'] else '',
                    'updated_at': row['updated_at'].isoformat() if row['updated_at'] else ''
                }
            return {'messages': [], 'created_at': datetime.now().isoformat()}
        
        session_file = SessionService.get_chat_session_file(session_id)
        if os.path.exists(session_file):
            with open(session_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'messages': [], 'created_at': datetime.now().isoformat()}
    
    @staticmethod
    def save_chat_session(session_id, session_data, user_id=None):
        """保存聊天会话"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            if user_id:
                AppDatabaseService.save_chat_session_with_user(
                    session_id,
                    user_id,
                    session_type='chat',
                    title=session_data.get('title', '新对话'),
                    messages=session_data.get('messages', [])
                )
            else:
                AppDatabaseService.save_chat_session(
                    session_id,
                    session_type='chat',
                    title=session_data.get('title', '新对话'),
                    messages=session_data.get('messages', [])
                )
            return
        
        session_file = SessionService.get_chat_session_file(session_id)
        session_data['updated_at'] = datetime.now().isoformat()
        with open(session_file, 'w', encoding='utf-8') as f:
            json.dump(session_data, f, ensure_ascii=False, indent=2)
    
    @staticmethod
    def clear_chat_session(session_id):
        """清除聊天会话"""
        if USE_DB_STORAGE:
            from .database_service import AppDatabaseService
            AppDatabaseService.delete_chat_session(session_id)
            return
        
        session_file = SessionService.get_chat_session_file(session_id)
        if os.path.exists(session_file):
            os.remove(session_file)
