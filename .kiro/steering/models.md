# AI 模型配置

## 模型提供商

### 火山引擎 (Volcengine) - 豆包 Doubao
- API: `https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- 配置项: `api_key`, `api_url`

| 模型 | 类型 | 用途 |
|-----|------|-----|
| doubao-1-5-vision-pro-32k-250115 | 视觉 | 专业视觉模型 (默认) |
| doubao-seed-1-8-251228 | 多模态 | 视觉识别，支持 reasoning_effort |
| doubao-seed-1-6-vision-250815 | 视觉 | 稳定的图片识别 |
| doubao-seed-1-6-thinking-250715 | 推理 | 复杂推理任务 |

### DeepSeek
- API: `https://api.deepseek.com/chat/completions`
- 配置项: `deepseek_api_key`

| 模型 | 用途 |
|-----|-----|
| deepseek-v3.2 | 最新版本，文本生成首选 |
| deepseek-chat | 通用对话 |

### 阿里云 Qwen
- API: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
- 配置项: `qwen_api_key`

| 模型 | 用途 |
|-----|-----|
| qwen3-max | 最强文本模型 |
| qwen-vl-plus | 视觉语言模型 |

## 项目默认配置

| 场景 | 模型 | 说明 |
|-----|------|-----|
| 视觉识别 | doubao-1-5-vision-pro-32k-250115 | 作业图片识别 |
| 文本生成 | deepseek-v3.2 | 知识点提取、类题生成 |
| 对话 | deepseek-chat | 通用对话 |

## Seed 1.8 思考程度 (reasoning_effort)

| 值 | 速度 | 准确度 |
|---|-----|-------|
| minimal | 最快 | 一般 |
| low | 快 | 较好 |
| medium | 中等 | 好 (默认) |
| high | 慢 | 最准确 |

## 调用示例

```python
from services.llm_service import LLMService

# 视觉模型
LLMService.call_vision_model(image_base64, prompt, model='doubao-1-5-vision-pro-32k-250115')

# DeepSeek
LLMService.call_deepseek(prompt, model='deepseek-v3.2')

# Qwen
LLMService.call_qwen(prompt, model='qwen3-max')
```
