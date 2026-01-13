# 部署配置

## 服务器信息
- **IP**: 47.82.64.147
- **项目路径**: /www/wwwroot/ai-grading/Ai
- **访问地址**: http://47.82.64.147:5000

## SSH 连接
- **密钥文件**: C:\Users\Administrator\.ssh\id_ed25519_baota
- **连接命令**: `ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147`

## 一键部署
```powershell
.\deploy-quick.ps1
```

使用 tar 打包 + ssh 流式传输，比逐个 scp 快很多。

## 同步内容
- 主文件: app.py, requirements.txt, Dockerfile, docker-compose.yml 等
- 目录: routes, services, utils, templates, static, knowledge_agent, tests

## 排除文件
- `.git`, `__pycache__`, `*.pyc`
- `sessions/`, `exports/`, `batch_tasks/`
- `analysis_tasks/`, `knowledge_tasks/`, `prompt_tasks/`
- `knowledge_uploads/`, `datasets/`, `chat_sessions/`
- `config.json`, `.env` (服务器独立配置)

## 服务器操作

### 查看容器状态
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "docker ps"
```

### 查看日志
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "docker logs ai-grading-platform --tail 100"
```

### 重启容器
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "docker restart ai-grading-platform"
```

### 重新构建
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "cd /www/wwwroot/ai-grading/Ai && docker-compose up -d --build"
```
