"""
Playwright 浏览器与反检测驱动模块
"""
import asyncio
from typing import Optional
from playwright.async_api import async_playwright, BrowserContext, Page, Playwright
from config import USER_DATA_DIR, USER_AGENT, DEFAULT_HEADLESS, PAGE_TIMEOUT_MS

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
    """管理持久化 Playwright 浏览器实例"""

    def __init__(self, headless: bool = DEFAULT_HEADLESS):
        self.headless = headless
        self._playwright: Optional[Playwright] = None
        self._context: Optional[BrowserContext] = None

    async def get_context(self, headless: Optional[bool] = None) -> BrowserContext:
        """获取或创建持久化 BrowserContext"""
        target_headless = self.headless if headless is None else headless
        
        # 如果上下文存在但 headless 需求变化，先关闭重建
        if self._context:
            return self._context

        if not self._playwright:
            self._playwright = await async_playwright().start()

        USER_DATA_DIR.mkdir(parents=True, exist_ok=True)

        self._context = await self._playwright.chromium.launch_persistent_context(
            user_data_dir=str(USER_DATA_DIR),
            headless=target_headless,
            user_agent=USER_AGENT,
            viewport={"width": 1280, "height": 800},
            args=[
                "--disable-blink-features=AutomationControlled",
                "--no-sandbox",
                "--disable-infobars",
                "--lang=zh-CN",
            ],
            ignore_default_args=["--enable-automation"],
        )
        self._context.set_default_timeout(PAGE_TIMEOUT_MS)
        return self._context

    async def new_page(self, headless: Optional[bool] = None) -> Page:
        """创建注入了反检测脚本的新标签页"""
        context = await self.get_context(headless=headless)
        page = await context.new_page()
        await page.add_init_script(STEALTH_INIT_SCRIPT)
        return page

    async def close(self):
        """关闭上下文与 Playwright 进程"""
        if self._context:
            try:
                await self._context.close()
            except Exception:
                pass
            self._context = None
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception:
                pass
            self._playwright = None
