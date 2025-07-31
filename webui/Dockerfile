# webui/Dockerfile - Next.js开发服务器模式
FROM node:18-alpine

# 设置工作目录
WORKDIR /webui

# 安装pnpm
RUN npm install -g pnpm

# 复制package.json和pnpm-lock.yaml
COPY package.json pnpm-lock.yaml* ./

# 安装依赖
RUN pnpm install

# 复制源代码
COPY . .

# 暴露Next.js默认端口
EXPOSE 3000

# 启动开发服务器
CMD ["pnpm", "dev"]