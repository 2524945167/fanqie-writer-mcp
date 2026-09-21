import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

BOOK_ID = "7687873685029407806"

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        url = f"https://fanqienovel.com/main/writer/chapter-manage/{BOOK_ID}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # Click 草稿箱 tab
        draft_tab = await page.query_selector("div:has-text('草稿箱'), span:has-text('草稿箱')")
        if draft_tab:
            await draft_tab.click()
            print("Clicked 草稿箱 tab", flush=True)
            await asyncio.sleep(2)
            await page.screenshot(path='tests/draft_box.png')
            print("Saved tests/draft_box.png", flush=True)

            text = await page.evaluate("() => document.body.innerText")
            for line in text.splitlines():
                if "第" in line or "草稿" in line:
                    print("  Line:", line.strip())
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
