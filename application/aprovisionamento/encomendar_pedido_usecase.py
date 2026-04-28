# atrpt/application/aprovisionamento/encomendar_pedido_usecase.py

import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class EncomendarPedidoUseCase:
    """
    Marca um pedido como encomendado e notifica o fornecedor por email.

    Pré-condição : pedido no estado 'autorizado'
    Pós-condição : pedido no estado 'encomendado'

    Envio de email ao fornecedor — previsto mas não implementado:
        O método _enviar_email_fornecedor está definido como placeholder.
        Quando implementado deverá usar o template Word
        templates/aprovisionamento/EncomendaFornecedor.docx
        e enviar para o email do fornecedor seleccionado na proposta.
    """

    ESTADO_REQUERIDO  = "autorizado"
    ESTADO_RESULTANTE = "encomendado"

    def _estado_str(self, pedido) -> str:
        e = pedido.estado
        return e.value if hasattr(e, 'value') else str(e)

    def __init__(self, pedido_repo, encomenda_repo=None, fornecedor_repo=None, email_sender=None, template_builder=None):
        self.pedido_repo      = pedido_repo
        self.encomenda_repo   = encomenda_repo      # EncomendaRepository
        self.fornecedor_repo  = fornecedor_repo
        self.email_sender     = email_sender
        self.template_builder = template_builder

    def execute(self, numero: str, encomendado_por: str) -> object:
        """
        Executa o processo de encomenda.

        Args:
            numero        : número do pedido (ex: "2026/04")
            encomendado_por: username do utilizador que executa a acção

        Returns:
            Pedido actualizado

        Raises:
            ValueError   : pedido não encontrado ou estado inválido
        """
        pedido = self.pedido_repo.get_by_numero(numero)
        if not pedido:
            raise ValueError(f"Pedido {numero} não encontrado.")

        if self._estado_str(pedido) != self.ESTADO_REQUERIDO:
            raise ValueError(
                f"Pedido {numero} não pode ser encomendado "
                f"(estado actual: '{self._estado_str(pedido)}', requerido: '{self.ESTADO_REQUERIDO}')."
            )

        # ── actualizar estado do pedido ───────────────────────────────
        from domain.aprovisionamento.enums import PedidoEstado
        from domain.aprovisionamento.encomenda import Encomenda
        pedido.estado          = PedidoEstado(self.ESTADO_RESULTANTE)
        pedido.encomendado_por = encomendado_por
        pedido.encomendado_em  = datetime.now()

        self.pedido_repo.update(pedido)

        # ── criar entidade Encomenda ───────────────────────────────────
        proposta = pedido.proposta_selecionada
        encomenda = Encomenda(
            pedido_numero  = pedido.numero,
            fornecedor_id  = proposta.fornecedor_id if proposta else "",
            descricao      = pedido.descricao,
            valor          = proposta.valor if proposta else 0.0,
            pdf_proposta   = proposta.pdf_path if proposta else None,
            data_encomenda = pedido.encomendado_em,
            responsavel    = encomendado_por,
            log_user       = encomendado_por,
            log_data       = pedido.encomendado_em,
        )

        if self.encomenda_repo is not None:
            self.encomenda_repo.save(encomenda)
            logger.info(
                f"Encomenda {encomenda.numero} criada para pedido {numero} "
                f"por {encomendado_por}"
            )
        else:
            logger.warning("encomenda_repo não configurado — encomenda não persistida")

        # ── notificação ao fornecedor ──────────────────────────────────
        self._enviar_email_fornecedor(pedido)

        return pedido, encomenda

    # ------------------------------------------------------------------
    # Placeholder — implementar quando o fluxo de email estiver definido
    # ------------------------------------------------------------------

    def _enviar_email_fornecedor(self, pedido):
        """
        Envia email de encomenda ao fornecedor da proposta seleccionada.

        TODO — implementar:
            1. Identificar a proposta seleccionada do pedido
            2. Obter o fornecedor via self.fornecedor_repo.get_by_id(proposta.fornecedor_id)
            3. Verificar que o fornecedor tem email
            4. Construir mensagem via self.template_builder.build(
                   "EncomendaFornecedor.docx",
                   {"numero": pedido.numero, "descricao": pedido.descricao, ...}
               )
            5. Enviar via self.email_sender.send_one(msg)

        Por agora regista apenas um aviso no log.
        """
        if self.email_sender is None or self.template_builder is None:
            logger.warning(
                f"Email ao fornecedor não enviado para pedido {pedido.numero} "
                f"— email_sender ou template_builder não configurados."
            )
            return

        # TODO: implementar envio
        logger.warning(
            f"_enviar_email_fornecedor não implementado — pedido {pedido.numero}"
        )
