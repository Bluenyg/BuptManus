import asyncio
import platform
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Type
from langchain.tools import BaseTool
from browser_use import AgentHistoryList, Browser, BrowserConfig
from browser_use import Agent as BrowserAgent
from src.agents.llm import vl_llm
from src.tools.decorators import create_logged_tool
from src.config import CHROME_INSTANCE_PATH

# 在模块开始时设置事件循环策略
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

expected_browser = None

# Use Chrome instance if specified
if CHROME_INSTANCE_PATH:
    expected_browser = Browser(
        config=BrowserConfig(chrome_instance_path=CHROME_INSTANCE_PATH)
    )


class BrowserUseInput(BaseModel):
    """Input for BrowserTool."""
    instruction: str = Field(..., description="The instruction to use browser")


class BrowserTool(BaseTool):
    name: ClassVar[str] = "browser"
    args_schema: Type[BaseModel] = BrowserUseInput
    description: ClassVar[str] = (
        "Use this tool to interact with web browsers. Input should be a natural language description of what you want to do with the browser, such as 'Go to google.com and search for browser-use', or 'Navigate to Reddit and find the top post about AI'."
    )

    _agent: Optional[BrowserAgent] = None

    def _run(self, instruction: str) -> str:
        """Run the browser task synchronously."""
        try:
            # 获取当前事件循环，如果没有则创建新的
            try:
                loop = asyncio.get_event_loop()
                if loop.is_closed():
                    raise RuntimeError("Event loop is closed")
            except RuntimeError:
                # 没有事件循环或循环已关闭，创建新的
                if platform.system() == 'Windows':
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 创建 BrowserAgent
            self._agent = BrowserAgent(
                task=instruction,
                llm=vl_llm,
                browser=expected_browser,
            )

            # 如果当前在异步上下文中，使用 run_until_complete
            if loop.is_running():
                # 如果循环正在运行，创建新线程运行异步任务
                import concurrent.futures
                import threading

                def run_in_thread():
                    new_loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(new_loop)
                    try:
                        return new_loop.run_until_complete(self._async_run(instruction))
                    finally:
                        new_loop.close()

                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(run_in_thread)
                    result = future.result()
            else:
                # 循环未运行，直接使用
                result = loop.run_until_complete(self._async_run(instruction))

            return self._format_result(result)

        except Exception as e:
            return f"Error executing browser task: {str(e)}"

    async def _async_run(self, instruction: str) -> str:
        """实际的异步执行逻辑"""
        self._agent = BrowserAgent(
            task=instruction,
            llm=vl_llm,
            browser=expected_browser,
        )
        result = await self._agent.run()
        return result

    def _format_result(self, result) -> str:
        """格式化结果"""
        if isinstance(result, AgentHistoryList):
            return result.final_result
        return str(result)

    async def _arun(self, instruction: str) -> str:
        """Run the browser task asynchronously."""
        try:
            result = await self._async_run(instruction)
            return self._format_result(result)
        except Exception as e:
            return f"Error executing browser task: {str(e)}"


BrowserTool = create_logged_tool(BrowserTool)
browser_tool = BrowserTool()
