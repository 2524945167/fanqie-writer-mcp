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
        manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{BOOK_ID}"
        await page.goto(manage_url, wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Click 设置
        set_btn = await page.query_selector("button:has-text('设置'), [class*='setting']")
        if set_btn:
            await set_btn.click()
            await asyncio.sleep(1)
            await page.screenshot(path='tests/setting_menu.png')
            print("Saved tests/setting_menu.png", flush=True)

            opts = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.arco-dropdown, .arco-dropdown-menu, li, [role=\"menuitem\"]')).map(el => el.innerText.trim()).filter(Boolean);
            }""")
            print("Setting options:", opts)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
