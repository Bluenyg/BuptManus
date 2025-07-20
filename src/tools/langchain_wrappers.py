# src/tools/langchain_wrappers.py
from typing import Dict, Any, List
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import logging

logger = logging.getLogger(__name__)


class MCPToolWrapper(BaseTool):
    """MCP 工具的 LangChain 包装器"""

    name: str = Field(...)
    description: str = Field(...)
    tool_name: str = Field(...)

    def _run(self, **kwargs: Any) -> str:
        """运行工具"""
        from .mcp_tools import call_mcp_tool_sync
        try:
            return call_mcp_tool_sync(self.tool_name, kwargs)
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name}: {e}")
            return f"工具调用失败: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """异步运行工具"""
        from .mcp_tools import call_mcp_tool
        try:
            return await call_mcp_tool(self.tool_name, kwargs)
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name}: {e}")
            return f"工具调用失败: {str(e)}"


def create_langchain_tools() -> List[BaseTool]:
    """创建 LangChain 工具列表"""
    from .mcp_tools import get_mcp_tools_sync

    tools = []

    try:
        # 获取 MCP 工具
        mcp_tools = get_mcp_tools_sync()

        for tool_info in mcp_tools:
            # 创建 LangChain 工具
            tool = MCPToolWrapper(
                name=tool_info["name"],
                description=tool_info["description"],
                tool_name=tool_info["name"]
            )
            tools.append(tool)

        logger.info(f"Created {len(tools)} LangChain tools from MCP")

    except Exception as e:
        logger.error(f"Failed to create LangChain tools: {e}")
        tools = []

    return tools


# 模块级别的工具缓存
_langchain_tools = None


def get_langchain_tools() -> List[BaseTool]:
    """获取 LangChain 工具列表（带缓存）"""
    global _langchain_tools

    if _langchain_tools is None:
        _langchain_tools = create_langchain_tools()

    return _langchain_tools
