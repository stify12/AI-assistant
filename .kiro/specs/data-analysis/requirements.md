# Requirements Document

## Introduction

本功能为 AI 批改效果分析平台新增数据分析模块，实现一个完整的 AI 驱动工作流。用户上传多个 Excel 文件后，系统通过并发 LLM 调用完成数据解析和内容分析，每个文件的结果结构化分别输出。然后 AI 生成报告模板并编写完整报告。用户可以查看每一步的执行结果，整个流程完全由 AI 自动完成。

## Glossary

- **Task（分析任务）**: 用户创建的一次数据分析会话，包含任务元信息和关联的数据文件
- **Task_ID**: 系统为每个分析任务生成的唯一标识符
- **LLM（大语言模型）**: 用于执行工作流各步骤的 AI 模型
- **Workflow Step（工作流步骤）**: 分析流程中的一个独立阶段，每个步骤由 LLM 执行并产生可查看的结果
- **Concurrent Processing（并发处理）**: 同时处理多个文件的能力，提高处理效率
- **Structured Output（结构化输出）**: 每个文件解析后产生的格式化结果数据

## Requirements

### Requirement 1

**User Story:** As a user, I want to create analysis tasks and upload multiple data files, so that I can start the AI-driven analysis workflow.

#### Acceptance Criteria

1. WHEN a user clicks the "新建分析任务" button THEN the System SHALL display a task creation form with fields for task name and description
2. WHEN a user submits a task creation form THEN the System SHALL generate a unique task_id and store the task metadata
3. WHEN a user uploads multiple xlsx files THEN the System SHALL validate file format and size constraints (single file ≤ 10MB, maximum 10 files per task)
4. WHEN file upload completes THEN the System SHALL associate all uploaded files with the current task_id and display the workflow steps panel
5. IF a user uploads an invalid file format THEN the System SHALL reject the upload and display an error message specifying the allowed formats

### Requirement 2

**User Story:** As a user, I want the system to use LLM to parse my data files and show me the parsing results for each file, so that I can verify the data understanding before proceeding.

#### Acceptance Criteria

1. WHEN the parsing step begins THEN the System SHALL extract raw table data from each uploaded file
2. WHEN LLM parsing executes THEN the System SHALL process multiple files concurrently by sending each file's data to LLM in parallel
3. WHEN LLM parsing completes for each file THEN the System SHALL display the parsing results separately for each file including identified columns, data summary, and extracted records
4. WHEN a user views parsing results THEN the System SHALL show a list of files with expandable sections to view each file's structured parsing output
5. WHEN all files are parsed THEN the System SHALL enable the next workflow step (content analysis)

### Requirement 3

**User Story:** As a user, I want the system to use LLM to analyze the content of each file and show me the analysis results separately, so that I can understand the insights from each data source.

#### Acceptance Criteria

1. WHEN the content analysis step begins THEN the System SHALL send each file's parsed data to LLM for content analysis concurrently
2. WHEN LLM analysis executes THEN the System SHALL have LLM analyze the content, identify patterns, extract key insights, and generate structured findings for each file
3. WHEN LLM analysis completes for each file THEN the System SHALL display the analysis results separately for each file with structured output format
4. WHEN a user views analysis results THEN the System SHALL show a list of files with expandable sections to view each file's analysis output including key findings, patterns, and statistics
5. WHEN all files are analyzed THEN the System SHALL enable the next workflow step (report template generation)

### Requirement 4

**User Story:** As a user, I want the system to use LLM to generate a report template based on all analysis results, so that I can see the proposed report structure.

#### Acceptance Criteria

1. WHEN the template generation step begins THEN the System SHALL aggregate all file analysis results and send to LLM
2. WHEN LLM template generation executes THEN the System SHALL have LLM create a customized report outline based on the combined analysis findings from all files
3. WHEN LLM template generation completes THEN the System SHALL display the proposed report template including sections, headings, and content placeholders
4. WHEN a user views the template THEN the System SHALL show the complete report structure with section descriptions
5. WHEN template step completes THEN the System SHALL enable the next workflow step (report writing)

### Requirement 5

**User Story:** As a user, I want the system to use LLM to write the complete report based on the template, so that I can get a professional analysis document.

#### Acceptance Criteria

1. WHEN the report writing step begins THEN the System SHALL send the template and all previous analysis results to LLM
2. WHEN LLM report writing executes THEN the System SHALL have LLM fill in each section of the template with detailed analysis content, insights, and recommendations
3. WHEN LLM report writing completes THEN the System SHALL display the complete report content in the browser
4. WHEN a user views the report THEN the System SHALL show the full report with all sections, data summaries, and conclusions
5. WHEN report writing completes THEN the System SHALL enable the download button for Word export

### Requirement 6

**User Story:** As a user, I want to download the generated report as a Word document, so that I can share it with the team.

#### Acceptance Criteria

1. WHEN a user clicks the download button THEN the System SHALL convert the LLM-generated report content to Word format
2. WHEN Word conversion completes THEN the System SHALL provide the .docx file for download
3. WHEN generating Word document THEN the System SHALL apply professional formatting including headings, paragraphs, and tables
4. IF Word generation fails THEN the System SHALL display an error message and allow retry

### Requirement 7

**User Story:** As a user, I want to see the progress of each workflow step and each file's processing status, so that I can track the analysis process.

#### Acceptance Criteria

1. WHEN a workflow is running THEN the System SHALL display a step indicator showing current step, completed steps, and pending steps
2. WHEN processing multiple files THEN the System SHALL show individual progress for each file within the current step
3. WHEN each file completes processing THEN the System SHALL update the file status and display its result immediately
4. WHEN a user clicks on a completed step THEN the System SHALL display the results of that step with per-file breakdown
5. IF any file processing fails THEN the System SHALL display an error message for that file and allow retry for the failed file

### Requirement 8

**User Story:** As a user, I want to access the data analysis feature from the main navigation, so that I can easily find and use this functionality.

#### Acceptance Criteria

1. WHEN a user views the main page THEN the System SHALL display a "数据分析" navigation link in the sidebar footer
2. WHEN a user clicks the "数据分析" link THEN the System SHALL navigate to the data analysis page
3. WHEN a user views the data analysis page THEN the System SHALL display the task list and task creation interface
4. WHEN a user has existing tasks THEN the System SHALL display a list of previous tasks with workflow status indicators
