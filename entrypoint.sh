#!/bin/sh

# 脚本在任何命令失败时退出
set -e

# 等待PostgreSQL服务完全启动并准备好接受连接
# 使用 netcat (nc) 检查数据库服务(db)的5432端口
echo "Waiting for postgres..."
while ! nc -z db 5432; do
  sleep 1
done
echo "PostgreSQL started"

# 运行数据库初始化脚本
# -u 标志确保Python的输出是无缓冲的，这样日志可以实时显示
echo "Running database initialization..."
python -u init_db.py
echo "Database initialization finished."

# 执行 Dockerfile 的 CMD 中定义的命令
# `exec "$@"` 会用 CMD 的命令替换掉当前脚本的进程，
# 这是正确传递信号（如 SIGTERM）以实现优雅关闭的最佳实践。
echo "Starting server..."
exec "$@"
