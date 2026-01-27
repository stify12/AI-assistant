# Requirements Document

## Introduction

本需求文档定义了 AI 智能数据分析功能，通过接入大模型对批量评估数据进行深度分析，自动识别错误模式、分析根因、生成优化建议。系统在批量评估任务完成后自动触发分析，支持多层级粒度（学科→书本→页码→题目），帮助用户精准定位问题并改进 AI 批改效果。

## Glossary

- **AI_Analysis_Service**: AI 数据分析服务，负责调用大模型分析数据
- **Error_Pattern**: 错误模式，从错误样本中识别出的规律性问题
- **Root_Cause**: 根因，导致错误的底层原因（OCR问题/评分逻辑/标准答案等）
- **Insight**: 洞察，大模型分析后生成的有价值发现
- **Optimization_Suggestion**: 优化建议，基于分析结果生成的改进方案
- **Analysis_Report**: 分析报告，包含错误模式、根因、建议的完整报告
- **Drill_Down**: 下钻分析，从学科→书本→页码→题目的层级分析

## Requirements

### Requirement 1: 任务完成自动分析

**User Story:** As a 测试人员, I want to 批量评估任务完成后自动触发分析, so that I can 立即获得该任务的分析结果。

#### Acceptance Criteria

1. WHEN 批量评估任务状态变为 completed, THE AI_Analysis_Service SHALL 自动触发该任务的数据分析
2. WHEN 分析触发, THE AI_Analysis_Service SHALL 收集该任务的所有错误样本数据
3. WHEN 分析完成, THE AI_Analysis_Service SHALL 将结果关联到该批量评估任务
4. WHEN 分析完成, THE Dashboard SHALL 自动更新显示最新分析结果
5. IF 分析过程出错, THEN THE AI_Analysis_Service SHALL 记录错误日志并支持手动重试
6. THE AI_Analysis_Service SHALL 支持并发分析多个任务（队列机制）

### Requirement 2: 多层级粒度分析

**User Story:** As a 测试人员, I want to 按学科→书本→页码→题目层级分析错误, so that I can 精准定位到具体哪本书的哪些页面问题最多。

#### Acceptance Criteria

1. WHEN 分析错误样本, THE AI_Analysis_Service SHALL 按以下层级聚合统计：
   - 第一层：学科（语文/数学/英语/物理/化学/生物/地理）
   - 第二层：书本（如"物理八上"）
   - 第三层：页码（如"P97-98"）
   - 第四层：题目（如"第5题"）
2. WHEN 展示分析结果, THE Dashboard SHALL 支持逐层下钻查看
3. THE Analysis_Report SHALL 标识每个层级的错误数量和错误率
4. WHEN 某层级错误率超过阈值（20%）, THE Analysis_Report SHALL 标记为重点关注
5. THE Analysis_Report SHALL 识别错误最集中的 Top 5 位置（精确到页码级别）

### Requirement 3: 错误模式识别

**User Story:** As a 测试人员, I want to 自动识别错误样本中的规律, so that I can 针对性地改进批改效果。

#### Acceptance Criteria

1. WHEN 分析错误样本, THE AI_Analysis_Service SHALL 识别以下错误类型的分布：
   - 识别错误-判断错误（OCR 识别问题导致）
   - 识别正确-判断错误（评分逻辑问题）
   - 缺失题目（题目未被识别）
   - AI识别幻觉（识别出不存在的内容）
   - 答案不匹配（标准答案问题）
2. WHEN 分析完成, THE AI_Analysis_Service SHALL 识别出现频率最高的错误模式（Top 5）
3. WHEN 识别到错误模式, THE AI_Analysis_Service SHALL 生成该模式的描述
4. THE Analysis_Report SHALL 包含每种错误模式的具体样本示例（最多3个）
5. THE Analysis_Report SHALL 包含错误模式的严重程度评级（高/中/低）

### Requirement 4: 根因分析

**User Story:** As a 测试人员, I want to 了解错误的根本原因, so that I can 从源头解决问题。

#### Acceptance Criteria

1. WHEN 分析错误样本, THE AI_Analysis_Service SHALL 调用大模型分析每类错误的根因
2. THE Root_Cause SHALL 分为以下类别：
   - OCR识别问题：手写体识别差、图片质量低、特殊符号识别错误
   - 评分逻辑问题：评分标准不清晰、部分得分判断错误、等价答案未覆盖
   - 标准答案问题：标准答案有误、答案格式不统一、多解情况未考虑
   - Prompt问题：指令不够明确、缺少特定场景处理、格式要求不清晰
   - 数据问题：数据集标注错误、题目信息缺失
3. WHEN 识别到根因, THE AI_Analysis_Service SHALL 提供具体的证据（错误样本对比）
4. THE Analysis_Report SHALL 按根因类别统计错误数量占比
5. WHEN 某根因占比超过 30%, THE Analysis_Report SHALL 标记为主要问题

### Requirement 5: 智能优化建议

**User Story:** As a 测试人员, I want to 获得 AI 生成的优化建议, so that I can 快速找到改进方向。

#### Acceptance Criteria

1. WHEN 分析完成, THE AI_Analysis_Service SHALL 基于错误模式和根因生成优化建议
2. THE Optimization_Suggestion SHALL 包含：
   - 标题：简洁描述建议内容
   - 详细描述：具体的改进方案
   - 优先级：高/中/低
   - 预期效果：预计可减少的错误数量或提升的准确率
   - 关联根因：该建议针对哪个根因
3. WHEN 建议涉及 prompt 优化, THE AI_Analysis_Service SHALL 提供具体的修改建议文本
4. THE AI_Analysis_Service SHALL 按优先级和预期效果排序建议
5. THE Analysis_Report SHALL 最多生成 5 条优化建议（聚焦最重要的问题）

### Requirement 6: 分析报告展示

**User Story:** As a 测试人员, I want to 在看板查看分析报告, so that I can 快速了解问题和改进方向。

#### Acceptance Criteria

1. WHEN 批量评估任务有分析结果, THE Dashboard SHALL 在任务详情中显示分析入口
2. WHEN 用户点击查看分析, THE Dashboard SHALL 显示完整的分析报告弹窗
3. THE Analysis_Report SHALL 包含以下模块：
   - 概览：总错误数、错误率、主要问题摘要
   - 层级分析：可下钻的学科→书本→页码→题目统计
   - 错误模式：Top 5 错误模式及示例
   - 根因分析：根因分布饼图及详情
   - 优化建议：按优先级排列的建议列表
4. WHEN 有高优先级建议, THE Dashboard SHALL 在任务列表中显示提示标记
5. THE Dashboard SHALL 支持导出分析报告（JSON/Excel）

### Requirement 7: 手动触发分析

**User Story:** As a 测试人员, I want to 手动触发或重新分析, so that I can 在需要时获得最新分析结果。

#### Acceptance Criteria

1. WHEN 用户点击"重新分析"按钮, THE AI_Analysis_Service SHALL 重新执行该任务的分析
2. WHEN 分析进行中, THE Dashboard SHALL 显示分析进度状态
3. WHEN 分析完成, THE Dashboard SHALL 自动刷新显示最新结果
4. IF 已有分析任务在执行, THEN THE AI_Analysis_Service SHALL 将新请求加入队列
5. THE Dashboard SHALL 显示分析队列状态（等待中/分析中/已完成）

### Requirement 8: 自动化任务管理界面

**User Story:** As a 管理员, I want to 查看和管理系统所有自动化任务, so that I can 了解系统运行状态并进行配置调整。

#### Acceptance Criteria

1. THE Dashboard SHALL 提供"自动化管理"入口，显示所有自动化任务列表
2. THE Automation_Panel SHALL 显示以下任务类型：
   - AI 数据分析任务
   - 日报自动生成任务
   - 统计快照任务
   - 其他定时任务
3. WHEN 查看任务列表, THE Automation_Panel SHALL 显示每个任务的：
   - 任务名称和描述
   - 触发方式（事件触发/定时触发/手动触发）
   - 当前状态（启用/禁用/运行中/等待中）
   - 上次执行时间和结果（成功/失败）
   - 下次计划执行时间
   - 执行次数统计（今日/本周/本月）
4. WHEN 用户点击任务详情, THE Automation_Panel SHALL 显示：
   - 任务配置参数
   - 执行历史记录（最近 50 条）
   - 错误日志（如有）
   - 性能统计（平均执行时长、成功率）

### Requirement 9: 自动化任务配置

**User Story:** As a 管理员, I want to 配置自动化任务的执行参数, so that I can 根据需求调整任务行为。

#### Acceptance Criteria

1. THE Automation_Panel SHALL 支持配置 AI 数据分析任务：
   - 启用/禁用自动分析
   - 分析触发延迟（任务完成后等待 N 秒再分析，默认 10 秒）
   - 并发分析数量限制（默认 2）
   - 分析超时时间（默认 300 秒）
   - 大模型选择（DeepSeek V3.2 / Qwen3 Max）
   - Temperature 参数（0-1，默认 0.3）
   - 分析深度（仅错误模式 / 含根因分析 / 完整分析）
2. THE Automation_Panel SHALL 支持配置日报生成任务：
   - 启用/禁用自动生成
   - 生成时间（cron 表达式，默认每天 18:00）
   - 日报内容范围（当日/自定义时间范围）
3. THE Automation_Panel SHALL 支持配置统计快照任务：
   - 启用/禁用
   - 快照时间（cron 表达式，默认每天 00:00）
   - 保留天数（默认 30 天）
4. WHEN 配置变更, THE Automation_Panel SHALL 立即生效（无需重启服务）
5. THE Automation_Panel SHALL 支持导出/导入配置（JSON 格式）

### Requirement 10: 任务执行监控

**User Story:** As a 管理员, I want to 实时监控任务执行情况, so that I can 及时发现和处理问题。

#### Acceptance Criteria

1. THE Automation_Panel SHALL 显示任务队列实时状态：
   - 等待中的任务数量
   - 正在执行的任务列表
   - 最近完成的任务（最近 10 条）
2. WHEN 任务执行失败, THE Automation_Panel SHALL 显示错误提示并支持：
   - 查看错误详情
   - 手动重试
   - 跳过该任务
3. THE Automation_Panel SHALL 支持以下操作：
   - 暂停所有自动任务
   - 恢复所有自动任务
   - 清空等待队列
   - 强制停止正在执行的任务
4. WHEN 任务执行时间超过阈值（如 5 分钟）, THE Automation_Panel SHALL 显示警告
5. THE Automation_Panel SHALL 提供任务执行统计图表：
   - 每日执行次数趋势
   - 成功/失败比例
   - 平均执行时长趋势

