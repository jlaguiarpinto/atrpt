from PyInstaller.building.build_main import Analysis, PYZ, EXE

a = Analysis(
    ['pessoas.py'],
    pathex=['.'],
    binaries=[],

    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'tkinter.filedialog', 'tkinter.simpledialog',
        'sqlite3',
        'pyodbc',
        'logging.handlers', 'getpass', 'configparser',
        'pathlib', 'dataclasses', 'decimal',
    ],
    excludes=[
        'matplotlib', 'numpy', 'pandas', 'scipy',
        'PIL', 'cv2', 'test', 'unittest',
        'IPython', 'jupyter', 'openpyxl', 'docx',
        'smtplib', 'xmlrpc', 'ftplib', 'telnetlib',
        'curses', 'readline',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    noarchive=False,
    optimize=1,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='pessoas',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
