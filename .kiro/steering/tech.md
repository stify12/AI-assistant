# 技术栈

## 后端
- **框架**: Flask (Python)
- **数据库**: MySQL (PyMySQL)
- **生产服务器**: Gunicorn

## 前端
- **模板引擎**: Jinja2
- **样式**: 原生CSS (无框架)
- **脚本**: 原生JavaScript (无框架)

## AI/LLM集成
- **Qwen**: 通义千问 (dashscope API)
- **DeepSeek**: deepseek-chat, deepseek-v3.2
- **视觉模型**: 豆包 doubao-vision (火山引擎 API)

## 依赖库
- `flask`: Web框架
- `requests`: HTTP请求
- `openpyxl`: Excel文件处理
- `python-docx`: Word文档处理
- `pymysql`: MySQL连接

## 常用命令

```bash
# 开发运行
python app.py

# 生产运行
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app

# Docker构建
docker build -t ai-grading-platform .

# Docker运行
docker-compose up -d

# 运行测试
pytest tests/ -v

# 运行属性测试
pytest tests/test_properties.py -v
```

## 环境变量
- `FLASK_ENV`: production/development
- `USE_DB_STORAGE`: true/false (是否使用数据库存储)
- `TZ`: 时区设置 (Asia/Shanghai)
