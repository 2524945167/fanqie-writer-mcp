import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager
from core.novel_parser import get_novel_tree

BOOK_ID = "7687873685029407806"

async def test():
    vols = get_novel_tree()
    vol1 = vols[0]
    ch2 = vol1["chapters"][1]

    content = ch2.read_text(encoding='utf-8')
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    raw_title = lines[0]
    body_lines = lines[1:]

    m = re.search(r'第?\s*(\d+)\s*章?\s*(.*)', raw_title)
    ch_num = str(int(m.group(1))) if m else "2"
    ch_title = m.group(2).strip() if m else raw_title

    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        url = f"https://fanqienovel.com/main/writer/{BOOK_ID}/publish/?enter_from=newchapter"
        await page.goto(url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # 1. Fill title
        serial_inputs = await page.query_selector_all(".serial-input")
        if len(serial_inputs) >= 2:
            await serial_inputs[0].fill(ch_num)
            await serial_inputs[1].fill(ch_title)

        # 2. Fill body
        editor = await page.query_selector(".ProseMirror, [contenteditable='true']")
        html_p = "".join(f"<p>{l}</p>" for l in body_lines)
        await page.evaluate("""([el, html]) => {
            el.focus();
            el.innerHTML = html;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""", [editor, html_p])
        await asyncio.sleep(1)

        # 3. Click 存草稿
        draft_btn = await page.query_selector("button:has-text('存草稿')")
        if draft_btn:
            await draft_btn.click()
            print("Clicked 存草稿", flush=True)
            await asyncio.sleep(2)
            await page.screenshot(path='tests/ch2_draft_result.png')
            print("Saved tests/ch2_draft_result.png", flush=True)

            msg = await page.evaluate("() => { const el = document.querySelector('.arco-message, .arco-notification'); return el ? el.innerText : ''; }")
            print("Message after draft:", msg, flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
