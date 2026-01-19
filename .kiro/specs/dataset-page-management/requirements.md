# Requirements Document

## Introduction

本功能增强数据集管理模块的编辑弹窗，在现有编辑界面中添加单页重新识别和单页删除功能，使用户可以更灵活地管理数据集中的各个页面，而不需要删除整个数据集重新创建。

## Glossary

- **Dataset**: 数据集，包含多个页码的基准效果数据，用于批量评估AI批改效果
- **Page**: 页码，数据集中的单个页面，包含该页的作业图片和识别结果
- **Base_Effect**: 基准效果，某一页作业的标准识别结果，包含题号、学生答案、正确性等信息
- **Recognition**: 识别，使用AI视觉模型识别作业图片中的学生答案
- **Edit_Modal**: 编辑弹窗，用于编辑数据集内容的模态对话框
- **Page_Tab**: 页码标签，编辑弹窗中用于切换不同页码的标签按钮

## Requirements

### Requirement 1: 编辑界面页面操作区

**User Story:** As a 数据管理员, I want to 在编辑弹窗中对单个页面进行操作, so that 我可以灵活管理数据集中的各个页面。

#### Acceptance Criteria

1. WHEN 编辑弹窗打开时 THEN THE Edit_Modal SHALL 在页码标签区域下方显示当前页的操作按钮区
2. THE Edit_Modal SHALL 显示"重新识别"按钮和"删除此页"按钮
3. WHEN 用户切换页码标签 THEN THE Edit_Modal SHALL 更新操作按钮区对应当前选中的页码

### Requirement 2: 单页重新识别

**User Story:** As a 数据管理员, I want to 重新识别数据集中某一页的内容, so that 我可以在识别结果不准确时重新获取该页的基准效果。

#### Acceptance Criteria

1. WHEN 用户点击"重新识别"按钮 THEN THE Edit_Modal SHALL 显示图片选择面板
2. THE 图片选择面板 SHALL 显示该页码最近可用的作业图片列表（从数据库查询）
3. WHEN 用户选择一张图片 THEN THE System SHALL 高亮显示选中的图片
4. WHEN 用户点击"开始识别"按钮 THEN THE System SHALL 调用AI视觉模型识别该图片
5. WHILE 识别进行中 THEN THE System SHALL 显示加载状态指示器
6. WHEN 识别完成 THEN THE System SHALL 用新的识别结果替换该页码的原有基准效果并更新表格显示
7. IF 识别过程中发生错误 THEN THE System SHALL 显示错误信息并保留原有数据
8. WHEN 用户点击"取消"按钮 THEN THE System SHALL 关闭图片选择面板并保持原有数据

### Requirement 3: 单页删除

**User Story:** As a 数据管理员, I want to 删除数据集中的某一页, so that 我可以移除不需要或错误的页面数据。

#### Acceptance Criteria

1. WHEN 用户点击"删除此页"按钮 THEN THE System SHALL 显示确认对话框
2. THE 确认对话框 SHALL 显示将要删除的页码信息
3. WHEN 用户确认删除且数据集有多个页码 THEN THE System SHALL 从编辑数据中移除该页码并切换到下一个可用页码
4. WHEN 用户确认删除且数据集只有一个页码 THEN THE System SHALL 提示"删除最后一页将删除整个数据集"并请求二次确认
5. IF 用户取消删除操作 THEN THE System SHALL 关闭确认对话框并保持当前状态

### Requirement 4: 图片预览

**User Story:** As a 数据管理员, I want to 在编辑界面中看到当前页的图片, so that 我可以更直观地了解数据内容。

#### Acceptance Criteria

1. WHEN 编辑弹窗打开时 THEN THE Edit_Modal SHALL 在操作区显示当前页码对应的作业图片缩略图
2. WHEN 用户切换页码标签 THEN THE Edit_Modal SHALL 更新显示对应页码的图片
3. WHEN 用户点击图片缩略图 THEN THE System SHALL 显示图片大图预览弹窗
4. IF 数据集中某页没有关联图片信息 THEN THE Edit_Modal SHALL 显示占位图并提示"无图片"

### Requirement 5: 数据保存

**User Story:** As a 数据管理员, I want to 保存对数据集的修改, so that 我的更改能够被正确保存。

#### Acceptance Criteria

1. WHEN 用户点击"保存修改"按钮 THEN THE System SHALL 将所有更改（包括重新识别和删除的页面）保存到数据集文件
2. WHEN 保存成功 THEN THE System SHALL 显示成功提示、关闭编辑弹窗并刷新数据集列表
3. IF 保存过程中发生错误 THEN THE System SHALL 显示错误信息并保留编辑弹窗状态
4. WHEN 数据集更新后 THEN THE System SHALL 同步更新数据集的题目数量和页码列表统计信息
5. IF 所有页面都被删除 THEN THE System SHALL 删除整个数据集并刷新列表
