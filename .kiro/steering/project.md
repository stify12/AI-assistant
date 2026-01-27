# AI批改效果分析平台

## 产品定位
面向教育科技团队的 AI 批改效果分析平台，量化评估 AI 批改准确性、追踪效果趋势。

## 核心功能

| 模块 | 路由 | 功能 |
|------|------|------|
| 测试计划看板 | `/` | Dashboard，测试计划管理、数据概览 |
| 批量评估 | `/batch-evaluation` | 批量评估 AI 批改结果 |
| 学科批改 | `/subject-grading` | 单份作业实时批改评估 |
| 知识点类题 | `/knowledge-agent` | 提取知识点，生成类似题目 |
| 数据分析 | `/data-analysis` | 可视化统计分析 |
| 数据集管理 | `/dataset-manage` | 管理基准效果数据集 |
| 提示词优化 | `/prompt-optimize` | Prompt 调试、版本管理 |

---

## 技术栈

| 层 | 技术 |
|-----|------|
| 后端 | Flask + Gunicorn + PyMySQL |
| 前端 | Jinja2 + 原生 CSS/JS |
| AI | 豆包(视觉) / DeepSeek(文本) / Qwen(备选) |
| 部署 | Docker + Docker Compose |

---

## 项目结构

```
├── app.py                 # Flask 入口
├── config.json            # 配置 (API密钥、数据库)
├── routes/                # Flask 蓝图路由
├── services/              # 业务服务层
├── knowledge_agent/       # 知识点类题模块
├── templates/             # Jinja2 模板
├── static/                # CSS/JS
└── tests/                 # 测试
```

### 命名约定
- 路由: `snake_case.py` → 蓝图 `feature_name_bp`
- API: `/api/feature-name/action`
- 模板/样式: `feature-name.html/css/js`

---

## 数据库

| 库 | 地址 | 用途 |
|----|------|------|
| zpsmart | 47.113.230.78:3306 | 业务数据、作业、提示词配置 |
| aiuser | 47.82.64.147:3306 | 分析平台、数据集、测试计划 |

---

## 学科配置

| ID | 学科 | 匹配规则 | 提示词配置键 |
|----|------|----------|--------------|
| 0 | 英语 | index | EnglishHomeWorkPrompt |
| 1 | 语文 | index (模糊85%) | ChineseHomeWorkRecognition |
| 2 | 数学 | index | HomeWorkPrompt |
| 3 | 物理 | index | PhysicsHomeWorkPrompt2 |
| 4 | 化学 | index | ChemistryHomeWorkPrompt |
| 5 | 生物 | index | BiologyHomeWorkPrompt |
| 6 | 地理 | index | GeographyHomeWorkRecognition |

---

## AI 模型

```python
from services.llm_service import LLMService

# 视觉识别
LLMService.call_vision_model(image_base64, prompt)

# 文本生成
LLMService.call_deepseek(prompt, model='deepseek-v3.2')
```

| 模型 | 用途 |
|------|------|
| doubao-1-5-vision-pro-32k | 视觉识别 (默认) |
| doubao-seed-1-8 | 多模态 |
| deepseek-chat | 通用对话 |

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

## 部署

```powershell
# 一键部署
.\deploy-quick.ps1

# SSH 连接
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
ssh -i $SSH_KEY root@47.82.64.147

# 常用命令
docker ps
docker logs ai-grading-platform --tail 100
docker restart ai-grading-platform
```

服务器: `47.82.64.147:5000` | 路径: `/www/wwwroot/ai-grading/Ai`

---

## 常用命令

```bash
# 开发
python app.py

# 测试
USE_DB_STORAGE=false pytest tests/ -v

# 部署
.\deploy-quick.ps1
```
