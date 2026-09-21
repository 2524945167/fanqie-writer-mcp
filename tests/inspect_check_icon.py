import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/chapter-manage/7687873685029407806', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        guide = await page.query_selector("button:has-text('我知道了')")
        if guide:
            await guide.click()
            await asyncio.sleep(0.5)
        await page.click("button:has-text('编辑分卷')")
        await asyncio.sleep(1)
        await page.click(".chapter-volume-footer-add-volume")
        await asyncio.sleep(0.5)
        html = await page.evaluate("() => document.querySelector('.chapter-volume-list-item').outerHTML")
        print('Row HTML:', html)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
