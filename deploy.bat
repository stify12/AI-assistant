@echo off
setlocal

set SSH_KEY=C:\Users\Administrator\.ssh\id_ed25519_baota
set SERVER=root@47.82.64.147
set REMOTE_PATH=/www/wwwroot/ai-grading/Ai

echo [1/3] 同步代码到服务器...
rsync -avz --delete -e "ssh -i %SSH_KEY%" ^
  --exclude=".git" ^
  --exclude="__pycache__" ^
  --exclude="*.pyc" ^
  --exclude="sessions/" ^
  --exclude="exports/" ^
  --exclude="batch_tasks/" ^
  --exclude="analysis_tasks/" ^
  --exclude="knowledge_tasks/" ^
  --exclude="prompt_tasks/" ^
  --exclude="knowledge_uploads/" ^
  --exclude="*.log" ^
  --exclude="config.json" ^
  --exclude=".env" ^
  ./ %SERVER%:%REMOTE_PATH%/

if %errorlevel% neq 0 (
    echo 同步失败!
    exit /b 1
)

echo [2/3] 重启 Docker 容器...
ssh -i %SSH_KEY% %SERVER% "cd %REMOTE_PATH% && docker-compose restart"

echo [3/3] 部署完成!
echo 访问: http://47.82.64.147:5000

endlocal
