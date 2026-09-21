import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

BOOK_ID = "7687873685029407806"
CH2_FILE = Path(r"D:\AI-Outputs\Antigravity\都市长篇_不肯散场_全本交付\分卷章节TXT\卷一_这笔账先算清\第002章_三百万的底线.txt")

async def test():
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        content = CH2_FILE.read_text(encoding='utf-8')
        lines = [l.strip() for l in content.splitlines() if l.strip()]
        title_line = lines[0] # 第002章 三百万的底线
        body_lines = lines[1:]

        publish_url = f"https://fanqienovel.com/main/writer/{BOOK_ID}/publish/"
        print(f"Going to {publish_url}...", flush=True)
        await page.goto(publish_url, wait_until='domcontentloaded')
        await asyncio.sleep(2)

        # 1. Fill title
        serial_inputs = await page.query_selector_all(".serial-input")
        if len(serial_inputs) >= 2:
            await serial_inputs[0].fill("2")
            await serial_inputs[1].fill("三百万的底线")
            print("Filled chapter 2 title: 2 三百万的底线", flush=True)

        # 2. Fill content
        editor = await page.query_selector(".ProseMirror, [contenteditable='true']")
        html_p = "".join(f"<p>{l}</p>" for l in body_lines)
        await page.evaluate("""([el, html]) => {
            el.focus();
            el.innerHTML = html;
            el.dispatchEvent(new Event('input', { bubbles: true }));
            el.dispatchEvent(new Event('change', { bubbles: true }));
        }""", [editor, html_p])
        print(f"Filled body with {len(body_lines)} paragraphs", flush=True)
        await asyncio.sleep(1)

        # 3. Next step
        next_btn = await page.query_selector("button:has-text('下一步')")
        if next_btn:
            await next_btn.click()
            print("Clicked 下一步", flush=True)
            await asyncio.sleep(1.5)

            # Typo modal if any
            typo_confirm = await page.query_selector(".arco-modal button:has-text('提交'), button:has-text('提交')")
            if typo_confirm:
                await typo_confirm.click()
                print("Clicked typo confirm", flush=True)
                await asyncio.sleep(1.5)

            check_btn = await page.query_selector("button:has-text('仅基础检测'), button:has-text('全面检测')")
            if check_btn:
                await check_btn.click()
                print("Clicked 仅基础检测", flush=True)
                await asyncio.sleep(1.5)

            # AI: 否
            ai_no = await page.query_selector(".arco-modal label:has-text('否'), label:has-text('否')")
            if ai_no:
                await ai_no.click()
                print("Selected 是否使用AI: 否", flush=True)
                await asyncio.sleep(0.5)

            # Confirm publish
            confirm_btn = await page.query_selector(".arco-modal button:has-text('确认发布')")
            if confirm_btn:
                await confirm_btn.click()
                print("Clicked 确认发布!", flush=True)
                await asyncio.sleep(3)
                print("Final URL:", page.url, flush=True)
                await page.screenshot(path='tests/ch2_published_success.png')
                print("Saved tests/ch2_published_success.png", flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
