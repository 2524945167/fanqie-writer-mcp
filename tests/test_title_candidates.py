import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

CANDIDATES = [
    "不肯散场",
    "不肯散场：逆流2019",
    "不肯散场2019",
    "不肯散场：这笔账先算清",
    "不肯散场：绝不认输",
    "重回2019：不肯散场"
]

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

        title_input = await page.query_selector("#name_input input")
        
        for cand in CANDIDATES:
            await title_input.fill("")
            await asyncio.sleep(0.3)
            await title_input.fill(cand)
            # trigger blur
            await page.keyboard.press("Tab")
            await asyncio.sleep(1.5)
            
            error_el = await page.query_selector(".arco-form-item-message")
            err_text = await error_el.inner_text() if error_el else ""
            
            # also check if any element contains 该书名已存在
            exists = await page.evaluate("""() => {
                const el = document.querySelector('.arco-form-item-message, [class*=\"error\"], [class*=\"message\"]');
                return el ? el.innerText : '';
            }""")
            print(f"Title: '{cand}', error: '{exists}'", flush=True)
            if not exists or "存在" not in exists:
                print(f">>> AVAILABLE TITLE FOUND: '{cand}'", flush=True)
            else:
                print(f"XXX TAKEN: '{cand}'", flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
