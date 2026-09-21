"""
番茄作家助手 FastMCP 服务端
提供标准的 MCP 工具接口：
1. fanqie_check_status: 检查登录态与作者信息
2. fanqie_login_interactive: 弹出浏览器窗口交互登录
3. fanqie_get_login_qrcode: 无头截取登录二维码图片
4. fanqie_list_books: 查询作品列表与状态
5. fanqie_publish_chapter: 发布单章节（支持存草稿、定时发布、立即发布）
6. fanqie_batch_publish_chapters: 一键批量自动定时发布大量文章
7. fanqie_update_book_title: 修改书名并提交审核
8. fanqie_update_book_cover: 更换封面并提交审核
9. fanqie_get_batch_progress: 查询批量发文进度与记录
"""
import asyncio
import os
import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from mcp.server import MCPServer

from config import DEFAULT_HEADLESS, DEFAULT_PUBLISH_INTERVAL_HOURS
from core.browser import BrowserManager
from core.session import SessionManager
from core.fanqie_client import FanqieClient
from core.scheduler import ChapterScheduler

# 初始化 MCPServer 实例
mcp = MCPServer("fanqie-writer-assistant", dependencies=["playwright", "pillow", "pydantic"])

# 实例化全局单例
browser_mgr = BrowserManager(headless=DEFAULT_HEADLESS)
session_mgr = SessionManager(browser_mgr)
fanqie_client = FanqieClient(browser_mgr, session_mgr)

@mcp.tool()
async def fanqie_check_status() -> str:
    """
    检查番茄作家助手当前登录状态及作者账号信息。
    """
    res = await session_mgr.check_login_status()
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_login_interactive(timeout_sec: int = 180) -> str:
    """
    在本地弹出 Chromium 浏览器窗口，供作者使用番茄作家助手 App 或抖音扫码/手机号登录。
    登录成功后凭证将自动持久化，后续无需重复登录。
    - timeout_sec: 登录等待超时时间（秒，默认 180 秒）
    """
    res = await session_mgr.login_interactive(timeout_sec=timeout_sec)
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_get_login_qrcode() -> str:
    """
    无头模式下截取番茄作家助手登录二维码保存到本地，返回图片路径供用户扫码。
    """
    res = await session_mgr.get_login_qrcode()
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_list_books() -> str:
    """
    获取作者名下的所有作品列表，包含书籍 ID (book_id)、书名、封面地址、字数和连载状态。
    """
    books = await fanqie_client.list_books()
    return json.dumps({"count": len(books), "books": books}, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_publish_chapter(
    book_id: str,
    title: str,
    content: str,
    is_draft: bool = False,
    publish_time: Optional[str] = None
) -> str:
    """
    全自动发布单章节或设置定时发布。
    - book_id: 书籍唯一 ID
    - title: 章节名称（如：'第1章 惊变'）
    - content: 章节正文文本
    - is_draft: 是否仅存为草稿（默认 False）
    - publish_time: 定时发布时间，格式如 '2026-09-22 12:00:00'。若不传则立即发布。
    """
    res = await fanqie_client.publish_chapter(
        book_id=book_id,
        title=title,
        content=content,
        is_draft=is_draft,
        publish_time=publish_time
    )
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_batch_publish_chapters(
    book_id: str,
    chapters_source: str,
    start_time: Optional[str] = None,
    interval_hours: Optional[float] = None,
    daily_slots: Optional[List[str]] = None,
    is_draft: bool = False,
    delay_between_chapters_sec: float = 2.0
) -> str:
    """
    一键批量自动定时发布大量文章章节。
    - book_id: 书籍唯一 ID
    - chapters_source: 章节来源，可以是包含多个章节文件的目录路径、单个完整小说文本文件路径，或 JSON 文件路径
    - start_time: 首章计划发布时间，如 '2026-09-22 10:00:00'。默认从次日上午 10:00 开始
    - interval_hours: 章节发布时间间隔（小时，如 12.0 表示每 12 小时发布一章）
    - daily_slots: 每日固定发布档期，如 ['10:00', '18:00']（与 interval_hours 二选一，优先采用 daily_slots）
    - is_draft: 是否批量保存为草稿（默认 False）
    - delay_between_chapters_sec: 每章发布间隔等待秒数，防止过快触发限频（默认 2 秒）
    """
    source_path = Path(chapters_source)
    if not source_path.exists():
        return json.dumps({"success": False, "message": f"章节来源不存在: {chapters_source}"}, ensure_ascii=False)

    # 1. 解析章节
    try:
        if source_path.is_dir():
            raw_chapters = ChapterScheduler.parse_from_directory(source_path)
        elif source_path.suffix.lower() == '.json':
            raw_chapters = json.loads(source_path.read_text(encoding='utf-8'))
        else:
            raw_chapters = ChapterScheduler.parse_from_single_file(source_path)
    except Exception as e:
        return json.dumps({"success": False, "message": f"解析章节失败: {str(e)}"}, ensure_ascii=False)

    if not raw_chapters:
        return json.dumps({"success": False, "message": "未提取到任何有效章节"}, ensure_ascii=False)

    # 2. 计算排期时间
    scheduled_chapters = ChapterScheduler.calculate_schedule(
        chapters=raw_chapters,
        start_time=start_time,
        daily_slots=daily_slots,
        interval_hours=interval_hours or DEFAULT_PUBLISH_INTERVAL_HOURS
    )

    total = len(scheduled_chapters)
    success_count = 0
    failed_items = []

    progress_data = {
        "book_id": book_id,
        "total": total,
        "completed": 0,
        "status": "processing",
        "chapters": []
    }
    ChapterScheduler.save_progress(progress_data)

    # 3. 循环批量发布
    for idx, item in enumerate(scheduled_chapters):
        title = item["title"]
        content = item["content"]
        ptime = item.get("publish_time") if not is_draft else None

        res = await fanqie_client.publish_chapter(
            book_id=book_id,
            title=title,
            content=content,
            is_draft=is_draft,
            publish_time=ptime
        )

        item_record = {
            "index": idx + 1,
            "title": title,
            "publish_time": ptime,
            "success": res.get("success", False),
            "message": res.get("message", "")
        }

        if res.get("success"):
            success_count += 1
        else:
            failed_items.append(item_record)

        progress_data["completed"] = idx + 1
        progress_data["chapters"].append(item_record)
        ChapterScheduler.save_progress(progress_data)

        if delay_between_chapters_sec > 0:
            await asyncio.sleep(delay_between_chapters_sec)

    progress_data["status"] = "finished" if not failed_items else "partial_failed"
    ChapterScheduler.save_progress(progress_data)

    return json.dumps({
        "success": len(failed_items) == 0,
        "total_chapters": total,
        "published_count": success_count,
        "failed_count": len(failed_items),
        "failed_items": failed_items,
        "message": f"批量处理完成！成功: {success_count}/{total}"
    }, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_update_book_title(
    book_id: str,
    new_title: str,
    reason: str = "优化作品书名以契合后续故事发展"
) -> str:
    """
    修改指定作品的书名并提交平台审核。
    - book_id: 书籍唯一 ID
    - new_title: 新书名
    - reason: 修改书名理由（平台审核要求）
    """
    res = await fanqie_client.update_book_title(book_id=book_id, new_title=new_title, reason=reason)
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_update_book_cover(
    book_id: str,
    image_path: str
) -> str:
    """
    更换指定作品的封面图片并提交审核。
    自动检测图片尺寸比例，自动按番茄标准 3:4 比例裁剪优化后上传。
    - book_id: 书籍唯一 ID
    - image_path: 本地图片文件的绝对路径
    """
    res = await fanqie_client.update_book_cover(book_id=book_id, image_path=image_path)
    return json.dumps(res, ensure_ascii=False, indent=2)

@mcp.tool()
async def fanqie_get_batch_progress() -> str:
    """
    查询最近一次批量发文的执行进度与详细结果。
    """
    data = ChapterScheduler.load_progress()
    return json.dumps(data, ensure_ascii=False, indent=2)

if __name__ == "__main__":
    # 以标准 stdio 方式运行 MCP Server
    mcp.run(transport="stdio")
