# src/tools/langchain_wrappers.py

from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool
from pydantic import BaseModel, Field
import logging
import json

logger = logging.getLogger(__name__)


class MCPToolWrapper(BaseTool):
    """MCP 工具的 LangChain 包装器"""

    name: str = Field(...)
    description: str = Field(...)
    tool_name: str = Field(...)
    # 注意：BaseTool 已经有一个 args_schema 字段，我们最好不要覆盖它。
    # LangChain 会根据 Pydantic 模型自动推断，或者我们可以用 tool_input 来定义。
    # 这里我们保持原样，因为 create_langchain_tools 会动态创建。
    args_schema: Optional[Dict[str, Any]] = Field(default=None)

    def _extract_args(self, **kwargs: Any) -> Dict[str, Any]:
        """提取并清理参数"""
        if len(kwargs) == 1 and 'kwargs' in kwargs:
            args = kwargs['kwargs']
        else:
            args = kwargs
        logger.info(f"Extracted kwargs for tool {self.tool_name}: {args}")
        return args

    def _run(self, **kwargs: Any) -> str:
        """运行工具"""
        from .mcp_tools import call_mcp_tool_sync

        try:
            args = self._extract_args(**kwargs)

            # 关键修改 3: 移除所有不必要的参数映射。
            # 由于我们统一了工具名称和参数，这里不再需要任何转换。
            logger.info(f"Calling MCP tool {self.tool_name} with args: {args}")
            result = call_mcp_tool_sync(self.tool_name, args)
            logger.info(f"MCP tool {self.tool_name} result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name}: {e}")
            return f"工具调用失败: {str(e)}"

    async def _arun(self, **kwargs: Any) -> str:
        """异步运行工具"""
        from .mcp_tools import call_mcp_tool_async

        try:
            args = self._extract_args(**kwargs)

            # 关键修改 3: 同样移除异步方法中的参数映射。
            logger.info(f"Async calling MCP tool {self.tool_name} with args: {args}")
            result = await call_mcp_tool_async(self.tool_name, args)
            logger.info(f"MCP tool {self.tool_name} async result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name}: {e}")
            return f"工具调用失败: {str(e)}"


def get_langchain_tools() -> List[BaseTool]:
    """获取 LangChain 工具列表（每次都重新创建，不使用缓存）"""
    logger.info("开始获取 LangChain 工具列表")

    tools = create_langchain_tools()

    if tools:
        logger.info(f"成功创建 {len(tools)} 个工具: {[tool.name for tool in tools]}")
    else:
        logger.error("没有创建任何工具！")

    return tools


def create_langchain_tools() -> List[BaseTool]:
    """创建 LangChain 工具列表"""
    from .mcp_tools import get_mcp_tools_sync

    tools = []

    try:
        # 每次都重新获取 MCP 工具实例
        mcp_tools_instance = get_mcp_tools_sync()

        # 确保连接是活跃的
        if not mcp_tools_instance.is_initialized:
            import asyncio
            asyncio.run(mcp_tools_instance.connect_to_mcp_server())

        # 获取工具列表
        mcp_tools_list = mcp_tools_instance.get_available_tools()

        for tool_info in mcp_tools_list:
            tool = MCPToolWrapper(
                name=tool_info["name"],
                description=tool_info["description"],
                tool_name=tool_info["name"],
                args_schema=tool_info.get("input_schema")
            )
            tools.append(tool)

        logger.info(f"Created {len(tools)} LangChain tools from MCP")

    except Exception as e:
        logger.error(f"Failed to create LangChain tools: {e}")
        tools = []

    return tools



def refresh_langchain_tools() -> List[BaseTool]:
    """刷新 LangChain 工具列表"""
    global _langchain_tools
    _langchain_tools = None
    return get_langchain_tools()