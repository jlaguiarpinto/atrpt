# ponto.spec  —  PyInstaller spec para ponto.exe  (onefile / Miniconda)

from pathlib import Path
import sys

RAIZ = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt")

block_cipher = None

a = Analysis(
    [str(RAIZ / "ponto.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=[(str(RAIZ / "app.ini"), ".")],
    runtime_hooks=[],
    hiddenimports=[
        "tkinter", "tkinter.ttk", "tkinter.messagebox",
        "tkinter.filedialog", "tkinter.simpledialog",
        "pandas",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",
        "openpyxl", "openpyxl.styles", "openpyxl.utils",
        "openpyxl.workbook", "openpyxl.worksheet",
        "openpyxl.reader.excel", "openpyxl.writer.excel",
        "pyodbc", "sqlite3",
        "core.config", "core.logging_utils",
        "core.month_context", "core.paths",
        "infrastructure.logging.log_handler_gui",
        "infrastructure.persistence.user_repository",
        "infrastructure.persistence.pessoas.empregado_repository",
        "infrastructure.persistence.aprovisionamento.fornecedor_repository",
        "infrastructure.persistence.ponto.ponto_repository",
        "infrastructure.persistence.ponto.ponto_mapa_repository",
        "application.auth.login_usecase",
        "application.secretaria.processar_ponto_usecase",
        "domain.secretaria.ponto_processor",
        "presentation.shared.base_gui",
        "presentation.secretaria.ponto_controller",
        "presentation.secretaria.ponto_gui",
        "presentation.secretaria.ponto_resumo_mensal_view",
        "presentation.secretaria.ponto_resumo_empregado_view",
        "presentation.secretaria.ponto_emparelhamento_dialog",
    ],
    excludes=[
        "matplotlib", "scipy", "numpy.distutils",
        "IPython", "jupyter", "PIL",
        "test", "unittest", "setuptools", "pkg_resources",
        "presentation.secretaria.ponto_mapa_operacao_view",
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

# ── onefile ───────────────────────────────────────────────────────────────────
exe = EXE(
    pyz,
    a.scripts,
    a.binaries,      # binários embutidos no exe
    a.zipfiles,
    a.datas,
    [],
    name="ponto",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    # icon=str(RAIZ / "assets" / "ponto.ico"),
)
