# src/tools/browser.py

import asyncio
import logging
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Type
from langchain.tools import BaseTool
import atexit

# 外部库导入
from browser_use import AgentHistoryList, Browser, BrowserConfig
from browser_use import Agent as BrowserAgent

# --- 关键修改：移除顶层的 LLM 导入 ---
# from src.agents.llm import vl_llm  # <--- 已移除，这是解决循环导入的关键

from src.tools.decorators import create_logged_tool
from src.config import CHROME_INSTANCE_PATH

# 配置日志
logger = logging.getLogger(__name__)


# 全局浏览器实例管理 (代码保持不变)
class BrowserManager:
    def __init__(self):
        self._browser = None
        self._lock = asyncio.Lock()

    async def get_browser(self):
        """获取浏览器实例，使用单例模式"""
        if self._browser is None:
            async with self._lock:
                if self._browser is None:
                    try:
                        config_params = {
                            'headless': True,
                            'disable_security': True,
                            'additional_args': [
                                '--no-sandbox',
                                '--disable-dev-shm-usage',
                                '--disable-web-security',
                                '--disable-extensions',
                                '--disable-plugins',
                                '--disable-background-timer-throttling',
                                '--disable-backgrounding-occluded-windows',
                                '--disable-renderer-backgrounding',
                                '--window-size=1920,1080',
                            ]
                        }
                        if CHROME_INSTANCE_PATH:
                            config_params['chrome_instance_path'] = CHROME_INSTANCE_PATH

                        config = BrowserConfig(**config_params)
                        self._browser = Browser(config=config)
                        logger.info("Browser instance created successfully")
                    except Exception as e:
                        logger.error(f"Failed to create browser: {e}")
                        try:
                            logger.info("Trying with default browser configuration...")
                            self._browser = Browser()
                            logger.info("Browser created with default configuration")
                        except Exception as e2:
                            logger.error(f"Failed to create browser with default config: {e2}")
                            raise e2
        return self._browser

    async def cleanup(self):
        """清理浏览器资源"""
        if self._browser:
            try:
                await self._browser.close()
                self._browser = None
                logger.info("Browser cleaned up successfully")
            except Exception as e:
                logger.error(f"Error during browser cleanup: {e}")


# 全局浏览器管理器实例
browser_manager = BrowserManager()


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
    _llm: Optional[object] = None  # 用于缓存LLM实例

    def _get_llm(self):
        """在需要时才导入和获取LLM实例，并缓存它"""
        if self._llm is None:
            # --- 关键修改：将导入移到方法内部 ---
            from src.agents.llm import vl_llm
            self._llm = vl_llm
        return self._llm

    def _run(self, instruction: str) -> str:
        """Run the browser task synchronously."""
        try:
            try:
                # 检查是否已有事件循环
                asyncio.get_running_loop()
                # 如果有，避免使用 asyncio.run()，因为它会创建新循环
                # 这里使用一个简单的线程技巧来在同步代码中运行异步代码
                import threading
                import queue

                q = queue.Queue()

                def run_async_task():
                    try:
                        result = asyncio.run(self._arun(instruction))
                        q.put(result)
                    except Exception as e:
                        q.put(e)

                thread = threading.Thread(target=run_async_task)
                thread.start()
                thread.join(timeout=300)  # 5分钟超时

                if thread.is_alive():
                    return "Error: Browser task timed out in synchronous call."

                result = q.get()
                if isinstance(result, Exception):
                    raise result
                return result

            except RuntimeError:
                # 没有运行的事件循环，可以安全地创建新的
                return asyncio.run(self._arun(instruction))
        except Exception as e:
            logger.exception(f"Error in BrowserTool _run: {e}")
            return f"Error executing browser task: {str(e)}"

    async def _arun(self, instruction: str) -> str:
        """Run the browser task asynchronously."""
        try:
            logger.info(f"Starting browser task: {instruction}")

            # 获取浏览器实例
            browser = await browser_manager.get_browser()

            # --- 关键修改：使用 _get_llm() 方法获取 LLM ---
            vision_llm = self._get_llm()

            # 创建代理
            self._agent = BrowserAgent(
                task=instruction,
                llm=vision_llm,  # 使用延迟加载的 LLM
                browser=browser,
            )

            # 执行任务
            result = await self._agent.run()
            logger.info("Browser task completed successfully")

            # 处理结果
            if isinstance(result, AgentHistoryList):
                return result.final_result() if hasattr(result, 'final_result') and callable(
                    result.final_result) else str(result)
            else:
                return str(result)

        except asyncio.TimeoutError:
            error_msg = "Browser task timed out"
            logger.error(error_msg)
            return f"Error: {error_msg}"
        except Exception as e:
            error_msg = f"Error executing browser task: {str(e)}"
            logger.exception(error_msg)
            return error_msg
        finally:
            self._agent = None


# --- 关键修改：将工具的创建和注册封装在函数中 ---
def create_browser_tool() -> BrowserTool:
    """创建并返回 BrowserTool 的实例，应用装饰器。"""
    DecoratedBrowserTool = create_logged_tool(BrowserTool)
    return DecoratedBrowserTool()


# 在模块顶层，我们只导出这个创建函数。
# 在 __init__.py 中，我们将调用这个函数来获取实例。
# browser_tool = create_browser_tool_instance() # 不在这里调用

def cleanup_on_exit():
    """程序退出时清理浏览器资源"""
    try:
        # 尝试获取现有循环，如果没有则创建新的
        try:
            loop = asyncio.get_event_loop()
            if loop.is_closed():
                raise RuntimeError
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        loop.run_until_complete(browser_manager.cleanup())
        if not loop.is_running():  # 只有在它不是主循环时才关闭
            loop.close()

    except Exception as e:
        logger.error(f"Error during exit cleanup: {e}")


atexit.register(cleanup_on_exit)

# 测试代码 (保持不变)
if __name__ == "__main__":
    async def execute_browser_task():
        print("开始执行指令:", "在百度上查询今日北京天气")
        try:
            # 在测试时，我们直接调用创建函数
            browser_tool_instance = create_browser_tool_instance()
            result = await browser_tool_instance._arun("在百度上查询今日北京天气")
            print("任务执行完成，结果如下:")
            print(result)
        except Exception as e:
            print("执行错误:", e)
        finally:
            await browser_manager.cleanup()


    try:
        asyncio.run(execute_browser_task())
    except KeyboardInterrupt:
        print("任务被用户中断")
    except Exception as e:
        print(f"执行失败: {e}")

