# atrpt/domain/aprovisionamento/encomenda.py

from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional


@dataclass
class Encomenda:
    """
    Criada quando um pedido de compra é encomendado.
    Representa o ciclo de vida da encomenda até ao pagamento.
    """

    # ── identidade ────────────────────────────────────────────────────
    id:               Optional[int]  = None   # atribuído pela BD
    numero:           str            = ""     # nº sequencial ex: 2026/001
    pedido_numero:    str            = ""     # FK → pedidos.numero (histórico/audit)

    # ── dados da encomenda ────────────────────────────────────────────
    fornecedor_id:    str            = ""
    descricao:        str            = ""
    valor:            float          = 0.0
    pdf_proposta:     Optional[str]  = None   # path do PDF aceite

    data_encomenda:   Optional[datetime] = None
    prazo_entrega:    Optional[datetime] = None
    local_entrega:    str            = ""
    responsavel:      str            = ""

    # ── recepção ──────────────────────────────────────────────────────
    recebido:         Optional[str]  = None   # "ok" | "notok" | None
    data_recebido:    Optional[datetime] = None

    # ── pagamento ─────────────────────────────────────────────────────
    pode_pagar:       bool           = False

    # ── auditoria ─────────────────────────────────────────────────────
    log_user:         str            = ""
    log_data:         Optional[datetime] = None

    def marcar_recebido(self, ok: bool, username: str) -> None:
        self.recebido      = "ok" if ok else "notok"
        self.data_recebido = datetime.now()
        self.pode_pagar    = ok
        self._log(username)

    def _log(self, username: str) -> None:
        self.log_user = username
        self.log_data = datetime.now()
