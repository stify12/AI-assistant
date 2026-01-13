# Implementation Plan - Prompt 调优与评测系统

- [x] 1. 项目结构和基础设置




  - [x] 1.1 创建前端文件结构







    - 创建 `templates/prompt-optimize.html` 页面模板
    - 创建 `static/js/prompt-optimize.js` JavaScript 文件
    - 创建 `static/css/prompt-optimize.css` 样式文件
    - _Requirements: 1.1, 1.2_

  - [x] 1.2 创建后端存储目录和数据模型

    - 创建 `prompt_tasks/` 目录用于存储任务数据
    - 实现 JSON 文件读写工具函数
    - _Requirements: 2.7, 3.2_
  - [ ]* 1.3 Write property test for data model serialization
    - **Property 3: Sample Addition Increases Dataset Size**
    - **Validates: Requirements 2.7, 3.2**

- [x] 2. 主界面入口和页面框架


  - [x] 2.1 在主界面添加"提示词优化"按钮


    - 修改 `templates/index.html` 添加导航按钮
    - 添加路由 `/prompt-optimize` 到 `app.py`
    - _Requirements: 1.1_
  - [x] 2.2 实现页面基础框架

    - 实现三个 Tab 切换（调试、批量、智能优化）
    - 实现 Prompt 编辑器区域
    - 实现模型选择器和版本选择器
    - _Requirements: 1.2, 1.3_

- [x] 3. Prompt 编辑器和变量检测



  - [x] 3.1 实现 Prompt 编辑器组件

    - 实现 textarea 编辑器
    - 实现 `{{变量名}}` 语法高亮
    - 实现变量自动检测和提取
    - _Requirements: 2.1, 2.2_
  - [ ]* 3.2 Write property test for variable detection
    - **Property 1: Variable Detection Consistency**
    - **Validates: Requirements 2.2**
  - [x] 3.3 实现变量输入区域

    - 根据检测到的变量动态生成输入字段
    - 实现图片类型变量的上传功能
    - 实现文本类型变量的输入框
    - _Requirements: 2.2, 2.3_

- [x] 4. 调试模式功能


  - [x] 4.1 实现模型回答生成

    - 实现 `/api/prompt-eval/generate` API
    - 实现流式响应显示
    - 实现生成按钮和加载状态
    - _Requirements: 2.4, 2.5_

  - [x] 4.2 实现评分功能
    - 实现 1-10 分评分 UI 组件
    - 实现评分保存逻辑
    - 实现评分验证（1-10范围）
    - _Requirements: 2.6_
  - [ ]* 4.3 Write property test for score validation
    - **Property 2: Score Recording Validity**
    - **Validates: Requirements 2.6**
  - [x] 4.4 实现添加至评测集功能

    - 实现 `/api/prompt-sample` POST API
    - 实现样本保存到 JSON 文件
    - 实现添加成功提示
    - _Requirements: 2.7_

- [x] 5. Checkpoint - 确保调试模式功能正常

  - Ensure all tests pass, ask the user if questions arise.

- [x] 6. 批量评测界面


  - [x] 6.1 实现数据表格组件

    - 实现表格渲染（序号、提问、模型回答、理想回答、评分）
    - 实现单元格展开查看功能
    - 实现行选择功能
    - _Requirements: 3.1, 3.6_
  - [x] 6.2 实现分页功能

    - 实现分页计算逻辑
    - 实现分页 UI 控件
    - 实现每页条数选择（10/20/50）
    - _Requirements: 3.5_
  - [ ]* 6.3 Write property test for pagination
    - **Property 5: Pagination Correctness**
    - **Validates: Requirements 3.5**
  - [x] 6.4 实现添加行功能

    - 实现添加空行按钮
    - 实现行内编辑功能
    - _Requirements: 3.2_

- [x] 7. 批量数据导入



  - [x] 7.1 实现文件上传功能

    - 实现 `/api/prompt-sample/batch` API
    - 实现 Excel/CSV 文件解析
    - 实现导入进度显示
    - _Requirements: 3.3_
  - [ ]* 7.2 Write property test for file import
    - **Property 4: File Import Preserves Data**
    - **Validates: Requirements 3.3**

- [x] 8. 批量生成回答

  - [x] 8.1 实现批量生成 API
    - 扩展 `/api/prompt-eval/generate` 支持批量处理
    - 实现 SSE 流式进度返回
    - 实现并发控制
    - _Requirements: 4.1, 4.2, 4.3_
  - [ ]* 8.2 Write property test for batch generation
    - **Property 6: Batch Generation Processes All Unscored**
    - **Property 7: Progress Tracking Accuracy**
    - **Validates: Requirements 4.1, 4.2, 4.3**
  - [x] 8.3 实现取消操作


    - 实现取消按钮
    - 实现后端任务取消逻辑
    - _Requirements: 4.4_

- [x] 9. Checkpoint - 确保批量功能正常
  - Ensure all tests pass, ask the user if questions arise.

- [x] 10. 智能评分功能
  - [x] 10.1 实现评分配置面板
    - 实现评分面板 UI
    - 实现三种评分规则生成方式选择
    - _Requirements: 5.1, 5.2_
  - [x] 10.2 实现 AI 生成评分规则
    - 实现 `/api/prompt-score/rules` API
    - 实现基于 Prompt 分析生成规则
    - 实现基于用户打分学习生成规则
    - _Requirements: 5.3, 5.4_
  - [x] 10.3 实现用户自定义评分规则
    - 实现评分规则编辑器
    - 实现规则验证逻辑
    - _Requirements: 6.1, 6.2, 6.3_
  - [ ]* 10.4 Write property test for scoring rules validation
    - **Property 10: Scoring Rules Validation**
    - **Validates: Requirements 6.3**
  - [x] 10.5 实现批量 AI 评分
    - 实现 `/api/prompt-score/batch` API
    - 实现"为未评分的回答评分"功能
    - 实现"为所有回答评分"功能（带确认）
    - _Requirements: 5.5, 5.6, 5.7_
  - [ ]* 10.6 Write property test for AI scoring
    - **Property 8: AI Scoring Completeness**
    - **Property 9: Score Display Format**
    - **Validates: Requirements 5.5, 5.6, 5.7**

- [x] 11. 理想回答管理
  - [x] 11.1 实现理想回答编辑
    - 实现单元格点击编辑
    - 实现理想回答保存
    - _Requirements: 7.1_
  - [x] 11.2 实现 AI 生成理想回答
    - 实现 `/api/prompt-eval/generate-ideal` API
    - 实现生成后编辑功能
    - _Requirements: 7.2, 7.3_
  - [x] 11.3 实现批量设置理想回答
    - 实现批量设置对话框
    - 实现批量更新逻辑
    - _Requirements: 7.4_

- [x] 12. 统计和导出功能
  - [x] 12.1 实现统计面板
    - 实现平均分计算和显示
    - 实现评分分布图表
    - 实现已评分/总数统计
    - _Requirements: 8.1_
  - [ ]* 12.2 Write property test for statistics calculation
    - **Property 11: Statistics Calculation**
    - **Validates: Requirements 8.1**
  - [x] 12.3 实现导出功能
    - 实现 Excel 导出 API
    - 实现导出按钮和下载
    - _Requirements: 8.2_
  - [ ]* 12.4 Write property test for export
    - **Property 12: Export Data Completeness**
    - **Validates: Requirements 8.2**
  - [x] 12.5 实现排序功能
    - 实现按评分排序
    - 实现按状态排序
    - 实现按序号排序
    - _Requirements: 8.3_
  - [ ]* 12.6 Write property test for sorting
    - **Property 13: Sorting Correctness**
    - **Validates: Requirements 8.3**

- [x] 13. Checkpoint - 确保评分和统计功能正常
  - Ensure all tests pass, ask the user if questions arise.

- [x] 14. 智能优化功能
  - [x] 14.1 实现优化前置检查
    - 实现数据集要求检查（至少5个已评分样本）
    - 实现检查结果提示
    - _Requirements: 9.1, 9.2_
  - [ ]* 14.2 Write property test for optimization prerequisite
    - **Property 14: Optimization Prerequisite Check**
    - **Validates: Requirements 9.1**
  - [x] 14.3 实现智能优化流程
    - 实现低分样本分析
    - 实现 Prompt 优化生成
    - 实现优化进度显示
    - _Requirements: 9.3_
  - [x] 14.4 实现优化报告
    - 实现新版本创建
    - 实现前后对比展示
    - _Requirements: 9.4, 9.5_

- [x] 15. 版本管理功能
  - [x] 15.1 实现版本保存
    - 实现 `/api/prompt-version` POST API
    - 实现版本数据存储
    - 实现平均分计算
    - _Requirements: 10.1_
  - [ ]* 15.2 Write property test for version creation
    - **Property 15: Version Creation**
    - **Validates: Requirements 10.1**
  - [x] 15.3 实现版本列表和选择
    - 实现版本选择器 UI
    - 实现版本列表排序（按时间倒序）
    - _Requirements: 10.2_
  - [ ]* 15.4 Write property test for version sorting
    - **Property 16: Version Sorting**
    - **Validates: Requirements 10.2**
  - [x] 15.5 实现版本加载
    - 实现版本切换加载
    - 实现 Prompt 和数据集恢复
    - _Requirements: 10.3_
  - [ ]* 15.6 Write property test for version loading
    - **Property 17: Version Loading Restores State**
    - **Validates: Requirements 10.3**
  - [x] 15.7 实现版本比对
    - 实现 `/api/prompt-version/<task_id>/compare` API
    - 实现 Prompt 文本差异高亮
    - 实现评分对比图表
    - _Requirements: 10.4, 10.5_
  - [ ]* 15.8 Write property test for version comparison
    - **Property 18: Version Comparison Shows Differences**
    - **Validates: Requirements 10.5**

- [x] 16. Prompt 快速优化功能
  - [x] 16.1 实现一键改写
    - 实现改写按钮
    - 调用现有 `/api/optimize-prompt` API
    - 实现改写结果预览和应用
    - _Requirements: 2.1 (from prompt调优.md)_

- [x] 17. 单样本调试模式
  - [x] 17.1 实现从批量进入调试
    - 实现行点击进入调试模式
    - 实现调试模式数据回填
    - 实现调试结果同步回批量
    - _Requirements: 8.4_

- [x] 18. Final Checkpoint - 确保所有功能正常
  - Ensure all tests pass, ask the user if questions arise.
