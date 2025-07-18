import asyncio
import json
from typing import Any, Dict, List, Callable
from mcp.server import Server, NotificationOptions
from mcp.server.models import InitializationOptions
import mcp.server.stdio
import mcp.types as types

# 导入工具模块
from tools.logistics_tool import LogisticsTool


# 未来可以添加更多工具
# from tools.weather_tool import WeatherTool
# from tools.calendar_tool import CalendarTool
# from tools.translator_tool import TranslatorTool


class DailyToolsServer:
    """日常生活工具集 MCP 服务器"""

    def __init__(self):
        self.server = Server("daily-tools")
        self.tools: Dict[str, Any] = {}
        self._register_tools()
        self._setup_handlers()

    def _register_tools(self):
        """注册所有工具"""
        # 注册物流跟踪工具
        logistics_tool = LogisticsTool()
        self.tools[logistics_tool.name] = logistics_tool

        # 未来在这里注册更多工具
        # weather_tool = WeatherTool()
        # self.tools[weather_tool.name] = weather_tool

        print(f"Registered {len(self.tools)} tools: {list(self.tools.keys())}")

    def _setup_handlers(self):
        """设置MCP处理器"""

        @self.server.list_tools()
        async def handle_list_tools() -> List[types.Tool]:
            """列出所有可用工具"""
            tool_list = []
            for tool in self.tools.values():
                tool_list.append(types.Tool(
                    name=tool.name,
                    description=tool.description,
                    inputSchema=tool.input_schema
                ))
            return tool_list

        @self.server.call_tool()
        async def handle_call_tool(
                name: str, arguments: dict[str, Any] | None
        ) -> List[types.TextContent]:
            """处理工具调用请求"""
            if name not in self.tools:
                raise ValueError(f"Unknown tool: {name}")

            if not arguments:
                raise ValueError("Missing arguments")

            try:
                tool = self.tools[name]
                result = await tool.execute(arguments)
                return [types.TextContent(type="text", text=result)]
            except Exception as e:
                return [types.TextContent(
                    type="text",
                    text=f"Error executing tool '{name}': {str(e)}"
                )]

    async def run(self):
        """启动服务器"""
        async with mcp.server.stdio.stdio_server() as (read_stream, write_stream):
            await self.server.run(
                read_stream,
                write_stream,
                InitializationOptions(
                    server_name="daily-tools",
                    server_version="0.1.0",
                    capabilities=self.server.get_capabilities(
                        notification_options=NotificationOptions(),
                        experimental_capabilities={},
                    ),
                ),
            )


async def main():
    """启动日常工具 MCP 服务器"""
    server = DailyToolsServer()
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
