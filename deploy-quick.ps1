# Quick deploy - frontend only, no restart needed
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "[Frontend] Syncing..." -ForegroundColor Cyan

scp -i $SSH_KEY -r -o StrictHostKeyChecking=no templates "${SERVER}:${REMOTE_PATH}/"
scp -i $SSH_KEY -r -o StrictHostKeyChecking=no static "${SERVER}:${REMOTE_PATH}/"

Write-Host "[Done] Refresh browser to see changes" -ForegroundColor Green
