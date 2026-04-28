# atrpt/infrastructure/persistence/aprovisionamentoencomenda_repository.py

import sqlite3
import json
import logging
from datetime import datetime
from typing import Optional, List
from pathlib import Path

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Pedido, Proposta
from domain.aprovisionamento.enums import PedidoEstado

logger = logging.getLogger(__name__)


class EncomendaRepository(PedidoRepository):

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._criar_tabelas()

    # ── setup ─────────────────────────────────────────────────────────────────
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _criar_tabelas(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    numero              INTEGER PRIMARY KEY AUTOINCREMENT,
                    centro_custo        TEXT    NOT NULL,
                    descricao           TEXT    NOT NULL,
                    criado_por          TEXT    NOT NULL,
                    data_criacao        TEXT    NOT NULL,
                    estado              TEXT    NOT NULL DEFAULT 'criado',
                    proposta_selecionada TEXT,
                    autorizacao_1_por   TEXT,
                    autorizacao_1_em    TEXT,
                    autorizacao_2_por   TEXT,
                    autorizacao_2_em    TEXT,
                    encomendado_por     TEXT,
                    encomendado_em      TEXT,
                    anexos              TEXT    DEFAULT '[]'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS propostas (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_numero INTEGER NOT NULL REFERENCES pedidos(numero),
                    fornecedor_id TEXT    NOT NULL,
                    valor         REAL    NOT NULL,
                    pdf_path      TEXT
                )
            """)

    # ── helpers de serialização ───────────────────────────────────────────────
    @staticmethod
    def _dt_str(val: Optional[datetime]) -> Optional[str]:
        return val.isoformat() if val else None

    @staticmethod
    def _str_dt(val: Optional[str]) -> Optional[datetime]:
        return datetime.fromisoformat(val) if val else None

    @staticmethod
    def _proposta_to_json(p: Proposta) -> str:
        return json.dumps({
            "fornecedor_id": p.fornecedor_id,
            "valor":         p.valor,
            "pdf_path":      p.pdf_path,
        })

    @staticmethod
    def _json_to_proposta(s: str) -> Proposta:
        d = json.loads(s)
        return Proposta(
            fornecedor_id = d["fornecedor_id"],
            valor         = d["valor"],
            pdf_path      = d.get("pdf_path"),
        )

    def _row_to_pedido(self, row: sqlite3.Row, propostas: List[Proposta]) -> Pedido:
        proposta_sel = (
            self._json_to_proposta(row["proposta_selecionada"])
            if row["proposta_selecionada"] else None
        )
        return Pedido(
            numero               = row["numero"],
            centro_custo         = row["centro_custo"],
            descricao            = row["descricao"],
            criado_por           = row["criado_por"],
            data_criacao         = self._str_dt(row["data_criacao"]),
            estado               = PedidoEstado(row["estado"]),
            propostas            = propostas,
            proposta_selecionada = proposta_sel,
            autorizacao_1_por    = row["autorizacao_1_por"],
            autorizacao_1_em     = self._str_dt(row["autorizacao_1_em"]),
            autorizacao_2_por    = row["autorizacao_2_por"],
            autorizacao_2_em     = self._str_dt(row["autorizacao_2_em"]),
            encomendado_por      = row["encomendado_por"],
            encomendado_em       = self._str_dt(row["encomendado_em"]),
            anexos               = json.loads(row["anexos"] or "[]"),
        )

    def _load_propostas(self, conn, pedido_numero: int) -> List[Proposta]:
        rows = conn.execute(
            "SELECT fornecedor_id, valor, pdf_path FROM propostas "
            "WHERE pedido_numero = ? ORDER BY id",
            (pedido_numero,)
        ).fetchall()
        return [Proposta(fornecedor_id=r["fornecedor_id"],
                         valor=r["valor"],
                         pdf_path=r["pdf_path"]) for r in rows]

    # ── PedidoRepository ──────────────────────────────────────────────────────
    def save(self, pedido: Pedido) -> None:
        with self._conn() as conn:
            proposta_sel_json = (
                self._proposta_to_json(pedido.proposta_selecionada)
                if pedido.proposta_selecionada else None
            )
            anexos_json = json.dumps(pedido.anexos or [])

            existe = conn.execute(
                "SELECT 1 FROM pedidos WHERE numero = ?", (pedido.numero,)
            ).fetchone()

            if not existe:
                conn.execute("""
                    INSERT INTO pedidos (
                        numero, centro_custo, descricao, criado_por, data_criacao,
                        estado, proposta_selecionada,
                        autorizacao_1_por, autorizacao_1_em,
                        autorizacao_2_por, autorizacao_2_em,
                        encomendado_por, encomendado_em, anexos
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    pedido.numero, pedido.centro_custo, pedido.descricao,
                    pedido.criado_por, self._dt_str(pedido.data_criacao),
                    pedido.estado.value, proposta_sel_json,
                    pedido.autorizacao_1_por, self._dt_str(pedido.autorizacao_1_em),
                    pedido.autorizacao_2_por, self._dt_str(pedido.autorizacao_2_em),
                    pedido.encomendado_por, self._dt_str(pedido.encomendado_em),
                    anexos_json,
                ))
            else:
                conn.execute("""
                    UPDATE pedidos SET
                        centro_custo        = ?,
                        descricao           = ?,
                        estado              = ?,
                        proposta_selecionada= ?,
                        autorizacao_1_por   = ?,
                        autorizacao_1_em    = ?,
                        autorizacao_2_por   = ?,
                        autorizacao_2_em    = ?,
                        encomendado_por     = ?,
                        encomendado_em      = ?,
                        anexos              = ?
                    WHERE numero = ?
                """, (
                    pedido.centro_custo, pedido.descricao,
                    pedido.estado.value, proposta_sel_json,
                    pedido.autorizacao_1_por, self._dt_str(pedido.autorizacao_1_em),
                    pedido.autorizacao_2_por, self._dt_str(pedido.autorizacao_2_em),
                    pedido.encomendado_por, self._dt_str(pedido.encomendado_em),
                    anexos_json, pedido.numero,
                ))

            # propostas — apagar e reinserir (simples e seguro)
            conn.execute(
                "DELETE FROM propostas WHERE pedido_numero = ?", (pedido.numero,)
            )
            for p in pedido.propostas:
                conn.execute(
                    "INSERT INTO propostas (pedido_numero, fornecedor_id, valor, pdf_path) "
                    "VALUES (?, ?, ?, ?)",
                    (pedido.numero, p.fornecedor_id, p.valor, p.pdf_path),
                )

    def get_by_numero(self, numero: str) -> Optional[Pedido]:
        with self._conn() as conn:
            row = conn.execute(
                "SELECT * FROM pedidos WHERE numero = ?", (numero,)
            ).fetchone()
            if not row:
                return None
            propostas = self._load_propostas(conn, numero)
        return self._row_to_pedido(row, propostas)

    def next_numero(self) -> str:
        with self._conn() as conn:
            row = conn.execute("SELECT MAX(numero) FROM pedidos").fetchone()
            maximo = row[0] or 0
        return str(maximo + 1)

    def list_by_estado(self, *estados) -> List[Pedido]:
        with self._conn() as conn:
            if not estados:
                rows = conn.execute(
                    "SELECT * FROM pedidos ORDER BY numero DESC"
                ).fetchall()
            else:
                valores = [e.value if isinstance(e, PedidoEstado) else e for e in estados]
                placeholders = ",".join("?" * len(valores))
                rows = conn.execute(
                    f"SELECT * FROM pedidos WHERE estado IN ({placeholders}) "
                    f"ORDER BY numero DESC",
                    valores,
                ).fetchall()

            pedidos = []
            for row in rows:
                propostas = self._load_propostas(conn, row["numero"])
                pedidos.append(self._row_to_pedido(row, propostas))
        return pedidos
