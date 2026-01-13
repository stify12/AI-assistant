"""
AI批改效果分析平台 - 主入口文件
Flask 应用初始化和蓝图注册
"""
import os
import secrets
from flask import Flask
from datetime import timedelta

# 创建 Flask 应用实例
app = Flask(__name__)

# 配置 Session（使用固定的 secret_key，避免重启后 session 失效）
app.secret_key = os.environ.get('SECRET_KEY', 'ai-grading-platform-secret-key-2026')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 注册所有路由蓝图
from routes import register_blueprints
register_blueprints(app)

# 注册认证蓝图
from routes.auth import auth_bp
app.register_blueprint(auth_bp)

# 注册知识点类题生成蓝图
from knowledge_agent.routes import knowledge_agent_bp
app.register_blueprint(knowledge_agent_bp)


if __name__ == '__main__':
    # 开发模式支持热重载
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
