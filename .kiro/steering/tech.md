# 技术栈

## 后端
- **框架**: Flask (Python 3.8+)
- **数据库**: MySQL (PyMySQL)
- **生产服务器**: Gunicorn
- **容器化**: Docker + Docker Compose

## 前端
- **模板引擎**: Jinja2
- **样式**: 原生CSS (无框架)
- **脚本**: 原生JavaScript (无框架)

## AI/LLM集成
- **豆包 Doubao**: 火山引擎视觉模型 (主要)
- **DeepSeek**: deepseek-chat, deepseek-v3.2
- **Qwen**: 通义千问 (dashscope API)

## 核心依赖
```
flask          # Web框架
gunicorn       # 生产服务器
requests       # HTTP请求
openpyxl       # Excel文件处理
python-docx    # Word文档处理
pymysql        # MySQL连接
pytest         # 测试框架
hypothesis     # 属性测试
```

## 常用命令

```bash
# 开发运行
python app.py

# 生产运行
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app

# Docker构建运行
docker-compose up -d --build

# 运行测试 (使用文件存储避免污染数据库)
USE_DB_STORAGE=false pytest tests/ -v

# 运行数据集API测试
USE_DB_STORAGE=false pytest tests/test_dataset_api.py -v

# 部署到服务器
.\deploy-quick.ps1
```

## 环境变量
| 变量 | 说明 | 默认值 |
|-----|------|-------|
| FLASK_ENV | 运行环境 | development |
| USE_DB_STORAGE | 是否使用数据库存储 | true |
| TZ | 时区设置 | Asia/Shanghai |

## 配置文件
- `config.json`: 应用配置 (API密钥、数据库连接)
- `config.example.json`: 配置模板
- `prompts.json`: AI提示词配置
- `.env.example`: 环境变量模板
