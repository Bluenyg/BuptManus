# test_mcp_simple.py

import asyncio
import logging
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.abspath('.'))

from src.tools.mcp_tools import get_mcp_tools_sync, call_mcp_tool_sync

# 设置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def mcp_sync():
    """同步测试 MCP 连接"""
    print("=" * 50)
    print("Testing MCP connection (synchronous)...")

    try:
        # 测试获取工具列表
        print("Fetching tools...")
        tools = get_mcp_tools_sync()
        print(f"✓ Found {len(tools)} tools:")

        for tool in tools:
            print(f"  - {tool['name']}: {tool['description']}")

        # 如果有工具，测试调用
        if tools:
            tool_name = tools[0]['name']
            print(f"\n✓ Testing tool: {tool_name}")

            # 根据 track_logistics 工具调整参数
            if tool_name == "track_logistics":
                test_args = {"tracking_number": "TEST123"}
            else:
                test_args = {}

            result = call_mcp_tool_sync(tool_name, test_args)
            print(f"✓ Result: {result}")
            print("✓ MCP connection test PASSED!")
        else:
            print("⚠ No tools available to test")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


if __name__ == "__main__":
    success = mcp_sync()
    sys.exit(0 if success else 1)