# 使用 Python 3.11 作为基础镜像 (基于 Debian Bookworm)
FROM python:3.11-slim-bookworm

# 设置工作目录
WORKDIR /app

# 设置环境变量
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV FLASK_APP=app.py
ENV FLASK_ENV=production
ENV USE_DB_STORAGE=true

# 配置国内镜像源（阿里云）
RUN sed -i 's/deb.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's/security.debian.org/mirrors.aliyun.com/g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    default-libmysqlclient-dev \
    pkg-config \
    curl \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY requirements.txt .

# 配置pip国内镜像源并安装依赖
RUN pip install --no-cache-dir -i https://mirrors.aliyun.com/pypi/simple/ -r requirements.txt gunicorn

# 复制应用代码
COPY . .

# 创建必要的目录
RUN mkdir -p datasets batch_tasks baseline_effects sessions chat_sessions \
    analysis_files analysis_tasks exports knowledge_tasks knowledge_uploads prompt_tasks

# 暴露端口
EXPOSE 5000

# 启动命令 - 使用 gunicorn 生产服务器
CMD ["gunicorn", "--bind", "0.0.0.0:5000", "--workers", "4", "--timeout", "120", "app:app"]
