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
        url = 'https://fanqienovel.com/main/writer/7661632549390666776/publish/'
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)
        selectors_info = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('input, [contenteditable="true"], textarea, div[class*="title"], div[class*="editor"]')).map(el => ({
                tag: el.tagName,
                type: el.type || '',
                placeholder: el.placeholder || '',
                className: el.className || '',
                contentEditable: el.contentEditable || '',
                id: el.id || ''
            })).filter(x => x.tag === 'INPUT' || x.contentEditable === 'true' || x.placeholder);
        }""")
        print(json.dumps(selectors_info, ensure_ascii=False, indent=2))
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
