# Backend deploy - Python code + restart container
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "[Backend] Syncing..." -ForegroundColor Cyan

scp -i $SSH_KEY -r -o StrictHostKeyChecking=no routes "${SERVER}:${REMOTE_PATH}/"
scp -i $SSH_KEY -r -o StrictHostKeyChecking=no services "${SERVER}:${REMOTE_PATH}/"
scp -i $SSH_KEY -r -o StrictHostKeyChecking=no utils "${SERVER}:${REMOTE_PATH}/"
scp -i $SSH_KEY -r -o StrictHostKeyChecking=no knowledge_agent "${SERVER}:${REMOTE_PATH}/"
scp -i $SSH_KEY -o StrictHostKeyChecking=no app.py "${SERVER}:${REMOTE_PATH}/"

Write-Host "[Restart] Container..." -ForegroundColor Cyan
ssh -i $SSH_KEY $SERVER "docker restart ai-grading-platform"

Write-Host "[Done]" -ForegroundColor Green
