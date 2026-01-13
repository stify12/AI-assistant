# 部署配置

## 服务器信息
- **IP**: 47.82.64.147
- **项目路径**: /www/wwwroot/ai-grading/Ai
- **访问地址**: http://47.82.64.147:5000

## SSH 连接
- **密钥文件**: C:\Users\Administrator\.ssh\id_ed25519_baota
- **连接命令**: `ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147`

## 部署方式

### 一键部署
```powershell
.\deploy.ps1
```

### 手动部署步骤
1. 本地修改代码
2. 运行 `.\deploy.ps1` 同步代码到服务器
3. 脚本自动重启 Docker 容器
4. 刷新浏览器查看效果

## 部署脚本说明
- `deploy.ps1`: PowerShell 部署脚本，使用 scp 上传文件
- `deploy.bat`: Batch 部署脚本，使用 rsync 同步（需要 Git Bash）

## 排除文件
部署时不会同步以下文件/目录：
- `.git`, `__pycache__`, `*.pyc`
- `sessions/`, `exports/`, `batch_tasks/`
- `analysis_tasks/`, `knowledge_tasks/`, `prompt_tasks/`
- `knowledge_uploads/`, `*.log`
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
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "cd /www/wwwroot/ai-grading/Ai && docker-compose restart"
```

### 重新构建
```bash
ssh -i "$env:USERPROFILE\.ssh\id_ed25519_baota" root@47.82.64.147 "cd /www/wwwroot/ai-grading/Ai && docker-compose up -d --build"
```
