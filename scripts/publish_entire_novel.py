import asyncio
import sys
from pathlib import Path

# Add project root to sys.path
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from core.browser import BrowserManager
from core.session import SessionManager
from core.fanqie_client import FanqieClient

BOOK_ID = "7687873685029407806"
FOLDER = r"D:\AI-Outputs\Antigravity\都市长篇_不肯散场_全本交付\分卷章节TXT"

async def main():
    bm = BrowserManager(headless=True)
    sm = SessionManager(bm)
    client = FanqieClient(bm, sm)
    try:
        print(f"Starting whole novel volume publishing for book {BOOK_ID}...", flush=True)
        # We start from chapter 6 since chapters 1-5 are already uploaded
        res = await client.publish_volume_book(
            book_id=BOOK_ID,
            folder_path=FOLDER,
            mode="draft",
            start_chapter=6,
            delay_seconds=1.5
        )
        print("Final batch result:", res, flush=True)
    finally:
        await bm.close()

if __name__ == '__main__':
    asyncio.run(main())
