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

# 设置日志 - 确保日志立即刷新
handler = logging.StreamHandler(sys.stderr)
handler.flush = sys.stderr.flush
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - SERVER - %(levelname)s - %(message)s',
    handlers=[handler],
    force=True,
)

logger = logging.getLogger(__name__)

# 创建服务器实例
server = Server("daily_tools_mcp")

# 工具注册表
tools_registry: dict[str, BaseTool] = {}


def load_and_register_tools():
    """加载和注册工具"""
    logger.info("Starting to load and register tools...")

    # 根据你的工具结构来注册
    tool_classes_to_register = [
        LogisticsTool,
        # 未来可以添加更多工具
        # WeatherTool,
        # TranslatorTool,
    ]

    for tool_class in tool_classes_to_register:
        try:
            instance = tool_class()
            tools_registry[instance.get_name()] = instance
            logger.info(f"Successfully registered tool: {instance.get_name()}")
        except Exception as e:
            logger.exception(f"Failed to register tool {tool_class.__name__}: {e}")

    logger.info(f"Total tools registered: {len(tools_registry)}")


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
        except Exception as e:
            logger.error(f"Error creating tool definition for {name}: {e}")

    logger.info(f"Returning {len(tools)} tools to client")
    return ListToolsResult(tools=tools)


@server.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> CallToolResult:
    """处理工具调用请求"""
    logger.info(f"Calling tool: {name} with args: {json.dumps(arguments, ensure_ascii=False, indent=2)}")

    instance = tools_registry.get(name)
    if not instance:
        error_msg = f"Unknown tool: {name}. Available tools: {list(tools_registry.keys())}"
        logger.error(error_msg)
        return CallToolResult(
            content=[TextContent(type="text", text=error_msg)],
            isError=True
        )

    try:
        # 调用你的工具实例
        result = await instance.execute(arguments)
        logger.info(f"Tool {name} executed successfully")
        logger.debug(f"Tool result: {result[:200]}...")  # 只显示前200个字符

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
    # 确保在 Windows 上使用正确的事件循环策略
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

    logger.info("=" * 50)
    logger.info("Starting Daily Tools MCP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Project root: {project_root}")

    # 加载并注册所有工具
    load_and_register_tools()

    if not tools_registry:
        logger.error("CRITICAL: No tools registered! Server will now exit.")
        logger.error("Please check that your tool classes are properly imported and instantiated.")
        sys.exit(1)

    logger.info(f"Successfully registered {len(tools_registry)} tools:")
    for tool_name, tool_instance in tools_registry.items():
        logger.info(f"  - {tool_name}: {tool_instance.get_description()}")

    # 初始化选项
    init_options = InitializationOptions(
        server_name="daily_tools_mcp",
        server_version="0.1.0",
        capabilities=server.get_capabilities(
            notification_options=NotificationOptions(),
            experimental_capabilities={},
        ),
    )

    logger.info("Server capabilities initialized. Starting stdio server...")

    try:
        # stdio_server 管理读写流的生命周期
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Stdio streams established. Server is ready and waiting for client initialization.")
            # 确保所有缓冲都已刷新
            sys.stdout.flush()
            sys.stderr.flush()

            # server.run() 是一个将永远运行的循环，直到连接关闭
            await server.run(
                read_stream,
                write_stream,
                init_options,
            )
    except Exception as e:
        logger.exception(f"FATAL: Server loop error: {e}")
        sys.exit(1)
    finally:
        logger.info("Server run loop has exited.")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server stopped by user.")
    except Exception as e:
        logger.exception(f"FATAL: Unhandled exception in __main__: {e}")
    finally:
        logger.info("Server shutdown complete.")
        sys.stdout.flush()
        sys.stderr.flush()
