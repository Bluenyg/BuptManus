import sqlite3
import datetime

def init_database():
    """
    初始化数据库。如果数据库文件或表不存在，则会创建它们。
    """
    # 1. 连接到数据库。如果 "chat_history.db" 文件不存在，会自动创建。
    conn = sqlite3.connect('chat_history.db')

    # 2. 创建一个游标对象，用于执行SQL语句。
    cursor = conn.cursor()

    # 3. 编写SQL语句来创建表。
    # 使用 "CREATE TABLE IF NOT EXISTS" 可以防止在表已存在时重复创建而出错。
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS chat_history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_id TEXT NOT NULL,
        role TEXT NOT NULL,
        content TEXT NOT NULL,
        timestamp DATETIME NOT NULL
    );
    """

    # 4. 执行SQL语句。
    cursor.execute(create_table_sql)

    print("数据库和表初始化成功！")

    # 5. 提交事务并关闭连接。
    conn.commit()
    conn.close()

# --- 如何使用 ---
if __name__ == '__main__':
    # 当您直接运行这个Python文件时，会执行下面的代码
    init_database()