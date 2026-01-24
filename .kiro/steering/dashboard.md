# 测试计划看板 (Dashboard)

## 功能概述
首页 Dashboard 看板提供测试计划管理和数据概览功能，是平台的核心入口。

## API 路由 (`routes/dashboard.py`)

### 概览统计
- `GET /api/dashboard/overview?range=today|week|month` - 获取概览统计数据
- `POST /api/dashboard/sync` - 手动刷新数据

### 任务列表
- `GET /api/dashboard/tasks?page=1&page_size=20&status=all` - 获取批量任务列表

### 数据集概览
- `GET /api/dashboard/datasets?subject_id=&sort_by=created_at&order=desc` - 获取数据集概览
- `GET /api/dashboard/datasets/<dataset_id>/history?limit=5` - 获取数据集历史测试记录

### 学科评估
- `GET /api/dashboard/subjects` - 获取学科评估概览

### 测试计划 CRUD
- `GET /api/dashboard/plans?status=all` - 获取计划列表
- `POST /api/dashboard/plans` - 创建计划
- `GET /api/dashboard/plans/<plan_id>` - 获取计划详情
- `PUT /api/dashboard/plans/<plan_id>` - 更新计划
- `DELETE /api/dashboard/plans/<plan_id>` - 删除计划
- `POST /api/dashboard/plans/<plan_id>/start` - 启动计划
- `POST /api/dashboard/plans/<plan_id>/clone` - 克隆计划
- `POST /api/dashboard/plans/<plan_id>/tasks` - 关联任务到计划

### AI生成计划
- `POST /api/dashboard/ai-plan` - AI生成测试计划建议

### 自动化调度
- `PUT /api/dashboard/plans/<plan_id>/schedule` - 设置计划调度配置

### 缓存管理
- `GET /api/dashboard/cache/status` - 获取缓存状态
- `POST /api/dashboard/cache/clear` - 清除缓存

## 服务层 (`services/dashboard_service.py`)

### 缓存机制
- 内存缓存，默认 5 分钟 TTL
- 缓存键: `overview_{range}`, `all_batch_tasks`, `datasets_overview_*`, `subjects_overview`
- 支持手动清除和自动过期

### 统计计算
- 从 `batch_tasks/` 目录扫描所有任务 JSON 文件
- 按时间范围筛选: today/week/month
- 准确率计算: 从每个作业的 evaluation 直接统计
- 趋势对比: 当前周 vs 上周

### 数据集难度标签
- 简单 (easy): 历史准确率 >= 90%
- 中等 (medium): 70% <= 准确率 < 90%
- 困难 (hard): 准确率 < 70%

## 前端实现

### 页面结构 (`templates/index.html`)
- 顶部统计卡片: 数据集数、任务数、题目数、准确率
- 左侧: 批量任务列表 (分页)
- 右侧: 数据集概览、学科评估、测试计划

### JavaScript (`static/js/index.js`)
- `loadOverview()` - 加载概览统计
- `loadTasks()` - 加载任务列表
- `loadDatasets()` - 加载数据集概览
- `loadSubjects()` - 加载学科评估
- `loadPlans()` - 加载测试计划

### 样式 (`static/css/index.css`)
- 深色主题，参考 ChatGPT 风格
- 统计卡片、任务列表、数据集卡片样式

## 高级分析模块

### 批量对比 (`routes/batch_compare.py`)
- 多任务准确率对比
- 趋势图表生成

### 异常检测 (`routes/anomaly.py`)
- 自动识别准确率异常波动
- 基于统计方法检测异常

### 聚类分析 (`routes/clustering.py`)
- 按错误类型聚类
- 按学科聚类

### 下钻分析 (`routes/drilldown.py`)
- 多维度数据钻取
- 学科 → 书本 → 页码 → 题目

### 错误样本 (`routes/error_samples.py`)
- 错误样本管理
- 支持标记和导出

## 自动化调度 (`routes/automation.py`)

### 调度类型
- `daily`: 每天固定时间执行
- `weekly`: 每周固定日期时间执行
- `cron`: 自定义 cron 表达式

### 配置文件
- `automation_config.json`: 存储调度配置
