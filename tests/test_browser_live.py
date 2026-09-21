"""
测试 Playwright 浏览器启动与反检测执行
"""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.browser import BrowserManager

async def test_browser():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto("about:blank")
        is_webdriver = await page.evaluate("navigator.webdriver")
        plugins_len = await page.evaluate("navigator.plugins.length")
        languages = await page.evaluate("navigator.languages")
        print(f"[TEST] navigator.webdriver: {is_webdriver} (应为 None/undefined)")
        print(f"[TEST] navigator.plugins.length: {plugins_len} (应大于 0)")
        print(f"[TEST] navigator.languages: {languages}")
        assert is_webdriver is None, "Anti-detection failed: webdriver is not None"
        assert plugins_len > 0, "Anti-detection failed: plugins empty"
        print("[TEST] 浏览器反检测环境验证完全通过！")
    finally:
        await page.close()
        await bm.close()

if __name__ == "__main__":
    asyncio.run(test_browser())
