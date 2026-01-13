# Git deploy - push to GitHub, server auto pulls
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

# 1. Commit and push
Write-Host "[1/3] Commit and push..." -ForegroundColor Cyan
git add -A
$msg = Read-Host "Commit message (or press Enter for default)"
if ([string]::IsNullOrEmpty($msg)) { $msg = "Update $(Get-Date -Format 'yyyy-MM-dd HH:mm')" }
git commit -m $msg
git push origin main

# 2. Server pull
Write-Host "[2/3] Server pulling..." -ForegroundColor Cyan
ssh -i $SSH_KEY $SERVER "cd $REMOTE_PATH && git fetch origin && git reset --hard origin/main"

# 3. Restart if needed
$restart = Read-Host "Restart container? (y/N)"
if ($restart -eq "y") {
    Write-Host "[3/3] Restarting..." -ForegroundColor Cyan
    ssh -i $SSH_KEY $SERVER "docker restart ai-grading-platform"
}

Write-Host "[Done]" -ForegroundColor Green
