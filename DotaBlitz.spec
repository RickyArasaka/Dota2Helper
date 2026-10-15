# -*- mode: python ; coding: utf-8 -*-

from pathlib import Path
import sys

block_cipher = None
project_root = Path.cwd()

# Data files to embed into the executable
datas = [
    (str(project_root / 'src' / 'frontend'), 'src/frontend'),
    (str(project_root / 'data' / 'gsi'), 'data/gsi'),
]

# Hidden imports that PyInstaller might miss with dynamic loading
hiddenimports = [
    'uvicorn',
    'uvicorn.logging',
    'uvicorn.loops',
    'uvicorn.loops.auto',
    'uvicorn.protocols',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.auto',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.lifespan',
    'uvicorn.lifespan.on',
    'fastapi',
    'fastapi.staticfiles',
    'fastapi.middleware.cors',
    'sqlalchemy.dialects.sqlite',
    'sqlalchemy.dialects.sqlite.aiosqlite',
    'aiosqlite',
    'sqlite3',
    'apscheduler',
    'apscheduler.schedulers.asyncio',
    'pydantic',
    'pydantic_settings',
    'httpx',
    'bs4',
    'lxml',
    'jinja2',
    'webview',
]

a = Analysis(
    ['desktop.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['tkinter', 'matplotlib', 'numpy', 'scipy'],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='DotaBlitz',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
