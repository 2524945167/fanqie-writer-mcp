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
        # 1. Click 编辑分卷 on Chapter Manage
        manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{BOOK_ID}"
        await page.goto(manage_url, wait_until='domcontentloaded')
        await asyncio.sleep(2)
        
        # Dismiss any guide tooltip if present
        guide = await page.query_selector("button:has-text('我知道了')")
        if guide:
            await guide.click()
            await asyncio.sleep(0.5)

        edit_vol_btn = await page.query_selector("button:has-text('编辑分卷')")
        if edit_vol_btn:
            await edit_vol_btn.click()
            print("Clicked 编辑分卷", flush=True)
            await asyncio.sleep(1.5)
            await page.screenshot(path='tests/volume_edit_modal.png')
            print("Saved tests/volume_edit_modal.png", flush=True)

            modal_info = await page.evaluate("""() => {
                const modal = document.querySelector('.arco-modal, [role=\"dialog\"]');
                return modal ? {
                    text: modal.innerText,
                    html: modal.outerHTML
                } : null;
            }""")
            with open('tests/volume_modal_info.json', 'w', encoding='utf-8') as f:
                json.dump(modal_info, f, ensure_ascii=False, indent=2)

        # 2. Inspect publish page volume dropdown
        publish_url = f"https://fanqienovel.com/main/writer/{BOOK_ID}/publish/"
        await page.goto(publish_url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        vol_trigger = await page.query_selector(".publish-header-volume-wrap, .publish-maintain-volume")
        if vol_trigger:
            await vol_trigger.click()
            print("Clicked publish volume trigger", flush=True)
            await asyncio.sleep(1)
            await page.screenshot(path='tests/publish_volume_dropdown.png')
            print("Saved tests/publish_volume_dropdown.png", flush=True)

            drop_info = await page.evaluate("""() => {
                return Array.from(document.querySelectorAll('.arco-dropdown, .arco-trigger-popup, .publish-volume-dropdown, [class*=\"volume\"]')).map(el => ({
                    className: el.className,
                    text: el.innerText
                })).filter(x => x.text);
            }""")
            print("Publish volume dropdown info:", json.dumps(drop_info[:10], ensure_ascii=False), flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
