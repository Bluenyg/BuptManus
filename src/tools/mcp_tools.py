# src/tools/mcp_tools.py

import asyncio
import sys
import os
import logging
import threading
import subprocess
import time
from typing import List, Dict, Any, Optional

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class MCPClientManager:
    """MCP 客户端管理器 - 简化版本"""
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if not self._initialized:
            self.client_session: Optional[ClientSession] = None
            self.stdio_client_manager = None
            self.tools_cache: Optional[List[Dict[str, Any]]] = None
            self.server_process: Optional[subprocess.Popen] = None
            self._initialized = True

    def _get_server_path(self) -> str:
        """获取服务器路径"""
        current_dir = os.path.dirname(os.path.abspath(__file__))
        server_path = os.path.join(
            current_dir, "..", "daily_tools_mcp", "daily_tools_mcp_server.py"
        )
        server_path = os.path.normpath(server_path)

        if not os.path.exists(server_path):
            raise FileNotFoundError(f"MCP server not found at: {server_path}")

        return server_path

    async def _create_session_with_retry(self, max_attempts: int = 3) -> ClientSession:
        """创建会话，支持重试"""
        server_path = self._get_server_path()

        for attempt in range(max_attempts):
            logger.info(f"Attempt {attempt + 1}/{max_attempts} to create MCP session")

            try:
                # 准备环境
                env = os.environ.copy()
                env['PYTHONPATH'] = os.pathsep.join(sys.path)
                env['PYTHONUNBUFFERED'] = '1'
                env['PYTHONIOENCODING'] = 'utf-8'

                # 创建服务器参数
                server_params = StdioServerParameters(
                    command=sys.executable,
                    args=[server_path],
                    env=env
                )

                logger.info(f"Starting MCP server: {sys.executable} {server_path}")

                # 创建 stdio 客户端
                self.stdio_client_manager = stdio_client(server_params)
                read_stream, write_stream = await self.stdio_client_manager.__aenter__()

                # 等待一小段时间让服务器完全启动
                await asyncio.sleep(0.5)

                # 创建客户端会话
                session = ClientSession(read_stream, write_stream)

                logger.info("Initializing MCP client session...")

                # 尝试初始化，使用较短的超时时间但多次重试
                try:
                    await asyncio.wait_for(session.initialize(), timeout=10.0)
                    logger.info("MCP client session initialized successfully")
                    return session

                except asyncio.TimeoutError:
                    logger.warning(f"Session initialization timed out on attempt {attempt + 1}")
                    await self._cleanup_current_attempt()
                    if attempt < max_attempts - 1:
                        await asyncio.sleep(1)  # 等待后重试
                        continue
                    else:
                        raise

            except Exception as e:
                logger.error(f"Attempt {attempt + 1} failed: {e}")
                await self._cleanup_current_attempt()
                if attempt < max_attempts - 1:
                    await asyncio.sleep(1)
                    continue
                else:
                    raise

    async def _cleanup_current_attempt(self):
        """清理当前尝试的资源"""
        if self.stdio_client_manager:
            try:
                await self.stdio_client_manager.__aexit__(None, None, None)
            except Exception:
                pass
            self.stdio_client_manager = None

    async def get_session(self) -> ClientSession:
        """获取或创建 MCP 客户端会话"""
        if self.client_session is None:
            logger.info("Creating new MCP session")
            self.client_session = await self._create_session_with_retry()
        return self.client_session

    async def get_tools(self) -> List[Dict[str, Any]]:
        """获取工具列表"""
        if self.tools_cache is None:
            try:
                session = await self.get_session()
                logger.info("Listing tools from MCP server...")

                # 使用较短的超时时间
                response = await asyncio.wait_for(
                    session.list_tools(),
                    timeout=10.0
                )

                tools_list = [
                    {
                        "name": tool.name,
                        "description": tool.description,
                        "inputSchema": tool.inputSchema
                    }
                    for tool in response.tools
                ]

                self.tools_cache = tools_list
                logger.info(f"Successfully loaded {len(self.tools_cache)} MCP tools")

            except Exception as e:
                logger.exception("Failed to get MCP tools")
                self.tools_cache = []

        return self.tools_cache

    async def call_tool(self, tool_name: str, arguments: Dict[str, Any]) -> str:
        """调用工具"""
        try:
            session = await self.get_session()
            logger.info(f"Calling tool: {tool_name}")

            response = await asyncio.wait_for(
                session.call_tool(tool_name, arguments),
                timeout=20.0
            )

            if response.content and response.content[0].text:
                return response.content[0].text
            return ""

        except Exception as e:
            logger.exception(f"Failed to call MCP tool '{tool_name}'")
            return f"工具调用失败: {str(e)}"

    async def close(self):
        """关闭客户端会话"""
        logger.info("Closing MCP client...")

        if self.client_session:
            try:
                await self.client_session.close()
            except Exception as e:
                logger.error(f"Error closing session: {e}")
            finally:
                self.client_session = None

        if self.stdio_client_manager:
            try:
                await self.stdio_client_manager.__aexit__(None, None, None)
            except Exception as e:
                logger.error(f"Error exiting stdio manager: {e}")
            finally:
                self.stdio_client_manager = None

        self.tools_cache = None


# 全局客户端管理器
_client_manager = MCPClientManager()


class EventLoopManager:
    _loop: Optional[asyncio.AbstractEventLoop] = None
    _thread: Optional[threading.Thread] = None
    _lock = threading.Lock()

    @classmethod
    def get_loop(cls) -> asyncio.AbstractEventLoop:
        with cls._lock:
            if cls._loop is None or cls._loop.is_closed():
                cls._start_loop()
            return cls._loop

    @classmethod
    def _start_loop(cls):
        def run_loop():
            # 在 Windows 上使用 ProactorEventLoop
            if sys.platform == 'win32':
                asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

            cls._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(cls._loop)
            cls._loop.run_forever()

        cls._thread = threading.Thread(target=run_loop, daemon=True)
        cls._thread.start()

        # 等待事件循环启动
        max_wait = 50  # 最多等待 5 秒
        wait_count = 0
        while (cls._loop is None or not cls._loop.is_running()) and wait_count < max_wait:
            time.sleep(0.1)
            wait_count += 1

        if wait_count >= max_wait:
            raise RuntimeError("Failed to start event loop")

    @classmethod
    def run_coroutine(cls, coro, timeout=60):
        loop = cls.get_loop()
        future = asyncio.run_coroutine_threadsafe(coro, loop)
        return future.result(timeout=timeout)


# 同步包装器函数
def get_mcp_tools_sync() -> List[Dict[str, Any]]:
    """同步获取 MCP 工具列表"""
    try:
        logger.info("Getting MCP tools synchronously...")
        tools = EventLoopManager.run_coroutine(_client_manager.get_tools(), timeout=30)
        logger.info(f"Got {len(tools)} tools")
        return tools
    except Exception:
        logger.exception("Failed to get MCP tools synchronously")
        return []


def call_mcp_tool_sync(tool_name: str, arguments: Dict[str, Any]) -> str:
    """同步调用 MCP 工具"""
    try:
        return EventLoopManager.run_coroutine(
            _client_manager.call_tool(tool_name, arguments),
            timeout=30
        )
    except Exception:
        logger.exception(f"Failed to call MCP tool '{tool_name}' synchronously")
        return f"调用工具失败"


# 异步函数
async def get_mcp_tools() -> List[Dict[str, Any]]:
    return await _client_manager.get_tools()


async def call_mcp_tool(tool_name: str, arguments: Dict[str, Any]) -> str:
    return await _client_manager.call_tool(tool_name, arguments)


# 清理函数
def cleanup_mcp_client():
    logger.info("Cleaning up MCP client...")
    if _client_manager._initialized:
        try:
            EventLoopManager.run_coroutine(_client_manager.close(), timeout=5)
        except Exception:
            logger.exception("Error during MCP client cleanup")


import atexit

atexit.register(cleanup_mcp_client)
