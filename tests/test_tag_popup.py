import asyncio
import json
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

        await page.get_by_text("连载模式").first.click()
        await asyncio.sleep(0.5)
        await page.get_by_text("男频").first.click()
        await asyncio.sleep(1)

        # Click the 阅读标签 select-view inside #selectRow
        tag_btn = await page.query_selector("#selectRow .select-view")
        if tag_btn:
            await tag_btn.click()
            print("Clicked #selectRow .select-view", flush=True)
            await asyncio.sleep(1.5)
            await page.screenshot(path='tests/tag_modal_opened.png')

            # Let's inspect all visible popups / modals / dropdowns
            modal_info = await page.evaluate("""() => {
                const elements = Array.from(document.querySelectorAll('.arco-modal, .arco-trigger-popup, .arco-select-popup, .select-popup, .modal-wrap, .dialog, [class*=\"modal\"], [class*=\"popup\"], [class*=\"dialog\"], [class*=\"dropdown\"]'));
                return elements.map(el => ({
                    className: el.className,
                    text: el.innerText ? el.innerText.substring(0, 300) : '',
                    visible: el.offsetParent !== null,
                    html: el.outerHTML.substring(0, 500)
                }));
            }""")
            with open('tests/popup_info.json', 'w', encoding='utf-8') as f:
                json.dump(modal_info, f, ensure_ascii=False, indent=2)
            print("Saved tests/popup_info.json, count:", len(modal_info), flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
