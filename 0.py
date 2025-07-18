# test_browser_env.py
import asyncio
import logging
from playwright.async_api import async_playwright

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def playwright():
    """测试 Playwright 环境"""
    try:
        async with async_playwright() as p:
            logger.info("Playwright started successfully")

            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-dev-shm-usage']
            )
            logger.info("Browser launched successfully")

            page = await browser.new_page()
            logger.info("Page created successfully")

            await page.goto('https://www.baidu.com')
            title = await page.title()
            logger.info(f"Page title: {title}")

            await browser.close()
            logger.info("Browser closed successfully")

            return True
    except Exception as e:
        logger.error(f"Test failed: {e}")
        return False


if __name__ == "__main__":
    success = asyncio.run(playwright())
    if success:
        print("✅ Playwright environment is working correctly")
    else:
        print("❌ Playwright environment has issues")
