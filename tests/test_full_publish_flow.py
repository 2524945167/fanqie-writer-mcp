import asyncio
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager
from core.novel_parser import get_novel_tree

BOOK_ID = "7687873685029407806"

async def publish_one_chapter(page, book_id, chapter_file, volume_title=None):
    content = chapter_file.read_text(encoding='utf-8')
    lines = [l.strip() for l in content.splitlines() if l.strip()]
    raw_title = lines[0]
    body_lines = lines[1:]

    # Extract chapter number and title
    # e.g. "第002章 三百万的底线" -> num: 2, title: "三百万的底线"
    m = re.search(r'第?\s*(\d+)\s*章?\s*(.*)', raw_title)
    if m:
        ch_num = str(int(m.group(1)))
        ch_title = m.group(2).strip() or raw_title
    else:
        ch_num = "1"
        ch_title = raw_title

    url = f"https://fanqienovel.com/main/writer/{book_id}/publish/?enter_from=newchapter"
    await page.goto(url, wait_until='domcontentloaded')
    await asyncio.sleep(2)

    # 1. Check volume if volume_title is provided
    if volume_title:
        cur_vol_text = await page.evaluate("() => { const el = document.querySelector('.publish-header-volume-name, .publish-header-volume-wrap'); return el ? el.innerText : ''; }")
        if volume_title not in cur_vol_text:
            print(f"Switching volume from '{cur_vol_text}' to '{volume_title}'...", flush=True)
            vol_trigger = await page.query_selector(".publish-header-volume-wrap, .publish-maintain-volume")
            if vol_trigger:
                await vol_trigger.click()
                await asyncio.sleep(1)

                # Look for volume_title in the modal list
                matched_item = await page.query_selector(f".chapter-volume-list-item:has-text('{volume_title}'), .editor-volume-list-item:has-text('{volume_title}')")
                if not matched_item:
                    # Need to add new volume
                    print(f"Volume '{volume_title}' not found in modal, creating it...", flush=True)
                    add_btn = await page.query_selector(".chapter-volume-footer-add-volume")
                    if add_btn:
                        await add_btn.click()
                        await asyncio.sleep(0.5)
                        inp = await page.query_selector(".chapter-volume input")
                        if inp:
                            await inp.fill(volume_title)
                            await page.click(".tomato-confirm.green")
                            await asyncio.sleep(0.5)
                else:
                    await matched_item.click()
                    await asyncio.sleep(0.5)

                # Confirm modal selection
                confirm_modal = await page.query_selector(".chapter-volume button:has-text('确定'), .chapter-volume-footer-buttons button.byte-btn-primary, .byte-modal-footer button.byte-btn-primary")
                if confirm_modal:
                    await confirm_modal.click()
                    await asyncio.sleep(1)

    # 2. Fill chapter number and title
    serial_inputs = await page.query_selector_all(".serial-input")
    if len(serial_inputs) >= 2:
        await serial_inputs[0].click()
        await serial_inputs[0].fill(ch_num)
        await serial_inputs[1].click()
        await serial_inputs[1].fill(ch_title)
    else:
        title_inp = await page.query_selector("input[placeholder*='标题'], input[placeholder*='章节名']")
        if title_inp:
            await title_inp.fill(raw_title)

    # 3. Fill body text
    html_p = "".join(f"<p>{l}</p>" for l in body_lines)
    editor = await page.query_selector(".ProseMirror, [contenteditable='true']")
    await page.evaluate("""([el, html]) => {
        el.focus();
        el.innerHTML = html;
        el.dispatchEvent(new Event('input', { bubbles: true }));
        el.dispatchEvent(new Event('change', { bubbles: true }));
    }""", [editor, html_p])
    await asyncio.sleep(1)

    # 4. Click 下一步
    next_btn = await page.query_selector("button:has-text('下一步')")
    if not next_btn:
        raise ValueError("未找到下一步按钮")
    await next_btn.click()
    await asyncio.sleep(1.5)

    # 5. Check for typo dialog
    typo_btn = await page.query_selector(".arco-modal button:has-text('提交'), button:has-text('提交')")
    if typo_btn:
        await typo_btn.click()
        await asyncio.sleep(1.5)

    # 6. Check for content test dialog
    check_btn = await page.query_selector("button:has-text('仅基础检测'), button:has-text('全面检测')")
    if check_btn:
        await check_btn.click()
        await asyncio.sleep(1.5)

    # 7. Check for 是否使用 AI -> 否
    ai_no = await page.query_selector(".arco-modal label:has-text('否'), label:has-text('否')")
    if ai_no:
        await ai_no.click()
        await asyncio.sleep(0.5)

    # 8. Confirm publish
    confirm_publish = await page.query_selector(".arco-modal button:has-text('确认发布'), button:has-text('确认发布')")
    if not confirm_publish:
        raise ValueError("未找到确认发布按钮")
    await confirm_publish.click()
    await asyncio.sleep(2.5)

    print(f"Successfully published: 第{ch_num}章 {ch_title}", flush=True)

async def test():
    vols = get_novel_tree()
    # Vol 1
    vol1 = vols[0]
    ch2 = vol1["chapters"][1] # 第002章
    print(f"Testing publish of: {ch2.name} in volume: {vol1['volume_title']}")

    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        await publish_one_chapter(page, BOOK_ID, ch2, vol1['volume_title'])
        await page.screenshot(path='tests/ch2_published.png')
        print("Saved tests/ch2_published.png", flush=True)
    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
