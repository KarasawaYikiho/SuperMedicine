# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['..\\gui_standalone.py'],
    pathex=[],
    binaries=[],
    datas=[('D:\\GIT\\SuperMedicine\\core\\tui\\app.tcss', 'core\\tui'), ('D:\\GIT\\SuperMedicine\\assets', 'assets'), ('D:\\GIT\\SuperMedicine\\core\\web\\frontend', 'core\\web\\frontend')],
    hiddenimports=[],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='SuperMedicine',
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
    icon='..\\assets\\logo.ico',
)
