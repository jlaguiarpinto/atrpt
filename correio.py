# atrpt/correio.py
#
# App standalone para leitura da caixa de correio da Secretaria (IMAP).
# Credenciais lidas de [email.secretaria] em app.ini.

import tkinter as tk
from pathlib import Path

from core.config import load_config, load_paths
from core.logging_utils import setup_logging

from infrastructure.email.imap_client import ImapClient
from infrastructure.persistence.user_repository import UserRepository
from application.auth.login_usecase import LoginUseCase

from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.aprovisionamento.faturacao_fornecedores_repository import FaturacaoFornecedoresRepository

from presentation.shared.base_gui import BaseGui as BG
from presentation.correio.correio_controller import CorreioController
from presentation.correio.correio_gui import CorreioGUI
from presentation.correio.selecao_pasta_gui import SelecaoPastaGUI
from presentation.correio.analise_correio_gui import AnaliseCorreioGUI
from presentation.correio.guardar_pdfs_gui import GuardarPdfsGUI
from presentation.correio.faturas_gui import FaturasGUI
from presentation.correio.recolher_dados_gui import RecolherDadosGUI


_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")
PASTA_FATURAS = Path(r"G:\.shortcut-targets-by-id\1Qr9fyP5j561vVIXw8b6mKJvgTyhTQF14\Secretaria\Faturas")


class CorreioMainGUI(BG):

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.set_title("Correio — Secretaria")
        self._build_main_menu()
        self._restore_root_menu = self._build_main_menu

    def _build_main_menu(self):
        self.abrir_work_area()
        self.build_menu_buttons([
            ("Caixa de Correio",   self._open_correio),
            ("Selecionar Pasta",   self._open_selecao_pasta),
            ("Análise da Caixa",   self._open_analise),
            ("Guardar PDFs",       self._open_guardar_pdfs),
            ("Ler Faturas",        self._open_faturas),
            ("Recolher Dados",     self._open_recolher_dados),
        ])

    def _open_correio(self):
        self.show_view(CorreioGUI, self.controller)

    def _open_selecao_pasta(self):
        self.show_view(SelecaoPastaGUI, self.controller)

    def _open_analise(self):
        self.show_view(AnaliseCorreioGUI, self.controller)

    def _open_guardar_pdfs(self):
        self.show_view(GuardarPdfsGUI, self.controller)

    def _open_faturas(self):
        self.show_view(FaturasGUI, self.controller)

    def _open_recolher_dados(self):
        self.show_view(RecolherDadosGUI, self.controller)


def main():
    root = tk.Tk()
    root.withdraw()
    root.title("ATRPT - Correio")

    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum")
    setup_logging(cfg, "correio")

    db_path = cfg.paths["atrpt_db"]

    # ── Autenticação ─────────────────────────────────────────────────
    user_repo    = UserRepository(db_path)
    login_uc     = LoginUseCase(user_repo)
    user_context = login_uc.execute(root)
    root.deiconify()

    # ── IMAP — credenciais de [email.secretaria] ──────────────────────
    perfil = cfg.emails["secretaria"]
    imap_client = ImapClient(
        host=perfil.imap_server,
        port=perfil.imap_port,
        user=perfil.imap_user,
        password=perfil.imap_password,
        ssl=perfil.imap_ssl,
    )

    # ── Repositórios ──────────────────────────────────────────────────
    fornecedor_repo  = FornecedorRepository(db_path)
    faturacao_repo   = FaturacaoFornecedoresRepository(db_path)

    # ── Controller + GUI ──────────────────────────────────────────────
    controller = CorreioController(
        gui=None,
        imap_client=imap_client,
        fornecedor_repo=fornecedor_repo,
        faturacao_repo=faturacao_repo,
        pasta_faturas=PASTA_FATURAS,
        nif_proprio=cfg.nif_proprio,
    )
    gui = CorreioMainGUI(root, controller)
    controller.gui = gui

    root.mainloop()


if __name__ == "__main__":
    main()
