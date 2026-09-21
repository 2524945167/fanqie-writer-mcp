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

        # Inspect all inputs, selects, labels
        data = await page.evaluate("""() => {
            const results = [];
            document.querySelectorAll('div, form, section').forEach(el => {
                if (el.innerText && el.innerText.includes('阅读标签') && el.innerText.length < 200) {
                    results.push({
                        text: el.innerText,
                        className: el.className,
                        html: el.outerHTML
                    });
                }
            });
            return results;
        }""")
        with open('tests/tag_container.json', 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print("Done, results:", len(data))
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
