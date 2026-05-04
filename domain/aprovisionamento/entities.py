# atrpt/domain/aprovisionamento/entities.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional

from .enums import PedidoEstado


@dataclass(frozen=True)
class Proposta:
    fornecedor_id: str
    valor: float
    pdf_path: str | None = None


@dataclass
class Pedido:
    numero: int
    centro_custo: str
    descricao: str
    criado_por: str
    data_criacao: datetime
    propostas: List[Proposta]

    estado: PedidoEstado = PedidoEstado.criado
    proposta_selecionada: Optional[Proposta] = None

    autorizacao_1_por: Optional[str] = None
    autorizacao_1_em: Optional[datetime] = None
    autorizacao_2_por: Optional[str] = None
    autorizacao_2_em: Optional[datetime] = None

    encomendado_por: Optional[str] = None
    encomendado_em: Optional[datetime] = None
    anexos: List[str] = field(default_factory=list)  # lista de paths

    # --------------------------------------------------

    def propostas_validas(self) -> List[Proposta]:
        """Propostas com fornecedor e valor preenchidos."""
        return [
            p for p in self.propostas
            if p.fornecedor_id and p.valor is not None and p.valor > 0
        ]

    def registar_autorizacao(self, username: str, proposta: Optional[Proposta] = None) -> None:
        """
        Regista autorização e avança estado.
        proposta : proposta seleccionada (obrigatório se houver mais de uma válida)
        """
        from datetime import datetime as _dt

        validas = self.propostas_validas()
        if not validas:
            raise ValueError(
                f"Pedido {self.numero} não tem propostas válidas "                "(fornecedor e valor obrigatórios)."
            )

        # selecção automática se só existir uma
        if len(validas) == 1:
            self.proposta_selecionada = validas[0]
        elif proposta is not None:
            if proposta not in validas:
                raise ValueError("Proposta seleccionada não é válida.")
            self.proposta_selecionada = proposta
        else:
            raise ValueError(
                f"Pedido {self.numero} tem {len(validas)} propostas — "                "seleccione a proposta a adjudicar."
            )

        agora = _dt.now()
        if self.autorizacao_1_por is None:
            self.autorizacao_1_por = username
            self.autorizacao_1_em  = agora
            self.estado = PedidoEstado.autorizado
        else:
            self.autorizacao_2_por = username
            self.autorizacao_2_em  = agora