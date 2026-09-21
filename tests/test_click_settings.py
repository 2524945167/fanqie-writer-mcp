import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/book-manage', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        btn = await page.query_selector("button:has-text('作品设置')")
        if btn:
            await btn.click()
            await asyncio.sleep(2)
            print("Clicked 作品设置, new URL:", page.url)
            await page.screenshot(path='tests/book_settings_preview.png')
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
