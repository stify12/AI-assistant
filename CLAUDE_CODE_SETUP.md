# Claude Code 配置说明

## 安装状态
✅ Claude Code CLI 已成功安装 (版本 2.1.7)
✅ 配置文件模板已创建

## 配置智谱大模型

### 步骤 1: 获取智谱 API Key
1. 访问智谱AI官网: https://open.bigmodel.cn/
2. 注册/登录账号
3. 在控制台获取 API Key

### 步骤 2: 配置 Claude Code

#### 方法一: 使用项目配置文件（推荐）
项目目录已创建配置文件模板: `claude-code-config.json`

1. 编辑 `claude-code-config.json`，将 `your_zhipu_api_key_here` 替换为您的智谱 API Key:
```json
{
  "apiKey": "your_actual_zhipu_api_key",
  "apiUrl": "https://open.bigmodel.cn/api/paas/v4/chat/completions",
  "model": "glm-4",
  "provider": "zhipu",
  "temperature": 0.7,
  "maxTokens": 4096,
  "timeout": 60000
}
```

2. 使用配置文件运行 Claude Code:
```bash
npx @anthropic-ai/claude-code --settings claude-code-config.json
```

#### 方法二: 使用全局配置文件
1. 将配置文件复制到用户目录:
```powershell
Copy-Item claude-code-config.json $env:USERPROFILE\.claude-code\config.json
```

2. 直接运行 Claude Code:
```bash
npx @anthropic-ai/claude-code
```

### 步骤 3: 验证配置
运行以下命令验证配置是否正确:
```bash
npx @anthropic-ai/claude-code --print "你好，请介绍一下自己"
```

## 可用的智谱模型
- `glm-4`: 智谱 GLM-4 主力模型
- `glm-4-flash`: GLM-4 快速版
- `glm-4-plus`: GLM-4 增强版
- `glm-3-turbo`: GLM-3 Turbo 版本

## 常用命令
```bash
# 启动 Claude Code（交互模式）
npx @anthropic-ai/claude-code

# 使用特定模型
npx @anthropic-ai/claude-code --model glm-4

# 使用配置文件
npx @anthropic-ai/claude-code --settings claude-code-config.json

# 打印模式（非交互）
npx @anthropic-ai/claude-code --print "你的问题"

# 查看帮助
npx @anthropic-ai/claude-code --help

# 查看版本
npx @anthropic-ai/claude-code --version
```

## 注意事项
1. 请妥善保管您的 API Key，不要将其提交到版本控制系统
2. 建议将 `claude-code-config.json` 添加到 `.gitignore` 文件
3. 首次使用可能需要认证，请按照提示操作
4. 确保网络可以访问智谱 API 端点

## 故障排除
如果遇到问题，可以运行:
```bash
npx @anthropic-ai/claude-code doctor
```

查看详细的诊断信息。
