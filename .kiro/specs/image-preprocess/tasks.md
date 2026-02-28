# 实施计划：作业图片预处理工具

## 概述

基于需求文档和设计文档，将作业图片预处理工具拆分为增量式编码任务。每个任务构建在前一个任务之上，最终完成完整功能的集成。使用 Python (Flask + OpenCV) 后端和原生 JS 前端。

## 任务

- [x] 1. 搭建项目基础结构与依赖
  - [x] 1.1 在 `requirements.txt` 中添加 `opencv-python-headless` 和 `numpy` 依赖
    - _Requirements: 2.1_
  - [x] 1.2 创建 `Ai/services/image_preprocess_service.py`，实现 `ImagePreprocessService` 类骨架
    - 定义 `STEP_ORDER`、`STEP_LABELS`、`DEFAULT_PARAMS`、`PARAM_RANGES` 常量
    - 实现 `decode_base64_image()` 和 `encode_image_base64()` 静态方法
    - 实现 `validate_and_fix_params()` 参数校验与修正方法
    - _Requirements: 2.1, 8.5, 8.6_
  - [ ]* 1.3 编写参数校验的属性测试
    - **Property 5: 参数范围校验与修正**
    - **Validates: Requirements 8.6**

- [x] 2. 实现图片处理步骤函数
  - [x] 2.1 实现 `step_grayscale()`、`step_denoise()`、`step_contrast()` 方法
    - 灰度转换：`cv2.cvtColor`
    - 去噪：`cv2.GaussianBlur`，kernel_size 参数
    - 对比度增强：`cv2.createCLAHE`，clip_limit 和 tile_grid_size 参数
    - _Requirements: 2.1, 8.5_
  - [x] 2.2 实现 `step_deskew()` 倾斜矫正方法
    - Canny 边缘检测 → 霍夫变换 → 计算角度 → 仿射变换
    - 角度 < 0.5° 时跳过矫正
    - _Requirements: 2.1_
  - [x] 2.3 实现 `step_binarize()` 和 `step_crop()` 方法
    - 自适应二值化：`cv2.adaptiveThreshold`，block_size 和 constant_c 参数
    - 边缘裁剪：检测非白色区域边界 + 10px 边距
    - _Requirements: 2.1, 8.5_
  - [x] 2.4 实现 `step_super_resolution()` 智能高清化方法
    - 尝试加载 EDSR 模型（`cv2.dnn_superres.DnnSuperResImpl_create()`）
    - 回退到 `cv2.resize` + `INTER_CUBIC`
    - 应用 Unsharp Mask 锐化
    - _Requirements: 9.1, 9.2, 9.3_
  - [ ]* 2.5 编写超分辨率尺寸不变量的属性测试
    - **Property 6: 超分辨率尺寸不变量**
    - **Validates: Requirements 9.1**

- [x] 3. 实现处理流水线核心逻辑
  - [x] 3.1 实现 `process_image()` 流水线方法
    - 按 `STEP_ORDER` 顺序遍历已启用步骤
    - 每步执行后保存中间结果（base64 编码）
    - 步骤异常时跳过并记录 warning
    - 返回 `{processed_image, step_results, warnings, param_corrections}`
    - _Requirements: 2.2, 2.3, 2.4, 3.2, 7.1_
  - [ ]* 3.2 编写流水线执行顺序属性测试
    - **Property 2: 流水线执行顺序不变性**
    - **Validates: Requirements 2.2, 3.2**
  - [ ]* 3.3 编写中间结果数量属性测试
    - **Property 3: 中间结果数量与启用步骤一致**
    - **Validates: Requirements 2.3**
  - [ ]* 3.4 编写流水线幂等性属性测试
    - **Property 4: 处理流水线幂等性**
    - **Validates: Requirements 7.1**
  - [ ]* 3.5 编写流水线容错性属性测试
    - **Property 7: 流水线容错性**
    - **Validates: Requirements 2.4**

- [x] 4. Checkpoint - 确保后端服务层测试通过
  - 确保所有测试通过，如有问题请向用户确认。

- [x] 5. 实现路由层与 API
  - [x] 5.1 创建 `Ai/routes/image_preprocess.py`，实现蓝图与 API 路由
    - `GET /image-preprocess` 页面路由
    - `POST /api/image-preprocess/process` 图片处理 API
    - `POST /api/image-preprocess/recognize` 识别对比 API
    - 请求参数校验（格式、大小、base64 有效性）
    - _Requirements: 1.1, 1.2, 1.3, 5.1, 6.1_
  - [x] 5.2 在 `Ai/routes/__init__.py` 中注册 `image_preprocess_bp` 蓝图
    - _Requirements: 6.1_
  - [ ]* 5.3 编写格式校验属性测试
    - **Property 1: 图片格式校验**
    - **Validates: Requirements 1.1, 1.2**

- [x] 6. 实现前端页面
  - [x] 6.1 创建 `Ai/templates/image-preprocess.html` 页面模板
    - 页面布局：左侧控制面板（上传 + 步骤配置 + 参数调节）、右侧预览面板（原图 + 处理结果 + 步骤缩略图）
    - 遵循项目 UI 规范（浅色主题、卡片布局、8px 圆角）
    - _Requirements: 1.4, 3.1, 4.1, 4.2, 8.1, 8.2, 8.3, 8.4_
  - [x] 6.2 创建 `Ai/static/css/image-preprocess.css` 页面样式
    - 左右分栏布局、步骤开关样式、参数滑块样式、图片对比预览样式、步骤缩略图列表样式
    - _Requirements: 4.1, 4.5_
  - [x] 6.3 创建 `Ai/static/js/image-preprocess.js` 页面逻辑
    - 图片上传与预览、步骤开关控制、参数调节控件
    - 调用处理 API 并渲染步骤中间结果
    - 步骤缩略图点击切换预览
    - 调用识别对比 API 并渲染结果
    - 加载状态指示器、错误提示与重试
    - _Requirements: 1.4, 3.1, 4.3, 4.4, 4.5, 5.1, 5.2, 5.3, 5.4, 8.1_

- [x] 7. 集成与导航
  - [x] 7.1 在 `Ai/templates/index.html` 侧边栏工具区添加"图片预处理"导航链接
    - _Requirements: 6.2, 6.3_

- [x] 8. 最终 Checkpoint - 确保所有测试通过，功能完整
  - 确保所有测试通过，如有问题请向用户确认。

## 备注

- 标记 `*` 的子任务为可选测试任务，可跳过以加快 MVP 交付
- 每个任务引用了具体的需求编号以确保可追溯性
- 属性测试使用 `hypothesis` 库，每个测试至少 100 次迭代
- 超分辨率模型文件（EDSR_x2.pb / EDSR_x4.pb）需在部署时下载，不纳入 Git
