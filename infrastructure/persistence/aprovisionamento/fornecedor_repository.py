# atrpt/infrastructure/persistence/aprovisionamento/fornecedor_repository.py

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


class FornecedorRepository:

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
            # Migration: remove índice UNIQUE no nif se criado por versão anterior
            self._migration_remover_unique_nif(conn)

    @staticmethod
    def _migration_remover_unique_nif(conn: sqlite3.Connection) -> None:
        """
        Versões antigas criavam UNIQUE(nif). Como o NIF pode ser desconhecido
        (NULL), esse constraint impede guardar mais de um fornecedor sem NIF.
        Esta migration recria a tabela sem esse índice, preservando os dados.
        """
        indices = conn.execute(
            "SELECT name FROM sqlite_master "
            "WHERE type='index' AND tbl_name='fornecedores' AND sql LIKE '%nif%'"
        ).fetchall()
        nomes_unicos = [
            row[0] for row in indices
            if conn.execute(
                "SELECT sql FROM sqlite_master WHERE name=?", (row[0],)
            ).fetchone()[0].upper().startswith("CREATE UNIQUE")
        ]
        if not nomes_unicos:
            return

        logger.info("Migration: a remover UNIQUE constraint do campo 'nif'…")
        conn.execute("ALTER TABLE fornecedores RENAME TO _fornecedores_bak")
        conn.execute("""
            CREATE TABLE fornecedores (
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
        conn.execute("""
            INSERT INTO fornecedores
            SELECT id, nome, email, nif, iban, tipo_fornecedor, tipo_relacao,
                   setor, metodo_pagamento, comercial_nome, comercial_email,
                   comercial_telemovel, administrativo_nome, administrativo_email,
                   administrativo_telemovel
            FROM _fornecedores_bak
        """)
        conn.execute("DROP TABLE _fornecedores_bak")
        logger.info("Migration concluída — UNIQUE(nif) removido.")

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
        # string vazia ou só espaços → None (evita colisão em nif e outros campos)
        def _normalizar(v):
            if v is None:
                return None
            if isinstance(v, str) and v.strip() == "":
                return None
            return v

        valores = [_normalizar(getattr(fornecedor, c)) for c in campos]

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
    def update(self, dados) -> Fornecedor:
        """
        Actualiza um fornecedor existente.
        Aceita um Fornecedor ou um dict com pelo menos 'id'.
        """
        if isinstance(dados, dict):
            fornecedor = self.get_by_id(dados["id"])
            if fornecedor is None:
                raise ValueError(f"Fornecedor id={dados['id']} não encontrado")
            for campo, valor in dados.items():
                if campo != "id" and hasattr(fornecedor, campo):
                    setattr(fornecedor, campo, valor)
        else:
            fornecedor = dados

        if fornecedor.id is None:
            raise ValueError("update requer fornecedor com id definido")

        return self.save(fornecedor)

    def get_by_nome(self, nome: str) -> Optional[Fornecedor]:
        """Devolve o primeiro fornecedor com nome exacto (case-insensitive)."""
        with self._conn() as conn:
            conn.row_factory = sqlite3.Row
            row = conn.execute(
                "SELECT * FROM fornecedores WHERE LOWER(nome) = LOWER(?) LIMIT 1",
                (nome,)
            ).fetchone()
        return self._row_to_fornecedor(row) if row else None

    def save_from_dict(self, dados: dict) -> Fornecedor:
        """Cria ou actualiza um fornecedor a partir de um dicionário."""
        def _v(key, default=None):
            """Devolve None se o valor for string vazia."""
            val = dados.get(key, default)
            return None if val == "" else val
        fornecedor = Fornecedor(
            id               = dados.get("id"),
            nome             = dados.get("nome", ""),
            email            = _v("email"),
            nif              = _v("nif"),
            iban             = _v("iban"),
            tipo_fornecedor  = _v("tipo_fornecedor"),
            tipo_relacao     = _v("tipo_relacao"),
            setor            = _v("setor"),
            metodo_pagamento = _v("metodo_pagamento"),
            comercial_nome           = _v("comercial_nome"),
            comercial_email          = _v("comercial_email"),
            comercial_telemovel      = _v("comercial_telemovel"),
            administrativo_nome      = _v("administrativo_nome"),
            administrativo_email     = _v("administrativo_email"),
            administrativo_telemovel = _v("administrativo_telemovel"),
        )
        return self.save(fornecedor)
