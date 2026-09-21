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

        # 1. 连载模式 & 男频
        await page.get_by_text("连载模式").first.click()
        await asyncio.sleep(0.5)
        await page.get_by_text("男频").first.click()
        await asyncio.sleep(1)

        # 2. 点击阅读标签
        await page.click("#selectRow .select-view")
        await asyncio.sleep(1)

        # 3. 选择主分类: 都市日常
        tag_elem = page.locator(".category-modal").get_by_text("都市日常", exact=True).first
        await tag_elem.click()
        print("Clicked tag 都市日常", flush=True)
        await asyncio.sleep(1)

        # 4. 点击 确认
        confirm_btn = page.locator(".category-modal .arco-modal-footer button:has-text('确认')")
        await confirm_btn.click()
        print("Clicked 确认", flush=True)
        await asyncio.sleep(1)

        await page.screenshot(path='tests/after_tag_selected.png')
        print("Saved tests/after_tag_selected.png", flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
