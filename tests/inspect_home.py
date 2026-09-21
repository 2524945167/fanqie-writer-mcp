import asyncio
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

async def inspect():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await page.goto('https://fanqienovel.com/main/writer/home', wait_until='domcontentloaded')
        await asyncio.sleep(3)
        await page.screenshot(path='tests/home_preview.png')
        print("Home preview saved to tests/home_preview.png")

        items = await page.evaluate("""() => {
            const list = [];
            document.querySelectorAll('a, button, div[class*="menu"], span[class*="menu"]').forEach(el => {
                const txt = (el.innerText || '').trim();
                const href = el.getAttribute('href') || '';
                if (txt && txt.length < 30 && (href || el.tagName === 'BUTTON' || el.className.includes('item'))) {
                    list.push({ tag: el.tagName, text: txt, href: href, class: el.className });
                }
            });
            return list;
        }""")
        print(json.dumps(items, ensure_ascii=False, indent=2))
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(inspect())
