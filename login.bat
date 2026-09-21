@echo off
chcp 65001 >nul
title 番茄作家助手 - 扫码登录
cd /d "%~dp0"
echo ========================================================
echo   番茄作家助手 MCP 登录助手
echo   正在启动独立浏览器窗口，请稍候...
echo ========================================================
"C:\Users\Kupetis\AppData\Local\Python\pythoncore-3.14-64\python.exe" -c "import asyncio; from core.browser import BrowserManager; from core.session import SessionManager; bm = BrowserManager(headless=False); sm = SessionManager(bm); res = asyncio.run(sm.login_interactive(timeout_sec=300)); print(res)"
echo.
echo 登录流程已结束。按任意键退出...
pause >nul
