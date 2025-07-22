"""
FastAPI application for LangManus.
"""

import json
import logging
import asyncio
import base64
from typing import Dict, List, Any, Optional, Union

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
    conversationId: Optional[str] = None # 兼容前端可能发送的 conversationId
    debug: bool = False
    deep_thinking_mode: bool = False
    search_before_planning: bool = False


# 统一的聊天接口，现在可以处理 JSON 和 multipart/form-data
@app.post("/api/chat/stream")
async def chat_stream_endpoint(req: Request):
    """
    Unified chat endpoint that handles both JSON and multipart/form-data requests.
    - For JSON: Expects a body matching the ChatRequest model.
    - For multipart/form-data: Expects fields like 'messages' (JSON string) and an optional 'image' file.
    """
    logger.info("Received request for /api/chat/stream")

    content_type = req.headers.get("content-type", "")
    messages_data = []
    debug = False
    deep_thinking_mode = False
    search_before_planning = False

    try:
        # 场景一：处理 application/json 请求
        if "application/json" in content_type:
            logger.info("Processing JSON request")
            json_body = await req.json()
            # 使用 Pydantic 模型进行验证和解析
            chat_req = ChatRequest(**json_body)
            messages_data = [msg.dict() for msg in chat_req.messages]
            debug = chat_req.debug
            deep_thinking_mode = chat_req.deep_thinking_mode
            search_before_planning = chat_req.search_before_planning

        # 场景二：处理 multipart/form-data 请求
        elif "multipart/form-data" in content_type:
            logger.info("Processing multipart/form-data request")
            form_data = await req.form()

            # 1. 解析 messages JSON 字符串
            messages_str = form_data.get("messages")
            if not messages_str:
                raise HTTPException(status_code=400, detail="Missing 'messages' field in form data")
            try:
                messages_data = json.loads(messages_str)
            except json.JSONDecodeError:
                raise HTTPException(status_code=400, detail="Invalid JSON format for 'messages' field")

            # 2. 获取其他参数
            debug = form_data.get("debug", "false").lower() == "true"
            deep_thinking_mode = form_data.get("deep_thinking_mode", "false").lower() == "true"
            search_before_planning = form_data.get("search_before_planning", "false").lower() == "true"

            # 3. 处理图片文件
            image: Optional[UploadFile] = form_data.get("image")
            if image:
                logger.info(f"Processing uploaded image: {image.filename}")
                if not image.content_type or not image.content_type.startswith("image/"):
                    raise HTTPException(status_code=400, detail="Uploaded file is not a valid image")

                image_bytes = await image.read()
                base64_image = base64.b64encode(image_bytes).decode('utf-8')
                image_url = f"data:{image.content_type};base64,{base64_image}"

                # 找到最后一条用户消息并附加图片
                last_user_message_index = next((i for i, msg in reversed(list(enumerate(messages_data))) if msg.get("role") == "user"), -1)

                if last_user_message_index != -1:
                    original_content = messages_data[last_user_message_index].get("content", "")
                    # 确保 content 是一个列表
                    if isinstance(original_content, str):
                        messages_data[last_user_message_index]["content"] = [{"type": "text", "text": original_content}]

                    # 附加图片内容
                    messages_data[last_user_message_index]["content"].append(
                        {"type": "image_url", "image_url": {"url": image_url}}
                    )
                else:
                    # 如果没有用户消息，就创建一条新的
                    messages_data.append({"role": "user", "content": [{"type": "image_url", "image_url": {"url": image_url}}]})

        else:
            raise HTTPException(status_code=415, detail=f"Unsupported Content-Type: {content_type}")

        # --- 工作流执行 (通用逻辑) ---
        final_input = {"messages": messages_data}
        async def event_generator():
            try:
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
            except Exception as e:
                logger.error(f"Error in workflow execution: {e}", exc_info=True)
                yield {"event": "error", "data": json.dumps({"error": str(e)})}

        return EventSourceResponse(event_generator(), media_type="text/event-stream", sep="\n")

    except Exception as e:
        logger.error(f"Error in chat endpoint: {e}", exc_info=True)
        # 避免将内部错误直接暴露给客户端
        if isinstance(e, HTTPException):
             raise e
        raise HTTPException(status_code=500, detail="An internal server error occurred.")