from sqlmodel import Session, select
from db.database import get_session
from db.models import User, UserType
from fastapi import Depends

def get_default_user(db: Session = Depends(get_session)) -> User:
    """获取默认用户"""
    query = select(User).where(User.email == 'default@system.local')
    user = db.exec(query).first()
    if not user:
        # 如果没有默认用户，创建一个
        user = User(
            name="Default User",
            email="default@system.local",
            user_type=UserType.NORMAL_USER
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user
