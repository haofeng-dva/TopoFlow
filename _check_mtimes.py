import os, time
from pathlib import Path

root = Path(".")
files = []
for f in root.rglob("*"):
    if f.is_file() and "__pycache__" not in str(f):
        mtime = f.stat().st_mtime
        size = f.stat().st_size
        files.append((mtime, size, f.as_posix()))

files.sort(reverse=True)
print(f"{'修改时间':<16} {'大小':>8}  {'文件路径'}")
print("=" * 80)
for mtime, size, path in files:
    ts = time.strftime("%m-%d %H:%M", time.localtime(mtime))
    print(f"{ts:<16} {size:>8}B  {path}")
