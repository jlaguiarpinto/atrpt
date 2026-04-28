# atrpt/infrastructure/persistence/ponto/ponto_mapa_repository.py
"""
Repositório da tabela ponto_mapa_enfermeiros.
Guarda o emparelhamento manual entre nomes/números do ponto
e fornecedores (enfermeiros) na BD principal (atrpt.db).
"""

import sqlite3
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


class PontoMapaRepository:

    TABELA = "ponto_mapa_enfermeiros"

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._criar_tabela()

    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _criar_tabela(self):
        with self._conn() as conn:
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {self.TABELA} (
                    ponto_numero  TEXT,
                    ponto_nome    TEXT NOT NULL,
                    fornecedor_id INTEGER NOT NULL,
                    PRIMARY KEY (ponto_numero, ponto_nome)
                )
            """)

    def get(self, numero: str, nome: str) -> Optional[int]:
        """Devolve fornecedor_id para este numero/nome, ou None."""
        with self._conn() as conn:
            row = conn.execute(
                f"SELECT fornecedor_id FROM {self.TABELA} "
                f"WHERE ponto_numero = ? OR ponto_nome = ? LIMIT 1",
                (numero.strip(), nome.strip().upper())
            ).fetchone()
        return int(row["fornecedor_id"]) if row else None

    def save(self, numero: str, nome: str, fornecedor_id: int) -> None:
        """Grava ou actualiza o emparelhamento."""
        with self._conn() as conn:
            conn.execute(
                f"INSERT OR REPLACE INTO {self.TABELA} "
                f"(ponto_numero, ponto_nome, fornecedor_id) VALUES (?, ?, ?)",
                (numero.strip(), nome.strip().upper(), fornecedor_id)
            )

    def list_all(self) -> list[dict]:
        with self._conn() as conn:
            rows = conn.execute(
                f"SELECT * FROM {self.TABELA} ORDER BY ponto_nome"
            ).fetchall()
        return [dict(r) for r in rows]

    def delete(self, numero: str, nome: str) -> None:
        with self._conn() as conn:
            conn.execute(
                f"DELETE FROM {self.TABELA} "
                f"WHERE ponto_numero = ? AND ponto_nome = ?",
                (numero.strip(), nome.strip().upper())
            )
