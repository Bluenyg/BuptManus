# utils/auth.py
import jwt
import hashlib
from datetime import datetime, timedelta
from typing import Optional
import secrets
import os

# JWT 配置 - 如果没有设置密钥则自动生成
def get_or_create_jwt_secret():
    secret = os.getenv("JWT_SECRET_KEY")
    if not secret:
        # 如果没有设置，生成一个临时密钥（仅用于开发）
        secret = secrets.token_urlsafe(64)
        print(f"⚠️  警告: JWT_SECRET_KEY 未设置，使用临时密钥")
        print(f"   请将以下内容添加到你的 .env 文件中：")
        print(f"   JWT_SECRET_KEY={secret}")
    return secret

SECRET_KEY = get_or_create_jwt_secret()
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_DAYS = 365


def hash_password(password: str) -> str:
    """对密码进行哈希处理"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """创建JWT访问令牌"""
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=ACCESS_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


def verify_token(token: str) -> Optional[dict]:
    """验证JWT令牌"""
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        return payload
    except jwt.PyJWTError:
        return None


def generate_api_key() -> str:
    """生成API密钥"""
    return secrets.token_urlsafe(32)
