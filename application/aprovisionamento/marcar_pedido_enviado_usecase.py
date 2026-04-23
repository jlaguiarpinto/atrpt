# application/aprovisionamento/marcar_pedido_enviado_usecase.py

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.pedido import Pedido


class MarcarPedidoEnviadoUseCase:

    def __init__(self, repository: PedidoRepository):
        self.repository = repository

    def execute(self, numero: str) -> Pedido:

        pedido = self.repository.get_by_numero(numero)

        if not pedido:
            raise ValueError(f"Pedido '{numero}' não encontrado.")

        pedido.marcar_enviada()

        self.repository.save(pedido)

        return pedido