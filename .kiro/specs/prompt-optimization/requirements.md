# Requirements Document

## Introduction

本功能为 AI 助手平台添加一个 Prompt 调优与评测功能模块，参考 PromptPilot 的设计理念。用户可以通过主界面的"提示词优化"按钮进入该功能，实现 Prompt 调试、批量评测、智能评分的完整流程。系统支持视觉理解任务（图片+Prompt），通过评测数据集对模型回答进行 1-5 分评分，帮助用户迭代优化 Prompt。

## Glossary

- **Prompt（提示词）**: 用于指导大语言模型生成特定输出的输入文本，支持 `{{变量名}}` 格式的变量占位符
- **Prompt_Optimizer（提示词优化器）**: 本系统中负责 Prompt 调试、批量评测和智能评分的核心模块
- **Test_Dataset（评测数据集）**: 包含多个测试样本的数据集合，用于评估 Prompt 效果
- **Sample（样本）**: 评测数据集中的单条记录，包含提问（图片+变量）、模型回答、理想回答、评分
- **Variable（变量）**: Prompt 中使用 `{{变量名}}` 格式定义的可替换占位符，支持文本和图像类型
- **Model_Response（模型回答）**: AI 模型对输入的响应结果
- **Ideal_Answer（理想回答）**: 用户提供或 AI 生成的标准答案，用于评分参考
- **Evaluation_Score（评分）**: 对模型回答的 1-10 分量化评分
- **Scoring_Rule（评分标准）**: 定义 1-10 分各档次的评分规则，支持用户自定义或 AI 根据 Prompt 自动生成
- **AI_Scoring（AI智能评分）**: 使用 AI 模型根据评分标准自动对模型回答进行评分
- **Version（版本）**: Prompt 的不同迭代版本，支持版本对比

## Requirements

### Requirement 1

**User Story:** As a user, I want to access the prompt optimization feature from the main interface, so that I can easily start optimizing and evaluating my prompts.

#### Acceptance Criteria

1. WHEN a user clicks the "提示词优化" button on the main interface header THEN the Prompt_Optimizer SHALL navigate to the prompt optimization page
2. WHEN the prompt optimization page loads THEN the Prompt_Optimizer SHALL display three workflow tabs: "调试", "批量", "智能优化"
3. WHEN a user switches between tabs THEN the Prompt_Optimizer SHALL preserve the current Prompt and dataset state

### Requirement 2

**User Story:** As a user, I want to debug my prompt with single samples in the "调试" workflow, so that I can test and refine my prompt before batch evaluation.

#### Acceptance Criteria

1. WHEN in "调试" tab THEN the Prompt_Optimizer SHALL display Prompt editor with variable support using `{{变量名}}` syntax
2. WHEN a user enters a Prompt with variables THEN the Prompt_Optimizer SHALL detect and display input fields for each variable
3. WHEN a variable is of image type THEN the Prompt_Optimizer SHALL display image upload area supporting local upload and URL input
4. WHEN a user clicks "生成模型回答" button THEN the Prompt_Optimizer SHALL send the Prompt with variables to the selected model and stream the response
5. WHEN model response is received THEN the Prompt_Optimizer SHALL display it in the output area with option to add "理想回答"
6. WHEN a user rates the response (1-10 score) THEN the Prompt_Optimizer SHALL record the Evaluation_Score
7. WHEN a user clicks "添加至评测集" button THEN the Prompt_Optimizer SHALL save the sample (提问、回答、评分) to the Test_Dataset

### Requirement 3

**User Story:** As a user, I want to manage batch evaluation samples in the "批量" workflow, so that I can evaluate my prompt across multiple inputs.

#### Acceptance Criteria

1. WHEN in "批量" tab THEN the Prompt_Optimizer SHALL display a data table with columns: 序号, 提问(变量), 模型回答, 理想回答, 评分
2. WHEN a user clicks "添加行" button THEN the Prompt_Optimizer SHALL add a new empty row to the Test_Dataset
3. WHEN a user clicks "上传文件" button THEN the Prompt_Optimizer SHALL allow batch import of samples from Excel/CSV file
4. WHEN a user clicks "AI生成变量" button THEN the Prompt_Optimizer SHALL use AI to generate diverse variable values based on seed samples
5. WHEN the dataset has samples THEN the Prompt_Optimizer SHALL display pagination controls with configurable items per page (10/20/50)
6. WHEN a user clicks the expand icon on a cell THEN the Prompt_Optimizer SHALL show full content in a modal dialog

### Requirement 4

**User Story:** As a user, I want to batch generate model responses, so that I can evaluate my prompt efficiently.

#### Acceptance Criteria

1. WHEN a user clicks "生成全部回答" button THEN the Prompt_Optimizer SHALL process all samples without Model_Response
2. WHEN processing samples THEN the Prompt_Optimizer SHALL show progress indicator with completed/total count
3. WHEN a model response is generated THEN the Prompt_Optimizer SHALL update the corresponding row in the data table
4. WHEN generation is running THEN the Prompt_Optimizer SHALL allow user to cancel the operation
5. WHEN all responses are generated THEN the Prompt_Optimizer SHALL display completion notification with statistics

### Requirement 5

**User Story:** As a user, I want to use AI intelligent scoring to evaluate model responses, so that I can efficiently assess prompt effectiveness.

#### Acceptance Criteria

1. WHEN a user clicks "智能评分" button THEN the Prompt_Optimizer SHALL open the scoring configuration panel
2. WHEN the scoring panel opens THEN the Prompt_Optimizer SHALL display options: "用户输入评分标准", "AI根据Prompt生成评分标准", and "AI根据用户打分学习评分标准"
3. WHEN user selects "AI根据Prompt生成评分标准" THEN the Prompt_Optimizer SHALL analyze the current Prompt and automatically generate appropriate 1-10 scoring rules
4. WHEN user selects "AI根据用户打分学习评分标准" and has at least 3 manually scored samples THEN the Prompt_Optimizer SHALL learn scoring patterns from user's scores and generate rules
5. WHEN a user clicks "为未评分的回答评分" button THEN the Prompt_Optimizer SHALL use AI to score all unscored Model_Responses on 1-10 scale
6. WHEN a user clicks "为所有回答评分" button THEN the Prompt_Optimizer SHALL use AI to re-score all Model_Responses with confirmation dialog
7. WHEN AI scoring completes for a sample THEN the Prompt_Optimizer SHALL display the score (1-10) with "AI评分" label and scoring reason

### Requirement 6

**User Story:** As a user, I want to define custom scoring rules, so that I can evaluate responses according to my specific criteria.

#### Acceptance Criteria

1. WHEN user selects "用户输入评分标准" THEN the Prompt_Optimizer SHALL display a text area for entering scoring rules
2. WHEN entering scoring rules THEN the Prompt_Optimizer SHALL support the following format for 1-10 scale:
   - 9-10分: [criteria for excellent response - fully meets requirements]
   - 7-8分: [criteria for good response - minor issues]
   - 5-6分: [criteria for acceptable response - some issues]
   - 3-4分: [criteria for poor response - major issues]
   - 1-2分: [criteria for unacceptable response - fails requirements]
3. WHEN scoring rules are saved THEN the Prompt_Optimizer SHALL validate that scoring criteria are properly defined
4. WHEN a user clicks "AI生成评分规则" button THEN the Prompt_Optimizer SHALL analyze the Prompt content and generate appropriate scoring rules automatically
5. WHEN AI generates scoring rules THEN the Prompt_Optimizer SHALL allow user to edit and customize the generated rules

### Requirement 7

**User Story:** As a user, I want to manage ideal answers for evaluation, so that I can provide reference standards for scoring.

#### Acceptance Criteria

1. WHEN a user clicks on "理想回答" cell THEN the Prompt_Optimizer SHALL open an editor for entering the ideal answer
2. WHEN a user clicks "AI生成理想回答" button THEN the Prompt_Optimizer SHALL use a more capable model to generate a reference answer
3. WHEN AI generates ideal answer THEN the Prompt_Optimizer SHALL allow user to edit and refine the generated content
4. WHEN a user clicks "批量设置理想回答" button THEN the Prompt_Optimizer SHALL open a dialog to set ideal answers for multiple samples

### Requirement 8

**User Story:** As a user, I want to view evaluation statistics and export results, so that I can analyze and share my prompt's performance.

#### Acceptance Criteria

1. WHEN samples have scores THEN the Prompt_Optimizer SHALL display summary statistics: 平均分, 评分分布 (1-5分各占比), 已评分/总数
2. WHEN a user clicks "导出为XLSX" button THEN the Prompt_Optimizer SHALL generate an Excel file with all samples and scores
3. WHEN viewing the dataset THEN the Prompt_Optimizer SHALL allow sorting by score, status, or index
4. WHEN a user clicks on a row THEN the Prompt_Optimizer SHALL allow entering "单样本调试模式" for detailed debugging

### Requirement 9

**User Story:** As a user, I want to optimize my prompt using the "智能优化" workflow, so that I can automatically improve my prompt based on evaluation results.

#### Acceptance Criteria

1. WHEN in "智能优化" tab THEN the Prompt_Optimizer SHALL check if evaluation dataset meets minimum requirements (at least 5 scored samples)
2. WHEN requirements are met THEN the Prompt_Optimizer SHALL display optimization configuration options
3. WHEN a user clicks "开始智能优化" button THEN the Prompt_Optimizer SHALL analyze low-scoring samples and generate optimized Prompt
4. WHEN optimization completes THEN the Prompt_Optimizer SHALL create a new Prompt version and display optimization report
5. WHEN viewing optimization report THEN the Prompt_Optimizer SHALL show before/after comparison of Prompt text and score distribution

### Requirement 10

**User Story:** As a user, I want to manage Prompt versions, so that I can track improvements and compare different versions.

#### Acceptance Criteria

1. WHEN a user saves a Prompt THEN the Prompt_Optimizer SHALL create a new Version with timestamp and average score
2. WHEN viewing version selector THEN the Prompt_Optimizer SHALL display all versions with their scores sorted by creation time
3. WHEN a user selects a historical version THEN the Prompt_Optimizer SHALL load that version's Prompt and associated evaluation dataset
4. WHEN a user clicks "版本比对" button THEN the Prompt_Optimizer SHALL display side-by-side comparison of two selected versions
5. WHEN comparing versions THEN the Prompt_Optimizer SHALL highlight Prompt text differences and show score comparison chart
