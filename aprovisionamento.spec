from PyInstaller.building.build_main import Analysis, PYZ, EXE

a = Analysis(
    ['aprovisionamento.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('templates/email/*.docx',                      'templates/email'),
        ('templates/email/aprovisionamento/*.docx',     'templates/email/aprovisionamento'),
    ],
    hiddenimports=[
        'tkinter', 'tkinter.ttk', 'tkinter.messagebox',
        'tkinter.filedialog', 'tkinter.simpledialog',
        'sqlite3',
        'docx', 'docx.oxml', 'docx.oxml.ns',
        'openpyxl', 'openpyxl.styles', 'openpyxl.utils',
        'smtplib', 'email', 'email.mime', 'email.mime.multipart',
        'email.mime.text', 'email.mime.base',
        'logging.handlers', 'getpass', 'configparser',
        'pathlib', 'dataclasses',
    ],
    excludes=['matplotlib', 'numpy', 'pandas', 'scipy', 'PIL', 'cv2', 'test', 'unittest'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
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
    name='aprovisionamento',
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
