# Requirements Document

## Introduction

本需求文档定义了批量评估模块Excel导出功能的优化需求。当前导出功能已包含7个工作表，但存在数据不完整、缺少关键信息、缺少汇总统计等问题。本次优化旨在提供更完整、更易分析的Excel报告，同时保持向后兼容性。

## Glossary

- **System**: AI批改效果分析平台的批量评估模块
- **Excel_Exporter**: Excel报告生成器
- **Task_Data**: 批量评估任务数据
- **Homework_Item**: 单个作业项数据
- **Base_Effect**: 基准效果数据（标准答案）
- **AI_Result**: AI批改结果数据
- **Dataset**: 数据集（包含基准效果）
- **Error_Detail**: 错误详情记录
- **Essay_Score**: 英语作文评分数据
- **Similarity**: 语文模糊匹配相似度
- **Question_Type**: 题目类型（选择题、客观填空题、主观题）

## Requirements

### Requirement 1: 数据完整性增强

**User Story:** 作为评估人员，我希望导出的Excel包含完整的评估数据，以便进行全面分析。

#### Acceptance Criteria

1. WHEN 导出错误详情表时，THE System SHALL 填充基准用户答案、AI识别答案、基准判断、AI判断等所有字段
2. WHEN 作业包含学生信息时，THE System SHALL 在所有相关表格中包含学生姓名和学生ID
3. WHEN 作业包含作业ID时，THE System SHALL 在题目明细表和错误详情表中包含作业ID
4. WHEN 任务使用了数据集时，THE System SHALL 在评估总结表中显示数据集名称、描述和创建时间
5. WHEN 英语学科包含作文评分时，THE System SHALL 提取并导出作文评分数据
6. WHEN 语文学科使用模糊匹配时，THE System SHALL 在错误详情中显示相似度百分比
7. WHEN 题目有题型信息时，THE System SHALL 在题目明细表中显示题型分类（选择题/客观填空题/主观题）

### Requirement 2: 新增汇总统计工作表

**User Story:** 作为评估人员，我希望按不同维度查看统计数据，以便快速定位问题。

#### Acceptance Criteria

1. WHEN 导出Excel时，THE System SHALL 创建"按学生统计"工作表
2. WHEN 创建按学生统计表时，THE System SHALL 包含学生姓名、作业数、总题数、正确数、错误数、准确率、各题型准确率
3. WHEN 导出Excel时，THE System SHALL 创建"按页码统计"工作表
4. WHEN 创建按页码统计表时，THE System SHALL 包含页码、作业数、总题数、正确数、错误数、准确率、错误类型分布
5. WHEN 导出Excel时，THE System SHALL 创建"按题型统计"工作表
6. WHEN 创建按题型统计表时，THE System SHALL 包含题型名称、总题数、正确数、错误数、准确率、错误类型分布
7. WHEN 学科为英语且包含作文时，THE System SHALL 创建"英语作文评分"工作表
8. WHEN 创建作文评分表时，THE System SHALL 包含学生姓名、题号、参考得分、综合评价、改进建议

### Requirement 3: 样式和可读性优化

**User Story:** 作为评估人员，我希望Excel报告样式统一且易读，以便快速理解数据。

#### Acceptance Criteria

1. WHEN 导出Excel时，THE System SHALL 使用统一的黑白简洁配色方案
2. WHEN 设置表头样式时，THE System SHALL 使用黑色背景（#1D1D1F）和白色文字
3. WHEN 显示准确率时，THE System SHALL 使用条件格式（>=90%绿色，70-90%黄色，<70%红色）
4. WHEN 创建工作表时，THE System SHALL 为所有表格添加筛选器
5. WHEN 创建工作表时，THE System SHALL 冻结首行表头
6. WHEN 设置列宽时，THE System SHALL 根据内容自动调整列宽
7. WHEN 显示数值时，THE System SHALL 使用居中对齐
8. WHEN 显示长文本时，THE System SHALL 使用自动换行

### Requirement 4: 图表优化

**User Story:** 作为评估人员，我希望图表更直观且与数据表集成，以便快速理解趋势。

#### Acceptance Criteria

1. WHEN 创建图表时，THE System SHALL 将图表放置在对应数据表的右侧或下方
2. WHEN 创建错误类型分布图时，THE System SHALL 使用饼图显示占比
3. WHEN 创建题型准确率对比图时，THE System SHALL 使用柱状图显示对比
4. WHEN 创建按学生统计图时，THE System SHALL 添加准确率趋势折线图
5. WHEN 创建按页码统计图时，THE System SHALL 添加错误分布柱状图
6. WHEN 图表数据为空时，THE System SHALL 跳过图表创建
7. WHEN 创建图表时，THE System SHALL 使用简洁的黑白配色

### Requirement 5: 题目明细表增强

**User Story:** 作为评估人员，我希望题目明细表包含更多信息，以便详细分析每道题。

#### Acceptance Criteria

1. WHEN 导出题目明细时，THE System SHALL 包含题目类型（选择题/客观填空题/主观题）
2. WHEN 导出题目明细时，THE System SHALL 包含标准答案字段
3. WHEN 导出题目明细时，THE System SHALL 包含AI判断结果（yes/no）
4. WHEN 导出题目明细时，THE System SHALL 包含基准判断结果（yes/no）
5. WHEN 题目有相似度数据时，THE System SHALL 在题目明细中显示相似度
6. WHEN 题目有错误类型时，THE System SHALL 在题目明细中显示错误类型
7. WHEN 题目有错误说明时，THE System SHALL 在题目明细中显示错误说明

### Requirement 6: 错误详情表增强

**User Story:** 作为评估人员，我希望错误详情表包含完整的对比信息，以便分析错误原因。

#### Acceptance Criteria

1. WHEN 导出错误详情时，THE System SHALL 从基准效果数据中提取基准用户答案
2. WHEN 导出错误详情时，THE System SHALL 从AI批改结果中提取AI识别答案
3. WHEN 导出错误详情时，THE System SHALL 从基准效果数据中提取基准判断结果
4. WHEN 导出错误详情时，THE System SHALL 从AI批改结果中提取AI判断结果
5. WHEN 导出错误详情时，THE System SHALL 包含标准答案字段
6. WHEN 错误有相似度数据时，THE System SHALL 在错误详情中显示相似度百分比
7. WHEN 错误有严重程度时，THE System SHALL 在错误详情中显示严重程度（high/medium/low）

### Requirement 7: 数据集信息展示

**User Story:** 作为评估人员，我希望了解使用的数据集信息，以便追溯评估依据。

#### Acceptance Criteria

1. WHEN 任务使用了数据集时，THE System SHALL 在评估总结表中添加"数据集信息"部分
2. WHEN 显示数据集信息时，THE System SHALL 包含数据集名称
3. WHEN 显示数据集信息时，THE System SHALL 包含数据集描述
4. WHEN 显示数据集信息时，THE System SHALL 包含数据集创建时间
5. WHEN 显示数据集信息时，THE System SHALL 包含数据集包含的页码列表
6. WHEN 显示数据集信息时，THE System SHALL 包含数据集题目总数
7. WHEN 作业使用不同数据集时，THE System SHALL 在作业明细表中显示对应的数据集名称

### Requirement 8: 英语作文评分导出

**User Story:** 作为英语教师，我希望导出英语作文的评分数据，以便分析作文批改效果。

#### Acceptance Criteria

1. WHEN 学科为英语且包含作文时，THE System SHALL 检测作文评分数据
2. WHEN 检测到作文评分时，THE System SHALL 创建"英语作文评分"工作表
3. WHEN 导出作文评分时，THE System SHALL 包含学生姓名、学生ID、题号
4. WHEN 导出作文评分时，THE System SHALL 包含参考得分
5. WHEN 导出作文评分时，THE System SHALL 包含综合评价
6. WHEN 导出作文评分时，THE System SHALL 包含针对性改进建议
7. WHEN 导出作文评分时，THE System SHALL 计算平均分、最高分、最低分
8. WHEN 导出作文评分时，THE System SHALL 添加得分分布统计

### Requirement 9: 性能优化

**User Story:** 作为评估人员，我希望大量数据时导出速度快，以便提高工作效率。

#### Acceptance Criteria

1. WHEN 导出数据量超过1000条时，THE System SHALL 使用批量写入优化性能
2. WHEN 创建图表时，THE System SHALL 限制数据点数量避免性能问题
3. WHEN 处理大量错误详情时，THE System SHALL 使用流式处理避免内存溢出
4. WHEN 导出Excel时，THE System SHALL 显示进度提示
5. WHEN 导出失败时，THE System SHALL 返回明确的错误信息
6. WHEN 导出成功时，THE System SHALL 记录导出日志

### Requirement 10: 向后兼容性

**User Story:** 作为系统管理员，我希望新功能兼容旧数据，以便历史任务也能正常导出。

#### Acceptance Criteria

1. WHEN 旧任务缺少数据集信息时，THE System SHALL 跳过数据集信息部分
2. WHEN 旧任务缺少题型信息时，THE System SHALL 使用默认题型分类
3. WHEN 旧任务缺少学生信息时，THE System SHALL 显示"未知学生"
4. WHEN 旧任务缺少相似度信息时，THE System SHALL 跳过相似度显示
5. WHEN 旧任务缺少作文评分时，THE System SHALL 跳过作文评分工作表
6. WHEN 旧任务数据结构不完整时，THE System SHALL 使用默认值填充
7. WHEN 导出旧任务时，THE System SHALL 不报错且生成有效的Excel文件
