from typing import Literal, Optional
from typing_extensions import TypedDict
from langgraph.graph import MessagesState

from src.config import TEAM_MEMBERS
from typing import Dict

OPTIONS = TEAM_MEMBERS + ["FINISH"]

class Router(TypedDict):
    """Worker to route to next. If no workers needed, route to FINISH."""

    next: Literal[*OPTIONS]


class State(MessagesState):
    """State for the agent system, extends MessagesState with next field."""

    # Constants
    TEAM_MEMBERS: list[str]

    # Runtime Variables
    next: str
    full_plan: str
    deep_thinking_mode: bool
    search_before_planning: bool
    user_feedback: Optional[str] = None # 新增一个栏位
    image_base64: Optional[str] = None  # 用来存储图片
    # 用于追踪每个任务的重试次数
    task_retry_counts: Dict[str, int]