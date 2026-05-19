# atrpt/pessoas.py

import tkinter as tk
from pathlib import Path
from core.config import load_config, load_paths
from core.logging_utils import setup_logging, setup_audit_logger


_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")


def main():
    root = tk.Tk()
    root.withdraw()
    root.title("ATRPT - Pessoas")

    try:
        import pyi_splash
        pyi_splash.close()
    except Exception:
        pass

    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_pessoas")
    setup_logging(cfg, "pessoas")
    audit_log = setup_audit_logger(cfg, "pessoas")

    from application.auth.login_usecase import LoginUseCase
    from infrastructure.persistence.user_repository import UserRepository
    from presentation.pessoas.pessoas_controller import PessoasController
    from presentation.pessoas.pessoas_gui import PessoasGUI

    db_path      = cfg.paths["atrpt_db"]
    user_repo    = UserRepository(db_path)
    user_context = LoginUseCase(user_repo).execute(root)
    root.deiconify()

    controller     = PessoasController(cfg, user_context, audit_log)
    gui            = PessoasGUI(root, controller)
    controller.gui = gui

    root.mainloop()


if __name__ == "__main__":
    main()
