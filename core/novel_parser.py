import re
from pathlib import Path

base_dir = Path(r"D:\AI-Outputs\Antigravity\都市长篇_不肯散场_全本交付\分卷章节TXT")

def get_novel_tree():
    volumes = []
    # Sort folders by volume number
    vol_dirs = [d for d in base_dir.iterdir() if d.is_dir()]
    def vol_sort_key(d):
        m = re.search(r'卷([一二三四五六七八九十]+|\d+)', d.name)
        cn_nums = {"一": 1, "二": 2, "三": 3, "四": 4, "五": 5, "六": 6, "七": 7, "八": 8, "九": 9, "十": 10}
        if m:
            val = m.group(1)
            return cn_nums.get(val, int(val) if val.isdigit() else 999)
        return 999

    vol_dirs.sort(key=vol_sort_key)
    for vd in vol_dirs:
        # Extract volume title after underscore or prefix
        # e.g. "卷一_这笔账先算清" -> "这笔账先算清"
        vol_clean_name = vd.name.split("_", 1)[-1] if "_" in vd.name else vd.name
        ch_files = sorted(list(vd.glob("*.txt")), key=lambda f: int(re.search(r'\d+', f.name).group(0)) if re.search(r'\d+', f.name) else 0)
        volumes.append({
            "dir_name": vd.name,
            "volume_title": vol_clean_name,
            "chapters": ch_files
        })
    return volumes

if __name__ == '__main__':
    vols = get_novel_tree()
    print(f"Total volumes: {len(vols)}")
    for v in vols:
        print(f"Volume: {v['volume_title']} ({v['dir_name']}), chapters: {len(v['chapters'])}")
        if v['chapters']:
            print(f"  First: {v['chapters'][0].name}")
            print(f"  Last:  {v['chapters'][-1].name}")
