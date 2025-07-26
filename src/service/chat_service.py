from sqlalchemy.orm import Session
from sqlalchemy import desc
from typing import List, Dict, Any, Optional
from datetime import datetime
import json
import uuid
import logging
from typing import Union

from src.models.chat import ChatSession, ChatMessageRecord

# 添加日志配置
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ChatService:

    @staticmethod
    def get_sessions(db: Session, user_id: str) -> List[Dict[str, Any]]:
        try:
            logger.info(f"Getting sessions for user: {user_id}")

            sessions = db.query(ChatSession).filter(
                ChatSession.user_id == user_id
            ).order_by(desc(ChatSession.updated_at)).all()

            logger.info(f"Found {len(sessions)} sessions from database")

            result = []
            for session in sessions:
                # 确保返回一致的格式
                session_data = {
                    "id": session.id,
                    "title": session.title or "新对话",
                    "created_at": session.created_at.isoformat() if session.created_at else "",
                    "createdAt": session.created_at.isoformat() if session.created_at else "",
                }
                result.append(session_data)

            logger.info(f"Returning sessions: {result}")
            return result

        except Exception as e:
            logger.error(f"Error in get_sessions: {e}", exc_info=True)
            return []

    @staticmethod
    def create_session(db: Session, user_id: str, title: str = "新对话") -> Dict[str, Any]:
        try:
            session_id = str(uuid.uuid4())
            now = datetime.now()

            new_session = ChatSession(
                id=session_id,
                user_id=user_id,
                title=title,
                created_at=now,
                updated_at=now
            )

            db.add(new_session)
            db.commit()
            db.refresh(new_session)

            # 返回前端期望的格式
            return {
                "id": new_session.id,
                "title": new_session.title,
                "createdAt": new_session.created_at.isoformat(),
                "created_at": new_session.created_at.isoformat(),  # 兼容两种格式
            }
        except Exception as e:
            db.rollback()
            logger.error(f"Error creating session: {e}")
            raise e

    @staticmethod
    def delete_session(db: Session, session_id: str) -> bool:
        try:
            # 先删除相关的消息
            db.query(ChatMessageRecord).filter(
                ChatMessageRecord.session_id == session_id
            ).delete()

            # 再删除会话
            result = db.query(ChatSession).filter(
                ChatSession.id == session_id
            ).delete()

            db.commit()
            return result > 0

        except Exception as e:
            db.rollback()
            logger.error(f"Error deleting session {session_id}: {e}")
            raise e

    @staticmethod
    def get_messages(db: Session, session_id: str) -> List[Dict[str, Any]]:
        try:
            messages = db.query(ChatMessageRecord).filter(
                ChatMessageRecord.session_id == session_id
            ).order_by(ChatMessageRecord.created_at).all()

            result = []
            for msg in messages:
                message_data = {
                    "id": msg.id,
                    "role": msg.role,
                    "content": msg.content,
                    "created_at": msg.created_at.isoformat() if msg.created_at else ""
                }
                result.append(message_data)

            return result

        except Exception as e:
            logger.error(f"Error getting messages for session {session_id}: {e}")
            return []

    @staticmethod
    def save_message(db: Session, session_id: str, role: str, content: Union[str, List[Dict]]) -> Dict[str, Any]:
        try:
            message_id = str(uuid.uuid4())
            now = datetime.now()

            # 处理多模态内容
            if isinstance(content, list):
                # 如果是多模态内容，转换为JSON字符串保存
                content_str = json.dumps(content, ensure_ascii=False)
            else:
                content_str = str(content)

            new_message = ChatMessageRecord(
                id=message_id,
                session_id=session_id,
                role=role,
                content=content_str,
                created_at=now
            )

            db.add(new_message)

            # 更新会话的 updated_at
            session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
            if session:
                session.updated_at = now

            db.commit()
            db.refresh(new_message)

            return {
                "id": new_message.id,
                "role": new_message.role,
                "content": new_message.content,
                "created_at": new_message.created_at.isoformat()
            }

        except Exception as e:
            db.rollback()
            logger.error(f"Error saving message: {e}")
            raise e
