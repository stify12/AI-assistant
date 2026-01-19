# Implementation Plan: Dataset Page Management

## Overview

增强数据集编辑弹窗，添加单页重新识别和单页删除功能。实现分为后端API增强、前端UI组件、交互逻辑三个部分。

## Tasks

- [x] 1. 后端API增强
  - [x] 1.1 添加获取页码图片信息API
    - 在 `routes/dataset_manage.py` 中添加 `/api/dataset/page-image-info` 接口
    - 根据 book_id 和 page_num 查询最近的作业图片URL
    - _Requirements: 4.1, 4.2_

  - [x] 1.2 增强数据集更新API支持删除页码
    - 修改 `routes/batch_evaluation.py` 中的 `PUT /api/batch/datasets/<dataset_id>`
    - 支持删除指定页码的数据（当 base_effects 中某页为空数组或 null 时删除）
    - 自动更新 pages 列表和 question_count
    - _Requirements: 5.1, 5.4, 5.5_

- [x] 2. 前端编辑弹窗UI增强
  - [x] 2.1 添加页面操作区HTML结构
    - 在编辑弹窗的页码标签下方添加操作区
    - 包含图片预览区、"重新识别"按钮、"删除此页"按钮
    - _Requirements: 1.1, 1.2_

  - [x] 2.2 添加重新识别面板HTML结构
    - 添加可折叠的图片选择面板
    - 包含图片网格、加载状态、取消/确认按钮
    - _Requirements: 2.1_

  - [x] 2.3 添加相关CSS样式
    - 页面操作区样式
    - 重新识别面板样式
    - 图片选择卡片样式
    - _Requirements: 1.1, 2.1_

- [x] 3. 前端交互逻辑实现
  - [x] 3.1 实现图片预览功能
    - 加载并显示当前页码的图片缩略图
    - 切换页码时更新图片
    - 点击图片显示大图预览
    - _Requirements: 4.1, 4.2, 4.3, 4.4_

  - [x] 3.2 实现重新识别功能
    - 点击按钮展开图片选择面板
    - 加载可用作业图片列表
    - 选择图片后调用识别API
    - 识别完成后更新表格数据
    - _Requirements: 2.2, 2.3, 2.4, 2.5, 2.6, 2.7, 2.8_

  - [x] 3.3 实现删除页面功能
    - 点击按钮显示确认对话框
    - 确认后从编辑数据中移除该页
    - 处理最后一页删除的特殊情况
    - _Requirements: 3.1, 3.2, 3.3, 3.4, 3.5_

  - [x] 3.4 增强保存逻辑
    - 保存时处理删除的页码
    - 更新统计信息
    - 处理全部删除的情况
    - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.5_

- [x] 4. Checkpoint - 功能验证
  - 确保所有功能正常工作
  - 测试重新识别流程
  - 测试删除页面流程
  - 测试边界情况（最后一页删除）

- [ ]* 5. 属性测试
  - [ ]* 5.1 编写识别结果更新一致性属性测试
    - **Property 1: Recognition Result Update Consistency**
    - **Validates: Requirements 2.6, 2.7**

  - [ ]* 5.2 编写删除页面数据一致性属性测试
    - **Property 2: Delete Page Data Consistency**
    - **Validates: Requirements 3.3**

  - [ ]* 5.3 编写保存数据一致性属性测试
    - **Property 3: Save Data Consistency**
    - **Validates: Requirements 5.1, 5.4**

- [x] 6. Final Checkpoint
  - 确保所有测试通过
  - 验证UI交互流畅
  - 确认数据正确保存

## Notes

- Tasks marked with `*` are optional and can be skipped for faster MVP
- 主要修改文件：`routes/dataset_manage.py`, `routes/batch_evaluation.py`, `static/js/dataset-manage.js`, `static/css/dataset-manage.css`
- 复用现有的图片预览弹窗和加载状态组件
- 复用现有的识别API `/api/dataset/recognize`
