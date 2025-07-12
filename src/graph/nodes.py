import logging
import json
from copy import deepcopy
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END

from src.agents import research_agent, coder_agent, browser_agent
from src.agents.llm import get_llm_by_type
from src.config import TEAM_MEMBERS
from src.config.agents import AGENT_LLM_MAP
from src.prompts.template import apply_prompt_template
from src.tools.search import tavily_tool
from .types import State, Router

logger = logging.getLogger(__name__)

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"


def research_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the researcher agent that performs research tasks."""
    logger.info("Research agent starting task")
    result = research_agent.invoke(state)
    logger.info("Research agent completed task")
    logger.debug(f"Research agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        "researcher", result["messages"][-1].content
                    ),
                    name="researcher",
                )
            ]
        },
        goto="supervisor",
    )


def code_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the coder agent that executes Python code."""
    logger.info("Code agent starting task")
    result = coder_agent.invoke(state)
    logger.info("Code agent completed task")
    logger.debug(f"Code agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        "coder", result["messages"][-1].content
                    ),
                    name="coder",
                )
            ]
        },
        goto="supervisor",
    )


def browser_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the browser agent that performs web browsing tasks."""
    logger.info("Browser agent starting task")
    result = browser_agent.invoke(state)
    logger.info("Browser agent completed task")
    logger.debug(f"Browser agent response: {result['messages'][-1].content}")
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format(
                        "browser", result["messages"][-1].content
                    ),
                    name="browser",
                )
            ]
        },
        goto="supervisor",
    )


def supervisor_node(state: State) -> Command[Literal[*TEAM_MEMBERS, "__end__"]]:
    """Supervisor node that decides which agent should act next."""
    logger.info("Supervisor evaluating next action")

    # --- 新增：重试逻辑 ---
    MAX_RETRIES = 2  # 设置每个任务的最大重试次数
    # 初始化或获取重试计数器
    retry_counts = state.get("task_retry_counts", {})

    # 获取上一个执行的节点名称
    last_node = state.get("next")

    # 检查上一个节点是否是工具节点并且失败了 (通过检查最后一条消息的内容)
    # 这是一个简化的判断，您可以根据需要做得更精确
    if last_node and last_node in TEAM_MEMBERS and "错误" in state["messages"][-1].content:
        # 增加对应任务的重试次数
        retry_counts[last_node] = retry_counts.get(last_node, 0) + 1
        logger.warning(f"任务 '{last_node}' 失败，重试次数: {retry_counts[last_node]}")

        # 如果超过最大重试次数，则强制结束或转到报告节点
        if retry_counts[last_node] > MAX_RETRIES:
            logger.error(f"任务 '{last_node}' 已超过最大重试次数，工作流将结束。")
            return Command(goto="__end__", update={"task_retry_counts": retry_counts})

    # --- 原有逻辑开始 ---
    messages = apply_prompt_template("supervisor", state)
    response = (
        get_llm_by_type(AGENT_LLM_MAP["supervisor"])
        .with_structured_output(Router)
        .invoke(messages)
    )
    goto = response["next"]
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Supervisor response: {response}")

    if goto == "FINISH":
        goto = "__end__"
        logger.info("Workflow completed")
    else:
        logger.info(f"Supervisor delegating to: {goto}")
        # 如果分配了新任务，可以清零它的计数器（可选，但推荐）
        retry_counts[goto] = 0

    return Command(goto=goto, update={"next": goto, "task_retry_counts": retry_counts})


def planner_node(state: State) -> Command[Literal["supervisor", "__end__"]]:
    """Planner node that generate the full plan."""
    logger.info("Planner generating full plan")
    messages = apply_prompt_template("planner", state)
    # whether to enable deep thinking mode
    llm = get_llm_by_type("basic")
    if state.get("deep_thinking_mode"):
        llm = get_llm_by_type("reasoning")
    if state.get("search_before_planning"):
        searched_content = tavily_tool.invoke({"query": state["messages"][-1].content})
        print(f"searched_content: {searched_content}")
        messages = deepcopy(messages)
        messages[
            -1
        ].content += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
    stream = llm.stream(messages)
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"Planner response: {full_response}")

    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json")

    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```")

    goto = "supervisor"
    try:
        json.loads(full_response)
    except json.JSONDecodeError:
        logger.warning("Planner response is not a valid JSON")
        goto = "__end__"

    return Command(
        update={
            "messages": [HumanMessage(content=full_response, name="planner")],
            "full_plan": full_response,
        },
        goto=goto,
    )


def coordinator_node(state: State) -> Command[Literal["planner", "__end__"]]:
    """Coordinator node that communicate with customers."""
    logger.info("Coordinator talking.")
    messages = apply_prompt_template("coordinator", state)
    response = get_llm_by_type(AGENT_LLM_MAP["coordinator"]).invoke(messages)
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"reporter response: {response}")

    goto = "__end__"
    if "handoff_to_planner" in response.content:
        goto = "planner"

    return Command(
        goto=goto,
    )


def reporter_node(state: State) -> Command[Literal["supervisor"]]:
    """Reporter node that write a final report."""
    logger.info("Reporter write final report")
    messages = apply_prompt_template("reporter", state)
    response = get_llm_by_type(AGENT_LLM_MAP["reporter"]).invoke(messages)
    logger.debug(f"Current state messages: {state['messages']}")
    logger.debug(f"reporter response: {response}")

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("reporter", response.content),
                    name="reporter",
                )
            ]
        },
        goto="supervisor",
    )

from dashscope import Application

# --- 更新后的节点函数 ---

def flight_node(state: State) -> Command[Literal["supervisor"]]:
    # 记录日志，表示已进入这个节点
    logger.info("--- 进入 'flight_node' 节点 ---")
    query = state["messages"][0].content
    # 记录收到的具体查询内容
    logger.info(f"收到的查询: {query}")

    response_content = ""  # 默认的空内容，用于在出错时返回
    try:
        # 调用Dashscope应用API
        response = Application.call(
            api_key="sk-c7184ff1b3314d96b14426451a954b3d",
            app_id='9cdb1c6a1f9245c39ae9c4f88edd9acb',
            prompt=query
        )
        # 记录完整的API响应对象，用于详细调试。级别设为DEBUG，平时不显示，需要时再打开。
        logger.debug(f"来自 flight 应用的完整API响应: {response}")

        # 安全地访问输出内容，先判断 response 和 response.output 是否有效
        if response and response.output and response.output.text:
            response_content = response.output.text
            logger.info("成功从 flight API 响应中提取文本。")
        else:
            # 如果API响应无效或没有输出文本，则记录错误
            logger.error("Flight API 响应无效或没有输出文本。")
            logger.error(f"有问题的响应对象: {response}")
            response_content = "错误：机票工具未能获取有效响应。"

    except Exception as e:
        # 捕获所有其他可能的异常，例如网络错误
        logger.exception(f"在 flight_node 中发生意外错误: {e}")
        response_content = "错误：调用机票工具时发生异常。"

    # 返回Command对象，更新状态并指定下一个节点
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="flight", # 消息来源的名称
                )
            ]
        },
        goto="supervisor", # 指定下一个要跳转的节点
    )

def weather_node(state: State) -> Command[Literal["supervisor"]]:
    logger.info("--- 进入 'weather_node' 节点 ---")
    query = state["messages"][0].content
    logger.info(f"收到的查询: {query}")

    response_content = "" # 默认的空内容
    try:
        response = Application.call(
            api_key="sk-c7184ff1b3314d96b14426451a954b3d",
            app_id='c9ee8ae5e6bb45ee8b930de3cfdc8ec9',
            prompt=query
        )
        logger.debug(f"来自 weather 应用的完整API响应: {response}")

        if response and response.output and response.output.text:
            response_content = response.output.text
            logger.info("成功从 weather API 响应中提取文本。")
        else:
            logger.error("Weather API 响应无效或没有输出文本。")
            logger.error(f"有问题的响应对象: {response}")
            response_content = "错误：天气工具未能获取有效响应。"

    except Exception as e:
        logger.exception(f"在 weather_node 中发生意外错误: {e}")
        response_content = "错误：调用天气工具时发生异常。"

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=response_content,
                    name="weather",
                )
            ]
        },
        goto="supervisor",
    )



