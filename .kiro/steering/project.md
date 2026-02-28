# AI批改效果分析平台

## 产品定位
面向教育科技团队的 AI 批改效果分析平台，量化评估 AI 批改准确性、追踪效果趋势。

## 核心功能

| 模块 | 路由 | 功能 |
|------|------|------|
| 测试计划看板 | `/` | Dashboard，测试计划管理、工作流状态追踪 |
| 批量评估 | `/batch-evaluation` | 批量评估 AI 批改结果，按题型统计 |
| 学科批改 | `/subject-grading` | 单份作业实时批改评估 |
| 知识点类题 | `/knowledge-agent` | 提取知识点，生成类似题目 |
| 数据分析 | `/data-analysis` | 可视化统计分析、多维下钻 |
| 数据集管理 | `/dataset-manage` | 管理基准效果数据集 |
| 提示词优化 | `/prompt-optimize` | Prompt 调试、版本管理 |
| 错误样本库 | `/error-samples` | 错误样本收集与分析 |
| 测试用例生成 | `/testcase-generator` | AI 自动生成基准效果 |
| RFID 模拟器 | `/rfid-simulator` | 远程控制安卓设备模拟 RFID 刷卡 |
| NFC App API | `/api/nfc/*` | 安卓 NFC App 数据接口（文件缓存） |
| 智能发布 | `/api/smart-publish/*` | 一键发布作业 + 自动提交工作流 |
| 流程编排 | `/api/workflow/*` | 可视化工作流编排与执行 |
| 自动化管理 | `/api/automation/*` | 自动化任务配置与调度 |
| 认证 | `/api/auth/*` | 用户登录、注册、Token 管理 |

---

## 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Flask + Gevent + Gunicorn + PyMySQL + DBUtils连接池 |
| 前端 | Jinja2 + 原生 CSS/JS (模块化) |
| WebSocket | flask-sock (RFID 模拟器) |
| 调度 | APScheduler (测试计划、日报、统计快照) |
| AI | 豆包视觉 / DeepSeek / Qwen3 / 智谱GLM-4 |
| 部署 | Docker + Docker Compose |

---

## 项目结构

```
├── app.py                 # Flask 入口 (gevent monkey patch + WebSocket + APScheduler)
├── config.json            # 配置 (API密钥、数据库)
├── routes/                # Flask 蓝图路由 (36个)
├── services/              # 业务服务层 (38个)
├── knowledge_agent/       # 知识点类题模块 (agent/models/routes/services/tools)
├── templates/             # Jinja2 模板 (14个页面)
├── static/js/             # JS (页面脚本 + modules/ + components/)
├── static/css/            # CSS (页面样式 + modules/)
├── tools/                 # 工具脚本 (adb_client.py 等)
├── utils/                 # 工具函数 (text_utils.py 等)
└── tests/                 # 测试
```

### 命名约定
- 路由: `snake_case.py` → 蓝图 `feature_name_bp`
- API: `/api/feature-name/action`
- 模板/样式: `feature-name.html/css/js`

---

## 服务层架构

| 类别 | 服务 | 职责 |
|------|------|------|
| 核心 | DatabaseService | 业务数据库 zpsmart（DBUtils 连接池，maxconn=10） |
| 核心 | AppDatabaseService | 应用数据库 aiuser（直连，含数据集/批量任务/会话/用户 CRUD） |
| 核心 | ConfigService | 多层配置：文件 → 环境变量 → 用户DB → 请求头 |
| 核心 | StorageService | 双模式存储：文件 / 数据库（USE_DB_STORAGE 环境变量切换） |
| 核心 | LLMService | 多模型调用 + 异步并行 + 重试 + Token 日志 |
| 核心 | DashboardService | 看板统计 + 内存缓存（5/15/30分钟 TTL） |
| 业务 | SemanticEvalService | 规则预检 + LLM 语义评估 |
| 业务 | AIAnalysisService | AI 分析与报告生成 |
| 业务 | LLMAnalysisService | LLM 驱动的深度分析 |
| 业务 | AnalysisService | 数据分析服务 |
| 业务 | PromptConfigService | 提示词配置（从 zpsmart 读取） |
| 业务 | TestPlanService | 测试计划 CRUD |
| 业务 | AutomationService | 自动化任务管理 |
| 业务 | WorkflowService | 可视化工作流编排（坐标配置） |
| 业务 | SmartPublishService | 一键发布（教师查询 + Java后端集成） |
| 业务 | HomeworkPublishService | Java 后端 API 集成（发布/提交作业） |
| 业务 | UnifiedScheduleService | APScheduler 统一调度（cron 触发） |
| 业务 | BatchCompareService | 批次对比分析 |
| 业务 | AutoMergeService | 自动合并服务 |
| 业务 | ReportService | 报告生成 |
| 业务 | TestcaseGeneratorService | 测试用例生成 |
| 学科 | MathEval | LaTeX→Unicode 数学公式标准化 |
| 学科 | PhysicsEval | 物理公式标准化（复用 MathEval） |
| 学科 | ChemistryEval | 化学 Markdown 标准化（复用 PhysicsEval） |
| 分析 | ErrorSampleService | 错误样本管理 |
| 分析 | ErrorCorrelationService | 错误关联分析 |
| 分析 | AnomalyService | 异常检测 |
| 分析 | ClusteringService | 错误聚类 |
| 分析 | OptimizationService | 优化建议 |
| 分析 | DrilldownService | 数据下钻 |
| 分析 | BestPracticeService | 最佳实践库 |
| 工具 | RfidSimulatorService | RFID 模拟器（文件状态 + WebSocket getter 注入） |
| 工具 | ExcelExportService | Excel 导出 |
| 工具 | TaskAssignmentService | 任务分配 |
| 工具 | SavedFilterService | 保存筛选条件 |
| 工具 | AuthService | 认证（密码哈希 + Token） |
| 工具 | SessionService | 会话管理 |
| 工具 | ScheduleService | 旧调度服务（被 UnifiedScheduleService 替代） |

---

## 配置优先级

```
文件 config.json → 环境变量 → 用户数据库配置 → 请求头 (X-Doubao-Api-Key 等)
```

后者覆盖前者。环境变量映射见 `ConfigService.ENV_MAPPINGS`，请求头映射见 `ConfigService.HEADER_MAPPINGS`。

---

## AI 模型

```python
from services.llm_service import LLMService

# 视觉识别（豆包）
LLMService.call_vision_model(image_base64, prompt)

# 文本生成
LLMService.call_deepseek(prompt, model='deepseek-chat')      # 同步
LLMService.call_deepseek_async(prompt, model='deepseek-v3.2') # 异步
LLMService.call_qwen(prompt, model='qwen3-max')               # Qwen3
LLMService.call_zhipu(prompt, model='glm-4')                  # 智谱

# 异步并行调用（带重试 + 信号量控制）
LLMService.run_parallel_call(prompts, max_concurrent=10, max_retries=3)

# JSON 解析（处理 LaTeX 转义、markdown 代码块）
LLMService.parse_json_response(content)
LLMService.extract_json_array(content)
```

| 模型 | 用途 | API |
|------|------|-----|
| doubao-1-5-vision-pro-32k | 视觉识别 | 火山引擎 ARK |
| deepseek-chat / deepseek-v3.2 | 文本生成/异步批量 | DeepSeek |
| qwen3-max | 文本生成 | 阿里云 DashScope |
| glm-4 | 文本生成 | 智谱 BigModel |

---

## RFID 模拟器架构

```
┌─────────────┐    WebSocket    ┌─────────────┐    ADB     ┌─────────────┐
│  网页前端   │ ◄────────────► │  Flask 服务  │ ◄────────► │  ADB 客户端  │
│ (浏览器)    │                │ (单 worker)  │            │ (本地电脑)   │
└─────────────┘                └─────────────┘            └──────┬──────┘
                                                                 │ ADB 无线
                                                          ┌──────▼──────┐
                                                          │  安卓设备   │
                                                          └─────────────┘
```

关键设计：
- 单 worker 模式：Gunicorn `--workers 1`，WebSocket 和 HTTP 同进程
- WebSocket 存储：路由层 `_active_websockets`，service 层通过注入函数获取
- 心跳：客户端 15s，服务端 90s 超时清理
- 状态文件：`sessions/rfid_state.json`

---

## 数据库

| 库 | 地址 | 连接方式 | 用途 |
|----|------|----------|------|
| zpsmart | 47.113.230.78:3306 | DBUtils 连接池 | 业务数据、作业、提示词配置 |
| aiuser | 47.82.64.147:3306 | 直连 | 平台数据、数据集、测试计划、用户 |

### 核心表
- `zp_homework` / `zp_homework_publish` / `zp_homework_result` (业务)
- `test_plans` / `datasets` / `baseline_effects` / `batch_tasks` (平台)
- `users` / `chat_sessions` / `sys_config` / `prompt_templates` (应用)
- `dataset_collections` / `collection_datasets` (合集)
- `llm_call_logs` (LLM 调用日志)

---

## 学科配置

| ID | 学科 | 提示词配置键 |
|----|------|--------------|
| 0 | 英语 | EnglishHomeWorkPrompt |
| 1 | 语文 | ChineseHomeWorkRecognition |
| 2 | 数学 | HomeWorkPrompt |
| 3 | 物理 | PhysicsHomeWorkPrompt2 |
| 4 | 化学 | ChemistryHomeWorkPrompt |
| 5 | 生物 | BiologyHomeWorkPrompt |
| 6 | 地理 | GeographyHomeWorkRecognition |

---

## 题目类型分类

```python
bvalue = str(data.get('bvalue', ''))
qtype = data.get('questionType', '')

is_choice = bvalue in ('1', '2', '3')                    # 选择题
is_fill = (qtype == 'objective' and bvalue == '4')        # 客观填空
is_subjective = not is_choice and not is_fill             # 主观题
```

## 分数字段规范

```python
# 兼容三种字段名（注意 sorce 是历史拼写错误）
base_score = (
    item.get('maxScore') if item.get('maxScore') is not None
    else item.get('score') if item.get('score') is not None
    else item.get('sorce')
)
```

---

## 缓存策略 (DashboardService)

| 数据类型 | TTL | 说明 |
|----------|-----|------|
| 概览统计 | 5分钟 | 需要较新数据 |
| 数据集概览 | 15分钟 | 中等频率 |
| 批量任务 | 30分钟 | 数据量大，变化不频繁 |

---

## 部署

```powershell
.\deploy-quick.ps1  # 一键部署
```

服务器: `47.82.64.147:5000` | 路径: `/www/wwwroot/ai-grading/Ai`

```bash
python app.py                           # 开发
USE_DB_STORAGE=false pytest tests/ -v   # 测试
```
