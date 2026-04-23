# atrpt/application/aprovisionamento/list_pedidos_usecase.py

from typing import List
from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Pedido
from domain.aprovisionamento.enums import PedidoEstado


class ListPedidosUseCase:

    def __init__(self, repository: PedidoRepository):
        self.repository = repository

    def execute(self, *estados) -> List[Pedido]:
        """
        Sem argumentos  → todos os pedidos.
        Com um ou mais  → filtra pelos estados indicados (enum ou string).

        Exemplos:
            uc.execute()
            uc.execute(PedidoEstado.criado)
            uc.execute("criado", "aguarda_autorizacao_1")
        """
        # Normalizar para strings minúsculas — aceita enums ou strings
        lista = [
            e.value if isinstance(e, PedidoEstado) else str(e).lower()
            for e in estados
        ]

        # desempacotar com * para que o repositório receba args individuais
        return self.repository.list_by_estado(*lista)
