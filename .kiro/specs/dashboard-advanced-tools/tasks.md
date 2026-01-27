# Implementation Plan: 测试面板高级分析工具

## Overview

本实现计划将测试面板（index.html）的高级分析工具功能分解为可执行的编码任务。

**重要：所有数据都基于批量评估任务（batch_tasks）的评估结果进行分析。**

- 错误样本 = 批量评估中 AI 评分与期望评分不一致的作业
- 异常检测 = 批量评估中检测到的异常评分模式
- 错误聚类 = 对批量评估错误样本的聚类分析
- 优化建议 = 基于批量评估错误分析的 AI 建议
- 批次对比 = 不同批量评估任务的结果对比
- 数据下钻 = 批量评估数据的多维度分析

## Tasks

- [x] 1. 实现徽章数据加载功能
  - [x] 1.1 在 dashboard.py 中添加统计 API 端点
    - 创建 `/api/dashboard/advanced-tools/stats` 端点
    - 从批量评估任务中聚合错误样本、异常、聚类、建议的统计数据
    - _Requirements: 1.1_

  - [x] 1.2 在 index.js 中完善 loadAdvancedToolsStats 函数
    - 调用统计 API 获取数据
    - 更新各工具卡片的徽章数字
    - 处理 API 失败情况（显示 0）
    - _Requirements: 1.2, 1.3, 1.4, 1.5, 1.6_

  - [ ]* 1.3 编写徽章数据加载的属性测试
    - **Property 1: 徽章数据一致性**
    - **Validates: Requirements 1.2, 1.3, 1.4, 1.5**

- [x] 2. 实现错误样本库弹窗
  - [x] 2.1 在 index.html 中添加错误样本弹窗 HTML 结构
    - 添加弹窗容器、统计卡片、筛选器、列表区域
    - 添加批量操作栏
    - _Requirements: 2.1, 2.2, 2.3_

  - [x] 2.2 在 index.js 中实现 openErrorSamplesModal 函数
    - 打开弹窗并从批量评估任务加载统计数据
    - 加载错误样本列表（AI评分与期望评分不一致的作业）
    - 实现筛选功能（按错误类型、状态、学科筛选）
    - _Requirements: 2.4, 2.5_

  - [x] 2.3 实现错误样本详情展示和批量操作
    - 点击样本项显示详情（包含批量评估任务信息）
    - 勾选样本显示批量操作栏
    - 实现批量状态更新
    - _Requirements: 2.6, 2.7, 2.8, 2.9_

  - [ ]* 2.4 编写错误样本筛选的属性测试
    - **Property 2: 筛选结果正确性**
    - **Validates: Requirements 2.5**

- [x] 3. 实现异常检测弹窗
  - [x] 3.1 在 index.html 中添加异常检测弹窗 HTML 结构
    - 添加弹窗容器、统计卡片、日志列表
    - _Requirements: 3.1, 3.2_

  - [x] 3.2 在 index.js 中实现 openAnomalyModal 函数
    - 打开弹窗并从批量评估任务加载异常统计
    - 加载异常日志列表（批量评估中检测到的异常）
    - 实现确认异常功能
    - _Requirements: 3.3, 3.4, 3.5_

- [x] 4. 实现错误聚类弹窗
  - [x] 4.1 在 index.html 中添加错误聚类弹窗 HTML 结构
    - 添加弹窗容器、聚类列表、空状态
    - _Requirements: 4.1, 4.3_

  - [x] 4.2 在 index.js 中实现 openClusteringModal 函数
    - 打开弹窗并加载聚类列表（基于批量评估错误样本的聚类）
    - 点击聚类项显示该聚类下的样本列表
    - 处理空状态
    - _Requirements: 4.2, 4.4, 4.5_

- [x] 5. 实现优化建议弹窗
  - [x] 5.1 在 index.html 中添加优化建议弹窗 HTML 结构
    - 添加弹窗容器、建议列表、空状态
    - _Requirements: 5.1, 5.3_

  - [x] 5.2 在 index.js 中实现 openOptimizationModal 函数
    - 打开弹窗并加载建议列表（基于批量评估错误分析的 AI 建议）
    - 点击建议项展开详情
    - 实现状态更新功能
    - _Requirements: 5.2, 5.4, 5.5, 5.6_

- [ ] 6. Checkpoint - 确保核心弹窗功能正常
  - 确保所有测试通过，如有问题请询问用户

- [x] 7. 实现批次对比弹窗
  - [x] 7.1 在 dashboard.py 中添加批次对比 API
    - 创建 `/api/dashboard/batch-compare` 端点
    - 实现两个批量评估任务的数据对比逻辑
    - _Requirements: 8.3_

  - [x] 7.2 在 index.html 中添加批次对比弹窗 HTML 结构
    - 添加弹窗容器、批次选择器（选择批量评估任务）、对比结果区域
    - _Requirements: 8.1, 8.2_

  - [x] 7.3 在 index.js 中实现 openBatchCompareModal 函数
    - 打开弹窗并加载批量评估任务列表
    - 选择两个任务后显示对比结果（准确率、错误类型分布）
    - _Requirements: 8.3, 8.4_

  - [ ]* 7.4 编写批次对比的属性测试
    - **Property 5: 批次对比计算正确性**
    - **Validates: Requirements 8.3**

- [x] 8. 实现数据下钻弹窗
  - [x] 8.1 在 dashboard.py 中添加数据下钻 API
    - 创建 `/api/dashboard/drilldown` 端点
    - 基于批量评估任务数据实现多维度聚合逻辑
    - _Requirements: 9.3_

  - [x] 8.2 在 index.html 中添加数据下钻弹窗 HTML 结构
    - 添加弹窗容器、维度选择器（学科、书本、页码、题型）、数据列表
    - _Requirements: 9.1, 9.2_

  - [x] 8.3 在 index.js 中实现 openDrilldownModal 函数
    - 打开弹窗并显示维度选择器
    - 选择维度后显示批量评估数据的分析结果
    - 点击数据项进一步下钻
    - _Requirements: 9.3, 9.4, 9.5_

  - [ ]* 8.4 编写数据下钻的属性测试
    - **Property 6: 数据下钻聚合正确性**
    - **Validates: Requirements 9.3**

- [ ] 9. 完善热点图详情弹窗
  - [ ] 9.1 完善 heatmapDetailModal 的内容渲染
    - 显示错误统计和错误列表
    - 点击错误项跳转到错误样本详情
    - _Requirements: 6.1, 6.2, 6.3, 6.4_

- [ ] 10. 完善日报详情弹窗
  - [ ] 10.1 完善 reportDetailModal 的内容渲染
    - 显示完整的日报内容
    - 包含统计数据、任务列表、问题汇总
    - _Requirements: 7.1, 7.2, 7.3_

- [x] 11. 实现空状态优化
  - [x] 11.1 为所有列表添加空状态处理
    - 错误样本列表空状态
    - 异常日志列表空状态
    - 聚类列表空状态（含开始分析按钮）
    - 建议列表空状态（含生成建议按钮）
    - 热点图空状态
    - 日报列表空状态
    - _Requirements: 10.1, 10.2, 10.3, 10.4, 10.5, 10.6_

  - [ ]* 11.2 编写空状态显示的属性测试
    - **Property 7: 空状态显示正确性**
    - **Validates: Requirements 10.1, 10.2, 10.3, 10.4, 10.5, 10.6**

- [x] 12. 添加弹窗样式
  - [x] 12.1 在 index.css 中添加弹窗相关样式
    - 统一弹窗样式（遵循 ui-style.md 规范）
    - 添加统计卡片、列表项、筛选器样式
    - 添加空状态样式
    - _Requirements: 2.1, 3.1, 4.1, 5.1, 8.1, 9.1_

- [x] 13. Final Checkpoint - 确保所有功能正常
  - 确保所有测试通过，如有问题请询问用户

## Notes

- 任务标记 `*` 的为可选测试任务，可跳过以加快 MVP 开发
- 每个任务都引用了具体的需求编号以便追溯
- 检查点任务用于确保增量验证
- 属性测试验证通用正确性属性
- 单元测试验证具体示例和边界情况
