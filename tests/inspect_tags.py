import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/create?enter_from=book_manage', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        ack = await page.query_selector("button:has-text('知道了')")
        if ack:
            await ack.click()
            await asyncio.sleep(1)

        # 1. 点击 连载模式
        await page.get_by_text("连载模式").first.click()
        print("Clicked 连载模式", flush=True)
        await asyncio.sleep(1)

        # 2. 点击 男频
        await page.get_by_text("男频").first.click()
        print("Clicked 男频", flush=True)
        await asyncio.sleep(1)

        await page.screenshot(path='tests/mode_and_gender_selected.png')
        print("Saved tests/mode_and_gender_selected.png", flush=True)

        # 3. 点击阅读标签
        tag_box = await page.query_selector(".select-view")
        if tag_box:
            await tag_box.click()
            await asyncio.sleep(1)
            await page.screenshot(path='tests/tag_options_open.png')
            opts = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.arco-select-option, [role=\"option\"], .select-popup span, .select-option, .muye-select-option, li')).map(el => el.innerText.trim()).filter(Boolean);
            }""")
            print("Tag options count:", len(opts), opts[:30], flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
