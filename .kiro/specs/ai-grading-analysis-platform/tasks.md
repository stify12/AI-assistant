# Implementation Plan

## 评估模型分工架构实现

- [x] 1. 配置管理扩展




  - [x] 1.1 扩展config.json支持DeepSeek API Key


    - 在config.json中添加deepseek_api_key字段


    - 更新后端/api/config接口支持读写DeepSeek配置


    - _Requirements: 8.1.2, 13.3_
  - [x] 1.2 更新前端设置弹窗
    - 在设置弹窗中添加DeepSeek API Key输入框
    - 实现独立保存和验证逻辑
    - _Requirements: 8.1.2, 13.2_
  - [x] 1.3 编写配置持久化属性测试
    - **Property 13: 评估模型API Key独立配置**
    - 测试类: TestProperty13_APIKeyIndependentConfig
    - **Validates: Requirements 8.1.2**

- [x] 2. Qwen3-Max宏观分析模块

  - [x] 2.1 实现后端Qwen3-Max API调用
    - 创建/api/qwen/macro-analysis接口
    - 实现generateMacroReport函数
    - _Requirements: 8.2.1, 8.2.2_
  - [x] 2.2 实现多模型对比分析报告
    - 创建/api/qwen/compare-report接口
    - 实现analyzeModelComparison函数
    - _Requirements: 8.2.2, 8.2.3_
  - [x] 2.3 实现提示词优化建议

    - 创建/api/qwen/optimization-advice接口
    - 实现generateOptimizationAdvice函数
    - _Requirements: 8.2.5_

  - [x] 2.4 编写宏观分析报告完整性属性测试
    - **Property 14: 宏观分析报告完整性**
    - 测试类: TestProperty14_MacroAnalysisReportCompleteness
    - **Validates: Requirements 8.2.2**

- [x] 3. DeepSeek微观评估模块

  - [x] 3.1 实现后端DeepSeek API调用
    - 创建/api/deepseek/semantic-eval接口
    - 实现semanticEvaluate函数
    - _Requirements: 8.3.1, 8.3.2, 25.1_
  - [x] 3.2 实现模型输出仲裁
    - 创建/api/deepseek/judge接口
    - 实现judgeModels函数
    - _Requirements: 8.3.4, 26.1, 26.2_
  - [x] 3.3 实现错误归因分析


    - 创建/api/deepseek/diagnose接口
    - 实现diagnoseError函数
    - _Requirements: 8.3.3, 27.1, 27.2_
  - [x] 3.4 编写DeepSeek响应完整性属性测试
    - **Property 15: DeepSeek语义评估响应完整性**
    - 测试类: TestProperty15_DeepSeekSemanticEvalCompleteness
    - **Validates: Requirements 8.3.2**




- [ ] 4. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.



- [x] 5. 联合评估报告模块
  - [x] 5.1 实现联合报告生成接口

    - 创建/api/eval/joint-report接口
    - 实现generateJointReport函数
    - _Requirements: 27.1.1, 27.1.2_

  - [x] 5.2 实现评估结果合并逻辑
    - 实现mergeEvaluationResults函数
    - 实现identifyDiscrepancies函数
    - _Requirements: 27.1.2, 27.1.4_
  - [x] 5.3 实现联合报告前端展示
    - 添加联合报告展示组件
    - 分区显示Qwen3-Max和DeepSeek结果
    - _Requirements: 27.1.3_
  - [x] 5.4 编写联合报告属性测试
    - **Property 16: 联合报告数据来源完整性**
    - **Property 17: 联合报告结构分区正确性**
    - **Property 18: 评估分歧标注完整性**
    - 测试类: TestProperty16, TestProperty17, TestProperty18
    - **Validates: Requirements 27.1.2, 27.1.3, 27.1.4**

- [x] 6. 前端集成
  - [x] 6.1 更新批量对比界面
    - 添加"语义评估"模式切换
    - 集成DeepSeek语义评估调用
    - _Requirements: 25.2, 25.3_
  - [x] 6.2 更新多模型对比界面
    - 添加"AI仲裁"按钮
    - 集成DeepSeek模型仲裁调用（runAIJudge函数）
    - _Requirements: 26.1_
  - [x] 6.3 添加联合评估入口
    - 添加"生成联合报告"按钮
    - 实现联合报告弹窗展示（generateMultiModelJointReport函数）
    - _Requirements: 27.1.1, 27.1.3_
  - [x] 6.4 实现单模型降级提示
    - 检测API Key配置状态
    - 显示降级提示信息（showDegradedModeWarning函数）
    - _Requirements: 8.1.4_

- [ ] 7. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 统一AI评估功能实现

- [x] 8. 统一AI评估入口
  - [x] 8.1 实现后端统一AI评估接口
    - 创建/api/ai-eval/unified接口
    - 支持所有测试类型（single/batch/consistency/multi_model）
    - 支持评估模型选择（qwen3-max/deepseek/joint）
    - _Requirements: 31.1, 31.2, 31.3, 31.4_
  - [x] 8.2 实现前端评估模型选择器
    - 添加评估模型选择弹窗（showEvalModelSelector函数）
    - 支持Qwen3-Max/DeepSeek/联合评估三种模式
    - _Requirements: 31.5_
  - [x] 8.3 集成AI评估到单图测试
    - 在单图测试结果区添加"AI评估"按钮
    - 调用统一AI评估接口
    - _Requirements: 31.1_
  - [x] 8.4 集成AI评估到批量对比
    - 在批量对比结果区添加"AI评估"按钮
    - 调用统一AI评估接口（runUnifiedEval函数）
    - _Requirements: 31.2_
  - [x] 8.5 集成AI评估到一致性测试
    - 在一致性测试结果区添加"AI评估"按钮
    - 调用统一AI评估接口（runUnifiedEval函数）
    - _Requirements: 31.3_
  - [x] 8.6 集成AI评估到多模型对比
    - 在多模型对比结果区添加"AI评估"按钮
    - 调用统一AI评估接口（runUnifiedEval函数）
    - _Requirements: 31.4_
  - [x] 8.7 编写统一AI评估属性测试
    - **Property 19: 统一AI评估入口兼容性**
    - 测试类: TestProperty19_UnifiedAIEvalCompatibility
    - **Validates: Requirements 31.1, 31.2, 31.3, 31.4**

- [x] 9. 量化数据输出
  - [x] 9.1 实现后端量化数据接口
    - 创建/api/ai-eval/quantify接口
    - 计算各维度得分、排名、阈值对比
    - _Requirements: 32.1, 32.2, 32.3_
  - [x] 9.2 实现前端量化数据卡片渲染
    - 实现renderQuantifiedCards函数
    - 支持高亮达标指标
    - _Requirements: 32.4, 32.5_
  - [x] 9.3 编写量化数据属性测试
    - **Property 20: 量化数据阈值对比正确性**
    - 测试类: TestProperty20_QuantifyThresholdComparison
    - **Validates: Requirements 32.3, 32.5**

- [x] 10. LLM问题定位
  - [x] 10.1 实现后端问题定位接口
    - 创建/api/ai-eval/problem-locate接口
    - 调用DeepSeek分析错误
    - _Requirements: 33.1_
  - [x] 10.2 实现错误类型分类逻辑
    - 实现classifyErrorType函数（在后端prompt中定义5种错误类型）
    - 支持5种错误类型分类
    - _Requirements: 33.2_
  - [x] 10.3 实现前端问题定位表格
    - 实现renderProblemLocateResult函数
    - 支持展开详细分析
    - _Requirements: 33.3, 33.4, 33.5_
  - [x] 10.4 编写问题定位属性测试
    - **Property 21: 问题定位错误类型完整性**
    - 测试类: TestProperty21_ProblemLocateErrorTypes
    - **Validates: Requirements 33.2**

- [ ] 11. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## 可视化图表增强

- [x] 12. 图表数据生成
  - [x] 12.1 实现后端图表数据接口
    - 创建/api/ai-eval/charts接口
    - 返回所有图表所需数据
    - _Requirements: 34.1-34.9_
  - [x] 12.2 实现多模型对比柱状图
    - 实现generateMultiModelBarData函数
    - 渲染Chart.js柱状图
    - _Requirements: 34.1_
  - [x] 12.3 实现批次耗时折线图
    - 实现generateBatchTimeLineData函数（batch_time_line）
    - 渲染Chart.js折线图
    - _Requirements: 34.2_
  - [x] 12.4 实现错误类型饼图
    - 实现generateErrorTypePieData函数
    - 渲染Chart.js饼图
    - _Requirements: 34.3_
  - [x] 12.5 实现评分偏差热力图
    - 实现generateScoreDeviationHeatmapData函数（后端score_deviation_heatmap）
    - 使用表格模拟热力图渲染（renderScoreDeviationHeatmap函数）
    - _Requirements: 34.4_
  - [x] 12.6 实现准确率折线图
    - 实现generateAccuracyLineData函数（accuracy_line）
    - 渲染Chart.js折线图
    - _Requirements: 34.5_
  - [x] 12.7 实现模型耗时箱线图
    - 实现generateModelTimeBoxplotData函数（后端model_time_boxplot）
    - 使用CSS模拟箱线图渲染（renderModelTimeBoxplot函数）
    - _Requirements: 34.6_
  - [x] 12.8 实现Token使用条形图
    - 实现generateTokenUsageBarData函数（token_usage_bar）
    - 渲染Chart.js条形图
    - _Requirements: 34.7_
  - [x] 12.9 实现多模型能力雷达图
    - 实现generateCapabilityRadarData函数
    - 渲染Chart.js雷达图
    - _Requirements: 34.8_
  - [x] 12.10 实现模型×学科×题型热力图
    - 实现generateHeatmapData函数（后端model_subject_type_heatmap）
    - 渲染支持矩阵热力图（renderModelSubjectTypeHeatmap函数）
    - _Requirements: 34.9_
  - [x] 12.11 实现图表交互功能
    - 实现图表缩放功能
    - 实现导出PNG功能（exportChartAsPNG, exportAllCharts）
    - 实现维度切换功能
    - _Requirements: 34.10_
  - [x] 12.12 编写图表数据属性测试
    - **Property 22: 可视化图表数据完整性**
    - 测试类: TestProperty22_ChartDataCompleteness
    - **Validates: Requirements 34.1, 34.2, 34.3**

- [ ] 13. Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.

## DeepSeek评估报告生成

- [x] 14. 评估报告生成
  - [x] 14.1 实现后端报告生成接口
    - 创建/api/deepseek/report接口
    - 调用DeepSeek生成结构化报告
    - _Requirements: 35.1_
  - [x] 14.2 实现报告内容格式化
    - 实现format_report_background函数（评估背景）
    - 实现format_report_config函数（配置信息）
    - 实现format_report_core_data函数（核心数据）
    - 实现formatReportProblemAnalysis函数（问题分析 - 由DeepSeek生成）
    - 实现formatReportOptimization函数（优化建议 - 由DeepSeek生成）
    - _Requirements: 35.2, 35.3, 35.4, 35.5, 35.6_
  - [x] 14.3 实现报告导出功能
    - 创建/api/export/report接口
    - 实现generate_report_html函数
    - 实现generate_report_markdown函数
    - _Requirements: 35.7, 35.8, 35.9_
  - [x] 14.4 实现前端报告展示
    - 添加报告预览弹窗（showDeepSeekReport函数）
    - 添加导出格式选择（exportDeepSeekReport函数）
    - _Requirements: 35.1_
  - [x] 14.5 编写报告结构属性测试
    - **Property 23: DeepSeek报告结构完整性**
    - 测试类: TestProperty23_DeepSeekReportStructureCompleteness
    - **Validates: Requirements 35.2, 35.3, 35.4, 35.5, 35.6**

## 自定义评估配置

- [x] 15. 评估配置管理
  - [x] 15.1 实现后端评估配置接口
    - 创建/api/eval-config接口
    - 支持配置的保存和加载
    - _Requirements: 6.1.1-6.1.9_
  - [x] 15.2 实现前端评估配置面板
    - 添加评估维度选择器（showEvalConfigPanel函数）
    - 添加学科评分规则配置（数学、语文权重配置）
    - 添加评估范围选择（单模型/多模型/版本对比）
    - _Requirements: 6.1.1-6.1.9_
  - [x] 15.3 编写评估配置属性测试
    - **Property 25: 自定义评估配置权重和为1**
    - 测试类: TestProperty25_EvalConfigWeightSum
    - **Validates: Requirements 6.1.5, 6.1.6**

## 自动题型识别

- [x] 16. 题型识别功能
  - [x] 16.1 实现后端题型识别接口
    - 创建/api/question-type/detect接口
    - 实现规则识别逻辑（选择题、填空题、计算题、作文题、简答题、论述题）
    - _Requirements: 6.2.1-6.2.5_
  - [x] 16.2 实现AI辅助题型识别
    - 调用AI模型辅助判断（ai_detect_question_type函数）
    - _Requirements: 6.2.7_
  - [x] 16.3 实现前端题型识别展示
    - 显示识别结果（renderTypeDetectionResult函数）
    - 支持手动修正（allowManualCorrection函数）
    - _Requirements: 6.2.6_
  - [x] 16.4 编写题型识别属性测试
    - **Property 24: 题型识别结果有效性**
    - 测试类: TestProperty24_QuestionTypeDetection
    - **Validates: Requirements 6.2.2, 6.2.3, 6.2.4, 6.2.5**

## 数据上传增强

- [x] 17. JSON数组格式支持
  - [x] 17.1 增强Excel解析支持JSON数组列
    - 解析JSON数组格式的批改结果（parseNewFormatExcel函数）
    - 提取index、answer、userAnswer、correct字段
    - _Requirements: 4.7, 4.8, 4.9_
  - [x] 17.2 增强数据校验
    - 校验JSON格式完整性（detectExcelFormat函数）
    - 校验必要字段存在性
    - 显示清晰的错误提示
    - _Requirements: 1.3, 1.4, 1.8, 1.9_

- [ ] 18. Final Checkpoint - 确保所有测试通过
  - Ensure all tests pass, ask the user if questions arise.
