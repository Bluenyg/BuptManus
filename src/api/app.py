"""
FastAPI application for LangManus.
"""

import json
import logging
import asyncio
import base64
import re  # 添加这个import
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

from fastapi import FastAPI, HTTPException, Request, File, Form, UploadFile, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse
from sqlalchemy.orm import Session

from src.graph import build_graph
from src.config import TEAM_MEMBERS
from src.service.workflow_service import run_agent_workflow
# 修复导入
from src.database import get_db
from src.models.chat import ChatSession, ChatMessageRecord  # 保持原有导入
from src.service.chat_service import ChatService  # 修正类名

# Configure logging
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BUPTManus API",
    description="API for BUPTManus LangGraph-based agent workflow",
    version="0.1.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Create the graph
graph = build_graph()

class ContentItem(BaseModel):
    type: str
    text: Optional[str] = None
    image_url: Optional[Dict[str, str]] = None

class ChatMessage(BaseModel):
    role: str
    content: Union[str, List[ContentItem]]

class ChatRequest(BaseModel):
    messages: List[ChatMessage]
    conversationId: Optional[str] = None
    debug: bool = False
    deep_thinking_mode: bool = False
    search_before_planning: bool = False

# 响应模型
class SessionResponse(BaseModel):
    id: str
    title: str
    created_at: datetime
    updated_at: datetime

class SessionDetailResponse(BaseModel):
    id: str
    title: str
    messages: List[dict]
    created_at: datetime
    updated_at: datetime

class CreateSessionRequest(BaseModel):
    title: Optional[str] = None

# 添加这个新函数
def parse_message_content(content: str) -> List[Dict[str, Any]]:
    """
    解析消息内容，将包含图片的文本转换为多模态格式

    Args:
        content: 原始消息内容，可能包含文本和图片

    Returns:
        符合多模态格式的内容数组
    """
    # 使用正则表达式匹配图片格式: [image]: data:image/...
    image_pattern = r'\[image\]:\s*(data:image/[^;]+;base64,[A-Za-z0-9+/=]+)'

    # 查找所有图片
    images = re.findall(image_pattern, content)

    # 移除图片标记，获取纯文本
    text_content = re.sub(image_pattern, '', content).strip()
    # 清理多余的换行符
    text_content = re.sub(r'\n\s*\n', '\n', text_content).strip()

    result = []

    # 如果有文本内容，添加文本部分
    if text_content:
        result.append({
            "type": "text",
            "text": text_content
        })

    # 添加所有图片
    for image_data in images:
        result.append({
            "type": "image_url",
            "image_url": {
                "url": image_data
            }
        })

    # 如果没有任何内容，返回原始内容作为文本
    if not result:
        result = [{"type": "text", "text": content}]

    return result

# 修改现有的聊天路由，添加聊天历史保存功能
@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: Request, db: Session = Depends(get_db)):
    """
    Unified chat endpoint that handles both JSON and multipart/form-data requests.
    """
    logger.info("Received request for /api/chat/stream")

    content_type = req.headers.get("content-type", "")
    messages_data = []
    debug = False
    deep_thinking_mode = False
    search_before_planning = False
    conversation_id = None

    try:
        # 场景一：处理 application/json 请求
        if "application/json" in content_type:
            logger.info("Processing JSON request")
            json_body = await req.json()
            chat_req = ChatRequest(**json_body)

            # 获取会话ID
            conversation_id = chat_req.conversationId

            # 处理多模态内容
            messages_data = []
            for msg in chat_req.messages:
                if isinstance(msg.content, str):
                    if '[image]:' in msg.content:
                        content = parse_message_content(msg.content)
                    else:
                        content = msg.content
                else:
                    content = [item.dict() for item in msg.content] if hasattr(msg.content[0], 'dict') else msg.content

                messages_data.append({
                    "role": msg.role,
                    "content": content
                })

            debug = chat_req.debug
            deep_thinking_mode = chat_req.deep_thinking_mode
            search_before_planning = chat_req.search_before_planning

        # 场景二：处理 multipart/form-data 请求
        elif "multipart/form-data" in content_type:
            logger.info("Processing multipart/form-data request")
            form_data = await req.form()

            messages_str = form_data.get("messages")
            if not messages_str:
                raise HTTPException(status_code=400, detail="Missing 'messages' field in form data")
            try:
                messages_data = json.loads(messages_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for 'messages' field")

            conversation_id = form_data.get("conversationId")
            debug = form_data.get("debug", "false").lower() == "true"
            deep_thinking_mode = form_data.get("deep_thinking_mode", "false").lower() == "true"
            search_before_planning = form_data.get("search_before_planning", "false").lower() == "true"

            # 处理图片文件
            image: Optional[UploadFile] = form_data.get("image")
            if image:
                logger.info(f"Processing uploaded image: {image.filename}")
                if not image.content_type or not image.content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

                image_bytes = await image.read()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_url = f"data:{image.content_type};base64,{base64_image}"

                last_user_message_index = next(
                    (i for i, msg in reversed(list(enumerate(messages_data))) if msg.get("role") == "user"), -1)

                if last_user_message_index != -1:
                    original_content = messages_data[last_user_message_index].get("content", "")
                    if isinstance(original_content, str):
                        messages_data[last_user_message_index]["content"] = [{"type": "text", "text": original_content}]

                    messages_data[last_user_message_index]["content"].append(
                        {"type": "image_url", "image_url": {"url": image_url}}
                    )
                else:
                    messages_data.append(
                        {"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]})

        else:
            raise HTTPException(status_code=415, detail=f"Unsupported Content-Type: {content_type}")

        # --- 修正的聊天历史处理逻辑 ---
        user_id = "default_user"

        if conversation_id:
            session = ChatService.get_sessions(db, conversation_id, user_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            conversation_id = session["id"]
        else:
            # 创建新会话
            user_message = messages_data[-1] if messages_data else {"content": "新对话"}
            title = user_message.get("content", "新对话")
            if isinstance(title, list):
                # 如果是多模态内容，提取文本部分
                text_parts = [item.get("text", "") for item in title if item.get("type") == "text"]
                title = " ".join(text_parts) if text_parts else "新对话"
            title = str(title)[:50]  # 限制标题长度

            session = ChatService.create_session(db, user_id, title)
            conversation_id = session["id"]

        # 保存用户消息
        if messages_data:
            last_message = messages_data[-1]
            if last_message.get("role") == "user":
                # 将内容转换为字符串格式保存
                content_to_save = last_message.get("content")
                if isinstance(content_to_save, list):
                    # 如果是多模态内容，转换为JSON字符串
                    content_to_save = json.dumps(content_to_save, ensure_ascii=False)

                ChatService.save_message(db, conversation_id, "user", content_to_save)
                logger.info(f"✅ Saved user message for session {conversation_id}")

        # 工作流执行
        final_input = {"messages": messages_data}

        async def event_generator():
            assistant_response_parts = []
            logger.info(f"🎬 Starting event generator for session: {conversation_id}")

            try:
                async for event in run_agent_workflow(
                        user_input_messages=final_input["messages"],
                        debug=debug,
                        deep_thinking_mode=deep_thinking_mode,
                        search_before_planning=search_before_planning,
                        session_id=conversation_id,
                ):
                    logger.debug(f"📡 Received event: {event.get('event', 'unknown')}")

                    if await req.is_disconnected():
                        logger.warning("🔌 Client disconnected, stopping workflow")
                        break

                    # 收集助手响应内容
                    if event["event"] == "message":
                        delta = event["data"].get("delta", {})
                        content = delta.get("content", "")
                        if content:
                            assistant_response_parts.append(content)
                            logger.debug(f"📝 Collected content chunk (length: {len(content)})")

                    # 发送事件到前端
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }

                # 工作流完成后保存助手响应
                if assistant_response_parts and conversation_id:
                    full_response = "".join(assistant_response_parts)
                    logger.info(
                        f"💾 Saving assistant response (length: {len(full_response)}) to session {conversation_id}")

                    if full_response.strip():  # 确保不是空内容
                        try:
                            ChatService.save_message(db, conversation_id, "assistant", full_response)
                            logger.info(f"✅ Successfully saved assistant message to database")
                        except Exception as save_error:
                            logger.error(f"❌ Failed to save assistant message: {save_error}", exc_info=True)
                    else:
                        logger.warning("⚠️ Assistant response was empty, not saving")
                else:
                    logger.warning(
                        f"⚠️ No assistant response to save. Parts: {len(assistant_response_parts)}, Session: {conversation_id}")

            except Exception as e:
                logger.error(f"❌ Error in event generator: {e}", exc_info=True)
                yield {"event": "error", "data": json.dumps({"error": str(e)})}

            logger.info("🏁 Event generator completed")

        return EventSourceResponse(event_generator(), media_type="text/event-stream", sep="\n")

    except Exception as e:
        logger.error(f"❌ Error in chat endpoint: {e}", exc_info=True)
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail="An internal server error occurred.")

# 修改现有的 sessions 相关 API
@app.get("/api/chat/sessions")
async def get_chat_sessions(db: Session = Depends(get_db)):
    """获取会话列表 - 确保返回数组格式"""
    try:
        user_id = "default_user"
        sessions = ChatService.get_sessions(db, user_id)

        # 确保返回的是数组
        if not isinstance(sessions, list):
            logger.warning(f"Sessions is not a list: {type(sessions)}")
            return []

        logger.info(f"Returning {len(sessions)} sessions to frontend")
        return sessions

    except Exception as e:
        logger.error(f"Error fetching chat sessions: {e}", exc_info=True)
        return []  # 确保返回空数组

@app.post("/api/chat/sessions")
async def create_chat_session(request: Request, db: Session = Depends(get_db)):
    """创建新会话"""
    try:
        try:
            body = await request.json()
        except:
            body = {}

        title = body.get("title", "新对话")
        user_id = "default_user"
        session = ChatService.create_session(db, user_id, title)

        logger.info(f"Created session: {session}")
        return session

    except Exception as e:
        logger.error(f"Error creating session: {e}")
        raise HTTPException(status_code=500, detail="Failed to create session")

@app.delete("/api/chat/sessions/{session_id}")
async def delete_session(
        session_id: str,
        db: Session = Depends(get_db)
):
    try:
        logger.info(f"Deleting session: {session_id}")

        # 查找session
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        # 先删除相关的消息 - 修复模型名称
        deleted_messages = db.query(ChatMessageRecord).filter(
            ChatMessageRecord.session_id == session_id
        ).delete(synchronize_session=False)
        logger.info(f"Deleted {deleted_messages} messages for session {session_id}")

        # 再删除session
        db.delete(session)
        db.commit()

        logger.info(f"Successfully deleted session: {session_id}")
        return {
            "message": "Session deleted successfully",
            "session_id": session_id,
            "deleted_messages": deleted_messages
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting session {session_id}: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/chat/sessions/{session_id}/messages")
async def get_session_messages(
        session_id: str,
        db: Session = Depends(get_db)
):
    try:
        logger.info(f"Fetching messages for session: {session_id}")

        # 检查session是否存在
        session = db.query(ChatSession).filter(ChatSession.id == session_id).first()
        if not session:
            logger.warning(f"Session not found: {session_id}")
            raise HTTPException(status_code=404, detail="Session not found")

        # 获取该会话的所有消息，按时间排序 - 修复模型名称
        messages = db.query(ChatMessageRecord).filter(
            ChatMessageRecord.session_id == session_id
        ).order_by(ChatMessageRecord.created_at.asc()).all()

        logger.info(f"Found {len(messages)} messages for session {session_id}")

        # 转换为前端需要的格式
        formatted_messages = []
        for msg in messages:
            # 尝试解析JSON内容（多模态消息）
            try:
                content = json.loads(msg.content) if msg.content.startswith('[') or msg.content.startswith('{') else msg.content
            except:
                content = msg.content

            formatted_messages.append({
                "id": msg.id,
                "role": msg.role,  # 'user' 或 'assistant'
                "content": content,
                "timestamp": msg.created_at.isoformat() if msg.created_at else None,
                "session_id": msg.session_id
            })

        return formatted_messages

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching messages for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
