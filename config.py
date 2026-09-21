"""
番茄作家助手 MCP 配置文件
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent

# 用户数据与会话存储路径 (持久化 Chromium 登录态)
SESSION_DIR = BASE_DIR / ".session"
SESSION_DIR.mkdir(parents=True, exist_ok=True)
USER_DATA_DIR = SESSION_DIR / "browser_profile"
STORAGE_STATE_FILE = SESSION_DIR / "storage_state.json"
QRCODE_IMAGE_PATH = SESSION_DIR / "login_qrcode.png"
BATCH_PROGRESS_FILE = SESSION_DIR / "batch_progress.json"

# 优先输出路径（遵循用户规范）
D_OUTPUT_DIR = Path(r"D:\AI-Outputs\Antigravity\fanqie-writer-mcp")
if D_OUTPUT_DIR.parent.parent.exists():
    OUTPUT_DIR = D_OUTPUT_DIR
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
else:
    OUTPUT_DIR = BASE_DIR / "outputs"
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# 平台 URL 定义
FANQIE_BASE_URL = "https://author.fanqienovel.com"
FANQIE_LOGIN_URL = f"{FANQIE_BASE_URL}/login"
FANQIE_HOME_URL = f"{FANQIE_BASE_URL}/page/home"
FANQIE_BOOK_LIST_URL = f"{FANQIE_BASE_URL}/page/book"
FANQIE_CHAPTER_CREATE_URL = f"{FANQIE_BASE_URL}/page/book/{{book_id}}/chapter/create"
FANQIE_BOOK_INFO_URL = f"{FANQIE_BASE_URL}/page/book/{{book_id}}/info"

# 浏览器设置
DEFAULT_HEADLESS = os.getenv("FANQIE_HEADLESS", "true").lower() in ("1", "true", "yes")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/131.0.0.0 Safari/537.36"
)

# 默认超时与间隔配置
PAGE_TIMEOUT_MS = 30000
ACTION_TIMEOUT_MS = 10000
DEFAULT_PUBLISH_INTERVAL_HOURS = 12.0
