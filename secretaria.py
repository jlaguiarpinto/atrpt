#atrpt/secretaria_main.py

import tkinter as tk
from pathlib import Path
import warnings

from core.config import load_config
from core.logging_utils import setup_logging, setup_audit_logger
from infrastructure.email.smtp_client import SmtpClient
from infrastructure.email.emailer import Emailer

# repos
from infrastructure.persistence.residentes_repository import ResidentesRepository
from infrastructure.persistence.contacorrente_repository import ContaCorrenteRepository
from infrastructure.persistence.inflow_repository import InflowRepository
from infrastructure.persistence.pim_repository import PimRepository
from infrastructure.persistence.user_repository import UserRepositorySQL

# usecases / services
from application.auth.login_usecase import LoginUseCase
from application.email.email_template_builder import EmailTemplateBuilder

# controller
from presentation.secretaria.secretaria_controller import SecretariaController

# path fixo do app.ini — resguardado na raiz do projecto atrpt
_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")

def main():
    root = tk.Tk()
    root.title("ATRPT - Secretaria")
    cfg = load_config(_APP_INI)

    setup_logging(cfg, "secretaria")
    audit_log = setup_audit_logger(cfg, "secretaria")
    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported")

    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported")

    db_path = cfg.paths["atrpt_db"]
    user_repo      = UserRepositorySQL(db_path)

    login_uc = LoginUseCase(user_repo)

    user_context = login_uc.execute(root)

    # -------------------------
    # EMAIL
    # -------------------------
    perfil = cfg.emails["secretaria"]

    smtp = SmtpClient(
        server=perfil.smtp_server,
        port=perfil.smtp_port,
        user=perfil.smtp_user,
        password=perfil.smtp_password,
        use_ssl=perfil.smtp_ssl,)

    emailer = Emailer(smtp,)

    ResidentesRepository(cfg.paths["residentes_file"])
    ContaCorrenteRepository(cfg.paths["residentes_cc_file"])
    PimRepository(cfg.paths["pim_file"])   # histórico/base
    InflowRepository(cfg.paths["comprovativo_file"], cfg.paths["inflow_file"], cfg.paths["comprovativodd_file"])

    # -------------------------
    # CONTROLLER
    # -------------------------
    controller = SecretariaController(
        root=root,
        user_context=user_context,
        cfg=cfg,
        emailer=emailer,
        pim_repo=PimRepository(cfg.paths["pim_file"]),
        residentes_repo=ResidentesRepository(cfg.paths["residentes_file"]),
        contacorrente_repo=ContaCorrenteRepository(cfg.paths["residentes_cc_file"]),
        inflow_repo=InflowRepository(cfg.paths["comprovativo_file"], cfg.paths["inflow_file"], cfg.paths["comprovativodd_file"]),
        template_builder=EmailTemplateBuilder(cfg.paths["template_enviofat"]))

    controller.start()
    root.mainloop()

if __name__ == "__main__":
    main()
