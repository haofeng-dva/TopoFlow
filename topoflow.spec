# -*- mode: python ; coding: utf-8 -*-
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in ("gradio", "fastapi", "trimesh", "PIL", "toml"):
    d, b, h = collect_all(package)
    datas += d; binaries += b; hiddenimports += h
a = Analysis(["topoflow.py"], pathex=["."], binaries=binaries, datas=datas + [("config.toml.example", "."), ("README.md", ".")], hiddenimports=hiddenimports, excludes=["torch", "tensorflow", "jupyter"], noarchive=False)
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="TopoFlow", console=True)
coll = COLLECT(exe, a.binaries, a.datas, strip=False, upx=False, name="TopoFlow")

