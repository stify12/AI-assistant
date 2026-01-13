# Requirements Document

## Introduction

本功能将现有的"AI对比分析"页面重构为"AI学科批改评估"页面，按学科（英语、语文、数学、物理）分类展示AI批改效果评估。系统从MySQL数据库获取最近一小时的AI批改结果，用户可选择数据后上传图片识别基准效果，通过DeepSeek大模型评估AI批改输出是否与基准效果一致。

## Glossary

- **Subject_Grading_Evaluation_System**: AI学科批改评估系统，用于评估AI批改作业的准确性
- **Base_Effect**: 基准效果，用户通过图片识别或手动输入的标准批改结果，AI输出需与此完全一致才算准确
- **Homework_Result**: AI批改结果，从数据库zp_homework表获取的批改数据
- **Subject**: 学科，包括英语(0)、语文(1)、数学(2)、物理(3)
- **Evaluation_Result**: 评估结果，DeepSeek对比基准效果和AI批改结果后的分析报告

## Requirements

### Requirement 1: 数据库批改数据获取

**User Story:** As a 测试人员, I want to 自动获取最近一小时的AI批改数据, so that 我可以快速选择需要评估的作业记录。

#### Acceptance Criteria

1. WHEN 用户进入学科Tab页面 THEN the Subject_Grading_Evaluation_System SHALL 自动查询该学科最近1小时内status=3的批改记录
2. WHEN 数据库返回批改记录 THEN the Subject_Grading_Evaluation_System SHALL 以表格形式展示记录列表（包含ID、学生ID、页码、创建时间、题目数量）
3. WHEN 用户点击某条记录 THEN the Subject_Grading_Evaluation_System SHALL 展示该记录的详细批改结果JSON数据
4. WHEN 数据库查询失败 THEN the Subject_Grading_Evaluation_System SHALL 显示错误提示并提供重试按钮
5. WHEN 查询结果为空 THEN the Subject_Grading_Evaluation_System SHALL 显示"暂无批改数据"的空状态提示

### Requirement 2: 学科Tab分类展示

**User Story:** As a 测试人员, I want to 按学科分类查看批改数据, so that 我可以针对不同学科进行独立评估。

#### Acceptance Criteria

1. WHEN 页面加载完成 THEN the Subject_Grading_Evaluation_System SHALL 显示四个学科Tab（英语、语文、数学、物理）
2. WHEN 用户切换学科Tab THEN the Subject_Grading_Evaluation_System SHALL 加载对应学科的批改数据列表
3. WHEN 用户在某学科Tab操作 THEN the Subject_Grading_Evaluation_System SHALL 保持该Tab的状态直到用户切换

### Requirement 3: 基准效果图片识别

**User Story:** As a 测试人员, I want to 上传作业图片让AI识别基准效果, so that 我可以快速获取标准批改结果用于评估。

#### Acceptance Criteria

1. WHEN 用户上传作业图片 THEN the Subject_Grading_Evaluation_System SHALL 调用AI视觉模型识别图片中的答案并生成基准效果JSON
2. WHEN AI识别完成 THEN the Subject_Grading_Evaluation_System SHALL 以可编辑的模块化JSON形式展示识别结果
3. WHEN 用户修改识别结果 THEN the Subject_Grading_Evaluation_System SHALL 实时更新基准效果数据
4. WHEN 图片识别失败 THEN the Subject_Grading_Evaluation_System SHALL 显示错误信息并允许重新上传

### Requirement 4: 基准效果模块化编辑

**User Story:** As a 测试人员, I want to 以模块化方式编辑基准效果, so that 我可以方便地修改每道题的标准批改结果。

#### Acceptance Criteria

1. WHEN 基准效果加载完成 THEN the Subject_Grading_Evaluation_System SHALL 以卡片形式展示每道题的批改信息（answer、correct、index、tempIndex、userAnswer）
2. WHEN 用户点击某题卡片 THEN the Subject_Grading_Evaluation_System SHALL 允许编辑该题的answer、correct、userAnswer、mainAnswer字段
3. WHEN 用户添加新题目 THEN the Subject_Grading_Evaluation_System SHALL 创建新的题目卡片并自动分配index和tempIndex
4. WHEN 用户删除题目 THEN the Subject_Grading_Evaluation_System SHALL 移除对应卡片并重新排序题号

### Requirement 5: AI评估对比分析

**User Story:** As a 测试人员, I want to 使用DeepSeek评估AI批改是否与基准效果一致, so that 我可以发现AI批改的错误和问题。

#### Acceptance Criteria

1. WHEN 用户选择批改记录并设置基准效果后点击评估 THEN the Subject_Grading_Evaluation_System SHALL 调用DeepSeek进行对比分析
2. WHEN DeepSeek评估完成 THEN the Subject_Grading_Evaluation_System SHALL 显示评估报告（包含准确率、错误题目列表、错误类型分析）
3. WHEN AI批改结果的格式或内容与基准效果不一致 THEN the Subject_Grading_Evaluation_System SHALL 标记该题为批改错误
4. WHEN 评估过程出错 THEN the Subject_Grading_Evaluation_System SHALL 显示错误信息并允许重新评估

### Requirement 6: 评估结果可视化

**User Story:** As a 测试人员, I want to 以丰富的可视化方式查看评估结果, so that 我可以直观了解AI批改的效果并进行多维度分析。

#### Acceptance Criteria

1. WHEN 评估完成 THEN the Subject_Grading_Evaluation_System SHALL 显示准确率统计卡片（正确数/总数/准确率百分比/精确率/召回率/F1值）
2. WHEN 存在批改错误 THEN the Subject_Grading_Evaluation_System SHALL 以表格形式展示错误题目详情（题号、基准效果、AI批改结果、错误类型）
3. WHEN 用户点击错误题目 THEN the Subject_Grading_Evaluation_System SHALL 高亮显示该题在基准效果和批改结果中的对比
4. WHEN 评估完成 THEN the Subject_Grading_Evaluation_System SHALL 显示准确率折线图展示批次准确率变化趋势
5. WHEN 评估完成 THEN the Subject_Grading_Evaluation_System SHALL 显示错误类型饼图展示各类错误的分布占比
6. WHEN 评估完成 THEN the Subject_Grading_Evaluation_System SHALL 显示评分偏差热力图展示题目维度的批改偏差分布
7. WHEN 用户操作图表 THEN the Subject_Grading_Evaluation_System SHALL 支持图表缩放、导出PNG/SVG、自定义维度切换
8. WHEN 有多次评估记录 THEN the Subject_Grading_Evaluation_System SHALL 支持多记录对比展示在同一图表中

### Requirement 7: DeepSeek��估模型集成

**User Story:** As a 测试人员, I want to 使用DeepSeek作为评估模型, so that 我可以获得专业的AI批改效果分析。

#### Acceptance Criteria

1. WHEN 用户发起评估请求 THEN the Subject_Grading_Evaluation_System SHALL 调用DeepSeek模型进行基准效果与AI批改结果的对比分析
2. WHEN DeepSeek分析完成 THEN the Subject_Grading_Evaluation_System SHALL 返回结构化的评估报告（包含错误分类、错误原因、改进建议）
3. WHEN DeepSeek识别到错误 THEN the Subject_Grading_Evaluation_System SHALL 将错误分类为：识别错误、判断错误、格式错误、其他错误
4. WHEN DeepSeek调用失败 THEN the Subject_Grading_Evaluation_System SHALL 显示错误信息并提供重试选项

### Requirement 8: 评估记录保存

**User Story:** As a 测试人员, I want to 保存评估记录, so that 我可以后续查看历史评估结果。

#### Acceptance Criteria

1. WHEN 评估完成 THEN the Subject_Grading_Evaluation_System SHALL 提供保存评估记录的按钮
2. WHEN 用户点击保存 THEN the Subject_Grading_Evaluation_System SHALL 将评估结果存储到本地（包含学科、时间、准确率、详细数据）
3. WHEN 用户查看历史记录 THEN the Subject_Grading_Evaluation_System SHALL 按学科和时间筛选展示历史评估记录
