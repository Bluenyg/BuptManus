#!/usr/bin/env python3
"""
工具管理脚本
用于查看、测试和管理工具
"""

import asyncio
import json
from tools.logistics_tool import LogisticsTool


# from tools.weather_tool import WeatherTool
# from tools.translator_tool import TranslatorTool


async def list_tools():
    """列出所有可用工具"""
    tools = [
        LogisticsTool(),
        # WeatherTool(),
        # TranslatorTool(),
    ]

    print("=== 可用工具列表 ===")
    for i, tool in enumerate(tools, 1):
        print(f"{i}. {tool.name}")
        print(f"   描述: {tool.description}")
        print(f"   必需参数: {tool.input_schema.get('required', [])}")
        print()


async def test_tool(tool_name: str, test_args: dict):
    """测试指定工具"""
    tools_map = {
        "track_logistics": LogisticsTool(),
        # "get_weather": WeatherTool(),
        # "translate_text": TranslatorTool(),
    }

    if tool_name not in tools_map:
        print(f"Unknown tool: {tool_name}")
        return

    tool = tools_map[tool_name]

    try:
        result = await tool.execute(test_args)
        print(f"=== {tool_name} 测试结果 ===")
        print(result)
    except Exception as e:
        print(f"测试失败: {e}")


async def main():
    """主函数"""
    import sys

    if len(sys.argv) < 2:
        print("用法:")
        print("  python manage_tools.py list                    # 列出所有工具")
        print("  python manage_tools.py test <tool_name>        # 测试工具")
        return

    command = sys.argv[1]

    if command == "list":
        await list_tools()
    elif command == "test":
        if len(sys.argv) < 3:
            print("请指定要测试的工具名称")
            return

        tool_name = sys.argv[2]

        # 这里可以添加不同工具的测试参数
        test_args = {}
        if tool_name == "track_logistics":
            test_args = {
                "com": "shunfeng",
                "num": "SF3190621662050",
                "phone": "18138199852"
            }
        # elif tool_name == "get_weather":
        #     test_args = {"city": "北京", "days": 3}
        # elif tool_name == "translate_text":
        #     test_args = {"text": "Hello, world!", "target_language": "zh"}

        await test_tool(tool_name, test_args)
    else:
        print(f"未知命令: {command}")


if __name__ == "__main__":
    asyncio.run(main())
