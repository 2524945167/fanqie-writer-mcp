import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        url = 'https://fanqienovel.com/main/writer/7661632549390666776/publish/'
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)
        print("Publish page URL:", page.url)
        await page.screenshot(path='tests/publish_page_preview.png')
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
