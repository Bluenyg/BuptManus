# 创建一个新的脚本 reset_database.py
import os
from src.database import engine, Base, DATA_DIR


def reset_database():
    # 删除旧的数据库文件
    db_path = os.path.join(DATA_DIR, "chat_history.db")
    if os.path.exists(db_path):
        os.remove(db_path)
        print(f"已删除旧数据库: {db_path}")

    # 重新创建表
    Base.metadata.create_all(bind=engine)
    print("数据库表重新创建完成！")


if __name__ == "__main__":
    reset_database()
