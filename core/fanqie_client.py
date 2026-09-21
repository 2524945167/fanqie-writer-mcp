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
    FANQIE_CHAPTER_CREATE_URL,
    FANQIE_BOOK_INFO_URL,
    OUTPUT_DIR,
)
from core.browser import BrowserManager
from core.session import SessionManager

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

    async def publish_chapter(
        self,
        book_id: str,
        title: str,
        content: str,
        is_draft: bool = False,
        publish_time: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        全自动发布单章节（支持存草稿、立即发布或指定日期时间定时发布）
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await self._ensure_logged_in(page)

            # 打开章节创建/编辑页
            url = FANQIE_CHAPTER_CREATE_URL.format(book_id=book_id)
            await page.goto(url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2)

            # 1. 填写章节序号与名称
            serial_inputs = await page.query_selector_all(".serial-input")
            if len(serial_inputs) >= 2:
                # 尝试从 title 中分离出序号与标题（如 "第14章 万道共鸣"）
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

            # 2. 填写章节正文 (ProseMirror 富文本编辑器)
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

            # 3. 存草稿流程
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
                    "mode": "draft",
                    "message": f"章节《{title}》已成功保存为草稿！",
                }

            # 4. 发布 / 定时发布流程
            next_btn = await page.query_selector("button:has-text('下一步')")
            if not next_btn:
                raise ValueError("未找到'下一步'按钮")
            await next_btn.click()
            await asyncio.sleep(1.5)

            # 处理可能出现的内容检测方式弹窗
            check_btn = await page.query_selector("button:has-text('仅基础检测'), button:has-text('全面检测')")
            if check_btn:
                await check_btn.click()
                await asyncio.sleep(1.5)

            # 处理定时发布开关
            if publish_time:
                switch_btn = await page.query_selector("button[role='switch'], .arco-switch")
                if switch_btn:
                    await switch_btn.click()
                    await asyncio.sleep(1)
                    # 填入时间
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
            await asyncio.sleep(2)

            return {
                "success": True,
                "book_id": book_id,
                "title": title,
                "mode": "scheduled" if publish_time else "published",
                "publish_time": publish_time,
                "message": f"章节《{title}》{'已成功设置定时发布: ' + publish_time if publish_time else '已成功发布！'}",
            }
        except Exception as e:
            # 截屏排查
            err_shot = OUTPUT_DIR / f"error_publish_{book_id}.png"
            await page.screenshot(path=str(err_shot))
            return {
                "success": False,
                "book_id": book_id,
                "title": title,
                "error": str(e),
                "debug_screenshot": str(err_shot),
                "message": f"发布章节失败: {str(e)}",
            }
        finally:
            await page.close()

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
