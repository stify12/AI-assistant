# Requirements Document

## Introduction

本需求文档描述数据集管理和批量评估模块的优化功能。当前系统中，数据集只能通过 book_id + pages 来标识，无法自定义命名。当同一本书的相同页码存在多个数据集时（如不同学生的答案作为基准），系统无法区分，批量评估时也无法让用户选择使用哪个数据集。本次优化将支持数据集自定义命名，并在批量评估时允许用户选择特定数据集。

## Glossary

- **Dataset**: 数据集，存储基准效果数据的集合，用于与AI批改结果进行对比评估
- **Dataset_Manager**: 数据集管理模块，负责数据集的创建、编辑、删除等操作
- **Batch_Evaluator**: 批量评估模块，负责执行批量评估任务，将AI批改结果与基准效果对比
- **Base_Effect**: 基准效果，人工标注的正确答案和判断结果，作为评估AI批改准确性的标准
- **Book_ID**: 书本唯一标识符
- **Page_Num**: 页码编号
- **Dataset_Name**: 数据集名称，用户自定义的数据集标识名称
- **Duplicate_Dataset**: 重复数据集，指同一 book_id + page_num 组合存在多个数据集的情况
- **Dataset_Description**: 数据集描述，用户可选填的详细说明信息

## Requirements

### Requirement 1: 数据集自定义命名

**User Story:** As a 评估人员, I want to 为数据集设置自定义名称, so that 我可以区分同一本书相同页码的不同数据集。

#### Acceptance Criteria

1. WHEN 用户创建新数据集时, THE Dataset_Manager SHALL 提供名称输入字段，允许用户输入自定义名称
2. WHEN 用户未输入数据集名称时, THE Dataset_Manager SHALL 自动生成默认名称，格式为"书名_页码范围_创建时间"
3. WHEN 用户编辑已有数据集时, THE Dataset_Manager SHALL 允许修改数据集名称
4. THE Dataset_Manager SHALL 在数据集列表中显示数据集名称作为主要标识
5. WHEN 数据集名称为空或仅包含空白字符时, THE Dataset_Manager SHALL 拒绝保存并提示用户输入有效名称
6. WHEN 用户创建或编辑数据集时, THE Dataset_Manager SHALL 提供可选的描述字段，允许用户添加备注说明

### Requirement 2: 数据库结构扩展

**User Story:** As a 系统开发者, I want to 扩展数据库结构支持数据集命名, so that 数据集名称可以持久化存储。

#### Acceptance Criteria

1. THE Database_Service SHALL 在 datasets 表中新增 name 字段（VARCHAR 200）存储数据集名称
2. WHEN 读取现有数据集时, THE Database_Service SHALL 兼容无 name 字段的旧数据，自动生成默认名称
3. WHEN 保存数据集时, THE Database_Service SHALL 将 name 字段与其他字段一同持久化
4. THE Database_Service SHALL 支持按 name 字段进行模糊搜索查询
5. THE Database_Service SHALL 确保 name 字段允许为空，以兼容旧数据

### Requirement 3: 数据集列表展示优化

**User Story:** As a 评估人员, I want to 在数据集列表中清晰看到每个数据集的名称和关键信息, so that 我可以快速识别和选择需要的数据集。

#### Acceptance Criteria

1. THE Dataset_Manager SHALL 在数据集列表中显示：数据集名称、书名、页码范围、题目数量、创建时间
2. WHEN 同一本书存在多个数据集时, THE Dataset_Manager SHALL 在列表中明确标识每个数据集的名称
3. THE Dataset_Manager SHALL 支持按数据集名称进行搜索筛选
4. THE Dataset_Manager SHALL 支持按创建时间排序数据集列表
5. WHEN 数据集有描述信息时, THE Dataset_Manager SHALL 在列表中显示描述的摘要或提供查看入口

### Requirement 4: 批量评估时选择数据集

**User Story:** As a 评估人员, I want to 在批量评估时选择使用哪个数据集, so that 当存在多个相同页码的数据集时我可以指定使用特定的基准效果。

#### Acceptance Criteria

1. WHEN 批量评估任务中的作业存在多个匹配数据集时, THE Batch_Evaluator SHALL 提示用户选择要使用的数据集
2. WHEN 用户手动匹配数据集时, THE Batch_Evaluator SHALL 显示所有匹配的数据集列表，包含名称、题目数量等信息
3. WHEN 只有一个匹配数据集时, THE Batch_Evaluator SHALL 自动使用该数据集，无需用户选择
4. THE Batch_Evaluator SHALL 在作业详情中显示当前使用的数据集名称
5. WHEN 用户更换作业匹配的数据集时, THE Batch_Evaluator SHALL 清除该作业的评估结果，标记为待重新评估
6. THE Batch_Evaluator SHALL 支持批量为多个作业选择同一数据集

### Requirement 5: 数据集匹配逻辑优化

**User Story:** As a 系统开发者, I want to 优化数据集匹配逻辑, so that 系统能正确处理同一 book_id + page_num 存在多个数据集的情况。

#### Acceptance Criteria

1. WHEN 查询匹配数据集时, THE Batch_Evaluator SHALL 返回所有符合 book_id + page_num 条件的数据集列表
2. WHEN 存在多个匹配数据集时, THE Batch_Evaluator SHALL 按创建时间倒序排列，最新的排在前面
3. IF 自动匹配时存在多个数据集, THEN THE Batch_Evaluator SHALL 默认选择最新创建的数据集
4. THE Batch_Evaluator SHALL 在任务数据中记录每个作业使用的数据集ID和名称
5. THE Batch_Evaluator SHALL 提供API接口查询指定 book_id + page_num 的所有可用数据集

### Requirement 6: 兼容现有数据

**User Story:** As a 系统管理员, I want to 确保现有数据集数据在升级后仍可正常使用, so that 不会因为功能升级导致数据丢失或不可用。

#### Acceptance Criteria

1. WHEN 读取无 name 字段的现有数据集时, THE Database_Service SHALL 自动生成默认名称用于显示
2. THE Dataset_Manager SHALL 正常读取和显示升级前创建的数据集
3. THE Batch_Evaluator SHALL 正常使用升级前创建的数据集进行评估
4. WHEN 编辑旧数据集时, THE Dataset_Manager SHALL 允许为其添加自定义名称
5. THE Database_Service SHALL 提供数据迁移脚本，为现有数据集批量生成默认名称

### Requirement 7: 数据集重复检测与提示

**User Story:** As a 评估人员, I want to 在创建数据集时知道是否已存在相同页码的数据集, so that 我可以决定是创建新数据集还是编辑现有数据集。

#### Acceptance Criteria

1. WHEN 用户选择页码创建数据集时, THE Dataset_Manager SHALL 检查是否已存在相同 book_id + page_num 的数据集
2. IF 存在重复数据集, THEN THE Dataset_Manager SHALL 显示提示信息，列出已有数据集的名称和创建时间
3. THE Dataset_Manager SHALL 允许用户选择继续创建新数据集或跳转编辑现有数据集
4. THE Dataset_Manager SHALL 在提示中明确说明创建多个数据集的用途场景
