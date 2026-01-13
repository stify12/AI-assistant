# Requirements Document

## Introduction

AI批改效果分析平台是一款面向AI批改产品的专业评测工具，通过上传数据与AI批改结果，结合多维度评估指标和可视化手段，量化分析AI批改的准确性、效率、资源消耗等核心维度。平台支持实时调用多类AI模型进行测试，允许用户自定义评估规则，为AI批改算法优化、产品选型、效果验证提供数据支撑。

### 核心目标
- 解决AI批改效果缺乏标准化、可视化评估手段的问题
- 支持多学科、多AI模型的批改效果对比分析
- 降低人工评估AI批改效果的成本，提升分析效率
- 提供灵活的自定义评估能力，适配不同场景的评估需求
- 输出评估报告，为AI批改产品优化提供决策依据

## Glossary

- **AI批改系统**: 本平台的核心系统，负责调用AI视觉模型进行图片识别和答案批改
- **基准答案**: 用户提供的标准正确答案，用于计算批改准确率
- **准确率**: 批改结果与基准答案匹配的题目数占总题目数的百分比
- **精确率(Precision)**: 预测为正确的样本中实际正确的比例
- **召回率(Recall)**: 实际正确的样本中被预测为正确的比例
- **F1值**: 精确率和召回率的调和平均数
- **一致性**: 相同输出结果出现次数最多的比例
- **Token消耗**: AI模型处理请求时消耗的token数量
- **单图并行测试**: 对单张图片同时发送多个并行请求，测试模型输出的一致性和准确率
- **批量结果对比**: 通过Excel文件导入多次批改结果，与基准答案进行系统性对比分析
- **提示词模板**: 预设的AI调用提示词，用于指导模型执行特定识别任务
- **Vision Pro 1.5**: 豆包视觉模型doubao-1-5-vision-pro-32k-250115
- **Seed Vision 1.6**: 豆包视觉模型doubao-seed-1-6-vision-250815
- **Qwen VL**: 阿里云通义千问视觉语言模型
- **Qwen3-Max**: 阿里云通义千问大语言模型，在本系统中负责宏观分析总结、整体趋势洞察、模型选型建议等高层次分析任务
- **DeepSeek-V3**: DeepSeek大语言模型，在本系统中负责微观语义评估、逐题正确性判断、错误归因分析、模型输出仲裁等精细化评估任务
- **评估模型分工**: 采用Qwen3-Max和DeepSeek双模型协作的评估架构，Qwen3-Max负责宏观分析（整体报告、趋势分析、战略建议），DeepSeek负责微观评估（语义判断、逐题评分、错误诊断、质量仲裁）
- **LLM-as-a-Judge**: 使用大语言模型作为评判者，对其他AI模型的输出质量进行评估和仲裁的方法
- **联合评估**: 同时使用Qwen3-Max和DeepSeek进行评估，整合两者结果生成综合报告

## Requirements

### Requirement 1: 数据上传与解析

**User Story:** As a 测试人员, I want to 上传基准答案和AI批改结果数据, so that 我可以进行批改效果评估。

#### Acceptance Criteria

1. WHEN 用户上传Excel格式基准答案文件 THEN AI批改系统 SHALL 使用SheetJS库解析文件并验证数据格式完整性
2. WHEN Excel文件格式为：第一列题号、第二列基准答案、后续列为批改结果 THEN AI批改系统 SHALL 正确识别数据结构并显示预览
3. WHEN 用户上传JSON格式数据 THEN AI批改系统 SHALL 解析JSON数组并验证必要字段（index、answer、userAnswer、correct）
4. IF 数据格式不正确或缺少必要字段 THEN AI批改系统 SHALL 显示清晰的错误提示信息（如"基准答案缺少评分标准"、"JSON格式错误"、"缺少必要字段index"）
5. WHEN 数据上传成功 THEN AI批改系统 SHALL 显示数据预览表格（前5行）并启用评估按钮
6. WHEN 用户上传单条数据 THEN AI批改系统 SHALL 支持手动输入JSON格式的单条基准答案
7. WHEN 用户上传批量数据 THEN AI批改系统 SHALL 支持Excel批量导入多条基准答案
8. WHEN 上传AI批改结果 THEN AI批改系统 SHALL 自动校验与基准答案的题号匹配关系
9. IF AI批改结果与基准答案题号不匹配 THEN AI批改系统 SHALL 显示"批改结果与基准答案题号不匹配，请检查数据"错误提示

### Requirement 2: 实时模型测试

**User Story:** As a 测试人员, I want to 实时调用多类AI模型进行批改测试, so that 我可以快速验证模型效果。

#### Acceptance Criteria

1. WHEN 用户进入主界面 THEN AI批改系统 SHALL 提供模型选择按钮组，包含Vision Pro、Seed Vision、Seed 1.6、Seed Thinking、Qwen VL等国内主流大模型
2. WHEN 用户上传图片并输入提示词 THEN AI批改系统 SHALL 支持流式响应实时展示批改结果
3. WHEN 批改完成 THEN AI批改系统 SHALL 显示批改耗时、Token消耗（输入/输出/总计）等基础数据
4. WHEN 用户点击"全部对比"按钮 THEN AI批改系统 SHALL 并行调用所有可用模型并以卡片网格形式展示对比结果
5. WHEN 用户设置重复次数大于1 THEN AI批改系统 SHALL 执行并行测试并展示一致性统计
6. WHEN 用户选择学科 THEN AI批改系统 SHALL 提供学科选择器（语文/数学/英语/物理/化学/生物/历史/地理/政治）
7. WHEN 用户选择题型 THEN AI批改系统 SHALL 提供题型选择器（客观题/主观题/计算题/作文题）
8. WHEN 用户输入测试用例后点击批改 THEN AI批改系统 SHALL 一键触发AI批改并实时展示结果
9. WHEN 测试完成 THEN AI批改系统 SHALL 自动保存测试记录到本地存储
10. WHEN 用户查看历史记录 THEN AI批改系统 SHALL 支持快速回溯和对比多次测试结果

### Requirement 3: 单图并行测试

**User Story:** As a 测试人员, I want to 对单张图片进行多次并行AI调用, so that 我可以评估模型输出的一致性和准确率。

#### Acceptance Criteria

1. WHEN 用户上传图片并点击开始测试 THEN AI批改系统 SHALL 使用Promise.all并行发送指定次数（1-20次）的API请求
2. WHEN 所有并行请求完成 THEN AI批改系统 SHALL 收集所有响应结果并计算一致性百分比
3. WHEN 用户提供JSON格式基准答案 THEN AI批改系统 SHALL 解析响应中的JSON数组并与基准答案逐题对比计算准确率
4. WHEN 显示测试结果 THEN AI批改系统 SHALL 展示统计卡片：总次数、不同结果数、一致性百分比、平均准确率
5. WHEN 显示测试结果 THEN AI批改系统 SHALL 渲染准确率柱状图和响应长度折线图
6. WHEN 显示测试结果 THEN AI批改系统 SHALL 以卡片列表形式展示每次调用的原始响应内容及准确率标签

### Requirement 4: 批量结果对比

**User Story:** As a 数据分析师, I want to 上传Excel文件对比多次批改结果, so that 我可以系统性地分析批改质量。

#### Acceptance Criteria

1. WHEN 用户上传xlsx/xls格式Excel文件 THEN AI批改系统 SHALL 使用SheetJS库解析文件并显示数据预览表格
2. WHEN 用户点击开始对比 THEN AI批改系统 SHALL 计算每列批改结果与基准答案的匹配准确率
3. WHEN 显示对比结果 THEN AI批改系统 SHALL 以表格形式展示逐题对比，使用黄色背景高亮不一致单元格
4. WHEN 显示对比结果 THEN AI批改系统 SHALL 使用绿色背景标记全部正确的行，红色背景标记全部错误的行
5. WHEN 显示对比结果 THEN AI批改系统 SHALL 渲染各次批改准确率柱状图和正确率分布饼图（全对/部分对/全错）
6. WHEN 显示对比结果 THEN AI批改系统 SHALL 展示统计卡片：总题数、批改次数、平均准确率、全部正确题数
7. WHEN Excel文件包含JSON数组列 THEN AI批改系统 SHALL 解析JSON数组格式的批改结果（包含index、answer、userAnswer、correct字段）
8. WHEN Excel文件格式为模型+批次+学科+题型+JSON数组 THEN AI批改系统 SHALL 按模型分组进行对比分析
9. WHEN 解析JSON数组 THEN AI批改系统 SHALL 提取每题的标准答案、用户答案、正确性判断
10. WHEN 显示对比结果 THEN AI批改系统 SHALL 按模型维度展示准确率排名

### Requirement 5: 输出一致性测试

**User Story:** As a 质量工程师, I want to 测试AI模型对同一输入的输出稳定性, so that 我可以评估模型的可靠性。

#### Acceptance Criteria

1. WHEN 用户上传图片并设置重复次数（3-30次） THEN AI批改系统 SHALL 顺序执行API调用并实时更新进度条
2. WHEN 每次调用完成 THEN AI批改系统 SHALL 更新进度显示（已完成/总次数）
3. WHEN 所有调用完成 THEN AI批改系统 SHALL 对响应内容进行标准化处理（去除空白字符、转小写）后分组
4. WHEN 显示测试结果 THEN AI批改系统 SHALL 计算一致性百分比（出现次数最多的结果占总次数的比例）
5. WHEN 显示测试结果 THEN AI批改系统 SHALL 展示统计卡片：一致性百分比、不同输出数、最多次数、总次数
6. WHEN 显示测试结果 THEN AI批改系统 SHALL 以分组卡片形式展示各种输出及其出现次数和对应的调用序号
7. WHEN 显示测试结果 THEN AI批改系统 SHALL 渲染输出分布饼图和响应长度变化折线图

### Requirement 6: 多维度评估指标

**User Story:** As a 测试人员, I want to 查看多维度的评估指标, so that 我可以全面了解AI批改效果。

#### Acceptance Criteria

1. WHEN 评估完成 THEN AI批改系统 SHALL 计算准确性指标：准确率、精确率、召回率、F1值、一致性
2. WHEN 评估完成 THEN AI批改系统 SHALL 计算效率指标：单题批改耗时、批量批改平均耗时
3. WHEN 评估完成 THEN AI批改系统 SHALL 计算资源指标：Token消耗量（输入/输出/总计）、Token成本估算
4. WHEN 显示评估结果 THEN AI批改系统 SHALL 以统计卡片网格形式展示各项指标数值
5. WHEN 指标值大于等于80% THEN AI批改系统 SHALL 为该统计卡片添加highlight样式（深色背景）
6. WHEN 用户配置权重 THEN AI批改系统 SHALL 支持自定义各维度权重（准确性/稳定性/成本/延迟）
7. WHEN 评估完成 THEN AI批改系统 SHALL 根据权重计算综合评分（0-100分）
8. WHEN 多模型评估完成 THEN AI批改系统 SHALL 根据综合评分自动生成模型排名
9. WHEN 显示综合评分 THEN AI批改系统 SHALL 以雷达图形式展示各维度得分分布

### Requirement 6.1: 自定义评估配置

**User Story:** As a 测试人员, I want to 自定义评估配置, so that 我可以根据不同场景灵活调整评估标准。

#### Acceptance Criteria

1. WHEN 用户进入评估配置界面 THEN AI批改系统 SHALL 提供评估维度选择器（准确性类/效率类/资源类）
2. WHEN 用户选择准确性类维度 THEN AI批改系统 SHALL 支持选择准确率、精确率、召回率、F1值、一致性
3. WHEN 用户选择效率类维度 THEN AI批改系统 SHALL 支持选择单题批改耗时、批量批改平均耗时
4. WHEN 用户选择资源类维度 THEN AI批改系统 SHALL 支持选择Token消耗量、Token成本
5. WHEN 用户配置学科评分规则 THEN AI批改系统 SHALL 支持为作文题配置权重（如内容40%、结构30%、语言30%）
6. WHEN 用户配置学科评分规则 THEN AI批改系统 SHALL 支持为数学题配置各题型占比
7. WHEN 用户选择评估范围 THEN AI批改系统 SHALL 支持单模型单次结果评估
8. WHEN 用户选择评估范围 THEN AI批改系统 SHALL 支持多模型对比评估
9. WHEN 用户选择评估范围 THEN AI批改系统 SHALL 支持同一模型不同版本对比评估

### Requirement 6.2: 自动题型识别

**User Story:** As a 测试人员, I want to 系统自动识别题目类型, so that 我可以减少手动配置工作量。

#### Acceptance Criteria

1. WHEN 用户上传题目数据 THEN AI批改系统 SHALL 自动解析题目内容
2. WHEN 解析题目内容 THEN AI批改系统 SHALL 根据规则判断题型为客观题（选择题、填空题）
3. WHEN 解析题目内容 THEN AI批改系统 SHALL 根据规则判断题型为主观题（简答题、论述题）
4. WHEN 解析题目内容 THEN AI批改系统 SHALL 根据规则判断题型为计算题
5. WHEN 解析题目内容 THEN AI批改系统 SHALL 根据规则判断题型为作文题
6. WHEN 自动识别完成 THEN AI批改系统 SHALL 显示识别结果并支持用户手动修正
7. IF 无法自动识别题型 THEN AI批改系统 SHALL 调用AI模型辅助判断题型

### Requirement 7: 数据可视化

**User Story:** As a 用户, I want to 通过图表直观地查看测试结果, so that 我可以快速理解数据分析结论。

#### Acceptance Criteria

1. WHEN 测试完成 THEN AI批改系统 SHALL 使用Chart.js库渲染柱状图展示准确率分布和多模型对比
2. WHEN 测试完成 THEN AI批改系统 SHALL 使用Chart.js库渲染折线图展示批次耗时变化趋势
3. WHEN 测试完成 THEN AI批改系统 SHALL 使用Chart.js库渲染饼图展示错误类型分布
4. WHEN 测试完成 THEN AI批改系统 SHALL 使用Chart.js库渲染环形图展示结果分布比例（全对/部分对/全错）
5. WHEN 图表容器存在 THEN AI批改系统 SHALL 支持图表缩放和自定义维度切换

### Requirement 8: 智能分析总结（Qwen3-Max）

**User Story:** As a 用户, I want to 获取AI生成的测试结果分析总结, so that 我可以获得专业的数据解读和优化建议。

#### Acceptance Criteria

1. WHEN 测试完成且配置了Qwen API Key THEN AI批改系统 SHALL 支持调用qwen3-max模型生成分析总结
2. WHEN 生成分析总结 THEN AI批改系统 SHALL 包含数据解读、差异分析、优劣评估和实用建议
3. WHEN 显示分析总结 THEN AI批改系统 SHALL 以深色背景卡片形式展示总结内容
4. WHEN 生成分析总结 THEN AI批改系统 SHALL 自动移除模型输出中的思考标签内容

### Requirement 8.1: 评估模型分工架构

**User Story:** As a 系统架构师, I want to 明确Qwen3-Max和DeepSeek的评估分工, so that 我可以充分发挥各模型优势进行高质量评估。

#### Acceptance Criteria

1. WHEN 系统进行AI输出质量评估 THEN AI批改系统 SHALL 采用Qwen3-Max负责宏观分析总结，DeepSeek负责微观语义评估的分工模式
2. WHEN 配置评估模型 THEN AI批改系统 SHALL 支持独立配置Qwen3-Max API Key和DeepSeek API Key
3. WHEN 两个评估模型均已配置 THEN AI批改系统 SHALL 支持联合评估模式，综合两者结果
4. IF 仅配置其中一个评估模型 THEN AI批改系统 SHALL 使用已配置的模型完成可用的评估功能

### Requirement 8.2: Qwen3-Max宏观分析职责

**User Story:** As a 测试人员, I want to 使用Qwen3-Max进行宏观层面的分析, so that 我可以获得整体性的数据洞察和战略建议。

#### Acceptance Criteria

1. WHEN 多模型对比完成 THEN AI批改系统 SHALL 调用Qwen3-Max生成整体对比分析报告
2. WHEN 生成对比报告 THEN AI批改系统 SHALL 包含各模型优劣势总结、适用场景分析、选型建议
3. WHEN 批量测试完成 THEN AI批改系统 SHALL 调用Qwen3-Max分析整体趋势和规律
4. WHEN 显示Qwen3-Max分析 THEN AI批改系统 SHALL 以结构化报告形式展示（概述、详细分析、结论建议）
5. WHEN 用户请求优化建议 THEN AI批改系统 SHALL 调用Qwen3-Max生成提示词优化方向和模型选型策略

### Requirement 8.3: DeepSeek微观评估职责

**User Story:** As a 测试人员, I want to 使用DeepSeek进行微观层面的语义评估, so that 我可以获得精确的答案正确性判断。

#### Acceptance Criteria

1. WHEN 进行单题评估 THEN AI批改系统 SHALL 调用DeepSeek进行语义级正确性判断
2. WHEN DeepSeek评估单题 THEN AI批改系统 SHALL 返回语义正确性、得分、缺失要点、错误类型
3. WHEN 发现批改错误 THEN AI批改系统 SHALL 调用DeepSeek分析具体错误原因和修复建议
4. WHEN 进行模型输出仲裁 THEN AI批改系统 SHALL 调用DeepSeek对多个模型输出进行逐项对比评分
5. WHEN 显示DeepSeek评估 THEN AI批改系统 SHALL 以详细评分卡形式展示各评估维度得分

### Requirement 9: 题号识别功能

**User Story:** As a 用户, I want to 自动识别试卷图片中的题号, so that 我可以快速生成题目结构数据。

#### Acceptance Criteria

1. WHEN 用户在侧边栏上传试卷图片 THEN AI批改系统 SHALL 调用Seed Vision模型识别题号
2. WHEN 识别完成 THEN AI批改系统 SHALL 提取题号和题目前15个字符作为内容预览
3. WHEN 识别完成 THEN AI批改系统 SHALL 以列表形式展示识别结果（题号+内容预览）
4. WHEN 用户点击保存按钮 THEN AI批改系统 SHALL 支持将识别结果保存为JSON或文本格式的提示词模板
5. WHEN 用户自定义识别提示词 THEN AI批改系统 SHALL 使用自定义提示词替代默认提示词

### Requirement 10: 提示词模板管理

**User Story:** As a 用户, I want to 管理和复用提示词模板, so that 我可以提高测试效率。

#### Acceptance Criteria

1. WHEN 用户打开侧边栏 THEN AI批改系统 SHALL 显示已保存的提示词模板列表
2. WHEN 用户点击模板 THEN AI批改系统 SHALL 将模板内容追加到输入框
3. WHEN 用户点击添加按钮 THEN AI批改系统 SHALL 显示模板编辑弹窗，支持多字段结构化编辑
4. WHEN 用户保存模板 THEN AI批改系统 SHALL 将模板持久化到prompts.json文件
5. WHEN 用户点击删除按钮 THEN AI批改系统 SHALL 确认后删除对应模板

### Requirement 11: 会话上下文管理

**User Story:** As a 用户, I want to 进行多轮对话测试, so that 我可以测试模型的上下文理解能力。

#### Acceptance Criteria

1. WHEN 用户启用上下文开关 THEN AI批改系统 SHALL 创建会话并保存对话历史
2. WHEN 启用上下文后发送消息 THEN AI批改系统 SHALL 将历史消息（最近20条）包含在API请求中
3. WHEN 显示对话历史 THEN AI批改系统 SHALL 以聊天气泡形式展示用户和助手的消息
4. WHEN 用户点击清除按钮 THEN AI批改系统 SHALL 清除当前会话历史并创建新会话

### Requirement 12: 深度思考模式

**User Story:** As a 用户, I want to 配置模型的深度思考级别, so that 我可以平衡响应质量和速度。

#### Acceptance Criteria

1. WHEN 用户选择支持reasoning_effort的模型 THEN AI批改系统 SHALL 显示深度思考模式选择器
2. WHEN 用户选择思考级别（高/中/低/最小） THEN AI批改系统 SHALL 在API请求中设置对应的reasoning_effort参数
3. WHEN 深度思考模式启用 THEN AI批改系统 SHALL 设置max_completion_tokens为65535

### Requirement 13: API配置管理

**User Story:** As a 用户, I want to 配置不同AI服务的API密钥, so that 我可以使用多种AI模型。

#### Acceptance Criteria

1. WHEN 用户点击设置按钮 THEN AI批改系统 SHALL 显示设置弹窗
2. WHEN 显示设置弹窗 THEN AI批改系统 SHALL 提供豆包API Key、API URL、Qwen API Key的输入框
3. WHEN 用户保存设置 THEN AI批改系统 SHALL 将配置持久化到config.json文件
4. IF API Key未配置 THEN AI批改系统 SHALL 在调用对应模型时显示配置提示

### Requirement 14: 界面交互

**User Story:** As a 用户, I want to 获得流畅的操作体验, so that 我可以高效地完成测试任务。

#### Acceptance Criteria

1. WHEN 页面加载 THEN AI批改系统 SHALL 显示固定顶部导航栏，包含标题、对比分析链接、清除按钮、提示词按钮、设置按钮
2. WHEN 用户切换测试模式Tab THEN AI批改系统 SHALL 显示对应的测试面板并隐藏其他面板
3. WHEN 执行API调用 THEN AI批改系统 SHALL 显示加载状态（流式响应显示loading动画）
4. WHEN API调用完成 THEN AI批改系统 SHALL 隐藏加载状态并显示结果
5. WHEN 屏幕宽度小于768px THEN AI批改系统 SHALL 将图表网格调整为单列布局
6. WHEN 用户点击图片预览 THEN AI批改系统 SHALL 显示全屏图片查看弹窗

### Requirement 15: 文件上传与预览

**User Story:** As a 用户, I want to 上传图片和Excel文件进行测试, so that 我可以使用自己的数据进行分析。

#### Acceptance Criteria

1. WHEN 用户点击图片上传区域或按钮 THEN AI批改系统 SHALL 触发隐藏的file input元素
2. WHEN 用户选择图片文件 THEN AI批改系统 SHALL 使用FileReader读取为base64格式并显示预览
3. WHEN 图片上传成功 THEN AI批改系统 SHALL 为上传区域添加has-file样式并启用相关按钮
4. WHEN 用户选择Excel文件 THEN AI批改系统 SHALL 使用XLSX库解析并显示前5行数据预览
5. IF Excel数据行数少于2行 THEN AI批改系统 SHALL 显示"数据不足"错误提示
6. WHEN 用户点击移除按钮 THEN AI批改系统 SHALL 清除已上传的文件和预览


### Requirement 16: 学科分类评估

**User Story:** As a 测试人员, I want to 按不同学科进行分类评估, so that 我可以针对性地分析各学科的批改效果。

#### Acceptance Criteria

1. WHEN 用户进入评估界面 THEN AI批改系统 SHALL 提供学科选择器（语文/数学/英语/物理/化学/生物/历史/地理/政治）
2. WHEN 用户选择学科 THEN AI批改系统 SHALL 加载该学科对应的评估规则和权重配置
3. WHEN 用户选择题型（客观题/主观题/计算题/作文题） THEN AI批改系统 SHALL 应用对应题型的评分标准
4. WHEN 显示评估结果 THEN AI批改系统 SHALL 按学科维度展示准确率、错误类型分布等指标
5. WHEN 用户自定义学科评分规则 THEN AI批改系统 SHALL 支持配置各题型权重和评分占比

### Requirement 17: 自定义模型配置保存

**User Story:** As a 用户, I want to 快速保存和切换不同的模型配置, so that 我可以高效地进行多模型对比测试。

#### Acceptance Criteria

1. WHEN 用户配置模型参数后点击保存 THEN AI批改系统 SHALL 将模型配置（名称、API地址、密钥、默认参数）保存到本地
2. WHEN 用户进入测试界面 THEN AI批改系统 SHALL 显示已保存的模型配置列表，支持快速切换
3. WHEN 用户点击模型配置 THEN AI批改系统 SHALL 自动加载该配置的所有参数
4. WHEN 用户编辑已保存的配置 THEN AI批改系统 SHALL 支持修改和更新配置
5. WHEN 用户删除配置 THEN AI批改系统 SHALL 确认后移除该模型配置

### Requirement 18: 智能问题诊断与改进建议

**User Story:** As a 测试人员, I want to 获取系统自动分析的不足之处和改进建议, so that 我可以针对性地优化AI批改效果。

#### Acceptance Criteria

1. WHEN 评估完成 THEN AI批改系统 SHALL 自动分析批改结果中的错误模式和薄弱环节
2. WHEN 显示诊断结果 THEN AI批改系统 SHALL 标注错误类型分类（识别错误/规则错误/格式错误/逻辑错误）
3. WHEN 显示诊断结果 THEN AI批改系统 SHALL 定位具体出错的题目并展示错误详情
4. WHEN 显示诊断结果 THEN AI批改系统 SHALL 生成针对性的改进建议（如"数学公式识别准确率低，建议优化提示词"）
5. WHEN 用户查看改进建议 THEN AI批改系统 SHALL 提供可操作的优化方案（提示词优化建议、模型选择建议、参数调整建议）
6. WHEN 多次评估后 THEN AI批改系统 SHALL 展示改进趋势图，对比优化前后的效果变化


### Requirement 19: 测试结果导出

**User Story:** As a 用户, I want to 导出测试结果和评估报告, so that 我可以保存和分享分析数据。

#### Acceptance Criteria

1. WHEN 测试完成 THEN AI批改系统 SHALL 提供导出按钮
2. WHEN 用户点击导出Excel THEN AI批改系统 SHALL 将测试结果、统计数据导出为xlsx格式
3. WHEN 用户点击导出PDF THEN AI批改系统 SHALL 将评估报告（含图表）导出为PDF格式
4. WHEN 用户点击导出JSON THEN AI批改系统 SHALL 将原始数据导出为JSON格式
5. WHEN 导出完成 THEN AI批改系统 SHALL 自动下载文件并显示成功提示

### Requirement 20: 历史记录管理

**User Story:** As a 用户, I want to 查看和管理历史测试记录, so that 我可以回溯和对比历史数据。

#### Acceptance Criteria

1. WHEN 测试完成 THEN AI批改系统 SHALL 自动保存测试记录到本地存储
2. WHEN 用户打开历史记录面板 THEN AI批改系统 SHALL 显示历史测试列表（按时间倒序）
3. WHEN 用户点击历史记录 THEN AI批改系统 SHALL 加载并展示该次测试的完整结果
4. WHEN 用户选择多条记录 THEN AI批改系统 SHALL 支持一键生成对比报表
5. WHEN 用户删除记录 THEN AI批改系统 SHALL 确认后移除该条记录

### Requirement 21: 快捷操作与键盘支持

**User Story:** As a 用户, I want to 使用快捷键和快捷操作, so that 我可以更高效地完成测试任务。

#### Acceptance Criteria

1. WHEN 用户按Ctrl+Enter THEN AI批改系统 SHALL 触发发送/开始测试操作
2. WHEN 用户按Ctrl+V粘贴图片 THEN AI批改系统 SHALL 自动识别并上传图片
3. WHEN 用户拖拽文件到页面 THEN AI批改系统 SHALL 自动识别文件类型并处理
4. WHEN 用户双击结果卡片 THEN AI批改系统 SHALL 展开显示完整内容
5. WHEN 用户按Esc THEN AI批改系统 SHALL 关闭当前弹窗或取消操作

### Requirement 22: 实时性能监控

**User Story:** As a 用户, I want to 实时查看API调用的性能数据, so that 我可以监控系统状态和资源消耗。

#### Acceptance Criteria

1. WHEN API调用进行中 THEN AI批改系统 SHALL 显示实时耗时计时器
2. WHEN 流式响应进行中 THEN AI批改系统 SHALL 显示实时字符数和预估Token数
3. WHEN 批量测试进行中 THEN AI批改系统 SHALL 显示整体进度和预估剩余时间
4. WHEN 测试完成 THEN AI批改系统 SHALL 显示本次调用的详细性能数据（耗时、Token、成本估算）

### Requirement 23: 结果对比视图

**User Story:** As a 用户, I want to 并排对比不同测试结果, so that 我可以直观地发现差异。

#### Acceptance Criteria

1. WHEN 用户选择两个或多个结果 THEN AI批改系统 SHALL 提供并排对比视图
2. WHEN 显示对比视图 THEN AI批改系统 SHALL 高亮显示差异部分
3. WHEN 显示对比视图 THEN AI批改系统 SHALL 支持同步滚动
4. WHEN 用户点击差异项 THEN AI批改系统 SHALL 展开显示详细差异内容

### Requirement 24: 收藏与标记功能

**User Story:** As a 用户, I want to 收藏重要的测试结果和提示词, so that 我可以快速访问常用内容。

#### Acceptance Criteria

1. WHEN 用户点击收藏按钮 THEN AI批改系统 SHALL 将当前结果/提示词添加到收藏列表
2. WHEN 用户打开收藏面板 THEN AI批改系统 SHALL 显示所有收藏项
3. WHEN 用户为结果添加标签 THEN AI批改系统 SHALL 支持按标签筛选
4. WHEN 用户添加备注 THEN AI批改系统 SHALL 保存备注并在列表中显示


### Requirement 25: DeepSeek语义评估引擎（微观评估）

**User Story:** As a 测试人员, I want to 使用DeepSeek进行语义级答案评估, so that 我可以准确评估主观题、简答题、作文题的批改效果。

#### Acceptance Criteria

1. WHEN 用户配置DeepSeek API Key THEN AI批改系统 SHALL 支持调用DeepSeek-V3作为语义评估引擎
2. WHEN 进行批量对比评估 THEN AI批改系统 SHALL 支持选择"严格匹配"或"语义评估"模式
3. WHEN 使用语义评估模式 THEN AI批改系统 SHALL 将题目、标准答案、AI答案、学科、题型发送给DeepSeek
4. WHEN DeepSeek返回评估结果 THEN AI批改系统 SHALL 解析语义正确性、得分、缺失要点、错误类型、置信度
5. WHEN 显示评估结果 THEN AI批改系统 SHALL 展示语义匹配分数和详细评估说明
6. WHEN 主观题评估 THEN AI批改系统 SHALL 支持"意思对但表述不同"的情况判定为正确

### Requirement 26: LLM-as-a-Judge模型仲裁（DeepSeek主导）

**User Story:** As a 测试人员, I want to 使用DeepSeek对多模型输出进行质量仲裁, so that 我可以获得更全面的模型对比评估。

#### Acceptance Criteria

1. WHEN 多模型对比完成 THEN AI批改系统 SHALL 支持调用DeepSeek进行输出质量仲裁
2. WHEN 进行模型仲裁 THEN AI批改系统 SHALL 评估正确性、清晰度、教学风格等多维度
3. WHEN 仲裁完成 THEN AI批改系统 SHALL 生成模型排名和排名理由
4. WHEN 显示仲裁结果 THEN AI批改系统 SHALL 展示各维度得分和综合推荐
5. WHEN 用户查看详情 THEN AI批改系统 SHALL 显示DeepSeek的详细评估说明

### Requirement 27: 智能错误归因分析（DeepSeek）

**User Story:** As a 测试人员, I want to 自动诊断批改错误的根本原因, so that 我可以针对性地优化AI批改效果。

#### Acceptance Criteria

1. WHEN 发现批改错误 THEN AI批改系统 SHALL 调用DeepSeek分析错误根因
2. WHEN 分析完成 THEN AI批改系统 SHALL 识别错误阶段（视觉识别/语义理解/推理计算/格式输出）
3. WHEN 分析完成 THEN AI批改系统 SHALL 判断错误严重程度（高/中/低）
4. WHEN 显示分析结果 THEN AI批改系统 SHALL 提供工程可执行的修复建议
5. WHEN 用户查看建议 THEN AI批改系统 SHALL 展示具体的提示词优化、参数调整建议

### Requirement 27.1: 联合评估报告生成

**User Story:** As a 测试人员, I want to 获取Qwen3-Max和DeepSeek联合生成的综合评估报告, so that 我可以同时获得宏观洞察和微观细节。

#### Acceptance Criteria

1. WHEN 两个评估模型均已配置且评估完成 THEN AI批改系统 SHALL 支持生成联合评估报告
2. WHEN 生成联合报告 THEN AI批改系统 SHALL 整合DeepSeek的逐题评估结果和Qwen3-Max的整体分析
3. WHEN 显示联合报告 THEN AI批改系统 SHALL 分为"详细评估"（DeepSeek）和"总结建议"（Qwen3-Max）两部分
4. WHEN 评估结果存在分歧 THEN AI批改系统 SHALL 标注分歧点并展示两个模型的不同观点
5. WHEN 用户导出报告 THEN AI批改系统 SHALL 支持导出包含两个模型评估结果的完整报告

### Requirement 28: 提示词A/B测试

**User Story:** As a 用户, I want to 对比不同提示词的效果, so that 我可以科学地优化提示词。

#### Acceptance Criteria

1. WHEN 用户选择两个提示词模板 THEN AI批改系统 SHALL 支持A/B测试模式
2. WHEN 执行A/B测试 THEN AI批改系统 SHALL 使用相同数据分别测试两个提示词
3. WHEN 测试完成 THEN AI批改系统 SHALL 对比各项指标（准确率、一致性、耗时、Token消耗）
4. WHEN 显示对比结果 THEN AI批改系统 SHALL 高亮显示优胜提示词和优势项
5. WHEN 配置DeepSeek THEN AI批改系统 SHALL 支持调用DeepSeek评估提示词质量差异

### Requirement 29: 提示词版本管理

**User Story:** As a 用户, I want to 管理提示词的版本历史, so that 我可以追溯和回滚提示词变更。

#### Acceptance Criteria

1. WHEN 用户修改提示词 THEN AI批改系统 SHALL 自动保存版本历史
2. WHEN 用户查看版本历史 THEN AI批改系统 SHALL 显示所有历史版本列表（时间、修改内容摘要）
3. WHEN 用户选择历史版本 THEN AI批改系统 SHALL 支持查看完整内容和差异对比
4. WHEN 用户点击回滚 THEN AI批改系统 SHALL 恢复到选定的历史版本
5. WHEN 版本关联测试结果 THEN AI批改系统 SHALL 显示该版本的历史测试效果数据

### Requirement 30: 智能模型推荐

**User Story:** As a 用户, I want to 获取系统自动推荐的最优模型, so that 我可以快速选择适合场景的模型。

#### Acceptance Criteria

1. WHEN 多模型评估完成 THEN AI批改系统 SHALL 根据综合评分自动推荐最优模型
2. WHEN 用户指定场景（准确性优先/成本优先/速度优先） THEN AI批改系统 SHALL 推荐该场景下的最优模型
3. WHEN 显示推荐结果 THEN AI批改系统 SHALL 展示推荐理由和各模型的优劣势对比
4. WHEN 用户指定学科和题型 THEN AI批改系统 SHALL 推荐该学科题型下表现最好的模型

### Requirement 31: 统一AI评估功能

**User Story:** As a 测试人员, I want to 在所有测试模式中使用AI评估功能, so that 我可以获得专业的评估分析和问题诊断。

#### Acceptance Criteria

1. WHEN 单图测试完成 THEN AI批改系统 SHALL 支持调用Qwen3-Max和DeepSeek-V3进行AI评估
2. WHEN 批量对比完成 THEN AI批改系统 SHALL 支持调用Qwen3-Max和DeepSeek-V3进行AI评估
3. WHEN 一致性测试完成 THEN AI批改系统 SHALL 支持调用Qwen3-Max和DeepSeek-V3进行AI评估
4. WHEN 多模型对比完成 THEN AI批改系统 SHALL 支持调用Qwen3-Max和DeepSeek-V3进行AI评估
5. WHEN 用户点击"AI评估"按钮 THEN AI批改系统 SHALL 显示评估模型选择（Qwen3-Max/DeepSeek-V3/联合评估）

### Requirement 32: AI评估量化数据输出

**User Story:** As a 测试人员, I want to 获取AI评估的量化数据, so that 我可以客观地了解批改效果。

#### Acceptance Criteria

1. WHEN AI评估完成 THEN AI批改系统 SHALL 输出各评估维度的具体数值（准确率、一致性、响应时间、Token消耗）
2. WHEN AI评估完成 THEN AI批改系统 SHALL 输出各模型的排名结果
3. WHEN AI评估完成 THEN AI批改系统 SHALL 输出与预设阈值（80%准确率）的对比结果
4. WHEN 显示量化数据 THEN AI批改系统 SHALL 以统计卡片形式展示核心指标
5. WHEN 指标超过阈值 THEN AI批改系统 SHALL 使用高亮样式标记达标指标

### Requirement 33: LLM问题定位功能

**User Story:** As a 测试人员, I want to 通过LLM自动定位批改问题, so that 我可以快速发现和修复批改错误。

#### Acceptance Criteria

1. WHEN 用户请求问题定位 THEN AI批改系统 SHALL 调用DeepSeek-V3分析批改错误
2. WHEN 分析完成 THEN AI批改系统 SHALL 标注错误类型（识别不准确/规则有误/格式错误/计算错误/选项混淆）
3. WHEN 分析完成 THEN AI批改系统 SHALL 定位具体出错的题目编号
4. WHEN 显示问题定位结果 THEN AI批改系统 SHALL 以表格形式展示错误题目、错误类型、错误原因
5. WHEN 用户点击错误题目 THEN AI批改系统 SHALL 展开显示详细的错误分析和修复建议

### Requirement 34: LLM可视化图表生成

**User Story:** As a 测试人员, I want to 通过LLM生成可视化图表, so that 我可以直观地理解评估数据。

#### Acceptance Criteria

1. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染柱状图展示多模型维度对比
2. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染折线图展示批次耗时变化
3. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染饼图展示错误类型分布
4. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染热力图展示评分偏差分布
5. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染准确率折线图
6. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染模型耗时箱线图
7. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染Token使用条形图
8. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染多模型能力雷达图
9. WHEN AI评估完成 THEN AI批改系统 SHALL 使用Chart.js渲染热力图展示模型×学科×题型支持矩阵
10. WHEN 用户操作图表 THEN AI批改系统 SHALL 支持图表缩放、导出PNG、自定义维度切换

### Requirement 35: DeepSeek评估报告生成

**User Story:** As a 测试人员, I want to 使用DeepSeek自动生成评估报告, so that 我可以获得结构化的评估文档。

#### Acceptance Criteria

1. WHEN 用户点击"生成报告"按钮 THEN AI批改系统 SHALL 调用DeepSeek-V3生成结构化评估报告
2. WHEN 生成报告 THEN AI批改系统 SHALL 包含评估背景（测试目的、测试时间、测试范围）
3. WHEN 生成报告 THEN AI批改系统 SHALL 包含配置信息（使用的模型、评估维度、阈值设置）
4. WHEN 生成报告 THEN AI批改系统 SHALL 包含核心数据（准确率、一致性、耗时、Token消耗、模型排名）
5. WHEN 生成报告 THEN AI批改系统 SHALL 包含问题分析（错误类型分布、问题题目列表、错误原因分析）
6. WHEN 生成报告 THEN AI批改系统 SHALL 包含优化建议（提示词优化、模型选择、参数调整）
7. WHEN 报告生成完成 THEN AI批改系统 SHALL 支持导出为HTML格式
8. WHEN 报告生成完成 THEN AI批改系统 SHALL 支持导出为PDF格式
9. WHEN 报告生成完成 THEN AI批改系统 SHALL 支持导出为Markdown格式
