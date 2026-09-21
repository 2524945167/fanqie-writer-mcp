"""
番茄作家助手登录态与会话管理
"""
import asyncio
import json
from typing import Dict, Any, Optional
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError

from config import (
    FANQIE_HOME_URL,
    FANQIE_LOGIN_URL,
    FANQIE_BOOK_LIST_URL,
    STORAGE_STATE_FILE,
    QRCODE_IMAGE_PATH,
    OUTPUT_DIR,
)
from core.browser import BrowserManager

class SessionManager:
    """管理作者后台登录凭证、状态检测及扫码流程"""

    def __init__(self, browser_mgr: BrowserManager):
        self.browser_mgr = browser_mgr

    async def check_login_status(self, page: Optional[Page] = None) -> Dict[str, Any]:
        """
        检查当前持久化会话是否有效
        返回: {"logged_in": bool, "author_name": Optional[str], "message": str}
        """
        should_close = False
        if page is None:
            page = await self.browser_mgr.new_page(headless=True)
            should_close = True

        try:
            await page.goto(FANQIE_HOME_URL, wait_until="domcontentloaded", timeout=15000)
            await asyncio.sleep(1.5)
            current_url = page.url

            # 若被重定向到 login 页面说明未登录
            if "/login" in current_url:
                return {
                    "logged_in": False,
                    "author_name": None,
                    "message": "未登录或登录态已失效，请先执行登录",
                }

            # 提取作者昵称或头像特征
            author_name = None
            author_selectors = [
                ".user-name",
                ".author-name",
                ".header-user-info span",
                ".arco-avatar + span",
                ".semi-avatar + span",
                "span[class*='name']",
                "[class*='author']",
            ]
            for sel in author_selectors:
                try:
                    el = await page.query_selector(sel)
                    if el:
                        text = (await el.inner_text()).strip()
                        if text and len(text) < 30:
                            author_name = text
                            break
                except Exception:
                    continue

            return {
                "logged_in": True,
                "author_name": author_name or "已登录作家",
                "message": "登录态有效",
            }
        except Exception as e:
            # 尝试访问作品列表页作兜底检测
            try:
                await page.goto(FANQIE_BOOK_LIST_URL, wait_until="domcontentloaded", timeout=10000)
                await asyncio.sleep(1)
                if "/login" not in page.url:
                    return {
                        "logged_in": True,
                        "author_name": "已登录作家",
                        "message": "登录态有效",
                    }
            except Exception:
                pass
            return {
                "logged_in": False,
                "author_name": None,
                "message": f"登录态检测失败: {str(e)}",
            }
        finally:
            if should_close:
                await page.close()

    async def login_interactive(self, timeout_sec: int = 180) -> Dict[str, Any]:
        """
        打开可视化 Chromium 窗口供用户扫码或手机验证码登录
        """
        # 关闭已有的后台持久化会话以便重新以有头模式启动
        await self.browser_mgr.close()
        page = await self.browser_mgr.new_page(headless=False)

        try:
            await page.goto(FANQIE_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)

            # 自动切换到“扫码登录”选项卡
            try:
                qr_tab = await page.query_selector("text='扫码登录'")
                if qr_tab:
                    await qr_tab.click()
            except Exception:
                pass

            print(f"请在弹出的浏览器窗口中完成番茄作家助手扫码登录（限时 {timeout_sec} 秒）...")

            # 等待跳转至管理后台页面（例如 /home 或 /book）
            for _ in range(timeout_sec):
                await asyncio.sleep(1)
                current_url = page.url
                if "/login" not in current_url and ("fanqienovel.com/main/writer" in current_url or "/page/" in current_url):
                    # 登录成功，提取信息
                    status = await self.check_login_status(page=page)
                    # 保存 storage_state
                    context = page.context
                    await context.storage_state(path=str(STORAGE_STATE_FILE))
                    return {
                        "success": True,
                        "author_name": status.get("author_name"),
                        "message": "登录成功！登录凭据已安全持久化到本地。",
                    }

            return {
                "success": False,
                "author_name": None,
                "message": "登录超时，未在指定时间内完成扫码登录",
            }
        except Exception as e:
            return {
                "success": False,
                "author_name": None,
                "message": f"交互登录异常: {str(e)}",
            }
        finally:
            await page.close()
            # 恢复为后台 headless 模式待命
            await self.browser_mgr.close()

    async def get_login_qrcode(self) -> Dict[str, Any]:
        """
        无头模式下截取登录二维码图片保存到本地供手机扫码
        """
        page = await self.browser_mgr.new_page(headless=True)
        try:
            await page.goto(FANQIE_LOGIN_URL, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(1)

            # 自动切换到“扫码登录”选项卡
            try:
                qr_tab = await page.query_selector("text='扫码登录'")
                if qr_tab:
                    await qr_tab.click()
                    await asyncio.sleep(1)
            except Exception:
                pass

            # 寻找二维码图片或容器元素
            qrcode_selectors = [
                "img[src*='qrcode']",
                ".qrcode-image",
                ".qrcode-wrapper img",
                ".byte-login-qrcode img",
                "canvas",
                ".qrcode-box",
            ]
            qrcode_el = None
            for sel in qrcode_selectors:
                qrcode_el = await page.query_selector(sel)
                if qrcode_el:
                    break

            # 目标保存路径
            target_path = OUTPUT_DIR / "fanqie_login_qrcode.png"

            if qrcode_el:
                await qrcode_el.screenshot(path=str(target_path))
            else:
                # 截取整个登录框作为兜底
                await page.screenshot(path=str(target_path), full_page=False)

            return {
                "success": True,
                "qrcode_path": str(target_path),
                "message": f"登录二维码已保存至: {target_path}。请使用番茄小说或番茄作家助手扫码后验证。",
            }
        except Exception as e:
            return {
                "success": False,
                "qrcode_path": None,
                "message": f"获取二维码失败: {str(e)}",
            }
        finally:
            await page.close()
