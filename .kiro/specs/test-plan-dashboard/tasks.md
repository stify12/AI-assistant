# 测试计划自动化工作流 - 实现任务

## 阶段一：数据库与基础 API（2天）

- [x] 1. 数据库表结构修改
  - [x] 1.1 修改 test_plans 表，添加工作流相关字段（task_keyword, keyword_match_type, matched_publish_ids, workflow_status, auto_execute, grading_threshold）
  - [x] 1.2 更新 database_schema.sql 文件
  - [x] 1.3 在服务器执行 ALTER TABLE 语句

- [x] 2. 测试计划 CRUD API
  - [x] 2.1 创建 routes/test_plans.py 蓝图文件
  - [x] 2.2 实现 POST /api/test-plans 创建测试计划
  - [x] 2.3 实现 GET /api/test-plans 获取测试计划列表
  - [x] 2.4 实现 GET /api/test-plans/{plan_id} 获取测试计划详情
  - [x] 2.5 实现 PUT /api/test-plans/{plan_id} 更新测试计划
  - [x] 2.6 实现 DELETE /api/test-plans/{plan_id} 删除测试计划
  - [x] 2.7 在 app.py 注册蓝图

- [x] 3. 关键字匹配预览 API
  - [x] 3.1 实现 POST /api/test-plans/preview-match 预览匹配结果
  - [x] 3.2 实现 parse_page_region() 页码解析函数
  - [x] 3.3 实现三种匹配模式（精确/模糊/正则）
  - [x] 3.4 返回匹配到的 publish 列表及统计信息


## 阶段二：工作流核心逻辑（3天）

- [x] 4. 作业匹配服务
  - [x] 4.1 创建 services/test_plan_service.py 服务文件
  - [x] 4.2 实现 match_homework_publish() 作业匹配逻辑
  - [x] 4.3 实现 check_page_match() 页码匹配检查
  - [x] 4.4 实现 POST /api/test-plans/{plan_id}/match-homework 执行匹配
  - [x] 4.5 保存匹配结果到 matched_publish_ids 字段

- [x] 5. 批改状态检测
  - [x] 5.1 实现 check_grading_status() 批改状态检查函数
  - [x] 5.2 实现 GET /api/test-plans/{plan_id}/grading-status 获取批改状态
  - [x] 5.3 实现 POST /api/test-plans/{plan_id}/refresh-grading 刷新批改状态
  - [x] 5.4 更新 workflow_status.homework_match 状态

- [x] 6. 工作流状态管理
  - [x] 6.1 实现 update_workflow_status() 状态更新函数
  - [x] 6.2 实现 get_workflow_progress() 获取工作流进度
  - [x] 6.3 实现状态流转逻辑（not_started → in_progress → completed）

## 阶段三：自动评估与报告（2天）

- [x] 7. 批量评估集成
  - [x] 7.1 实现 get_graded_homework_ids() 获取已批改作业ID
  - [x] 7.2 实现 create_batch_task_from_plan() 从计划创建批量任务
  - [x] 7.3 实现 POST /api/test-plans/{plan_id}/start-evaluation 开始评估
  - [x] 7.4 复用现有批量评估逻辑执行评估
  - [x] 7.5 更新 workflow_status.evaluation 状态

- [x] 8. 报告生成
  - [x] 8.1 实现 generate_test_report() 生成测试报告
  - [x] 8.2 实现 POST /api/test-plans/{plan_id}/generate-report 生成报告
  - [x] 8.3 汇总评估结果（准确率、错误分布、题型统计）
  - [x] 8.4 更新 workflow_status.report 状态

- [x] 9. 一键执行工作流
  - [x] 9.1 实现 POST /api/test-plans/{plan_id}/execute 一键执行
  - [x] 9.2 按顺序执行：匹配 → 等待批改 → 评估 → 报告
  - [x] 9.3 支持自动执行模式（auto_execute=true）


## 阶段四：前端 UI 实现（2天）

- [x] 10. 创建测试计划表单
  - [x] 10.1 在 index.html 添加创建测试计划弹窗
  - [x] 10.2 实现表单字段：计划名称、任务关键字、匹配方式、数据集选择
  - [x] 10.3 实现预览匹配结果功能
  - [x] 10.4 实现高级设置展开/收起
  - [x] 10.5 实现表单提交和验证

- [x] 11. 测试计划卡片组件
  - [x] 11.1 实现测试计划卡片 HTML 结构
  - [x] 11.2 实现工作流进度条（四步骤可视化）
  - [x] 11.3 实现统计概览区（作业数、批改率、准确率、耗时）
  - [x] 11.4 实现步骤详情展开/收起（默认收起）
  - [x] 11.5 实现状态标识样式（已完成/进行中/待开始/失败）

- [x] 12. 测试计划列表页
  - [x] 12.1 在 index.html 添加测试计划列表区域
  - [x] 12.2 实现计划列表加载和渲染
  - [x] 12.3 实现编辑/删除操作
  - [x] 12.4 实现刷新状态按钮
  - [x] 12.5 实现开始执行按钮

- [x] 13. 前端 JavaScript 逻辑
  - [x] 13.1 在 index.js 添加 TestPlanAPI 模块
  - [x] 13.2 实现 loadTestPlans() 加载测试计划列表
  - [x] 13.3 实现 createTestPlan() 创建测试计划
  - [x] 13.4 实现 previewMatch() 预览匹配结果
  - [x] 13.5 实现 refreshGradingStatus() 刷新批改状态
  - [x] 13.6 实现 startExecution() 开始执行
  - [x] 13.7 实现定时轮询批改状态（30秒间隔）

## 阶段五：样式与优化（1天）

- [x] 14. CSS 样式
  - [x] 14.1 在 index.css 添加测试计划卡片样式
  - [x] 14.2 添加工作流进度条样式
  - [x] 14.3 添加步骤详情展开样式
  - [x] 14.4 添加状态标识颜色样式
  - [x] 14.5 添加创建表单弹窗样式

- [x] 15. 优化与测试
  - [x] 15.1 添加加载状态和骨架屏
  - [x] 15.2 添加错误处理和提示
  - [x] 15.3 优化轮询逻辑（批改完成后停止）
  - [x] 15.4 测试完整工作流程
  - [x] 15.5 修复发现的问题

