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
        
        guide = await page.query_selector("button:has-text('我知道了')")
        if guide:
            await guide.click()
            await asyncio.sleep(0.5)

        await page.click("button:has-text('编辑分卷')")
        await asyncio.sleep(1)

        # Let's test clicking the edit icon on the first volume
        edit_icon = await page.query_selector(".tomato-edit")
        if edit_icon:
            await edit_icon.click()
            print("Clicked .tomato-edit", flush=True)
            await asyncio.sleep(1)
            await page.screenshot(path='tests/volume_edit_first.png')

        # Let's test clicking 新建分卷
        add_btn = await page.query_selector(".chapter-volume-footer-add-volume")
        if add_btn:
            await add_btn.click()
            print("Clicked 新建分卷", flush=True)
            await asyncio.sleep(1)
            await page.screenshot(path='tests/volume_add_new.png')

        inputs = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.chapter-volume input')).map(inp => ({
                placeholder: inp.placeholder,
                value: inp.value,
                className: inp.className,
                html: inp.outerHTML
            }));
        }""")
        print("Inputs in volume modal:", inputs, flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
