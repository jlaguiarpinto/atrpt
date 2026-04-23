#atrpt /domain/secretaria/recebimentos/recebimento.py
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from .enums import TipoRecebimento


@dataclass
class Recebimento:

    id: str
    data: datetime
    valor: float
    tipo: TipoRecebimento
    descricao_banco: str

    entidade_identificada: Optional[str] = None
    aplicado: bool = False

    # -------------------------
    # Regras de domínio
    # -------------------------

    def identificar(self, entidade: str):
        if self.entidade_identificada:
            raise ValueError("Recebimento já identificado.")
        self.entidade_identificada = entidade

    def marcar_aplicado(self):
        if not self.entidade_identificada:
            raise ValueError("Não pode aplicar sem entidade identificada.")
        if self.aplicado:
            raise ValueError("Recebimento já aplicado.")
        self.aplicado = True