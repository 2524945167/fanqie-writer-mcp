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
        # 1. Visit Chapter Manage
        manage_url = f"https://fanqienovel.com/main/writer/chapter-manage/{BOOK_ID}"
        print(f"Navigating to {manage_url}...", flush=True)
        await page.goto(manage_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        await page.screenshot(path='tests/chapter_manage_new_book.png')
        print("Saved tests/chapter_manage_new_book.png", flush=True)

        # Inspect buttons and links
        buttons = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('button, a, .arco-btn')).map(b => ({
                tag: b.tagName,
                text: b.innerText ? b.innerText.trim() : '',
                href: b.getAttribute('href') || '',
                className: b.className
            })).filter(x => x.text);
        }""")
        print("Chapter manage buttons:", json.dumps(buttons[:20], ensure_ascii=False), flush=True)

        # 2. Visit Publish Page
        publish_url = f"https://fanqienovel.com/main/writer/{BOOK_ID}/publish/"
        print(f"Navigating to {publish_url}...", flush=True)
        await page.goto(publish_url, wait_until='domcontentloaded')
        await asyncio.sleep(3)
        await page.screenshot(path='tests/publish_page_new_book.png')
        print("Saved tests/publish_page_new_book.png", flush=True)

        # Inspect volume dropdown/selector on publish page
        vol_info = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('*')).filter(el => {
                return el.innerText && (el.innerText.includes('分卷') || el.innerText.includes('卷') || el.innerText.includes('正文')) && el.innerText.length < 50;
            }).map(el => ({
                tag: el.tagName,
                text: el.innerText.trim(),
                className: el.className
            })).slice(0, 30);
        }""")
        print("Publish page volume elements:", json.dumps(vol_info, ensure_ascii=False), flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
