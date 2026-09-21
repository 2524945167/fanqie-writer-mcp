"""
无头扫码登录处理器
保持浏览器连接打开并监听扫码事件，同时将二维码输出到指定图片路径
"""
import asyncio
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from config import (
    FANQIE_LOGIN_URL,
    STORAGE_STATE_FILE,
    OUTPUT_DIR,
)
from core.browser import BrowserManager
from core.session import SessionManager

async def run_headless_qr_login(qr_output_path: Path, timeout_sec: int = 180):
    bm = BrowserManager(headless=True)
    page = await bm.new_page()
    try:
        print(f"[1/4] 正在加载番茄登录页面: {FANQIE_LOGIN_URL} ...", flush=True)
        await page.goto(FANQIE_LOGIN_URL, wait_until="domcontentloaded", timeout=25000)
        await asyncio.sleep(1.5)

        # 切换到扫码登录
        print("[2/4] 正在切换至扫码登录选项卡...", flush=True)
        try:
            qr_tab = await page.query_selector("text='扫码登录'")
            if qr_tab:
                await qr_tab.click()
                await asyncio.sleep(1.5)
        except Exception as e:
            print(f"切换扫码选项卡提示: {e}", flush=True)

        # 截取登录二维码
        print(f"[3/4] 正在截取登录二维码至: {qr_output_path} ...", flush=True)
        qr_output_path.parent.mkdir(parents=True, exist_ok=True)

        # 优先截取中间的卡片区域或二维码
        card_el = await page.query_selector(".login-card, [class*='login-box'], [class*='card'], .login-container")
        if card_el:
            await card_el.screenshot(path=str(qr_output_path))
        else:
            await page.screenshot(path=str(qr_output_path), full_page=False)

        print("[READY_FOR_SCAN] 最新二维码已就绪！正在实时监听扫码授权...", flush=True)

        last_refresh = 0
        # 持续轮询是否已扫码成功跳转
        for sec in range(timeout_sec):
            await asyncio.sleep(2)
            current_url = page.url
            if "/login" not in current_url and ("fanqienovel.com/main/writer" in current_url or "/page/" in current_url):
                print(f"[SUCCESS] 检测到页面跳转: {current_url}，扫码登录成功！", flush=True)
                # 保存 storage_state
                context = page.context
                await context.storage_state(path=str(STORAGE_STATE_FILE))
                print(f"[SAVED] 凭据已成功保存到: {STORAGE_STATE_FILE}", flush=True)
                return True

            # 检查是否有“点击刷新”/“已失效”提示，或每隔 45 秒主动刷新一次
            need_refresh = False
            refresh_btn = await page.query_selector("text='刷新', text='点击刷新', .refresh-mask, [class*='refresh']")
            if refresh_btn:
                try:
                    await refresh_btn.click()
                    need_refresh = True
                except Exception:
                    pass

            if (sec - last_refresh) >= 22 or need_refresh:  # 约 45 秒
                last_refresh = sec
                # 重新聚焦并截图
                try:
                    if not need_refresh:
                        # 尝试点击扫码 tab 刷新
                        qr_tab = await page.query_selector("text='扫码登录'")
                        if qr_tab:
                            await qr_tab.click()
                    await asyncio.sleep(1)
                    if card_el:
                        await card_el.screenshot(path=str(qr_output_path))
                    else:
                        await page.screenshot(path=str(qr_output_path), full_page=False)
                    print(f"[REFRESH] 已自动刷新并更新二维码图片 (已等待 {sec * 2} 秒)", flush=True)
                except Exception as e:
                    pass

            # 每 20 秒打印一次心跳
            if sec % 10 == 0 and sec > 0:
                print(f"[WAITING] 正在等待扫码确认... (剩余 {timeout_sec - sec * 2} 秒)", flush=True)

        print("[TIMEOUT] 扫码等待超时", flush=True)
        return False
    except Exception as e:
        print(f"[ERROR] 扫码登录流程异常: {e}", flush=True)
        return False
    finally:
        await page.close()
        await bm.close()

if __name__ == "__main__":
    target = Path(sys.argv[1]) if len(sys.argv) > 1 else OUTPUT_DIR / "login_qrcode.png"
    asyncio.run(run_headless_qr_login(target))
