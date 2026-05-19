# infrastructure/persistence/aprovisionamento/email_fornecedor_map_repository.py
#
# Associações persistentes entre domínio base de email e fornecedor.
# Criadas manualmente pelo utilizador quando o emissor não é reconhecido.

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class EmailFornecedorMapRepository:

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)
        self._criar_tabela()

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def _criar_tabela(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS email_fornecedor_map (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    dominio_base  TEXT    NOT NULL UNIQUE,
                    fornecedor_id INTEGER NOT NULL,
                    email_orig    TEXT,
                    criado_em     DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            """)

    # ------------------------------------------------------------------

    def find_by_domain(self, dominio_base: str) -> int | None:
        """Devolve fornecedor_id para o domínio, ou None se não mapeado."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT fornecedor_id FROM email_fornecedor_map "
                "WHERE dominio_base = ?",
                (dominio_base.lower(),),
            ).fetchone()
        return row[0] if row else None

    def save(self, dominio_base: str, fornecedor_id: int, email_orig: str = "") -> None:
        """Guarda ou actualiza a associação domínio → fornecedor."""
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO email_fornecedor_map (dominio_base, fornecedor_id, email_orig)
                VALUES (?, ?, ?)
                ON CONFLICT(dominio_base) DO UPDATE SET
                    fornecedor_id = excluded.fornecedor_id,
                    email_orig    = excluded.email_orig
                """,
                (dominio_base.lower(), fornecedor_id, email_orig),
            )
        logger.info("email_fornecedor_map: @%s → fornecedor_id=%d", dominio_base, fornecedor_id)
