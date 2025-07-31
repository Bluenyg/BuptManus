# 使用一个轻量的官方Python镜像
FROM python:3.12-slim

# 安装系统依赖，包括 Playwright 需要的依赖
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    build-essential \
    netcat-openbsd \
    # Playwright 浏览器依赖
    wget \
    gnupg \
    ca-certificates \
    fonts-liberation \
    libasound2 \
    libatk-bridge2.0-0 \
    libatk1.0-0 \
    libatspi2.0-0 \
    libdrm2 \
    libgtk-3-0 \
    libnspr4 \
    libnss3 \
    libx11-xcb1 \
    libxcomposite1 \
    libxdamage1 \
    libxrandr2 \
    libxss1 \
    libxtst6 \
    xdg-utils \
    libu2f-udev \
    libvulkan1 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# 安装 uv
RUN pip install uv

# 仅复制依赖清单文件，利用Docker缓存
COPY pyproject.toml uv.lock ./

# 复制 README.md
COPY README.md ./

# 使用 uv 安装依赖
RUN uv sync

# 安装 Playwright 浏览器
# 你可以选择只安装需要的浏览器来减小镜像体积
RUN uv run playwright install chromium
# 如果需要所有浏览器，使用: RUN uv run playwright install

# 安装 Playwright 的系统依赖
RUN uv run playwright install-deps chromium
# 如果安装了所有浏览器，使用: RUN uv run playwright install-deps

# 复制启动脚本并赋予执行权限
COPY entrypoint.sh /usr/local/bin/entrypoint.sh
RUN chmod +x /usr/local/bin/entrypoint.sh

# 复制所有源代码（.dockerignore 文件会排除不必要的内容）
COPY . .

# 暴露应用端口
EXPOSE 8000

# 设置环境变量
ENV PYTHONPATH=/langmanus
# Playwright 环境变量，确保在容器中正常运行
ENV PLAYWRIGHT_BROWSERS_PATH=/ms-playwright

# 例如: CMD ["gunicorn", "-w", "4", "-k", "uvicorn.workers.UvicornWorker", "server:app", "-b", "0.0.0.0:8000"]
CMD ["uv", "run", "python", "server.py"]
