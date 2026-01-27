# Requirements Document

## Introduction

本需求文档定义了 AI 智能分析功能的增强优化，核心目标是通过调用 LLM 大模型对批量评估数据进行深度分析，生成有价值、可读性强的分析数据，作为测试看板高级分析工具（错误样本库、异常检测、错误聚类、优化建议、批次对比、数据下钻）的数据底座。

**核心原则：全程 LLM 分析**
- 所有分析结果必须通过 LLM 大模型生成，不使用本地规则或硬编码逻辑
- 错误分类、根因分析、聚类命名、优化建议等全部由 LLM 动态生成
- 确保分析结果的智能性、准确性和可读性

## Glossary

- **AI_Analysis_Engine**: AI 分析引擎，负责调用 LLM 进行深度分析
- **Error_Sample**: 错误样本，批量评估中识别出的 AI 批改错误
- **LLM_Insight**: LLM 洞察，大模型分析后生成的结构化分析结果
- **Error_Cluster**: 错误聚类，按语义相似度归类的错误样本组
- **Anomaly_Detection**: 异常检测，识别评分异常模式
- **Optimization_Suggestion**: 优化建议，基于分析结果生成的改进方案
- **Analysis_Report**: 分析报告，包含所有分析结果的完整报告

## Requirements

### Requirement 1: LLM 深度错误分析（聚类优先）

**User Story:** As a 测试人员, I want to 错误样本经过智能聚类后由 LLM 深度分析, so that I can 高效了解错误的具体原因和改进方向。

#### Acceptance Criteria

1. WHEN 批量评估任务完成后触发分析, THE AI_Analysis_Engine SHALL 先对错误样本进行初步聚类，再对每个聚类调用 LLM 进行深度分析
2. THE 初步聚类 SHALL 基于以下特征自动分组（本地预处理，减少 LLM 调用次数）：
   - error_type: 错误类型（答案不匹配/缺失题目/等）
   - book_name: 书本名称
   - page_num: 页码范围
   - question_pattern: 题目模式（选择题/填空题/主观题
3. WHEN 对聚类进行 LLM 分析, THE LLM_Insight SHALL 由 LLM 动态生成以下字段：
   - cluster_category: 聚类错误大类（LLM 根据聚类内样本智能判断）
   - cluster_subcategory: 聚类错误子类（LLM 根据聚类内样本智能细分）
   - root_cause: 根因分析（LLM 生成的描述导致这类错误的根本原因）
   - confidence: 分析置信度（high/medium/low）
   - fix_suggestion: 修复建议（LLM 针对该类错误生成的具体改进建议）
   - readable_summary: 可读摘要（LLM 生成的人类可读的聚类描述）
   - sample_count: 该聚类包含的样本数量
   - representative_samples: 代表性样本（最多 3 个，用于展示）
4. THE AI_Analysis_Engine SHALL 将聚类的分析结果继承给聚类内的所有样本
5. IF LLM 调用失败, THEN THE AI_Analysis_Engine SHALL 重试最多 3 次，仍失败则标记为 analysis_failed
6. THE AI_Analysis_Engine SHALL 记录每个聚类的分析耗时和 token 消耗
7. THE LLM_Insight SHALL 完全由 LLM 生成，不使用任何本地规则或硬编码映射

### Requirement 2: 智能错误聚类（二次聚类）

**User Story:** As a 测试人员, I want to 错误样本按语义相似度进行二次智能聚类, so that I can 快速发现批量出现的同类问题。

#### Acceptance Criteria

1. WHEN 初步聚类分析完成后, THE AI_Analysis_Engine SHALL 调用 LLM 对所有初步聚类进行二次智能聚类
2. THE 二次聚类 SHALL 由 LLM 基于初步聚类的分析结果进行语义合并，将相似问题归为一类
3. WHEN 生成二次聚类, THE Error_Cluster SHALL 包含（全部由 LLM 生成）：
   - cluster_id: 聚类ID
   - cluster_name: 聚类名称（LLM 生成的可读名称，如"物理力学题手写体识别问题"）
   - cluster_description: 聚类描述（LLM 生成的问题描述，说明这类错误的共同特征）
   - merged_from: 合并自哪些初步聚类
   - sample_count: 样本数量
   - severity: 严重程度（LLM 基于数量和影响智能判断）
   - representative_samples: 代表性样本（LLM 选择最具代表性的最多3个）
   - common_fix: 通用修复建议（LLM 生成的针对该聚类的改进方案）
   - pattern_insight: 模式洞察（LLM 生成的对该类错误的深度分析）
4. THE AI_Analysis_Engine SHALL 由 LLM 识别并排序最严重的聚类
5. WHEN 二次聚类数量过多, THE AI_Analysis_Engine SHALL 调用 LLM 进一步合并语义相似的聚类
6. THE 聚类逻辑 SHALL 完全由 LLM 驱动，不使用预定义的聚类规则

### Requirement 3: 异常模式检测

**User Story:** As a 测试人员, I want to 自动检测评分异常模式, so that I can 及时发现系统性问题。

#### Acceptance Criteria

1. WHEN 分析批量评估数据, THE Anomaly_Detection SHALL 检测以下异常：
   - 连续错误：同一页码连续 3 题以上错误
   - 批量缺失：同一作业超过 50% 题目缺失
   - 评分偏差：AI 评分与期望评分差异超过阈值
   - 识别异常：同一答案在不同作业中识别结果不一致
   - 时间异常：单题评估时间异常（过长或过短）
2. WHEN 检测到异常, THE Anomaly_Detection SHALL 生成异常记录：
   - anomaly_id: 异常ID
   - anomaly_type: 异常类型
   - severity: 严重程度（critical/warning/info）
   - description: 异常描述（LLM 生成的可读描述）
   - affected_items: 受影响的作业/题目列表
   - suggested_action: 建议操作
3. THE Anomaly_Detection SHALL 按严重程度排序异常列表
4. WHEN 检测到 critical 级别异常, THE Dashboard SHALL 显示醒目提示

### Requirement 4: 智能优化建议生成

**User Story:** As a 测试人员, I want to 获得 LLM 生成的具体优化建议, so that I can 快速改进 AI 批改效果。

#### Acceptance Criteria

1. WHEN 分析完成后, THE AI_Analysis_Engine SHALL 调用 LLM 生成优化建议
2. THE Optimization_Suggestion SHALL 包含：
   - suggestion_id: 建议ID
   - title: 建议标题（简洁明了）
   - category: 建议类别（Prompt优化/数据集优化/评分逻辑优化/OCR优化）
   - description: 详细描述（具体的改进方案）
   - priority: 优先级（P0/P1/P2）
   - expected_impact: 预期效果（如"预计可减少 30% 的识别错误"）
   - implementation_steps: 实施步骤（具体操作步骤列表）
   - related_clusters: 关联的错误聚类
   - prompt_template: 如果是 Prompt 优化，提供具体的 Prompt 修改建议
3. THE AI_Analysis_Engine SHALL 最多生成 5 条高价值建议
4. THE Optimization_Suggestion SHALL 按优先级和预期效果排序
5. WHEN 建议涉及 Prompt 修改, THE AI_Analysis_Engine SHALL 提供修改前后对比

### Requirement 5: 多维度数据下钻

**User Story:** As a 测试人员, I want to 从多个维度下钻分析数据, so that I can 精准定位问题。

#### Acceptance Criteria

1. THE AI_Analysis_Engine SHALL 支持以下下钻维度：
   - 学科维度：学科 → 书本 → 页码 → 题目
   - 错误类型维度：错误大类 → 错误子类 → 具体样本
   - 时间维度：日期 → 任务 → 作业 → 题目
   - 题型维度：题型 → 学科 → 具体样本
2. WHEN 下钻到任意层级, THE Dashboard SHALL 显示：
   - 该层级的统计数据（总数、错误数、错误率）
   - 错误类型分布（饼图数据）
   - 严重程度分布
   - 代表性错误样本
3. THE AI_Analysis_Engine SHALL 为每个层级生成 LLM 摘要（一句话总结该层级的主要问题）
4. WHEN 某层级错误率超过 20%, THE Dashboard SHALL 标记为重点关注

### Requirement 6: 批次对比分析

**User Story:** As a 测试人员, I want to 对比不同批次的评估结果, so that I can 了解改进效果。

#### Acceptance Criteria

1. WHEN 用户选择两个批次进行对比, THE AI_Analysis_Engine SHALL 调用 LLM 生成对比报告
2. THE 对比报告 SHALL 完全由 LLM 生成，包含：
   - comparison_summary: 对比总结（LLM 生成的整体对比分析）
   - accuracy_analysis: 准确率分析（LLM 分析整体、按学科、按题型的变化及原因）
   - error_pattern_changes: 错误模式变化（LLM 识别新增/减少的错误模式并分析原因）
   - improvement_items: 改进项（LLM 识别并描述具体改进的地方）
   - regression_items: 退步项（LLM 识别并描述退步的地方）
   - root_cause_analysis: 变化根因分析（LLM 深度分析导致改进或退步的根本原因）
   - recommendations: 后续建议（LLM 基于对比结果生成的改进建议）
3. THE AI_Analysis_Engine SHALL 由 LLM 智能判断改进率和退步率，并给出置信度
4. WHEN 有显著改进或退步, THE AI_Analysis_Engine SHALL 由 LLM 生成详细的原因分析
5. THE 对比分析 SHALL 完全由 LLM 驱动，不使用硬编码的对比规则

### Requirement 7: 错误样本库管理

**User Story:** As a 测试人员, I want to 管理和标注错误样本, so that I can 跟踪问题处理进度。

#### Acceptance Criteria

1. THE Error_Sample SHALL 包含以下状态：
   - pending: 待分析（新发现的错误）
   - analyzed: 已分析（LLM 已分析但未处理）
   - in_progress: 处理中（正在修复）
   - fixed: 已修复（问题已解决）
   - ignored: 已忽略（非问题或无法修复）
2. WHEN 查看错误样本, THE Dashboard SHALL 显示：
   - 样本基本信息（作业、题目、学科、页码）
   - AI 批改结果 vs 期望结果
   - LLM 分析结果（错误类型、根因、建议）
   - 所属聚类
   - 处理状态和历史
3. THE Dashboard SHALL 支持批量操作（批量标记状态、批量忽略）
4. THE Dashboard SHALL 支持按多条件筛选（状态、错误类型、学科、严重程度）

### Requirement 8: 分析报告可视化

**User Story:** As a 测试人员, I want to 查看可视化的分析报告, so that I can 快速了解整体情况。

#### Acceptance Criteria

1. THE Analysis_Report SHALL 包含以下可视化模块：
   - 概览卡片：总错误数、错误率、待处理数、已修复数
   - 错误类型分布：饼图展示各类错误占比
   - 错误趋势：折线图展示错误率变化趋势
   - 热点图：按学科×题型展示错误分布
   - Top 5 问题聚类：卡片列表展示最严重的问题
   - 优化建议：按优先级排列的建议列表
2. THE Dashboard SHALL 支持导出报告（PDF/Excel）
3. WHEN 有高优先级问题, THE Dashboard SHALL 在首页显示提醒
4. THE Analysis_Report SHALL 包含 LLM 生成的执行摘要（3-5 句话总结）

### Requirement 9: 分析配置管理

**User Story:** As a 管理员, I want to 配置分析参数, so that I can 控制分析成本。

#### Acceptance Criteria

1. THE Automation_Panel SHALL 支持配置：
   - LLM 模型选择：DeepSeek V3.2 / Qwen3 Max
   - 批量分析大小：每批分析的样本数（默认 20）
   - 分析超时时间：单个样本的最大分析时间
   - 自动触发：是否在任务完成后自动触发分析
   - 成本控制：每日最大 token 消耗限制
   - 分析温度：LLM 生成的随机性控制（0.1-1.0）
2. THE Dashboard SHALL 显示分析成本统计（token 消耗、API 调用次数、平均分析耗时）
3. WHEN 达到成本限制, THE AI_Analysis_Engine SHALL 暂停分析并通知管理员
4. THE 分析模式 SHALL 始终为 LLM 深度分析模式，不提供规则模式选项

### Requirement 10: 高级分析工具数据接口

**User Story:** As a 开发者, I want to 高级分析工具能获取完整的分析数据, so that I can 展示丰富的分析结果。

#### Acceptance Criteria

1. THE AI_Analysis_Engine SHALL 为高级分析工具提供以下数据接口：
   - 错误样本库：GET /api/analysis/samples（支持分页、筛选、排序）
   - 错误聚类：GET /api/analysis/clusters（聚类列表及详情）
   - 异常检测：GET /api/analysis/anomalies（异常列表及详情）
   - 优化建议：GET /api/analysis/suggestions（建议列表及详情）
   - 数据下钻：GET /api/analysis/drilldown（多维度下钻数据）
   - 批次对比：GET /api/analysis/compare（两个批次的对比数据）
   - 统计概览：GET /api/analysis/stats（各模块的统计数据）
2. THE API SHALL 返回 LLM 生成的可读描述和摘要
3. THE API SHALL 支持增量更新（只返回变化的数据）
4. THE API SHALL 包含数据更新时间戳
