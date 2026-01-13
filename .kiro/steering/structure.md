# 项目结构

```
├── app.py                 # Flask应用入口
├── config.json            # 应用配置 (API密钥、数据库连接等)
├── prompts.json           # AI提示词配置
│
├── routes/                # Flask蓝图路由
│   ├── __init__.py        # 蓝图注册
│   ├── common.py          # 通用路由 (首页、配置、会话)
│   ├── batch_evaluation.py # 批量评估
│   ├── subject_grading.py # 学科批改
│   ├── data_analysis.py   # 数据分析
│   ├── prompt_optimize.py # Prompt调优
│   └── ...
│
├── services/              # 业务服务层
│   ├── config_service.py  # 配置管理
│   ├── llm_service.py     # LLM调用封装
│   ├── database_service.py # 数据库操作
│   ├── session_service.py # 会话管理
│   └── storage_service.py # 文件存储
│
├── knowledge_agent/       # 知识点类题生成模块
│   ├── routes.py          # API路由
│   ├── agent.py           # Agent逻辑
│   ├── models.py          # 数据模型
│   ├── services.py        # 服务层
│   └── tools.py           # 工具函数
│
├── utils/                 # 工具函数
│   ├── file_utils.py      # 文件操作
│   └── text_utils.py      # 文本处理
│
├── templates/             # Jinja2 HTML模板
├── static/
│   ├── css/               # 样式文件
│   └── js/                # JavaScript文件
│
├── tests/                 # 测试文件
│   └── test_*.py          # pytest测试 (含hypothesis属性测试)
│
├── datasets/              # 数据集存储
├── batch_tasks/           # 批量任务存储
├── sessions/              # 会话数据
├── exports/               # 导出文件
└── knowledge_uploads/     # 知识点图片上传
```

## 架构模式
- **路由层** (`routes/`): Flask蓝图，处理HTTP请求
- **服务层** (`services/`): 业务逻辑封装
- **工具层** (`utils/`): 通用工具函数
- **模块化**: 独立功能模块如 `knowledge_agent/`

## 命名约定
- 路由文件: `snake_case.py`
- 蓝图命名: `feature_name_bp`
- API路径: `/api/feature-name/action`
- 模板文件: `feature-name.html`
- CSS/JS文件: `feature-name.css`, `feature-name.js`

## 数据存储
- JSON文件存储任务和会话数据
- MySQL存储作业数据和评估结果
- 文件上传存储在对应的 `*_uploads/` 目录
