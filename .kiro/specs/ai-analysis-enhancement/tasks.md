#  mplementation Plan: AI 智能分析功能增强优化

## Overview

本实现计划将 AI 智能分析功能增强优化分解为可执行的编码任务。采用渐进式实现策略：先完成后端核心服务和 API，再实现前端页面和交互功能。

**任务总数**: 约 120 个子任务
**预计工时**: 15-20 人天
**技术栈**: Flask (Python) + MySQL + 原生 CSS/JS + DeepSeek V3.2

## Tasks

### Phase 1: 数据库表结构创建

- [x] 1. 数据库表结构创建
  - [x] 1.1 创建 analysis_results 表（分析结果存储）
    - 字段: result_id, analysis_type, target_id, task_id, analysis_data, data_hash, status, token_usage, error_message, created_at, updated_at
    - 索引: idx_type_target, idx_task_id, idx_data_hash, idx_status
    - _Requirements: 15.1, 15.2_
  - [x] 1.2 创建 error_samples 表（错误样本）
    - 字段: sample_id, task_id, cluster_id, homework_id, book_name, page_num, question_index, subject_id, error_type, ai_answer, expected_answer, base_user, status, llm_insight, note, created_at, updated_at
    - 索引: idx_task_id, idx_cluster_id, idx_status, idx_base_user
    - _Requirements: 11.1, 11.2_
  - [x] 1.3 创建 error_clusters 表（错误聚类）
    - 字段: cluster_id, task_id, cluster_key, cluster_name, cluster_description, root_cause, severity, sample_count, common_fix, pattern_insight, representative_samples, created_at, updated_at
    - 索引: idx_task_id, idx_severity, uk_task_cluster
    - _Requirements: 2.3_
  - [x] 1.4 创建 analysis_anomalies 表（异常检测）
    - 字段: anomaly_id, task_id, anomaly_type, severity, base_user_answer, correct_cases, incorrect_cases, inconsistency_rate, description, suggested_action, status, created_at
    - 索引: idx_task_id, idx_type, idx_severity
    - _Requirements: 9.2_
  - [x] 1.5 创建 llm_call_logs 表（LLM 调用日志）
    - 字段: log_id, task_id, analysis_type, target_id, model, prompt_tokens, completion_tokens, total_tokens, duration_ms, retry_count, status, error_type, error_message, created_at
    - 索引: idx_task_id, idx_status, idx_created_at, idx_error_type
    - _Requirements: 19.7_
  - [x] 1.6 创建 analysis_config 表（分析配置）
    - 字段: config_key, config_value, config_type, description, updated_at
    - 插入默认配置: llm_model, temperature, max_concurrent, request_timeout, max_retries, batch_size, auto_trigger, daily_token_limit, enabled_dimensions
    - _Requirements: 13.1_
  - [x] 1.7 创建数据库迁移脚本
    - 文件: migrations/add_ai_analysis_enhanced_tables.sql
    - 包含所有表的 CREATE TABLE 语句
    - 包含默认数据 INSERT 语句

### Phase 2: 后端核心服务实现

- [x] 2. LLM 服务扩展 (services/llm_service.py)
  - [x] 2.1 实现 call_deepseek_async 异步调用方法
    - 使用 aiohttp 实现异步 HTTP 请求
    - 支持 timeout 参数（默认 60 秒）
    - 支持 temperature 参数（默认 0.2）
    - 返回格式: {success, content, error, tokens, duration}
    - _Requirements: 19.1_
  - [x] 2.2 实现 parallel_call 并行调用方法
    - 使用 asyncio.Semaphore 控制并发数（默认 10）
    - 使用 asyncio.gather 并行执行
    - 单个请求失败不影响其他请求
    - 返回所有结果列表（包含成功和失败）
    - _Requirements: 19.2, 19.5_
  - [x] 2.3 实现重试机制
    - 最大重试次数可配置（默认 3）
    - 指数退避策略（2^attempt 秒）
    - 记录每次重试的日志
    - _Requirements: 19.4_
  - [x] 2.4 实现 token 统计和日志记录
    - 解析 API 响应中的 usage 字段
    - 调用 log_llm_call 记录到数据库
    - _Requirements: 1.5, 19.7_
  - [x] 2.5 实现 parse_json_response 方法
    - 从 LLM 响应中提取 JSON
    - 处理 markdown 代码块包裹的 JSON
    - 错误时返回 None
    - _Requirements: 19.5_

- [x] 3. LLM 分析服务 (services/llm_analysis_service.py) - 新建
  - [x] 3.1 定义 CLUSTER_ANALYSIS_PROMPT 模板
    - 输入: cluster_key, sample_count, error_type, book_name, page_range, samples_json
    - 输出: cluster_name, cluster_description, root_cause, severity, common_fix, pattern_insight
    - _Requirements: 2.3_
  - [x] 3.2 定义 TASK_ANALYSIS_PROMPT 模板
    - 输入: task_id, total_questions, total_errors, error_rate, error_type_distribution, subject_distribution, clusters_summary
    - 输出: task_summary, accuracy_analysis, main_issues, error_distribution, risk_assessment, improvement_priority, actionable_suggestions
    - _Requirements: 3.2_
  - [x] 3.3 定义 DIMENSION_ANALYSIS_PROMPT 模板（学科/书本/题型通用）
    - 输入: dimension_name, name, error_count, total, error_rate, samples_summary
    - 输出: summary, common_error_patterns, specific_issues, improvement_suggestions
    - _Requirements: 4.2, 5.2, 6.2_
  - [x] 3.4 定义 TREND_ANALYSIS_PROMPT 模板
    - 输入: time_range, data_points, accuracy_trend_data
    - 输出: trend_summary, accuracy_trend, error_pattern_evolution, improvement_areas, regression_areas, prediction, recommendations
    - _Requirements: 7.2_
  - [x] 3.5 定义 COMPARISON_ANALYSIS_PROMPT 模板
    - 输入: batch1_info, batch2_info
    - 输出: comparison_summary, accuracy_change, error_pattern_changes, improvement_items, regression_items, root_cause_analysis, recommendations
    - _Requirements: 8.2_
  - [x] 3.6 定义 ANOMALY_ANALYSIS_PROMPT 模板
    - 输入: base_user_answer, occurrence_count, correct_count, incorrect_count, inconsistency_rate, correct_cases, incorrect_cases
    - 输出: description, root_cause, suggested_action, severity
    - _Requirements: 9.3_
  - [x] 3.7 定义 SUGGESTION_GENERATION_PROMPT 模板
    - 输入: task_summary, main_clusters, anomalies
    - 输出: suggestions 数组（最多 5 条）
    - _Requirements: 10.2_
  - [x] 3.8 实现 analyze_cluster 方法
    - 调用 CLUSTER_ANALYSIS_PROMPT
    - 解析 LLM 响应为结构化数据
    - 记录 token 消耗
    - _Requirements: 2.3_
  - [x] 3.9 实现 analyze_task 方法
    - 调用 TASK_ANALYSIS_PROMPT
    - 基于聚类分析结果综合分析
    - _Requirements: 3.2, 3.3_
  - [x] 3.10 实现 analyze_dimension 方法
    - 支持 subject/book/question_type 三种维度
    - 调用 DIMENSION_ANALYSIS_PROMPT
    - _Requirements: 4.2, 5.2, 6.2_
  - [x] 3.11 实现 analyze_trend 方法
    - 调用 TREND_ANALYSIS_PROMPT
    - 支持自定义时间范围
    - _Requirements: 7.2, 7.3_
  - [x] 3.12 实现 compare_batches 方法
    - 调用 COMPARISON_ANALYSIS_PROMPT
    - 对比两个批次的数据
    - _Requirements: 8.2_
  - [x] 3.13 实现 generate_suggestions 方法
    - 调用 SUGGESTION_GENERATION_PROMPT
    - 最多返回 5 条建议
    - 按优先级排序
    - _Requirements: 10.2, 10.3, 10.4_
  - [x] 3.14 实现 parallel_analyze 方法
    - 并行执行多个分析任务
    - 使用 LLMService.parallel_call
    - 汇总所有结果
    - _Requirements: 19.3_

- [x] 4. AI 分析服务增强 (services/ai_analysis_service.py)
  - [x] 4.1 实现分析队列管理
    - 定义 _queue 列表（任务队列）
    - 定义 _running 字典（运行中任务）
    - 定义 _lock 线程锁
    - 支持优先级（high/medium/low）
    - _Requirements: 16.2_
  - [x] 4.2 实现 trigger_analysis 方法
    - 将任务加入队列
    - 返回 job_id 和队列位置
    - 启动后台处理线程
    - _Requirements: 16.1_
  - [x] 4.3 实现 get_quick_stats 方法
    - 计算总错误数、错误率
    - 计算错误类型分布
    - 计算学科分布、书本分布
    - 生成初步聚类（按 error_type + book + page_range）
    - 响应时间 < 100ms
    - _Requirements: 17.2, 17.4_
  - [x] 4.4 实现 get_cached_analysis 方法
    - 计算源数据哈希值
    - 查询 analysis_results 表
    - 比较 data_hash 判断缓存有效性
    - 返回缓存结果或触发重新分析
    - _Requirements: 15.3, 15.4_
  - [x] 4.5 实现 detect_anomalies 方法
    - 检测批改不一致（同 base_user 不同结果）
    - 检测识别不稳定
    - 检测连续错误
    - 检测批量缺失
    - _Requirements: 9.1_
  - [x] 4.6 实现 get_analysis_queue_status 方法
    - 返回等待中任务数
    - 返回运行中任务列表（含进度）
    - 返回最近完成/失败的任务
    - _Requirements: 16.3_
  - [x] 4.7 实现 cancel_analysis 方法
    - 从队列中移除任务
    - 返回取消结果
    - _Requirements: 16.6_
  - [x] 4.8 实现 _process_queue 后台处理方法
    - 从队列取出任务
    - 控制并发数（最大 10）
    - 更新进度状态
    - _Requirements: 16.2_
  - [x] 4.9 实现 _run_full_analysis 完整分析流程
    - 步骤1: 快速本地统计
    - 步骤2: 初步聚类
    - 步骤3: 并行 LLM 聚类分析
    - 步骤4: 任务级别分析
    - 步骤5: 维度分析（学科/书本/题型）
    - 步骤6: 异常检测
    - 步骤7: 生成优化建议
    - 步骤8: 保存结果到数据库
    - _Requirements: 1, 2, 3, 4, 5, 6, 9, 10_
  - [x] 4.10 实现数据哈希计算
    - 对源数据进行 MD5/SHA256 哈希
    - 用于缓存判断
    - _Requirements: 15.3_
  - [x] 4.11 实现进度追踪
    - 更新 _running 中的 progress 和 step
    - 支持前端轮询获取进度
    - _Requirements: 16.3_

- [x] 5. Checkpoint - 核心服务测试
  - 测试 LLM 异步调用功能
  - 测试 LLM 并行调用功能（10 并发）
  - 测试重试机制
  - 测试快速统计响应时间（< 100ms）
  - 测试缓存机制
  - 测试分析队列管理
  - 如有问题请询问用户

### Phase 3: 后端 API 路由实现

- [x] 6. 分析触发与状态 API (routes/analysis.py)
  - [x] 6.1 实现 POST /api/analysis/trigger/{task_id}
    - 参数: priority (high/medium/low)
    - 返回: queued, job_id, position, message
    - _Requirements: 16.1_
  - [x] 6.2 实现 GET /api/analysis/queue
    - 返回: waiting, running, recent_completed, recent_failed
    - _Requirements: 16.3_
  - [x] 6.3 实现 DELETE /api/analysis/queue/{job_id}
    - 取消排队中的任务
    - 返回: success, message
    - _Requirements: 16.6_

- [x] 7. 分析结果 API
  - [x] 7.1 实现 GET /api/analysis/task/{task_id}
    - 返回: quick_stats, llm_analysis, analysis_status, updated_at
    - quick_stats 立即返回，llm_analysis 可能为 null
    - _Requirements: 3, 14.2, 17.3_
  - [x] 7.2 实现 GET /api/analysis/clusters
    - 参数: task_id, page, page_size
    - 返回: quick_stats.clusters, llm_analysis.clusters, top_5_clusters
    - _Requirements: 2, 14.1_
  - [x] 7.3 实现 GET /api/analysis/clusters/{cluster_id}
    - 返回: 聚类详情 + 样本列表
    - _Requirements: 2.3, 14.1_
  - [x] 7.4 实现 GET /api/analysis/samples
    - 参数: task_id, status, error_type, subject, book_id, severity, page, page_size, sort_by, sort_order
    - 返回: items, total, page, page_size
    - _Requirements: 11.2, 14.1, 14.4_
  - [x] 7.5 实现 GET /api/analysis/samples/{sample_id}
    - 返回: 样本详情 + LLM 分析结果 + 所属聚类
    - _Requirements: 1.2, 12.1_

- [x] 8. 维度分析 API
  - [x] 8.1 实现 GET /api/analysis/subject
    - 参数: task_id
    - 返回: quick_stats.subjects, llm_analysis.subjects
    - _Requirements: 4, 14.1_
  - [x] 8.2 实现 GET /api/analysis/subject/{subject_id}
    - 返回: 学科详情 + 书本列表
    - _Requirements: 4.3_
  - [x] 8.3 实现 GET /api/analysis/book
    - 参数: task_id, subject_id
    - 返回: quick_stats.books, llm_analysis.books
    - _Requirements: 5, 14.1_
  - [x] 8.4 实现 GET /api/analysis/book/{book_id}
    - 返回: 书本详情 + 页码分布
    - _Requirements: 5.3_
  - [x] 8.5 实现 GET /api/analysis/question-type
    - 参数: task_id
    - 返回: quick_stats.question_types, llm_analysis.question_types
    - _Requirements: 6, 14.1_
  - [x] 8.6 实现 GET /api/analysis/question-type/{type}
    - 返回: 题型详情
    - _Requirements: 6.3_
  - [x] 8.7 实现 GET /api/analysis/trend
    - 参数: task_ids, time_range (7d/30d/custom)
    - 返回: quick_stats.trend_data, llm_analysis.trend
    - _Requirements: 7, 14.1_
  - [x] 8.8 实现 GET /api/analysis/compare
    - 参数: task_id_1, task_id_2
    - 返回: quick_stats.comparison, llm_analysis.comparison
    - _Requirements: 8, 14.1_

- [x] 9. 异常检测和建议 API
  - [x] 9.1 实现 GET /api/analysis/anomalies
    - 参数: task_id
    - 返回: anomalies 列表, summary (critical/high/medium 数量)
    - _Requirements: 9, 14.1_
  - [x] 9.2 实现 GET /api/analysis/suggestions
    - 参数: task_id
    - 返回: suggestions 列表（最多 5 条）
    - _Requirements: 10, 14.1_

- [x] 10. 样本管理 API
  - [x] 10.1 实现 PUT /api/analysis/samples/{sample_id}/status
    - 参数: status, note
    - 更新样本状态和备注
    - 记录状态变更历史
    - _Requirements: 11.3_
  - [x] 10.2 实现 PUT /api/analysis/samples/batch-status
    - 参数: sample_ids, status
    - 批量更新样本状态
    - _Requirements: 11.3_
  - [x] 10.3 实现 POST /api/analysis/samples/{sample_id}/reanalyze
    - 对单个样本重新调用 LLM 分析
    - _Requirements: 1.4_

- [x] 11. 配置管理 API
  - [x] 11.1 实现 GET /api/analysis/config
    - 返回所有配置项
    - 返回成本统计
    - _Requirements: 13.1, 13.2_
  - [x] 11.2 实现 PUT /api/analysis/config
    - 更新配置项
    - 验证配置值有效性
    - _Requirements: 13.1_
  - [x] 11.3 实现 GET /api/analysis/cost-stats
    - 返回今日/本周/本月 token 消耗
    - 返回 API 调用次数
    - 返回成本估算
    - 返回限制状态
    - _Requirements: 13.2, 13.3_

- [x] 12. 高级可视化数据 API
  - [x] 12.1 实现 GET /api/analysis/chart/sankey
    - 参数: task_id
    - 返回: nodes (错误类型/根因/建议), links (流转关系)
    - _Requirements: 20.1.3_
  - [x] 12.2 实现 GET /api/analysis/chart/heatmap
    - 参数: task_id, book_id
    - 返回: x_axis (题目), y_axis (页码), data (错误数)
    - _Requirements: 20.1.4_
  - [x] 12.3 实现 GET /api/analysis/chart/radar
    - 参数: task_id, dimension (subject/question_type/book)
    - 返回: indicators, series (当前批次/上一批次)
    - _Requirements: 20.1.5_

- [x] 13. 搜索筛选 API
  - [x] 13.1 实现 SearchQueryParser 类
    - 解析高级搜索语法 (book:xxx AND status:xxx)
    - 支持 AND/OR 逻辑
    - 支持括号分组
    - 支持范围搜索 (page:10-20)
    - 生成 SQL WHERE 子句
    - _Requirements: 21.1.1, 21.1.2_
  - [x] 13.2 实现 GET /api/analysis/samples/search
    - 参数: q (搜索语法), page, page_size
    - 返回: items, total, query_parsed, highlights
    - _Requirements: 21.1_
  - [x] 13.3 实现 GET /api/analysis/filter-presets
    - 返回: system_presets, user_presets
    - _Requirements: 21.3.2_
  - [x] 13.4 实现 POST /api/analysis/filter-presets
    - 参数: name, query
    - 保存用户筛选预设
    - _Requirements: 21.3.1_
  - [x] 13.5 实现 DELETE /api/analysis/filter-presets/{preset_id}
    - 删除用户预设
    - _Requirements: 21.3.2_

- [x] 14. 导出报告 API
  - [x] 14.1 实现 POST /api/analysis/export
    - 参数: task_id, format (pdf/excel), sections, filters
    - 返回: export_id, status
    - 后台生成报告
    - _Requirements: 12.4_
  - [x] 14.2 实现 GET /api/analysis/export/{export_id}
    - 返回: status, download_url, file_name, file_size, expires_at
    - _Requirements: 12.4_
  - [x] 14.3 实现 GET /api/analysis/export/download/{export_id}
    - 返回文件流
    - _Requirements: 12.4_
  - [x] 14.4 实现 PDF 报告生成器
    - 使用 reportlab 或 weasyprint
    - 包含执行摘要、图表、聚类、建议
    - _Requirements: 12.4_
  - [x] 14.5 实现 Excel 报告生成器
    - 使用 openpyxl
    - 包含原始数据和分析结果明细
    - _Requirements: 12.4_

- [x] 15. 错误日志 API
  - [x] 15.1 实现 GET /api/analysis/logs
    - 参数: days, type (timeout/api_error/parse_error)
    - 返回: logs 列表, summary
    - _Requirements: 19.7_

- [x] 16. Checkpoint - API 测试
  - 测试所有 API 端点响应格式
  - 测试分页和筛选功能
  - 测试搜索语法解析
  - 测试导出功能
  - 如有问题请询问用户

### Phase 4: 前端页面实现 - 分析报告页

- [x] 17. 分析报告页面模板 (templates/analysis-report.html)
  - [x] 17.1 创建页面基础结构
  - [x] 17.2 实现概览卡片区
  - [x] 17.3 实现执行摘要区
  - [x] 17.4 实现图表区
  - [x] 17.5 实现维度分析 Tab 区
  - [x] 17.6 实现 Top 5 聚类列表
  - [x] 17.7 实现异常提醒区
  - [x] 17.8 实现优化建议列表

- [x] 18. 分析报告页面样式 (static/css/analysis-report.css)
  - [x] 18.1 定义 CSS 变量（遵循 ui-style.md）
  - [x] 18.2 实现概览卡片样式
  - [x] 18.3 实现图表区样式
  - [x] 18.4 实现 Tab 切换样式
  - [x] 18.5 实现聚类卡片样式
  - [x] 18.6 实现骨架屏样式
  - [x] 18.7 实现响应式布局

- [x] 19. 分析报告页面脚本 (static/js/analysis-report.js)
  - [x] 19.1 实现数据加载逻辑
  - [x] 19.2 实现概览卡片渲染
  - [x] 19.3 实现图表初始化
  - [x] 19.4 实现图表切换功能
  - [x] 19.5 实现桑基图渲染
  - [x] 19.6 实现热力图渲染
  - [x] 19.7 实现雷达图渲染
    - 鼠标悬停显示数值
    - _Requirements: 20.1.5_
  - [x] 19.8 实现维度 Tab 切换
    - 点击 Tab 加载对应维度数据
    - 渲染维度列表
    - _Requirements: 12.2_
  - [x] 19.9 实现学科维度渲染
    - 调用 /api/analysis/subject
    - 渲染学科卡片列表
    - 点击下钻到书本
    - _Requirements: 12.3.1_
  - [x] 19.10 实现书本维度渲染
    - 调用 /api/analysis/book
    - 渲染书本卡片列表
    - 显示页码分布热力图
    - _Requirements: 12.3.2_
  - [x] 19.11 实现题型维度渲染
    - 调用 /api/analysis/question-type
    - 渲染题型卡片列表
    - _Requirements: 12.3.3_
  - [x] 19.12 实现时间趋势渲染
    - 调用 /api/analysis/trend
    - 渲染折线图
    - 时间范围选择器
    - _Requirements: 12.3.4_
  - [x] 19.13 实现批次对比渲染
    - 批次选择器
    - 调用 /api/analysis/compare
    - 渲染对比表格和图表
    - _Requirements: 12.3.5_
  - [x] 19.14 实现进度轮询
    - 使用 AnalysisProgressPoller 类
    - 轮询 /api/analysis/queue
    - 更新进度条和步骤文字
    - 分析完成后自动刷新
    - _Requirements: 16.4, 16.5_
  - [x] 19.15 实现刷新分析按钮
    - 点击触发 POST /api/analysis/trigger/{task_id}
    - 显示确认弹窗
    - 开始进度轮询
    - _Requirements: 12.2_
  - [x] 19.16 实现导出按钮
    - 点击显示导出选项（PDF/Excel）
    - 调用 POST /api/analysis/export
    - 轮询导出状态
    - 完成后下载文件
    - _Requirements: 12.4_

### Phase 5: 前端页面实现 - 错误样本库（三栏布局）

- [x] 20. 错误样本库页面模板 (templates/error-samples.html)
  - [x] 20.1 创建三栏布局结构
    - 左栏（列表栏）: 300px 宽度
    - 中栏（详情栏）: 自适应宽度
    - 右栏（分析栏）: 350px 宽度，可折叠
    - 可调整宽度的分隔条
    - _Requirements: 20.2.1_
  - [x] 20.2 实现左栏列表区
    - 搜索框
    - 快速筛选按钮（待处理/全部/已修复）
    - 样本卡片列表
    - 加载更多按钮
    - 总数显示
    - _Requirements: 20.2.2_
  - [x] 20.3 实现中栏详情区
    - 基本信息区（作业ID、书本、页码、题目）
    - 答案对比区（标准答案、学生答案、AI识别、差异高亮）
    - 作业图片区（可放大）
    - 状态操作区（状态按钮、备注输入）
    - _Requirements: 20.2.3, 12.1.1_
  - [x] 20.4 实现右栏分析区
    - LLM 分析结果（折叠面板）
    - 所属聚类信息（点击跳转）
    - 相似样本推荐
    - 折叠/展开按钮
    - _Requirements: 20.2.4_
  - [x] 20.5 实现批量操作区
    - 批量操作下拉菜单
    - 导出按钮
    - 折叠右栏按钮
    - _Requirements: 11.3_

- [x] 21. 错误样本库页面样式 (static/css/error-samples.css)
  - [x] 21.1 实现三栏布局样式
    - flexbox 布局
    - 分隔条拖拽样式
    - 右栏折叠动画
    - _Requirements: 20.2_
  - [x] 21.2 实现样本卡片样式
    - 卡片布局
    - 状态标签样式
    - 选中高亮样式
    - 悬停效果
    - _Requirements: 20.2.2_
  - [x] 21.3 实现答案对比样式
    - 对比表格布局
    - 差异高亮样式（红色背景）
    - _Requirements: 12.1.1_
  - [x] 21.4 实现折叠面板样式
    - 折叠/展开图标
    - 展开动画
    - 内容区样式
    - _Requirements: 20.3_
  - [x] 21.5 实现图片预览样式
    - 缩略图样式
    - 放大弹窗样式
    - _Requirements: 12.1.1_

- [x] 22. 错误样本库页面脚本 (static/js/error-samples.js)
  - [x] 22.1 实现虚拟滚动 VirtualScroller 类
    - 计算可见范围
    - 只渲染可见项 + 缓冲区
    - 滚动时动态替换 DOM
    - 支持 1000+ 条数据
    - _Requirements: 18.1_
  - [x] 22.2 实现样本列表加载
    - 调用 /api/analysis/samples
    - 渲染样本卡片
    - 分页加载（滚动到底部加载更多）
    - _Requirements: 18.2_
  - [x] 22.3 实现样本选择和详情加载
    - 点击样本卡片选中
    - 调用 /api/analysis/samples/{sample_id}
    - 渲染详情区
    - _Requirements: 20.2_
  - [x] 22.4 实现键盘导航
    - ↑↓ 键切换选中样本
    - Enter 键查看详情
    - _Requirements: 20.2.2_
  - [x] 22.5 实现状态更新操作
    - 点击状态按钮
    - 调用 PUT /api/analysis/samples/{sample_id}/status
    - 显示成功动画
    - 更新列表状态
    - _Requirements: 11.3, 22.1_
  - [x] 22.6 实现批量操作
    - 多选样本
    - 批量标记状态
    - 调用 PUT /api/analysis/samples/batch-status
    - 显示确认弹窗
    - _Requirements: 11.3, 22.3_
  - [x] 22.7 实现右栏折叠/展开
    - 点击按钮切换
    - 动画过渡
    - 记住折叠状态
    - _Requirements: 20.2.4_
  - [x] 22.8 实现分隔条拖拽
    - 鼠标拖拽调整宽度
    - 最小/最大宽度限制
    - _Requirements: 20.2.1_
  - [x] 22.9 实现图片放大预览
    - 点击图片显示弹窗
    - 支持缩放和拖拽
    - _Requirements: 12.1.1_
  - [x] 22.10 实现 Tooltip 预览
    - 鼠标悬停 500ms 显示预览卡片
    - 预览内容：题目、答案对比、错误类型、LLM 摘要
    - _Requirements: 20.4.1_

### Phase 6: 前端页面实现 - 聚类详情页

- [x] 23. 聚类详情页面模板 (templates/cluster-detail.html)
  - [x] 23.1 创建页面结构
    - 返回按钮
    - 聚类概览区
    - LLM 分析结果区
    - 代表性样本区
    - 样本列表区
    - _Requirements: 12.2_
  - [x] 23.2 实现聚类概览区
    - 聚类名称（LLM 生成）
    - 聚类描述
    - 严重程度标签
    - 样本数量
    - _Requirements: 12.2.1_
  - [x] 23.3 实现 LLM 分析结果区
    - 根因分析（折叠面板）
    - 模式洞察（折叠面板）
    - 通用修复建议（折叠面板）
    - _Requirements: 12.2.1_
  - [x] 23.4 实现代表性样本区
    - 3 个代表性样本卡片
    - 显示标准答案 vs AI 识别
    - 查看详情按钮
    - _Requirements: 12.2.1_
  - [x] 23.5 实现样本列表区
    - 批量标记按钮
    - 导出按钮
    - 搜索框
    - 样本表格（分页）
    - _Requirements: 12.2.2_

- [x] 24. 聚类详情页面样式和脚本
  - [x] 24.1 创建样式文件 (static/css/cluster-detail.css)
    - 概览区样式
    - 折叠面板样式
    - 代表性样本卡片样式
    - 表格样式
    - _Requirements: 12.2_
  - [x] 24.2 创建脚本文件 (static/js/cluster-detail.js)
    - 加载聚类详情
    - 渲染各区域
    - 折叠面板交互
    - 样本列表分页
    - 批量操作
    - _Requirements: 12.2_

### Phase 7: 前端通用组件实现

- [x] 25. Toast 通知组件 (static/js/components/toast.js)
  - [x] 25.1 实现 ToastManager 类
    - createContainer 方法
    - show 方法（message, type, duration）
    - remove 方法
    - success/warning/error/info 快捷方法
    - _Requirements: 22.5_
  - [x] 25.2 实现 Toast 样式
    - 右上角定位
    - 类型颜色（成功绿/警告橙/错误红/信息蓝）
    - 滑入滑出动画
    - 堆叠显示
    - _Requirements: 22.5.1, 22.5.2_

- [x] 26. 骨架屏组件 (static/js/components/skeleton.js)
  - [x] 26.1 实现骨架屏模板
    - skeleton-card 模板
    - skeleton-text 模板（short/medium/long）
    - skeleton-chart 模板
    - skeleton-list 模板
    - _Requirements: 22.4.1_
  - [x] 26.2 实现骨架屏显示/隐藏方法
    - showSkeleton(containerId, type)
    - hideSkeleton(containerId)
    - _Requirements: 22.4.1_

- [x] 27. 进度条组件 (static/js/components/progress.js)
  - [x] 27.1 实现环形进度条
    - SVG 实现
    - 百分比显示
    - 动画过渡
    - _Requirements: 22.4.2_
  - [x] 27.2 实现进度状态显示
    - 当前步骤文字
    - 预计剩余时间
    - 取消按钮
    - _Requirements: 22.4.2_

- [x] 28. 确认弹窗组件 (static/js/components/confirm.js)
  - [x] 28.1 实现 ConfirmDialog 类
    - show 方法（title, message, onConfirm, onCancel）
    - 操作描述
    - 影响范围显示
    - 确认/取消按钮
    - "不再提示"复选框
    - _Requirements: 22.3_
  - [x] 28.2 实现弹窗样式
    - 遮罩层
    - 弹窗居中
    - 圆角 16px
    - 动画效果
    - _Requirements: 22.3_

- [x] 29. 空状态组件 (static/js/components/empty-state.js)
  - [x] 29.1 实现空状态模板
    - 无错误样本状态
    - 搜索无结果状态
    - 筛选无结果状态
    - 分析未完成状态
    - 分析失败状态
    - _Requirements: 22.2_
  - [x] 29.2 实现空状态样式
    - 简洁线条图标
    - 提示文案
    - 操作按钮
    - _Requirements: 22.2_

- [x] 30. 搜索筛选组件 (static/js/components/search-filter.js)
  - [x] 30.1 实现高级搜索框
    - 输入框
    - 语法提示下拉
    - 搜索历史下拉
    - 清除按钮
    - _Requirements: 21.1_
  - [x] 30.2 实现搜索历史管理
    - 记录最近 10 条搜索
    - localStorage 持久化
    - 点击复用
    - 删除单条/清空
    - _Requirements: 21.2_
  - [x] 30.3 实现筛选预设选择器
    - 下拉菜单
    - 系统预设 + 用户预设
    - 保存当前筛选按钮
    - 删除预设
    - _Requirements: 21.3_
  - [x] 30.4 实现关键词高亮
    - 匹配文字黄色背景
    - 多关键词同时高亮
    - _Requirements: 21.1.3_
  - [x] 30.5 实现实时搜索
    - 输入防抖 300ms
    - 显示搜索中状态
    - 结果数量实时更新
    - _Requirements: 21.4_

- [x] 31. 性能优化工具 (static/js/utils/performance.js)
  - [x] 31.1 实现防抖函数 debounce
    - 参数: fn, delay
    - 默认 delay 300ms
    - _Requirements: 18.3_
  - [x] 31.2 实现节流函数 throttle
    - 参数: fn, interval
    - 默认 interval 16ms (60fps)
    - _Requirements: 18.3_
  - [x] 31.3 实现懒加载类 LazyLoader
    - 使用 IntersectionObserver
    - 图片懒加载
    - 图表懒加载
    - _Requirements: 18.2_
  - [x] 31.4 实现分析进度轮询类 AnalysisProgressPoller
    - 构造函数（taskId, options）
    - start/stop 方法
    - onProgress/onComplete/onError 回调
    - 预计剩余时间计算
    - _Requirements: 16.4_

- [x] 32. Checkpoint - 前端功能测试
  - 测试所有页面加载和渲染
  - 测试图表切换和渲染
  - 测试三栏布局和拖拽
  - 测试虚拟滚动（1000+ 条数据）
  - 测试搜索筛选功能
  - 测试 Toast 通知
  - 测试骨架屏显示
  - 测试进度轮询
  - 如有问题请询问用户

### Phase 8: 集成与优化

- [x] 33. 路由注册和页面入口
  - [x] 33.1 在 routes/__init__.py 中注册分析蓝图
    - 导入 analysis_bp
    - 注册蓝图
    - _Requirements: 14_
  - [x] 33.2 添加页面路由
    - GET /analysis-report/{task_id} - 分析报告页
    - GET /error-samples - 错误样本库页
    - GET /cluster-detail/{cluster_id} - 聚类详情页
    - _Requirements: 14_

- [x] 34. 集成批量评估页面
  - [x] 34.1 在批量评估完成后添加"查看分析"按钮
    - 修改 batch-evaluation.html
    - 添加按钮跳转到分析报告页
    - _Requirements: 3.4_
  - [x] 34.2 添加分析状态指示器
    - 显示分析状态（未分析/分析中/已完成）
    - 点击触发分析
    - _Requirements: 3.4_

- [x] 35. 集成测试看板
  - [x] 35.1 在高级分析工具中添加入口
    - 错误样本库入口
    - 错误聚类入口
    - 异常检测入口
    - 优化建议入口
    - _Requirements: 14.3_
  - [x] 35.2 实现数据联动
    - 从看板跳转到分析页面
    - 传递筛选参数
    - _Requirements: 14.3_

- [x] 36. 自动化配置集成
  - [x] 36.1 在自动化面板添加分析配置
    - LLM 模型选择
    - 温度参数
    - 最大并发数
    - 请求超时
    - 自动触发开关
    - 每日 token 限制
    - 分析维度开关
    - _Requirements: 13.1_
  - [x] 36.2 显示成本统计
    - 今日/本周/本月 token 消耗
    - API 调用次数
    - 成本估算
    - _Requirements: 13.2_

### Phase 9: 测试

- [x] 37. 单元测试
  - [x] 37.1 创建 tests/test_ai_analysis_enhanced.py
    - 测试 get_quick_stats 响应时间 < 100ms
    - 测试 get_quick_stats 数据准确性
    - 测试聚类分配完整性
    - 测试聚类样本数一致性
    - _Requirements: Property 1, 2, 6_
  - [x] 37.2 测试 LLM 服务
    - 测试异步调用
    - 测试并行调用
    - 测试重试机制
    - 测试错误隔离
    - _Requirements: Property 4_
  - [x] 37.3 测试缓存机制
    - 测试缓存命中
    - 测试缓存失效
    - 测试数据哈希一致性
    - _Requirements: Property 3_
  - [x] 37.4 测试异常检测
    - 测试不一致率计算
    - 测试异常识别
    - _Requirements: Property 5_
  - [x] 37.5 测试分析队列
    - 测试任务排队
    - 测试优先级顺序
    - 测试并发控制
    - _Requirements: Property 7_

- [x] 38. 属性测试
  - [x] 38.1 创建 tests/test_ai_analysis_properties.py
    - 测试聚类完整性属性
    - 测试不一致率计算属性
    - 测试 Top 5 聚类排序属性
    - 测试样本状态有效性属性
    - 测试建议数量限制属性
    - _Requirements: Property 1-10_

- [x] 39. 集成测试
  - [x] 39.1 测试完整分析流程
    - 触发分析 → 快速统计 → LLM 分析 → 结果展示
    - _Requirements: 1-10_
  - [x] 39.2 测试并行 LLM 调用
    - 多聚类并行分析
    - 错误隔离验证
    - _Requirements: 19_
  - [x] 39.3 测试缓存命中
    - 首次请求 → 缓存 → 二次请求
    - _Requirements: 15_

- [x] 40. 前端测试
  - [x] 40.1 测试快速统计展示
    - 页面加载时间 < 500ms
    - 骨架屏显示
    - _Requirements: 17, 22_
  - [x] 40.2 测试图表切换
    - 饼图/桑基图/热力图/雷达图切换
    - _Requirements: 20_
  - [x] 40.3 测试三栏布局
    - 布局正确性
    - 右栏折叠
    - _Requirements: 20.2_
  - [x] 40.4 测试搜索功能
    - 高级搜索语法
    - 搜索历史
    - 筛选预设
    - _Requirements: 21_

- [x] 41. Final Checkpoint - 完整功能验证
  - 端到端测试完整分析流程
  - 验证所有 API 响应格式符合设计
  - 验证前端交互和状态反馈
  - 验证性能指标（快速统计 < 100ms）
  - 验证 LLM 并行调用（10 并发）
  - 验证缓存机制
  - 验证成本控制
  - 如有问题请询问用户

## Notes

- 任务按依赖顺序排列：数据库 → 后端服务 → API → 前端页面 → 集成 → 测试
- 每个 Phase 结束有 Checkpoint 用于验证阶段性成果
- 前端实现遵循 ui-style.md 规范（浅色主题，黑白简洁风格）
- 所有 LLM 分析使用 DeepSeek V3.2 模型
- 并行调用最大并发数默认为 10
- 快速本地统计响应时间要求 < 100ms
- 虚拟滚动支持 1000+ 条数据流畅滚动

## Dependencies

```
Phase 1 (数据库) 
    ↓
Phase 2 (后端服务) 
    ↓
Phase 3 (API) 
    ↓
Phase 4-7 (前端页面和组件) [可并行]
    ↓
Phase 8 (集成)
    ↓
Phase 9 (测试)
```

## Estimated Timeline

| Phase | 任务数 | 预计工时 |
|-------|--------|----------|
| Phase 1: 数据库 | 7 | 0.5 天 |
| Phase 2: 后端服务 | 25 | 3 天 |
| Phase 3: API | 30 | 3 天 |
| Phase 4: 分析报告页 | 25 | 2 天 |
| Phase 5: 错误样本库 | 15 | 2 天 |
| Phase 6: 聚类详情页 | 7 | 1 天 |
| Phase 7: 通用组件 | 20 | 2 天 |
| Phase 8: 集成 | 8 | 1 天 |
| Phase 9: 测试 | 15 | 2 天 |
| **总计** | **~150** | **16-17 天** |