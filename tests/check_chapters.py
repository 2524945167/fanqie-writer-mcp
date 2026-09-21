import os
from pathlib import Path

base_dir = Path(r"D:\AI-Outputs\Antigravity\都市长篇_不肯散场_全本交付\分卷章节TXT")

vols = sorted([d for d in base_dir.iterdir() if d.is_dir()])
for v in vols:
    files = sorted([f for f in v.glob("*.txt")])
    print(f"Volume: {v.name}, chapters: {len(files)}")
    if files:
        sample = files[0]
        content = sample.read_text(encoding='utf-8')
        lines = [l for l in content.split('\n') if l.strip()]
        title_line = lines[0] if lines else ""
        print(f"  First file: {sample.name}, title_line: {title_line}, len: {len(content)} chars")
