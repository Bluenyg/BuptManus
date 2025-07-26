# init_db.py
from src.database import Base, engine, DATA_DIR
from src.models.chat import ChatSession, ChatMessageRecord
import os


def create_tables():
    """创建所有数据库表"""
    print(f"数据库将创建在: {DATA_DIR}/chat_history.db")

    # 确保目录存在
    if not os.path.exists(DATA_DIR):
        os.makedirs(DATA_DIR)
        print(f"创建目录: {DATA_DIR}")

    # 创建表
    Base.metadata.create_all(bind=engine)
    print("数据库表创建完成！")
    print("数据库已准备就绪，可以开始使用了！")

    # 显示数据库文件位置
    db_path = os.path.join(DATA_DIR, "chat_history.db")
    if os.path.exists(db_path):
        print(f"✅ 数据库文件已创建: {db_path}")
    else:
        print(f"❌ 数据库文件创建失败")


if __name__ == "__main__":
    create_tables()
