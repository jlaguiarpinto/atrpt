# atrpt/fornecedores.py
#
# App standalone de gestão da tabela de Fornecedores.
# Usa a mesma BD (atrpt.db) e as mesmas views do módulo de aprovisionamento,
# mas com um controller próprio e sem dependência do AprovisionamentoController.

import tkinter as tk
from pathlib import Path

from core.config import load_config, load_paths
from core.logging_utils import setup_logging, setup_audit_logger

from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.user_repository import UserRepository

from application.auth.login_usecase import LoginUseCase
from application.aprovisionamento.list_fornecedores_usecase import ListFornecedoresUseCase
from application.fornecedores.import_fornecedores_usecase import ImportFornecedoresFromExcelUseCase
from application.fornecedores.importar_efatura_usecase import ImportarEFaturaUseCase

from presentation.shared.base_gui import BaseGui as BG
from presentation.aprovisionamento.fornecedores_gui import FornecedoresGUI
from presentation.fornecedores.fornecedores_controller import FornecedoresController


_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")


class FornecedoresMainGUI(BG):
    """Janela raiz da app de fornecedores."""

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.set_title("Gestão de Fornecedores")
        self._build_main_menu()
        self._restore_root_menu = self._build_main_menu

    def _build_main_menu(self):
        self.abrir_work_area()
        opcoes = [
            ("Fornecedores",        self._open_fornecedores),
            ("Análise Faturação",   self._open_analise),
            ("Histórico Faturação", self._open_historico),
        ]
        self.build_menu_buttons(opcoes)

    def _open_fornecedores(self):
        self.show_view(FornecedoresGUI, self.controller)

    def _open_analise(self):
        from presentation.fornecedores.analise_fornecedores_gui import AnaliseFornecedoresGUI
        self.show_view(AnaliseFornecedoresGUI, self.controller)

    def _open_historico(self):
        from presentation.fornecedores.historico_faturacao_gui import HistoricoFaturacaoGUI
        self.show_view(HistoricoFaturacaoGUI, self.controller)


def main():
    root = tk.Tk()
    root.withdraw()
    root.title("ATRPT - Fornecedores")

    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum")
    setup_logging(cfg, "fornecedores")
    audit_log = setup_audit_logger(cfg, "fornecedores")

    db_path = cfg.paths["atrpt_db"]

    # ── Autenticação ──────────────────────────────────────────────────
    user_repo = UserRepository(db_path)
    login_uc = LoginUseCase(user_repo)
    user_context = login_uc.execute(root)
    root.deiconify()

    # ── Repositório e use cases ───────────────────────────────────────
    fornecedor_repo        = FornecedorRepository(db_path)
    list_fornecedores_uc   = ListFornecedoresUseCase(fornecedor_repo)
    import_fornecedores_uc = ImportFornecedoresFromExcelUseCase(fornecedor_repo)
    importar_efatura_uc    = ImportarEFaturaUseCase(db_path)

    # ── Controller ───────────────────────────────────────────────────
    controller = FornecedoresController(
        gui=None,                           # injectado após criação da GUI
        user_context=user_context,
        fornecedor_repo=fornecedor_repo,
        audit_log=audit_log,
        list_fornecedores_uc=list_fornecedores_uc,
        import_fornecedores_uc=import_fornecedores_uc,
        importar_efatura_uc=importar_efatura_uc,
    )

    # ── GUI ──────────────────────────────────────────────────────────
    gui = FornecedoresMainGUI(root, controller)
    controller.gui = gui

    root.mainloop()


if __name__ == "__main__":
    main()
