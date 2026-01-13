# AI模型配置

## 火山引擎豆包模型 (Volcengine Doubao)

### 多模态/视觉模型 (Multimodal/Vision)
| 模型名称 | 简称 | 说明 |
|---------|------|------|
| doubao-seed-1-8-251228 | Seed 1.8 | 最新多模态模型，支持图片+文本，支持思考程度调节 |
| doubao-seed-1-6-vision-250815 | Seed 1.6 Vision | 稳定视觉模型 |
| doubao-1-5-vision-pro-32k-250115 | Vision Pro 1.5 | 专业视觉模型 |

### 文本/推理模型 (Text/Reasoning)
| 模型名称 | 简称 | 说明 |
|---------|------|------|
| doubao-seed-1-8-251228 | Seed 1.8 | 最新多模态模型，支持思考程度调节 |
| doubao-seed-1-6-251015 | Seed 1.6 | 稳定文本模型 |
| doubao-seed-1-6-thinking-250715 | Seed Thinking | 推理增强模型 |

### Seed 1.8 思考程度参数 (reasoning_effort)
| 值 | 说明 |
|---|------|
| minimal | 不思考，最快速度 |
| low | 低程度思考 |
| medium | 中等程度思考（默认） |
| high | 高程度思考，最慢但最准确 |

## DeepSeek模型

| 模型名称 | 简称 | 说明 |
|---------|------|------|
| deepseek-chat | DeepSeek Chat | 通用对话模型 |
| deepseek-v3.2 | DeepSeek V3.2 | 最新版本 |

## 阿里云通义千问 (Qwen)

| 模型名称 | 简称 | 说明 |
|---------|------|------|
| qwen3-max | Qwen3 Max | 最强文本模型 |
| qwen-vl-plus | Qwen VL Plus | 视觉语言模型 |

## 默认模型配置

- **视觉识别默认**: `doubao-seed-1-8-251228` (reasoning_effort: minimal)
- **文本生成默认**: `deepseek-v3.2`
- **知识点提取默认**: `deepseek-v3.2`
- **类题生成默认**: `deepseek-v3.2`

## API配置

- 火山引擎API: `https://ark.cn-beijing.volces.com/api/v3/chat/completions`
- DeepSeek API: `https://api.deepseek.com/chat/completions`
- 阿里云API: `https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions`
