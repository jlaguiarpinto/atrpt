# atrpt/application/aprovisionamento/create_pedido_usecase.py

from datetime import datetime
from typing import List

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Pedido, Proposta
from domain.aprovisionamento.enums import PedidoEstado

LIMIAR_AUTORIZACAO = 200.0


class CreatePedidoUseCase:

    def __init__(self, repository: PedidoRepository, enviar_email_uc=None):
        self.repository      = repository
        self.enviar_email_uc = enviar_email_uc

    def execute(
        self,
        centro_custo: str,
        descricao: str,
        criado_por: str,
        propostas: List[dict],
    ) -> Pedido:

        numero = self.repository.next_numero()

        # -------------------------
        # Construção de propostas
        # -------------------------
        propostas_obj = [
            Proposta(
                fornecedor_id=p.get("fornecedor_id",""),
                valor=p.get("valor",0.0),
                pdf_path=p.get("pdf_path",p.get("documento","")),
            )
            for p in propostas
        ]

        # -------------------------
        # Estado inicial por valor
        # -------------------------
        valor_total = sum(float(p.valor or 0) for p in propostas_obj)
        estado_inicial = PedidoEstado.autorizado if valor_total < LIMIAR_AUTORIZACAO else PedidoEstado.criado

        # -------------------------
        # Construção do pedido
        # -------------------------
        pedido = Pedido(
            numero=numero,
            centro_custo=centro_custo,
            descricao=descricao,
            criado_por=criado_por,
            data_criacao=datetime.now(),
            propostas=propostas_obj,
            estado=estado_inicial,
        )

        # Persistência
        self.repository.save(pedido)

        # Email — se usecase configurado
        if self.enviar_email_uc is not None:
            try:
                self.enviar_email_uc.execute(pedido)
            except Exception:
                import logging
                logging.getLogger(__name__).exception(
                    f"Erro ao enviar email para pedido {pedido.numero}"
                )

        return pedido
    