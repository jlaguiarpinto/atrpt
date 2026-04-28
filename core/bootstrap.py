# atrpt/core/bootstrap.py

import logging

from core.security import userContext
from pathlib import Path
from types import SimpleNamespace

from core.config import load_config
from core.paths import resolve_app_cfg_path
from core.logging_utils import setup_logging

from infrastructure.persistence.associados_repository import AssociadosRepo
from infrastructure.persistence.user_repository import UserRepository
from infrastructure.persistence.pedido_repository import PedidoRepositorySQL
from infrastructure.persistence.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.residentes_repository import ResidentesRepository
from infrastructure.persistence.inflow_repository import InflowRepository
from infrastructure.persistence.secretaria.pim_repository import PimRepository


from infrastructure.email.smtp_client import SmtpClient
from infrastructure.email.emailer import Emailer
from application.email.email_sender import EmailSender


# ==========================================================
# BASE COMUM
# ==========================================================

def _build_base(app_name: str):

    base_dir = Path(__file__).resolve().parent.parent
    cfg = load_config(base_dir / "app.ini")
    setup_logging(cfg, app_name)
    logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(message)s"
)

    perfil = cfg.emails[app_name]

    smtp = SmtpClient(
        server=perfil.smtp_server,
        port=perfil.smtp_port,
        user=perfil.smtp_user,
        password=perfil.smtp_password,
        use_ssl=perfil.smtp_ssl,
    )

    emailer = Emailer(
        smtp_client=smtp,
        modo_teste=cfg.modo_teste,
        email_teste=cfg.email_teste,
    )

    email_sender = EmailSender(
        emailer=emailer,
        modo_teste=cfg.modo_teste,
        email_teste=cfg.email_teste,
    )

    return SimpleNamespace(
        cfg=cfg,
        emailer=emailer,
        email_sender=email_sender,
        base_dir=base_dir
    )
