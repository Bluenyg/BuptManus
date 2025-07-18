import asyncio
import logging
from pydantic import BaseModel, Field
from typing import Optional, ClassVar, Type
from langchain.tools import BaseTool
from browser_use import AgentHistoryList, Browser, BrowserConfig
from browser_use import Agent as BrowserAgent
from src.agents.llm import vl_llm
from src.tools.decorators import create_logged_tool
from src.config import CHROME_INSTANCE_PATH

# 配置日志
logger = logging.getLogger(__name__)


# 全局浏览器实例管理
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
                        # 修正 BrowserConfig 参数
                        config_params = {
                            'headless': True,  # 无头模式提高稳定性
                            'disable_security': True,
                        }

                        # 只有当路径存在时才添加
                        if CHROME_INSTANCE_PATH:
                            config_params['chrome_instance_path'] = CHROME_INSTANCE_PATH

                        # 添加浏览器启动参数
                        config_params['additional_args'] = [
                            '--no-sandbox',
                            '--disable-dev-shm-usage',
                            '--disable-web-security',
                            '--disable-extensions',
                            '--disable-plugins',
                            '--disable-background-timer-throttling',
                            '--disable-backgrounding-occluded-windows',
                            '--disable-renderer-backgrounding',
                            '--window-size=1920,1080',  # 通过启动参数设置窗口大小
                        ]

                        config = BrowserConfig(**config_params)
                        self._browser = Browser(config=config)
                        logger.info("Browser instance created successfully")
                    except Exception as e:
                        logger.error(f"Failed to create browser: {e}")
                        # 如果配置失败，尝试使用默认配置
                        try:
                            logger.info("Trying with default browser configuration...")
                            self._browser = Browser()  # 使用默认配置
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


# 全局浏览器管理器
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

    def _run(self, instruction: str) -> str:
        """Run the browser task synchronously."""
        try:
            # 检查是否已经在事件循环中
            try:
                loop = asyncio.get_running_loop()
                # 如果已经在事件循环中，使用线程池执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, self._arun(instruction))
                    return future.result(timeout=300)  # 5分钟超时
            except RuntimeError:
                # 没有运行的事件循环，可以安全地创建新的
                return asyncio.run(self._arun(instruction))
        except Exception as e:
            logger.exception(f"Error in _run: {e}")
            return f"Error executing browser task: {str(e)}"

    async def _arun(self, instruction: str) -> str:
        """Run the browser task asynchronously."""
        try:
            logger.info(f"Starting browser task: {instruction}")

            # 获取浏览器实例
            browser = await browser_manager.get_browser()

            # 创建代理
            self._agent = BrowserAgent(
                task=instruction,
                llm=vl_llm,
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
            # 清理代理（但不关闭浏览器，因为它是共享的）
            self._agent = None


# 创建工具实例
BrowserTool = create_logged_tool(BrowserTool)
browser_tool = BrowserTool()

# 程序退出时清理资源
import atexit


def cleanup_on_exit():
    """程序退出时清理浏览器资源"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(browser_manager.cleanup())
        loop.close()
    except Exception as e:
        logger.error(f"Error during exit cleanup: {e}")


atexit.register(cleanup_on_exit)

# 测试代码
if __name__ == "__main__":
    # 模拟指令
    instruction = "在百度上查询今日北京天气"


    async def execute_browser_task():
        print("开始执行指令:", instruction)
        try:
            # 创建 BrowserTool 对象
            browser_tool_instance = BrowserTool()
            # 异步执行任务
            result = await browser_tool_instance._arun(instruction)
            print("任务执行完成，结果如下:")
            print(result)
        except Exception as e:
            print("执行错误:", e)
        finally:
            # 清理资源
            await browser_manager.cleanup()


    # 异步运行任务
    try:
        asyncio.run(execute_browser_task())
    except KeyboardInterrupt:
        print("任务被用户中断")
    except Exception as e:
        print(f"执行失败: {e}")
