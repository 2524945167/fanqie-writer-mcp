import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from core.browser import BrowserManager
from core.session import SessionManager
from core.fanqie_client import FanqieClient

BOOK_ID = "7687873685029407806"
FOLDER = r"D:\AI-Outputs\Antigravity\都市长篇_不肯散场_全本交付\分卷章节TXT"

async def test():
    bm = BrowserManager(headless=True)
    sm = SessionManager(bm)
    client = FanqieClient(bm, sm)
    try:
        # Test chapters 4 and 5 in draft mode
        res = await client.publish_volume_book(
            book_id=BOOK_ID,
            folder_path=FOLDER,
            mode="draft",
            start_chapter=4,
            max_chapters=2,
            delay_seconds=1.0
        )
        print("Test result:", res)
    finally:
        await bm.close()

if __name__ == '__main__':
    asyncio.run(test())
