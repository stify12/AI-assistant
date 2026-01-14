# 部署配置

## 服务器信息
- **IP**: 47.82.64.147
- **项目路径**: /www/wwwroot/ai-grading/Ai
- **访问地址**: http://47.82.64.147:5000

## SSH 连接
```powershell
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
ssh -i $SSH_KEY root@47.82.64.147
```

## 一键部署
```powershell
.\deploy-quick.ps1
```
使用 tar 打包 + ssh 流式传输，比逐个 scp 快很多。

## 同步内容
- 主文件: `app.py`, `requirements.txt`, `Dockerfile`, `docker-compose.yml`, `prompts.json`, `database_schema.sql`
- 目录: `routes/`, `services/`, `utils/`, `templates/`, `static/`, `knowledge_agent/`, `tests/`

## 排除文件 (服务器独立)
- `.git/`, `__pycache__/`, `*.pyc`
- `sessions/`, `exports/`, `batch_tasks/`
- `analysis_tasks/`, `knowledge_tasks/`, `prompt_tasks/`
- `knowledge_uploads/`, `datasets/`, `chat_sessions/`
- `analysis_files/`, `baseline_effects/`
- `config.json`, `.env`

## 服务器操作

```powershell
$SSH = "ssh -i `"$env:USERPROFILE\.ssh\id_ed25519_baota`" root@47.82.64.147"

# 查看容器状态
Invoke-Expression "$SSH `"docker ps`""

# 查看日志
Invoke-Expression "$SSH `"docker logs ai-grading-platform --tail 100`""

# 重启容器
Invoke-Expression "$SSH `"docker restart ai-grading-platform`""

# 重新构建
Invoke-Expression "$SSH `"cd /www/wwwroot/ai-grading/Ai && docker-compose up -d --build`""
```

## Docker 配置
- `docker-compose.yml`: 生产环境配置
- `docker-compose.dev.yml`: 开发环境配置
- `Dockerfile`: 镜像构建配置
