# Requirements Document

## Introduction

本文档定义了对 AI 批改效果分析平台主应用文件 `app.py` 进行代码重构的需求。当前 `app.py` 文件包含约 8674 行代码，将所有功能混合在一个文件中，导致代码难以维护和阅读。重构目标是将代码按功能模块拆分，提高可读性、可维护性和可测试性，同时保证所有现有功能和逻辑完全不变。

## Glossary

- **Flask Blueprint**: Flask 的蓝图机制，用于将应用拆分为多个模块
- **Route**: Flask 路由，定义 URL 与处理函数的映射
- **API**: 应用程序接口，提供 HTTP 端点供前端调用
- **Service**: 业务逻辑服务层，封装核心业务逻辑
- **Utils**: 工具函数模块，提供通用辅助功能

## Requirements

### Requirement 1

**User Story:** As a developer, I want the codebase to be organized into logical modules, so that I can easily navigate and understand the code structure.

#### Acceptance Criteria

1. WHEN the application starts THEN the system SHALL load all route blueprints and register them with the Flask app
2. WHEN a developer opens the project THEN the system SHALL present a clear directory structure with modules separated by functionality
3. WHEN code is refactored THEN the system SHALL maintain all existing API endpoints with identical request/response behavior

### Requirement 2

**User Story:** As a developer, I want configuration and utility functions separated from route handlers, so that I can reuse them across modules.

#### Acceptance Criteria

1. WHEN configuration is needed THEN the system SHALL provide centralized config loading functions from a dedicated config module
2. WHEN session management is needed THEN the system SHALL provide session utilities from a dedicated utils module
3. WHEN file operations are needed THEN the system SHALL provide file handling utilities from a dedicated utils module

### Requirement 3

**User Story:** As a developer, I want each functional area to have its own module, so that I can work on features independently.

#### Acceptance Criteria

1. WHEN batch comparison features are accessed THEN the system SHALL route requests to the batch_compare module
2. WHEN prompt optimization features are accessed THEN the system SHALL route requests to the prompt_optimize module
3. WHEN data analysis features are accessed THEN the system SHALL route requests to the data_analysis module
4. WHEN subject grading features are accessed THEN the system SHALL route requests to the subject_grading module
5. WHEN chat/AI features are accessed THEN the system SHALL route requests to the chat module
6. WHEN MCP tools features are accessed THEN the system SHALL route requests to the mcp_tools module
7. WHEN model recommendation features are accessed THEN the system SHALL route requests to the model_recommend module
8. WHEN batch evaluation features are accessed THEN the system SHALL route requests to the batch_evaluation module

### Requirement 4

**User Story:** As a developer, I want the main app.py to be minimal and focused on application setup, so that it serves as a clear entry point.

#### Acceptance Criteria

1. WHEN the main app.py is opened THEN the system SHALL show only Flask app initialization and blueprint registration
2. WHEN the main app.py is opened THEN the system SHALL contain less than 100 lines of code
3. WHEN blueprints are registered THEN the system SHALL use consistent URL prefixes for each module

### Requirement 5

**User Story:** As a developer, I want shared services and utilities to be accessible from any module, so that I can avoid code duplication.

#### Acceptance Criteria

1. WHEN LLM API calls are needed THEN the system SHALL provide a centralized LLM service with Qwen and DeepSeek support
2. WHEN database connections are needed THEN the system SHALL provide a centralized database service
3. WHEN file storage operations are needed THEN the system SHALL provide centralized storage utilities

### Requirement 6

**User Story:** As a tester, I want the refactored code to pass all existing tests, so that I can be confident the refactoring didn't break functionality.

#### Acceptance Criteria

1. WHEN existing tests are run THEN the system SHALL pass all tests without modification
2. WHEN API endpoints are called THEN the system SHALL return identical responses as before refactoring
