# application/aprovisionamento/autorizar_pedido_usecase.py

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Pedido, Proposta
from typing import Optional


class AutorizarPedidoUseCase:

    def __init__(self, repository: PedidoRepository):
        self.repository = repository

    def execute(self, numero: str, username: str, proposta: Optional[Proposta] = None) -> Pedido:
        """
        Autoriza um pedido.

        proposta : Proposta seleccionada pelo utilizador.
                   Se None e só existir uma proposta válida, é seleccionada automaticamente.
                   Se None e existirem várias, lança ValueError pedindo selecção.
        """
        pedido = self.repository.get_by_numero(numero)
        if not pedido:
            raise ValueError(f"Pedido '{numero}' não encontrado.")

        pedido.registar_autorizacao(username, proposta)

        self.repository.save(pedido)

        return pedido
