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

        # Click 新建分卷
        await page.click(".chapter-volume-footer-add-volume")
        await asyncio.sleep(0.5)
        inp = await page.query_selector(".chapter-volume input")
        if inp:
            await inp.fill("房间之外")
            await asyncio.sleep(0.3)
            await page.click(".tomato-confirm.green")
            await asyncio.sleep(0.5)
            print("Confirmed volume 2: 房间之外", flush=True)

        confirm_btn = await page.query_selector(".chapter-volume-footer-buttons button.byte-btn-primary")
        if confirm_btn:
            await confirm_btn.click()
            print("Clicked 确定!", flush=True)
            await asyncio.sleep(2)

        await page.screenshot(path='tests/vol2_saved.png')
        print("Saved tests/vol2_saved.png", flush=True)

        err = await page.evaluate("() => { const el = document.querySelector('.arco-message-error, .arco-message'); return el ? el.innerText : ''; }")
        print("Any error message:", err, flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
