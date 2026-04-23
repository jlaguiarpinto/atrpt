# atrpt/infrastructure/persistence/fornecedor_repository.py

import sqlite3
import logging
from typing import Optional
from domain.aprovisionamento.fornecedor import Fornecedor

logger = logging.getLogger(__name__)

CAMPOS_VALIDOS = {
    "nome", "email", "nif", "iban",
    "tipo_fornecedor", "tipo_relacao", "setor", "metodo_pagamento",
    "comercial_nome", "comercial_email", "comercial_telemovel",
    "administrativo_nome", "administrativo_email", "administrativo_telemovel",
}


class FornecedorRepositorySQL:

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._criar_tabela()

    # ── setup ─────────────────────────────────────────────────────────────────
    def _criar_tabela(self):
        with self._conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS fornecedores (
                    id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                    nome                      TEXT    NOT NULL,
                    email                     TEXT,
                    nif                       TEXT,
                    iban                      TEXT,
                    tipo_fornecedor           TEXT,
                    tipo_relacao              TEXT,
                    setor                     TEXT,
                    metodo_pagamento          TEXT,
                    comercial_nome            TEXT,
                    comercial_email           TEXT,
                    comercial_telemovel       TEXT,
                    administrativo_nome       TEXT,
                    administrativo_email      TEXT,
                    administrativo_telemovel  TEXT
                )
            """)

    def _conn(self):
        return sqlite3.connect(self.db_path)

    # ── mapeamento ────────────────────────────────────────────────────────────
    @staticmethod
    def _row_to_fornecedor(row: sqlite3.Row) -> Fornecedor:
        return Fornecedor(
            id                       = row["id"],
            nome                     = row["nome"],
            email                    = row["email"],
            nif                      = row["nif"],
            iban                     = row["iban"],
            tipo_fornecedor          = row["tipo_fornecedor"],
            tipo_relacao             = row["tipo_relacao"],
            setor                    = row["setor"],
            metodo_pagamento         = row["metodo_pagamento"],
            comercial_nome           = row["comercial_nome"],
            comercial_email          = row["comercial_email"],
            comercial_telemovel      = row["comercial_telemovel"],
            administrativo_nome      = row["administrativo_nome"],
            administrativo_email     = row["administrativo_email"],
            administrativo_telemovel = row["administrativo_telemovel"],
        )

    # ── queries ───────────────────────────────────────────────────────────────
    def list_all(self) -> list[Fornecedor]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT * FROM fornecedores ORDER BY nome"
            ).fetchall()
        return [self._row_to_fornecedor(r) for r in rows]

    def list_by(self, caracteristica: str, valor: str) -> list[Fornecedor]:
        """
        Devolve fornecedores cujo campo `caracteristica` corresponde a `valor`.
        A comparação é case-insensitive e por contenção parcial (LIKE).

        Exemplo:
            repo.list_by("setor", "saude")
            repo.list_by("tipo_fornecedor", "servicos")
        """
        if caracteristica not in CAMPOS_VALIDOS:
            raise ValueError(
                f"Característica '{caracteristica}' inválida. "
                f"Campos permitidos: {sorted(CAMPOS_VALIDOS)}"
            )
        sql = f"SELECT * FROM fornecedores WHERE {caracteristica} LIKE ? ORDER BY nome"
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(sql, (f"%{valor}%",)).fetchall()
        return [self._row_to_fornecedor(r) for r in rows]

    def get_by_id(self, fornecedor_id: int) -> Optional[Fornecedor]:
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM fornecedores WHERE id = ?", (fornecedor_id,)
            ).fetchone()
        return self._row_to_fornecedor(row) if row else None

    def save(self, fornecedor: Fornecedor) -> Fornecedor:
        """INSERT se id é None, UPDATE caso contrário. Devolve o fornecedor com id."""
        campos = [
            "nome", "email", "nif", "iban",
            "tipo_fornecedor", "tipo_relacao", "setor", "metodo_pagamento",
            "comercial_nome", "comercial_email", "comercial_telemovel",
            "administrativo_nome", "administrativo_email", "administrativo_telemovel",
        ]
        valores = [getattr(fornecedor, c) for c in campos]

        with self._conn() as conn:
            if fornecedor.id is None:
                placeholders = ", ".join(["?"] * len(campos))
                cols         = ", ".join(campos)
                cur = conn.execute(
                    f"INSERT INTO fornecedores ({cols}) VALUES ({placeholders})",
                    valores,
                )
                fornecedor.id = cur.lastrowid
            else:
                sets = ", ".join(f"{c} = ?" for c in campos)
                conn.execute(
                    f"UPDATE fornecedores SET {sets} WHERE id = ?",
                    valores + [fornecedor.id],
                )
        return fornecedor

    def delete(self, fornecedor_id: int) -> None:
        with self._conn() as conn:
            conn.execute(
                "DELETE FROM fornecedores WHERE id = ?", (fornecedor_id,)
            )
