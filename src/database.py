# src/database.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
import logging

# 配置日志
logger = logging.getLogger(__name__)

# 确保 data 目录存在
DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
os.makedirs(DATA_DIR, exist_ok=True)

# 数据库路径
DATABASE_PATH = os.path.join(DATA_DIR, "chat_history.db")
logger.info(f"数据库路径: {DATABASE_PATH}")

# 创建数据库引擎
DATABASE_URL = f"sqlite:///{DATABASE_PATH}"
engine = create_engine(
    DATABASE_URL,
    echo=False,  # 设置为 True 可以看到 SQL 语句
    connect_args={"check_same_thread": False}  # SQLite 需要这个配置
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 创建基类
Base = declarative_base()

# 数据库依赖
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

logger.info("数据库配置完成")
