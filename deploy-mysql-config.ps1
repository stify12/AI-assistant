# MySQL 配置优化部署脚本
$SSH_KEY = "$env:USERPROFILE\.ssh\id_ed25519_baota"
$SERVER = "root@47.82.64.147"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  MySQL 内存优化配置部署" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

# 1. 上传配置文件
Write-Host "`n[1/3] 上传配置文件..." -ForegroundColor Yellow
scp -i $SSH_KEY mysql_optimize.cnf ${SERVER}:/tmp/mysql_optimize.cnf

# 2. 显示后续手动操作步骤
Write-Host "`n[2/3] 配置文件已上传到 /tmp/mysql_optimize.cnf" -ForegroundColor Green

Write-Host "`n========================================" -ForegroundColor Cyan
Write-Host "  请手动 SSH 登录服务器执行以下命令：" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Write-Host @"

# 1. 备份原配置
sudo cp /etc/my.cnf /etc/my.cnf.backup

# 2. 复制优化配置
sudo cp /tmp/mysql_optimize.cnf /etc/my.cnf.d/optimize.cnf
# 或者（取决于 MySQL 安装方式）
sudo cp /tmp/mysql_optimize.cnf /etc/mysql/conf.d/optimize.cnf

# 3. 重启 MySQL
sudo systemctl restart mysqld
# 或
sudo systemctl restart mysql

# 4. 检查 MySQL 状态
sudo systemctl status mysqld

# 5. 检查内存使用
free -h

# 6. 重启应用容器
docker restart ai-grading-platform

"@ -ForegroundColor White

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  如果是 Docker 中的 MySQL：" -ForegroundColor Yellow
Write-Host "========================================" -ForegroundColor Cyan

Write-Host @"

# 1. 查看 MySQL 容器名
docker ps | grep mysql

# 2. 复制配置到容器
docker cp /tmp/mysql_optimize.cnf mysql容器名:/etc/mysql/conf.d/optimize.cnf

# 3. 重启 MySQL 容器
docker restart mysql容器名

"@ -ForegroundColor White

Write-Host "`n[3/3] 完成！请按上述步骤操作。" -ForegroundColor Green
