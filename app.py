"""
AI批改效果分析平台 - 主入口文件
Flask 应用初始化和蓝图注册
"""
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
    app.run(debug=True, port=5000)
