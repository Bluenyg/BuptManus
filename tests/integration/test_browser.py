# test_playwright.py
import asyncio
from playwright.async_api import async_playwright


async def main():
    print("--- 开始运行最小可验证脚本 ---")
    try:
        async with async_playwright() as p:
            print("1. Playwright 引擎已启动...")

            # 尝试以无头模式启动 (在服务器上或自动化时常用)
            print("2. 正在尝试以无头模式 (headless) 启动浏览器...")
            browser = await p.chromium.launch(headless=True)
            print("   ✅ 无头浏览器启动成功!")

            page = await browser.new_page()
            print("3. 新页面已创建。")

            await page.goto("https://www.baidu.com")
            print("4. 已导航至百度。")

            title = await page.title()
            print(f"5. 获取到页面标题: '{title}'")

            await browser.close()
            print("6. 浏览器已成功关闭。")

    except Exception as e:
        print(f"\n❌ 在脚本执行过程中发生严重错误: {e}")
        import traceback
        traceback.print_exc()

    print("\n--- 脚本执行完毕 ---")


if __name__ == "__main__":
    asyncio.run(main())