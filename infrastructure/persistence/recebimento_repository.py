# atrpt /domain/secretaria/recebimentos/repository.py
from abc import ABC, abstractmethod
from typing import List, Optional
from datetime import datetime

from .recebimento import Recebimento


class RecebimentoRepository(ABC):

    @abstractmethod
    def save(self, recebimento: Recebimento) -> None:
        pass

    @abstractmethod
    def get_by_id(self, recebimento_id: str) -> Optional[Recebimento]:
        pass

    @abstractmethod
    def list_nao_aplicados(self) -> List[Recebimento]:
        pass

    @abstractmethod
    def exists_movimento(
        self,
        data: datetime,
        valor: float,
        descricao_banco: str
    ) -> bool:
        """
        Evita duplicação na importação de extratos.
        """
        pass