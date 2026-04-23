# atrpt/domain/finance/recebimento.py

from dataclasses import dataclass
from datetime import datetime

@dataclass
class Recebimento:
    data: str
    origem: str
    tipo: str
    entidade_tipo: str
    entidade_id: str
    valor: float
    referencia: str | None
    criado_por: str
    criado_em: str