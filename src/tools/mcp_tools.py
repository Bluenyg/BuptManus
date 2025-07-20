# src/tools/mcp_tools.py

import asyncio
import subprocess
import sys
import os
import logging
import json
from typing import List, Dict, Any, Optional
import time
import threading

# MCP 客户端导入
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logger = logging.getLogger(__name__)


class MCPTools:
    def __init__(self):
        self.available_tools: List[Dict[str, Any]] = []
        self.server_params: Optional[StdioServerParameters] = None
        self.is_initialized = False

    async def connect_to_mcp_server(self, max_retries: int = 3, retry_delay: float = 1.0) -> bool:
        """初始化 MCP 服务器连接参数"""
        logger.info("Initializing MCP server connection parameters...")

        for attempt in range(max_retries):
            try:
                # 确定服务器脚本的绝对路径
                script_dir = os.path.dirname(os.path.abspath(__file__))
                project_root = os.path.join(script_dir, '..', '..')
                server_script = os.path.join(project_root, 'src', 'daily_tools_mcp', 'daily_tools_mcp_server.py')

                if not os.path.exists(server_script):
                    logger.error(f"Server script not found at: {server_script}")
                    return False

                logger.info(f"Server script found at: {server_script}")

                # 创建并保存服务器参数
                self.server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[server_script],
                    env=None
                )

                # 测试连接并获取工具列表
                success = await self._test_connection_and_get_tools()
                if success:
                    self.is_initialized = True
                    logger.info("MCP server connection parameters initialized successfully")
                    return True

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed to initialize MCP connection: {e}")
                if attempt < max_retries - 1:
                    logger.info(f"Retrying in {retry_delay} seconds...")
                    await asyncio.sleep(retry_delay)
                else:
                    logger.error("All initialization attempts failed")

        return False

    async def _test_connection_and_get_tools(self) -> bool:
        """测试连接并获取工具列表"""
        try:
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    logger.info("Testing connection to MCP server")

                    # 初始化连接
                    init_result = await session.initialize()
                    logger.info(f"Server initialization result: {init_result}")

                    # 获取可用工具列表
                    tools_result = await session.list_tools()
                    logger.info(f"Retrieved {len(tools_result.tools)} tools from server")

                    # 存储工具信息
                    self.available_tools = []
                    for tool in tools_result.tools:
                        tool_info = {
                            'name': tool.name,
                            'description': tool.description,
                            'input_schema': tool.inputSchema
                        }
                        self.available_tools.append(tool_info)
                        logger.info(f"Available tool: {tool.name} - {tool.description}")

                    return True

        except Exception as e:
            logger.error(f"Failed to test connection: {e}")
            return False

    async def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用 MCP 工具 - 每次调用都创建新连接"""
        if not self.is_initialized or not self.server_params:
            logger.error("MCP not initialized. Please connect first.")
            return "Error: No MCP connection available"

        try:
            logger.info(f"Calling MCP tool: {tool_name} with arguments: {arguments}")

            # 每次调用都创建新的连接
            async with stdio_client(self.server_params) as (read, write):
                async with ClientSession(read, write) as session:
                    # 初始化会话
                    await session.initialize()

                    # 调用工具
                    result = await session.call_tool(tool_name, arguments)

                    # 处理结果
                    if result.isError:
                        error_msg = "Tool execution error"
                        if result.content:
                            error_msg = str(result.content[0].text if result.content[0].text else error_msg)
                        logger.error(f"Tool {tool_name} returned error: {error_msg}")
                        return f"Error: {error_msg}"

                    # 成功结果
                    if result.content and len(result.content) > 0:
                        response = str(result.content[0].text)
                        logger.info(f"Tool {tool_name} executed successfully")
                        return response
                    else:
                        logger.warning(f"Tool {tool_name} returned empty result")
                        return "Tool executed but returned no content"

        except Exception as e:
            error_msg = f"Error calling tool {tool_name}: {e}"
            logger.exception(error_msg)
            return f"Error: {error_msg}"

    def get_available_tools(self) -> List[Dict[str, Any]]:
        """获取可用工具列表"""
        return self.available_tools

    async def close_connection(self):
        """清理连接信息"""
        self.server_params = None
        self.is_initialized = False
        self.available_tools = []
        logger.info("MCP connection info cleared")


def _run_async_safely(coro):
    """安全地运行异步协程"""
    try:
        # 检查是否已经在事件循环中
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # 如果已经在事件循环中，创建一个 Task
            return asyncio.create_task(coro)
        else:
            # 如果不在事件循环中，创建新的事件循环
            return asyncio.run(coro)
    except RuntimeError:
        # 没有运行的事件循环，创建新的
        return asyncio.run(coro)


# 全局 MCP 工具实例
_mcp_tools_instance = None
_instance_lock = threading.Lock()


def get_mcp_tools_sync():
    """获取全局 MCP 工具实例（单例模式）"""
    global _mcp_tools_instance

    if _mcp_tools_instance is None:
        with _instance_lock:
            if _mcp_tools_instance is None:
                _mcp_tools_instance = MCPTools()

                # 在后台线程中初始化连接
                def init_in_background():
                    try:
                        asyncio.run(_mcp_tools_instance.connect_to_mcp_server())
                    except Exception as e:
                        logger.error(f"Failed to initialize MCP in background: {e}")

                init_thread = threading.Thread(target=init_in_background, daemon=True)
                init_thread.start()

                # 给初始化一些时间
                time.sleep(2)

    return _mcp_tools_instance


async def call_mcp_tool_async(tool_name: str, arguments: Dict[str, Any]) -> str:
    """异步调用 MCP 工具"""
    mcp_tools = get_mcp_tools_instance()

    # 如果未初始化，尝试连接
    if not mcp_tools.is_initialized:
        logger.info("MCP not initialized, attempting to connect...")
        success = await mcp_tools.connect_to_mcp_server()
        if not success:
            return "Error: Failed to connect to MCP server"

    return await mcp_tools.call_mcp_tool(tool_name, arguments)


def call_mcp_tool_sync(tool_name: str, arguments: Dict[str, Any]) -> str:
    """同步调用 MCP 工具"""
    try:
        # 检查是否在事件循环中
        loop = asyncio.get_running_loop()
        if loop.is_running():
            # 在事件循环中，需要创建任务
            task = asyncio.create_task(call_mcp_tool_async(tool_name, arguments))
            # 注意：这里不能直接 await，因为我们在同步函数中
            # 实际上这种情况下应该使用异步版本
            logger.warning("call_mcp_tool_sync called from within event loop, consider using async version")
            return "Error: Cannot run sync version from within event loop"
    except RuntimeError:
        # 没有运行的事件循环，可以创建新的
        return asyncio.run(call_mcp_tool_async(tool_name, arguments))


def get_available_mcp_tools() -> List[Dict[str, Any]]:
    """获取可用的 MCP 工具列表"""
    mcp_tools = get_mcp_tools_instance()
    return mcp_tools.get_available_tools()


# 为了兼容性，保留一些旧的函数名
def get_mcp_tools() -> List[Dict[str, Any]]:
    """获取 MCP 工具列表（兼容性函数）"""
    return get_available_mcp_tools()


def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    """调用 MCP 工具（兼容性函数）"""
    return call_mcp_tool_sync(tool_name, arguments)
