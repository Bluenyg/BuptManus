# routes/threads_no_auth.py
from fastapi import APIRouter, Depends, status
from sqlmodel import Session, select, and_
from db.database import get_session
from db.models import (User, Thread, ThreadStatus, ThreadTask, ThreadMessage,
                       ThreadChatType, ThreadChatFromChoices, UserType)
from schemas.threads import CreateThread
from typing import Dict, Any
from utils.procedures import CustomError, extract_json
from utils import ai_helpers, ai_prompts, llm_provider
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import HumanMessage
import json

router = APIRouter(
    prefix='/apps/threads',
    tags=['threads-no-auth']
)


def get_default_user(db: Session = Depends(get_session)) -> User:
    """获取默认用户"""
    query = select(User).where(User.email == 'default@system.local')
    user = db.exec(query).first()
    if not user:
        user = User(
            name="Default User",
            email="default@system.local",
            user_type=UserType.NORMAL_USER
        )
        db.add(user)
        db.commit()
        db.refresh(user)
    return user


@router.post('/no-auth')
def create_thread_no_auth(
        create_thread_obj: CreateThread,
        db: Session = Depends(get_session),
        user: User = Depends(get_default_user)
) -> Dict[str, Any]:
    """创建线程（无需认证）"""

    # 检查是否有正在运行的线程
    working_threads = db.exec(select(Thread).where(and_(
        Thread.user_id == user.id,
        Thread.status == ThreadStatus.WORKING
    ))).all()

    if len(working_threads) > 0:
        raise CustomError(status.HTTP_400_BAD_REQUEST, 'Running_Thread')

    # 简化的分类逻辑
    task_lower = create_thread_obj.task.lower()

    if any(keyword in task_lower for keyword in
           ["open", "click", "type", "find", "browser", "file", "desktop", "screenshot"]):
        response_data = {
            'type': 'desktop_task',
            'thread_id': '',  # 稍后填充
            'is_background_mode_requested': False,
            'is_extended_thinking_mode_requested': False,
            'needs_memory_from_previous_tasks': False
        }
    else:
        response_data = {
            'type': 'general_task',
            'thread_id': '',
            'message': 'This is a general conversation task'
        }

    # 创建线程
    instance = Thread(
        title=ai_helpers.generate_thread_title(create_thread_obj.task),
        user_id=user.id,
        current_task=create_thread_obj.task,
    )
    db.add(instance)
    db.commit()
    db.refresh(instance)

    # 创建用户消息
    user_message = ThreadMessage(
        thread_id=instance.id,
        thread_chat_type=ThreadChatType.NORMAL_MESSAGE,
        thread_chat_from=ThreadChatFromChoices.FROM_USER,
        text=create_thread_obj.task,
    )
    db.add(user_message)
    db.commit()
    db.refresh(user_message)

    response_data['thread_id'] = instance.id

    if response_data.get('type') == 'desktop_task':
        # 创建桌面任务
        thread_task = ThreadTask(
            thread_id=instance.id,
            task_text=create_thread_obj.task,
            needs_memory_from_previous_tasks=False,
            background_mode=False,
            extended_thinking_mode=False,
        )
        db.add(thread_task)
        db.commit()
        db.refresh(thread_task)

        # 设置线程为工作状态
        instance.status = ThreadStatus.WORKING
        db.add(instance)
        db.commit()
        db.refresh(instance)

    # 创建AI回复消息
    ai_message = ThreadMessage(
        thread_id=instance.id,
        thread_chat_type=ThreadChatType.CLASSIFICATION,
        thread_chat_from=ThreadChatFromChoices.FROM_AI,
        text=json.dumps(response_data),
    )
    db.add(ai_message)
    db.commit()
    db.refresh(ai_message)

    return response_data


@router.get('/{thread_id}/no-auth')
def get_thread_no_auth(
        thread_id: str,
        db: Session = Depends(get_session),
        user: User = Depends(get_default_user)
) -> Dict[str, Any]:
    """获取线程信息（无需认证）"""

    instance = db.exec(select(Thread).where(and_(
        Thread.id == thread_id,
        Thread.user_id == user.id,
        Thread.status != ThreadStatus.DELETED
    ))).first()

    if not instance:
        raise CustomError(status.HTTP_404_NOT_FOUND, 'Thread not found')

    return {
        "thread_id": instance.id,
        "title": instance.title,
        "status": instance.status,
        "current_task": instance.current_task,
        "created_at": instance.created_at.isoformat() if instance.created_at else None
    }
