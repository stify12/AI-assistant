"""
数据库迁移脚本 - 添加用户认证相关表和字段
"""
from services.database_service import AppDatabaseService

def migrate():
    # 创建 users 表
    sql_users = '''
    CREATE TABLE IF NOT EXISTS users (
      id INT UNSIGNED NOT NULL AUTO_INCREMENT,
      username VARCHAR(50) NOT NULL,
      password_hash VARCHAR(255) NOT NULL,
      api_keys JSON,
      remember_token VARCHAR(64) DEFAULT NULL,
      token_expires_at DATETIME DEFAULT NULL,
      created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
      updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
      PRIMARY KEY (id),
      UNIQUE KEY uk_username (username),
      KEY idx_remember_token (remember_token)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4
    '''
    try:
        AppDatabaseService.execute_update(sql_users)
        print('users table created')
    except Exception as e:
        print(f'users table: {e}')

    # 添加 user_id 字段到 chat_sessions
    try:
        AppDatabaseService.execute_update('ALTER TABLE chat_sessions ADD COLUMN user_id INT UNSIGNED DEFAULT NULL')
        print('chat_sessions.user_id added')
    except Exception as e:
        print(f'chat_sessions.user_id: {e}')

    # 添加 user_id 字段到 prompt_templates
    try:
        AppDatabaseService.execute_update('ALTER TABLE prompt_templates ADD COLUMN user_id INT UNSIGNED DEFAULT NULL')
        print('prompt_templates.user_id added')
    except Exception as e:
        print(f'prompt_templates.user_id: {e}')

    # 添加 user_id 字段到 knowledge_tasks
    try:
        AppDatabaseService.execute_update('ALTER TABLE knowledge_tasks ADD COLUMN user_id INT UNSIGNED DEFAULT NULL')
        print('knowledge_tasks.user_id added')
    except Exception as e:
        print(f'knowledge_tasks.user_id: {e}')

    # 添加 user_id 字段到 model_stats
    try:
        AppDatabaseService.execute_update('ALTER TABLE model_stats ADD COLUMN user_id INT UNSIGNED DEFAULT NULL')
        print('model_stats.user_id added')
    except Exception as e:
        print(f'model_stats.user_id: {e}')

    print('Migration completed')

if __name__ == '__main__':
    migrate()
