# atrpt/domain/aprovisionamento/repository.py

from abc import ABC, abstractmethod
from typing import Optional, List
from .entities import Pedido


class PedidoRepository(ABC):

    @abstractmethod
    def save(self, pedido: Pedido) -> None:
        """Grava ou actualiza o pedido."""
        pass

    @abstractmethod
    def get_by_numero(self, numero: str) -> Optional[Pedido]:
        """Obtém pedido pelo número."""
        pass

    @abstractmethod
    def next_numero(self) -> str:
        """Gera o próximo número sequencial."""
        pass

    @abstractmethod
    def list_by_estado(self, *estados) -> List[Pedido]:
        """
        Sem argumentos  → devolve todos os pedidos.
        Com um ou mais  → filtra pelos estados indicados (enum ou string).
        """
        pass
