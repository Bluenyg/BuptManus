# src/daily_tools_mcp/daily_tools_mcp_server.py

import asyncio
import logging
import sys
import os
import json

# 动态添加项目根目录到 sys.path
try:
    project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
    if project_root not in sys.path:
        sys.path.insert(0, project_root)
except NameError:
    sys.path.insert(0, os.path.abspath('.'))

# 使用正确的 MCP SDK 导入
from mcp.server.models import InitializationOptions
from mcp.server.stdio import stdio_server
from mcp.server import NotificationOptions, Server
from mcp.types import (
    CallToolResult,
    ListToolsResult,
    Tool,
    TextContent,
)

# 导入工具
from src.daily_tools_mcp.tools import *
from src.daily_tools_mcp.tools.base_tool import BaseTool

# 设置日志 - 使用标准错误输出，避免与 stdio 通信冲突
logging.basicConfig(
    stream=sys.stderr,
    level=logging.DEBUG,  # 改为 DEBUG 级别
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    force=True
)
logger = logging.getLogger("daily_tools_mcp_server")

# 创建服务器实例
server = Server("daily_tools_mcp")

# 工具注册表
tools_registry: dict[str, BaseTool] = {}


def load_and_register_tools():
    """加载和注册工具"""
    logger.info("Starting to load and register tools...")

    tool_classes_to_register = [
        LogisticsTool,
        # 添加其他工具类
    ]

    for tool_class in tool_classes_to_register:
        try:
            logger.debug(f"Attempting to register tool: {tool_class.__name__}")
            instance = tool_class()
            if isinstance(instance, BaseTool):
                tools_registry[instance.get_name()] = instance
                logger.info(f"Successfully registered tool: {instance.get_name()}")
            else:
                logger.warning(f"Tool {tool_class.__name__} is not a BaseTool instance")
        except Exception as e:
            logger.exception(f"Failed to register tool {tool_class.__name__}: {e}")


# 加载工具
load_and_register_tools()


@server.list_tools()
async def handle_list_tools() -> ListToolsResult:
    """处理工具列表请求"""
    logger.info(f"Handling list_tools request. Available tools: {list(tools_registry.keys())}")

    tools = []
    for name, instance in tools_registry.items():
        try:
            tool = Tool(
                name=name,
                description=instance.get_description(),
                inputSchema=instance.get_input_schema()
            )
            tools.append(tool)
            logger.debug(f"Added tool to list: {name}")
        except Exception as e:
            logger.error(f"Error creating tool descriptor for {name}: {e}")

    logger.info(f"Returning {len(tools)} tools to client")
    return ListToolsResult(tools=tools)


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
    """处理工具调用请求"""
    logger.info(f"Calling tool: {name} with args: {arguments}")

    instance = tools_registry.get(name)
    if not instance:
        error_msg = f"Unknown tool: {name}. Available tools: {list(tools_registry.keys())}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True
        )

    try:
        result = await instance.execute(arguments)
        logger.info(f"Tool {name} executed successfully")
        return CallToolResult(
            content=[TextContent(type="text", text=str(result))]
        )
    except Exception as e:
        error_msg = f"Error executing tool {name}: {str(e)}"
        logger.exception(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True
        )


async def main():
    """主函数"""
    try:
        logger.info("=" * 50)
        logger.info("Starting Daily Tools MCP Server...")
        logger.info(f"Python version: {sys.version}")
        logger.info(f"Working directory: {os.getcwd()}")
        logger.info(f"Server script path: {__file__}")

        # 确保至少有一个工具注册
        if not tools_registry:
            logger.error("CRITICAL: No tools registered! Server will be useless.")
            sys.exit(1)
        else:
            logger.info(f"Successfully registered {len(tools_registry)} tools: {list(tools_registry.keys())}")

        # 创建初始化选项
        init_options = InitializationOptions(
            server_name="daily_tools_mcp",
            server_version="0.1.0",
            capabilities=server.get_capabilities(
                notification_options=NotificationOptions(),
                experimental_capabilities={},
            ),
        )

        logger.info("Server capabilities initialized")
        logger.info("Starting stdio server...")

        # 使用 stdio_server 运行服务器
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Stdio streams established")
            logger.info("Server is ready to accept connections")

            # 运行服务器
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )

    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.exception(f"FATAL: Server error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    try:
        # 设置事件循环策略 (Windows)
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

        logger.info("Starting asyncio event loop...")
        asyncio.run(main())

    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.exception(f"FATAL: Unhandled exception: {e}")
        sys.exit(1)
    finally:
        logger.info("Server shutdown complete")
