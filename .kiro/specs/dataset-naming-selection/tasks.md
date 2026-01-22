# Implementation Plan: 数据集命名与选择功能

## Overview

本实现计划将数据集命名和批量评估数据集选择功能分解为可执行的编码任务。实现顺序遵循：数据库变更 → 后端服务 → 后端API → 前端UI → 测试。

## Tasks

- [x] 1. 数据库结构变更
  - [x] 1.1 更新 database_schema.sql，为 datasets 表添加 name 字段
    - 添加 `name VARCHAR(200) DEFAULT NULL COMMENT '数据集名称'` 字段
    - 添加 `idx_datasets_name` 索引
    - _Requirements: 2.1, 2.5_
  
  - [x] 1.2 创建数据迁移脚本 migrate_dataset_names.py
    - 为现有无 name 字段的数据集生成默认名称
    - 格式："{book_name}_P{min_page}-{max_page}_{timestamp}"
    - _Requirements: 6.5_

- [x] 2. 后端服务层实现
  - [x] 2.1 扩展 AppDatabaseService 数据集方法
    - 修改 `create_dataset()` 添加 name 参数
    - 修改 `update_dataset()` 支持更新 name 字段
    - 新增 `get_datasets_by_book_page()` 方法查询匹配数据集
    - _Requirements: 2.1, 2.3, 5.1_
  
  - [x] 2.2 扩展 StorageService 数据集方法
    - 修改 `save_dataset()` 处理 name 字段
    - 新增 `generate_default_dataset_name()` 生成默认名称
    - 修改 `load_dataset()` 兼容无 name 字段的旧数据
    - 新增 `get_matching_datasets()` 获取匹配数据集列表
    - _Requirements: 1.2, 2.2, 5.1, 6.1_
  
  - [x] 2.3 编写属性测试：默认名称生成格式
    - **Property 1: Default Name Generation Format**
    - **Validates: Requirements 1.2, 6.1**
  
  - [x] 2.4 编写属性测试：数据集持久化往返
    - **Property 3: Dataset Persistence Round-Trip**
    - **Validates: Requirements 2.3, 5.4**

- [x] 3. Checkpoint - 服务层测试
  - 确保所有服务层测试通过，如有问题请询问用户

- [x] 4. 数据集管理 API 实现
  - [x] 4.1 修改 POST /api/batch/datasets 创建数据集接口
    - 接收 name 参数（可选）
    - 无 name 时自动生成默认名称
    - 验证 name 不能为空或纯空白
    - _Requirements: 1.1, 1.2, 1.5_
  
  - [x] 4.2 修改 PUT /api/batch/datasets/<dataset_id> 更新接口
    - 支持更新 name 和 description 字段
    - _Requirements: 1.3, 1.6_
  
  - [x] 4.3 新增 GET /api/batch/datasets/check-duplicate 重复检测接口
    - 接收 book_id 和 pages 参数
    - 返回已存在的重复数据集列表
    - _Requirements: 7.1, 7.2_
  
  - [x] 4.4 修改 GET /api/batch/datasets 列表接口
    - 返回结果包含 name 字段
    - 支持按 name 模糊搜索
    - 按 created_at 倒序排列
    - _Requirements: 3.1, 3.3, 3.4_
  
  - [x] 4.5 编写属性测试：空白名称拒绝
    - **Property 2: Whitespace Name Rejection**
    - **Validates: Requirements 1.5**
  
  - [x] 4.6 编写属性测试：名称搜索完整性
    - **Property 4: Name Search Completeness**
    - **Validates: Requirements 2.4, 3.3**

- [x] 5. 批量评估 API 实现
  - [x] 5.1 新增 GET /api/batch/matching-datasets 匹配数据集查询接口
    - 接收 book_id 和 page_num 参数
    - 返回所有匹配的数据集列表（含 name、question_count 等）
    - 按 created_at 倒序排列
    - _Requirements: 4.2, 5.1, 5.2, 5.5_
  
  - [x] 5.2 新增 POST /api/batch/tasks/<task_id>/select-dataset 数据集选择接口
    - 接收 homework_ids 数组和 dataset_id
    - 更新作业的 matched_dataset 和 matched_dataset_name
    - 清除已有评估结果，重置状态为 pending
    - _Requirements: 4.5, 4.6, 5.4_
  
  - [x] 5.3 修改 GET /api/batch/tasks/<task_id>/homework/<homework_id> 作业详情接口
    - 返回结果包含 matched_dataset_name 字段
    - _Requirements: 4.4_
  
  - [x] 5.4 修改自动匹配逻辑
    - 当存在多个匹配数据集时，默认选择最新创建的
    - 记录 matched_dataset_name 到任务数据
    - _Requirements: 4.3, 5.3_
  
  - [x] 5.5 编写属性测试：匹配数据集完整性
    - **Property 10: Matching Datasets Completeness**
    - **Validates: Requirements 5.1, 7.1**
  
  - [x] 5.6 编写属性测试：数据集列表排序
    - **Property 7: Dataset List Sorting**
    - **Validates: Requirements 3.4, 5.2**

- [x] 6. Checkpoint - API 层测试
  - 确保所有 API 测试通过，如有问题请询问用户

- [x] 7. 数据集管理前端实现
  - [x] 7.1 修改 dataset-manage.html 添加命名 UI
    - 在保存数据集前添加名称输入框
    - 添加描述文本框（可选）
    - 添加重复检测提示弹窗
    - _Requirements: 1.1, 1.6, 7.2, 7.3_
  
  - [x] 7.2 修改 dataset-manage.js 实现命名逻辑
    - 实现 `checkDuplicateDatasets()` 重复检测
    - 实现 `generateDefaultName()` 默认名称生成
    - 修改 `saveDataset()` 提交 name 参数
    - 修改数据集列表渲染显示 name
    - _Requirements: 1.2, 3.1, 3.2, 7.1_
  
  - [x] 7.3 修改 dataset-manage.css 添加命名相关样式
    - 命名输入区域样式
    - 重复检测弹窗样式
    - _Requirements: UI风格规范_

- [x] 8. 批量评估前端实现
  - [x] 8.1 修改 batch-evaluation.html 添加数据集选择 UI
    - 添加数据集选择弹窗
    - 在作业列表中显示数据集名称
    - 添加批量选择按钮
    - _Requirements: 4.1, 4.2, 4.4_
  
  - [x] 8.2 修改 batch-evaluation.js 实现数据集选择逻辑
    - 实现 `showDatasetSelector()` 显示选择弹窗
    - 实现 `loadMatchingDatasets()` 加载匹配数据集
    - 实现 `selectDatasetForHomework()` 单个选择
    - 实现 `batchSelectDataset()` 批量选择
    - 修改作业列表渲染显示 matched_dataset_name
    - _Requirements: 4.1, 4.2, 4.5, 4.6_
  
  - [x] 8.3 修改 batch-evaluation.css 添加数据集选择相关样式
    - 数据集选择弹窗样式
    - 多数据集提示样式
    - _Requirements: UI风格规范_

- [x] 9. Checkpoint - 前端功能测试
  - 确保前端功能正常工作，如有问题请询问用户

- [x] 10. 集成测试与兼容性验证
  - [x] 10.1 编写集成测试：创建数据集完整流程
    - 创建带名称的数据集
    - 验证列表显示
    - 编辑名称
    - 验证更新
    - _Requirements: 1.1, 1.3, 3.1_
  
  - [x] 10.2 编写集成测试：批量评估数据集选择流程
    - 创建多个相同页码的数据集
    - 创建评估任务
    - 验证多数据集返回
    - 选择特定数据集
    - 执行评估
    - _Requirements: 4.1, 4.2, 5.1_
  
  - [x] 10.3 编写兼容性测试：旧数据集读取
    - 模拟无 name 字段的旧数据
    - 验证读取时生成默认名称
    - 验证可正常用于评估
    - _Requirements: 6.1, 6.2, 6.3_
  
  - [x] 10.4 编写属性测试：向后兼容-无名称数据集读取
    - **Property 13: Backward Compatibility - Nameless Dataset Reading**
    - **Validates: Requirements 2.2, 6.1**

- [x] 11. Final Checkpoint - 完整功能验证
  - 确保所有测试通过，如有问题请询问用户

## Notes

- All tasks are required for comprehensive implementation
- Each task references specific requirements for traceability
- Checkpoints ensure incremental validation
- Property tests validate universal correctness properties
- Unit tests validate specific examples and edge cases
- 实现语言：Python (后端)、JavaScript (前端)
- 测试框架：pytest + hypothesis (属性测试)
