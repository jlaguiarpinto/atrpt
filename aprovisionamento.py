# atrpt/aprovisionamento.py

import tkinter as tk
from pathlib import Path
import warnings
from core.config import load_config, load_paths
from core.logging_utils import setup_logging, setup_audit_logger
from presentation.aprovisionamento.aprovisionamento_controller import AprovisionamentoController
from presentation.aprovisionamento.aprovisionamento_gui import AprovisionamentoGUI

from infrastructure.email.smtp_client import SmtpClient
from infrastructure.email.emailer import Emailer

# repos
from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from infrastructure.persistence.aprovisionamento.pedido_repository import PedidoRepositorySQL
from infrastructure.persistence.user_repository import UserRepository

# usecases / services
from application.auth.login_usecase import LoginUseCase
from application.aprovisionamento.list_fornecedores_usecase import ListFornecedoresUseCase
from application.aprovisionamento.create_pedido_usecase import CreatePedidoUseCase
from application.aprovisionamento.autorizar_pedido_usecase import AutorizarPedidoUseCase
from application.aprovisionamento.list_pedidos_usecase import ListPedidosUseCase as ListPedidos
from application.aprovisionamento.enviar_pedido_usecase import EnviarPedidoUseCase
from application.aprovisionamento.add_proposta_usecase import AddPropostaUseCase
from application.aprovisionamento.encomendar_pedido_usecase import EncomendarPedidoUseCase
from infrastructure.persistence.aprovisionamento.encomenda_repository import EncomendaRepository
from application.aprovisionamento.enviar_pedido_email_usecase import EnviarEmailPedidoUseCase
from application.aprovisionamento.submeter_pedido_usecase import SubmeterPedidoUseCase
from application.email.email_template_builder import EmailTemplateBuilder
from application.email.email_sender import EmailSender


# path fixo do app.ini — resguardado na raiz do projecto atrpt
_APP_INI = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\app.ini")

def main():
    root = tk.Tk()
    root.withdraw()
    root.title("ATRPT - Aprovisionamentos")

    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_aprovisionamento")

    setup_logging(cfg, "aprovisionamento")
    audit_log = setup_audit_logger(cfg, "aprovisionamento")
    warnings.filterwarnings(
        "ignore",
        message="Conditional Formatting extension is not supported")

    db_path = cfg.paths["atrpt_db"]

    user_repo      = UserRepository(db_path)
    fornecedor_repo = FornecedorRepository(db_path)
    pedido_repo    = PedidoRepositorySQL(db_path)

    login_uc     = LoginUseCase(user_repo)
    user_context = login_uc.execute(root)
    root.deiconify()

    perfil = cfg.emails["aprovisionamento"]

    smtp = SmtpClient(
        server=perfil.smtp_server,
        port=perfil.smtp_port,
        user=perfil.smtp_user,
        password=perfil.smtp_password,
        use_ssl=perfil.smtp_ssl,
    )

    emailer = Emailer(smtp,)

    # -------------------------
    # USECASES (mínimo viável)
    # -------------------------


    template_builder = EmailTemplateBuilder(cfg.paths["templates_dir"] / "aprovisionamento")

    email_sender = EmailSender(
        emailer    = emailer,
        modo_teste = cfg.modo_teste,
        email_teste= cfg.email_teste,
    )

    enviar_email_pedido_uc = EnviarEmailPedidoUseCase(
        email_sender     = email_sender,
        template_builder = template_builder,
        cfg              = cfg,
    )

    create_uc = CreatePedidoUseCase(pedido_repo, enviar_email_uc=enviar_email_pedido_uc)

    encomenda_repo = EncomendaRepository(db_path)

    encomendar_uc = EncomendarPedidoUseCase(
        pedido_repo      = pedido_repo,
        encomenda_repo   = encomenda_repo,
        fornecedor_repo  = fornecedor_repo,
        email_sender     = email_sender,
        template_builder = template_builder,
    )
    add_proposta_uc = AddPropostaUseCase(pedido_repo)
    select_proposta_uc = None  # 👈 para simplificar, não implementamos essa parte
    autorizar_uc = AutorizarPedidoUseCase(pedido_repo)
    list_pedidos_uc = ListPedidos(pedido_repo)
    enviar_uc = EnviarPedidoUseCase(pedido_repo, fornecedor_repo, emailer)
    list_fornecedores_uc = ListFornecedoresUseCase(fornecedor_repo)

    submeter_uc = SubmeterPedidoUseCase(
        pedido_repo      = pedido_repo,
        user_repo        = user_repo,
        email_sender     = email_sender,
        template_builder = template_builder,
    )

    # -------------------------
    # CONTROLLER
    # -------------------------
    controller = AprovisionamentoController(
        gui=None,
        user_context=user_context,
        cfg=cfg,
        audit_log=audit_log,
        encomendar_uc=encomendar_uc,
        encomenda_repo=encomenda_repo,
        create_uc=create_uc,
        add_proposta_uc=add_proposta_uc,
        select_proposta_uc=select_proposta_uc,
        autorizar_uc=autorizar_uc,
        enviar_uc=enviar_uc,
        list_pedidos_uc=list_pedidos_uc,
        list_fornecedores_uc=list_fornecedores_uc,
        fornecedor_repo=fornecedor_repo,
        pedido_repo=pedido_repo,
        user_repo=user_repo,
        submeter_uc=submeter_uc,
    )

    # -------------------------
    # GUI
    # -------------------------

    gui = AprovisionamentoGUI(root, controller)
    controller.gui = gui

    root.mainloop()

if __name__ == "__main__":
    main()