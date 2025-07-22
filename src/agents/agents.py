# src/agents/agents.py (可以还原为更简洁的形式)

from langgraph.prebuilt import create_react_agent
from langchain_core.tools import Tool
from typing import List

from src.prompts import apply_prompt_template
from .llm import get_llm_by_type
from src.config.agents import AGENT_LLM_MAP

# --- 现在可以安全地在顶层导入工具了 ---
from src.tools import (
    tavily_tool,
    crawl_tool,
    python_repl_tool,
    bash_tool,
    browser_tool
)
from src.tools.langchain_wrappers import get_langchain_tools

# --- Agent 创建保持原样或使用更简洁的版本 ---

research_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["researcher"]),
    tools=[tavily_tool, crawl_tool],
    prompt=lambda state: apply_prompt_template("researcher", state),
)

coder_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["coder"]),
    tools=[python_repl_tool, bash_tool],
    prompt=lambda state: apply_prompt_template("coder", state),
)

browser_agent = create_react_agent(
    get_llm_by_type(AGENT_LLM_MAP["browser"]),
    tools=[browser_tool],
    prompt=lambda state: apply_prompt_template("browser", state),
)


# src/agents/agents.py 中的 get_life_tools_agent 函数
import logging
logger = logging.getLogger(__name__)

def get_life_tools_agent():
    """创建并返回 Life Tools Agent (使用MCP工具)"""
    from src.tools.langchain_wrappers import get_langchain_tools

    # 每次都重新获取工具
    mcp_tools: List[Tool] = get_langchain_tools()

    logger.info(f"Creating life_tools_agent with {len(mcp_tools)} tools: {[tool.name for tool in mcp_tools]}")

    if not mcp_tools:
        logger.warning("警告: life_tools_agent 未能从 MCP 加载任何工具。")
        # 可以添加一个空工具作为fallback
        from langchain_core.tools import tool

        @tool
        def no_tools_available(query: str) -> str:
            """当没有可用工具时的占位符工具"""
            return "抱歉，当前没有可用的工具来处理您的请求。"

        mcp_tools = [no_tools_available]

    # 确保prompt函数正确
    def life_tools_prompt(state):
        return apply_prompt_template("life_tools", state)

    agent = create_react_agent(
        get_llm_by_type(AGENT_LLM_MAP.get("life_tools", "basic")),
        tools=mcp_tools,
        prompt=life_tools_prompt
    )

    logger.info(f"Life tools agent created successfully with tools: {[tool.name for tool in mcp_tools]}")
    return agent




