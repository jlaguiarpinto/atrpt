# atrpt/ponto.py
"""
Ponto de entrada autónomo para o módulo de Registo de Ponto.
Pode ser lançado independentemente sem carregar o resto da Secretaria.
"""

import tkinter as tk
from pathlib import Path
import warnings

from core.config import load_config
from core.logging_utils import setup_logging

# repos necessários ao módulo de ponto
from infrastructure.persistence.pessoas.empregado_repository import EmpregadoRepository
from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.ponto.ponto_mapa_repository import PontoMapaRepository
from infrastructure.persistence.user_repository import UserRepository

# autenticação
from application.auth.login_usecase import LoginUseCase

# usecase de ponto
from application.secretaria.processar_ponto_usecase import ProcessarPontoUseCase

# controller e base gui
from presentation.secretaria.ponto_controller import PontoController
from presentation.shared.base_gui import BaseGui

_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")


def main():
    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported",
    )

    root = tk.Tk()
    root.title("ATRPT - Ponto")

    cfg = load_config(_APP_INI)
    setup_logging(cfg, "ponto")

    # ── autenticação ──────────────────────────────────────────────────────────
    user_repo    = UserRepository(cfg.paths["atrpt_db"])
    login_uc     = LoginUseCase(user_repo)
    user_context = login_uc.execute(root)

    # ── repositórios ─────────────────────────────────────────────────────────
    pessoas_repo    = EmpregadoRepository(accdb_path=cfg.paths["rh_accdb"])
    fornecedor_repo = FornecedorRepository(db_path=cfg.paths["atrpt_db"])
    mapa_repo       = PontoMapaRepository(db_path=cfg.paths["atrpt_db"])

    # ── usecase ───────────────────────────────────────────────────────────────
    usecase = ProcessarPontoUseCase()

    # ── controller ───────────────────────────────────────────────────────────
    controller = PontoController(
        root            = root,
        cfg             = cfg,
        usecase         = usecase,
        user_context    = user_context,
        pessoas_repo    = pessoas_repo,
        fornecedor_repo = fornecedor_repo,
        mapa_repo       = mapa_repo,
    )

    # ── GUI raiz ─────────────────────────────────────────────────────────────
    # BaseGui(root) constrói toda a estrutura fixa: frame_top, frame_menu,
    # frame_work, frame_logs, txt_output e o GuiLogHandler de logging.
    # O seu show_view() instancia PontoGUI num Frame filho de frame_work,
    # injeta os frames de navegação e chama _post_init() — exactamente como
    # acontece dentro da SecretariaGUI.
    gui_root = BaseGui(root)
    gui_root.set_title("Ponto")

    # start() chama gui_root.show_view(PontoGUI, controller)
    controller.start(gui_root)

    root.mainloop()


if __name__ == "__main__":
    main()
