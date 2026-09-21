"""
Playwright 浏览器与反检测驱动模块
"""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from config import STORAGE_STATE_FILE, USER_AGENT, DEFAULT_HEADLESS, PAGE_TIMEOUT_MS

STEALTH_INIT_SCRIPT = """
(() => {
    // 隐藏 webdriver 特征
    Object.defineProperty(navigator, 'webdriver', {
        get: () => undefined
    });

    // 伪装 chrome 对象
    window.chrome = {
        runtime: {},
        loadTimes: function() {},
        csi: function() {},
        app: {}
    };

    // 伪装插件列表
    Object.defineProperty(navigator, 'plugins', {
        get: () => [1, 2, 3, 4, 5]
    });

    // 默认中文语言环境
    Object.defineProperty(navigator, 'languages', {
        get: () => ['zh-CN', 'zh', 'en']
    });

    // 伪装权限 API
    const originalQuery = window.navigator.permissions.query;
    window.navigator.permissions.query = (parameters) => (
        parameters.name === 'notifications' ?
            Promise.resolve({ state: Notification.permission }) :
            originalQuery(parameters)
    );
})();
"""

class BrowserManager:
    """管理 Playwright 浏览器实例并自动加载 storage_state 登录凭据"""

    def __init__(self, headless: bool = DEFAULT_HEADLESS):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._browser = None

    async def get_browser(self, headless: Optional[bool] = None):
        target_headless = self.headless if headless is None else headless
        if not self._playwright:
            self._playwright = await async_playwright().start()
        if not self._browser or not self._browser.is_connected():
            self._browser = await self._playwright.chromium.launch(
                headless=target_headless,
                args=[
                    "--disable-blink-features=AutomationControlled",
                    "--no-sandbox",
                    "--disable-infobars",
                    "--lang=zh-CN",
                ],
            )
        return self._browser

    async def get_context(self, headless: Optional[bool] = None) -> BrowserContext:
        """创建注入反检测和登录态的 Context"""
        browser = await self.get_browser(headless=headless)
        kwargs = {
            "user_agent": USER_AGENT,
            "viewport": {"width": 1280, "height": 800},
        }
        if STORAGE_STATE_FILE.exists() and STORAGE_STATE_FILE.stat().st_size > 10:
            kwargs["storage_state"] = str(STORAGE_STATE_FILE)
        context = await browser.new_context(**kwargs)
        context.set_default_timeout(PAGE_TIMEOUT_MS)
        return context

    async def new_page(self, headless: Optional[bool] = None) -> Page:
        """创建注入了反检测脚本与登录态的新标签页"""
        context = await self.get_context(headless=headless)
        page = await context.new_page()
        await page.add_init_script(STEALTH_INIT_SCRIPT)
        return page

    async def close(self):
        """关闭浏览器与 Playwright 进程"""
        if self._browser:
            try:
                await self._browser.close()
            except Exception:
                pass
            self._browser = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
