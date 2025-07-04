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

import os
logger = logging.getLogger(__name__)

RESPONSE_FORMAT = "Response from {}:\n\n<response>\n{}\n</response>\n\n*Please execute the next step.*"

#经验库的导入
EXPERIENCE_LOG_PATH = os.path.join(os.path.dirname(__file__), '..', 'data', 'experience_log.json')



def load_experience_log() -> list:
    """载入经验库"""
    if not os.path.exists(EXPERIENCE_LOG_PATH):
        return []
    with open(EXPERIENCE_LOG_PATH, 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except json.JSONDecodeError:
            return []

def save_experience_log(data: dict):
    """存储到经验库"""
    log = load_experience_log()
    log.append(data)
    with open(EXPERIENCE_LOG_PATH, 'w', encoding='utf-8') as f:
        json.dump(log, f, indent=2, ensure_ascii=False)

def human_in_the_loop_node(state: State) -> Command[Literal["supervisor", "planner", "__end__"]]:
    """Human-in-the-loop node to get user feedback."""
    logger.info("Human-in-the-loop: Awaiting user feedback.")
    full_plan = state.get("full_plan")

    # 在真實應用中，這裡會透過 API 或 UI 與使用者互動
    # 為了演示，我們使用 console input 來模擬
    print("\n" + "=" * 50)
    print("PLANNER'S PROPOSED PLAN:")
    print(full_plan)
    print("=" * 50)

    feedback = input("Do you approve this plan? (yes/no, or provide your feedback): ")

    # 儲存經驗
    experience_data = {
        "original_plan": json.loads(full_plan),
        "user_feedback": feedback
    }
    save_experience_log(experience_data)

    if feedback.lower() == 'yes':
        logger.info("User approved the plan. Proceeding to supervisor.")
        goto = "supervisor"
        user_feedback_message = "User approved the plan."
    else:
        logger.info(f"User provided feedback: {feedback}. Returning to planner.")
        goto = "planner"
        user_feedback_message = f"User has new suggestions, please replan based on the following: {feedback}"

    return Command(
        update={
            "messages": state["messages"] + [HumanMessage(content=user_feedback_message, name="user_feedback")],
            "user_feedback": feedback,
        },
        goto=goto,
    )


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

    return Command(goto=goto, update={"next": goto})


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
    """Coordinator node that communicates with customers and handles multimodal input."""
    logger.info("Coordinator talking.")

    # 從 state 中解析最原始的輸入
    # 這部分需要根據你的 app.py 如何傳入資料來調整
    initial_input_str = state["messages"][0].content
    try:
        initial_input_data = json.loads(initial_input_str)
        user_prompt = initial_input_data.get("messages", [{}])[0].get("content", "")
        image_base64 = initial_input_data.get("image_base64")
    except (json.JSONDecodeError, IndexError):
        # 如果解析失敗，則視為純文字輸入
        user_prompt = initial_input_str
        image_base64 = None

    # 建立多模態訊息內容
    multimodal_content = [{"type": "text", "text": user_prompt}]
    if image_base64:
        multimodal_content.append(
            {
                "type": "image_url",
                "image_url": {
                    "url": f"data:image/png;base64,{image_base64}"
                }
            }
        )
        logger.info("Image data found and included in the message for the coordinator.")

    # 建立新的 messages 列表
    # 我們用處理過的多模態訊息替換掉原始的 state message
    processed_messages = [HumanMessage(content=multimodal_content)]

    # 將處理後的訊息傳遞給 prompt 模板
    # 注意：這裡假設你的 coordinator prompt 能夠直接處理這種結構的訊息
    templated_messages = apply_prompt_template("coordinator", {"messages": processed_messages})

    llm = get_llm_by_type(AGENT_LLM_MAP["coordinator"])
    response = llm.invoke(templated_messages)

    logger.debug(f"Coordinator response: {response}")

    goto = "__end__"
    if "handoff_to_planner" in response.content:
        goto = "planner"

    # 將原始的使用者文字提示和圖片資訊儲存到 state 中，供後續節點使用
    return Command(
        goto=goto,
        update={
            "messages": [HumanMessage(content=user_prompt, name="coordinator_handoff")],
            "image_base64": image_base64,
        }
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
