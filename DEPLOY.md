# 宝塔面板 Docker管理器 部署教程

本教程详细介绍如何通过宝塔面板的 Docker管理器 图形界面部署 AI批改效果分析平台。

## 前置条件

- 一台公网服务器（推荐 2核4G 以上配置）
- 已安装宝塔面板 + Docker管理器
- 已备案的域名（可选，用于HTTPS访问）

---

## 第一步：上传项目代码

### 1.1 创建项目目录

通过宝塔 **文件** 管理器：
1. 导航到 `/www/wwwroot/`
2. 点击 **新建目录**，命名为 `ai-grading`

### 1.2 上传代码

**方式一：上传压缩包**
1. 将项目打包为 `ai-grading.zip`
2. 在宝塔文件管理器中上传到 `/www/wwwroot/ai-grading/`
3. 右键点击压缩包 → **解压**

**方式二：通过终端 Git 克隆**
1. 点击宝塔左侧 **终端**
2. 执行命令：
```bash
cd /www/wwwroot/ai-grading
git clone <你的仓库地址> .
```

### 1.3 创建环境配置文件

1. 在 `/www/wwwroot/ai-grading/` 目录下
2. 复制 `.env.example` 为 `.env`
3. 编辑 `.env` 文件，填入实际配置：

```env
# ========== API密钥 ==========
DOUBAO_API_KEY=你的豆包API密钥
DOUBAO_API_URL=https://ark.cn-beijing.volces.com/api/v3/chat/completions
DEEPSEEK_API_KEY=你的DeepSeek密钥
QWEN_API_KEY=你的千问密钥

# ========== 主数据库 ==========
MYSQL_HOST=数据库IP地址
MYSQL_PORT=3306
MYSQL_USER=数据库用户名
MYSQL_PASSWORD=数据库密码
MYSQL_DATABASE=数据库名
```

---

## 第二步：通过宝塔Docker管理器构建镜像

### 2.1 进入Docker管理器

1. 点击宝塔左侧菜单 **Docker**
2. 点击顶部 **本地镜像** 标签

### 2.2 构建镜像

1. 点击 **构建镜像** 按钮
2. 填写配置：
   - **镜像名称**: `ai-grading-platform`
   - **版本标签**: `latest`
   - **Dockerfile路径**: `/www/wwwroot/ai-grading/Dockerfile`
   - **构建目录**: `/www/wwwroot/ai-grading`
3. 点击 **确定** 开始构建
4. 等待构建完成（首次约5-10分钟）

构建成功后，在 **本地镜像** 列表中会看到 `ai-grading-platform:latest`

---

## 第三步：创建并运行容器

### 3.1 进入容器管理

1. 点击顶部 **容器** 标签
2. 点击 **创建容器** 按钮

### 3.2 基础配置

| 配置项 | 值 |
|--------|-----|
| 镜像 | `ai-grading-platform:latest`（从下拉列表选择） |
| 容器名称 | `ai-grading` |
| 重启策略 | `unless-stopped` |

### 3.3 端口映射

点击 **添加端口映射**：

| 容器端口 | 主机端口 | 协议 |
|---------|---------|------|
| 5000 | 5000 | TCP |

### 3.4 目录挂载（重要）

点击 **添加目录挂载**，添加以下挂载：

**代码目录（支持热更新）：**
| 主机目录 | 容器目录 |
|---------|---------|
| `/www/wwwroot/ai-grading/app.py` | `/app/app.py` |
| `/www/wwwroot/ai-grading/routes` | `/app/routes` |
| `/www/wwwroot/ai-grading/services` | `/app/services` |
| `/www/wwwroot/ai-grading/utils` | `/app/utils` |
| `/www/wwwroot/ai-grading/knowledge_agent` | `/app/knowledge_agent` |
| `/www/wwwroot/ai-grading/templates` | `/app/templates` |
| `/www/wwwroot/ai-grading/static` | `/app/static` |

**数据持久化目录：**
| 主机目录 | 容器目录 |
|---------|---------|
| `/www/wwwroot/ai-grading/datasets` | `/app/datasets` |
| `/www/wwwroot/ai-grading/batch_tasks` | `/app/batch_tasks` |
| `/www/wwwroot/ai-grading/sessions` | `/app/sessions` |
| `/www/wwwroot/ai-grading/exports` | `/app/exports` |
| `/www/wwwroot/ai-grading/knowledge_tasks` | `/app/knowledge_tasks` |
| `/www/wwwroot/ai-grading/knowledge_uploads` | `/app/knowledge_uploads` |

**配置文件：**
| 主机目录 | 容器目录 |
|---------|---------|
| `/www/wwwroot/ai-grading/config.json` | `/app/config.json` |
| `/www/wwwroot/ai-grading/prompts.json` | `/app/prompts.json` |

### 3.5 环境变量

点击 **添加环境变量**：

| 变量名 | 值 |
|--------|-----|
| FLASK_ENV | production |
| TZ | Asia/Shanghai |
| USE_DB_STORAGE | true |
| DOUBAO_API_KEY | 你的豆包API密钥 |
| DEEPSEEK_API_KEY | 你的DeepSeek密钥 |
| MYSQL_HOST | 数据库IP |
| MYSQL_PORT | 3306 |
| MYSQL_USER | 数据库用户名 |
| MYSQL_PASSWORD | 数据库密码 |
| MYSQL_DATABASE | 数据库名 |

### 3.6 创建容器

1. 确认所有配置无误
2. 点击 **确定** 创建容器
3. 容器会自动启动

---

## 第四步：验证容器运行

### 4.1 查看容器状态

在 **容器** 列表中，确认 `ai-grading` 容器状态为 **运行中**（绿色）

### 4.2 查看日志

1. 点击容器右侧的 **日志** 按钮
2. 确认没有错误信息
3. 看到类似 `[INFO] Listening at: http://0.0.0.0:5000` 表示启动成功

### 4.3 测试访问

打开浏览器访问：`http://服务器IP:5000`



---

## 第五步：配置宝塔反向代理（域名访问）

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

## 热更新代码

由于我们配置了目录挂载，代码更新非常方便：

### 前端代码热更新（无需重启）

修改以下文件后，刷新浏览器即可生效：
- `templates/*.html` - HTML模板
- `static/css/*.css` - 样式文件
- `static/js/*.js` - JavaScript文件

### 后端代码更新（需重启容器）

修改以下文件后，需要重启容器：
- `app.py` - 主应用
- `routes/*.py` - 路由文件
- `services/*.py` - 服务层
- `utils/*.py` - 工具函数
- `knowledge_agent/*.py` - 知识点模块

**重启方式：**

方式一：宝塔Docker管理器
1. 进入 Docker → 容器
2. 找到 `ai-grading` 容器
3. 点击 **重启** 按钮

方式二：命令行
```bash
docker restart ai-grading
```

### 配置文件更新

修改 `config.json` 或 `prompts.json` 后：
- 部分配置刷新页面即可生效（前端会重新读取）
- 后端配置需要重启容器

---

## 配置 SSH 密钥（免密登录）

配置SSH密钥可以实现免密登录服务器，方便代码部署和管理。

### 本地生成SSH密钥

**Windows (PowerShell):**
```powershell
# 生成密钥对（一路回车使用默认配置）
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"

# 密钥保存在：
# 私钥: C:\Users\你的用户名\.ssh\id_rsa
# 公钥: C:\Users\你的用户名\.ssh\id_rsa.pub
```

**Mac/Linux:**
```bash
ssh-keygen -t rsa -b 4096 -C "your_email@example.com"
# 密钥保存在 ~/.ssh/id_rsa 和 ~/.ssh/id_rsa.pub
```

### 上传公钥到服务器

**方式一：通过宝塔面板**
1. 登录宝塔面板
2. 进入 **安全** → **SSH管理**
3. 点击 **密钥管理** 或 **SSH密钥**
4. 点击 **添加密钥**
5. 将本地 `id_rsa.pub` 文件内容粘贴进去
6. 点击 **保存**

**方式二：命令行上传**
```bash
# Windows PowerShell
type $env:USERPROFILE\.ssh\id_rsa.pub | ssh root@服务器IP "mkdir -p ~/.ssh && cat >> ~/.ssh/authorized_keys"

# Mac/Linux
ssh-copy-id root@服务器IP
```

**方式三：手动添加**
```bash
# 登录服务器后执行
mkdir -p ~/.ssh
chmod 700 ~/.ssh
echo "你的公钥内容" >> ~/.ssh/authorized_keys
chmod 600 ~/.ssh/authorized_keys
```

### 配置SSH客户端（可选）

在本地创建 SSH 配置文件，简化连接：

**Windows:** `C:\Users\你的用户名\.ssh\config`
**Mac/Linux:** `~/.ssh/config`

```
Host ai-server
    HostName 服务器IP
    User root
    Port 22
    IdentityFile ~/.ssh/id_rsa
```

配置后可以直接使用：
```bash
ssh ai-server
```

### 测试免密登录

```bash
ssh root@服务器IP
# 或使用别名
ssh ai-server
```

如果不需要输入密码即可登录，说明配置成功。

### 使用 SSH 同步代码

配置好SSH后，可以方便地同步代码：

```bash
# 使用 rsync 同步（推荐）
rsync -avz --exclude 'node_modules' --exclude '__pycache__' --exclude '.git' \
  ./ root@服务器IP:/www/wwwroot/ai-grading/

# 使用 scp 上传单个文件
scp app.py root@服务器IP:/www/wwwroot/ai-grading/

# 使用 scp 上传目录
scp -r static/ root@服务器IP:/www/wwwroot/ai-grading/
```

### VS Code 远程开发（推荐）

1. 安装 VS Code 扩展：**Remote - SSH**
2. 按 `F1` 输入 `Remote-SSH: Connect to Host`
3. 选择或输入 `root@服务器IP`
4. 直接在服务器上编辑代码，保存即生效

---

## 使用 docker-compose 方式部署（命令行）

如果你更习惯命令行操作，也可以使用 docker-compose：

### 通过宝塔终端执行

1. 点击宝塔左侧 **终端**
2. 执行以下命令：

```bash
cd /www/wwwroot/ai-grading

# 构建并启动
docker-compose up -d --build

# 查看状态
docker-compose ps

# 查看日志
docker-compose logs -f
```

### 常用命令

```bash
# 停止容器
docker-compose down

# 重启容器
docker-compose restart

# 重新构建
docker-compose up -d --build

# 进入容器
docker exec -it ai-grading-platform bash
```

---

## 常见问题排查

### Q1: 镜像构建失败

在宝塔Docker管理器中：
1. 检查 Dockerfile 路径是否正确
2. 检查构建目录是否包含所有必要文件
3. 点击 **日志** 查看详细错误信息

常见原因：
- 网络问题导致 pip 安装失败 → 多试几次或配置国内镜像源
- Dockerfile 语法错误 → 检查 Dockerfile 文件

### Q2: 容器启动失败

在宝塔Docker管理器中：
1. 点击容器右侧 **日志** 按钮查看错误
2. 检查环境变量是否配置正确
3. 检查端口是否被占用

```bash
# 检查端口占用
netstat -tlnp | grep 5000
```

### Q3: 502 Bad Gateway

```bash
# 检查容器是否运行
docker ps

# 检查端口是否监听
netstat -tlnp | grep 5000

# 在宝塔Docker管理器中重启容器
# 或命令行: docker restart ai-grading
```

### Q4: 数据库连接失败

```bash
# 进入容器测试连接
docker exec -it ai-grading bash
python -c "import pymysql; pymysql.connect(host='数据库IP', user='用户名', password='密码', database='数据库名')"
```

### Q5: API 调用超时

修改 Nginx 超时配置：

```nginx
proxy_connect_timeout 600s;
proxy_send_timeout 600s;
proxy_read_timeout 600s;
```

### Q6: 文件上传失败

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
