FROM python:3.12-slim

WORKDIR /app

# 设置 apt 使用清华源
RUN sed -i 's|http://deb.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources && \
    sed -i 's|http://security.debian.org|https://mirrors.tuna.tsinghua.edu.cn|g' /etc/apt/sources.list.d/debian.sources

# 安装 curl 和 antiword (用于健康检查和.doc文档转换)
RUN apt-get update && \
    apt-get install -y curl antiword && \
    rm -rf /var/lib/apt/lists/*

# 设置 pip 使用清华源
RUN pip config set global.index-url https://pypi.tuna.tsinghua.edu.cn/simple

# 复制依赖文件并安装
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/
COPY src/ ./src/
COPY init.sh .

# 创建 file 目录
RUN mkdir -p /app/file

# 暴露 FastAPI 端口
EXPOSE 8000

# 使用初始化脚本作为入口点
ENTRYPOINT ["/app/init.sh"]