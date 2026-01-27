# Implementation Plan: AI 智能数据分析

## Overview

本实现计划将 AI 智能数据分析功能分解为可执行的编码任务。系统在批量评估任务完成后自动触发大模型分析，支持多层级粒度分析、根因识别和优化建议生成，并提供自动化任务管理界面。

## Tasks

- [x] 1. 创建数据库表和配置文件
  - [x] 1.1 创建 analysis_reports 表
    - 添加 migrations/add_analysis_reports.sql
    - 包含 report_id, task_id, status, summary, drill_down_data, error_patterns, root_causes, suggestions 等字段
    - _Requirements: 6.3_

  - [x] 1.2 创建 automation_logs 表
    - 添加到同一迁移文件
    - 包含 log_id, task_type, related_id, status, message, duration_seconds 等字段
    - _Requirements: 8.4_

  - [x] 1.3 创建 automation_config.json 配置文件
    - 在项目根目录创建配置文件
    - 包含 ai_analysis, daily_report, stats_snapshot, global 配置
    - _Requirements: 9.1, 9.2, 9.3_

- [x] 2. 实现 AI 分析服务核心逻辑
  - [x] 2.1 创建 services/ai_analysis_service.py
    - 实现 AIAnalysisService 类
    - 实现分析队列管理（_queue, _running, _max_concurrent）
    - 实现 trigger_analysis 方法
    - _Requirements: 1.1, 1.6_

  - [x] 2.2 实现错误样本收集
    - 实现 _collect_error_samples 方法
    - 从批量评估任务中收集所有 AI 评分与期望评分不一致的作业
    - _Requirements: 1.2_

  - [x] 2.3 实现多层级聚合统计
    - 实现 _aggregate_by_hierarchy 方法
    - 按学科→书本→页码→题目四级聚合
    - 计算每级的错误数量和错误率
    - _Requirements: 2.1, 2.3_

  - [ ]* 2.4 编写层级聚合的属性测试
    - **Property 3: 层级聚合正确性**
    - **Property 4: 错误率计算正确性**
    - **Validates: Requirements 2.1, 2.3**

  - [x] 2.5 实现重点关注标记和 Top 5 识别
    - 错误率超过 20% 标记为 is_focus=true
    - 识别错误最集中的 Top 5 位置
    - _Requirements: 2.4, 2.5_

  - [ ]* 2.6 编写阈值判断的属性测试
    - **Property 5: 重点关注标记正确性**
    - **Property 6: Top 5 排序正确性**
    - **Validates: Requirements 2.4, 2.5**

- [x] 3. 实现错误模式识别
  - [x] 3.1 实现错误类型分类
    - 实现 _classify_error_types 方法
    - 分类：识别错误-判断错误、识别正确-判断错误、缺失题目、AI识别幻觉、答案不匹配
    - _Requirements: 3.1_

  - [x] 3.2 实现错误模式统计和排序
    - 统计各类型出现频率
    - 识别 Top 5 错误模式
    - 为每个模式选取最多 3 个示例
    - _Requirements: 3.2, 3.4_

  - [x] 3.3 实现严重程度评级
    - 根据错误数量和影响范围评定 high/medium/low
    - _Requirements: 3.5_

  - [ ]* 3.4 编写错误模式的属性测试
    - **Property 7: 错误类型分类有效性**
    - **Property 8: 样本示例数量限制**
    - **Property 9: 严重程度有效性**
    - **Validates: Requirements 3.1, 3.4, 3.5**

- [x] 4. 实现根因分析
  - [x] 4.1 实现大模型根因分析调用
    - 实现 _analyze_root_causes 方法
    - 调用 DeepSeek V3.2 分析错误样本的根因
    - 构建分析 prompt
    - _Requirements: 4.1_

  - [x] 4.2 实现根因分类和统计
    - 分类：OCR识别问题、评分逻辑问题、标准答案问题、Prompt问题、数据问题
    - 统计各类根因的数量和占比
    - 占比超过 30% 标记为主要问题
    - _Requirements: 4.2, 4.4, 4.5_

  - [x] 4.3 实现证据收集
    - 为每个根因提供具体的错误样本作为证据
    - _Requirements: 4.3_

  - [ ]* 4.4 编写根因分析的属性测试
    - **Property 10: 根因分类有效性**
    - **Property 11: 根因占比总和**
    - **Property 12: 主要问题标记正确性**
    - **Validates: Requirements 4.2, 4.4, 4.5**

- [x] 5. 实现优化建议生成
  - [x] 5.1 实现大模型建议生成调用
    - 实现 _generate_suggestions 方法
    - 基于错误模式和根因生成优化建议
    - 构建建议生成 prompt
    - _Requirements: 5.1_

  - [x] 5.2 实现建议结构化和排序
    - 确保每个建议包含 title, description, priority, expected_effect, related_cause
    - 按优先级排序，最多返回 5 条
    - _Requirements: 5.2, 5.4, 5.5_

  - [ ]* 5.3 编写建议生成的属性测试
    - **Property 13: 建议结构完整性**
    - **Property 14: 建议优先级排序**
    - **Property 15: 建议数量限制**
    - **Validates: Requirements 5.2, 5.4, 5.5**

- [ ] 6. Checkpoint - 确保分析核心功能正常
  - 运行所有属性测试
  - 确保分析流程可以正常执行

- [x] 7. 实现分析 API 路由
  - [x] 7.1 创建 routes/analysis.py
    - 创建 analysis_bp 蓝图
    - 实现 POST /api/analysis/trigger/{task_id}
    - 实现 GET /api/analysis/report/{task_id}
    - 实现 GET /api/analysis/drilldown/{task_id}
    - _Requirements: 6.1, 6.2, 7.1_

  - [x] 7.2 在 app.py 中注册蓝图
    - 导入并注册 analysis_bp
    - _Requirements: 6.1_

- [x] 8. 实现任务完成自动触发
  - [x] 8.1 修改批量评估任务完成逻辑
    - 在 batch_evaluation.py 中，任务状态变为 completed 时调用 trigger_analysis
    - 添加触发延迟配置支持
    - _Requirements: 1.1, 1.3_

  - [ ]* 8.2 编写自动触发的属性测试
    - **Property 1: 任务完成触发分析**
    - **Validates: Requirements 1.1**

- [x] 9. 实现自动化管理服务
  - [x] 9.1 创建 services/automation_service.py
    - 实现 AutomationService 类
    - 实现 get_all_tasks 方法
    - 实现 get_task_config / update_task_config 方法
    - _Requirements: 8.2, 8.3, 9.1_

  - [x] 9.2 实现任务历史和队列状态
    - 实现 get_task_history 方法
    - 实现 get_queue_status 方法
    - _Requirements: 8.4, 10.1_

  - [x] 9.3 实现全局控制
    - 实现 pause_all / resume_all / clear_queue 方法
    - _Requirements: 10.3_

  - [ ]* 9.4 编写配置更新的属性测试
    - **Property 16: 配置即时生效**
    - **Validates: Requirements 9.4**

- [x] 10. 实现自动化管理 API 路由
  - [x] 10.1 创建 routes/automation.py
    - 创建 automation_bp 蓝图
    - 实现 GET /api/automation/tasks
    - 实现 GET/PUT /api/automation/tasks/{task_type}/config
    - 实现 GET /api/automation/queue
    - 实现 POST /api/automation/pause, resume, queue/clear
    - _Requirements: 8.1, 9.1, 10.1, 10.3_

  - [x] 10.2 在 app.py 中注册蓝图
    - 导入并注册 automation_bp
    - _Requirements: 8.1_

- [x] 11. 实现前端分析报告弹窗
  - [x] 11.1 在 index.html 中添加分析报告弹窗 HTML
    - 添加弹窗容器、概览、层级分析、错误模式、根因分析、建议列表模块
    - _Requirements: 6.2, 6.3_

  - [x] 11.2 在 index.js 中实现分析报告相关函数
    - 实现 openAnalysisReportModal 函数
    - 实现 loadAnalysisReport 函数
    - 实现 renderDrillDown 函数（支持下钻）
    - _Requirements: 6.2, 6.3, 6.4_

  - [x] 11.3 在任务列表中添加分析入口
    - 在任务卡片中显示"查看分析"按钮
    - 有高优先级建议时显示提示标记
    - _Requirements: 6.1, 6.4_

- [x] 12. 实现前端自动化管理界面
  - [x] 12.1 在 index.html 中添加自动化管理弹窗 HTML
    - 添加任务列表、配置面板、队列状态模块
    - _Requirements: 8.1, 8.2, 10.1_

  - [x] 12.2 在 index.js 中实现自动化管理相关函数
    - 实现 openAutomationModal 函数
    - 实现 loadAutomationTasks 函数
    - 实现 updateTaskConfig 函数
    - 实现 loadQueueStatus 函数
    - _Requirements: 8.2, 8.3, 9.1, 10.1_

  - [x] 12.3 在看板添加自动化管理入口
    - 在高级工具区域添加"自动化管理"卡片
    - _Requirements: 8.1_

- [x] 13. 添加样式
  - [x] 13.1 在 index.css 中添加分析报告弹窗样式
    - 概览卡片、层级列表、错误模式卡片、根因饼图、建议列表样式
    - _Requirements: 6.2_

  - [x] 13.2 在 index.css 中添加自动化管理弹窗样式
    - 任务列表、配置表单、队列状态样式
    - _Requirements: 8.1_

- [ ] 14. Final Checkpoint - 确保所有功能正常
  - 运行所有测试
  - 部署测试
  - 确保分析流程端到端正常

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号以便追溯
- 检查点任务用于确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
