# atrpt/application/aprovisionamento/enviar_pedido_email_usecase.py

import logging
from application.email.email_message import EmailMessage
from application.email.email_builder import build_email

logger = logging.getLogger(__name__)

LIMIAR_AUTORIZACAO = 200.0


class EnviarEmailPedidoUseCase:
    """
    Envia email após criação de pedido:
      - valor < 200  → estado AUTORIZADO  → email a emails_sg (para encomendar)
      - valor >= 200 → estado PENDENTE    → email a emails_auth_pedidos (para autorizar)

    Usa template Word  templates/email/encomendar_pedido.docx
    com blocos [autorizado]...[/autorizado] e [pendente]...[/pendente]
    e placeholders {numero}, {descricao}, {centro_custo}, {valor}, {criado_por}
    """

    def __init__(self, email_sender, template_builder, cfg):
        self.email_sender     = email_sender
        self.template_builder = template_builder
        self.cfg              = cfg

    def execute(self, pedido) -> str:
        """
        Determina estado, constrói e envia email.
        Devolve o estado aplicado: 'autorizado' | 'pendente'
        """
        valor = self._valor_total(pedido)

        if valor < LIMIAR_AUTORIZACAO:
            estado     = "autorizado"
            tipo_texto = "autorizado"
            destinatarios = self._lista("emails_sg")
        else:
            estado     = "pendente"
            tipo_texto = "pendente"
            destinatarios = self._lista("emails_auth_pedidos")

        if not destinatarios:
            logger.warning(
                f"Nenhum destinatário configurado para estado '{estado}' "
                f"— email não enviado para pedido {pedido.numero}"
            )
            return estado

        data = {
            "numero":      pedido.numero,
            "descricao":   pedido.descricao,
            "centro_custo": pedido.centro_custo,
            "valor":       valor,
            "criado_por":  pedido.criado_por,
            "tipo_texto":  tipo_texto,
        }

        try:
            msg = build_email(
                builder  = self.template_builder,
                template = "PedidosCompra.docx",
                data     = data,
                to       = destinatarios[0],
            )
            # destinatários adicionais em BCC
            msg.bcc = destinatarios[1:]

            self.email_sender.send_one(msg)
            logger.info(
                f"Email '{tipo_texto}' enviado para {destinatarios} "
                f"— pedido {pedido.numero}"
            )
        except Exception:
            logger.exception(
                f"Erro ao enviar email para pedido {pedido.numero}"
            )

        return estado

    # ------------------------------------------------------------------

    def _valor_total(self, pedido) -> float:
        """Soma os valores das propostas; devolve 0.0 se não houver."""
        try:
            return sum(
                float(p.valor or 0)
                for p in (pedido.propostas or [])
            )
        except Exception:
            return 0.0

    def _lista(self, secao: str) -> list[str]:
        """Lê a lista de emails de uma secção [emails_*] do app.ini."""
        return self.cfg.get_lista_emails(secao)
