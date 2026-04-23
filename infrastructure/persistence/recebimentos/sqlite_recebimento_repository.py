#atrpt / infrastructure/persistence/recebimentos/sqlite_recebimento_repository.py
import sqlite3
from pathlib import Path
from typing import List, Optional
from datetime import datetime

from domain.secretaria.recebimentos.repository import RecebimentoRepository
from domain.secretaria.recebimentos.recebimento import Recebimento
from domain.secretaria.recebimentos.enums import TipoRecebimento


class SQLiteRecebimentoRepository(RecebimentoRepository):

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    # -----------------------------------------------------

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    # -----------------------------------------------------

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS recebimentos (
                    id TEXT PRIMARY KEY,
                    data TEXT NOT NULL,
                    valor REAL NOT NULL,
                    tipo TEXT NOT NULL,
                    descricao_banco TEXT,
                    entidade_identificada TEXT,
                    aplicado INTEGER DEFAULT 0
                );
            """)

            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_recebimentos_aplicado
                ON recebimentos (aplicado);
            """)

    # -----------------------------------------------------
    # Interface implementation
    # -----------------------------------------------------

    def save(self, recebimento: Recebimento) -> None:

        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO recebimentos (
                    id,
                    data,
                    valor,
                    tipo,
                    descricao_banco,
                    entidade_identificada,
                    aplicado
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                recebimento.id,
                recebimento.data.isoformat(),
                recebimento.valor,
                recebimento.tipo.value,
                recebimento.descricao_banco,
                recebimento.entidade_identificada,
                int(recebimento.aplicado)
            ))

    # -----------------------------------------------------

    def get_by_id(self, recebimento_id: str) -> Optional[Recebimento]:

        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM recebimentos WHERE id = ?",
                (recebimento_id,)
            )
            row = cur.fetchone()

        if not row:
            return None

        return self._row_to_entity(row)

    # -----------------------------------------------------

    def list_nao_aplicados(self) -> List[Recebimento]:

        with self._connect() as conn:
            cur = conn.execute(
                "SELECT * FROM recebimentos WHERE aplicado = 0"
            )
            rows = cur.fetchall()

        return [self._row_to_entity(r) for r in rows]

    # -----------------------------------------------------

    def exists_movimento(
        self,
        data: datetime,
        valor: float,
        descricao_banco: str
    ) -> bool:

        with self._connect() as conn:
            cur = conn.execute("""
                SELECT 1 FROM recebimentos
                WHERE data = ?
                AND valor = ?
                AND descricao_banco = ?
            """, (
                data.isoformat(),
                valor,
                descricao_banco
            ))

            return cur.fetchone() is not None

    # -----------------------------------------------------

    def _row_to_entity(self, row) -> Recebimento:

        (
            rid,
            data,
            valor,
            tipo,
            descricao,
            entidade,
            aplicado
        ) = row

        return Recebimento(
            id=rid,
            data=datetime.fromisoformat(data),
            valor=valor,
            tipo=TipoRecebimento(tipo),
            descricao_banco=descricao,
            entidade_identificada=entidade,
            aplicado=bool(aplicado)
        )