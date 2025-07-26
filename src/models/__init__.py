# src/models/__init__.py
from .chat import ChatSession, ChatMessageRecord

# 为了兼容性，可以添加别名
ChatHistory = ChatSession

__all__ = ['ChatSession', 'ChatMessageRecord', 'ChatHistory']
