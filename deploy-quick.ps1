# Quick Deploy - Using tar + ssh streaming (much faster than scp)
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"
$SSH_EXE = "C:\Windows\System32\OpenSSH\ssh.exe"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  AI Grading Platform - Quick Deploy" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Git Bash
$gitBash = "D:\Git\bin\bash.exe"
if (-not (Test-Path $gitBash)) {
    Write-Host "[Error] Git Bash not found: $gitBash" -ForegroundColor Red
    Write-Host "Please install Git for Windows or update the path" -ForegroundColor Yellow
    exit 1
}

# Check SSH key
$sshKeyPath = "$env:USERPROFILE\.ssh\id_ed25519_baota"
if (-not (Test-Path $sshKeyPath)) {
    Write-Host "[Error] SSH key not found: $sshKeyPath" -ForegroundColor Red
    exit 1
}

Write-Host "[1/3] Checking files to sync..." -ForegroundColor Cyan

# Files and directories to sync
$items = @(
    "app.py", "requirements.txt", "Dockerfile",
    "docker-compose.yml", "docker-compose.dev.yml",
    "prompts.json", "config.example.json", "database_schema.sql",
    "routes", "services", "utils", "templates", "static", "knowledge_agent", "tests", "migrations"
)

# Check which items exist
$existingItems = @()
$missingItems = @()
foreach ($item in $items) {
    if (Test-Path $item) {
        $existingItems += $item
    } else {
        $missingItems += $item
    }
}

Write-Host "  Found $($existingItems.Count) files/directories" -ForegroundColor Green
if ($missingItems.Count -gt 0) {
    Write-Host "  Skipping $($missingItems.Count) missing items: $($missingItems -join ', ')" -ForegroundColor Yellow
}

if ($existingItems.Count -eq 0) {
    Write-Host "[Error] No files to sync" -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "[2/3] Packing and streaming to server..." -ForegroundColor Cyan

# Build tar command
$itemList = $existingItems -join " "

# Execute tar + ssh streaming via Git Bash
$tarCmd = "tar czf - $itemList 2>/dev/null | ssh -i ~/.ssh/id_ed25519_baota -o StrictHostKeyChecking=no $SERVER 'cd $REMOTE_PATH && tar xzf - --overwrite 2>/dev/null'"

$result = & $gitBash -c $tarCmd 2>&1

if ($LASTEXITCODE -ne 0) {
    Write-Host "[Warning] Transfer had warnings but may have succeeded" -ForegroundColor Yellow
    Write-Host "  Error: $result" -ForegroundColor DarkGray
} else {
    Write-Host "  Transfer completed" -ForegroundColor Green
}

Write-Host ""
Write-Host "[3/3] Restarting container..." -ForegroundColor Cyan

$restartResult = & $SSH_EXE -i $SSH_KEY $SERVER "docker restart ai-grading-platform" 2>&1

if ($LASTEXITCODE -eq 0) {
    Write-Host "  Container restarted successfully" -ForegroundColor Green
    Write-Host ""
    Write-Host "========================================" -ForegroundColor Green
    Write-Host "  Deployment Complete!" -ForegroundColor Green
    Write-Host "  URL: http://47.82.64.147:5000" -ForegroundColor Green
    Write-Host "========================================" -ForegroundColor Green
} else {
    Write-Host "[Warning] Container restart may have failed: $restartResult" -ForegroundColor Yellow
    Write-Host "Please check manually: & $SSH_EXE -i $SSH_KEY $SERVER 'docker ps'" -ForegroundColor Yellow
}
