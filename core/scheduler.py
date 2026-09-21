"""
章节解析与智能定时排期调度器
支持批量解析文件/全本、智能排期（每日固定时段/固定间隔）以及断点续传。
"""
import re
import os
import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Union

from config import BATCH_PROGRESS_FILE

def chinese_to_number(cn_str: str) -> int:
    """将中文数字转换为整数（支持 十、十二、一百二十三 等网文章节格式）"""
    if not cn_str:
        return 0
    if cn_str.isdigit():
        return int(cn_str)

    num_map = {
        '零': 0, '一': 1, '二': 2, '两': 2, '三': 3, '四': 4,
        '五': 5, '六': 6, '七': 7, '八': 8, '九': 9
    }
    unit_map = {'十': 10, '百': 100, '千': 1000, '万': 10000}

    total = 0
    r = 0
    for char in cn_str:
        if char in num_map:
            r = num_map[char]
        elif char in unit_map:
            unit = unit_map[char]
            if unit == 10000:
                total = (total + (r if r else 1)) * unit
                r = 0
            else:
                total += (r if r != 0 else 1) * unit
                r = 0
        else:
            continue
    total += r
    return total

def extract_chapter_sort_key(name: str) -> int:
    """提取章节序号作为排序权重"""
    # 匹配阿拉伯数字: 001, 1, 12 等
    match = re.search(r'第?(\d+)[章回节卷集幕篇部]?', name)
    if match:
        return int(match.group(1))
    
    # 匹配中文数字: 第一百二十章
    match_cn = re.search(r'第([零一二三四五六七八九十百千万]+)[章回节卷集幕篇部]', name)
    if match_cn:
        return chinese_to_number(match_cn.group(1))
    
    # 纯数字开头: 01.txt, 1.txt
    match_prefix = re.match(r'^(\d+)', name)
    if match_prefix:
        return int(match_prefix.group(1))
    
    return 999999

class ChapterScheduler:
    """批量文章处理与定时排期器"""

    @staticmethod
    def parse_from_directory(dir_path: Union[str, Path]) -> List[Dict[str, str]]:
        """从目录批量读取所有章节文件（支持 .txt 与 .md）"""
        path = Path(dir_path)
        if not path.is_dir():
            raise FileNotFoundError(f"指定的章节目录不存在: {dir_path}")

        files = [
            f for f in path.iterdir()
            if f.is_file() and f.suffix.lower() in ('.txt', '.md')
        ]
        if not files:
            raise ValueError(f"目录 {dir_path} 下未找到任何 .txt 或 .md 文件")

        # 按章节序号自然排序
        files.sort(key=lambda f: (extract_chapter_sort_key(f.stem), f.stem))

        chapters = []
        for file in files:
            try:
                content = file.read_text(encoding='utf-8').strip()
            except UnicodeDecodeError:
                content = file.read_text(encoding='gb18030', errors='ignore').strip()

            title = file.stem
            # 如果第一行是标题形式，优先提取第一行为标题
            lines = content.splitlines()
            if lines and re.match(r'^(第[0-9一二三四五六七八九十百千万]+[章回节卷集幕篇部].*)$', lines[0].strip()):
                title = lines[0].strip()
                content = "\n".join(lines[1:]).strip()

            chapters.append({
                "title": title,
                "content": content,
                "source_file": str(file)
            })

        return chapters

    @staticmethod
    def parse_from_single_file(file_path: Union[str, Path]) -> List[Dict[str, str]]:
        """从单个全本小说文本中切分出各章节"""
        path = Path(file_path)
        if not path.is_file():
            raise FileNotFoundError(f"小说文件不存在: {file_path}")

        try:
            text = path.read_text(encoding='utf-8')
        except UnicodeDecodeError:
            text = path.read_text(encoding='gb18030', errors='ignore')

        # 匹配标准章节头
        pattern = re.compile(r'(?m)^(第[0-9一二三四五六七八九十百千万\d]+[章回节卷集幕篇部][^\n\r]{0,40})$')
        matches = list(pattern.finditer(text))

        if not matches:
            raise ValueError(f"在文件 {file_path} 中未匹配到任何标准章节标题（例如：'第1章 ...'）")

        chapters = []
        for i, match in enumerate(matches):
            title = match.group(1).strip()
            start_pos = match.end()
            end_pos = matches[i + 1].start() if i + 1 < len(matches) else len(text)
            content = text[start_pos:end_pos].strip()

            chapters.append({
                "title": title,
                "content": content,
                "source_file": str(path)
            })

        return chapters

    @staticmethod
    def calculate_schedule(
        chapters: List[Dict[str, str]],
        start_time: Optional[str] = None,
        daily_slots: Optional[List[str]] = None,
        interval_hours: Optional[float] = None
    ) -> List[Dict[str, Any]]:
        """
        为章节列表自动生成定时发布排期
        - daily_slots: 每日固定发文时段，例如 ["10:00", "14:00", "18:00"]
        - interval_hours: 固定间隔小时数，例如 12.0
        """
        # 确定起始基准时间
        now = datetime.now()
        if start_time:
            try:
                base_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M:%S")
            except ValueError:
                base_dt = datetime.strptime(start_time, "%Y-%m-%d %H:%M")
        else:
            # 默认从明天上午 10:00 开始
            tomorrow = now + timedelta(days=1)
            base_dt = datetime(tomorrow.year, tomorrow.month, tomorrow.day, 10, 0, 0)

        scheduled_list = []

        if daily_slots and len(daily_slots) > 0:
            # 模式 A: 每日固定档期 (如每日 10:00, 18:00)
            slots = sorted(daily_slots)
            current_day = base_dt.date()
            slot_idx = 0

            # 找到首个大于等于 base_dt 的档期
            for idx, slot in enumerate(slots):
                sh, sm = map(int, slot.split(':'))
                slot_dt = datetime.combine(current_day, datetime.min.time()).replace(hour=sh, minute=sm)
                if slot_dt >= base_dt:
                    slot_idx = idx
                    break
            else:
                current_day += timedelta(days=1)
                slot_idx = 0

            for ch in chapters:
                sh, sm = map(int, slots[slot_idx].split(':'))
                target_dt = datetime.combine(current_day, datetime.min.time()).replace(hour=sh, minute=sm)
                
                scheduled_list.append({
                    **ch,
                    "publish_time": target_dt.strftime("%Y-%m-%d %H:%M:%S")
                })

                slot_idx += 1
                if slot_idx >= len(slots):
                    slot_idx = 0
                    current_day += timedelta(days=1)
        else:
            # 模式 B: 固定间隔小时 (默认 12 小时)
            step_hours = interval_hours if interval_hours and interval_hours > 0 else 12.0
            current_dt = base_dt

            for ch in chapters:
                scheduled_list.append({
                    **ch,
                    "publish_time": current_dt.strftime("%Y-%m-%d %H:%M:%S")
                })
                current_dt += timedelta(hours=step_hours)

        return scheduled_list

    @staticmethod
    def load_progress() -> Dict[str, Any]:
        """读取批处理进度"""
        if BATCH_PROGRESS_FILE.exists():
            try:
                return json.loads(BATCH_PROGRESS_FILE.read_text(encoding='utf-8'))
            except Exception:
                pass
        return {}

    @staticmethod
    def save_progress(data: Dict[str, Any]):
        """保存批处理进度"""
        BATCH_PROGRESS_FILE.parent.mkdir(parents=True, exist_ok=True)
        BATCH_PROGRESS_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
