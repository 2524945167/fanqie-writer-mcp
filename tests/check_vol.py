import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/chapter-manage/7687873685029407806', wait_until='domcontentloaded')
        await asyncio.sleep(2)
        # click 编辑分卷
        await page.click("button:has-text('编辑分卷')")
        await asyncio.sleep(1)
        items = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('.chapter-volume-list-item')).map(el => el.innerText.trim());
        }""")
        with open('tests/cur_vols.txt', 'w', encoding='utf-8') as f:
            for it in items:
                f.write(it + '\n')
        print("Saved to tests/cur_vols.txt")
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
