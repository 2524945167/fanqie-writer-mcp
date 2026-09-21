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
        ack_btn = await page.query_selector("button:has-text('知道了')")
        if ack_btn:
            await ack_btn.click()
            await asyncio.sleep(1)

        # 滚动到底部
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
        await asyncio.sleep(1)
        await page.screenshot(path='tests/create_book_bottom.png')

        # 查找底部按钮
        btns = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button')).map(b => ({
                text: b.innerText.trim(),
                className: b.className
            }));
        }""")
        print("Bottom buttons:", btns)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
