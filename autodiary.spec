# -*- mode: python ; coding: utf-8 -*-
r"""
    _    ____  
   / \  |  _ \ 
  / _ \ | | | |
 / ___ \| |_| |
/_/   \_\____/ 
VTU Auto Diary Filler - PyInstaller Configuration
"""


a = Analysis(
    ['src/autodiary/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('src/autodiary/resources/templates', 'autodiary/resources/templates'),
        ('src/autodiary/resources/skills_mapping.json', 'autodiary/resources'),
    ],
    hiddenimports=[
        'requests',
        'typer',
        'rich',
        'rich.console',
        'rich.panel',
        'rich.table',
        'questionary',
        'cryptography',
        'cryptography.hazmat.backends.openssl',
        'pydantic',
        'pydantic_core',
        'pydantic.fields',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,

    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='AutoDiary',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='src/autodiary/resources/autodiary.ico',
)
