# domain/ponto/ausencia_ponto.py

from dataclasses import dataclass
from datetime import date
from typing import Optional


TIPOS_AUSENCIA = {
    "ferias": "Férias",
    "baixa":  "Baixa Médica",
    "outro":  "Outro",
}


@dataclass
class AusenciaPonto:
    empregado_numero: int
    tipo:             str        # 'ferias' | 'baixa' | 'outro'
    data_inicio:      date
    data_fim:         date
    obs:              Optional[str] = None
    id:               Optional[int] = None

    @property
    def tipo_label(self) -> str:
        return TIPOS_AUSENCIA.get(self.tipo, self.tipo)

    def cobre_data(self, d: date) -> bool:
        return self.data_inicio <= d <= self.data_fim
