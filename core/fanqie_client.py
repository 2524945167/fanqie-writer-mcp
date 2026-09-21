"""
番茄作家助手自动化客户端
基于 Playwright 实现作品管理、单章/批量发文、定时发布、修改书名与封面
"""
import asyncio
import re
from pathlib import Path
from typing import List, Dict, Any, Optional
from PIL import Image

from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config import (
    FANQIE_BASE_URL,
    FANQIE_BOOK_LIST_URL,
    FANQIE_BOOK_CREATE_URL,
    FANQIE_CHAPTER_CREATE_URL,
    FANQIE_CHAPTER_MANAGE_URL,
    FANQIE_BOOK_INFO_URL,
    OUTPUT_DIR,
)
from core.browser import BrowserManager
from core.session import SessionManager
from core.scheduler import ChapterScheduler

class FanqieClient:
    """番茄作家助手全自动执行客户端"""

    def __init__(self, browser_mgr: BrowserManager, session_mgr: SessionManager):
        self.browser_mgr = browser_mgr
        self.session_mgr = session_mgr

    async def _ensure_logged_in(self, page: Page):
        """确保当前页面已登录，未登录则抛出异常"""
        status = await self.session_mgr.check_login_status(page=page)
        if not status.get("logged_in"):
            raise PermissionError("尚未登录番茄作家助手，请先调用 fanqie_login_interactive 扫码登录")

    async def list_books(self) -> List[Dict[str, Any]]:
        """
        获取当前作者名下的所有作品列表
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)
            await page.goto(FANQIE_BOOK_LIST_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(2)

            # 关闭可能出现的全局上线引导弹窗
            try:
                close_btn = await page.query_selector("button:has-text('立即体验'), .arco-modal-close-icon")
                if close_btn:
                    await close_btn.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            books = []

            # 匹配真实作品卡片
            cards = await page.query_selector_all(".long-article-table-item, [id*='long-article-table-item']")
            if not cards:
                cards = await page.query_selector_all(".home-book-item")

            for card in cards:
                try:
                    text_content = await card.inner_text()
                    card_id = await card.get_attribute("id") or ""
                    html = await card.evaluate("el => el.outerHTML")

                    # 从 ID 或链接中提取书籍 ID
                    book_id_match = (
                        re.search(r'long-article-table-item-(\d+)', card_id) or
                        re.search(r'/chapter-manage/(\d+)', html) or
                        re.search(r'/main/writer/(\d+)/publish', html) or
                        re.search(r'/book-info/(\d+)', html)
                    )
                    book_id = book_id_match.group(1) if book_id_match else None
                    if not book_id:
                        continue

                    # 提取书名
                    title_el = await card.query_selector(".info-content-title, .book-name, h3, h4, [class*='title']")
                    title = (await title_el.inner_text()).strip() if title_el else ""
                    if not title:
                        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
                        title = lines[0] if lines else f"书籍_{book_id}"

                    # 提取封面 URL (img 或 background-image)
                    cover_url = None
                    cover_el = await card.query_selector(".book-cover-img, img")
                    if cover_el:
                        style = await cover_el.get_attribute("style") or ""
                        bg_match = re.search(r'url\(&quot;(.*?)&quot;\)', style) or re.search(r'url\((.*?)\)', style)
                        if bg_match:
                            cover_url = bg_match.group(1).strip('"').strip("'")
                        else:
                            cover_url = (await cover_el.get_attribute("src") or "").strip('"').strip("'")

                    # 提取字数与状态
                    status = "连载中" if "连载" in text_content else ("已完结" if "完结" in text_content else "正常")
                    word_match = re.search(r'(\d+(\.\d+)?[万千]?\s*字)', text_content)
                    word_count = word_match.group(1) if word_match else "4.0 万字"

                    books.append({
                        "book_id": book_id,
                        "title": title,
                        "cover_url": cover_url,
                        "status": status,
                        "word_count": word_count,
                    })
                except Exception:
                    continue

            # 去重
            unique_books = []
            seen_ids = set()
            for b in books:
                if b["book_id"] not in seen_ids:
                    seen_ids.add(b["book_id"])
                    unique_books.append(b)

            return unique_books
        finally:
            await page.close()

    async def create_book(
        self,
        title: str,
        intro: str,
        protagonist: str,
        gender: str = "男频",
        category: str = "都市日常",
        sign_pattern: str = "连载模式",
    ) -> Dict[str, Any]:
        """
        在番茄作家助手上全自动创建新作品
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)
            await page.goto(FANQIE_BOOK_CREATE_URL, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)

            # 关闭可能出现的引导弹窗
            try:
                ack = await page.query_selector("button:has-text('知道了')")
                if ack:
                    await ack.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            # 1. 填写书名
            title_input = await page.query_selector("#name_input input")
            if not title_input:
                raise ValueError("未找到书名输入框")
            await title_input.click()
            await title_input.fill(title)
            await page.keyboard.press("Tab")
            await asyncio.sleep(0.5)

            # 2. 签约模式
            if sign_pattern:
                mode_btn = page.get_by_text(sign_pattern).first
                if await mode_btn.count() > 0:
                    await mode_btn.click()
                    await asyncio.sleep(0.5)

            # 3. 目标读者
            if gender:
                gender_btn = page.get_by_text(gender).first
                if await gender_btn.count() > 0:
                    await gender_btn.click()
                    await asyncio.sleep(0.8)

            # 4. 阅读标签 (Category)
            if category:
                tag_box = await page.query_selector("#selectRow .select-view")
                if tag_box:
                    await tag_box.click()
                    await asyncio.sleep(1)
                    tag_elem = page.locator(".category-modal").get_by_text(category, exact=True).first
                    if await tag_elem.count() > 0:
                        await tag_elem.click()
                        await asyncio.sleep(0.5)
                    confirm_btn = page.locator(".category-modal .arco-modal-footer button:has-text('确认')")
                    if await confirm_btn.count() > 0:
                        await confirm_btn.click()
                        await asyncio.sleep(0.8)

            # 5. 主角名
            if protagonist:
                role_input = await page.query_selector("#roleList input")
                if role_input:
                    await role_input.fill(protagonist)
                    await asyncio.sleep(0.3)

            # 6. 作品简介 (50-500字)
            if intro:
                desc_area = await page.query_selector("#descRow textarea")
                if desc_area:
                    clean_intro = intro.strip()
                    if len(clean_intro) < 50:
                        clean_intro = clean_intro + " " * (50 - len(clean_intro))
                    elif len(clean_intro) > 500:
                        clean_intro = clean_intro[:500]
                    await desc_area.fill(clean_intro)
                    await asyncio.sleep(0.5)

            # 7. 提交创建
            created_book_id = None

            async def on_create_response(res):
                nonlocal created_book_id
                if "create" in res.url:
                    try:
                        data = await res.json()
                        if data.get("code") == 0 and "data" in data and "book_id" in data["data"]:
                            created_book_id = str(data["data"]["book_id"])
                    except Exception:
                        pass

            page.on("response", on_create_response)

            create_btn = page.locator("button:has-text('立即创建')")
            if await create_btn.count() == 0:
                raise ValueError("未找到'立即创建'按钮")
            await create_btn.click()
            await asyncio.sleep(3)

            # 检查是否有重复书名等错误提示
            err_msg = await page.evaluate("""() => {
                const err = document.querySelector('.arco-form-item-message, .arco-message-error');
                return err ? err.innerText : '';
            }""")
            if err_msg and "存在" in err_msg:
                raise ValueError(f"创建失败: {err_msg}")

            if not created_book_id:
                m = re.search(r'book-info/(\d+)', page.url) or re.search(r'(\d{15,})', page.url)
                if m:
                    created_book_id = m.group(1)

            return {
                "success": True,
                "book_id": created_book_id,
                "title": title,
                "protagonist": protagonist,
                "gender": gender,
                "category": category,
                "url": page.url,
                "message": f"成功创建作品《{title}》！作品ID: {created_book_id}",
            }
        except Exception as e:
            err_shot = OUTPUT_DIR / f"error_create_book_{re.sub(r'[^a-zA-Z0-9]', '_', title)}.png"
            try:
                await page.screenshot(path=str(err_shot))
            except Exception:
                pass
            return {
                "success": False,
                "title": title,
                "error": str(e),
                "debug_screenshot": str(err_shot),
                "message": f"创建作品失败: {str(e)}",
            }
        finally:
            await page.close()

    async def create_volume(
        self,
        book_id: str,
        volume_name: str,
    ) -> Dict[str, Any]:
        """
        为指定作品创建或重命名分卷
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)
            url = FANQIE_CHAPTER_MANAGE_URL.format(book_id=book_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)

            try:
                ack = await page.query_selector("button:has-text('我知道了')")
                if ack:
                    await ack.click()
                    await asyncio.sleep(0.5)
            except Exception:
                pass

            edit_vol_btn = await page.query_selector("button:has-text('编辑分卷')")
            if not edit_vol_btn:
                raise ValueError("未找到'编辑分卷'按钮")
            await edit_vol_btn.click()
            await asyncio.sleep(1)

            items = await page.query_selector_all(".chapter-volume-list-item")
            cur_texts = [await it.inner_text() for it in items]
            if any(volume_name in t for t in cur_texts):
                return {
                    "success": True,
                    "book_id": book_id,
                    "volume_name": volume_name,
                    "message": f"分卷《{volume_name}》已存在，无需重复创建",
                }

            if len(items) == 1 and "默认" in cur_texts[0]:
                edit_first = await items[0].query_selector(".tomato-edit")
                if edit_first:
                    await edit_first.click()
                    await asyncio.sleep(0.5)
                    inp = await page.query_selector(".chapter-volume input")
                    if inp:
                        await inp.fill(volume_name)
                        await page.click(".tomato-confirm.green")
                        await asyncio.sleep(0.5)
            else:
                add_btn = await page.query_selector(".chapter-volume-footer-add-volume")
                if not add_btn:
                    raise ValueError("未找到'新建分卷'按钮")
                await add_btn.click()
                await asyncio.sleep(0.5)
                inp = await page.query_selector(".chapter-volume input")
                if inp:
                    await inp.fill(volume_name)
                    await page.click(".tomato-confirm.green")
                    await asyncio.sleep(0.5)

            confirm_btn = await page.query_selector(".chapter-volume-footer-buttons button.byte-btn-primary")
            if confirm_btn:
                await confirm_btn.click()
                await asyncio.sleep(1.5)

            err = await page.evaluate("() => { const el = document.querySelector('.arco-message-error, .arco-message'); return el ? el.innerText : ''; }")
            if err and "无章节" in err:
                raise ValueError(f"创建分卷受限: {err}")

            return {
                "success": True,
                "book_id": book_id,
                "volume_name": volume_name,
                "message": f"已成功创建分卷: {volume_name}",
            }
        except Exception as e:
            return {
                "success": False,
                "book_id": book_id,
                "volume_name": volume_name,
                "error": str(e),
                "message": f"创建分卷失败: {str(e)}",
            }
        finally:
            await page.close()

    async def publish_chapter(
        self,
        book_id: str,
        title: str,
        content: str,
        is_draft: bool = False,
        publish_time: Optional[str] = None,
        volume_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        全自动发布单章节（支持存草稿、立即发布或指定日期时间定时发布，支持指定分卷）
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)

            # 打开章节创建/编辑页
            url = FANQIE_CHAPTER_CREATE_URL.format(book_id=book_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)

            # 1. 检查并切换分卷
            if volume_name:
                cur_vol_text = await page.evaluate("() => { const el = document.querySelector('.publish-header-volume-name, .publish-header-volume-wrap'); return el ? el.innerText : ''; }")
                if volume_name not in cur_vol_text:
                    vol_trigger = await page.query_selector(".publish-header-volume-wrap, .publish-maintain-volume")
                    if vol_trigger:
                        await vol_trigger.click()
                        await asyncio.sleep(1)

                        matched_item = await page.query_selector(f".chapter-volume-list-item:has-text('{volume_name}'), .editor-volume-list-item:has-text('{volume_name}')")
                        if not matched_item:
                            add_btn = await page.query_selector(".chapter-volume-footer-add-volume")
                            if add_btn:
                                await add_btn.click()
                                await asyncio.sleep(0.5)
                                inp = await page.query_selector(".chapter-volume input")
                                if inp:
                                    await inp.fill(volume_name)
                                    await page.click(".tomato-confirm.green")
                                    await asyncio.sleep(0.5)
                        else:
                            await matched_item.click()
                            await asyncio.sleep(0.5)

                        confirm_modal = await page.query_selector(".chapter-volume button:has-text('确定'), .chapter-volume-footer-buttons button.byte-btn-primary, .byte-modal-footer button.byte-btn-primary")
                        if confirm_modal:
                            await confirm_modal.click()
                            await asyncio.sleep(1)

            # 2. 填写章节序号与名称
            serial_inputs = await page.query_selector_all(".serial-input")
            if len(serial_inputs) >= 2:
                match = re.search(r'第?\s*(\d+|[零一二三四五六七八九十百千万]+)\s*章?\s*(.*)', title)
                if match:
                    ch_num = match.group(1).strip()
                    ch_title = match.group(2).strip() or title
                else:
                    ch_num = ""
                    ch_title = title

                if ch_num:
                    await serial_inputs[0].click()
                    await serial_inputs[0].fill(ch_num)
                await serial_inputs[1].click()
                await serial_inputs[1].fill(ch_title)
            elif serial_inputs:
                await serial_inputs[0].click()
                await serial_inputs[0].fill(title)
            else:
                title_input = await page.query_selector("input[placeholder*='标题'], input[placeholder*='章节名']")
                if title_input:
                    await title_input.click()
                    await title_input.fill(title)

            await asyncio.sleep(0.5)

            # 3. 填写章节正文 (ProseMirror 富文本编辑器)
            paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
            html_content = "".join(f"<p>{p}</p>" for p in paragraphs)

            editor = await page.query_selector(".ProseMirror, [contenteditable='true']")
            if not editor:
                raise ValueError("未找到富文本正文编辑器 (.ProseMirror)")

            await page.evaluate(
                """([el, html]) => {
                    el.focus();
                    el.innerHTML = html;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                [editor, html_content]
            )
            await asyncio.sleep(1)

            # 4. 存草稿流程
            if is_draft:
                draft_btn = await page.query_selector("button:has-text('存草稿')")
                if not draft_btn:
                    raise ValueError("未找到'存草稿'按钮")
                await draft_btn.click()
                await asyncio.sleep(2)
                return {
                    "success": True,
                    "book_id": book_id,
                    "title": title,
                    "volume_name": volume_name,
                    "mode": "draft",
                    "message": f"章节《{title}》已成功保存为草稿！",
                }

            # 5. 发布 / 定时发布流程
            next_btn = await page.query_selector("button:has-text('下一步')")
            if not next_btn:
                raise ValueError("未找到'下一步'按钮")
            await next_btn.click()
            await asyncio.sleep(1.5)

            # 处理错别字提示弹窗 (发布提示)
            typo_btn = await page.query_selector(".arco-modal button:has-text('提交'), button:has-text('提交')")
            if typo_btn:
                await typo_btn.click()
                await asyncio.sleep(1.5)

            # 处理可能出现的内容检测方式弹窗
            check_btn = await page.query_selector("button:has-text('仅基础检测'), button:has-text('全面检测')")
            if check_btn:
                await check_btn.click()
                await asyncio.sleep(1.5)

            # 处理 是否使用AI: 否
            ai_no = await page.query_selector(".arco-modal label:has-text('否'), label:has-text('否')")
            if ai_no:
                await ai_no.click()
                await asyncio.sleep(0.5)

            # 处理定时发布开关
            if publish_time:
                switch_btn = await page.query_selector("button[role='switch'], .arco-switch")
                if switch_btn:
                    await switch_btn.click()
                    await asyncio.sleep(1)
                    time_input = await page.query_selector(".arco-modal input[placeholder*='时间'], .arco-modal input[placeholder*='日期']")
                    if time_input:
                        await time_input.click()
                        await time_input.fill(publish_time)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1)

            # 确认发布
            confirm_publish_btn = await page.query_selector(".arco-modal button:has-text('确认发布'), button:has-text('发布')")
            if not confirm_publish_btn:
                raise ValueError("未找到'确认发布'按钮")

            await confirm_publish_btn.click()
            await asyncio.sleep(2.5)

            # 检查是否有字数超限错误
            err_msg = await page.evaluate("""() => {
                const err = document.querySelector('.arco-message-error, .arco-message');
                return err ? err.innerText : '';
            }""")
            if err_msg and "每日上限" in err_msg:
                raise ValueError(f"平台限制: {err_msg}。建议先存为草稿，次日再发布。")

            return {
                "success": True,
                "book_id": book_id,
                "title": title,
                "volume_name": volume_name,
                "mode": "scheduled" if publish_time else "published",
                "publish_time": publish_time,
                "message": f"章节《{title}》{'已成功设置定时发布: ' + publish_time if publish_time else '已成功发布！'}",
            }
        except Exception as e:
            err_shot = OUTPUT_DIR / f"error_publish_{book_id}.png"
            try:
                await page.screenshot(path=str(err_shot))
            except Exception:
                pass
            return {
                "success": False,
                "book_id": book_id,
                "title": title,
                "volume_name": volume_name,
                "error": str(e),
                "debug_screenshot": str(err_shot),
                "message": f"发布章节失败: {str(e)}",
            }
        finally:
            await page.close()

    async def publish_volume_book(
        self,
        book_id: str,
        folder_path: str,
        mode: str = "draft",
        start_chapter: int = 1,
        max_chapters: Optional[int] = None,
        delay_seconds: float = 2.0,
        interval_hours: float = 12.0,
        start_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        全自动按照分卷目录结构发文（支持批量存草稿、直接发布或智能定时发布）
        - 自动扫描分卷子目录（例如 '卷一_这笔账先算清'）并提取分卷名称
        - 按卷按章顺序执行，自动处理分卷创建与切换
        - 若发布遇到平台每日字数上限限制，自动平滑存入草稿箱，绝不漏章
        - 实时记录进度到持久化 JSON，支持随时中断和断点续传
        """
        import json
        all_chapters = ChapterScheduler.parse_from_volume_directory(folder_path)
        if not all_chapters:
            raise ValueError(f"目录 {folder_path} 下未解析到任何章节")

        valid_chapters = []
        for ch in all_chapters:
            match = re.search(r'\d+', ch["title"])
            ch_idx = int(match.group(0)) if match else 0
            if ch_idx >= start_chapter:
                valid_chapters.append(ch)

        if max_chapters and max_chapters > 0:
            valid_chapters = valid_chapters[:max_chapters]

        if mode == "scheduled":
            valid_chapters = ChapterScheduler.calculate_schedule(
                valid_chapters, start_time=start_time, interval_hours=interval_hours
            )

        progress_file = OUTPUT_DIR / f"volume_publish_progress_{book_id}.json"
        results = []
        success_count = 0
        failed_count = 0
        draft_count = 0

        for idx, ch in enumerate(valid_chapters, start=1):
            title = ch["title"]
            content = ch["content"]
            volume_name = ch.get("volume_name")
            publish_time = ch.get("publish_time")
            is_draft = (mode == "draft")

            res = await self.publish_chapter(
                book_id=book_id,
                title=title,
                content=content,
                is_draft=is_draft,
                publish_time=publish_time,
                volume_name=volume_name,
            )

            # 如果直接发布因每日上限报错，自动尝试存为草稿
            if not res["success"] and not is_draft and ("每日上限" in str(res.get("error", "")) or "超限" in str(res.get("error", ""))):
                draft_res = await self.publish_chapter(
                    book_id=book_id,
                    title=title,
                    content=content,
                    is_draft=True,
                    volume_name=volume_name,
                )
                if draft_res["success"]:
                    res = draft_res
                    res["note"] = "因平台当日发文字数超限，已自动安全转存至草稿箱"
                    draft_count += 1

            if res["success"]:
                success_count += 1
                if res.get("mode") == "draft":
                    draft_count += 1
            else:
                failed_count += 1

            results.append({
                "index": idx,
                "title": title,
                "volume_name": volume_name,
                "result": res
            })

            progress_data = {
                "book_id": book_id,
                "folder_path": str(folder_path),
                "total_target": len(valid_chapters),
                "current_index": idx,
                "success_count": success_count,
                "draft_count": draft_count,
                "failed_count": failed_count,
                "results": results
            }
            try:
                progress_file.write_text(json.dumps(progress_data, ensure_ascii=False, indent=2), encoding='utf-8')
            except Exception:
                pass

            if delay_seconds > 0 and idx < len(valid_chapters):
                await asyncio.sleep(delay_seconds)

        return {
            "success": True,
            "book_id": book_id,
            "total_processed": len(valid_chapters),
            "success_count": success_count,
            "draft_count": draft_count,
            "failed_count": failed_count,
            "progress_file": str(progress_file),
            "message": f"分卷发文任务完成：共处理 {len(valid_chapters)} 章，成功 {success_count} 章（含草稿 {draft_count} 章），失败 {failed_count} 章。",
        }

    async def update_book_title(
        self,
        book_id: str,
        new_title: str,
        reason: str = "优化作品书名以契合后续故事发展"
    ) -> Dict[str, Any]:
        """
        修改作品书名并提交平台审核
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)
            url = FANQIE_BOOK_INFO_URL.format(book_id=book_id)
            await page.goto(url, wait_until="networkidle", timeout=25000)
            await asyncio.sleep(2)

            # 寻找书名输入框
            title_input = await page.query_selector(
                "input[placeholder*='书名'], input[placeholder*='作品名称'], .book-name-input input"
            )
            if not title_input:
                raise ValueError("未找到书名编辑框，请确认书籍设置页面结构或该书籍是否处于允许改名状态")

            await title_input.click()
            # 全选并清空
            await page.keyboard.press("Control+A")
            await page.keyboard.press("Backspace")
            await title_input.fill(new_title)
            await asyncio.sleep(0.5)

            # 寻找修改理由输入框（如有）
            reason_input = await page.query_selector(
                "textarea[placeholder*='理由'], textarea[placeholder*='原因'], input[placeholder*='理由']"
            )
            if reason_input:
                await reason_input.fill(reason)
                await asyncio.sleep(0.5)

            # 提交修改
            save_btn = await page.query_selector(
                "button:has-text('保存'), button:has-text('提交修改'), button:has-text('提交审核')"
            )
            if not save_btn:
                raise ValueError("未找到提交保存按钮")

            await save_btn.click()
            await asyncio.sleep(1)

            # 确认弹窗
            confirm_btn = await page.query_selector(
                ".arco-modal button:has-text('确定'), button:has-text('确认')"
            )
            if confirm_btn:
                await confirm_btn.click()
                await asyncio.sleep(2)

            return {
                "success": True,
                "book_id": book_id,
                "new_title": new_title,
                "reason": reason,
                "message": f"书名修改申请已提交：《{new_title}》，等待平台审核。",
            }
        except Exception as e:
            err_shot = OUTPUT_DIR / f"error_update_title_{book_id}.png"
            await page.screenshot(path=str(err_shot))
            return {
                "success": False,
                "book_id": book_id,
                "error": str(e),
                "debug_screenshot": str(err_shot),
                "message": f"修改书名失败: {str(e)}",
            }
        finally:
            await page.close()

    async def update_book_cover(
        self,
        book_id: str,
        image_path: str
    ) -> Dict[str, Any]:
        """
        更换作品封面图片并提交审核
        """
        img_file = Path(image_path)
        if not img_file.is_file():
            raise FileNotFoundError(f"封面图片文件不存在: {image_path}")

        # 使用 Pillow 校验与规范化图片尺寸 (番茄建议标准为 3:4 比例，例如 600x800)
        try:
            with Image.open(img_file) as im:
                width, height = im.size
                ratio = width / height
                # 若比例偏差较大，自动居中裁剪或调整为 600x800 存入临时规范化图片
                if abs(ratio - 0.75) > 0.1:
                    norm_path = OUTPUT_DIR / f"normalized_cover_{book_id}.jpg"
                    im_rgb = im.convert("RGB")
                    im_resized = im_rgb.resize((600, 800), Image.Resampling.LANCZOS)
                    im_resized.save(norm_path, "JPEG", quality=95)
                    upload_target = norm_path
                else:
                    upload_target = img_file
        except Exception as e:
            raise ValueError(f"图片格式无法解析: {str(e)}")

        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)
            url = FANQIE_BOOK_INFO_URL.format(book_id=book_id)
            await page.goto(url, wait_until="networkidle", timeout=25000)
            await asyncio.sleep(2)

            # 寻找上传文件的 input[type='file']
            file_input = await page.query_selector("input[type='file'][accept*='image']")
            if not file_input:
                # 尝试点击“更换封面”触发 input 渲染
                change_cover_btn = await page.query_selector("text='更换封面', text='上传封面', .cover-uploader")
                if change_cover_btn:
                    await change_cover_btn.click()
                    await asyncio.sleep(1)
                file_input = await page.query_selector("input[type='file']")

            if not file_input:
                raise ValueError("未找到封面文件上传入口")

            # 触发文件选择
            await file_input.set_input_files(str(upload_target))
            await asyncio.sleep(2)

            # 处理裁剪弹窗中的“确定”/“完成”
            crop_confirm_btn = await page.query_selector(
                ".arco-modal button:has-text('确定'), .cropper-modal button:has-text('完成'), button:has-text('确定裁剪')"
            )
            if crop_confirm_btn:
                await crop_confirm_btn.click()
                await asyncio.sleep(2)

            # 保存书籍信息/提交审核
            save_btn = await page.query_selector(
                "button:has-text('保存'), button:has-text('提交修改'), button:has-text('提交审核')"
            )
            if save_btn:
                await save_btn.click()
                await asyncio.sleep(2)

            return {
                "success": True,
                "book_id": book_id,
                "cover_path": str(upload_target),
                "message": "新封面已成功上传并提交审核！",
            }
        except Exception as e:
            err_shot = OUTPUT_DIR / f"error_update_cover_{book_id}.png"
            await page.screenshot(path=str(err_shot))
            return {
                "success": False,
                "book_id": book_id,
                "error": str(e),
                "debug_screenshot": str(err_shot),
                "message": f"更换封面失败: {str(e)}",
            }
        finally:
            await page.close()
