# infrastructure/persistence/secretaria/candidatos_repository.py
#
# Repositório SQLite para candidatos a residentes.
# Tabela independente de residentes — estados: pendente, espera, inscrito.

import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)

ESTADOS = ("pendente", "espera", "inscrito")

_DDL = """
    CREATE TABLE IF NOT EXISTS residentes_candidatos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        estado           TEXT DEFAULT 'pendente',
        nome             TEXT,
        data_nascimento  TEXT,
        genero           TEXT,
        nif              TEXT,
        id_tipo          TEXT,
        id_num           TEXT,
        id_val           TEXT,
        morada           TEXT,
        cod_postal       TEXT,
        contato          TEXT,
        responsavel      TEXT,
        relacao          TEXT,
        resp_gen         TEXT,
        resp_id_tipo     TEXT,
        resp_id_num      TEXT,
        resp_id_val      TEXT,
        resp_tlm         TEXT,
        email            TEXT,
        mensalidade      TEXT,
        caucao           TEXT,
        iban             TEXT,
        data_iban        TEXT,
        designacao_bancaria TEXT,
        data_admissao    TEXT,
        petit_nom        TEXT,
        copag            TEXT,
        numero_socio     TEXT,
        data_fim         TEXT,
        notas            TEXT,
        atualizado_em    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

_COLS = [
    "estado", "nome", "data_nascimento", "genero", "nif",
    "id_tipo", "id_num", "id_val",
    "morada", "cod_postal", "contato",
    "responsavel", "relacao", "resp_gen",
    "resp_id_tipo", "resp_id_num", "resp_id_val",
    "resp_tlm", "email",
    "mensalidade", "caucao", "iban", "data_iban", "designacao_bancaria",
    "data_admissao", "petit_nom", "copag", "numero_socio", "data_fim", "notas",
]


class CandidatosRepository:

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_DDL)
            logger.info("residentes_candidatos: tabela verificada/criada.")

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def get_all(self, estado: str | None = None) -> list[dict]:
        sql = "SELECT * FROM residentes_candidatos"
        params: tuple = ()
        if estado:
            sql += " WHERE estado = ?"
            params = (estado,)
        sql += " ORDER BY id DESC"
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql(sql, conn, params=params)
        return df.where(df.notna(), None).to_dict(orient="records")

    def get_by_id(self, cid: int) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "SELECT * FROM residentes_candidatos WHERE id = ?", (int(cid),)
            )
            row = cur.fetchone()
            if row is None:
                return None
            cols = [d[0] for d in cur.description]
        return dict(zip(cols, row))

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def insert(self, dados: dict) -> int:
        """Insere um candidato. Devolve o id auto-atribuído."""
        allowed = set(_COLS)
        cols = {k: v for k, v in dados.items() if k in allowed and v is not None}
        if "estado" not in cols:
            cols["estado"] = "pendente"
        fields = list(cols.keys())
        ph = ", ".join(["?"] * len(fields))
        sql = f"INSERT INTO residentes_candidatos ({', '.join(fields)}) VALUES ({ph})"
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql, list(cols.values()))
            return cur.lastrowid

    def update(self, cid: int, campos: dict) -> bool:
        allowed = set(_COLS)
        sets = {k: v for k, v in campos.items() if k in allowed}
        if not sets:
            return False
        sql = (
            "UPDATE residentes_candidatos SET "
            + ", ".join(f"{k} = ?" for k in sets)
            + ", atualizado_em = CURRENT_TIMESTAMP WHERE id = ?"
        )
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql, (*sets.values(), int(cid)))
        return cur.rowcount > 0

    def update_estado(self, cid: int, estado: str) -> bool:
        if estado not in ESTADOS:
            raise ValueError(f"Estado inválido: {estado!r}. Deve ser um de {ESTADOS}.")
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE residentes_candidatos SET estado = ?, atualizado_em = CURRENT_TIMESTAMP "
                "WHERE id = ?",
                (estado, int(cid)),
            )
        return cur.rowcount > 0
