# create_default_user.py
import sys
import os
from datetime import datetime, timezone, timedelta

# 添加项目根目录到 Python 路径
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlmodel import Session, select
from db.database import engine
from db.models import User, UserType
from utils.auth import hash_password, create_access_token, generate_api_key
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def create_default_user():
    """创建默认用户并生成访问令牌"""

    # 默认用户信息 - 根据实际的User模型字段调整
    DEFAULT_USER_DATA = {
        "email": "default@system.local",
        "name": "Default System User",  # 使用 name 而不是 full_name
        "password": "default_password_change_me"
    }

    try:
        with Session(engine) as session:
            # 检查默认用户是否已存在
            existing_user = session.exec(
                select(User).where(User.email == DEFAULT_USER_DATA["email"])
            ).first()

            if existing_user:
                logger.info(f"默认用户已存在: {existing_user.email}")
                user = existing_user
            else:
                # 根据你的User模型创建用户
                user_data = {
                    "email": DEFAULT_USER_DATA["email"],
                    "name": DEFAULT_USER_DATA["name"],
                    "password": hash_password(DEFAULT_USER_DATA["password"]),  # 使用 password 字段
                    "user_type": UserType.NORMAL_USER,
                    "is_email_verified": True,  # 设置为已验证
                    "is_blocked": False,
                    "created_at": datetime.now(timezone.utc),  # 使用新的datetime API
                    "updated_at": datetime.now(timezone.utc)
                }

                # 如果User模型有api_key字段，添加它
                try:
                    user_data["api_key"] = generate_api_key()
                except:
                    # 如果generate_api_key函数不存在或User模型没有api_key字段，忽略
                    pass

                user = User(**user_data)
                session.add(user)
                session.commit()
                session.refresh(user)

                logger.info(f"✅ 默认用户创建成功: {user.email}")

            # 生成访问令牌
            token_data = {
                "sub": str(user.id),  # subject (用户ID)
                "email": user.email,
                "name": user.name  # 使用 name 字段
            }

            access_token = create_access_token(
                data=token_data,
                expires_delta=timedelta(days=365)  # 1年有效期
            )

            # 输出重要信息
            print("\n" + "=" * 60)
            print("🎉 默认用户创建/更新成功！")
            print("=" * 60)
            print(f"用户ID: {user.id}")
            print(f"邮箱: {user.email}")
            print(f"姓名: {user.name}")
            print(f"用户类型: {user.user_type}")
            print(f"邮箱已验证: {user.is_email_verified}")

            # 如果有api_key字段才显示
            if hasattr(user, 'api_key') and user.api_key:
                print(f"API密钥: {user.api_key}")

            print(f"创建时间: {user.created_at}")
            print(f"更新时间: {user.updated_at}")

            print("\n" + "-" * 60)
            print("🔑 访问令牌 (NEURALAGENT_USER_ACCESS_TOKEN):")
            print("-" * 60)
            print(access_token)
            print("\n" + "-" * 60)
            print("📋 环境变量设置:")
            print("-" * 60)
            print(f"export NEURALAGENT_USER_ACCESS_TOKEN='{access_token}'")
            print(f"# 或者在 .env 文件中添加:")
            print(f"NEURALAGENT_USER_ACCESS_TOKEN={access_token}")
            print("=" * 60)

            return {
                "user": user,
                "access_token": access_token,
                "api_key": getattr(user, 'api_key', None)
            }

    except Exception as e:
        logger.error(f"❌ 创建默认用户失败: {e}")
        import traceback
        traceback.print_exc()
        return None


def show_user_model_info():
    """显示User模型的字段信息，帮助调试"""
    try:
        from db.models import User

        print("\n" + "=" * 60)
        print("User 模型字段信息")
        print("=" * 60)

        # 获取模型字段
        if hasattr(User, '__table__'):
            for column in User.__table__.columns:
                nullable = "可空" if column.nullable else "必填"
                default = f" (默认: {column.default.arg if column.default else 'None'})" if column.default else ""
                print(f"  {column.name}: {column.type} - {nullable}{default}")
        else:
            print("无法获取表结构信息")

        print("=" * 60)

    except Exception as e:
        logger.error(f"获取模型信息失败: {e}")


def update_user_token(user_email: str = "default@system.local"):
    """为现有用户重新生成访问令牌"""
    try:
        with Session(engine) as session:
            user = session.exec(
                select(User).where(User.email == user_email)
            ).first()

            if not user:
                logger.error(f"用户不存在: {user_email}")
                return None

            # 生成新的访问令牌
            token_data = {
                "sub": str(user.id),
                "email": user.email,
                "name": user.name
            }

            access_token = create_access_token(
                data=token_data,
                expires_delta=timedelta(days=365)
            )

            print(f"\n🔑 用户 {user_email} 的新访问令牌:")
            print("-" * 60)
            print(access_token)
            print("-" * 60)

            return access_token

    except Exception as e:
        logger.error(f"❌ 更新用户令牌失败: {e}")
        return None


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description='默认用户管理工具')
    parser.add_argument('--create', action='store_true', help='创建默认用户')
    parser.add_argument('--update-token', type=str, help='为指定用户重新生成令牌')
    parser.add_argument('--show-model', action='store_true', help='显示User模型字段信息')

    args = parser.parse_args()

    if args.show_model:
        show_user_model_info()
    elif args.update_token:
        update_user_token(args.update_token)
    else:
        create_default_user()
