#atrpt/secretaria_main.py

import tkinter as tk
from pathlib import Path
import warnings

from core.config import load_config, load_paths, load_paths_templates
from core.logging_utils import setup_logging, setup_audit_logger
from infrastructure.email.smtp_client import SmtpClient
from infrastructure.email.emailer import Emailer

# repos
from infrastructure.persistence.secretaria.residentes_sqlite_repository import ResidentesSQLiteRepository
from infrastructure.persistence.pessoas.empregado_sqlite_repository import EmpregadoSQLiteRepository
from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.ponto.ponto_mapa_repository import PontoMapaRepository
from infrastructure.persistence.secretaria.contacorrente_sqlite_repository import ContaCorrenteSQLiteRepository
from infrastructure.persistence.secretaria.inflow_repository import InflowRepository
from infrastructure.persistence.secretaria.pim_sqlite_repository import PimSQLiteRepository
from infrastructure.persistence.secretaria.candidatos_repository import CandidatosRepository
from infrastructure.persistence.user_repository import UserRepository

# usecases / services
from application.auth.login_usecase import LoginUseCase

# controller
from presentation.secretaria.secretaria_controller import SecretariaController

# path fixo do app.ini — resguardado na raiz do projecto atrpt
_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")

def main():
    root = tk.Tk()
    root.withdraw()
    root.title("ATRPT - Secretaria")
    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_secretaria")
    cfg.paths_templates = load_paths_templates(_APP_INI, cfg.paths)

    setup_logging(cfg, "secretaria")
    audit_log = setup_audit_logger(cfg, "secretaria")
    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported")

    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported")

    db_path = cfg.paths["atrpt_db"]
    user_repo      = UserRepository(db_path)

    login_uc = LoginUseCase(user_repo)

    user_context = login_uc.execute(root)
    root.deiconify()

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

    ResidentesSQLiteRepository(cfg.paths["atrpt_db"])
    ContaCorrenteSQLiteRepository(cfg.paths["atrpt_db"], cfg.paths["residentes_f3m_file"])
    InflowRepository(cfg.paths["comprovativo_file"], cfg.paths["inflow_file"], cfg.paths["comprovativodd_file"])

    # -------------------------
    # REPOS TRANSVERSAIS
    # -------------------------
    pessoas_repo = EmpregadoSQLiteRepository(
        db_path=cfg.paths["atrpt_db"]
    )
    fornecedor_repo = FornecedorRepository(
        db_path=cfg.paths["atrpt_db"]
    )
    mapa_repo = PontoMapaRepository(
        db_path=cfg.paths["atrpt_db"]
    )

    # -------------------------
    # CONTROLLER
    # -------------------------
    controller = SecretariaController(
        root=root,
        user_context=user_context,
        cfg=cfg,
        emailer=emailer,
        pim_repo=PimSQLiteRepository(cfg.paths["atrpt_db"]),
        residentes_repo=ResidentesSQLiteRepository(cfg.paths["atrpt_db"]),
        contacorrente_repo=ContaCorrenteSQLiteRepository(cfg.paths["atrpt_db"], cfg.paths["residentes_f3m_file"]),
        inflow_repo=InflowRepository(cfg.paths["comprovativo_file"], cfg.paths["inflow_file"], cfg.paths["comprovativodd_file"]),
        recibo_template_path=cfg.paths["template_enviorecibo"],
        pessoas_repo=pessoas_repo,
        fornecedor_repo=fornecedor_repo,
        mapa_repo=mapa_repo,
        candidatos_repo=CandidatosRepository(cfg.paths["atrpt_db"]),
    )

    controller.start()
    root.mainloop()

if __name__ == "__main__":
    main()
