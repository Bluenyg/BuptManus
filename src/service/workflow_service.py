import logging

from src.config import TEAM_MEMBERS
from src.graph import build_graph
from langchain_community.adapters.openai import convert_message_to_dict
import uuid

# Configure logging
logging.basicConfig(
    level=logging.INFO,  # Default level is INFO
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)


def enable_debug_logging():
    """Enable debug level logging for more detailed execution information."""
    logging.getLogger("src").setLevel(logging.DEBUG)


logger = logging.getLogger(__name__)

# Create the graph
graph = build_graph()

# Cache for coordinator messages
coordinator_cache = []
MAX_CACHE_SIZE = 2

# 在文件顶部添加导入
from src.service.chat_service import ChatService
from src.database import get_db
from sqlalchemy.orm import Session


# 修改 run_agent_workflow 函数
async def run_agent_workflow(
        user_input_messages: list,
        debug: bool = False,
        deep_thinking_mode: bool = False,
        search_before_planning: bool = False,
        session_id: str = None,
        user_id: str = "default_user",
):
    """Run the agent workflow with the given user input."""

    if not user_input_messages:
        raise ValueError("Input could not be empty")

    if debug:
        enable_debug_logging()

    logger.info(f"🚀 Starting workflow for session {session_id} with input: {user_input_messages}")

    workflow_id = str(uuid.uuid4())
    streaming_llm_agents = [*TEAM_MEMBERS, "planner", "coordinator"]

    # 重置协调器缓存
    global coordinator_cache
    coordinator_cache = []
    global is_handoff_case
    is_handoff_case = False

    # 收集完整的助手响应
    assistant_response_parts = []

    try:
        async for event in graph.astream_events(
                {
                    "TEAM_MEMBERS": TEAM_MEMBERS,
                    "messages": user_input_messages,
                    "deep_thinking_mode": deep_thinking_mode,
                    "search_before_planning": search_before_planning,
                },
                version="v2",
        ):
            kind = event.get("event")
            data = event.get("data")
            name = event.get("name")
            metadata = event.get("metadata")
            node = (
                ""
                if (metadata.get("checkpoint_ns") is None)
                else metadata.get("checkpoint_ns").split(":")[0]
            )
            langgraph_step = (
                ""
                if (metadata.get("langgraph_step") is None)
                else str(metadata["langgraph_step"])
            )
            run_id = "" if (event.get("run_id") is None) else str(event["run_id"])

            if kind == "on_chain_start" and name in streaming_llm_agents:
                if name == "planner":
                    yield {
                        "event": "start_of_workflow",
                        "data": {"workflow_id": workflow_id, "input": user_input_messages},
                    }
                ydata = {
                    "event": "start_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chain_end" and name in streaming_llm_agents:
                ydata = {
                    "event": "end_of_agent",
                    "data": {
                        "agent_name": name,
                        "agent_id": f"{workflow_id}_{name}_{langgraph_step}",
                    },
                }
            elif kind == "on_chat_model_start" and node in streaming_llm_agents:
                ydata = {
                    "event": "start_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_end" and node in streaming_llm_agents:
                ydata = {
                    "event": "end_of_llm",
                    "data": {"agent_name": node},
                }
            elif kind == "on_chat_model_stream" and node in streaming_llm_agents:
                content = data["chunk"].content
                if content is None or content == "":
                    if not data["chunk"].additional_kwargs.get("reasoning_content"):
                        continue
                    ydata = {
                        "event": "message",
                        "data": {
                            "message_id": data["chunk"].id,
                            "delta": {
                                "reasoning_content": (
                                    data["chunk"].additional_kwargs["reasoning_content"]
                                )
                            },
                        },
                    }
                else:
                    # 🔥 关键修复：收集所有助手响应内容
                    assistant_response_parts.append(content)
                    logger.debug(f"📝 Collected content from {node}: {content[:50]}...")

                    # 处理协调器逻辑...
                    if node == "coordinator":
                        if len(coordinator_cache) < MAX_CACHE_SIZE:
                            coordinator_cache.append(content)
                            cached_content = "".join(coordinator_cache)
                            if cached_content.startswith("handoff"):
                                is_handoff_case = True
                                continue
                            if len(coordinator_cache) < MAX_CACHE_SIZE:
                                continue
                            ydata = {
                                "event": "message",
                                "data": {
                                    "message_id": data["chunk"].id,
                                    "delta": {"content": cached_content},
                                },
                            }
                        elif not is_handoff_case:
                            ydata = {
                                "event": "message",
                                "data": {
                                    "message_id": data["chunk"].id,
                                    "delta": {"content": content},
                                },
                            }
                    else:
                        ydata = {
                            "event": "message",
                            "data": {
                                "message_id": data["chunk"].id,
                                "delta": {"content": content},
                            },
                        }
            elif kind == "on_tool_start" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_input": data.get("input"),
                    },
                }
            elif kind == "on_tool_end" and node in TEAM_MEMBERS:
                ydata = {
                    "event": "tool_call_result",
                    "data": {
                        "tool_call_id": f"{workflow_id}_{node}_{name}_{run_id}",
                        "tool_name": name,
                        "tool_result": data["output"].content if data.get("output") else "",
                    },
                }
            else:
                continue
            yield ydata

        # 🔥 关键修复：工作流结束后，保存完整的助手响应到数据库
        if assistant_response_parts and session_id:
            full_response = "".join(assistant_response_parts)
            logger.info(f"💾 Saving assistant response to database. Session: {session_id}, Length: {len(full_response)}")

            try:
                # 获取数据库连接并保存助手消息
                db = next(get_db())
                chat_service = ChatService(db)

                await chat_service.add_message(
                    session_id=session_id,
                    role="assistant",
                    content=full_response,
                    user_id=user_id
                )
                logger.info(f"✅ Assistant message saved successfully for session: {session_id}")

            except Exception as e:
                logger.error(f"❌ Failed to save assistant message: {e}", exc_info=True)
            finally:
                db.close()

            # 返回完整响应事件
            yield {
                "event": "assistant_response_complete",
                "data": {
                    "full_response": full_response,
                    "session_id": session_id
                }
            }

        if is_handoff_case:
            yield {
                "event": "end_of_workflow",
                "data": {
                    "workflow_id": workflow_id,
                    "messages": [
                        convert_message_to_dict(msg)
                        for msg in data["output"].get("messages", [])
                    ],
                },
            }

    except Exception as e:
        logger.error(f"❌ Error in workflow: {e}", exc_info=True)
        raise
