# Design Document

## Overview

本设计文档描述了将 `app.py`（约 8674 行）重构为模块化架构的详细方案。重构采用 Flask Blueprint 机制，将代码按功能拆分为独立模块，同时保持所有现有功能和 API 行为完全不变。

## Architecture

```
ai-grading-platform/
├── app.py                    # 精简入口（<100行）
├── config.json               # 配置文件（保持不变）
├── prompts.json              # 提示词文件（保持不变）
│
├── routes/                   # 路由模块
│   ├── __init__.py          # 蓝图注册与导出
│   ├── common.py            # 通用路由（首页、配置、会话）
│   ├── batch_compare.py     # 批量对比评估 API
│   ├── prompt_manage.py     # 提示词管理 API
│   ├── chat.py              # 聊天与 MCP 工具 API
│   ├── ai_eval.py           # AI 评估（Qwen/DeepSeek）API
│   ├── subject_grading.py   # 学科批改评估 API
│   ├── model_recommend.py   # 模型推荐 API
│   ├── prompt_optimize.py   # Prompt 优化评测 API
│   ├── data_analysis.py     # 数据分析 API
│   ├── batch_evaluation.py  # 批量评估任务 API
│   └── dataset_manage.py    # 数据集管理 API
│
├── services/                 # 服务层
│   ├── __init__.py
│   ├── config_service.py    # 配置管理服务
│   ├── session_service.py   # 会话管理服务
│   ├── llm_service.py       # LLM 调用服务
│   ├── database_service.py  # 数据库服务
│   └── storage_service.py   # 文件存储服务
│
├── utils/                    # 工具函数
│   ├── __init__.py
│   ├── file_utils.py        # 文件操作工具
│   └── text_utils.py        # 文本处理工具
│
└── knowledge_agent/          # 已有模块（保持不变）
    ├── __init__.py
    ├── routes.py
    ├── agent.py
    ├── models.py
    ├── services.py
    └── tools.py
```

## Components and Interfaces

### 1. 入口文件 (app.py)

精简的 Flask 应用入口，仅负责：
- 创建 Flask 应用实例
- 注册所有蓝图
- 启动应用

```python
# app.py 结构示意
from flask import Flask
from routes import register_blueprints
from knowledge_agent.routes import knowledge_agent_bp

app = Flask(__name__)
register_blueprints(app)
app.register_blueprint(knowledge_agent_bp)

if __name__ == '__main__':
    app.run(debug=True, port=5000)
```

### 2. 路由模块 (routes/)

#### 2.1 routes/__init__.py
```python
def register_blueprints(app):
    """注册所有蓝图"""
    from .common import common_bp
    from .batch_compare import batch_compare_bp
    from .prompt_manage import prompt_manage_bp
    from .chat import chat_bp
    from .ai_eval import ai_eval_bp
    from .subject_grading import subject_grading_bp
    from .model_recommend import model_recommend_bp
    from .prompt_optimize import prompt_optimize_bp
    from .data_analysis import data_analysis_bp
    from .batch_evaluation import batch_evaluation_bp
    from .dataset_manage import dataset_manage_bp
    
    app.register_blueprint(common_bp)
    app.register_blueprint(batch_compare_bp, url_prefix='/api/batch-compare')
    app.register_blueprint(prompt_manage_bp, url_prefix='/api')
    app.register_blueprint(chat_bp, url_prefix='/api')
    app.register_blueprint(ai_eval_bp, url_prefix='/api')
    app.register_blueprint(subject_grading_bp, url_prefix='/api/grading')
    app.register_blueprint(model_recommend_bp, url_prefix='/api')
    app.register_blueprint(prompt_optimize_bp, url_prefix='/api')
    app.register_blueprint(data_analysis_bp, url_prefix='/api/analysis')
    app.register_blueprint(batch_evaluation_bp, url_prefix='/api/batch')
    app.register_blueprint(dataset_manage_bp, url_prefix='/api/dataset')
```

#### 2.2 各路由模块职责

| 模块 | 职责 | 主要路由 |
|------|------|----------|
| common.py | 首页、配置、会话管理 | `/`, `/compare`, `/api/config`, `/api/session` |
| batch_compare.py | 批量对比分析 | `/analyze`, `/report`, `/export-report` |
| prompt_manage.py | 提示词 CRUD | `/prompts`, `/optimize-prompt` |
| chat.py | 聊天、MCP 工具 | `/chat`, `/mcp-servers`, `/mcp-tools` |
| ai_eval.py | AI 评估功能 | `/qwen/*`, `/deepseek/*`, `/eval/*` |
| subject_grading.py | 学科批改 | `/homework`, `/recognize`, `/evaluate` |
| model_recommend.py | 模型推荐 | `/recommend`, `/model-stats`, `/multi-model-compare` |
| prompt_optimize.py | Prompt 优化 | `/prompt-tasks`, `/prompt-eval/*` |
| data_analysis.py | 数据分析 | `/tasks`, `/workflow/*` |
| batch_evaluation.py | 批量评估 | `/books`, `/datasets`, `/tasks` |
| dataset_manage.py | 数据集管理 | `/available-homework`, `/recognize` |

### 3. 服务层 (services/)

#### 3.1 config_service.py
```python
class ConfigService:
    CONFIG_FILE = 'config.json'
    PROMPTS_FILE = 'prompts.json'
    
    @staticmethod
    def load_config() -> dict
    @staticmethod
    def save_config(config: dict) -> None
    @staticmethod
    def load_prompts() -> list
    @staticmethod
    def save_prompts(prompts: list) -> None
```

#### 3.2 session_service.py
```python
class SessionService:
    SESSIONS_DIR = 'sessions'
    CHAT_SESSIONS_DIR = 'chat_sessions'
    
    @staticmethod
    def load_session(session_id: str) -> dict
    @staticmethod
    def save_session(session_id: str, data: dict) -> None
    @staticmethod
    def clear_session(session_id: str) -> None
    @staticmethod
    def get_all_sessions() -> list
```

#### 3.3 llm_service.py
```python
class LLMService:
    @staticmethod
    def call_qwen(prompt: str, system_prompt: str = None) -> dict
    @staticmethod
    def call_deepseek(prompt: str, system_prompt: str = None) -> dict
    @staticmethod
    def call_vision_model(image: str, prompt: str, model: str = None) -> dict
    @staticmethod
    def parse_json_response(content: str) -> dict
```

#### 3.4 database_service.py
```python
class DatabaseService:
    @staticmethod
    def get_connection()
    @staticmethod
    def execute_query(sql: str, params: tuple = None) -> list
    @staticmethod
    def execute_update(sql: str, params: tuple = None) -> int
```

#### 3.5 storage_service.py
```python
class StorageService:
    @staticmethod
    def ensure_dir(path: str) -> None
    @staticmethod
    def load_json(filepath: str) -> dict
    @staticmethod
    def save_json(filepath: str, data: dict) -> None
    @staticmethod
    def list_json_files(directory: str) -> list
    @staticmethod
    def delete_file(filepath: str) -> bool
```

### 4. 工具函数 (utils/)

#### 4.1 file_utils.py
```python
def get_file_path(directory: str, filename: str) -> str
def generate_unique_id() -> str
def safe_filename(name: str) -> str
```

#### 4.2 text_utils.py
```python
def normalize_answer(text: str) -> str
def extract_json_from_text(text: str) -> dict
def remove_think_tags(content: str) -> str
```

## Data Models

数据模型保持不变，继续使用 JSON 文件存储：

| 数据类型 | 存储位置 | 格式 |
|----------|----------|------|
| 配置 | config.json | JSON |
| 提示词 | prompts.json | JSON Array |
| 会话 | sessions/*.json | JSON |
| 聊天会话 | chat_sessions/*.json | JSON |
| 分析任务 | analysis_tasks/*.json | JSON |
| Prompt任务 | prompt_tasks/*.json | JSON |
| 批量任务 | batch_tasks/*.json | JSON |
| 数据集 | datasets/*.json | JSON |
| 基准效果 | baseline_effects/*.json | JSON |

## Correctness Properties

*A property is a characteristic or behavior that should hold true across all valid executions of a system-essentially, a formal statement about what the system should do. Properties serve as the bridge between human-readable specifications and machine-verifiable correctness guarantees.*

### Property 1: Blueprint Registration Completeness
*For any* route that existed in the original app.py, after refactoring there SHALL exist a corresponding route registered through one of the blueprints with the same URL path and HTTP methods.
**Validates: Requirements 1.1, 3.1-3.8**

### Property 2: API Response Preservation
*For any* API endpoint and any valid request parameters, the refactored application SHALL return a response with identical JSON structure, status code, and content-type as the original application.
**Validates: Requirements 1.3, 6.2**

### Property 3: Service Layer Data Consistency
*For any* configuration or session data operation (load/save), the service layer functions SHALL produce identical results as the original inline functions in app.py.
**Validates: Requirements 2.1, 2.2**

### Property 4: Session Round-Trip Integrity
*For any* valid session data, saving the data followed by loading with the same session_id SHALL return data equivalent to the original saved data.
**Validates: Requirements 2.2**

## Error Handling

错误处理策略保持不变：
- API 错误返回 JSON 格式 `{'error': 'message'}` 和适当的 HTTP 状态码
- 服务层异常向上传播，由路由层统一处理
- 数据库连接错误返回 500 状态码

## Testing Strategy

### Unit Tests
- 测试各服务层函数的独立功能
- 测试工具函数的正确性
- 使用 pytest 框架

### Property-Based Tests
使用 Hypothesis 库进行属性测试：
- 测试 API 端点保持性（Property 1）
- 测试配置一致性（Property 4）
- 测试会话数据完整性（Property 5）

### Integration Tests
- 测试蓝图注册完整性
- 测试端到端 API 调用
- 对比重构前后的响应

测试配置：
- 使用 Hypothesis 库，每个属性测试运行至少 100 次迭代
- 测试文件位于 `tests/` 目录
- 测试命名格式：`test_<module>_<property>.py`
