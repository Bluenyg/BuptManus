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
    args_schema: Optional[Dict[str, Any]] = Field(default=None)  # 改名避免冲突

    def _extract_args(self, **kwargs: Any) -> Dict[str, Any]:
        """提取并清理参数"""
        # 检查是否有嵌套的 kwargs
        if len(kwargs) == 1 and 'kwargs' in kwargs:
            args = kwargs['kwargs']
            logger.info(f"Extracted nested kwargs: {args}")
        else:
            args = kwargs
            logger.info(f"Using direct kwargs: {args}")

        return args

    def _run(self, **kwargs: Any) -> str:
        """运行工具"""
        from .mcp_tools import call_mcp_tool_sync

        try:
            # 参数预处理
            args = self._extract_args(**kwargs)

            # 参数名称映射 - 处理参数名不匹配的问题
            if self.tool_name == "track_logistics":
                # 将 courier_number 映射为 tracking_number
                if 'courier_number' in args and 'tracking_number' not in args:
                    args['tracking_number'] = args.pop('courier_number')
                # 将 courier_company 映射为 company
                if 'courier_company' in args and 'company' not in args:
                    args['company'] = args.pop('courier_company')
                # 将 phone_number 映射为 phone
                if 'phone_number' in args and 'phone' not in args:
                    args['phone'] = args.pop('phone_number')

                logger.info(f"Mapped parameters for track_logistics: {args}")

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
            # 参数预处理
            args = self._extract_args(**kwargs)

            # 参数名称映射
            if self.tool_name == "track_logistics":
                if 'courier_number' in args and 'tracking_number' not in args:
                    args['tracking_number'] = args.pop('courier_number')
                if 'courier_company' in args and 'company' not in args:
                    args['company'] = args.pop('courier_company')
                if 'phone_number' in args and 'phone' not in args:
                    args['phone'] = args.pop('phone_number')

                logger.info(f"Mapped parameters for track_logistics: {args}")

            logger.info(f"Async calling MCP tool {self.tool_name} with args: {args}")
            result = await call_mcp_tool_async(self.tool_name, args)
            logger.info(f"MCP tool {self.tool_name} async result: {result}")
            return result
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.tool_name}: {e}")
            return f"工具调用失败: {str(e)}"


def create_langchain_tools() -> List[BaseTool]:
    """创建 LangChain 工具列表"""
    from .mcp_tools import get_mcp_tools_sync

    tools = []

    try:
        # 获取 MCP 工具实例
        mcp_tools_instance = get_mcp_tools_sync()

        # 获取工具列表
        mcp_tools_list = mcp_tools_instance.get_available_tools()

        for tool_info in mcp_tools_list:
            # 创建 LangChain 工具
            tool = MCPToolWrapper(
                name=tool_info["name"],
                description=tool_info["description"],
                tool_name=tool_info["name"],
                args_schema=tool_info.get("input_schema")  # 使用新的字段名
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


def refresh_langchain_tools() -> List[BaseTool]:
    """刷新 LangChain 工具列表"""
    global _langchain_tools
    _langchain_tools = None
    return get_langchain_tools()