"""
AI批改效果分析平台 - 主入口文件
Flask 应用初始化和蓝图注册
"""
import os
import secrets
import atexit
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

# 初始化调度服务 (US-10)
def init_scheduler():
    """初始化 APScheduler 调度器"""
    try:
        from services.schedule_service import ScheduleService
        if ScheduleService.init_scheduler():
            print("[App] 调度服务初始化成功")
            # 添加日报自动生成调度 (US-14, 9.3)
            ScheduleService.schedule_daily_report()
            # 添加每日统计快照调度 (US-15, 10.1)
            ScheduleService.schedule_daily_statistics_snapshot()
            # 注册退出时关闭调度器
            atexit.register(ScheduleService.shutdown_scheduler)
        else:
            print("[App] 调度服务初始化失败或 APScheduler 未安装")
    except Exception as e:
        print(f"[App] 调度服务初始化异常: {e}")

# 在非调试模式或主进程中初始化调度器
# 避免在 Flask 热重载时重复初始化
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    init_scheduler()


if __name__ == '__main__':
    # 开发模式支持热重载
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
