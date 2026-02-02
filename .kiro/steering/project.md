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
| 测试用例生成 | `/testcase-generator` | AI 自动生成基准效果（规划中） |

---

## 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Flask + Gunicorn + PyMySQL |
| 前端 | Jinja2 + 原生 CSS/JS (模块化) |
| AI | 豆包(视觉) / DeepSeek(文本) / Qwen(备选) |
| 部署 | Docker + Docker Compose |

---

## 项目结构

```
├── app.py                 # Flask 入口
├── config.json            # 配置 (API密钥、数据库)
├── routes/                # Flask 蓝图路由 (30+)
├── services/              # 业务服务层 (35+)
├── knowledge_agent/       # 知识点类题模块
├── templates/             # Jinja2 模板 (12个页面)
├── static/js/             # JS (页面脚本 + modules/ + components/)
├── static/css/            # CSS (页面样式 + modules/)
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
| 核心 | DatabaseService | 原业务数据库 (zpsmart) |
| 核心 | AppDatabaseService | 应用数据库 (aiuser) |
| 核心 | StorageService | 文件/数据库存储 |
| 核心 | LLMService | LLM 调用 (多模型) |
| 核心 | DashboardService | 看板统计 + 缓存管理 |
| 业务 | AIAnalysisService | AI 分析与报告 |
| 业务 | SemanticEvalService | 语义评估 |
| 业务 | PromptConfigService | 提示词配置 |
| 学科 | PhysicsEval | 物理公式标准化 |
| 学科 | ChemistryEval | 化学 Markdown 标准化 |

---

## 数据库

| 库 | 地址 | 用途 |
|----|------|------|
| zpsmart | 47.113.230.78:3306 | 业务数据、作业、提示词配置 |
| aiuser | 47.82.64.147:3306 | 分析平台、数据集、测试计划 |

### 核心表
- `zp_homework` / `zp_homework_publish` / `zp_homework_result` (业务)
- `test_plans` / `datasets` / `baseline_effects` / `batch_tasks` (平台)

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

## AI 模型

```python
from services.llm_service import LLMService

LLMService.call_vision_model(image_base64, prompt)  # 视觉识别
LLMService.call_deepseek(prompt, model='deepseek-v3.2')  # 文本生成
```

| 模型 | 用途 |
|------|------|
| doubao-1-5-vision-pro-32k | 视觉识别 (默认) |
| deepseek-chat | 通用对话/文本生成 |

---

## 题目类型分类

```python
def classify_question_type(data):
    bvalue = str(data.get('bvalue', ''))
    qtype = data.get('questionType', '')
    
    is_choice = bvalue in ('1', '2', '3')        # 选择题
    is_fill = (qtype == 'objective' and bvalue == '4')  # 客观填空
    is_subjective = not is_choice and not is_fill       # 主观题
```

---

## 分数字段规范

| 来源 | 字段名 | 说明 |
|------|--------|------|
| datavalue | `sorce` | 题目总分（注意拼写错误） |
| datavalue | `ans` | 标准答案 |
| base_effects | `maxScore` | 题目总分 |
| base_effects | `score` | 判断分值 |

```python
# 兼容三种字段名
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

---

## 常用命令

```bash
python app.py                           # 开发
USE_DB_STORAGE=false pytest tests/ -v   # 测试
.\deploy-quick.ps1                      # 部署
```
