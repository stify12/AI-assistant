$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"
$REMOTE_PATH = "/www/wwwroot/ai-grading/Ai"

Write-Host "Uploading batch-evaluation.html..." -ForegroundColor Cyan
scp -i $SSH_KEY "templates\batch-evaluation.html" "${SERVER}:${REMOTE_PATH}/templates/batch-evaluation.html"

if ($LASTEXITCODE -eq 0) {
    Write-Host "File uploaded successfully" -ForegroundColor Green
    Write-Host "Restarting container..." -ForegroundColor Cyan
    ssh -i $SSH_KEY $SERVER "docker restart ai-grading-platform"
    Write-Host "Done! Access: http://47.82.64.147:5000" -ForegroundColor Green
} else {
    Write-Host "Upload failed" -ForegroundColor Red
}
