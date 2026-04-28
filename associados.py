# atrpt/associados.py

import tkinter as tk
from pathlib import Path

from core.config import load_config
from core.logging_utils import setup_logging

from infrastructure.email import emailer
from infrastructure.email.smtp_client import SmtpClient
from infrastructure.email.emailer import Emailer

from infrastructure.persistence.envio_repository import EnvioRepository
from infrastructure.persistence.user_repository import UserRepository
from application.auth.login_usecase import LoginUseCase
from application.email.email_sender import EmailSender

# repos
from infrastructure.persistence.associados_repository import AssociadosRepo

# usecases
from application.associados.enviar_emails_usecase import EnviarEmailsAssociadosUseCase

# controller
from presentation.associados.associados_controller import AssociadosController

# path fixo do app.ini — resguardado na raiz do projecto atrpt
_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")


def main():

    root = tk.Tk()
    root.title("ATRPT - Associados")

    cfg = load_config(_APP_INI))
    setup_logging(cfg, "associados")

    # -------------------------
    # REPOS
    # -------------------------
    associados_file = cfg.paths["associados_dir"] / "Associados.xlsx"
    saldos_file = cfg.paths["associados_dir"] / "Saldos.xlsx"

    envio_email_dir = cfg.paths["associados_dir"] / "Comunicação/envio_emails"

    repo = AssociadosRepo(associados_file, saldos_file)
    envio_repo = EnvioRepository(envio_email_dir)

    user_repo = UserRepository(cfg.paths_app["atrpt_db"])

    # -------------------------
    # LOGIN
    # -------------------------
    login_uc = LoginUseCase(user_repo)
    user_context = login_uc.execute(root)

    # -------------------------
    # EMAIL
    # -------------------------
    perfil = cfg.emails["associados"]

    smtp = SmtpClient(
        server=perfil.smtp_server,
        port=perfil.smtp_port,
        user=perfil.smtp_user,
        password=perfil.smtp_password,
        use_ssl=perfil.smtp_ssl,
    )

    emailer = Emailer(
        smtp,
        modo_teste=cfg.modo_teste,
        email_teste=cfg.email_teste,
    )

    # -------------------------
    # CONTAINER
    # -------------------------
    class Container:
        pass

    container = Container()

    # repos
    container.associados = repo
    container.envio_repository = envio_repo

    # email
    container.emailer = emailer
    container.email_sender = EmailSender(
        emailer=container.emailer,
        modo_teste=cfg.modo_teste,
        email_teste=cfg.email_teste
    )

    # usecase
    container.usecase = EnviarEmailsAssociadosUseCase(
        repo_associados=container.associados,
        envio_repository=container.envio_repository,
        email_sender=container.email_sender
    )
    #-------------------------
    #CONTROLLER
    #-------------------------
    controller = AssociadosController(
        root=root,
        container=container,
        user_context=user_context
    )

    controller.start()

    root.mainloop()


if __name__ == "__main__":
    main()