# Requirements Document

## Introduction

本系统是一个基于LangChain的智能体，用于从作业图片中提取知识点并生成高质量类题。系统支持批量上传作业图片，通过多模态大模型解析图片内容，提取每道题目的知识点和详细解析，然后利用DeepSeek模型根据知识点解析生成类似题目。系统会自动去重，确保相同知识点不会重复生成类题，并提供多维度的质量控制机制。

## Glossary

- **Homework_Agent**: 基于LangChain构建的智能体，负责协调图片解析和类题生成的完整工作流
- **Multimodal_Model**: 多模态大模型，能够理解图片内容并输出结构化数据
- **Knowledge_Point**: 知识点，从题目中提取的精炼核心概念
- **Knowledge_Analysis**: 知识点解析，对知识点的详细说明和解题思路
- **Similar_Question**: 类题，根据知识点解析生成的相似题目
- **DeepSeek_Model**: DeepSeek大语言模型，用于根据知识点解析生成类题
- **Structured_Data**: 结构化数据，包含题目、知识点、知识点解析的JSON格式数据
- **Difficulty_Level**: 难度等级，分为简单、中等、困难三个级别
- **Question_Type**: 题目类型，如选择题、填空题、计算题、证明题等
- **Subject_Category**: 学科分类，如数学、物理、化学等
- **Knowledge_Hierarchy**: 知识点层级，包含一级知识点和二级知识点的树形结构
- **Excel_Export**: Excel导出文件，所有阶段的输出结果均支持Excel格式导出，便于导入其他系统
- **Model_Config**: 模型配置，用户可为每个处理步骤选择不同的AI模型

## Requirements

### Requirement 1

**User Story:** As a 教师, I want to 上传多张作业图片, so that 系统能够批量处理并提取题目信息。

#### Acceptance Criteria

1. WHEN 用户选择多张图片文件并点击上传按钮 THEN Homework_Agent SHALL 接收所有图片并存储到临时目录
2. WHEN 图片格式不符合要求（非JPG/PNG/JPEG） THEN Homework_Agent SHALL 拒绝该图片并返回格式错误提示
3. WHEN 图片大小超过10MB THEN Homework_Agent SHALL 拒绝该图片并返回大小超限提示
4. WHEN 上传成功 THEN Homework_Agent SHALL 显示已上传图片的预览列表

### Requirement 2

**User Story:** As a 教师, I want to 让系统解析作业图片中的题目, so that 我能获得每道题的知识点和详细解析。

#### Acceptance Criteria

1. WHEN 用户确认开始解析 THEN Homework_Agent SHALL 调用Multimodal_Model对每张图片进行内容识别
2. WHEN Multimodal_Model完成图片解析 THEN Homework_Agent SHALL 输出包含题目内容、Knowledge_Point和Knowledge_Analysis的Structured_Data
3. WHEN 提取Knowledge_Point THEN Homework_Agent SHALL 确保知识点描述精炼，不超过20个字符
4. WHEN 生成Knowledge_Analysis THEN Homework_Agent SHALL 包含解题思路、公式应用和关键步骤说明
5. WHEN 解析完成 THEN Homework_Agent SHALL 同时生成JSON格式数据和Excel_Export文件供用户下载
6. WHEN 提取知识点 THEN Homework_Agent SHALL 识别并标注Subject_Category和Question_Type
7. WHEN 解析题目 THEN Homework_Agent SHALL 评估并标注Difficulty_Level
8. WHEN 存在多个知识点 THEN Homework_Agent SHALL 构建Knowledge_Hierarchy，区分一级和二级知识点
9. WHEN 导出解析结果Excel THEN Homework_Agent SHALL 包含以下列：序号、图片来源、题目内容、学科分类、题目类型、难度等级、一级知识点、二级知识点、知识点解析

### Requirement 3

**User Story:** As a 教师, I want to 确认解析结果后生成类题, so that 我能获得基于相同知识点的练习题。

#### Acceptance Criteria

1. WHEN 用户确认解析结果 THEN Homework_Agent SHALL 启动类题生成流程
2. WHEN 检测到重复的Knowledge_Point THEN Homework_Agent SHALL 仅保留一个知识点用于类题生成，跳过重复项
3. WHEN 生成Similar_Question THEN DeepSeek_Model SHALL 根据Knowledge_Analysis内容生成题目，确保题目与原题考查相同知识点
4. WHEN 类题生成完成 THEN Homework_Agent SHALL 输出包含原题、知识点、知识点解析和类题的完整结果，同时生成Excel_Export文件
5. WHEN 生成类题 THEN DeepSeek_Model SHALL 保持与原题相同的Difficulty_Level
6. WHEN 生成类题 THEN DeepSeek_Model SHALL 保持与原题相同的Question_Type
7. WHEN 生成类题 THEN DeepSeek_Model SHALL 同时生成类题的标准答案和解题步骤
8. WHEN 用户指定生成数量 THEN Homework_Agent SHALL 为每个知识点生成指定数量的类题（默认1道，最多5道）
9. WHEN 导出类题结果Excel THEN Homework_Agent SHALL 包含以下列：序号、知识点、知识点解析、类题内容、类题答案、解题步骤、难度等级、题目类型

### Requirement 4

**User Story:** As a 教师, I want to 导出完整的分析和类题结果, so that 我能用于教学和学生练习并导入其他系统。

#### Acceptance Criteria

1. WHEN 用户请求导出 THEN Homework_Agent SHALL 生成包含所有数据的Excel_Export文件
2. WHEN 导出完整Excel THEN Homework_Agent SHALL 包含以下列：序号、图片来源、原题内容、学科分类、题目类型、难度等级、一级知识点、二级知识点、知识点解析、类题内容、类题答案、解题步骤
3. WHEN 导出完成 THEN Homework_Agent SHALL 提供文件下载链接
4. WHEN 用户选择分阶段导出 THEN Homework_Agent SHALL 支持单独导出解析结果Excel或类题结果Excel
5. WHEN 导出Excel THEN Homework_Agent SHALL 确保Excel格式兼容主流系统导入（支持xlsx格式）

### Requirement 5

**User Story:** As a 开发者, I want to 系统能够正确序列化和反序列化数据, so that 数据在存储和传输过程中保持完整。

#### Acceptance Criteria

1. WHEN 保存Structured_Data到文件 THEN Homework_Agent SHALL 使用JSON格式编码数据
2. WHEN 读取已保存的数据 THEN Homework_Agent SHALL 正确解析JSON并还原为原始数据结构
3. WHEN 序列化后再反序列化 THEN Homework_Agent SHALL 确保数据与原始数据完全一致（round-trip一致性）

### Requirement 6

**User Story:** As a 教师, I want to 查看处理进度, so that 我能了解系统当前的工作状态。

#### Acceptance Criteria

1. WHEN 图片解析进行中 THEN Homework_Agent SHALL 显示当前处理进度（已处理/总数）
2. WHEN 类题生成进行中 THEN Homework_Agent SHALL 显示当前生成进度和预计剩余时间
3. IF 处理过程中发生错误 THEN Homework_Agent SHALL 显示错误信息并允许用户重试该步骤

### Requirement 7

**User Story:** As a 教师, I want to 对生成的类题进行质量控制, so that 确保类题的准确性和教学价值。

#### Acceptance Criteria

1. WHEN 类题生成完成 THEN Homework_Agent SHALL 对类题进行自动质量评估
2. WHEN 质量评估 THEN Homework_Agent SHALL 检查类题是否覆盖Knowledge_Analysis中的核心考点
3. WHEN 质量评估 THEN Homework_Agent SHALL 验证类题答案的正确性
4. WHEN 用户对类题不满意 THEN Homework_Agent SHALL 支持重新生成该知识点的类题
5. WHEN 用户编辑类题 THEN Homework_Agent SHALL 保存用户修改并更新导出数据

### Requirement 8

**User Story:** As a 教师, I want to 管理知识点去重规则, so that 我能控制哪些知识点需要合并或区分。

#### Acceptance Criteria

1. WHEN 检测知识点相似度 THEN Homework_Agent SHALL 使用语义相似度算法判断知识点是否重复
2. WHEN 相似度超过阈值（默认0.85） THEN Homework_Agent SHALL 将知识点标记为重复
3. WHEN 显示重复知识点 THEN Homework_Agent SHALL 允许用户手动确认是否合并
4. WHEN 用户调整相似度阈值 THEN Homework_Agent SHALL 重新计算知识点去重结果
5. WHEN 导出去重结果 THEN Homework_Agent SHALL 生成Excel_Export文件，包含：原知识点、合并后知识点、相似度分数、是否合并

### Requirement 9

**User Story:** As a 教师, I want to 为每个处理步骤选择不同的AI模型, so that 我能根据需求和成本灵活配置系统。

#### Acceptance Criteria

1. WHEN 用户进入图片解析步骤 THEN Homework_Agent SHALL 显示可用的Multimodal_Model列表供用户选择
2. WHEN 用户进入类题生成步骤 THEN Homework_Agent SHALL 显示可用的文本生成模型列表供用户选择
3. WHEN 用户选择模型 THEN Homework_Agent SHALL 保存用户的模型偏好设置
4. WHEN 系统启动 THEN Homework_Agent SHALL 加载用户上次选择的模型作为默认值
5. WHEN 显示模型列表 THEN Homework_Agent SHALL 展示每个模型的名称、提供商和简要说明
6. WHEN 模型调用失败 THEN Homework_Agent SHALL 提示用户切换到其他可用模型

### Requirement 10

**User Story:** As a 教师, I want to 从主界面快速访问知识点类题生成功能, so that 我能方便地使用该功能。

#### Acceptance Criteria

1. WHEN 用户访问主界面 THEN Homework_Agent SHALL 在左侧边栏底部显示"知识点类题"入口链接
2. WHEN 用户点击"知识点类题"链接 THEN Homework_Agent SHALL 跳转到独立的知识点类题生成页面
3. WHEN 用户访问知识点类题页面 THEN Homework_Agent SHALL 显示与主界面配色和风格一致的UI界面
4. WHEN 用户在知识点类题页面 THEN Homework_Agent SHALL 提供返回主界面的导航链接
5. WHEN 用户在知识点类题页面 THEN Homework_Agent SHALL 复用主界面的模型配置和API设置

### Requirement 11

**User Story:** As a 教师, I want to 通过清晰的步骤流程完成知识点类题生成, so that 我能直观地了解当前进度并方便操作。

#### Acceptance Criteria

1. WHEN 用户进入知识点类题页面 THEN Homework_Agent SHALL 显示智能体工作流程步骤指示器（步骤1:上传图片 → 步骤2:解析题目 → 步骤3:确认知识点 → 步骤4:生成类题 → 步骤5:导出结果）
2. WHEN 用户处于某个步骤 THEN Homework_Agent SHALL 高亮显示当前步骤，并灰显未完成的后续步骤
3. WHEN 用户完成当前步骤 THEN Homework_Agent SHALL 自动切换到下一步骤的操作界面
4. WHEN 用户需要返回上一步骤 THEN Homework_Agent SHALL 提供返回按钮，允许用户修改之前的操作
5. WHEN 显示每个步骤界面 THEN Homework_Agent SHALL 提供清晰的操作按钮和说明文字
6. WHEN 用户在步骤2解析完成 THEN Homework_Agent SHALL 显示解析结果表格，支持在线预览和编辑
7. WHEN 用户在步骤3确认知识点 THEN Homework_Agent SHALL 显示知识点去重结果，支持勾选确认
8. WHEN 用户在步骤4生成类题 THEN Homework_Agent SHALL 显示生成进度和实时预览
9. WHEN 用户在步骤5导出结果 THEN Homework_Agent SHALL 提供多种导出选项（解析结果Excel、类题结果Excel、完整结果Excel）
