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


# life_tools_agent 的创建逻辑是正确的，需要延迟执行
def get_life_tools_agent():
    """创建并返回 Life Tools Agent (使用MCP工具)"""
    mcp_tools: List[Tool] = get_langchain_tools()

    if not mcp_tools:
        print("警告: life_tools_agent 未能从 MCP 加载任何工具。")

    agent = create_react_agent(
        get_llm_by_type(AGENT_LLM_MAP.get("life_tools", "basic")),
        tools=mcp_tools,
        prompt=lambda state: apply_prompt_template("life_tools", state)
    )
    return agent


life_tools_agent = get_life_tools_agent()
