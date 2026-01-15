# 简单部署 - 使用 scp 逐个传输（更稳定但较慢）
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI批改平台 - 简单部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# 检查 SSH 密钥
if (-not (Test-Path $SSH_KEY)) {
    Write-Host "[Error] SSH 密钥未找到: $SSH_KEY" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] 同步文件到服务器..." -ForegroundColor Cyan

# 要同步的文件
$files = @(
    "app.py",
    "requirements.txt",
    "Dockerfile",
    "docker-compose.yml",
    "prompts.json",
    "database_schema.sql"
)

# 要同步的目录
$dirs = @(
    "routes",
    "services",
    "utils",
    "templates",
    "static",
    "knowledge_agent",
    "tests"
)

$successCount = 0
$failCount = 0

# 同步文件
foreach ($file in $files) {
    if (Test-Path $file) {
        Write-Host "  上传: $file" -ForegroundColor Gray
        scp -i $SSH_KEY $file "${SERVER}:${REMOTE_PATH}/$file" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $successCount++
        } else {
            Write-Host "    失败" -ForegroundColor Red
            $failCount++
        }
    }
}

# 同步目录
foreach ($dir in $dirs) {
    if (Test-Path $dir) {
        Write-Host "  上传: $dir/" -ForegroundColor Gray
        scp -i $SSH_KEY -r $dir "${SERVER}:${REMOTE_PATH}/" 2>$null
        if ($LASTEXITCODE -eq 0) {
            $successCount++
        } else {
            Write-Host "    失败" -ForegroundColor Red
            $failCount++
        }
    }
}

Write-Host ""
Write-Host "  成功: $successCount 项, 失败: $failCount 项" -ForegroundColor $(if ($failCount -eq 0) { "Green" } else { "Yellow" })

if ($successCount -eq 0) {
    Write-Host "[Error] 没有成功上传任何文件" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] 重启容器..." -ForegroundColor Cyan

$restartResult = ssh -i $SSH_KEY $SERVER "docker restart ai-grading-platform" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  容器重启成功" -ForegroundColor Green
} else {
    Write-Host "[Warning] 容器重启可能失败" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "[3/3] 检查容器状态..." -ForegroundColor Cyan

$statusResult = ssh -i $SSH_KEY $SERVER "docker ps --filter name=ai-grading-platform --format '{{.Status}}'" 2>&1

if ($statusResult -match "Up") {
    Write-Host "  容器运行正常" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  部署完成!" -ForegroundColor Green
    Write-Host "  访问地址: http://47.82.64.147:5000" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "  容器状态: $statusResult" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "请检查日志: ssh -i $SSH_KEY $SERVER 'docker logs ai-grading-platform --tail 50'" -ForegroundColor Yellow
}
