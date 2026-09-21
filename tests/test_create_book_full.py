import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager

INTRO = """前世死于酒店火灾的会展经理陈越，醒来回到2019年9月签署离职交接单的胶合板桌前。这一次，他没有狂妄地以为重活一次就能主宰世界，也没有去当面面俱到的拯救者。他在活页本第一页写下了【300万元个人现金储备】的安全离场线。他唯一的底线，是不替别人的人生签字，也不让虚妄的泡沫压断自己的脊梁。从濒临倒闭的临川泊岸客栈开始，他结识了死战不退的老板娘周岚、野蛮生长的会展人丁薇、在名利场自持的孟宁……没有系统开挂，硬核写透酒店、会展、文旅真实行业的账本、博弈与人情冷暖。宴席终会散场，风暴终会过去；但认真生活的骨头，永远不肯认输！"""

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

        # Listen to API responses
        async def on_response(res):
            if "create" in res.url or "book" in res.url:
                try:
                    text = await res.text()
                    if "code" in text or "msg" in text:
                        print(f"API {res.status} {res.url[:80]} -> {text[:200]}", flush=True)
                except Exception:
                    pass
        page.on("response", on_response)

        # 1. 书名
        title_input = await page.query_selector("#name_input input")
        test_title = "不肯散场：逆流2019"
        await title_input.fill(test_title)
        print(f"Filled book title: {test_title}", flush=True)

        # 2. 签约模式
        await page.get_by_text("连载模式").first.click()
        await asyncio.sleep(0.5)

        # 3. 目标读者
        await page.get_by_text("男频").first.click()
        await asyncio.sleep(1)

        # 4. 阅读标签
        await page.click("#selectRow .select-view")
        await asyncio.sleep(1)
        tag_elem = page.locator(".category-modal").get_by_text("都市日常", exact=True).first
        await tag_elem.click()
        await asyncio.sleep(0.5)
        confirm_btn = page.locator(".category-modal .arco-modal-footer button:has-text('确认')")
        await confirm_btn.click()
        print("Selected tag 都市日常", flush=True)
        await asyncio.sleep(1)

        # 5. 主角名
        role_input = await page.query_selector("#roleList input")
        if role_input:
            await role_input.fill("陈越")
            print("Filled protagonist: 陈越", flush=True)

        # 6. 作品简介
        desc_area = await page.query_selector("#descRow textarea")
        if desc_area:
            await desc_area.fill(INTRO.strip())
            print(f"Filled synopsis ({len(INTRO.strip())} chars)", flush=True)

        await page.screenshot(path='tests/form_ready_to_create.png')
        print("Saved tests/form_ready_to_create.png", flush=True)

        # 7. 点击立即创建
        create_btn = page.locator("button:has-text('立即创建')")
        await create_btn.click()
        print("Clicked 立即创建", flush=True)
        await asyncio.sleep(3)

        print("Current URL after create:", page.url, flush=True)
        await page.screenshot(path='tests/after_create.png')
        print("Saved tests/after_create.png", flush=True)

    finally:
        await page.close()
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
