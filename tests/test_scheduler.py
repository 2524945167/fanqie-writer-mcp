"""
调度器与文章切分单元测试
"""
import unittest
import shutil
from pathlib import Path
from core.scheduler import (
    chinese_to_number,
    extract_chapter_sort_key,
    ChapterScheduler,
)

class TestScheduler(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path(__file__).parent / "sample_chapters"
        self.test_dir.mkdir(parents=True, exist_ok=True)

        # 创建乱序命名的章节文件以测试排序
        (self.test_dir / "第10章_风暴前夕.txt").write_text("第10章 风暴前夕\n\n大风呼啸，山雨欲来...", encoding="utf-8")
        (self.test_dir / "第1章_初入仙途.txt").write_text("第1章 初入仙途\n\n天地不仁，以万物为刍狗...", encoding="utf-8")
        (self.test_dir / "第2章_灵脉觉醒.txt").write_text("第2章 灵脉觉醒\n\n少年双拳紧握，眸光如电...", encoding="utf-8")
        (self.test_dir / "第100章_大结局.txt").write_text("第100章 大结局\n\n终成大道，笑傲诸天。", encoding="utf-8")

        # 创建单文件小说
        self.single_novel_file = Path(__file__).parent / "sample_novel.txt"
        self.single_novel_file.write_text(
            "第1章 惊变\n\n这是第一章的内容。\n\n"
            "第2章 破晓\n\n这是第二章的内容。\n\n"
            "第3章 登峰\n\n这是第三章的内容。\n",
            encoding="utf-8"
        )

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)
        if self.single_novel_file.exists():
            self.single_novel_file.unlink()

    def test_chinese_to_number(self):
        self.assertEqual(chinese_to_number("一"), 1)
        self.assertEqual(chinese_to_number("十"), 10)
        self.assertEqual(chinese_to_number("十二"), 12)
        self.assertEqual(chinese_to_number("一百二十三"), 123)

    def test_sort_key(self):
        self.assertEqual(extract_chapter_sort_key("第1章"), 1)
        self.assertEqual(extract_chapter_sort_key("第10章"), 10)
        self.assertEqual(extract_chapter_sort_key("第十二章"), 12)

    def test_parse_directory_sorting(self):
        chapters = ChapterScheduler.parse_from_directory(self.test_dir)
        self.assertEqual(len(chapters), 4)
        titles = [ch["title"] for ch in chapters]
        self.assertEqual(titles[0], "第1章 初入仙途")
        self.assertEqual(titles[1], "第2章 灵脉觉醒")
        self.assertEqual(titles[2], "第10章 风暴前夕")
        self.assertEqual(titles[3], "第100章 大结局")

    def test_parse_single_file(self):
        chapters = ChapterScheduler.parse_from_single_file(self.single_novel_file)
        self.assertEqual(len(chapters), 3)
        self.assertEqual(chapters[0]["title"], "第1章 惊变")
        self.assertIn("这是第一章的内容", chapters[0]["content"])
        self.assertEqual(chapters[1]["title"], "第2章 破晓")
        self.assertEqual(chapters[2]["title"], "第3章 登峰")

    def test_calculate_schedule_daily_slots(self):
        chapters = [
            {"title": "第1章", "content": "c1"},
            {"title": "第2章", "content": "c2"},
            {"title": "第3章", "content": "c3"},
        ]
        # 设定每天 10:00 与 18:00 两更
        scheduled = ChapterScheduler.calculate_schedule(
            chapters=chapters,
            start_time="2026-10-01 08:00:00",
            daily_slots=["10:00", "18:00"]
        )
        self.assertEqual(len(scheduled), 3)
        self.assertEqual(scheduled[0]["publish_time"], "2026-10-01 10:00:00")
        self.assertEqual(scheduled[1]["publish_time"], "2026-10-01 18:00:00")
        self.assertEqual(scheduled[2]["publish_time"], "2026-10-02 10:00:00")

    def test_calculate_schedule_interval(self):
        chapters = [
            {"title": "第1章", "content": "c1"},
            {"title": "第2章", "content": "c2"},
        ]
        scheduled = ChapterScheduler.calculate_schedule(
            chapters=chapters,
            start_time="2026-10-01 12:00:00",
            interval_hours=6.0
        )
        self.assertEqual(scheduled[0]["publish_time"], "2026-10-01 12:00:00")
        self.assertEqual(scheduled[1]["publish_time"], "2026-10-01 18:00:00")

if __name__ == "__main__":
    unittest.main()
