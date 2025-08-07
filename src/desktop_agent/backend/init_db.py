# init_database_complete.py
import sys
import os
import logging
from pathlib import Path

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

from sqlmodel import SQLModel, Session, text, create_engine
from sqlalchemy import inspect
import traceback

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def import_all_models():
    """显式导入所有模型以确保它们被SQLModel注册"""
    try:
        logger.info("正在导入所有模型...")

        # 导入数据库引擎
        from db.database import engine, DATABASE_URL

        # 显式导入所有模型类
        from db.models import (
            User, UserType,
            LoginSession, LoginSessionTypes,
            EmailVerificationEntry,
            Thread, ThreadStatus,
            ThreadTask, ThreadTaskStatus,
            ThreadTaskPlan, ThreadTaskPlanStatus,
            PlanSubtask, SubtaskStatus, SubtaskType,
            ThreadTaskMemoryEntry,
            ThreadMessage, ThreadChatType, ThreadChatFromChoices
        )

        logger.info("✅ 所有模型导入成功")

        # 返回引擎和数据库URL以便使用
        return engine, DATABASE_URL

    except ImportError as e:
        logger.error(f"❌ 模型导入失败: {e}")
        logger.error("请检查以下文件是否存在：")
        logger.error("  - db/database.py (包含 engine 和 DATABASE_URL)")
        logger.error("  - db/models.py (包含所有模型类)")
        logger.error("  - utils/procedures.py (包含生成函数)")
        raise
    except Exception as e:
        logger.error(f"❌ 模型导入过程中发生未知错误: {e}")
        logger.error(traceback.format_exc())
        raise


def get_all_table_info():
    """获取所有表的详细信息"""
    tables_info = {}

    for table_name, table in SQLModel.metadata.tables.items():
        columns = []
        for column in table.columns:
            col_info = {
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'foreign_key': bool(column.foreign_keys)
            }
            columns.append(col_info)

        tables_info[table_name] = {
            'columns': columns,
            'column_count': len(columns)
        }

    return tables_info


def verify_database_connection(engine, database_url):
    """验证数据库连接"""
    try:
        logger.info("正在测试数据库连接...")
        with Session(engine) as session:
            session.exec(text("SELECT 1"))
        logger.info(f"✅ 数据库连接成功: {database_url}")
        return True
    except Exception as e:
        logger.error(f"❌ 数据库连接失败: {e}")
        logger.error(f"数据库URL: {database_url}")
        return False


def create_all_tables(engine):
    """创建所有表"""
    try:
        logger.info("开始创建数据库表...")

        # 获取表信息
        tables_info = get_all_table_info()
        logger.info(f"准备创建 {len(tables_info)} 个表:")

        for table_name, info in tables_info.items():
            logger.info(f"  - {table_name} ({info['column_count']} 列)")

        # 创建所有表
        SQLModel.metadata.create_all(engine)

        logger.info("✅ 所有表创建完成！")
        return True

    except Exception as e:
        logger.error(f"❌ 创建表失败: {e}")
        logger.error(traceback.format_exc())
        return False


def verify_tables_exist(engine, database_url):
    """验证表是否存在"""
    try:
        logger.info("正在验证表结构...")

        with Session(engine) as session:
            # 获取期望的表名
            expected_tables = set(SQLModel.metadata.tables.keys())
            logger.info(f"期望的表: {sorted(expected_tables)}")

            # 根据数据库类型获取实际存在的表
            if "postgresql" in database_url.lower():
                result = session.exec(text("""
                                           SELECT table_name
                                           FROM information_schema.tables
                                           WHERE table_schema = 'public'
                                             AND table_type = 'BASE TABLE'
                                           ORDER BY table_name
                                           """))
                actual_tables = set(row[0] for row in result)

            elif "sqlite" in database_url.lower() or database_url.startswith("sqlite"):
                result = session.exec(text("""
                                           SELECT name
                                           FROM sqlite_master
                                           WHERE type = 'table'
                                             AND name NOT LIKE 'sqlite_%'
                                           ORDER BY name
                                           """))
                actual_tables = set(row[0] for row in result)

            else:
                logger.warning("未识别的数据库类型，使用SQLAlchemy inspector")
                inspector = inspect(engine)
                actual_tables = set(inspector.get_table_names())

            logger.info(f"实际存在的表: {sorted(actual_tables)}")

            # 比较表
            missing_tables = expected_tables - actual_tables
            extra_tables = actual_tables - expected_tables

            if missing_tables:
                logger.warning(f"⚠️  缺少的表: {sorted(missing_tables)}")

            if extra_tables:
                logger.info(f"📋 额外的表: {sorted(extra_tables)}")

            if not missing_tables:
                logger.info("✅ 所有期望的表都存在！")

                # 验证表结构
                logger.info("正在验证表结构...")
                for table_name in expected_tables:
                    try:
                        # 简单的查询测试
                        session.exec(text(f"SELECT COUNT(*) FROM {table_name}"))
                        logger.info(f"  ✅ {table_name} - 结构正常")
                    except Exception as e:
                        logger.warning(f"  ⚠️  {table_name} - 结构可能有问题: {e}")

                return True
            else:
                return False

    except Exception as e:
        logger.error(f"❌ 表验证失败: {e}")
        logger.error(traceback.format_exc())
        return False


def drop_all_tables(engine):
    """删除所有表"""
    try:
        logger.info("⚠️  开始删除所有表...")

        # 获取要删除的表信息
        tables_info = get_all_table_info()
        logger.info(f"将要删除 {len(tables_info)} 个表:")
        for table_name in tables_info.keys():
            logger.info(f"  - {table_name}")

        # 删除所有表
        SQLModel.metadata.drop_all(engine)

        logger.info("✅ 所有表已删除")
        return True

    except Exception as e:
        logger.error(f"❌ 删除表失败: {e}")
        logger.error(traceback.format_exc())
        return False


def show_detailed_info(engine, database_url):
    """显示详细的数据库信息"""
    logger.info("=" * 60)
    logger.info("数据库详细信息")
    logger.info("=" * 60)

    logger.info(f"数据库URL: {database_url}")

    # 连接状态
    if verify_database_connection(engine, database_url):
        logger.info("连接状态: ✅ 正常")
    else:
        logger.info("连接状态: ❌ 失败")
        return

    # 模型信息
    tables_info = get_all_table_info()
    logger.info(f"定义的模型数量: {len(tables_info)}")

    logger.info("\n模型详情:")
    for table_name, info in tables_info.items():
        logger.info(f"  📋 {table_name}:")
        logger.info(f"     列数: {info['column_count']}")
        for col in info['columns']:
            flags = []
            if col['primary_key']:
                flags.append("PK")
            if col['foreign_key']:
                flags.append("FK")
            if not col['nullable']:
                flags.append("NOT NULL")

            flag_str = f" [{', '.join(flags)}]" if flags else ""
            logger.info(f"       - {col['name']}: {col['type']}{flag_str}")

    # 实际表状态
    logger.info("\n实际表状态:")
    verify_tables_exist(engine, database_url)

    logger.info("=" * 60)


def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description='完整的数据库管理工具')
    parser.add_argument('--init', action='store_true', help='初始化数据库（创建所有表）')
    parser.add_argument('--verify', action='store_true', help='验证表结构')
    parser.add_argument('--drop', action='store_true', help='删除所有表（危险操作）')
    parser.add_argument('--reset', action='store_true', help='重置数据库（删除后重新创建）')
    parser.add_argument('--info', action='store_true', help='显示详细数据库信息')

    args = parser.parse_args()

    try:
        # 导入所有模型
        engine, database_url = import_all_models()

        if args.info:
            show_detailed_info(engine, database_url)

        elif args.verify:
            if verify_database_connection(engine, database_url):
                verify_tables_exist(engine, database_url)

        elif args.drop:
            if verify_database_connection(engine, database_url):
                confirm = input("⚠️  确定要删除所有表吗？这将删除所有数据！(输入 'YES' 确认): ")
                if confirm == 'YES':
                    drop_all_tables(engine)
                else:
                    logger.info("操作已取消")

        elif args.reset:
            if verify_database_connection(engine, database_url):
                confirm = input("⚠️  确定要重置数据库吗？这将删除所有数据并重新创建表！(输入 'YES' 确认): ")
                if confirm == 'YES':
                    logger.info("🔄 开始重置数据库...")
                    if drop_all_tables(engine) and create_all_tables(engine):
                        logger.info("✅ 数据库重置完成")
                        verify_tables_exist(engine, database_url)
                    else:
                        logger.error("❌ 数据库重置失败")
                else:
                    logger.info("操作已取消")

        elif args.init:
            if verify_database_connection(engine, database_url):
                if create_all_tables(engine):
                    verify_tables_exist(engine, database_url)

        else:
            # 默认行为：显示信息并询问是否初始化
            show_detailed_info(engine, database_url)

            if verify_database_connection(engine, database_url):
                # 检查是否需要初始化
                tables_info = get_all_table_info()
                expected_tables = set(tables_info.keys())

                try:
                    with Session(engine) as session:
                        if "postgresql" in database_url.lower():
                            result = session.exec(text("""
                                                       SELECT table_name
                                                       FROM information_schema.tables
                                                       WHERE table_schema = 'public'
                                                         AND table_type = 'BASE TABLE'
                                                       """))
                            actual_tables = set(row[0] for row in result)
                        else:
                            result = session.exec(text("""
                                                       SELECT name
                                                       FROM sqlite_master
                                                       WHERE type = 'table'
                                                         AND name NOT LIKE 'sqlite_%'
                                                       """))
                            actual_tables = set(row[0] for row in result)

                    missing_tables = expected_tables - actual_tables

                    if missing_tables:
                        logger.info(f"\n发现缺少 {len(missing_tables)} 个表")
                        response = input("是否现在初始化数据库？(y/N): ").strip().lower()
                        if response in ['y', 'yes']:
                            if create_all_tables(engine):
                                verify_tables_exist(engine, database_url)
                    else:
                        logger.info("\n所有表都已存在，数据库状态正常")

                except Exception as e:
                    logger.info(f"\n无法检查现有表（可能是新数据库）: {e}")
                    response = input("是否现在初始化数据库？(y/N): ").strip().lower()
                    if response in ['y', 'yes']:
                        if create_all_tables(engine):
                            verify_tables_exist(engine, database_url)

    except KeyboardInterrupt:
        logger.info("\n操作已取消")
    except Exception as e:
        logger.error(f"❌ 程序执行失败: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == "__main__":
    main()
