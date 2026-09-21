import asyncio
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

        inputs = await page.query_selector_all(".serial-input")
        if len(inputs) >= 2:
            await inputs[0].fill("14")
            await inputs[1].fill("万道共鸣")

        body_text = ("天极大陆，十条天脉分割九域。" * 100)
        paragraphs = [body_text[i:i+200] for i in range(0, len(body_text), 200)]
        html_p = "".join(f"<p>{p}</p>" for p in paragraphs)

        editor = await page.query_selector(".ProseMirror")
        if editor:
            await page.evaluate("""([el, html]) => {
                el.focus();
                el.innerHTML = html;
                el.dispatchEvent(new Event('input', { bubbles: true }));
            }""", [editor, html_p])

        await asyncio.sleep(1)

        next_btn = await page.query_selector("button:has-text('下一步')")
        if next_btn:
            await next_btn.click()
            await asyncio.sleep(1.5)

            check_btn = await page.query_selector("button:has-text('仅基础检测')")
            if check_btn:
                await check_btn.click()
                await asyncio.sleep(1.5)

                # 点击定时发布开关
                switch_btn = await page.query_selector("button[role='switch'], .arco-switch")
                if switch_btn:
                    await switch_btn.click()
                    print("Toggled 定时发布 switch")
                    await asyncio.sleep(1)
                    await page.screenshot(path='tests/timed_publish_preview.png')
                    print("Saved tests/timed_publish_preview.png")

                    # 获取时间选择器输入框
                    pickers = await page.evaluate("""() => {
                        return Array.from(document.querySelectorAll('.arco-modal input')).map(el => ({
                            placeholder: el.placeholder,
                            className: el.className,
                            value: el.value
                        }));
                    }""")
                    print("Time pickers:", pickers)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
