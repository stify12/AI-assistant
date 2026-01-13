# 快速部署 - 使用 tar + ssh 流式传输（比 scp 快很多）
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "[1/2] 打包并流式传输..." -ForegroundColor Cyan

# 要同步的目录和文件
$items = @(
    "app.py", "requirements.txt", "Dockerfile",
    "docker-compose.yml", "docker-compose.dev.yml",
    "prompts.json", "config.example.json", "database_schema.sql",
    "routes", "services", "utils", "templates", "static", "knowledge_agent", "tests"
)

# 使用 Git Bash 的 tar 打包并通过 ssh 流式传输解压
$gitBash = "D:\Git\bin\bash.exe"
$itemList = ($items | Where-Object { Test-Path $_ }) -join " "

& $gitBash -c "tar czf - $itemList | ssh -i ~/.ssh/id_ed25519_baota -o StrictHostKeyChecking=no $SERVER 'cd $REMOTE_PATH && tar xzf - --overwrite'"

if ($LASTEXITCODE -eq 0) {
    Write-Host "[2/2] 重启容器..." -ForegroundColor Cyan
    ssh -i $SSH_KEY $SERVER "docker restart ai-grading-platform"
    Write-Host "[Done] http://47.82.64.147:5000" -ForegroundColor Green
} else {
    Write-Host "[Error] 传输失败" -ForegroundColor Red
}
