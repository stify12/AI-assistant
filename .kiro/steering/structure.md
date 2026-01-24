# 项目结构

```
├── app.py                 # Flask应用入口
├── config.json            # 应用配置 (API密钥、数据库连接等)
├── config.example.json    # 配置文件模板
├── prompts.json           # AI提示词配置
├── database_schema.sql    # 数据库表结构
├── automation_config.json # 自动化调度配置
│
├── routes/                # Flask蓝图路由
│   ├── __init__.py        # 蓝图注册
│   ├── common.py          # 通用路由 (首页、配置、会话)
│   ├── auth.py            # 用户认证
│   ├── dashboard.py       # 测试计划看板 (概览/任务/数据集/学科/计划CRUD)
│   ├── batch_evaluation.py # 批量评估
│   ├── batch_compare.py   # 批量对比分析
│   ├── subject_grading.py # 学科批改
│   ├── data_analysis.py   # 数据分析
│   ├── dataset_manage.py  # 数据集管理
│   ├── prompt_optimize.py # Prompt调优
│   ├── prompt_manage.py   # Prompt管理
│   ├── ai_eval.py         # AI评估
│   ├── chat.py            # 对话功能
│   ├── model_recommend.py # 模型推荐
│   ├── automation.py      # 自动化调度
│   ├── anomaly.py         # 异常检测
│   ├── clustering.py      # 聚类分析
│   ├── drilldown.py       # 下钻分析
│   ├── error_samples.py   # 错误样本管理
│   ├── error_correlation.py # 错误关联分析
│   ├── error_mark.py      # 错误标记
│   ├── best_practice.py   # 最佳实践推荐
│   ├── optimization.py    # 优化建议
│   ├── saved_filter.py    # 保存筛选器
│   ├── task_assignment.py # 任务分配
│   ├── image_compare.py   # 图片对比
│   └── analysis.py        # 通用分析
│
├── services/              # 业务服务层
│   ├── config_service.py  # 配置管理
│   ├── llm_service.py     # LLM调用封装
│   ├── database_service.py # 数据库操作 (含数据集CRUD)
│   ├── session_service.py # 会话管理
│   ├── storage_service.py # 文件/数据库存储 (USE_DB_STORAGE控制)
│   ├── auth_service.py    # 认证服务
│   ├── physics_eval.py    # 物理评估服务
│   ├── chemistry_eval.py  # 化学评估服务
│   ├── dashboard_service.py # 看板服务 (统计/缓存/计划管理)
│   ├── automation_service.py # 自动化调度服务
│   ├── anomaly_service.py # 异常检测服务
│   ├── clustering_service.py # 聚类分析服务
│   ├── drilldown_service.py # 下钻分析服务
│   ├── error_sample_service.py # 错误样本服务
│   ├── error_correlation_service.py # 错误关联服务
│   ├── batch_compare_service.py # 批量对比服务
│   ├── best_practice_service.py # 最佳实践服务
│   ├── optimization_service.py # 优化建议服务
│   ├── saved_filter_service.py # 筛选器服务
│   ├── task_assignment_service.py # 任务分配服务
│   ├── ai_analysis_service.py # AI分析服务
│   └── excel_export_service.py # Excel导出服务
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
│   │   ├── index.css      # 首页样式 (含Dashboard看板)
│   │   ├── compare.css    # 对比页样式
│   │   ├── batch-evaluation.css
│   │   ├── subject-grading.css
│   │   ├── subject-grading-modules.css
│   │   ├── data-analysis.css
│   │   ├── dataset-manage.css
│   │   ├── knowledge-agent.css
│   │   ├── prompt-optimize.css
│   │   └── modules/       # 模块化CSS
│   │       ├── batch-compare.css
│   │       ├── drilldown.css
│   │       └── virtual-scroll.css
│   └── js/                # JavaScript文件
│       ├── index.js       # 首页JS (含Dashboard看板)
│       ├── compare.js
│       ├── batch-evaluation.js
│       ├── subject-grading.js
│       ├── subject-grading-*.js  # 学科批改模块化JS
│       ├── data-analysis.js
│       ├── dataset-manage.js
│       ├── knowledge-agent.js
│       ├── prompt-optimize.js
│       └── modules/       # 模块化JS
│           ├── ab-test.js
│           ├── anomaly-detection.js
│           ├── batch-compare.js
│           ├── best-practice.js
│           ├── clustering.js
│           ├── coverage-analysis.js
│           ├── drilldown.js
│           ├── error-samples.js
│           ├── export-progress.js
│           ├── image-compare.js
│           ├── optimization.js
│           └── virtual-scroll.js
│
├── tests/                 # 测试文件
│   ├── test_dataset_api.py    # 数据集API测试 (含属性测试)
│   ├── test_physics_eval.py   # 物理评估测试
│   └── test_*.py              # 其他测试文件
│
├── migrations/            # 数据库迁移脚本
│   ├── 00_init_schema.sql     # 初始化表结构
│   ├── add_ai_analysis_tables.sql  # AI分析相关表
│   ├── add_error_analysis_tables.sql # 错误分析相关表
│   └── run_migration.py       # 迁移执行脚本
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
└── saved_filters/         # 保存的筛选器
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
- MySQL存储作业数据、评估结果、数据集
- 文件上传存储在对应的 `*_uploads/` 目录
- 存储模式由 `USE_DB_STORAGE` 环境变量控制 (默认 true)

## 数据集存储
- 数据库表: `datasets` (元数据) + `baseline_effects` (基准效果)
- 支持字段: `name`, `description`, `book_id`, `book_name`, `pages`, `question_count`
- 默认名称生成: `StorageService.generate_default_dataset_name()`
