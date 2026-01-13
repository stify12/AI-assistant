# Implementation Plan

- [x] 1. 创建项目目录结构和基础模块




  - [ ] 1.1 创建 routes/ 目录和 __init__.py
    - 创建 routes 目录


    - 创建 __init__.py 文件，包含 register_blueprints 函数
    - _Requirements: 1.1, 4.1_


  - [ ] 1.2 创建 services/ 目录和 __init__.py
    - 创建 services 目录




    - 创建 __init__.py 文件
    - _Requirements: 2.1, 2.2_
  - [ ] 1.3 创建 utils/ 目录和 __init__.py
    - 创建 utils 目录
    - 创建 __init__.py 文件


    - _Requirements: 2.3_

- [ ] 2. 实现服务层模块
  - [ ] 2.1 实现 config_service.py
    - 提取 load_config, save_config, load_prompts, save_prompts 函数


    - 创建 ConfigService 类封装配置操作
    - _Requirements: 2.1_
  - [ ]* 2.2 编写 config_service 属性测试
    - **Property 3: Service Layer Data Consistency**


    - **Validates: Requirements 2.1**
  - [x] 2.3 实现 session_service.py


    - 提取会话管理函数：load_session, save_session, clear_session, get_all_sessions
    - 支持普通会话和聊天会话两种类型




    - _Requirements: 2.2_


  - [ ]* 2.4 编写 session_service 属性测试
    - **Property 4: Session Round-Trip Integrity**
    - **Validates: Requirements 2.2**
  - [x] 2.5 实现 llm_service.py




    - 提取 Qwen API 调用逻辑
    - 提取 DeepSeek API 调用逻辑
    - 提取视觉模型调用逻辑
    - 提取 JSON 响应解析逻辑



    - _Requirements: 5.1_

  - [ ] 2.6 实现 database_service.py
    - 提取 get_mysql_connection 函数
    - 封装数据库查询和更新操作



    - _Requirements: 5.2_
  - [ ] 2.7 实现 storage_service.py
    - 提取文件存储相关函数



    - 封装 JSON 文件读写操作
    - _Requirements: 5.3_

- [ ] 3. 实现工具函数模块
  - [ ] 3.1 实现 file_utils.py
    - 提取 get_file_path, generate_unique_id, safe_filename 等函数

    - _Requirements: 2.3_

  - [ ] 3.2 实现 text_utils.py
    - 提取 normalize_answer, extract_json_from_text, remove_think_tags 等函数
    - _Requirements: 2.3_

- [ ] 4. Checkpoint - 确保服务层和工具层测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [x] 5. 实现路由模块 - 通用路由

  - [x] 5.1 实现 routes/common.py

    - 提取首页路由：/, /compare, /subject-grading, /batch-evaluation
    - 提取配置路由：/api/config
    - 提取会话路由：/api/session, /api/all-sessions
    - 提取模板下载路由：/api/download-template
    - _Requirements: 3.1, 4.3_


- [x] 6. 实现路由模块 - 批量对比

  - [ ] 6.1 实现 routes/batch_compare.py
    - 提取 /api/batch-compare/analyze 路由
    - 提取 /api/batch-compare/report 路由
    - 提取 /api/batch-compare/export-report 路由
    - 提取 analyze_error_type, generate_optimization_suggestions 辅助函数

    - _Requirements: 3.1_


- [ ] 7. 实现路由模块 - 提示词管理
  - [ ] 7.1 实现 routes/prompt_manage.py
    - 提取 /api/prompts 路由（GET, POST, DELETE）
    - 提取 /api/optimize-prompt 路由
    - _Requirements: 3.2_


- [x] 8. 实现路由模块 - 聊天与 MCP 工具

  - [ ] 8.1 实现 routes/chat.py
    - 提取 /api/chat 路由
    - 提取 /api/chat-session 路由
    - 提取 MCP 服务器管理路由：/api/mcp-servers
    - 提取 MCP 工具管理路由：/api/mcp-tools
    - 提取搜索和网页抓取工具函数

    - _Requirements: 3.3_


- [ ] 9. 实现路由模块 - AI 评估
  - [ ] 9.1 实现 routes/ai_eval.py
    - 提取 Qwen 评估路由：/api/qwen/*
    - 提取 DeepSeek 评估路由：/api/deepseek/*
    - 提取联合评估路由：/api/eval/*

    - 提取图表数据生成路由

    - _Requirements: 3.4_

- [ ] 10. Checkpoint - 确保核心路由测试通过
  - Ensure all tests pass, ask the user if questions arise.







- [ ] 11. 实现路由模块 - 学科批改评估
  - [ ] 11.1 实现 routes/subject_grading.py
    - 提取 /api/grading/homework 路由
    - 提取 /api/grading/recognize 路由
    - 提取 /api/grading/evaluate 路由
    - 提取 /api/grading/prompts 路由
    - 提取基准效果管理路由
    - _Requirements: 3.5_

- [ ] 12. 实现路由模块 - 模型推荐
  - [ ] 12.1 实现 routes/model_recommend.py
    - 提取 /api/recommend 路由
    - 提取 /api/model-stats 路由
    - 提取 /api/multi-model-compare 路由
    - 提取模型性能计算函数
    - _Requirements: 3.6_

- [ ] 13. 实现路由模块 - Prompt 优化评测
  - [ ] 13.1 实现 routes/prompt_optimize.py
    - 提取 /prompt-optimize 页面路由
    - 提取 /api/prompt-tasks 路由
    - 提取 /api/prompt-task/<task_id> 路由
    - 提取 /api/prompt-sample 路由
    - 提取 /api/prompt-eval/* 路由
    - 提取 /api/prompt-version 路由
    - _Requirements: 3.7_

- [ ] 14. 实现路由模块 - 数据分析
  - [ ] 14.1 实现 routes/data_analysis.py
    - 提取 /data-analysis 页面路由
    - 提取 /api/analysis/tasks 路由
    - 提取 /api/analysis/tasks/<task_id>/files 路由
    - 提取 /api/analysis/tasks/<task_id>/workflow/* 路由
    - 提取文件解析和报告生成函数
    - _Requirements: 3.8_

- [ ] 15. 实现路由模块 - 批量评估任务
  - [ ] 15.1 实现 routes/batch_evaluation.py
    - 提取 /api/batch/books 路由
    - 提取 /api/batch/homework 路由
    - 提取 /api/batch/tasks 路由
    - 提取 /api/batch/tasks/<task_id>/evaluate 路由
    - 提取评估计算函数
    - _Requirements: 3.8_

- [ ] 16. 实现路由模块 - 数据集管理
  - [ ] 16.1 实现 routes/dataset_manage.py
    - 提取 /dataset-manage 页面路由
    - 提取 /api/dataset/available-homework 路由
    - 提取 /api/dataset/recognize 路由
    - _Requirements: 3.8_

- [ ] 17. 重构主入口文件
  - [ ] 17.1 重构 app.py
    - 移除所有路由定义和辅助函数
    - 保留 Flask 应用初始化
    - 导入并注册所有蓝图
    - 确保文件少于 100 行
    - _Requirements: 4.1, 4.2_

- [ ] 18. Checkpoint - 确保所有路由测试通过
  - Ensure all tests pass, ask the user if questions arise.

- [ ] 19. 编写集成测试
  - [ ]* 19.1 编写 Blueprint 注册完整性测试
    - **Property 1: Blueprint Registration Completeness**
    - **Validates: Requirements 1.1, 3.1-3.8**
  - [ ]* 19.2 编写 API 响应保持测试
    - **Property 2: API Response Preservation**
    - **Validates: Requirements 1.3, 6.2**

- [ ] 20. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
