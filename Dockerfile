FROM python:3.12-slim

WORKDIR /app

# 设置 apt 使用清华源
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装系统依赖
# - curl: 健康检查
# - antiword: .doc文档转换（fallback方案）
# - libreoffice-writer: 处理复杂.doc文件（推荐，支持Visio图、横向页面等）
# - libreoffice-common: LibreOffice核心组件
# - default-jre-headless: LibreOffice运行时依赖（精简版，无GUI）
RUN apt-get update && \
    apt-get install -y \
    curl \
    antiword \
    libreoffice-writer \
    libreoffice-common \
    default-jre-headless && \
    rm -rf /var/lib/apt/lists/*

# 设置 pip 使用清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 暴露 FastAPI 端口
EXPOSE 8000

# 直接启动 FastAPI（依赖编排由 Docker Compose 负责）
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]