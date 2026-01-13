"""
AI批改效果分析平台 - 主入口文件
Flask 应用初始化和蓝图注册
"""
import os
from flask import Flask

# 创建 Flask 应用实例
app = Flask(__name__)

# 注册所有路由蓝图
from routes import register_blueprints
register_blueprints(app)

# 注册知识点类题生成蓝图
from knowledge_agent.routes import knowledge_agent_bp
app.register_blueprint(knowledge_agent_bp)


if __name__ == '__main__':
    # 开发模式支持热重载
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
