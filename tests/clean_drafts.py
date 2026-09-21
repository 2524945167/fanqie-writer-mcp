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
        url = f"https://fanqienovel.com/main/writer/chapter-manage/{BOOK_ID}"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        guide = await page.query_selector("button:has-text('我知道了')")
        if guide:
            await guide.click()
            await asyncio.sleep(0.5)

        # Switch to 草稿箱
        await page.get_by_text("草稿箱").first.click()
        await asyncio.sleep(1.5)

        # Find all rows in draft box
        # We want to remove the draft of chapter 1 (since ch1 is already published)
        # and duplicate drafts of chapter 2
        while True:
            rows = await page.query_selector_all("tr")
            found_to_delete = False
            for r in rows:
                txt = await r.inner_text()
                if "第1章" in txt or (txt.count("第2章") > 0 and len([x for x in await page.query_selector_all("tr") if "第2章" in (await x.inner_text())]) > 1):
                    del_btn = await r.query_selector(".tomato-delete, [class*='delete'], svg")
                    if del_btn:
                        await del_btn.click()
                        await asyncio.sleep(0.5)
                        confirm = await page.query_selector(".arco-modal button:has-text('确定'), .byte-modal button:has-text('确定')")
                        if confirm:
                            await confirm.click()
                            print(f"Deleted draft: {txt.splitlines()[0]}", flush=True)
                            await asyncio.sleep(1)
                            found_to_delete = True
                            break
            if not found_to_delete:
                break

        await page.screenshot(path='tests/clean_drafts.png')
        print("Cleaned drafts, saved tests/clean_drafts.png", flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
