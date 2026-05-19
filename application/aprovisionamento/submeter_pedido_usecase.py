# atrpt/application/aprovisionamento/submeter_pedido_usecase.py

import logging
from application.email.email_builder import build_email

logger = logging.getLogger(__name__)


class SubmeterPedidoUseCase:
    """
    Muda pedido de 'criado' para 'pendente' e envia email de pedido de autorização
    a dois diretores:
      - Diretor Financeiro (perfil=DirFin) — sempre obrigatório
      - 2º Diretor — o criador do pedido se for diretor (Dir/DirFin), ou o escolhido pelo utilizador
    """

    def __init__(self, pedido_repo, user_repo, email_sender, template_builder):
        self.pedido_repo      = pedido_repo
        self.user_repo        = user_repo
        self.email_sender     = email_sender
        self.template_builder = template_builder

    def execute(self, numero: str, proposta, diretor_financeiro, diretor2, observacoes: str = ""):
        """
        numero            — número do pedido
        proposta          — Proposta seleccionada
        diretor_financeiro — objeto user com perfil=DirFin
        diretor2          — objeto user (Dir ou DirFin) que será 2.º autorizador
        observacoes       — texto livre opcional
        Devolve o pedido actualizado.
        """
        from domain.aprovisionamento.enums import PedidoEstado

        pedido = self.pedido_repo.get_by_numero(numero)
        if not pedido:
            raise ValueError(f"Pedido {numero} não encontrado.")
        if pedido.estado != PedidoEstado.criado:
            raise ValueError(f"Pedido {numero} não está em estado 'criado' (está '{pedido.estado.value}').")

        pedido.estado = PedidoEstado.pendente
        pedido.proposta_selecionada = proposta
        self.pedido_repo.save(pedido)

        self._enviar_email(pedido, proposta, diretor_financeiro, diretor2, observacoes)
        return pedido

    # ------------------------------------------------------------------

    def _enviar_email(self, pedido, proposta, dir_fin, dir2, observacoes):
        valor = float(proposta.valor) if proposta and proposta.valor else 0.0

        destinatarios = [e for e in [dir_fin.email, dir2.email] if e]
        if not destinatarios:
            logger.warning(f"Sem emails de diretores — email não enviado para pedido {pedido.numero}")
            return

        data = {
            "numero":       pedido.numero,
            "descricao":    pedido.descricao,
            "centro_custo": pedido.centro_custo,
            "valor":        valor,
            "criado_por":   pedido.criado_por,
            "tipo_texto":   "pendente",
            "dir_fin":      dir_fin.nome,
            "dir2":         dir2.nome,
            "observacoes":  observacoes or "",
        }

        try:
            msg = build_email(
                builder  = self.template_builder,
                template = "PedidosCompra.docx",
                data     = data,
                to       = destinatarios[0],
            )
            msg.bcc = destinatarios[1:]
            self.email_sender.send_one(msg)
            logger.info(
                f"Email de autorização enviado para {destinatarios} — pedido {pedido.numero}"
            )
        except Exception:
            logger.exception(f"Erro ao enviar email de autorização — pedido {pedido.numero}")
