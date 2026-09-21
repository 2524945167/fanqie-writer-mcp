import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def inspect():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/book-manage', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        cards = await page.query_selector_all("div:has(button:has-text('作品设置'))")
        print("Cards matching div:has(button:has-text('作品设置')):", len(cards))
        for idx, c in enumerate(cards):
            html = await c.evaluate("el => el.outerHTML")
            print(f"--- Card {idx} ---")
            print(html[:1000])
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(inspect())
