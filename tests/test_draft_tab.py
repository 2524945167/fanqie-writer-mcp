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

        # Inspect all tabs
        tabs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.arco-tabs-header-cell, [role=\"tab\"], .tab, [class*=\"tab\"]')).map(t => ({
                text: t.innerText,
                className: t.className,
                html: t.outerHTML
            }));
        }""")
        print("Found tabs:", tabs)

        # Click the actual draft tab
        draft_tab = page.locator(".arco-tabs-header-cell").get_by_text("草稿箱")
        if await draft_tab.count() > 0:
            await draft_tab.first.click()
            print("Clicked .arco-tabs-header-cell 草稿箱", flush=True)
        else:
            await page.get_by_text("草稿箱").first.click()
            print("Clicked get_by_text 草稿箱", flush=True)

        await asyncio.sleep(2)
        await page.screenshot(path='tests/draft_tab_active.png')
        print("Saved tests/draft_tab_active.png", flush=True)

        items = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('tr, .arco-table-tr, .chapter-list-item, .item')).map(r => r.innerText.trim()).filter(Boolean);
        }""")
        print("Draft table rows:", items)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
