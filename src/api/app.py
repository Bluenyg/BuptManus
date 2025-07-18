"""
FastAPI application for LangManus.
"""

import json
import logging
import asyncio
import base64 # 新增：用於 Base64 編碼
from typing import Dict, List, Any, Optional, Union

# 導入 FastAPI 相關模組，並新增 File, Form, UploadFile
from fastapi import FastAPI, HTTPException, Request, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from src.graph import build_graph
from src.config import TEAM_MEMBERS
from src.service.workflow_service import run_agent_workflow

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
    allow_origins=["*"],  # Allows all origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Create the graph
graph = build_graph()


class ContentItem(BaseModel):
    type: str = Field(..., description="The type of content (text, image, etc.)")
    text: Optional[str] = Field(None, description="The text content if type is 'text'")
    image_url: Optional[str] = Field(
        None, description="The image URL if type is 'image'"
    )


class ChatMessage(BaseModel):
    role: str = Field(
        ..., description="The role of the message sender (user or assistant)"
    )
    content: Union[str, List[ContentItem]] = Field(
        ...,
        description="The content of the message, either a string or a list of content items",
    )


class ChatRequest(BaseModel):
    messages: List[ChatMessage] = Field(..., description="The conversation history")
    debug: Optional[bool] = Field(False, description="Whether to enable debug logging")
    deep_thinking_mode: Optional[bool] = Field(
        False, description="Whether to enable deep thinking mode"
    )
    search_before_planning: Optional[bool] = Field(
        False, description="Whether to search before planning"
    )


# 合并后的统一聊天接口
@app.post("/api/chat/stream")
async def chat_stream_endpoint(
        req: Request,
        # 所有字段都从 Form 中获取
        messages: str = Form(...),
        debug: bool = Form(False),
        deep_thinking_mode: bool = Form(False),
        search_before_planning: bool = Form(False),
        # 图片文件是可选的
        image: Optional[UploadFile] = File(None),
):
    """
    统一的聊天接口，支持纯文本和带图片的多模态输入。
    此接口接收 multipart/form-data 格式的请求。
    """
    logger.info("Received request for /api/chat/stream")
    try:
        # 1. 解析从表单传来的 messages JSON 字符串
        try:
            messages_data = json.loads(messages)
        except json.JSONDecodeError:
            logger.error(f"Failed to parse messages JSON: {messages}")
            raise HTTPException(status_code=400, detail="Invalid JSON format for messages")

        # 2. 如果有图片文件，处理并更新消息内容
        if image:
            logger.info(f"Processing uploaded image: {image.filename}")
            # 验证文件类型
            if not image.content_type or not image.content_type.startswith("image/"):
                raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

            # 读取图片字节并编码为 Base64 Data URL
            image_bytes = await image.read()
            base64_image = base64.b64encode(image_bytes).decode('utf-8')
            mime_type = image.content_type
            image_url = f"data:{mime_type};base64,{base64_image}"

            # 找到最后一条用户消息来附加图片
            last_user_message_index = -1
            for i in range(len(messages_data) - 1, -1, -1):
                if messages_data[i].get("role") == "user":
                    last_user_message_index = i
                    break

            if last_user_message_index != -1:
                # 获取原始文本内容
                original_content = messages_data[last_user_message_index].get("content", "")

                # 构建新的多模态 content
                new_content = [
                    {"type": "text", "text": original_content},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]
                messages_data[last_user_message_index]["content"] = new_content
            else:
                # 如果没有用户消息，就创建一条新的
                messages_data.append({"role": "user", "content": [
                    {"type": "text", "text": ""},
                    {"type": "image_url", "image_url": {"url": image_url}},
                ]})

        # 3. 准备输入并执行工作流 (这段逻辑对于两种情况是通用的)
        final_input = {"messages": messages_data}

        async def event_generator():
            try:
                # 注意：这里我们直接使用 messages_data，它已经是正确的格式
                # 核心修正：将关键字参数从 'messages' 改为 'user_input_messages'
                async for event in run_agent_workflow(
                        user_input_messages=final_input["messages"],
                        debug=debug,
                        deep_thinking_mode=deep_thinking_mode,
                        search_before_planning=search_before_planning,
                ):
                    if await req.is_disconnected():
                        logger.info("Client disconnected, stopping workflow")
                        break
                    yield {
                        "event": event["event"],
                        "data": json.dumps(event["data"], ensure_ascii=False),
                    }
            except asyncio.CancelledError:
                logger.info("Stream processing cancelled")
                raise
            except Exception as e:
                logger.error(f"Error in workflow execution: {e}", exc_info=True)
                # 可以在这里发送一个错误事件给前端
                yield {
                    "event": "error",
                    "data": json.dumps({"error": str(e)})
                }

        return EventSourceResponse(
            event_generator(),
            media_type="text/event-stream",
            sep="\n",
        )
    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))