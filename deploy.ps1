$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "[1/3] 同步代码到服务器..." -ForegroundColor Cyan

# 上传主要文件
$files = @(
    "app.py", "requirements.txt", "Dockerfile", 
    "docker-compose.yml", "docker-compose.dev.yml",
    "prompts.json", "config.example.json", "database_schema.sql"
)

foreach ($file in $files) {
    if (Test-Path $file) {
        scp -i $SSH_KEY -o StrictHostKeyChecking=no $file "${SERVER}:${REMOTE_PATH}/"
    }
}

# 上传目录
$dirs = @("routes", "services", "utils", "templates", "static", "knowledge_agent", "tests")
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "上传 $dir ..."
        scp -i $SSH_KEY -r -o StrictHostKeyChecking=no $dir "${SERVER}:${REMOTE_PATH}/"
    }
}

Write-Host "[2/3] 重启 Docker 容器..." -ForegroundColor Cyan
ssh -i $SSH_KEY $SERVER "cd $REMOTE_PATH && docker-compose restart"

Write-Host "[3/3] 部署完成!" -ForegroundColor Green
Write-Host "访问: http://47.82.64.147:5000"
