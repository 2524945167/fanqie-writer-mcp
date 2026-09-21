import asyncio
import json
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

        # 1. Edit the first volume name to "这笔账先算清"
        await page.click(".tomato-edit")
        await asyncio.sleep(0.5)
        inp = await page.query_selector(".chapter-volume input")
        await inp.fill("这笔账先算清")
        await asyncio.sleep(0.5)
        # click the green checkmark
        check_icon = await page.query_selector(".byte-icon-check, .tomato-check, svg path[d*='check'], [class*='check']")
        # Or let's find the check button next to the input
        await page.evaluate("""() => {
            const icons = document.querySelectorAll('.chapter-volume svg, .chapter-volume i, .chapter-volume span');
            // find the checkmark element
            for (const el of icons) {
                if (el.innerHTML.includes('check') || el.className.includes('check') || el.className.includes('confirm')) {
                    el.click();
                    return;
                }
            }
            // or find the element with green color
            const check = document.querySelector('.chapter-volume .byte-icon-check, .chapter-volume .tomato-check');
            if (check) check.click();
        }""")
        await asyncio.sleep(1)
        await page.screenshot(path='tests/volume_renamed.png')
        print("Saved tests/volume_renamed.png", flush=True)

        # 2. Add second volume
        await page.click(".chapter-volume-footer-add-volume")
        await asyncio.sleep(1)
        await page.screenshot(path='tests/volume_added_second.png')
        print("Saved tests/volume_added_second.png", flush=True)

        # Inspect DOM
        vol_list = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.chapter-volume-list-item')).map(el => el.innerText);
        }""")
        print("Volume list items:", vol_list, flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
