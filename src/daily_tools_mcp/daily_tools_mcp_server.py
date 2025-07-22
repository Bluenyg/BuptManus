# src/daily_tools_mcp/daily_tools_mcp_server.py

import asyncio
import sys
import os
import logging
from typing import Any, Sequence
import json

# 添加项目路径到 Python 路径
current_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(current_dir, '..', '..'))
sys.path.insert(0, project_root)

# MCP 服务器导入
from mcp.server.models import InitializationOptions
from mcp.server import NotificationOptions, Server
from mcp.server.stdio import stdio_server
from mcp.types import (
    CallToolRequest,
    CallToolResult,
    ListToolsRequest,
    ListToolsResult,
    Tool,
    TextContent,
)

# 导入工具
from tools.logistics_tool import LogisticsTool

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stderr)  # 使用 stderr 避免与 stdio 通信冲突
    ]
)
logger = logging.getLogger("SERVER")


class DailyToolsMCPServer:
    def __init__(self):
        # 创建 MCP 服务器实例
        self.server = Server("daily_tools_mcp")

        # 工具实例
        self.tools = {}

        # 注册处理器
        self._register_handlers()

        # 初始化工具
        self._initialize_tools()

    def _initialize_tools(self):
        """初始化所有工具"""
        logger.info("Starting to load and register tools...")

        try:
            # 初始化物流工具
            logistics_tool = LogisticsTool()
            # 关键修改 1: 将工具名改为 LLM 期望的名称 "logistics_tracking"
            # 这比让 LLM 适应你的内部命名要可靠得多
            tool_name = "logistics_tracking"
            self.tools[tool_name] = logistics_tool
            logger.info(f"Successfully registered tool: {tool_name}")

            logger.info(f"Successfully registered {len(self.tools)} tools: {list(self.tools.keys())}")

        except Exception as e:
            logger.error(f"Error initializing tools: {e}")
            raise

    def _register_handlers(self):
        """注册请求处理器"""
        logger.debug("Registering handler for ListToolsRequest")
        logger.debug("Registering handler for CallToolRequest")

        @self.server.list_tools()
        async def handle_list_tools() -> list[Tool]:
            """处理工具列表请求"""
            logger.info("Received list_tools request")

            tools = []
            for tool_name, tool_instance in self.tools.items():
                try:
                    # 关键修改 2: 直接调用 get_input_schema() 方法
                    # 这是修复工具参数无法被 LLM 感知的核心
                    input_schema = tool_instance.get_input_schema()

                    # 获取工具描述和参数
                    tool_info = Tool(
                        name=tool_name,
                        description=tool_instance.get_description(),
                        inputSchema=input_schema
                    )
                    tools.append(tool_info)
                    logger.debug(f"Added tool to list: {tool_name} with schema: {input_schema}")

                except Exception as e:
                    logger.error(f"Error processing tool {tool_name}: {e}")

            logger.info(f"Returning {len(tools)} tools")
            return tools

        @self.server.call_tool()
        async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
            """处理工具调用请求"""
            logger.info(f"Received call_tool request: {name} with arguments: {arguments}")

            try:
                if name not in self.tools:
                    error_msg = f"Tool '{name}' not found. Available tools: {list(self.tools.keys())}"
                    logger.error(error_msg)
                    return [TextContent(type="text", text=f"Error: {error_msg}")]

                tool_instance = self.tools[name]

                # 调用工具 (这里逻辑保持不变)
                result = await tool_instance.execute(arguments)

                logger.info(f"Tool {name} executed successfully")
                return [TextContent(type="text", text=str(result))]

            except Exception as e:
                error_msg = f"Error executing tool {name}: {str(e)}"
                logger.error(error_msg, exc_info=True)  # 添加 exc_info=True 方便调试
                return [TextContent(type="text", text=f"Error: {error_msg}")]

    async def run(self):
        """运行服务器"""
        logger.info("Server capabilities initialized. Starting stdio server...")

        # 使用 stdio_server 运行
        async with stdio_server() as (read_stream, write_stream):
            logger.info("Stdio streams established. Server is ready and waiting for client initialization.")

            try:
                await self.server.run(
                    read_stream,
                    write_stream,
                    InitializationOptions(
                        server_name="daily_tools_mcp",
                        server_version="1.0.0",
                        capabilities=self.server.get_capabilities(
                            notification_options=NotificationOptions(),
                            experimental_capabilities={}
                        )
                    )
                )
            except Exception as e:
                logger.error(f"Server run error: {e}")
                raise
            finally:
                logger.info("Server run loop has exited.")


async def main():
    """主函数"""
    logger.info("=" * 50)
    logger.info("Starting Daily Tools MCP Server...")
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")

    try:
        # 创建并运行服务器
        server = DailyToolsMCPServer()
        await server.run()

    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down...")
    except Exception as e:
        logger.error(f"Server error: {e}")
        raise
    finally:
        logger.info("Server shutdown complete.")
        sys.stdout.flush()
        sys.stderr.flush()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Server interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)