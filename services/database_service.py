"""
数据库服务模块
提供 MySQL 数据库连接和查询功能
支持两个数据库：
- mysql: 原业务数据库(zpsmart)，用于获取作业数据
- app_mysql: 应用数据库(aiuser)，用于存储平台数据
"""
import json
from datetime import datetime
from .config_service import ConfigService


class DatabaseService:
    """数据库服务类 - 原业务数据库"""
    
    # 配置缓存
    _config_cache = None
    _config_cache_time = 0
    _CONFIG_CACHE_TTL = 60  # 配置缓存60秒
    
    @staticmethod
    def _get_cached_config():
        """获取缓存的数据库配置"""
        import time
        now = time.time()
        if DatabaseService._config_cache is None or (now - DatabaseService._config_cache_time) > DatabaseService._CONFIG_CACHE_TTL:
            config = ConfigService.load_config()
            DatabaseService._config_cache = config.get('mysql', {})
            DatabaseService._config_cache_time = now
        return DatabaseService._config_cache
    
    @staticmethod
    def get_connection(retries=3):
        """获取原业务数据库连接，带重试机制"""
        import pymysql
        import time
        
        mysql_config = DatabaseService._get_cached_config()
        
        last_error = None
        for attempt in range(retries):
            try:
                return pymysql.connect(
                    host=mysql_config.get('host', '47.113.230.78'),
                    port=mysql_config.get('port', 3306),
                    user=mysql_config.get('user', 'zpsmart'),
                    password=mysql_config.get('password', 'rootyouerkj!'),
                    database=mysql_config.get('database', 'zpsmart'),
                    charset='utf8mb4',
                    cursorclass=pymysql.cursors.DictCursor,
                    connect_timeout=30,
                    read_timeout=60,
                    write_timeout=60
                )
            except Exception as e:
                last_error = e
                print(f"[MySQL] Connection attempt {attempt + 1} failed: {str(e)}")
                if attempt < retries - 1:
                    time.sleep(1)
        
        raise last_error
    
    @staticmethod
    def execute_query(sql, params=None):
        """执行查询并返回结果"""
        conn = None
        cursor = None
        try:
            conn = DatabaseService.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_one(sql, params=None):
        """执行查询并返回单条结果"""
        conn = None
        cursor = None
        try:
            conn = DatabaseService.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchone()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_update(sql, params=None):
        """执行更新操作"""
        conn = None
        cursor = None
        try:
            conn = DatabaseService.get_connection()
            cursor = conn.cursor()
            affected = cursor.execute(sql, params or ())
            conn.commit()
            return affected
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()


class AppDatabaseService:
    """应用数据库服务类 - 平台自有数据库"""
    
    # 配置缓存
    _config_cache = None
    _config_cache_time = 0
    _CONFIG_CACHE_TTL = 60  # 配置缓存60秒
    
    @staticmethod
    def _get_cached_config():
        """获取缓存的数据库配置"""
        import time
        now = time.time()
        if AppDatabaseService._config_cache is None or (now - AppDatabaseService._config_cache_time) > AppDatabaseService._CONFIG_CACHE_TTL:
            config = ConfigService.load_config()
            AppDatabaseService._config_cache = config.get('app_mysql', {})
            AppDatabaseService._config_cache_time = now
        return AppDatabaseService._config_cache
    
    @staticmethod
    def get_connection():
        """获取应用数据库连接"""
        import pymysql
        
        mysql_config = AppDatabaseService._get_cached_config()
        
        return pymysql.connect(
            host=mysql_config.get('host', '47.82.64.147'),
            port=mysql_config.get('port', 3306),
            user=mysql_config.get('user', 'aiuser'),
            password=mysql_config.get('password', '123456'),
            database=mysql_config.get('database', 'aiuser'),
            charset='utf8mb4',
            cursorclass=pymysql.cursors.DictCursor
        )
    
    @staticmethod
    def execute_query(sql, params=None):
        """执行查询并返回结果"""
        conn = None
        cursor = None
        try:
            conn = AppDatabaseService.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchall()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_one(sql, params=None):
        """执行查询并返回单条结果"""
        conn = None
        cursor = None
        try:
            conn = AppDatabaseService.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            return cursor.fetchone()
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_update(sql, params=None):
        """执行更新操作，返回影响行数"""
        conn = None
        cursor = None
        try:
            conn = AppDatabaseService.get_connection()
            cursor = conn.cursor()
            affected = cursor.execute(sql, params or ())
            conn.commit()
            return affected
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    @staticmethod
    def execute_insert(sql, params=None):
        """执行插入操作，返回插入ID"""
        conn = None
        cursor = None
        try:
            conn = AppDatabaseService.get_connection()
            cursor = conn.cursor()
            cursor.execute(sql, params or ())
            conn.commit()
            return cursor.lastrowid
        finally:
            if cursor:
                cursor.close()
            if conn:
                conn.close()
    
    # ========== 数据集相关操作 ==========
    
    @staticmethod
    def get_datasets(book_id=None):
        """获取数据集列表"""
        sql = "SELECT * FROM datasets WHERE 1=1"
        params = []
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)
        sql += " ORDER BY created_at DESC"
        return AppDatabaseService.execute_query(sql, tuple(params) if params else None)
    
    @staticmethod
    def get_dataset(dataset_id):
        """获取单个数据集"""
        sql = "SELECT * FROM datasets WHERE dataset_id = %s"
        return AppDatabaseService.execute_one(sql, (dataset_id,))
    
    @staticmethod
    def create_dataset(dataset_id, book_id, pages, book_name=None, subject_id=None, 
                       question_count=0, name=None, description=None):
        """
        创建数据集
        
        Args:
            dataset_id: 数据集唯一标识
            book_id: 关联书本ID
            pages: 页码列表
            book_name: 书本名称
            subject_id: 学科ID
            question_count: 题目总数
            name: 数据集名称（可选，为空时由调用方生成默认名称）
            description: 数据集描述（可选）
        
        Returns:
            int: 插入的记录ID
        """
        sql = """INSERT INTO datasets 
                 (dataset_id, name, book_id, book_name, subject_id, pages, question_count, description, created_at) 
                 VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
        pages_json = json.dumps(pages) if isinstance(pages, list) else pages
        return AppDatabaseService.execute_insert(sql, (
            dataset_id, name, book_id, book_name, subject_id, pages_json, question_count, description, datetime.now()
        ))
    
    @staticmethod
    def update_dataset(dataset_id, **kwargs):
        """更新数据集"""
        if not kwargs:
            return 0
        set_parts = []
        params = []
        for key, value in kwargs.items():
            if key == 'pages' and isinstance(value, list):
                value = json.dumps(value)
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.append(dataset_id)
        sql = f"UPDATE datasets SET {', '.join(set_parts)} WHERE dataset_id = %s"
        return AppDatabaseService.execute_update(sql, tuple(params))
    
    @staticmethod
    def delete_dataset(dataset_id):
        """删除数据集及其基准效果"""
        AppDatabaseService.execute_update("DELETE FROM baseline_effects WHERE dataset_id = %s", (dataset_id,))
        return AppDatabaseService.execute_update("DELETE FROM datasets WHERE dataset_id = %s", (dataset_id,))
    
    @staticmethod
    def get_datasets_by_book_page(book_id, page_num):
        """
        根据 book_id 和 page_num 查询所有匹配的数据集
        
        Args:
            book_id: 书本ID
            page_num: 页码
        
        Returns:
            list: 匹配的数据集列表，按创建时间倒序排列
        """
        sql = """
            SELECT dataset_id, name, book_id, book_name, subject_id, 
                   pages, question_count, description, created_at
            FROM datasets 
            WHERE book_id = %s 
              AND JSON_CONTAINS(pages, %s)
            ORDER BY created_at DESC
        """
        return AppDatabaseService.execute_query(sql, (book_id, json.dumps(page_num)))
    
    @staticmethod
    def search_datasets_by_name(search_query, book_id=None):
        """
        按名称模糊搜索数据集
        
        Args:
            search_query: 搜索关键词
            book_id: 可选，限定书本ID
        
        Returns:
            list: 匹配的数据集列表
        """
        sql = "SELECT * FROM datasets WHERE name LIKE %s"
        params = [f'%{search_query}%']
        
        if book_id:
            sql += " AND book_id = %s"
            params.append(book_id)
        
        sql += " ORDER BY created_at DESC"
        return AppDatabaseService.execute_query(sql, tuple(params))
    
    # ========== 基准效果相关操作 ==========
    
    @staticmethod
    def get_baseline_effects(dataset_id, page_num=None):
        """获取基准效果列表"""
        sql = "SELECT * FROM baseline_effects WHERE dataset_id = %s"
        params = [dataset_id]
        if page_num is not None:
            sql += " AND page_num = %s"
            params.append(page_num)
        sql += " ORDER BY page_num, temp_index"
        return AppDatabaseService.execute_query(sql, tuple(params))
    
    @staticmethod
    def get_baseline_effects_by_page(dataset_id, page_num):
        """获取指定页码的基准效果，返回格式化的列表"""
        rows = AppDatabaseService.get_baseline_effects(dataset_id, page_num)
        result = []
        for row in rows:
            item = {
                'index': row['question_index'],
                'tempIndex': row['temp_index'],
                'type': row['question_type'],
                'answer': row['answer'],
                'userAnswer': row['user_answer'],
                'correct': row['is_correct']
            }
            # 解析 extra_data 获取 questionType、bvalue、maxScore 和 score
            extra_data = row.get('extra_data')
            if extra_data:
                try:
                    if isinstance(extra_data, str):
                        extra = json.loads(extra_data)
                    else:
                        extra = extra_data
                    item['questionType'] = extra.get('questionType', 'objective')
                    item['bvalue'] = extra.get('bvalue', '4')
                    if extra.get('maxScore') is not None:
                        item['maxScore'] = extra.get('maxScore')
                    if extra.get('score') is not None:
                        item['score'] = extra.get('score')
                except:
                    item['questionType'] = 'objective'
                    item['bvalue'] = '4'
            else:
                item['questionType'] = 'objective'
                item['bvalue'] = '4'
            result.append(item)
        return result
    
    @staticmethod
    def save_baseline_effects(dataset_id, page_num, effects):
        """保存基准效果（先删除旧数据再插入）"""
        AppDatabaseService.execute_update(
            "DELETE FROM baseline_effects WHERE dataset_id = %s AND page_num = %s",
            (dataset_id, page_num)
        )
        for effect in effects:
            # 构建extra_data存储额外字段（包含maxScore和score）
            extra_data = {
                'questionType': effect.get('questionType', 'objective'),
                'bvalue': effect.get('bvalue', '4')
            }
            # 存储 maxScore（题目总分）
            if effect.get('maxScore') is not None:
                extra_data['maxScore'] = effect.get('maxScore')
            # 存储 score（判断分值）
            if effect.get('score') is not None:
                extra_data['score'] = effect.get('score')
            sql = """INSERT INTO baseline_effects 
                     (dataset_id, page_num, question_index, temp_index, question_type, answer, user_answer, is_correct, extra_data)
                     VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"""
            AppDatabaseService.execute_insert(sql, (
                dataset_id, page_num,
                effect.get('index', ''),
                effect.get('tempIndex', 0),
                effect.get('type', 'choice'),
                effect.get('answer', ''),
                effect.get('userAnswer', ''),
                effect.get('correct', ''),
                json.dumps(extra_data, ensure_ascii=False)
            ))
    
    # ========== 批量任务相关操作 ==========
    
    @staticmethod
    def get_batch_tasks():
        """获取批量任务列表"""
        sql = "SELECT * FROM batch_tasks ORDER BY created_at DESC"
        return AppDatabaseService.execute_query(sql)
    
    @staticmethod
    def get_batch_task(task_id):
        """获取单个批量任务"""
        sql = "SELECT * FROM batch_tasks WHERE task_id = %s"
        return AppDatabaseService.execute_one(sql, (task_id,))
    
    @staticmethod
    def create_batch_task(task_id, name, homework_count=0):
        """创建批量任务"""
        sql = """INSERT INTO batch_tasks (task_id, name, status, homework_count, created_at) 
                 VALUES (%s, %s, 'pending', %s, %s)"""
        return AppDatabaseService.execute_insert(sql, (task_id, name, homework_count, datetime.now()))
    
    @staticmethod
    def update_batch_task(task_id, **kwargs):
        """更新批量任务"""
        if not kwargs:
            return 0
        set_parts = []
        params = []
        for key, value in kwargs.items():
            if key == 'error_distribution' and isinstance(value, dict):
                value = json.dumps(value)
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.append(task_id)
        sql = f"UPDATE batch_tasks SET {', '.join(set_parts)} WHERE task_id = %s"
        return AppDatabaseService.execute_update(sql, tuple(params))
    
    @staticmethod
    def delete_batch_task(task_id):
        """删除批量任务及其作业项"""
        # 先删除错误详情
        items = AppDatabaseService.execute_query(
            "SELECT id FROM batch_task_items WHERE task_id = %s", (task_id,)
        )
        for item in items:
            AppDatabaseService.execute_update(
                "DELETE FROM evaluation_errors WHERE task_item_id = %s", (item['id'],)
            )
        # 删除作业项
        AppDatabaseService.execute_update("DELETE FROM batch_task_items WHERE task_id = %s", (task_id,))
        # 删除任务
        return AppDatabaseService.execute_update("DELETE FROM batch_tasks WHERE task_id = %s", (task_id,))
    
    # ========== 批量任务作业项相关操作 ==========
    
    @staticmethod
    def get_batch_task_items(task_id):
        """获取批量任务的作业项列表"""
        sql = "SELECT * FROM batch_task_items WHERE task_id = %s ORDER BY id"
        return AppDatabaseService.execute_query(sql, (task_id,))
    
    @staticmethod
    def get_batch_task_item(task_id, homework_id):
        """获取单个作业项"""
        sql = "SELECT * FROM batch_task_items WHERE task_id = %s AND homework_id = %s"
        return AppDatabaseService.execute_one(sql, (task_id, homework_id))
    
    @staticmethod
    def create_batch_task_item(task_id, homework_id, **kwargs):
        """创建批量任务作业项"""
        fields = ['task_id', 'homework_id']
        values = [task_id, homework_id]
        placeholders = ['%s', '%s']
        
        for key, value in kwargs.items():
            fields.append(key)
            if key == 'evaluation_result' and isinstance(value, dict):
                value = json.dumps(value)
            values.append(value)
            placeholders.append('%s')
        
        sql = f"INSERT INTO batch_task_items ({', '.join(fields)}) VALUES ({', '.join(placeholders)})"
        return AppDatabaseService.execute_insert(sql, tuple(values))
    
    @staticmethod
    def update_batch_task_item(item_id, **kwargs):
        """更新批量任务作业项"""
        if not kwargs:
            return 0
        set_parts = []
        params = []
        for key, value in kwargs.items():
            if key == 'evaluation_result' and isinstance(value, dict):
                value = json.dumps(value)
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.append(item_id)
        sql = f"UPDATE batch_task_items SET {', '.join(set_parts)} WHERE id = %s"
        return AppDatabaseService.execute_update(sql, tuple(params))
    
    # ========== 会话相关操作 ==========
    
    @staticmethod
    def get_chat_sessions(session_type='chat'):
        """获取会话列表"""
        sql = "SELECT * FROM chat_sessions WHERE session_type = %s ORDER BY updated_at DESC"
        return AppDatabaseService.execute_query(sql, (session_type,))
    
    @staticmethod
    def get_chat_session(session_id):
        """获取单个会话"""
        sql = "SELECT * FROM chat_sessions WHERE session_id = %s"
        return AppDatabaseService.execute_one(sql, (session_id,))
    
    @staticmethod
    def save_chat_session(session_id, session_type='chat', title='新对话', messages=None):
        """保存或更新会话"""
        existing = AppDatabaseService.get_chat_session(session_id)
        messages_json = json.dumps(messages or [], ensure_ascii=False)
        
        if existing:
            sql = "UPDATE chat_sessions SET title = %s, messages = %s, updated_at = %s WHERE session_id = %s"
            return AppDatabaseService.execute_update(sql, (title, messages_json, datetime.now(), session_id))
        else:
            sql = """INSERT INTO chat_sessions (session_id, session_type, title, messages, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s)"""
            now = datetime.now()
            return AppDatabaseService.execute_insert(sql, (session_id, session_type, title, messages_json, now, now))
    
    @staticmethod
    def delete_chat_session(session_id):
        """删除会话"""
        return AppDatabaseService.execute_update("DELETE FROM chat_sessions WHERE session_id = %s", (session_id,))
    
    # ========== 系统配置相关操作 ==========
    
    @staticmethod
    def get_config(config_key):
        """获取配置项"""
        sql = "SELECT config_value FROM sys_config WHERE config_key = %s"
        row = AppDatabaseService.execute_one(sql, (config_key,))
        if row:
            try:
                return json.loads(row['config_value'])
            except:
                return row['config_value']
        return None
    
    @staticmethod
    def set_config(config_key, config_value, description=None):
        """设置配置项"""
        value_json = json.dumps(config_value, ensure_ascii=False) if not isinstance(config_value, str) else config_value
        existing = AppDatabaseService.execute_one(
            "SELECT id FROM sys_config WHERE config_key = %s", (config_key,)
        )
        if existing:
            sql = "UPDATE sys_config SET config_value = %s WHERE config_key = %s"
            return AppDatabaseService.execute_update(sql, (value_json, config_key))
        else:
            sql = "INSERT INTO sys_config (config_key, config_value, description) VALUES (%s, %s, %s)"
            return AppDatabaseService.execute_insert(sql, (config_key, value_json, description))
    
    # ========== 提示词模板相关操作 ==========
    
    @staticmethod
    def get_prompt_templates(prompt_type=None):
        """获取提示词模板列表"""
        sql = "SELECT * FROM prompt_templates WHERE is_active = 1"
        params = []
        if prompt_type:
            sql += " AND prompt_type = %s"
            params.append(prompt_type)
        sql += " ORDER BY is_default DESC, id"
        return AppDatabaseService.execute_query(sql, tuple(params) if params else None)
    
    @staticmethod
    def save_prompt_template(name, content, prompt_type='general', is_default=False):
        """保存提示词模板"""
        sql = """INSERT INTO prompt_templates (name, content, prompt_type, is_default) 
                 VALUES (%s, %s, %s, %s)"""
        return AppDatabaseService.execute_insert(sql, (name, content, prompt_type, 1 if is_default else 0))

    # ========== 用户相关操作 ==========
    
    @staticmethod
    def get_user_by_id(user_id):
        """根据ID获取用户"""
        sql = "SELECT * FROM users WHERE id = %s"
        return AppDatabaseService.execute_one(sql, (user_id,))
    
    @staticmethod
    def get_user_by_username(username):
        """根据用户名获取用户"""
        sql = "SELECT * FROM users WHERE username = %s"
        return AppDatabaseService.execute_one(sql, (username,))
    
    @staticmethod
    def get_user_by_token(token):
        """根据记住登录Token获取用户"""
        sql = "SELECT * FROM users WHERE remember_token = %s"
        return AppDatabaseService.execute_one(sql, (token,))
    
    @staticmethod
    def create_user(username, password_hash):
        """创建用户"""
        sql = """INSERT INTO users (username, password_hash, created_at, updated_at) 
                 VALUES (%s, %s, %s, %s)"""
        now = datetime.now()
        return AppDatabaseService.execute_insert(sql, (username, password_hash, now, now))
    
    @staticmethod
    def update_user_token(user_id, token, expires_at):
        """更新用户的记住登录Token"""
        sql = "UPDATE users SET remember_token = %s, token_expires_at = %s, updated_at = %s WHERE id = %s"
        return AppDatabaseService.execute_update(sql, (token, expires_at, datetime.now(), user_id))
    
    @staticmethod
    def update_user_api_keys(user_id, api_keys):
        """更新用户的API密钥配置"""
        api_keys_json = json.dumps(api_keys, ensure_ascii=False) if api_keys else None
        sql = "UPDATE users SET api_keys = %s, updated_at = %s WHERE id = %s"
        return AppDatabaseService.execute_update(sql, (api_keys_json, datetime.now(), user_id))
    
    @staticmethod
    def get_user_api_keys(user_id):
        """获取用户的API密钥配置"""
        sql = "SELECT api_keys FROM users WHERE id = %s"
        row = AppDatabaseService.execute_one(sql, (user_id,))
        if row and row['api_keys']:
            try:
                keys = json.loads(row['api_keys'])
                # 兼容旧字段名
                result = {}
                result['api_key'] = keys.get('api_key') or keys.get('doubao_key', '')
                result['gpt_api_key'] = keys.get('gpt_api_key') or keys.get('gpt_key', '')
                result['deepseek_api_key'] = keys.get('deepseek_api_key') or keys.get('deepseek_key', '')
                result['qwen_api_key'] = keys.get('qwen_api_key') or keys.get('qwen_key', '')
                result['api_url'] = keys.get('api_url', '')
                result['gpt_api_url'] = keys.get('gpt_api_url', '')
                return result
            except:
                return {}
        return {}
    
    # ========== 会话相关操作（支持用户隔离）==========
    
    @staticmethod
    def get_chat_sessions_by_user(user_id, session_type='chat'):
        """获取指定用户的会话列表"""
        sql = "SELECT * FROM chat_sessions WHERE user_id = %s AND session_type = %s ORDER BY updated_at DESC"
        return AppDatabaseService.execute_query(sql, (user_id, session_type))
    
    @staticmethod
    def save_chat_session_with_user(session_id, user_id, session_type='chat', title='新对话', messages=None):
        """保存或更新会话（带用户ID）"""
        existing = AppDatabaseService.get_chat_session(session_id)
        messages_json = json.dumps(messages or [], ensure_ascii=False)
        
        if existing:
            sql = "UPDATE chat_sessions SET title = %s, messages = %s, updated_at = %s WHERE session_id = %s"
            return AppDatabaseService.execute_update(sql, (title, messages_json, datetime.now(), session_id))
        else:
            sql = """INSERT INTO chat_sessions (session_id, user_id, session_type, title, messages, created_at, updated_at) 
                     VALUES (%s, %s, %s, %s, %s, %s, %s)"""
            now = datetime.now()
            return AppDatabaseService.execute_insert(sql, (session_id, user_id, session_type, title, messages_json, now, now))


    # ========== 基准合集相关操作 ==========
    
    @staticmethod
    def get_collections():
        """获取所有合集列表"""
        sql = """
            SELECT c.*, COUNT(cd.dataset_id) as dataset_count
            FROM dataset_collections c
            LEFT JOIN collection_datasets cd ON c.collection_id = cd.collection_id
            GROUP BY c.collection_id
            ORDER BY c.created_at DESC
        """
        return AppDatabaseService.execute_query(sql)
    
    @staticmethod
    def get_collection(collection_id):
        """获取单个合集"""
        sql = "SELECT * FROM dataset_collections WHERE collection_id = %s"
        return AppDatabaseService.execute_one(sql, (collection_id,))
    
    @staticmethod
    def get_collection_with_datasets(collection_id):
        """获取合集及其包含的数据集列表"""
        collection = AppDatabaseService.get_collection(collection_id)
        if not collection:
            return None
        
        # 获取关联的数据集ID列表
        # 使用 COLLATE 解决字符集排序规则不匹配问题
        sql = """
            SELECT cd.dataset_id, d.name, d.book_id, d.book_name, d.pages, 
                   d.question_count, d.created_at as dataset_created_at, cd.added_at
            FROM collection_datasets cd
            LEFT JOIN datasets d ON cd.dataset_id COLLATE utf8mb4_general_ci = d.dataset_id COLLATE utf8mb4_general_ci
            WHERE cd.collection_id = %s
            ORDER BY cd.added_at DESC
        """
        datasets = AppDatabaseService.execute_query(sql, (collection_id,))
        
        # 解析 pages JSON
        for ds in datasets:
            if ds.get('pages'):
                try:
                    ds['pages'] = json.loads(ds['pages']) if isinstance(ds['pages'], str) else ds['pages']
                except:
                    ds['pages'] = []
        
        collection['datasets'] = datasets
        return collection
    
    @staticmethod
    def create_collection(collection_id, name, description=None):
        """创建合集"""
        sql = """INSERT INTO dataset_collections (collection_id, name, description, created_at, updated_at) 
                 VALUES (%s, %s, %s, %s, %s)"""
        now = datetime.now()
        return AppDatabaseService.execute_insert(sql, (collection_id, name, description, now, now))
    
    @staticmethod
    def update_collection(collection_id, **kwargs):
        """更新合集"""
        if not kwargs:
            return 0
        kwargs['updated_at'] = datetime.now()
        set_parts = []
        params = []
        for key, value in kwargs.items():
            set_parts.append(f"{key} = %s")
            params.append(value)
        params.append(collection_id)
        sql = f"UPDATE dataset_collections SET {', '.join(set_parts)} WHERE collection_id = %s"
        return AppDatabaseService.execute_update(sql, tuple(params))
    
    @staticmethod
    def delete_collection(collection_id):
        """删除合集及其关联"""
        # 先删除关联
        AppDatabaseService.execute_update(
            "DELETE FROM collection_datasets WHERE collection_id = %s", (collection_id,)
        )
        # 再删除合集
        return AppDatabaseService.execute_update(
            "DELETE FROM dataset_collections WHERE collection_id = %s", (collection_id,)
        )
    
    @staticmethod
    def add_dataset_to_collection(collection_id, dataset_id):
        """添加数据集到合集"""
        sql = """INSERT IGNORE INTO collection_datasets (collection_id, dataset_id, added_at) 
                 VALUES (%s, %s, %s)"""
        return AppDatabaseService.execute_insert(sql, (collection_id, dataset_id, datetime.now()))
    
    @staticmethod
    def remove_dataset_from_collection(collection_id, dataset_id):
        """从合集移除数据集"""
        sql = "DELETE FROM collection_datasets WHERE collection_id = %s AND dataset_id = %s"
        return AppDatabaseService.execute_update(sql, (collection_id, dataset_id))
    
    @staticmethod
    def get_collection_dataset_ids(collection_id):
        """获取合集中的数据集ID列表"""
        sql = "SELECT dataset_id FROM collection_datasets WHERE collection_id = %s"
        rows = AppDatabaseService.execute_query(sql, (collection_id,))
        return [row['dataset_id'] for row in rows]
    
    @staticmethod
    def batch_add_datasets_to_collection(collection_id, dataset_ids):
        """批量添加数据集到合集"""
        if not dataset_ids:
            return 0
        now = datetime.now()
        count = 0
        for dataset_id in dataset_ids:
            try:
                sql = """INSERT IGNORE INTO collection_datasets (collection_id, dataset_id, added_at) 
                         VALUES (%s, %s, %s)"""
                AppDatabaseService.execute_insert(sql, (collection_id, dataset_id, now))
                count += 1
            except:
                pass
        return count
