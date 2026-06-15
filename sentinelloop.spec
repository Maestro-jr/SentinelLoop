# PyInstaller spec — builds a single-file, offline SentinelLoop.exe (DEMO mode).
# Build:  pyinstaller sentinelloop.spec        (output: dist/SentinelLoop.exe)
# The bundled app ignores any .env (see config.py) and runs the full demo with
# zero setup — no Splunk, no MCP server, no API keys.

# -*- mode: python ; coding: utf-8 -*-
block_cipher = None

a = Analysis(
    ['run.py'],
    pathex=[],
    binaries=[],
    # Recorded fixtures power DEMO mode; they must travel with the app.
    datas=[('app/splunk/fixtures', 'app/splunk/fixtures')],
    # Lazy-imported modules so LIVE code is present even if a judge sets env vars.
    hiddenimports=['app.agent.autonomous', 'app.agent.llm', 'app.splunk.mcp_client'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    # Trim heavy/unused libs to keep the exe smaller (DEMO needs none of these).
    excludes=['mcp', 'anthropic', 'tkinter', 'matplotlib', 'numpy', 'pandas',
              'scipy', 'PIL', 'pytest'],
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
    name='SentinelLoop',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,          # windowed GUI app (no console window)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
