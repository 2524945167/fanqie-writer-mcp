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
            await page.goto(FANQIE_BOOK_LIST_URL, wait_until="networkidle", timeout=20000)
            await asyncio.sleep(2)

            books = []
            
            # 兼容多种常见的作品卡片容器选择器
            card_selectors = [
                ".book-manage-item",
                ".book-card",
                "[class*='book-item']",
                "[class*='bookCard']",
                "tr[class*='book']",
            ]
            
            cards = []
            for sel in card_selectors:
                cards = await page.query_selector_all(sel)
                if cards:
                    break

            # 如果没有匹配到预设卡片选择器，通过带 book id 的链接反查
            if not cards:
                cards = await page.query_selector_all("a[href*='/page/book/']")

            for card in cards:
                try:
                    text_content = await card.inner_text()
                    # 提取书籍 ID
                    html = await card.evaluate("el => el.outerHTML")
                    book_id_match = re.search(r'/page/book/(\d+)', html) or re.search(r'book_id[=:]\s*[\'"]?(\d+)', html)
                    book_id = book_id_match.group(1) if book_id_match else None

                    if not book_id:
                        continue

                    # 提取书名
                    title_el = await card.query_selector("[class*='title'], h3, h4, .book-name, a[title]")
                    title = ""
                    if title_el:
                        title = (await title_el.inner_text()).strip()
                    if not title:
                        lines = [line.strip() for line in text_content.splitlines() if line.strip()]
                        title = lines[0] if lines else f"书籍_{book_id}"

                    # 提取封面图片 URL
                    img_el = await card.query_selector("img")
                    cover_url = await img_el.get_attribute("src") if img_el else None

                    # 提取字数/状态
                    status = "连载中" if "连载" in text_content else ("已完结" if "完结" in text_content else "正常")
                    word_count_match = re.search(r'(\d+(\.\d+)?[万千]?字)', text_content)
                    word_count = word_count_match.group(1) if word_count_match else "未知"

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
            
            # 打开章节创建页
            url = FANQIE_CHAPTER_CREATE_URL.format(book_id=book_id)
            await page.goto(url, wait_until="networkidle", timeout=25000)
            await asyncio.sleep(2)

            # 1. 填写章节标题
            title_selectors = [
                "input[placeholder*='章节名']",
                "input[placeholder*='章节标题']",
                "input[placeholder*='输入标题']",
                ".chapter-title-input input",
                "input.byte-input",
                "input[type='text']",
            ]
            title_input = None
            for sel in title_selectors:
                title_input = await page.query_selector(sel)
                if title_input:
                    break

            if not title_input:
                raise ValueError("未找到章节标题输入框，请检查页面是否加载完全")

            await title_input.click()
            await title_input.fill(title)
            await asyncio.sleep(0.5)

            # 2. 填写章节正文
            # 番茄后台为富文本编辑器，采用 contenteditable 或 ProseMirror
            editor_selectors = [
                ".ProseMirror",
                "[contenteditable='true']",
                ".editor-content",
                ".public-DraftEditor-content",
                "textarea[placeholder*='正文']",
            ]
            editor_el = None
            for sel in editor_selectors:
                editor_el = await page.query_selector(sel)
                if editor_el:
                    break

            if not editor_el:
                raise ValueError("未找到正文编辑器区域")

            # 格式化正文段落（按换行符转为 HTML 段落或保留空行）
            paragraphs = [p.strip() for p in content.splitlines() if p.strip()]
            html_content = "".join(f"<p>{p}</p>" for p in paragraphs)

            # 通过 JS 注入富文本，高效且保持段落结构，同时派发 input 事件
            await page.evaluate(
                """([selector, html]) => {
                    const el = document.querySelector(selector);
                    if (el) {
                        el.focus();
                        el.innerHTML = html;
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }
                }""",
                [editor_selectors[0], html_content]
            )
            await asyncio.sleep(1)

            # 3. 处理发布策略：存草稿 / 定时发布 / 立即发布
            if is_draft:
                # 点击保存草稿
                draft_btn = await page.query_selector("button:has-text('存草稿'), button:has-text('保存草稿')")
                if not draft_btn:
                    raise ValueError("未找到'保存草稿'按钮")
                await draft_btn.click()
                await asyncio.sleep(2)
                return {
                    "success": True,
                    "book_id": book_id,
                    "title": title,
                    "mode": "draft",
                    "message": "章节已成功保存为草稿！",
                }

            if publish_time:
                # 定时发布流程
                timed_radio = await page.query_selector("label:has-text('定时发布'), text='定时发布', input[value*='timed']")
                if timed_radio:
                    await timed_radio.click()
                    await asyncio.sleep(1)

                    # 定位日期时间输入框并填入
                    time_input = await page.query_selector(
                        "input[placeholder*='时间'], input[placeholder*='日期'], .arco-picker-input input"
                    )
                    if time_input:
                        await time_input.click()
                        await time_input.fill(publish_time)
                        await page.keyboard.press("Enter")
                        await asyncio.sleep(1)

            # 点击立即发布 / 发布 / 确认定时发布
            publish_btn = await page.query_selector(
                "button:has-text('立即发布'), button:has-text('定时发布'), button:has-text('发布')"
            )
            if not publish_btn:
                raise ValueError("未找到发布确认按钮")

            await publish_btn.click()
            await asyncio.sleep(1)

            # 处理可能弹出的二次确认对话框 ("确定发布", "确认")
            confirm_btn = await page.query_selector(
                ".arco-modal button:has-text('确定'), .arco-modal button:has-text('发布'), button:has-text('确认发布')"
            )
            if confirm_btn:
                await confirm_btn.click()
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
