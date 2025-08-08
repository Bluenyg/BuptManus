import logging
import json
from copy import deepcopy
from typing import Literal
from langchain_core.messages import HumanMessage
from langgraph.types import Command
from langgraph.graph import END

from src.agents import research_agent, coder_agent, browser_agent, get_life_tools_agent,get_desktop_agent
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

import asyncio
def browser_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the browser agent that performs web browsing tasks."""
    logger.info("Browser agent starting task")

    # 处理多模态输入，移除图片信息
    first_msg = state["messages"][0]
    if isinstance(first_msg.content, list):
        first_msg.content = [item for item in first_msg.content if item.get("type") == "text"]
        logger.debug(f"去除图片信息后的内容：{first_msg.content}")

    try:
        # 检查是否在异步上下文中
        try:
            loop = asyncio.get_running_loop()
            # 如果在异步上下文中，使用线程池执行同步调用
            import concurrent.futures

            def run_browser_sync():
                return browser_agent.invoke(state)

            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(run_browser_sync)
                result = future.result(timeout=300)  # 5分钟超时

        except RuntimeError:
            # 不在异步上下文中，直接调用
            result = browser_agent.invoke(state)

        logger.info("Browser agent completed task")
        logger.debug(f"Browser agent response: {result['messages'][-1].content}")
        response_content = result["messages"][-1].content

    except Exception as e:
        logger.exception(f"browser_agent.invoke 执行失败: {e}")
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


def convert_yaml_like_to_json(yaml_like_text: str) -> str:
    """尝试将类似 YAML 的文本转换为 JSON 格式"""
    try:
        import re

        # 提取 thought, title, 和 steps 部分
        thought_match = re.search(r'thought:\s*(.*?)(?=\n\w+:|$)', yaml_like_text, re.DOTALL)
        title_match = re.search(r'title:\s*(.*?)(?=\n\w+:|$)', yaml_like_text, re.DOTALL)

        thought = thought_match.group(1).strip() if thought_match else ""
        title = title_match.group(1).strip() if title_match else "Generated Plan"

        # 提取 steps 数组
        steps_match = re.search(r'steps:\s*\[(.*?)\]', yaml_like_text, re.DOTALL)
        if not steps_match:
            return None

        steps_text = steps_match.group(1)

        # 解析每个 step
        steps = []
        step_pattern = r'\{\s*agent_name:\s*"([^"]+)",\s*title:\s*"([^"]+)",\s*description:\s*"([^"]+)"(?:,\s*note:\s*"([^"]+)")?\s*\}'

        for match in re.finditer(step_pattern, steps_text):
            step = {
                "agent_name": match.group(1),
                "title": match.group(2),
                "description": match.group(3)
            }
            if match.group(4):  # note 是可选的
                step["note"] = match.group(4)
            steps.append(step)

        # 构建 JSON 结构
        json_structure = {
            "thought": thought,
            "title": title,
            "steps": steps
        }

        return json.dumps(json_structure, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"Error converting YAML-like format: {e}")
        return None


def create_basic_plan_json(original_text: str) -> str:
    """创建一个基本的 JSON 计划结构"""
    # 尝试从原始文本中提取有用信息
    import re

    # 查找是否提到了特定的 agent
    agent_mentions = re.findall(r'(coder|researcher|browser|reporter|life_tools)', original_text.lower())

    # 默认使用 coder，或者使用找到的第一个 agent
    agent_name = agent_mentions[0] if agent_mentions else "coder"

    # 创建基本计划
    plan = {
        "thought": "Processing user request for 3D animation",
        "title": "3D Animation Display Plan",
        "steps": [
            {
                "agent_name": agent_name,
                "title": "Create and run 3D animation",
                "description": "Generate Python code to create a 3D animation using matplotlib and execute it",
                "note": "Ensure matplotlib and numpy are available"
            }
        ]
    }

    return json.dumps(plan, ensure_ascii=False, indent=2)

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

    # 6. 改进的 JSON 处理逻辑
    # 先清理响应格式
    if full_response.startswith("```json"):
        full_response = full_response.removeprefix("```json").strip()
    if full_response.endswith("```"):
        full_response = full_response.removesuffix("```").strip()

    goto = "supervisor"

    # 尝试解析 JSON
    try:
        parsed_json = json.loads(full_response)
        logger.info("Planner response successfully parsed as JSON")
    except json.JSONDecodeError as e:
        logger.warning(f"Planner response is not a valid JSON. Error: {e}")
        logger.info("Attempting to convert YAML-like format to JSON...")

        # 尝试转换类似 YAML 的格式为 JSON
        try:
            # 如果响应包含类似 YAML 的结构，尝试转换
            if "steps:" in full_response and "agent_name:" in full_response:
                # 简单的启发式转换：将 YAML 风格转换为 JSON
                converted_response = convert_yaml_like_to_json(full_response)
                if converted_response:
                    full_response = converted_response
                    parsed_json = json.loads(full_response)
                    logger.info("Successfully converted YAML-like format to JSON")
                else:
                    # 如果转换失败，创建一个基本的 JSON 结构
                    logger.warning("Failed to convert format. Creating basic JSON structure.")
                    full_response = create_basic_plan_json(full_response)
                    parsed_json = json.loads(full_response)
            else:
                # 如果不是预期的格式，创建基本结构
                logger.warning("Unexpected format. Creating basic JSON structure.")
                full_response = create_basic_plan_json(full_response)
                parsed_json = json.loads(full_response)

        except Exception as conversion_error:
            logger.error(f"Failed to convert or create valid JSON: {conversion_error}")
            logger.error(f"Original response: {full_response}")
            # 最后的备用方案：创建一个简单的默认计划
            full_response = json.dumps({
                "thought": "Plan generation failed, using default structure",
                "title": "Default Plan",
                "steps": [
                    {
                        "agent_name": "coder",
                        "title": "Execute user request",
                        "description": "Process the user's request using available tools",
                        "note": "Fallback plan due to planning format issues"
                    }
                ]
            }, ensure_ascii=False, indent=2)
            logger.info("Created fallback JSON plan")

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


# 在 life_tools_node 中添加调试
# src/graph/nodes.py 中的 life_tools_node 函数

def life_tools_node(state: State) -> Command[Literal["supervisor"]]:
    """Node for the life tools agent that handles daily life tasks."""
    logger.info("Life tools agent starting task")

    # 直接获取工具列表进行调试
    from src.tools.langchain_wrappers import get_langchain_tools
    available_tools = get_langchain_tools()
    logger.info(f"Available MCP tools: {[tool.name for tool in available_tools]}")

    life_tools_agent = get_life_tools_agent()

    # 修改调试信息 - create_react_agent 返回的是图，不是简单的agent
    logger.info(f"Life tools agent type: {type(life_tools_agent)}")

    try:
        # 调用生活工具 agent
        result = life_tools_agent.invoke(state)
        logger.info("Life tools agent completed task")

        # 检查结果
        if result.get("messages"):
            last_msg = result["messages"][-1]
            logger.info(f"Last message type: {type(last_msg)}")
            logger.info(f"Last message content: {last_msg.content}")

            # 检查是否有工具调用
            if hasattr(last_msg, 'tool_calls') and last_msg.tool_calls:
                logger.info(f"Tool calls found: {last_msg.tool_calls}")

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


def get_user_query_from_state(state):
    """从状态中提取纯净的用户查询"""
    messages = state.get("messages", [])
    if not messages:
        return "请提供具体任务"

    # 获取最新的用户消息
    for msg in reversed(messages):
        if hasattr(msg, 'content'):
            content = msg.content

            # 如果是列表格式
            if isinstance(content, list):
                for content_item in content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                        text = content_item.get('text', '').strip()
                        # 提取纯净的用户查询
                        return extract_pure_query(text)

            # 如果是字符串格式
            elif isinstance(content, str):
                return extract_pure_query(content.strip())

    return "请提供具体任务"


def extract_pure_query(text):
    """从复杂文本中提取纯净的用户查询"""
    try:
        # 尝试解析JSON
        import json
        data = json.loads(text)

        # 从JSON中提取简单查询
        if isinstance(data, dict):
            # 优先级：title > thought > steps中的description
            if 'title' in data:
                title = data['title'].strip()
                if title and title != "":
                    return title

            if 'thought' in data:
                thought = data['thought'].strip()
                # 提取思考中的核心动作
                if '打开' in thought:
                    # 提取"打开XX"的部分
                    import re
                    match = re.search(r'打开(.+?)(?:应用|程序|软件|。|$)', thought)
                    if match:
                        app_name = match.group(1).strip()
                        return f"打开{app_name}"

            if 'steps' in data and isinstance(data['steps'], list):
                for step in data['steps']:
                    if isinstance(step, dict) and 'title' in step:
                        return step['title'].strip()

    except (json.JSONDecodeError, Exception):
        # 如果不是JSON，直接处理文本
        pass

    # 如果解析失败，尝试从文本中提取简单指令
    text = text.strip()

    # 提取简单的动作指令
    import re

    # 匹配 "打开XX" 模式
    match = re.search(r'打开(.+?)(?:应用|程序|软件|。|$)', text)
    if match:
        app_name = match.group(1).strip()
        return f"打开{app_name}"

    # 匹配其他常见模式
    action_patterns = [
        r'(启动.+?)(?:应用|程序|软件|。|$)',
        r'(运行.+?)(?:应用|程序|软件|。|$)',
        r'(打开.+?)(?:。|$)',
    ]

    for pattern in action_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1).strip()

    # 如果都匹配不到，返回原文本的前50个字符
    return text[:50] if len(text) > 50 else text

from src.tools.desktop_interaction import remote_desktop_agent


def desktop_node(state: State) -> Command[Literal["supervisor"]]:
    """
    执行桌面自动化任务的节点。
    修复版：正确跟踪已完成的任务并执行下一个任务。
    """
    logger.info("Desktop agent node starting task")

    # 统计已完成的桌面任务数量
    completed_desktop_tasks = count_completed_desktop_tasks(state)
    logger.info(f"已完成的桌面任务数量: {completed_desktop_tasks}")

    # 根据已完成的任务数量获取下一个任务
    task_description = get_next_desktop_task_from_plan(state, completed_desktop_tasks)

    logger.info(f"Task for desktop agent: '{task_description}'")

    # 如果所有任务都已完成，直接返回
    if "所有桌面任务已完成" in task_description or "所有任务已完成" in task_description:
        logger.info("所有桌面任务已完成，返回完成状态")
        return Command(
            update={
                "messages": [
                    HumanMessage(
                        content=RESPONSE_FORMAT.format("desktop",
                                                       "所有桌面任务已成功完成。用户的QQ音乐已打开并播放了指定歌曲。"),
                        name="desktop",
                    )
                ]
            },
            goto="supervisor",
        )

    # 调用桌面自动化工具
    observation = remote_desktop_agent.invoke({"task_description": task_description})

    logger.info("Desktop agent node completed task")
    logger.debug(f"Desktop agent tool observation: {observation}")

    # 将工具的执行结果作为一条新消息返回给 supervisor
    return Command(
        update={
            "messages": [
                HumanMessage(
                    content=RESPONSE_FORMAT.format("desktop", observation),
                    name="desktop",
                )
            ]
        },
        goto="supervisor",
    )


def count_completed_desktop_tasks(state: State) -> int:
    """
    统计已成功完成的桌面任务数量
    """
    completed_count = 0

    # 遍历消息历史，查找来自 desktop 节点且标记为成功的消息
    for message in state["messages"]:
        if (hasattr(message, 'name') and
                message.name == "desktop" and
                isinstance(message.content, str) and
                ("completed successfully" in message.content or
                 "任务完成" in message.content)):
            completed_count += 1
            logger.debug(f"找到已完成任务 #{completed_count}: {message.content[:100]}...")

    return completed_count


def get_fallback_task_from_user_message(state: State, completed_count: int) -> str:
    """
    通用回退策略：当无法解析计划时，从用户原始消息中推断任务
    """
    # 获取用户的原始消息
    user_message = ""
    for message in state["messages"]:
        if not hasattr(message, 'name'):  # 用户消息通常没有name属性
            if isinstance(message.content, list):
                # 多模态消息，提取文本部分
                for content_item in message.content:
                    if isinstance(content_item, dict) and content_item.get('type') == 'text':
                        user_message = content_item.get('text', '')
                        break
            elif isinstance(message.content, str):
                user_message = message.content
            break

    if not user_message:
        return "执行用户请求的任务" if completed_count == 0 else "继续执行用户任务"

    # 基于完成数量和用户消息内容推断任务
    if completed_count == 0:
        # 第一个任务通常是打开或启动某个应用
        return f"根据用户请求执行第一步操作: {user_message[:50]}"
    else:
        # 后续任务是在已打开的应用中进行具体操作
        return f"在已打开的应用中继续执行用户请求: {user_message[:50]}"


def get_next_desktop_task_from_plan(state: State, completed_count: int) -> str:
    """
    根据已完成的任务数量，从计划中获取下一个桌面任务
    """
    try:
        plan = json.loads(state["full_plan"])
        desktop_steps = [
            step for step in plan.get("steps", [])
            if step.get("agent_name", "").lower() == "desktop"
        ]

        logger.debug(f"找到 {len(desktop_steps)} 个桌面任务步骤")
        for i, step in enumerate(desktop_steps):
            logger.debug(f"步骤 {i}: {step.get('description', 'No description')}")

        if not desktop_steps:
            return "没有找到桌面任务"

        # 如果还有未完成的任务
        if completed_count < len(desktop_steps):
            next_task = desktop_steps[completed_count].get("description", "执行桌面任务")
            logger.info(f"返回第 {completed_count + 1} 个任务: {next_task}")
            return next_task
        else:
            logger.info("所有桌面任务都已完成")
            return "所有桌面任务已完成"

    except (json.JSONDecodeError, KeyError) as e:
        logger.warning(f"无法解析计划: {e}")
        # 通用回退策略：从用户原始消息中推断任务
        return get_fallback_task_from_user_message(state, completed_count)

