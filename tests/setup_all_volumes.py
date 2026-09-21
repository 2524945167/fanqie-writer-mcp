import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

BOOK_ID = "7687873685029407806"
VOLUMES = [
    "这笔账先算清",
    "房间之外",
    "谁替谁签字",
    "空房的声音",
    "不替你决定",
    "留下不是认输"
]

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

        # 1. First volume: check if already named "这笔账先算清" or needs renaming
        vol_items = await page.query_selector_all(".chapter-volume-list-item")
        print(f"Current volume items count: {len(vol_items)}", flush=True)

        # Rename first volume if needed
        first_text = await vol_items[0].inner_text() if vol_items else ""
        if VOLUMES[0] not in first_text:
            edit_btn = await vol_items[0].query_selector(".tomato-edit")
            if edit_btn:
                await edit_btn.click()
                await asyncio.sleep(0.5)
                inp = await page.query_selector(".chapter-volume input")
                await inp.fill(VOLUMES[0])
                await page.click(".tomato-confirm.green")
                await asyncio.sleep(0.5)
                print(f"Set volume 1: {VOLUMES[0]}", flush=True)
        else:
            print(f"Volume 1 already set: {first_text}", flush=True)

        # 2. Add remaining volumes
        for vol_idx in range(1, len(VOLUMES)):
            vol_name = VOLUMES[vol_idx]
            # Check if volume already exists
            cur_items = await page.query_selector_all(".chapter-volume-list-item")
            cur_texts = [await it.inner_text() for it in cur_items]
            if any(vol_name in t for t in cur_texts):
                print(f"Volume {vol_idx+1} already exists: {vol_name}", flush=True)
                continue

            # Click 新建分卷
            await page.click(".chapter-volume-footer-add-volume")
            await asyncio.sleep(0.5)
            inp = await page.query_selector(".chapter-volume input")
            if inp:
                await inp.fill(vol_name)
                await asyncio.sleep(0.3)
                await page.click(".tomato-confirm.green")
                await asyncio.sleep(0.5)
                print(f"Added volume {vol_idx+1}: {vol_name}", flush=True)

        await page.screenshot(path='tests/all_volumes_before_confirm.png')
        print("Saved tests/all_volumes_before_confirm.png", flush=True)

        # Click the orange 确定 button to save all volumes
        confirm_btn = await page.query_selector(".chapter-volume button:has-text('确定'), .chapter-volume-footer-buttons button.byte-btn-primary")
        if confirm_btn:
            await confirm_btn.click()
            print("Clicked 确定 to save all volumes!", flush=True)
            await asyncio.sleep(2)

        await page.screenshot(path='tests/all_volumes_saved.png')
        print("Saved tests/all_volumes_saved.png", flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
