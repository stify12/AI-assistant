# 测试计划看板 - 需求文档

## 功能概述

开发一个测试计划看板功能，替换现有首页的聊天界面（`templates/index.html`），让团队成员能够清晰地了解每天的测试情况、测试内容和测试进度。支持智能分析、自动化调度、团队协作等高级功能。

## 术语表

| 术语 | 定义 | 对应数据 |
|------|------|----------|
| 测试计划 | 一组有组织的测试任务集合，包含目标、时间、数据集等 | 新建 `test_plans` 表 |
| 数据集 | 基准效果数据，用于评估AI批改准确率 | `datasets` 表 + `baseline_effects` 表 |
| 批量任务 | 批量评估任务，包含多个作业的评估结果 | `batch_tasks/` 目录下的 JSON 文件 |
| 作业项 | 批量任务中的单个作业评估记录 | `homework_items` 数组 |
| 准确率 | 正确题目数 / 总题目数 | `correct_count / total_questions` |
| 错误类型 | 识别错误-判断错误、识别正确-判断错误、缺失题目、AI识别幻觉等 | `evaluation.errors[].error_type` |
| 热点图 | 可视化展示错误分布的图表 | 按 book_id/page_num/index 聚合 |
| 回归测试 | 模型更新后对所有数据集重新测试 | 关联 `test_plans` 和 `datasets` |
| A/B测试 | 同一数据集用不同配置测试对比效果 | 对比不同 `task_id` 的结果 |
| 错误聚类 | 将相似错误自动归类 | AI 分析 `errors` 数组 |

## 现有数据结构说明

### 批量任务数据结构 (`batch_tasks/*.json`)
```json
{
  "task_id": "074805e2",
  "name": "批量评估-2026/1/9",
  "status": "completed",  // pending | processing | completed | failed
  "homework_items": [
    {
      "homework_id": "2009453813070671874",
      "student_name": "张奕一",
      "book_id": "1997848714229166082",
      "book_name": "袁崇焕中学校本作业.同步导学练.物理.八上",
      "page_num": 76,
      "pic_path": "https://...",
      "homework_result": "[...]",  // AI批改结果JSON字符串
      "matched_dataset": "b3b0395e",
      "status": "completed",
      "accuracy": 0.1667,
      "evaluation": {
        "accuracy": 0.1667,
        "total_questions": 6,
        "correct_count": 1,
        "error_count": 5,
        "errors": [
          {
            "index": "1",
            "base_answer": "冷热程度 摄氏度 ℃",
            "base_user": "热量 度 ℃",
            "hw_user": "热量",
            "error_type": "识别错误-判断错误"
          }
        ]
      }
    }
  ],
  "overall_report": {
    "overall_accuracy": 0.0435,
    "total_homework": 11,
    "total_questions": 46,
    "correct_questions": 2
  },
  "created_at": "2026-01-09T15:26:23.620417"
}
```

### 数据集数据结构 (`datasets` 表)
```sql
-- 数据集元数据
datasets (
  dataset_id VARCHAR(36),  -- 唯一标识
  name VARCHAR(200),       -- 数据集名称，如 "物理八上_P76-86_01091526"
  book_id VARCHAR(50),     -- 关联书本ID
  book_name VARCHAR(200),  -- 书本名称
  subject_id INT,          -- 学科ID (0=英语,1=语文,2=数学,3=物理,4=化学,5=生物,6=地理)
  pages JSON,              -- 页码列表 [76,77,78,...]
  question_count INT,      -- 题目总数
  description TEXT,        -- 描述
  created_at DATETIME
)

-- 基准效果数据
baseline_effects (
  dataset_id VARCHAR(36),
  page_num INT,
  question_index VARCHAR(50),  -- 题号
  temp_index INT,              -- 临时索引
  question_type VARCHAR(20),   -- 题目类型
  answer TEXT,                 -- 标准答案
  user_answer TEXT,            -- 用户答案（基准）
  is_correct VARCHAR(10),      -- 判断结果 yes/no
  extra_data JSON              -- 额外数据 {questionType, bvalue}
)
```

### 学科ID映射
| subject_id | 学科 | 匹配规则 |
|------------|------|----------|
| 0 | 英语 | 按 tempIndex 匹配 |
| 1 | 语文 | 按 index 匹配，支持模糊匹配(85%) |
| 2 | 数学 | 按 tempIndex 匹配 |
| 3 | 物理 | 按 tempIndex 匹配 |
| 4 | 化学 | 按 tempIndex 匹配 |
| 5 | 生物 | 按 tempIndex 匹配 |
| 6 | 地理 | 按 tempIndex 匹配 |

### 错误类型分类
| 错误类型 | 说明 | 严重程度 |
|----------|------|----------|
| 识别错误-判断错误 | 识别和判断都有误 | high |
| 识别正确-判断错误 | 识别正确但判断错误 | high |
| 识别错误-判断正确 | 识别不准确但判断结果正确 | medium |
| 识别差异-判断正确 | 模糊匹配通过，判断正确 | low |
| 识别题干-判断正确 | AI多识别了题干内容，但判断正确 | low |
| 缺失题目 | AI批改结果中缺少该题 | high |
| AI识别幻觉 | AI将学生错误答案"脑补"成标准答案 | high |

---

## 一、基础功能需求（1-9）

### US-1: 测试计划看板首页布局
**作为** 测试人员
**我希望** 在首页看到清晰的测试看板布局
**以便于** 快速了解测试整体情况

**技术背景:**
- 当前首页 `templates/index.html` 是聊天界面，需要重构为看板
- 保留原有侧边栏导航结构（批量评估、学科批改、知识点类题、数据分析、数据集管理、提示词优化）
- 遵循项目 UI 规范：浅色主题，背景 #f5f5f7，卡片 #fff，圆角 12px

**验收标准:**
- 1.1 替换原有聊天界面为测试计划看板，原聊天功能移至 `/chat` 路由
- 1.2 页面分为四个主要区域：统计概览区（顶部）、任务列表区（左下）、数据集区（右上）、学科概览区（右下）
- 1.3 保留侧边栏导航，结构与现有 `index.html` 一致
- 1.4 顶部显示最后数据同步时间，格式：`最后同步: 2026-01-23 10:30`
- 1.5 支持响应式布局，断点：1200px（两列）、768px（单列）

### US-2: 统计概览卡片展示
**作为** 测试人员
**我希望** 看到关键统计数据的卡片展示
**以便于** 一眼了解测试状态

**数据来源:**
- 从 `batch_tasks/` 目录扫描所有 JSON 文件
- 聚合 `overall_report` 中的统计数据
- 按 `created_at` 字段筛选时间范围

**验收标准:**
- 2.1 显示数据集总数卡片：总数 + 按学科分布（如：物理 5、数学 3、英语 2）
- 2.2 显示批量任务总数卡片：今日/本周/本月任务数，点击切换时间范围
- 2.3 显示题目总数卡片：已测试题目数 / 数据集总题目数
- 2.4 显示整体准确率卡片：`correct_questions / total_questions`，含趋势箭头（与上周对比）
- 2.5 卡片支持点击跳转：数据集卡片→`/dataset-manage`，任务卡片→`/batch-evaluation`

### US-3: 批量任务列表展示
**作为** 测试人员
**我希望** 看到最近的批量评估任务列表
**以便于** 追踪测试进度

**数据来源:**
- 扫描 `batch_tasks/` 目录，按 `created_at` 倒序排列
- 读取每个任务的 `name`, `status`, `overall_report`, `created_at`

**验收标准:**
- 3.1 显示最近20条批量任务，支持分页加载（每页20条）
- 3.2 每条任务显示：
  - 名称（`name`）
  - 创建时间（`created_at`，格式：01-09 15:26）
  - 状态标签
  - 准确率（`overall_report.overall_accuracy`，百分比格式）
  - 题目数（`overall_report.total_questions`）
- 3.3 状态标签样式：
  - pending: 灰色背景 #f5f5f7，文字 #86868b
  - processing: 蓝色背景 #e3f2fd，文字 #1565c0
  - completed: 绿色背景 #e3f9e5，文字 #1e7e34
  - failed: 红色背景 #ffeef0，文字 #d73a49
- 3.4 点击任务行跳转到 `/batch-evaluation?task_id={task_id}`
- 3.5 支持按状态筛选：全部、待处理、进行中、已完成、异常

### US-4: 数据集概览展示
**作为** 测试人员
**我希望** 看到数据集的概览信息
**以便于** 了解可用的测试基准数据并快速选择合适的数据集

**数据来源:**
- 调用 `StorageService.get_all_datasets_summary()` 获取数据集列表
- 从 `datasets` 表查询元数据
- 聚合 `batch_tasks` 中的历史测试结果

**验收标准:**
- 4.1 显示数据集总数和各学科分布饼图（使用原生 Canvas 或 SVG，不引入图表库）
- 4.2 列表显示每个数据集：
  - 名称（`name`）
  - 学科（根据 `subject_id` 映射）
  - 题目数（`question_count`）
  - 页码范围（从 `pages` 数组计算 min-max）
  - 使用次数（统计 `batch_tasks` 中 `matched_dataset` 匹配次数）
  - 最近使用时间
  - **历史准确率**: 该数据集历次测试的平均准确率（聚合所有关联任务的 `overall_accuracy`）
  - **最近一次测试结果**: 显示最近一次使用该数据集的准确率和时间
- 4.3 点击数据集跳转到 `/dataset-manage?dataset_id={dataset_id}`
- 4.4 显示数据集使用频率排行（Top 5）
- 4.5 支持按学科筛选数据集
- 4.6 **数据集难度标签**: 基于历史准确率自动标记
  - 简单（准确率 >= 90%）：绿色标签 #e3f9e5
  - 中等（准确率 70%-90%）：黄色标签 #fff3e0
  - 困难（准确率 < 70%）：红色标签 #ffeef0
- 4.7 支持按历史准确率排序（升序/降序）
- 4.8 鼠标悬停数据集行时，显示历史测试摘要（最近5次测试的准确率列表）

### US-5: 学科评估概览
**作为** 测试人员
**我希望** 按学科查看评估效果概览
**以便于** 了解各学科AI批改准确率

**数据来源:**
- 聚合所有 `batch_tasks` 中的 `homework_items`
- 按 `subject_id` 分组统计

**验收标准:**
- 5.1 显示各学科准确率柱状图（水平条形图，原生实现）
- 5.2 显示各学科测试任务数量和题目数量
- 5.3 显示各学科错误类型分布：
  - 识别错误-判断错误
  - 识别正确-判断错误
  - 缺失题目
  - AI识别幻觉
- 5.4 准确率低于80%的学科标红警告（背景 #ffeef0）
- 5.5 点击学科行展开详细评估报告（错误样本列表）

### US-6: 测试计划CRUD管理
**作为** 测试人员
**我希望** 创建和管理测试计划
**以便于** 有组织地进行测试工作

**数据存储:**
- 新建 `test_plans` 表存储测试计划
- 新建 `test_plan_datasets` 表存储计划与数据集的关联
- 新建 `test_plan_tasks` 表存储计划与批量任务的关联

**验收标准:**
- 6.1 支持创建测试计划，字段：
  - 名称（必填，最大200字符）
  - 描述（可选，TEXT）
  - 目标学科（下拉选择，可多选）
  - 预期测试量（数字输入）
  - 开始/结束日期（日期选择器）
- 6.2 支持关联数据集到测试计划（多选）
- 6.3 显示测试计划进度条：`completed_count / target_count`
- 6.4 支持编辑测试计划信息（弹窗表单）
- 6.5 支持删除测试计划（需二次确认弹窗）
- 6.6 支持克隆已有测试计划（复制所有字段，名称加"(副本)"后缀）
- 6.7 测试计划状态流转：draft → active → completed/archived
- 6.8 **任务执行记录**: 显示该计划下所有关联的批量评估任务列表
  - 任务名称、执行时间、准确率、状态
  - 支持从计划详情页直接跳转到任务详情
- 6.9 **计划完成度自动计算**: 基于关联任务的完成状态自动更新 `completed_count`
  - 当关联的批量任务状态变为 completed 时，自动 +1
  - 完成度 = 已完成任务数 / 目标测试量
- 6.10 支持手动关联已有批量任务到测试计划（下拉选择或搜索）

### US-7: AI生成测试计划模板
**作为** 测试人员
**我希望** AI根据数据集自动生成测试计划
**以便于** 快速制定合理的测试方案

**技术实现:**
- 调用 `LLMService.call_deepseek()` 生成测试计划
- 分析数据集的 `base_effects` 内容

**验收标准:**
- 7.1 选择数据集作为测试计划基础（支持多选）
- 7.2 设置测试样本数量（模拟学生数，默认30）
- 7.3 AI分析数据集内容，生成测试计划建议，包含：
  - 计划名称（如：物理八上温度章节测试计划）
  - 测试目标（3-5条）
  - 测试步骤
  - 预期时长
  - 验收标准（如：选择题准确率>=95%）
- 7.4 生成内容显示在可编辑文本框中
- 7.5 支持编辑AI生成的内容后保存为测试计划
- 7.6 使用 DeepSeek V3.2 模型生成

### US-8: 侧边栏快捷导航
**作为** 测试人员
**我希望** 保留功能导航入口
**以便于** 快速访问其他功能模块

**技术背景:**
- 复用现有 `index.html` 的侧边栏结构
- 保持与其他页面导航一致

**验收标准:**
- 8.1 保留原有侧边栏结构，包含品牌标识
- 8.2 导航项（与现有一致）：
  - 学科批改评估 → `/subject-grading`
  - 批量评估 → `/batch-evaluation`
  - 知识点类题 → `/knowledge-agent`
  - 数据分析 → `/data-analysis`
  - 数据集管理 → `/dataset-manage`
  - 提示词优化 → `/prompt-optimize`
- 8.3 高亮当前页面对应的导航项（添加 `active` 类）
- 8.4 支持侧边栏折叠/展开（保存状态到 localStorage）

### US-9: 数据手动刷新
**作为** 测试人员
**我希望** 手动刷新看板数据
**以便于** 获取最新统计信息

**验收标准:**
- 9.1 顶部显示"刷新"按钮（图标 + 文字）
- 9.2 点击后重新加载所有统计数据（调用 `/api/dashboard/sync`）
- 9.3 刷新时显示加载动画（按钮旋转 + 禁用状态）
- 9.4 刷新完成后更新"最后同步时间"显示
- 9.5 刷新失败时显示错误提示（Toast 通知，3秒后自动消失）

---

## 二、高级功能需求（10-16）

### US-10: 自动化调度
**作为** 测试人员
**我希望** 定时自动执行测试计划
**以便于** 无需手动触发测试

**技术实现:**
- 使用 APScheduler 实现定时任务
- 调度配置存储在 `test_plans` 表的 `schedule_config` 字段

**验收标准:**
- 10.1 支持设置测试计划的执行时间：
  - 每天固定时间（如：每天 09:00）
  - 每周固定日期时间（如：每周一 09:00）
  - 自定义 cron 表达式
- 10.2 到达执行时间自动触发批量评估（调用现有 `/api/batch/evaluate` 接口）
- 10.3 执行完成后记录执行日志到 `test_plan_logs` 表
- 10.4 支持启用/禁用自动调度（开关按钮）
- 10.5 显示下次执行时间（根据 cron 表达式计算）

### US-11: 问题热点图
**作为** 测试人员
**我希望** 可视化查看错误分布
**以便于** 快速定位问题集中区域

**数据来源:**
- 聚合所有 `batch_tasks` 中的 `evaluation.errors`
- 按 `book_name` → `page_num` → `index` 三级分组

**验收标准:**
- 11.1 按书本-页码-题号三级展示错误热点（树形结构）
- 11.2 颜色深浅表示错误频率：
  - 0-2次：浅绿 #e3f9e5
  - 3-5次：浅黄 #fff3e0
  - 6-10次：浅红 #ffeef0
  - >10次：深红 #d73a49
- 11.3 点击热点查看具体错误详情（弹窗显示错误列表）
- 11.4 支持按学科筛选热点图
- 11.5 支持按时间范围筛选（最近7天/30天/全部）

### US-12: AI测试覆盖率分析
**作为** 测试人员
**我希望** AI分析测试覆盖情况
**以便于** 发现测试盲区

**技术实现:**
- 调用 `LLMService.call_deepseek()` 分析覆盖率
- 对比数据集题目与已测试题目

**验收标准:**
- 12.1 AI分析各学科、各题型的测试覆盖率：
  - 选择题（bvalue=1,2,3）覆盖率
  - 客观填空题（bvalue=4, questionType=objective）覆盖率
  - 主观题（bvalue=5）覆盖率
- 12.2 识别未覆盖或覆盖不足的区域（<50%覆盖率）
- 12.3 生成覆盖率报告（Markdown 格式）
- 12.4 提供补充测试建议（推荐需要测试的数据集）
- 12.5 支持导出覆盖率报告（下载 .md 文件）

### US-13: 测试任务分配
**作为** 测试负责人
**我希望** 将测试计划分配给团队成员
**以便于** 团队协作完成测试

**数据存储:**
- 复用现有 `users` 表
- 新建 `test_plan_assignments` 表存储分配关系

**验收标准:**
- 13.1 测试计划支持指定负责人（从 `users` 表选择）
- 13.2 显示各成员的任务列表（按负责人分组）
- 13.3 支持任务状态更新：待处理 → 进行中 → 已完成
- 13.4 显示团队成员工作量统计（已完成任务数、总题目数）
- 13.5 支持任务评论和备注（存储在 `test_plan_comments` 表）

### US-14: 日报自动生成
**作为** 测试负责人
**我希望** 自动生成测试日报
**以便于** 每日追踪测试进展

**技术实现:**
- 使用 APScheduler 每天 18:00 自动生成当日日报
- 调用 `LLMService.call_deepseek()` 总结关键信息

**验收标准:**
- 14.1 每天 18:00 自动生成当日测试日报
- 14.2 日报内容：
  - 今日任务完成数（今日完成 / 今日计划）
  - 今日准确率（与昨日对比 + 与上周同日对比）
  - 今日主要问题（错误类型 Top 5）
  - **新增错误类型**: 今日首次出现的错误模式（与历史错误类型对比）
  - **高频错误题目**: 同一题目多次出错的情况（按题号聚合，显示出错次数>=3的题目）
  - 明日计划（待处理任务列表）
  - 异常情况（准确率异常波动、任务失败等）
  - 模型版本信息（当日使用的 AI 模型版本）
- 14.3 支持手动触发生成日报（按钮）
- 14.4 支持导出日报（PDF 使用 reportlab，Word 使用 python-docx）
- 14.5 日报使用 AI 总结关键信息（DeepSeek V3.2）
- 14.6 支持查看历史日报列表（按日期倒序）
- 14.7 日报存储到 `daily_reports` 表，保留30天历史
- 14.8 新增错误类型高亮显示（黄色背景 #fff3e0），提醒测试人员关注

### US-15: 测试数据沉淀与趋势分析
**作为** 测试人员
**我希望** 查看历史测试数据趋势
**以便于** 分析长期效果变化

**数据存储:**
- 新建 `daily_statistics` 表存储每日统计快照
- 定时任务每天 00:00 生成当日统计

**验收标准:**
- 15.1 保存所有测试结果到 `daily_statistics` 表
- 15.2 显示准确率趋势折线图（原生 Canvas 实现）：
  - 近7天
  - 近30天
  - 近90天
- 15.3 支持按学科查看趋势（多条折线）
- 15.4 支持标记重要时间点（如模型更新），存储在 `milestones` 表
- 15.5 支持导出历史数据（CSV 格式）

### US-16: 最佳实践库与Prompt版本管理
**作为** 测试人员
**我希望** 沉淀高准确率的配置
**以便于** 复用最佳实践

**数据来源:**
- 从 `prompts.json` 读取 Prompt 配置
- 关联 `batch_tasks` 的评估结果

**验收标准:**
- 16.1 自动获取作业对应的 Prompt 配置（从 `prompts.json`）
- 16.2 记录每次测试使用的 Prompt 版本（存储在 `batch_tasks` 的 `prompt_version` 字段）
- 16.3 标记高准确率（>90%）的 Prompt 为最佳实践（添加 `is_best_practice` 标记）
- 16.4 支持查看 Prompt 版本历史（列表展示）
- 16.5 支持一键应用最佳实践 Prompt（复制到当前配置）

---

## 三、分析功能需求（17-28）

### US-17: A/B测试对比分析
**作为** 测试人员
**我希望** 对比不同配置的测试效果
**以便于** 找到最优配置

**数据来源:**
- 从 `batch_tasks/` 选择两个任务进行对比
- 对比 `overall_report` 和 `evaluation.errors`

**验收标准:**
- 17.1 支持选择两个批量任务进行对比（下拉选择）
- 17.2 并排显示两个任务的：
  - 准确率（百分比 + 差值）
  - 错误分布（按错误类型统计）
  - 题目数和正确数
- 17.3 高亮显示差异项（差值>5%标红/绿）
- 17.4 支持同一数据集不同 Prompt 的对比（筛选 `matched_dataset` 相同的任务）
- 17.5 生成对比报告（Markdown 格式，可下载）

### US-18: 批次对比分析
**作为** 测试人员
**我希望** 对比不同批次的测试结果
**以便于** 发现效果波动

**验收标准:**
- 18.1 选择时间范围内的多个批次（日期选择器）
- 18.2 显示批次间准确率变化曲线（折线图）
- 18.3 标记准确率异常波动的批次（偏离均值>10%）
- 18.4 点击批次节点查看详情（弹窗）
- 18.5 支持导出对比数据（CSV 格式）

### US-19: 错误样本库
**作为** 测试人员
**我希望** 收集典型错误案例
**以便于** 复现和分析问题

**数据存储:**
- 新建 `error_samples` 表存储错误样本
- 关联 `batch_tasks` 的 `evaluation.errors`

**验收标准:**
- 19.1 自动收集所有错误样本（从 `evaluation.errors` 提取）
- 19.2 支持按错误类型分类查看（Tab 切换）
- 19.3 显示错误样本详情：
  - 题号（`index`）
  - 基准答案（`base_answer`）
  - 基准用户答案（`base_user`）
  - AI识别答案（`hw_user`）
  - 错误类型（`error_type`）
- 19.4 支持标记样本状态：待分析、已分析、已修复
- 19.5 支持添加分析备注（文本输入）

### US-20: 错误关联分析
**作为** 测试人员
**我希望** 分析错误之间的关联性
**以便于** 发现系统性问题

**技术实现:**
- 使用 `LLMService.call_deepseek()` 分析关联性
- 聚合错误数据进行统计分析

**验收标准:**
- 20.1 分析错误与书本/页码的关联（哪些书本错误率高）
- 20.2 分析错误与题型的关联（选择题/填空题/主观题）
- 20.3 分析错误与学科的关联（各学科错误分布）
- 20.4 生成关联分析报告（图表 + 文字说明）
- 20.5 提供优化建议（AI 生成）

### US-21: 多维度数据下钻
**作为** 测试人员
**我希望** 从总体数据逐层下钻到详情
**以便于** 深入分析问题

**验收标准:**
- 21.1 支持下钻路径：总体准确率 → 学科 → 书本 → 页码 → 题目
- 21.2 每层显示该层级的统计数据：
  - 总体：整体准确率、总题目数、总错误数
  - 学科：各学科准确率、题目数
  - 书本：各书本准确率、页码范围
  - 页码：各页准确率、题目列表
  - 题目：具体错误详情
- 21.3 支持面包屑导航返回上层（可点击）
- 21.4 下钻时保持筛选条件（时间范围、状态等）
- 21.5 支持在任意层级导出数据（CSV）

### US-22: 错误详情快速查看
**作为** 测试人员
**我希望** 快速查看错误详情
**以便于** 高效分析问题

**验收标准:**
- 22.1 点击错误统计数字直接跳转到错误列表
- 22.2 错误列表显示：题号、错误类型、基准答案、AI答案
- 22.3 支持按错误类型筛选（多选）
- 22.4 支持批量标记错误状态（勾选 + 批量操作按钮）
- 22.5 支持导出错误列表（Excel 格式，使用 openpyxl）

### US-23: 图片对比查看
**作为** 测试人员
**我希望** 同时查看原图和识别结果
**以便于** 分析识别错误原因

**数据来源:**
- 从 `homework_items[].pic_path` 获取原图 URL
- 从 `homework_items[].homework_result` 获取识别结果

**验收标准:**
- 23.1 左右并排显示原图和识别结果（50%/50%布局）
- 23.2 支持图片缩放（滚轮）和拖拽（鼠标拖动）
- 23.3 高亮标记识别错误的区域（红色边框）
- 23.4 显示该题的基准答案和AI答案（底部信息栏）
- 23.5 支持切换上一题/下一题（左右箭头按钮）

### US-24: 多条件组合筛选
**作为** 测试人员
**我希望** 使用多条件组合筛选数据
**以便于** 精确定位问题

**验收标准:**
- 24.1 支持按学科筛选（下拉多选）
- 24.2 支持按题型筛选：
  - 选择题（bvalue=1,2,3）
  - 客观填空题（bvalue=4, questionType=objective）
  - 主观题（其他）
- 24.3 支持按错误类型筛选（多选）
- 24.4 支持按时间范围筛选（日期选择器）
- 24.5 支持按准确率范围筛选（滑块：0%-100%）
- 24.6 支持保存常用筛选条件（存储到 localStorage）

### US-25: 快速导出
**作为** 测试人员
**我希望** 一键导出筛选后的数据
**以便于** 进一步分析

**技术实现:**
- 使用 openpyxl 生成 Excel
- 使用 csv 模块生成 CSV

**验收标准:**
- 25.1 支持导出当前筛选结果
- 25.2 支持导出格式：Excel（.xlsx）、CSV（.csv）
- 25.3 导出内容包含所有字段（题号、答案、错误类型等）
- 25.4 大数据量导出时显示进度（>1000条时）
- 25.5 导出完成后提供下载链接（存储到 `exports/` 目录）

### US-26: 异常检测
**作为** 测试人员
**我希望** 自动识别准确率异常
**以便于** 及时发现问题

**验收标准:**
- 26.1 自动检测准确率异常波动（偏离均值2个标准差）
- 26.2 异常批次标红高亮显示（背景 #ffeef0）
- 26.3 支持设置异常阈值（默认2σ，可调整）
- 26.4 异常时发送通知提醒（页面内 Toast 通知）
- 26.5 记录异常历史（存储到 `anomaly_logs` 表）

### US-27: 相似错误聚类
**作为** 测试人员
**我希望** 自动归类相似错误
**以便于** 减少重复分析

**技术实现:**
- 使用 `LLMService.call_deepseek()` 进行相似度分析
- 基于错误类型和答案内容聚类

**验收标准:**
- 27.1 使用 AI 对错误进行相似度聚类
- 27.2 显示聚类结果：
  - 每类错误数量
  - 典型样本（代表性错误）
  - 聚类标签（AI 生成）
- 27.3 支持查看聚类详情（展开显示所有错误）
- 27.4 支持合并/拆分聚类（手动调整）
- 27.5 支持为聚类添加自定义标签

### US-28: 大模型优化建议
**作为** 测试人员
**我希望** AI根据错误分析生成优化建议
**以便于** 指导改进方向

**技术实现:**
- 调用 `LLMService.call_deepseek()` 分析错误并生成建议
- 输入：错误样本列表、错误类型分布

**验收标准:**
- 28.1 AI 分析错误样本，识别主要问题（Top 5 问题）
- 28.2 生成针对性的优化建议，包含：
  - 问题描述
  - 影响范围（涉及学科、题型）
  - 优化方案（具体建议）
- 28.3 支持标记建议状态：待处理、处理中、已完成
- 28.4 支持导出优化建议报告（Markdown 格式）
- 28.5 建议历史记录（存储到 `optimization_suggestions` 表）

---

## 四、性能与体验优化需求（29-33）

### US-29: 数据缓存策略
**作为** 系统
**我希望** 合理缓存统计数据
**以便于** 提升页面加载速度

**技术实现:**
- 使用 `daily_statistics` 表存储每日统计快照
- 内存缓存使用 Python dict + TTL

**验收标准:**
- 29.1 统计数据缓存5分钟（存储在内存中）
- 29.2 热点图数据后台定时计算并缓存（每小时更新）
- 29.3 支持手动清除缓存（管理员功能）
- 29.4 缓存失效时自动重新计算（懒加载）
- 29.5 显示数据缓存状态（缓存时间、是否过期）

### US-30: 异步加载与骨架屏
**作为** 用户
**我希望** 页面快速响应
**以便于** 获得流畅的使用体验

**验收标准:**
- 30.1 首屏优先加载统计卡片和任务列表（关键数据）
- 30.2 热点图、趋势图延迟加载（非关键数据）
- 30.3 数据加载时显示骨架屏（灰色占位块动画）
- 30.4 鼠标悬停任务行时预加载详情数据（hover 300ms 后触发）
- 30.5 首屏渲染时间 < 3秒（LCP 指标）

### US-31: 大数据量处理
**作为** 系统
**我希望** 高效处理大量数据
**以便于** 保持系统流畅

**验收标准:**
- 31.1 列表超过100条时使用虚拟滚动（只渲染可见区域）
- 31.2 趋势图使用增量更新（只更新变化的数据点）
- 31.3 周报生成、聚类分析等耗时操作放入后台队列（使用 threading）
- 31.4 后台任务显示执行进度（进度条 + 百分比）
- 31.5 虚拟滚动保持60fps（使用 requestAnimationFrame）

### US-32: 智能搜索
**作为** 测试人员
**我希望** 快速搜索任务和数据
**以便于** 高效定位信息

**验收标准:**
- 32.1 全局搜索框支持搜索：
  - 任务名（`batch_tasks[].name`）
  - 数据集名（`datasets.name`）
  - 书本名（`book_name`）
  - 题号（`index`）
- 32.2 记录最近10条搜索历史（存储到 localStorage）
- 32.3 输入时显示搜索建议（防抖 300ms）
- 32.4 搜索结果高亮匹配关键词（黄色背景）
- 32.5 支持快捷键（`/`）聚焦搜索框

### US-33: 数据对比增强
**作为** 测试人员
**我希望** 查看数据的环比/同比变化
**以便于** 了解效果趋势

**验收标准:**
- 33.1 支持与选定时间段进行对比：
  - 上周同期
  - 上月同期
  - 自定义时间段
- 33.2 设置准确率基线（默认85%，可调整）
- 33.3 所有数据与基线对比显示差异值
- 33.4 差异使用颜色标识：
  - 高于基线：绿色 #1e7e34
  - 低于基线：红色 #d73a49
  - 等于基线：灰色 #86868b
- 33.5 支持自定义基线值（输入框 + 保存按钮）

---

## 五、非功能性需求（34）

### NFR-34: 代码质量标准
**作为** 开发团队
**我希望** 代码符合生产级标准
**以便于** 保证系统稳定性和可维护性

**代码注释要求:**
- 34.1 路由函数必须包含文档字符串，说明功能、参数、返回值
  ```python
  @dashboard_bp.route('/api/dashboard/overview')
  def get_overview():
      """
      获取看板概览统计数据
      
      Returns:
          JSON: {
              success: bool,
              data: {
                  today: {...},
                  week: {...},
                  month: {...}
              }
          }
      """
  ```
- 34.2 核心逻辑（统计计算、数据聚合、缓存处理）必须添加行内注释
- 34.3 前端 JavaScript 函数必须添加 JSDoc 注释
  ```javascript
  /**
   * 加载看板概览数据
   * @param {string} timeRange - 时间范围: today|week|month
   * @returns {Promise<Object>} 统计数据
   */
  async function loadOverview(timeRange) { ... }
  ```
- 34.4 复杂条件判断必须添加注释说明判断逻辑

**异常处理要求:**
- 34.5 所有 API 必须校验参数空值，返回明确错误信息
  ```python
  if not task_id:
      return jsonify({'success': False, 'error': '任务ID不能为空'})
  ```
- 34.6 所有 API 必须校验参数类型，类型错误返回 400 状态码
- 34.7 数据库操作必须捕获异常，记录日志并返回友好错误信息
  ```python
  try:
      result = AppDatabaseService.execute_query(sql, params)
  except Exception as e:
      print(f"[Dashboard] 查询失败: {e}")
      return jsonify({'success': False, 'error': '数据查询失败，请稍后重试'})
  ```
- 34.8 外部 API 调用必须设置超时（30秒），超时后返回错误
- 34.9 前端必须捕获 API 调用异常，显示用户友好的错误提示
- 34.10 数组访问必须检查越界，使用安全访问方法

**模块化设计要求:**
- 34.11 路由层、服务层、工具层分离：
  - `routes/dashboard.py` - 路由定义
  - `services/dashboard_service.py` - 业务逻辑
  - `utils/dashboard_utils.py` - 工具函数（可选）
- 34.12 统计计算、缓存管理、AI 分析封装为独立服务类
- 34.13 前端 API 调用封装为统一的请求模块
  ```javascript
  // static/js/dashboard.js
  const DashboardAPI = {
      getOverview: () => fetch('/api/dashboard/overview').then(r => r.json()),
      getDaily: (date) => fetch(`/api/dashboard/daily?date=${date}`).then(r => r.json()),
      // ...
  };
  ```
- 34.14 UI 组件（卡片、图表、列表）封装为可复用函数
- 34.15 避免重复代码，公共逻辑提取为工具函数

**性能要求:**
- 34.16 首屏渲染时间 < 3秒（LCP 指标）
- 34.17 API 响应时间 < 2秒（P95）
- 34.18 输入框使用防抖（300ms）
- 34.19 滚动事件使用节流（16ms，约60fps）
- 34.20 数据库查询必须使用索引（`idx_status`, `idx_subject`, `idx_created_at`）

---

## 六、新增数据库表设计

### test_plans 表
```sql
CREATE TABLE test_plans (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL UNIQUE COMMENT '计划唯一标识',
    name VARCHAR(200) NOT NULL COMMENT '计划名称',
    description TEXT COMMENT '计划描述',
    subject_ids JSON COMMENT '目标学科ID列表',
    target_count INT DEFAULT 0 COMMENT '目标测试数量',
    completed_count INT DEFAULT 0 COMMENT '已完成数量',
    status ENUM('draft', 'active', 'completed', 'archived') DEFAULT 'draft' COMMENT '状态',
    start_date DATE COMMENT '开始日期',
    end_date DATE COMMENT '结束日期',
    schedule_config JSON COMMENT '调度配置 {type, cron, enabled}',
    ai_generated TINYINT(1) DEFAULT 0 COMMENT '是否AI生成',
    assignee_id INT COMMENT '负责人ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_status (status),
    INDEX idx_assignee (assignee_id),
    INDEX idx_created_at (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划表';
```

### test_plan_datasets 表
```sql
CREATE TABLE test_plan_datasets (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    dataset_id VARCHAR(36) NOT NULL COMMENT '数据集ID',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_dataset (plan_id, dataset_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_dataset_id (dataset_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划-数据集关联表';
```

### test_plan_tasks 表
```sql
CREATE TABLE test_plan_tasks (
    id INT AUTO_INCREMENT PRIMARY KEY,
    plan_id VARCHAR(36) NOT NULL COMMENT '计划ID',
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    task_status ENUM('pending', 'processing', 'completed', 'failed') DEFAULT 'pending' COMMENT '任务状态',
    accuracy DECIMAL(5,4) COMMENT '任务准确率',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_plan_task (plan_id, task_id),
    INDEX idx_plan_id (plan_id),
    INDEX idx_task_id (task_id),
    INDEX idx_task_status (task_status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试计划-批量任务关联表';
```

### daily_statistics 表
```sql
CREATE TABLE daily_statistics (
    id INT AUTO_INCREMENT PRIMARY KEY,
    stat_date DATE NOT NULL COMMENT '统计日期',
    subject_id INT COMMENT '学科ID，NULL表示全部',
    task_count INT DEFAULT 0 COMMENT '任务数',
    homework_count INT DEFAULT 0 COMMENT '作业数',
    question_count INT DEFAULT 0 COMMENT '题目数',
    correct_count INT DEFAULT 0 COMMENT '正确数',
    accuracy DECIMAL(5,4) DEFAULT 0 COMMENT '准确率',
    error_distribution JSON COMMENT '错误类型分布',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    UNIQUE KEY uk_date_subject (stat_date, subject_id),
    INDEX idx_stat_date (stat_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='每日统计缓存表';
```

### error_samples 表
```sql
CREATE TABLE error_samples (
    id INT AUTO_INCREMENT PRIMARY KEY,
    task_id VARCHAR(36) NOT NULL COMMENT '批量任务ID',
    homework_id VARCHAR(50) NOT NULL COMMENT '作业ID',
    question_index VARCHAR(50) NOT NULL COMMENT '题号',
    error_type VARCHAR(50) NOT NULL COMMENT '错误类型',
    base_answer TEXT COMMENT '基准答案',
    base_user TEXT COMMENT '基准用户答案',
    hw_user TEXT COMMENT 'AI识别答案',
    status ENUM('pending', 'analyzed', 'fixed') DEFAULT 'pending' COMMENT '状态',
    notes TEXT COMMENT '分析备注',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_task_id (task_id),
    INDEX idx_error_type (error_type),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='错误样本库';
```

### daily_reports 表
```sql
CREATE TABLE daily_reports (
    id INT AUTO_INCREMENT PRIMARY KEY,
    report_id VARCHAR(36) NOT NULL UNIQUE COMMENT '日报唯一标识',
    report_date DATE NOT NULL COMMENT '日报日期',
    task_completed INT DEFAULT 0 COMMENT '完成任务数',
    task_planned INT DEFAULT 0 COMMENT '计划任务数',
    accuracy DECIMAL(5,4) DEFAULT 0 COMMENT '当日准确率',
    accuracy_change DECIMAL(5,4) DEFAULT 0 COMMENT '准确率变化（与昨日对比）',
    top_errors JSON COMMENT '主要错误类型 Top 5',
    tomorrow_plan JSON COMMENT '明日计划任务列表',
    anomalies JSON COMMENT '异常情况列表',
    ai_summary TEXT COMMENT 'AI生成的总结',
    raw_content TEXT COMMENT '完整日报内容（Markdown）',
    generated_by ENUM('auto', 'manual') DEFAULT 'auto' COMMENT '生成方式',
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    UNIQUE KEY uk_report_date (report_date),
    INDEX idx_report_date (report_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='测试日报表';
```

---

## 需求优先级

| 优先级 | 需求编号 | 说明 |
|--------|----------|------|
| P0-必须 | 1-9 | 基础功能，MVP必需 |
| P1-重要 | 10-16, 29-33 | 高级功能和性能优化 |
| P2-期望 | 17-28 | 分析功能，可迭代开发 |
| P3-可选 | 34 | 代码质量，贯穿开发全程 |

---

## 技术约束

1. **前端**: 原生 JavaScript + CSS，不引入 React/Vue 等框架
2. **图表**: 使用原生 Canvas/SVG 实现，不引入 ECharts/Chart.js
3. **后端**: Flask 蓝图，遵循现有项目结构
4. **数据库**: MySQL，使用 `AppDatabaseService` 操作
5. **AI调用**: 使用 `LLMService.call_deepseek()` 
6. **样式**: 遵循 `ui-style.md` 规范，浅色主题
