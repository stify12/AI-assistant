# Requirements Document

## Introduction

本功能在现有「学科评估」界面基础上新增「批量评估」入口，支持对AI已批改的多份作业进行批量评估。系统从数据库表zp_book_chapter和zp_make_book读取图书数据，用户可管理数据集（基准效果），创建批量评估任务，自动匹配或识别基准效果，依次评估多份作业，生成总体报告并支持导出Excel。

## Glossary

- **Batch_Evaluation_System**: 批量评估系统，用于批量评估AI批改作业的准确性
- **Book**: 图书，从zp_make_book表获取的教材信息
- **Chapter**: 章节，从zp_book_chapter表获取的章节信息
- **Dataset**: 数据集，包含特定书本页码的基准效果数据集合
- **Base_Effect**: 基准效果，标准批改结果，用于与AI批改结果对比
- **Batch_Task**: 批量评估任务，包含多个待评估作业任务的集合
- **Homework_Task**: 作业任务，数据库中AI已批改的单份作业记录
- **Evaluation_Result**: 评估结果，单个作业任务的评估数据
- **Overall_Report**: 总体报告，批量评估任务完成后的汇总分析报告
- **Accuracy_Rate**: 准确率，正确题目数除以总题目数的百分比
- **Question_Type**: 题目类型，根据questionType字段区分主观题和客观题
- **Objective_Question**: 客观题，questionType字段值为"objective"的题目
- **Subjective_Question**: 主观题，questionType字段值不为"objective"或该字段不存在的题目
- **Choice_Question**: 选择题，bvalue字段值为"1"（单选）或"2"（多选）的题目
- **Non_Choice_Question**: 非选择题，bvalue字段值不为"1"且不为"2"的题目
- **Single_Choice**: 单选题，bvalue字段值为"1"的题目
- **Multiple_Choice**: 多选题，bvalue字段值为"2"的题目

## Requirements

### Requirement 1: 批量评估入口

**User Story:** As a 测试人员, I want to 从学科评估界面进入批量评估页面, so that 我可以对多份作业进行批量评估。

#### Acceptance Criteria

1. WHEN 用户访问学科评估页面 THEN the Batch_Evaluation_System SHALL 在页面顶部显示「批量评估」入口按钮
2. WHEN 用户点击「批量评估」入口 THEN the Batch_Evaluation_System SHALL 跳转到批量评估页面
3. WHEN 用户进入批量评估页面 THEN the Batch_Evaluation_System SHALL 显示任务列表和「新建任务」按钮

### Requirement 2: 图书数据展示

**User Story:** As a 测试人员, I want to 查看按学科分类的图书列表, so that 我可以为特定书本页码配置基准效果数据集。

#### Acceptance Criteria

1. WHEN 用户进入数据集管理页面 THEN the Batch_Evaluation_System SHALL 从zp_make_book表读取图书数据并按学科分组展示
2. WHEN 系统展示图书列表 THEN the Batch_Evaluation_System SHALL 直接使用zp_make_book表的book_name字段展示中文书名
3. WHEN 用户点击某本图书 THEN the Batch_Evaluation_System SHALL 展示该书对应的所有页码列表（从zp_book_chapter表获取）
4. WHEN 数据库查询失败 THEN the Batch_Evaluation_System SHALL 显示错误提示并提供重试按钮

### Requirement 3: 数据集管理

**User Story:** As a 测试人员, I want to 为特定书本页码添加基准效果数据集, so that 批量评估时可以自动匹配基准效果。

#### Acceptance Criteria

1. WHEN 用户在书本详情页点击「添加数据集」 THEN the Batch_Evaluation_System SHALL 显示数据集创建表单
2. WHEN 用户创建数据集 THEN the Batch_Evaluation_System SHALL 允许选择多个页码并为每个页码配置基准效果
3. WHEN 用户保存数据集 THEN the Batch_Evaluation_System SHALL 将数据集信息持久化存储
4. WHEN 用户查看已有数据集 THEN the Batch_Evaluation_System SHALL 展示数据集列表（包含书本名、页码范围、题目数量、创建时间）
5. WHEN 用户删除数据集 THEN the Batch_Evaluation_System SHALL 移除对应数据集并更新列表
6. WHEN 系统检测到30分钟内有对应书本页码的作业图片 THEN the Batch_Evaluation_System SHALL 在数据集页码旁显示「自动识别」按钮
7. WHEN 用户点击数据集页码的「自动识别」按钮 THEN the Batch_Evaluation_System SHALL 调用AI视觉模型识别该页码对应的学生作业图片生成基准效果
8. WHEN 自动识别完成 THEN the Batch_Evaluation_System SHALL 以模块化卡片形式展示识别结果供用户编辑调整
9. WHEN 用户编辑基准效果 THEN the Batch_Evaluation_System SHALL 支持修改每道题的answer、correct、userAnswer、mainAnswer字段

### Requirement 4: 新建批量评估任务

**User Story:** As a 测试人员, I want to 创建批量评估任务并选择待评估的作业, so that 我可以对多份AI批改结果进行统一评估。

#### Acceptance Criteria

1. WHEN 用户点击「新建任务」 THEN the Batch_Evaluation_System SHALL 显示作业任务选择界面
2. WHEN 系统展示作业任务列表 THEN the Batch_Evaluation_System SHALL 从数据库获取status=3的已批改作业记录
3. WHEN 用户选择作业任务 THEN the Batch_Evaluation_System SHALL 支持多选并显示已选数量
4. WHEN 用户确认选择 THEN the Batch_Evaluation_System SHALL 创建批量评估任务并将所有选中作业依次排列展示
5. WHEN 任务创建成功 THEN the Batch_Evaluation_System SHALL 为任务分配唯一标识并保存任务状态

### Requirement 5: 基准效果自动匹配

**User Story:** As a 测试人员, I want to 系统自动匹配已配置的基准效果, so that 我不需要为每份作业手动设置基准效果。

#### Acceptance Criteria

1. WHEN 批量评估任务创建后 THEN the Batch_Evaluation_System SHALL 根据作业的书本ID和页码自动查找匹配的数据集
2. WHEN 找到匹配的数据集 THEN the Batch_Evaluation_System SHALL 自动关联基准效果并标记为「已匹配」
3. WHEN 未找到匹配的数据集 THEN the Batch_Evaluation_System SHALL 在作业任务下方显示「自动识别」选项
4. WHEN 用户选择「自动识别」 THEN the Batch_Evaluation_System SHALL 调用AI视觉模型识别作业图片生成基准效果

### Requirement 6: 批量评估执行

**User Story:** As a 测试人员, I want to 系统依次评估所有作业任务, so that 我可以获得每份作业的评估结果。

#### Acceptance Criteria

1. WHEN 用户启动批量评估 THEN the Batch_Evaluation_System SHALL 按列表顺序依次评估每个作业任务
2. WHEN 单个作业评估完成 THEN the Batch_Evaluation_System SHALL 在任务列表中显示该作业的准确率
3. WHEN 评估过程中出错 THEN the Batch_Evaluation_System SHALL 标记该作业为「评估失败」并继续评估下一个
4. WHEN 用户点击某个作业任务 THEN the Batch_Evaluation_System SHALL 展示该作业的详细评估结果（与单次评估一致）
5. WHEN 所有作业评估完成 THEN the Batch_Evaluation_System SHALL 更新任务状态为「已完成」
6. WHEN 用户使用一键AI评估功能 THEN the Batch_Evaluation_System SHALL 并行执行所有作业的评估并按题目类型分类统计准确率
7. WHEN 一键AI评估完成 THEN the Batch_Evaluation_System SHALL 在评估结果中包含主观题准确率、客观题准确率、选择题准确率、非选择题准确率

### Requirement 7: 总体评估报告

**User Story:** As a 测试人员, I want to 查看批量评估任务的总体报告, so that 我可以了解整体AI批改效果。

#### Acceptance Criteria

1. WHEN 批量评估任务完成 THEN the Batch_Evaluation_System SHALL 生成总体评估报告
2. WHEN 展示总体报告 THEN the Batch_Evaluation_System SHALL 显示总体准确率、按书本统计、按页码统计、按题型统计
3. WHEN 用户请求AI分析 THEN the Batch_Evaluation_System SHALL 调用DeepSeek生成总结与分析文字报告
4. WHEN AI分析完成 THEN the Batch_Evaluation_System SHALL 展示教学诊断和改进建议

### Requirement 12: 题目类型分类统计

**User Story:** As a 测试人员, I want to 按题目类型分类查看准确率统计, so that 我可以了解AI批改在不同题型上的表现差异。

#### Acceptance Criteria

1. WHEN 系统读取作业数据 THEN the Batch_Evaluation_System SHALL 从zp_homework表的data_value字段解析每道题的questionType和bvalue字段
2. WHEN 系统判断题目是否为客观题 THEN the Batch_Evaluation_System SHALL 根据questionType字段值为"objective"判定为客观题，其他值判定为主观题
3. WHEN 系统判断题目是否为选择题 THEN the Batch_Evaluation_System SHALL 根据bvalue字段值为"1"判定为单选题、值为"2"判定为多选题，其他值判定为非选择题
4. WHEN 展示总体报告 THEN the Batch_Evaluation_System SHALL 显示主观题准确率和客观题准确率的分类统计
5. WHEN 展示总体报告 THEN the Batch_Evaluation_System SHALL 显示选择题准确率和非选择题准确率的分类统计
6. WHEN 展示单个作业评估详情 THEN the Batch_Evaluation_System SHALL 显示该作业的主观题准确率、客观题准确率、选择题准确率、非选择题准确率
7. WHEN 用户创建数据集 THEN the Batch_Evaluation_System SHALL 自动从zp_homework的data_value中读取并保存每道题的questionType和bvalue字段到基准效果数据中
8. WHEN 系统执行评估比对 THEN the Batch_Evaluation_System SHALL 在比对结果中标注每道题的题目类型（主观/客观、选择/非选择）

### Requirement 8: Excel导出

**User Story:** As a 测试人员, I want to 将评估结果导出为Excel文档, so that 我可以离线查看和分享评估数据。

#### Acceptance Criteria

1. WHEN 用户点击「导出Excel」 THEN the Batch_Evaluation_System SHALL 生成包含评估数据的Excel文件
2. WHEN 生成Excel文件 THEN the Batch_Evaluation_System SHALL 包含总体概览工作表（整体准确率、各作业任务指标）
3. WHEN 生成Excel文件 THEN the Batch_Evaluation_System SHALL 包含明细数据工作表（每个作业任务的详细评估数据）
4. WHEN 生成Excel文件 THEN the Batch_Evaluation_System SHALL 在总体概览工作表中包含主观题准确率、客观题准确率、选择题准确率、非选择题准确率的分类统计
5. WHEN 生成Excel文件 THEN the Batch_Evaluation_System SHALL 在明细数据工作表中标注每道题的题目类型（主观/客观、选择/非选择）
6. WHEN Excel生成完成 THEN the Batch_Evaluation_System SHALL 自动下载文件到用户本地

### Requirement 9: 任务历史管理

**User Story:** As a 测试人员, I want to 查看和管理历史批量评估任务, so that 我可以回顾之前的评估结果。

#### Acceptance Criteria

1. WHEN 用户进入批量评估页面 THEN the Batch_Evaluation_System SHALL 显示历史任务列表（按创建时间倒序）
2. WHEN 用户点击历史任务 THEN the Batch_Evaluation_System SHALL 加载并展示该任务的评估结果
3. WHEN 用户删除历史任务 THEN the Batch_Evaluation_System SHALL 移除任务记录并更新列表

### Requirement 10: 界面风格一致性

**User Story:** As a 测试人员, I want to 批量评估页面保持与现有系统一致的黑白简洁风格, so that 我可以获得统一的使用体验。

#### Acceptance Criteria

1. WHEN 展示批量评估页面 THEN the Batch_Evaluation_System SHALL 采用黑白简洁配色方案
2. WHEN 展示页面元素 THEN the Batch_Evaluation_System SHALL 不使用emoji图标
3. WHEN 展示数据表格 THEN the Batch_Evaluation_System SHALL 使用与现有系统一致的表格样式
4. WHEN 展示按钮和表单 THEN the Batch_Evaluation_System SHALL 使用与现有系统一致的组件样式

### Requirement 11: 页面结构规划

**User Story:** As a 测试人员, I want to 在统一的页面内完成任务管理和数据集管理, so that 我可以减少页面跳转获得流畅的操作体验。

#### Acceptance Criteria

1. WHEN 用户进入批量评估页面 THEN the Batch_Evaluation_System SHALL 显示顶部Tab切换（任务管理/数据集管理）
2. WHEN 用户在任务管理Tab THEN the Batch_Evaluation_System SHALL 左侧显示任务列表，右侧显示任务详情
3. WHEN 用户在数据集管理Tab THEN the Batch_Evaluation_System SHALL 左侧显示图书列表（按学科分组），右侧显示书本详情和页码数据集
4. WHEN 用户新建任务或添加数据集 THEN the Batch_Evaluation_System SHALL 使用弹窗形式处理，不跳转页面
5. WHEN 用户查看单个作业评估详情 THEN the Batch_Evaluation_System SHALL 使用抽屉或弹窗展示详细数据

