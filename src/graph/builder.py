from langgraph.graph import StateGraph, START, END

from .types import State
from .nodes import (
    supervisor_node,
    research_node,
    code_node,
    coordinator_node,
    browser_node,
    reporter_node,
    planner_node,
    human_in_the_loop_node,  # 匯入新節點
)


def build_graph():
    """Build and return the agent workflow graph."""
    builder = StateGraph(State)
    builder.add_node("coordinator", coordinator_node)
    builder.add_node("planner", planner_node)
    builder.add_node("human_in_the_loop", human_in_the_loop_node)  # 新增節點
    builder.add_node("supervisor", supervisor_node)
    builder.add_node("researcher", research_node)
    builder.add_node("coder", code_node)
    builder.add_node("browser", browser_node)
    builder.add_node("reporter", reporter_node)

    # 定义图的边
    builder.add_edge(START, "coordinator")
    builder.add_edge("coordinator", "planner")
    builder.add_edge("planner", "human_in_the_loop")  # planner -> human_in_the_loop

    # 根據 HITL 的結果決定下一步
    builder.add_conditional_edges(
        "human_in_the_loop",
        lambda x: x["next"],
        {
            "supervisor": "supervisor",
            "planner": "planner",
            "__end__": END
        }
    )

    builder.add_conditional_edges(
        "supervisor",
        lambda x: x["next"],
        {
            "researcher": "researcher",
            "coder": "coder",
            "browser": "browser",
            "reporter": "reporter",
            "__end__": END,
        },
    )

    builder.add_edge("researcher", "supervisor")
    builder.add_edge("coder", "supervisor")
    builder.add_edge("browser", "supervisor")
    builder.add_edge("reporter", "supervisor")

    return builder.compile()