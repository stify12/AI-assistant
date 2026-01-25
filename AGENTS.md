
### 常用命令
```bash
python app.py
gunicorn --bind 0.0.0.0:5000 --workers 4 --timeout 120 app:app
docker-compose up -d --build
USE_DB_STORAGE=false pytest tests/ -v
USE_DB_STORAGE=false pytest tests/test_dataset_api.py -v
.\deploy-quick.ps1
```

---

## AI 模型配置
### 火山引擎 Doubao
- API: https://ark.cn-beijing.volces.com/api/v3/chat/completions

| 模型 | 类型 | 用途 |
|-----|------|-----|
| doubao-1-5-vision-pro-32k-250115 | 视觉 | 默认视觉 |
| doubao-seed-1-8-251228 | 多模态 | 视觉识别 + reasoning_effort |
| doubao-seed-1-6-vision-250815 | 视觉 | 稳定识别 |
| doubao-seed-1-6-thinking-250715 | 推理 | 复杂推理 |

### DeepSeek
- API: https://api.deepseek.com/chat/completions
| 模型 | 用途 |
|-----|-----|
| deepseek-v3.2 | 文本生成首选 |
| deepseek-chat | 通用对话 |

### Qwen
- API: https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions
| 模型 | 用途 |
|-----|-----|
| qwen3-max | 文本 |
| qwen-vl-plus | 视觉 |

### 默认配置
| 场景 | 模型 |
|-----|------|
| 视觉识别 | doubao-1-5-vision-pro-32k-250115 |
| 文本生成 | deepseek-v3.2 |
| 对话 | deepseek-chat |

### reasoning_effort
| 值 | 速度 | 准确度 |
|---|-----|-------|
| minimal | 最快 | 一般 |
| low | 快 | 较好 |
| medium | 中等 | 好（默认） |
| high | 慢 | 最准确 |

---

## UI 风格规范
### 设计风格
- 黑白简洁风格，参考 ChatGPT/Apple
- 高对比度、圆角、无框架原生实现
- 禁止使用 emoji

### 深色主题变量
```css
--bg-main: #212121;
--bg-sidebar: #171717;
--bg-input: #2f2f2f;
--bg-hover: #2f2f2f;
--bg-active: #424242;
--text-primary: #ececec;
--text-secondary: #b4b4b4;
--text-muted: #8e8e8e;
--border-color: #424242;
--accent-color: #10a37f;
--error-color: #ef4444;
```

### 浅色主题
- 背景：#f5f5f7（页面）/ #fff（卡片）
- 主文字：#1d1d1f
- 次要文字：#86868b
- 边框：#e5e5e5 / #d2d2d7
- 强调：#1d1d1f

### 圆角
```css
--radius-sm: 6px;
--radius-md: 12px;
--radius-lg: 16px;
--radius-xl: 24px;
--radius-full: 9999px;
```

### 按钮（文字统一黑色）
```css
.btn { padding: 10px 16px; border-radius: 9999px; font-size: 14px; font-weight: 500; color: #1d1d1f; }
.btn-primary { background: #1d1d1f; color: #1d1d1f; border-radius: 8px; }
.btn-secondary { background: #f5f5f7; border: 1px solid #d2d2d7; color: #1d1d1f; }
```

### 表单输入（白底黑字）
```css
input, select, textarea {
  padding: 10px 12px;
  background: #ffffff;
  border: 1px solid #d2d2d7;
  border-radius: 8px;
  font-size: 14px;
  color: #1d1d1f;
}
```

---

## Dashboard（测试计划看板）
### API 路由
- GET /api/dashboard/overview?range=today|week|month
- POST /api/dashboard/sync
- GET /api/dashboard/tasks?page=1&page_size=20&status=all
- GET /api/dashboard/datasets?subject_id=&sort_by=created_at&order=desc
- GET /api/dashboard/datasets/<dataset_id>/history?limit=5
- GET /api/dashboard/subjects
- CRUD：/api/dashboard/plans
- POST /api/dashboard/plans/<plan_id>/start
- POST /api/dashboard/plans/<plan_id>/clone
- POST /api/dashboard/plans/<plan_id>/tasks
- POST /api/dashboard/ai-plan
- PUT /api/dashboard/plans/<plan_id>/schedule
- GET /api/dashboard/cache/status
- POST /api/dashboard/cache/clear

### 服务层摘要
- 内存缓存，默认 5 分钟 TTL
- 扫描 batch_tasks/ 统计
- 准确率直接统计 evaluation
- 数据集难度标签：easy/medium/hard

---

## 批量评估数据流程
### 数据来源与字段
- homework_result：AI 批改结果（JSON）
- data_value：题目原始数据（含 bvalue、questionType）

### 题型分类
| bvalue | 类型 | 分类 |
|--------|------|------|
| 1 | 单选 | 选择题 |
| 2 | 多选 | 选择题 |
| 3 | 判断 | 选择题 |
| 4 | 填空 | 客观填空（questionType=objective） |
| 5 | 解答 | 主观题 |
| 8 | 英语作文 | 主观题 |

三类互斥：
1. 选择题：bvalue=1/2/3  
2. 客观填空：questionType=objective 且 bvalue=4  
3. 主观题：其余  

### 任务创建与类型映射
- 任务存储包含 data_value
- type_map 通过 data_value 递归构建，支持 index/tempIndex

### 题目类型优先级
1. type_map  
2. base_item  
3. hw_item  
4. 默认主观题

### 数据集选择
- 同一 book_id + page_num 支持多个数据集
- 自动匹配 / 手动选择 / 批量选择
- 更换数据集后状态重置为 pending

### 语文学科特殊
- 语文使用题号 index 匹配
- 其他学科使用 tempIndex
- 语文非选择题支持模糊匹配（阈值 85%）

---

## 部署配置
### 服务器信息
- IP: 47.82.64.147
- 项目路径: /www/wwwroot/ai-grading/Ai
- 访问地址: http://47.82.64.147:5000

### SSH
```powershell
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
ssh -i $SSH_KEY root@47.82.64.147
```

### 一键部署
```powershell
.\deploy-quick.ps1
```

### 同步与排除
- 同步：app.py, requirements.txt, Dockerfile, docker-compose.yml, prompts.json, database_schema.sql, routes/, services/, utils/, templates/, static/, knowledge_agent/, tests/
- 排除：.git/, __pycache__/, *.pyc, sessions/, exports/, batch_tasks/, analysis_tasks/, knowledge_tasks/, prompt_tasks/, knowledge_uploads/, datasets/, chat_sessions/, analysis_files/, baseline_effects/, config.json, .env

### 服务器操作
```powershell
$SSH = "ssh -i `"$env:USERPROFILE\.ssh\id_ed25519_baota`" root@47.82.64.147"
Invoke-Expression "$SSH `"docker ps`""
Invoke-Expression "$SSH `"docker logs ai-grading-platform --tail 100`""
Invoke-Expression "$SSH `"docker restart ai-grading-platform`""
Invoke-Expression "$SSH `"cd /www/wwwroot/ai-grading/Ai && docker-compose up -d --build`""
```

### Docker 配置
- docker-compose.yml（生产）
- docker-compose.dev.yml（开发）
- Dockerfile