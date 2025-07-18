import asyncio
import json
import subprocess
import sys
from typing import Dict, Any, List, Optional
from langchain_core.tools import BaseTool
from langchain_core.pydantic_v1 import BaseModel, Field
import logging
import os

logger = logging.getLogger(__name__)


class MCPClient:
    """MCP 客户端，用于连接 MCP 服务器"""

    def __init__(self, server_script_path: str):
        self.server_script_path = server_script_path
        self.process = None
        self.request_id = 0
        self.tools = {}
        self._loop = None

    async def start(self):
        """启动 MCP 服务器进程"""
        try:
            self.process = await asyncio.create_subprocess_exec(
                sys.executable, self.server_script_path,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 初始化连接
            await self._initialize()
            # 获取工具列表
            await self._load_tools()

            logger.info(f"MCP Client connected successfully. Available tools: {list(self.tools.keys())}")

        except Exception as e:
            logger.error(f"Failed to start MCP server: {e}")
            raise

    async def _send_request(self, method: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """发送请求到 MCP 服务器"""
        self.request_id += 1

        request = {
            "jsonrpc": "2.0",
            "id": self.request_id,
            "method": method
        }

        if params:
            request["params"] = params

        # 发送请求
        request_json = json.dumps(request) + '\n'
        self.process.stdin.write(request_json.encode())
        await self.process.stdin.drain()

        # 读取响应
        response_line = await self.process.stdout.readline()
        if not response_line:
            raise Exception("No response from MCP server")

        response = json.loads(response_line.decode())

        if "error" in response:
            raise Exception(f"MCP Error: {response['error']}")

        return response.get("result", {})

    async def _initialize(self):
        """初始化 MCP 连接"""
        params = {
            "protocolVersion": "2024-11-05",
            "capabilities": {
                "tools": {}
            },
            "clientInfo": {
                "name": "langgraph-agent",
                "version": "1.0.0"
            }
        }

        result = await self._send_request("initialize", params)
        logger.info("MCP connection initialized")
        return result

    async def _load_tools(self):
        """加载可用工具列表"""
        result = await self._send_request("tools/list")

        for tool in result.get("tools", []):
            self.tools[tool["name"]] = tool

        logger.info(f"Loaded {len(self.tools)} tools")

    async def call_tool(self, name: str, arguments: Dict[str, Any]) -> Any:
        """调用工具"""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found. Available tools: {list(self.tools.keys())}")

        params = {
            "name": name,
            "arguments": arguments
        }

        result = await self._send_request("tools/call", params)
        return result.get("content", [])

    def get_tool_schema(self, name: str) -> Dict[str, Any]:
        """获取工具的参数 schema"""
        if name not in self.tools:
            raise ValueError(f"Tool '{name}' not found")

        return self.tools[name]

    def list_tools(self) -> List[str]:
        """列出所有可用工具"""
        return list(self.tools.keys())

    async def close(self):
        """关闭连接"""
        if self.process:
            self.process.terminate()
            await self.process.wait()


class MCPTool(BaseTool):
    """将 MCP 工具封装为 LangChain 工具"""

    name: str
    description: str
    mcp_client: MCPClient
    tool_schema: Dict[str, Any]

    def __init__(self, name: str, mcp_client: MCPClient, tool_schema: Dict[str, Any]):
        self.name = name
        self.mcp_client = mcp_client
        self.tool_schema = tool_schema
        self.description = tool_schema.get("description", f"MCP tool: {name}")

        # 创建动态参数模型
        self.args_schema = self._create_args_schema()

        super().__init__()

    def _create_args_schema(self):
        """根据 MCP 工具 schema 创建参数验证模型"""
        properties = self.tool_schema.get("inputSchema", {}).get("properties", {})
        required = self.tool_schema.get("inputSchema", {}).get("required", [])

        fields = {}
        for prop_name, prop_schema in properties.items():
            field_type = str  # 简化处理，都当作字符串
            default = ... if prop_name in required else None
            fields[prop_name] = (field_type, Field(default=default, description=prop_schema.get("description", "")))

        return type(f"{self.name}Args", (BaseModel,), fields)

    async def _arun(self, **kwargs) -> str:
        """异步运行工具"""
        try:
            result = await self.mcp_client.call_tool(self.name, kwargs)
            return json.dumps(result, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error(f"Error calling MCP tool {self.name}: {e}")
            return f"Error: {str(e)}"

    def _run(self, **kwargs) -> str:
        """同步运行工具"""
        # 获取当前事件循环
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(self._arun(**kwargs))


# 全局 MCP 客户端实例
_mcp_client = None


def get_mcp_client() -> MCPClient:
    """获取全局 MCP 客户端实例"""
    global _mcp_client
    if _mcp_client is None:
        # 获取 MCP 服务器脚本路径
        server_path = os.path.join(os.path.dirname(__file__), "..", "..", "daily_tools_mcp_server.py")
        _mcp_client = MCPClient(server_path)

        # 在新的事件循环中启动客户端
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(_mcp_client.start())

    return _mcp_client


def get_mcp_tools() -> List[MCPTool]:
    """获取所有 MCP 工具"""
    client = get_mcp_client()
    tools = []

    for tool_name in client.list_tools():
        tool_schema = client.get_tool_schema(tool_name)
        mcp_tool = MCPTool(tool_name, client, tool_schema)
        tools.append(mcp_tool)

    return tools
