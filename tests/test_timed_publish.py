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
        url = f"https://fanqienovel.com/main/writer/{BOOK_ID}/publish/?enter_from=newchapter"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # Click 下一步
        next_btn = await page.query_selector("button:has-text('下一步')")
        if next_btn:
            await next_btn.click()
            await asyncio.sleep(1.5)

            typo_btn = await page.query_selector(".arco-modal button:has-text('提交'), button:has-text('提交')")
            if typo_btn:
                await typo_btn.click()
                await asyncio.sleep(1.5)

            check_btn = await page.query_selector("button:has-text('仅基础检测'), button:has-text('全面检测')")
            if check_btn:
                await check_btn.click()
                await asyncio.sleep(1.5)

            # AI: 否
            ai_no = await page.query_selector(".arco-modal label:has-text('否'), label:has-text('否')")
            if ai_no:
                await ai_no.click()
                await asyncio.sleep(0.5)

            # Toggle 定时发布
            switch_btn = await page.query_selector(".arco-modal button[role='switch'], .arco-modal .arco-switch")
            if switch_btn:
                await switch_btn.click()
                print("Toggled 定时发布", flush=True)
                await asyncio.sleep(1)

                await page.screenshot(path='tests/timed_modal_open.png')
                print("Saved tests/timed_modal_open.png", flush=True)

                # Inspect modal inputs
                inps = await page.evaluate("""() => {
                    return Array.from(document.querySelectorAll('.arco-modal input')).map(i => ({
                        placeholder: i.placeholder,
                        value: i.value,
                        className: i.className
                    }));
                }""")
                print("Modal inputs:", inps, flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
