# AI批改效果分析平台 - 开发环境配置指南

## 环境要求

- Python 3.9+
- MySQL 5.7+
- Git

## 快速开始

### 1. 克隆项目

```bash
git clone <仓库地址>
cd Ai
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置文件

复制示例配置文件并修改：

```bash
cp config.example.json config.json
```

编辑 `config.json`，填入以下配置：

```json
{
  "api_key": "你的火山引擎API密钥",
  "api_url": "https://ark.cn-beijing.volces.com/api/v3/chat/completions",
  "deepseek_api_key": "你的DeepSeek API密钥",
  "mysql": {
    "host": "47.113.230.78",
    "port": 3306,
    "user": "zpsmart",
    "password": "rootyouerkj!",
    "database": "zpsmart"
  },
  "app_mysql": {
    "host": "47.82.64.147",
    "port": 3306,
    "user": "aiuser",
    "password": "123456",
    "database": "aiuser"
  }
}
```

配置说明：
- `mysql`: 原业务数据库(zpsmart)，用于获取作业数据
- `app_mysql`: 应用数据库(aiuser)，用于存储平台数据（数据集、评估记录等）

### 4. 启动开发服务器

```bash
python app.py
```

访问 http://localhost:5000

## 数据库说明

项目使用两个数据库：

| 数据库 | 用途 | 说明 |
|--------|------|------|
| zpsmart | 业务数据库 | 读取作业数据(zp_homework表) |
| aiuser | 应用数据库 | 存储数据集、基准效果、评估记录等 |

应用数据库表结构在 `database_schema.sql` 中定义。

## 服务器部署

### 访问地址

- 服务器IP: 47.82.64.147
- 端口: 5000
- 访问地址: http://47.82.64.147:5000

### 部署方式

项目使用 Docker 部署，一键部署脚本：

```powershell
.\deploy-quick.ps1
```

### 手动部署

1. SSH连接服务器：
```bash
ssh -i ~/.ssh/id_ed25519_baota root@47.82.64.147
```

2. 进入项目目录：
```bash
cd /www/wwwroot/ai-grading/Ai
```

3. 重新构建并启动：
```bash
docker-compose up -d --build
```

### 查看日志

```bash
docker logs ai-grading-platform --tail 100
```

## 目录结构

```
├── app.py                 # Flask应用入口
├── config.json            # 应用配置
├── routes/                # Flask蓝图路由
├── services/              # 业务服务层
├── templates/             # Jinja2 HTML模板
├── static/                # 静态资源(CSS/JS)
├── datasets/              # 数据集存储
└── tests/                 # 测试文件
```

## 常用命令

```bash
# 运行测试
pytest tests/ -v

# 本地开发
python app.py

# Docker构建
docker build -t ai-grading-platform .

# Docker运行
docker-compose up -d
```

## API密钥获取

- 火山引擎(豆包): https://console.volcengine.com/ark
- DeepSeek: https://platform.deepseek.com
- 阿里云(通义千问): https://dashscope.console.aliyun.com

## 注意事项

1. `config.json` 包含敏感信息，已加入 `.gitignore`，不会提交到仓库
2. 本地开发时确保能访问两个数据库
3. 如需修改数据库配置，请联系管理员获取权限
