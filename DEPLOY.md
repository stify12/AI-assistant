# 宝塔面板 + Docker 部署教程

本教程详细介绍如何将 AI批改效果分析平台 通过 Docker 部署到宝塔面板服务器上。

## 前置条件

- 一台公网服务器（推荐 2核4G 以上配置）
- 已安装宝塔面板
- 已备案的域名（可选，用于HTTPS访问）

---

## 第一步：安装 Docker

### 1.1 通过宝塔安装 Docker

1. 登录宝塔面板
2. 进入 **软件商店**
3. 搜索 **Docker管理器**
4. 点击 **安装**

或者通过命令行安装：

```bash
# CentOS
yum install -y docker-ce docker-ce-cli containerd.io

# Ubuntu/Debian
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io

# 启动 Docker
systemctl start docker
systemctl enable docker

# 安装 docker-compose
curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
chmod +x /usr/local/bin/docker-compose
```

### 1.2 验证安装

```bash
docker --version
docker-compose --version
```

---

## 第二步：上传项目代码

### 2.1 创建项目目录

```bash
mkdir -p /www/wwwroot/ai-grading
cd /www/wwwroot/ai-grading
```

### 2.2 上传代码

**方式一：通过宝塔文件管理器**
1. 进入宝塔 **文件** 管理
2. 导航到 `/www/wwwroot/ai-grading`
3. 上传项目压缩包并解压

**方式二：通过 Git 克隆**
```bash
cd /www/wwwroot/ai-grading
git clone <你的仓库地址> .
```

**方式三：通过 SFTP/SCP**
```bash
# 本地执行
scp -r ./* root@你的服务器IP:/www/wwwroot/ai-grading/
```

---

## 第三步：配置环境变量

### 3.1 创建 .env 文件

```bash
cd /www/wwwroot/ai-grading
cp .env.example .env
```

### 3.2 编辑 .env 文件

```bash
nano .env
# 或使用宝塔文件管理器编辑
```

填入实际配置：

```env
# ========== API密钥 ==========
# 豆包视觉模型（火山引擎）- 必填
DOUBAO_API_KEY=你的豆包API密钥
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions

# DeepSeek - 必填
DEEPSEEK_API_KEY=你的DeepSeek密钥

# 通义千问 - 可选
QWEN_API_KEY=你的千问密钥

# ========== 主数据库（作业数据源） ==========
MYSQL_HOST=数据库IP地址
MYSQL_PORT=3306
MYSQL_USER=数据库用户名
MYSQL_PASSWORD=数据库密码
MYSQL_DATABASE=数据库名

# ========== 应用数据库（可选，存储评估结果） ==========
APP_MYSQL_HOST=
APP_MYSQL_PORT=3306
APP_MYSQL_USER=
APP_MYSQL_PASSWORD=
APP_MYSQL_DATABASE=
```

### 3.3 创建 config.json（可选）

如果需要更多配置，可以创建 config.json：

```bash
cp config.example.json config.json
nano config.json
```

---

## 第四步：构建并启动容器

### 4.1 构建 Docker 镜像

```bash
cd /www/wwwroot/ai-grading
docker-compose build
```

首次构建可能需要 5-10 分钟。

### 4.2 启动容器

```bash
docker-compose up -d
```

### 4.3 查看运行状态

```bash
# 查看容器状态
docker-compose ps

# 查看日志
docker-compose logs -f

# 查看最近100行日志
docker-compose logs --tail=100
```

### 4.4 常用命令

```bash
# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 重新构建并启动
docker-compose up -d --build

# 进入容器内部
docker exec -it ai-grading-platform bash
```

---

## 第五步：配置宝塔反向代理

### 5.1 添加网站

1. 进入宝塔 **网站** 管理
2. 点击 **添加站点**
3. 填写域名（如 `ai.yourdomain.com`）
4. PHP版本选择 **纯静态**
5. 点击 **提交**

### 5.2 配置反向代理

1. 点击刚创建的网站 **设置**
2. 进入 **反向代理** 选项卡
3. 点击 **添加反向代理**
4. 填写配置：
   - 代理名称：`ai-grading`
   - 目标URL：`http://127.0.0.1:5000`
   - 发送域名：`$host`
5. 点击 **提交**

### 5.3 手动配置（可选）

如果反向代理不生效，可以手动编辑 Nginx 配置：

1. 点击网站 **设置** → **配置文件**
2. 在 `server` 块内添加：

```nginx
location / {
    proxy_pass http://127.0.0.1:5000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    
    # WebSocket 支持（如需要）
    proxy_http_version 1.1;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection "upgrade";
    
    # 超时设置（AI接口可能较慢）
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;
}
```

3. 点击 **保存** 并重载 Nginx

---

## 第六步：配置 SSL（HTTPS）

### 6.1 申请证书

1. 点击网站 **设置** → **SSL**
2. 选择 **Let's Encrypt**
3. 勾选域名
4. 点击 **申请**

### 6.2 强制 HTTPS

申请成功后，开启 **强制HTTPS** 选项。

---

## 第七步：配置防火墙

### 7.1 宝塔防火墙

1. 进入 **安全** 管理
2. 确保 **80** 和 **443** 端口已放行
3. **5000** 端口可以不对外开放（通过反向代理访问）

### 7.2 服务器防火墙

```bash
# CentOS
firewall-cmd --permanent --add-port=80/tcp
firewall-cmd --permanent --add-port=443/tcp
firewall-cmd --reload

# Ubuntu
ufw allow 80/tcp
ufw allow 443/tcp
```

### 7.3 云服务器安全组

如果使用阿里云/腾讯云等，需要在控制台安全组中放行 80、443 端口。

---

## 第八步：验证部署

### 8.1 访问测试

- 直接访问：`http://服务器IP:5000`
- 域名访问：`https://ai.yourdomain.com`

### 8.2 健康检查

```bash
curl http://127.0.0.1:5000/
```

---

## 常见问题排查

### Q1: 容器启动失败

```bash
# 查看详细日志
docker-compose logs ai-grading

# 常见原因：
# 1. .env 文件配置错误
# 2. 端口被占用
# 3. 数据库连接失败
```

### Q2: 502 Bad Gateway

```bash
# 检查容器是否运行
docker ps

# 检查端口是否监听
netstat -tlnp | grep 5000

# 重启容器
docker-compose restart
```

### Q3: 数据库连接失败

```bash
# 进入容器测试连接
docker exec -it ai-grading-platform bash
python -c "import pymysql; pymysql.connect(host='数据库IP', user='用户名', password='密码', database='数据库名')"
```

### Q4: API 调用超时

修改 Nginx 超时配置：

```nginx
proxy_connect_timeout 600s;
proxy_send_timeout 600s;
proxy_read_timeout 600s;
```

### Q5: 文件上传失败

修改 Nginx 上传限制：

```nginx
client_max_body_size 50m;
```

---

## 数据备份

### 备份数据目录

```bash
cd /www/wwwroot/ai-grading
tar -czvf backup_$(date +%Y%m%d).tar.gz datasets batch_tasks baseline_effects sessions exports
```

### 定时备份（宝塔计划任务）

1. 进入 **计划任务**
2. 添加 **Shell脚本** 任务
3. 执行周期：每天
4. 脚本内容：

```bash
cd /www/wwwroot/ai-grading
tar -czvf /www/backup/ai-grading_$(date +%Y%m%d).tar.gz datasets batch_tasks baseline_effects
find /www/backup -name "ai-grading_*.tar.gz" -mtime +7 -delete
```

---

## 更新部署

```bash
cd /www/wwwroot/ai-grading

# 拉取最新代码
git pull

# 重新构建并启动
docker-compose up -d --build

# 查看日志确认启动成功
docker-compose logs -f
```

---

## 性能优化建议

1. **增加 Worker 数量**：修改 Dockerfile 中的 `--workers` 参数
2. **使用 Redis 缓存**：添加 Redis 服务到 docker-compose.yml
3. **配置 CDN**：静态资源使用 CDN 加速
4. **数据库优化**：确保数据库有适当的索引

---

## 联系支持

如遇到问题，请检查：
1. Docker 日志：`docker-compose logs`
2. Nginx 错误日志：`/www/wwwlogs/域名.error.log`
3. 宝塔面板日志
