# 项目结构

```
├── app.py                 # Flask应用入口
├── config.json            # 应用配置 (API密钥、数据库连接等)
├── config.example.json    # 配置文件模板
├── prompts.json           # AI提示词配置
├── database_schema.sql    # 数据库表结构
│
├── routes/                # Flask蓝图路由
│   ├── __init__.py        # 蓝图注册
│   ├── common.py          # 通用路由 (首页、配置、会话)
│   ├── auth.py            # 用户认证
│   ├── batch_evaluation.py # 批量评估
│   ├── batch_compare.py   # 批量对比
│   ├── subject_grading.py # 学科批改
│   ├── data_analysis.py   # 数据分析
│   ├── dataset_manage.py  # 数据集管理
│   ├── prompt_optimize.py # Prompt调优
│   ├── prompt_manage.py   # Prompt管理
│   ├── ai_eval.py         # AI评估
│   ├── chat.py            # 对话功能
│   └── model_recommend.py # 模型推荐
│
├── services/              # 业务服务层
│   ├── config_service.py  # 配置管理
│   ├── llm_service.py     # LLM调用封装
│   ├── database_service.py # 数据库操作
│   ├── session_service.py # 会话管理
│   ├── storage_service.py # 文件存储
│   └── auth_service.py    # 认证服务
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
│   ├── index.html         # 首页 (对话)
│   ├── compare.html       # 对比页面
│   ├── batch-evaluation.html  # 批量评估
│   ├── subject-grading.html   # 学科批改
│   ├── data-analysis.html     # 数据分析
│   ├── dataset-manage.html    # 数据集管理
│   ├── knowledge-agent.html   # 知识点类题
│   └── prompt-optimize.html   # Prompt调优
│
├── static/
│   ├── css/               # 样式文件
│   │   ├── common.css     # 公共样式
│   │   ├── index.css      # 首页样式
│   │   ├── compare.css    # 对比页样式
│   │   ├── batch-evaluation.css
│   │   ├── subject-grading.css
│   │   ├── subject-grading-modules.css
│   │   ├── data-analysis.css
│   │   ├── dataset-manage.css
│   │   ├── knowledge-agent.css
│   │   └── prompt-optimize.css
│   └── js/                # JavaScript文件
│       ├── index.js
│       ├── compare.js
│       ├── batch-evaluation.js
│       ├── subject-grading.js
│       ├── subject-grading-*.js  # 学科批改模块化JS
│       ├── data-analysis.js
│       ├── dataset-manage.js
│       ├── knowledge-agent.js
│       └── prompt-optimize.js
│
├── tests/                 # 测试文件
│   ├── test_batch_evaluation.py
│   ├── test_knowledge_agent.py
│   └── test_properties.py # hypothesis属性测试
│
├── datasets/              # 数据集存储 (JSON)
├── batch_tasks/           # 批量任务存储
├── analysis_tasks/        # 分析任务存储
├── prompt_tasks/          # Prompt任务存储
├── knowledge_tasks/       # 知识点任务存储
├── sessions/              # 会话数据
├── chat_sessions/         # 对话会话
├── exports/               # 导出文件
├── knowledge_uploads/     # 知识点图片上传
├── analysis_files/        # 分析文件上传
└── baseline_effects/      # 基准效果数据
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
- JSON文件存储任务和会话数据 (`*_tasks/`, `sessions/`)
- MySQL存储作业数据和评估结果
- 文件上传存储在对应的 `*_uploads/` 目录
