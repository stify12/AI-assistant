"""
AI批改效果分析平台 - 主入口文件
Flask 应用初始化和蓝图注册
"""
import os
import secrets
import atexit
import gzip
from io import BytesIO
from flask import Flask, request, send_from_directory
from datetime import timedelta

# 创建 Flask 应用实例
app = Flask(__name__)

# 配置 Session（使用固定的 secret_key，避免重启后 session 失效）
app.secret_key = os.environ.get('SECRET_KEY', 'ai-grading-platform-secret-key-2026')
app.config['SESSION_TYPE'] = 'filesystem'
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=30)

# 静态文件缓存配置 - 提升加载速度
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 31536000  # 1年缓存


@app.after_request
def add_cache_headers(response):
    """为静态资源添加缓存头和 gzip 压缩，提升加载速度"""
    # gzip 压缩：对 API JSON 响应启用（静态文件由 send_file 处理，不在这里压缩）
    if (response.status_code == 200 and 
        response.content_type and
        'application/json' in response.content_type and
        'gzip' in request.headers.get('Accept-Encoding', '') and
        'Content-Encoding' not in response.headers and
        not response.direct_passthrough):
        
        try:
            data = response.get_data()
            if len(data) > 500:  # 只压缩大于 500 字节的响应
                gzip_buffer = BytesIO()
                with gzip.GzipFile(mode='wb', fileobj=gzip_buffer, compresslevel=6) as f:
                    f.write(data)
                response.set_data(gzip_buffer.getvalue())
                response.headers['Content-Encoding'] = 'gzip'
                response.headers['Content-Length'] = len(response.get_data())
                response.headers['Vary'] = 'Accept-Encoding'
        except Exception:
            pass  # 压缩失败时静默忽略
    
    if request.path.startswith('/static/'):
        # CSS/JS 文件使用版本号控制，可以长期缓存
        if request.path.endswith(('.css', '.js')):
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1年
        # 图片等资源
        elif request.path.endswith(('.png', '.jpg', '.jpeg', '.gif', '.ico', '.svg', '.woff', '.woff2')):
            response.headers['Cache-Control'] = 'public, max-age=31536000'  # 1年
    # API 响应不缓存
    elif request.path.startswith('/api/'):
        response.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    return response

# 注册所有路由蓝图
from routes import register_blueprints
register_blueprints(app)

# 注册认证蓝图
from routes.auth import auth_bp
app.register_blueprint(auth_bp)

# 注册知识点类题生成蓝图
from knowledge_agent.routes import knowledge_agent_bp
app.register_blueprint(knowledge_agent_bp)

# 初始化调度服务 (US-10) - 使用统一调度服务
def init_scheduler():
    """初始化 APScheduler 调度器"""
    try:
        from services.unified_schedule_service import UnifiedScheduleService
        if UnifiedScheduleService.init_scheduler():
            print("[App] 统一调度服务初始化成功")
            # 注册退出时关闭调度器
            atexit.register(UnifiedScheduleService.shutdown_scheduler)
        else:
            print("[App] 调度服务初始化失败或 APScheduler 未安装")
    except Exception as e:
        print(f"[App] 调度服务初始化异常: {e}")
        import traceback
        traceback.print_exc()

# 在非调试模式或主进程中初始化调度器
# 避免在 Flask 热重载时重复初始化
if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not app.debug:
    init_scheduler()


if __name__ == '__main__':
    # 开发模式支持热重载
    debug_mode = os.environ.get('FLASK_DEBUG', '0') == '1' or os.environ.get('FLASK_ENV') == 'development'
    app.run(debug=debug_mode, host='0.0.0.0', port=5000)
