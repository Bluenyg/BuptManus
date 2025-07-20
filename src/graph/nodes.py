import logging
import json
from copy import deepcopy
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END

from src.agents import research_agent, coder_agent, browser_agent, life_tools_agent
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

    # 处理多模态输入，移除图片信息
    first_msg = state["messages"][0]
    if isinstance(first_msg.content, list):
        first_msg.content = [item for item in first_msg.content if item.get("type") == "text"]
        logger.debug(f"去除图片信息后的内容：{first_msg.content}")

    try:
        result = browser_agent.invoke(state)
        logger.info("Browser agent completed task")
        logger.debug(f"Browser agent response: {result['messages'][-1].content}")

        response_content = result["messages"][-1].content

    except Exception as e:
        logger.exception(f"browser_agent.invoke 执行失败: {e}")
        # 在异常情况下提供默认的错误响应
        response_content = f"Browser agent encountered an error: {str(e)}"

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("browser", response_content),
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
    """
    Planner node that generates the full plan.
    It dynamically selects a vision-capable LLM if an image is present in the input.
    """
    logger.info("Planner generating full plan")

    # 1. Preparar los mensajes para el LLM
    messages = apply_prompt_template("planner", state)

    # 2. Determinar si la entrada es multimodal
    # LangChain formatea las entradas multimodales como una lista de diccionarios en el contenido del mensaje.
    last_message = state["messages"][-1]
    is_multimodal_input = isinstance(last_message.content, list)

    # 3. Seleccionar el LLM dinámicamente
    llm = None
    if is_multimodal_input:
        logger.info("Multimodal input detected. Using vision LLM for planning.")
        # Usamos el LLM de visión que ya tienes configurado en llm.py
        llm = get_llm_by_type("vision")
    else:
        logger.info("Text-only input detected. Selecting LLM based on thinking mode.")
        # Mantenemos la lógica original para entradas de solo texto
        if state.get("deep_thinking_mode"):
            llm = get_llm_by_type("reasoning")
        else:
            llm = get_llm_by_type("basic")

    # 4. (Opcional) Añadir resultados de búsqueda si es necesario
    if state.get("search_before_planning"):
        # Extraer el texto del prompt del usuario, incluso en casos multimodales
        user_prompt_text = ""
        if is_multimodal_input:
            # En una lista de contenidos, el texto suele ser el primer elemento
            text_part = next((item for item in last_message.content if item.get("type") == "text"), None)
            if text_part:
                user_prompt_text = text_part.get("text", "")
        else:
            user_prompt_text = last_message.content

        if user_prompt_text:
            searched_content = tavily_tool.invoke({"query": user_prompt_text})
            messages = deepcopy(messages)
            messages[
                -1].content += f"\n\n# Relative Search Results\n\n{json.dumps([{'titile': elem['title'], 'content': elem['content']} for elem in searched_content], ensure_ascii=False)}"
        else:
            logger.warning("Search before planning was enabled, but no text was found in the user message.")

    # 5. Invocar el LLM y procesar la respuesta
    logger.debug(f"Current state messages: {state['messages']}")
    stream = llm.stream(messages)
    full_response = ""
    for chunk in stream:
        full_response += chunk.content
    logger.debug(f"Planner response: {full_response}")

    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json")
    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```")

    goto = "supervisor"
    try:
        # Es crucial que el modelo de visión también devuelva un JSON válido.
        # Puede que necesites ajustar tu prompt para asegurarte de esto.
        json.loads(full_response)
    except json.JSONDecodeError:
        logger.warning(f"Planner response is not a valid JSON. Response:\n{full_response}")
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



def life_tools_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the life tools agent that handles daily life tasks."""
    logger.info("Life tools agent starting task")

    try:
        # 调用生活工具 agent
        result = life_tools_agent.invoke(state)
        logger.info("Life tools agent completed task")

        logger.debug(f"Life tools agent execution result (full state): \n{result}")

        # 提取最终答案
        response_content = result["messages"][-1].content

    except Exception as e:
        logger.exception(f"life_tools_agent.invoke failed: {e}")
        response_content = f"Life tools agent encountered an error: {str(e)}"

    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("life_tools", response_content),
                    name="life_tools",
                )
            ]
        },
        goto="supervisor",
    )

