# secretaria.spec  —  PyInstaller spec para secretaria.exe  (Miniconda / conda env atrpt)
#
# Uso:   python utils\build.py secretaria
# Saída: dist\secretaria.exe

from pathlib import Path
import sys, shutil

RAIZ    = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt")
ENV_DIR = Path(sys.base_prefix)

block_cipher = None

a = Analysis(
    [str(RAIZ / "secretaria.py")],
    pathex=[str(RAIZ)],
    binaries=[],
    datas=[(str(RAIZ / "app.ini"), ".")],
    runtime_hooks=[],
    hiddenimports=[
        # tkinter
        "tkinter", "tkinter.ttk", "tkinter.messagebox",
        "tkinter.filedialog", "tkinter.simpledialog",

        # pandas
        "pandas",
        "pandas._libs.tslibs.np_datetime",
        "pandas._libs.tslibs.nattype",
        "pandas._libs.tslibs.timedeltas",
        "pandas._libs.tslibs.timestamps",

        # openpyxl
        "openpyxl", "openpyxl.styles", "openpyxl.utils",
        "openpyxl.workbook", "openpyxl.worksheet",
        "openpyxl.reader.excel", "openpyxl.writer.excel",

        # word (templates .docx)
        "docx", "docx.document", "docx.oxml",

        # email
        "smtplib", "email", "email.mime",
        "email.mime.multipart", "email.mime.text",
        "email.mime.base", "email.mime.image",

        # db
        "pyodbc", "sqlite3",

        # core
        "core.config", "core.logging_utils",
        "core.month_context", "core.paths",

        # infrastructure — email
        "infrastructure.email.smtp_client",
        "infrastructure.email.emailer",
        "infrastructure.system.power_management",

        # infrastructure — persistence
        "infrastructure.persistence.user_repository",
        "infrastructure.persistence.pessoas.empregado_repository",
        "infrastructure.persistence.aprovisionamento.fornecedor_repository",
        "infrastructure.persistence.ponto.ponto_repository",
        "infrastructure.persistence.ponto.ponto_mapa_repository",
        "infrastructure.persistence.secretaria.residentes_repository",
        "infrastructure.persistence.secretaria.contacorrente_repository",
        "infrastructure.persistence.secretaria.inflow_repository",
        "infrastructure.persistence.secretaria.pim_repository",

        # application — auth
        "application.auth.login_usecase",

        # application — email
        "application.email.email_message",
        "application.email.email_builder",
        "application.email.email_sender",
        "application.email.email_service",
        "application.email.email_template_builder",
        "application.email.template_utils",
        "application.email.word_template_loader",
        "application.email.enviar_doc_usecase",

        # application — secretaria
        "application.secretaria.processar_ponto_usecase",
        "application.secretaria.tesouraria_service",

        # presentation — shared
        "infrastructure.logging.log_handler_gui",
        "presentation.shared.base_gui",

        # presentation — secretaria
        "presentation.secretaria.secretaria_controller",
        "presentation.secretaria.secretaria_gui",
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

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name="secretaria",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    # icon=str(RAIZ / "assets" / "secretaria.ico"),
)

# ── Pós-build: copiar python311.dll para dist\ ────────────────────────────────
import os
_dist = RAIZ / "dist"
_dlls = ["python3.dll", "python311.dll", "vcruntime140.dll",
         "vcruntime140_1.dll", "msvcp140.dll"]

print("\n[pós-build] A copiar DLLs do runtime...")
for nome in _dlls:
    origem  = ENV_DIR / nome
    destino = _dist / nome
    if origem.exists():
        shutil.copy2(str(origem), str(destino))
        print(f"  OK  {nome}")
    else:
        print(f"  --  {nome}  (não existe)")
