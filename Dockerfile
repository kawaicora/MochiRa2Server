FROM python:3.11-slim

LABEL maintainer="MochiOnline"
LABEL description="MochiOnline 中心服务器 - CS 模式联机代理"

WORKDIR /app

# 复制依赖文件
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制源代码
COPY src/ ./src/

# 暴露端口
EXPOSE 36211

# 健康检查
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import socket; s = socket.socket(); s.settimeout(5); s.connect(('localhost', 36211)); s.close()" || exit 1

# 启动命令
CMD ["python", "-m", "src"]
