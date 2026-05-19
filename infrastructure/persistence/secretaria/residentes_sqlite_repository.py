# infrastructure/persistence/secretaria/residentes_sqlite_repository.py
#
# Repositório SQLite para residentes — substitui ResidentesRepository (Excel).
# Mantém interface idêntica para não quebrar código existente.

import logging
import sqlite3

import pandas as pd
from domain.shared.strings import simplificar_nome, normalizar_nome

logger = logging.getLogger(__name__)

_DDL = """
    CREATE TABLE IF NOT EXISTS residentes (
        id                   INTEGER,
        numero_residente     INTEGER PRIMARY KEY,
        numero_socio         INTEGER,
        nome                 TEXT,
        genero               TEXT,
        relacao              TEXT,
        petit_nom            TEXT,
        resp_gen             TEXT,
        responsavel          TEXT,
        email                TEXT,
        especial             TEXT,
        copag                TEXT,
        iban                 TEXT,
        data_iban            TEXT,
        designacao_bancaria  TEXT,
        nif                  TEXT,
        data_nascimento      TEXT,
        data_admissao        TEXT,
        data_fim             TEXT,
        resp_tlm             TEXT,
        atualizado_em        DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

_COLS = [
    "id", "numero_residente", "numero_socio", "nome", "genero", "relacao",
    "petit_nom", "resp_gen", "responsavel", "email", "resp_tlm", "especial", "copag",
    "iban", "data_iban", "designacao_bancaria",
    "nif", "data_nascimento", "data_admissao", "data_fim",
]

# Colunas novas adicionadas após o schema original — migradas em _setup()
_MIGRATION_COLS = [
    ("nif",             "TEXT"),
    ("data_nascimento", "TEXT"),
    ("data_admissao",   "TEXT"),
    ("data_fim",        "TEXT"),
    ("resp_tlm",        "TEXT"),
]


class ResidentesSQLiteRepository:

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_DDL)
            existing = {r[1] for r in conn.execute("PRAGMA table_info(residentes)").fetchall()}
            for col, typ in _MIGRATION_COLS:
                if col not in existing:
                    conn.execute(f"ALTER TABLE residentes ADD COLUMN {col} {typ}")
                    logger.info("residentes: coluna '%s' adicionada (migração).", col)
            # NIF deve ser TEXT; corrigir valores guardados como INTEGER
            n = conn.execute(
                "UPDATE residentes SET nif = CAST(nif AS TEXT) "
                "WHERE nif IS NOT NULL AND TYPEOF(nif) = 'integer'"
            ).rowcount
            if n:
                logger.info("residentes: %d NIF(s) convertido(s) de inteiro para texto.", n)

    # ------------------------------------------------------------------
    # Leitura — interface idêntica ao ResidentesRepository (Excel)
    # ------------------------------------------------------------------

    def get_all(self) -> list[dict]:
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("SELECT * FROM residentes ORDER BY numero_residente", conn)
        return df.where(df.notna(), None).to_dict(orient="records")

    def get_all_df(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql("SELECT * FROM residentes ORDER BY numero_residente", conn)

    def get_by_numero(self, numero: int) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT * FROM residentes WHERE numero_residente = ?",
                (int(numero),),
            ).fetchone()
            if row is None:
                return None
            cols = [d[0] for d in conn.execute(
                "SELECT * FROM residentes WHERE 1=0"
            ).description or []]
        if not cols:
            with sqlite3.connect(self.db_path) as conn:
                cur = conn.execute("PRAGMA table_info(residentes)")
                cols = [r[1] for r in cur.fetchall()]
        return dict(zip(cols, row))

    def get_residentes_lookups(self) -> dict:
        rows = self.get_all()
        df = pd.DataFrame(rows)
        if df.empty:
            return {}
        df["numero_residente"] = pd.to_numeric(df["numero_residente"], errors="coerce")
        df = df.dropna(subset=["numero_residente"])
        df["numero_residente"] = df["numero_residente"].astype(int)
        lookups = {"numero_nome": dict(zip(df["numero_residente"], df["nome"]))}
        for col, key in [("email", "numero_email"), ("designacao_bancaria", "numero_designacao")]:
            if col in df.columns:
                lookups[key] = dict(zip(df["numero_residente"], df[col]))
        return lookups

    def update_designacao(self, numero: int, novo_valor: str) -> bool:
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(
                "UPDATE residentes SET designacao_bancaria = ?, atualizado_em = CURRENT_TIMESTAMP "
                "WHERE numero_residente = ?",
                (str(novo_valor).strip(), int(numero)),
            )
        return cur.rowcount > 0

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def update(self, numero: int, campos: dict) -> bool:
        """Actualiza campos arbitrários de um residente."""
        allowed = set(_COLS) - {"numero_residente", "id"}
        sets = {k: v for k, v in campos.items() if k in allowed}
        if not sets:
            return False
        sql = (
            "UPDATE residentes SET "
            + ", ".join(f"{k} = ?" for k in sets)
            + ", atualizado_em = CURRENT_TIMESTAMP WHERE numero_residente = ?"
        )
        with sqlite3.connect(self.db_path) as conn:
            cur = conn.execute(sql, (*sets.values(), int(numero)))
        return cur.rowcount > 0

    def insert(self, dados: dict) -> int:
        """Insere um novo residente. Devolve o numero_residente criado."""
        allowed = set(_COLS)
        cols = {k: v for k, v in dados.items() if k in allowed and v is not None}
        if "numero_residente" not in cols:
            raise ValueError("numero_residente é obrigatório.")
        fields = list(cols.keys())
        ph = ", ".join(["?"] * len(fields))
        sql = (
            f"INSERT INTO residentes ({', '.join(fields)}) VALUES ({ph})"
        )
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(sql, list(cols.values()))
        return int(cols["numero_residente"])

    def get_all_with_cc(self) -> list[dict]:
        """
        Devolve todos os residentes enriquecidos com saldo, pim, anterior e quota
        de residentes_cc (LEFT JOIN por numero_residente).
        """
        sql = """
            SELECT
                r.id,
                r.numero_residente,
                r.numero_socio,
                COALESCE(NULLIF(TRIM(cc.excepcao), ''), r.especial) AS especial,
                r.copag,
                r.nome,
                cc.mensalidade,
                (COALESCE(cc.atual, 0) + COALESCE(cc.pim, 0)) AS saldo,
                cc.atual,
                cc.pim,
                cc.anterior,
                cc.quota,
                cc.activo,
                r.relacao,
                r.responsavel,
                r.email,
                r.genero,
                r.petit_nom,
                r.resp_gen,
                r.nif,
                r.iban,
                r.data_iban,
                r.designacao_bancaria,
                r.data_nascimento,
                r.data_admissao,
                r.data_fim
            FROM residentes r
            LEFT JOIN residentes_cc cc ON cc.numero_residente = r.numero_residente
            ORDER BY r.id
        """
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql(sql, conn)
        # converter NaN → None coluna a coluna (where() não o faz em float64)
        records = []
        for row in df.itertuples(index=False):
            d = {}
            for col, val in zip(df.columns, row):
                try:
                    d[col] = None if pd.isna(val) else val
                except TypeError:
                    d[col] = val
            records.append(d)
        return records

    def upsert_df(self, df: pd.DataFrame) -> int:
        """UPSERT de um DataFrame completo. Usado pela migração."""
        cols = [c for c in _COLS if c in df.columns]
        ph   = ", ".join(["?"] * len(cols))
        upd  = ", ".join(f"{c} = excluded.{c}" for c in cols if c != "numero_residente")
        sql  = (
            f"INSERT INTO residentes ({', '.join(cols)}) VALUES ({ph}) "
            f"ON CONFLICT(numero_residente) DO UPDATE SET {upd}, "
            f"atualizado_em = CURRENT_TIMESTAMP"
        )
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df[cols].iterrows():
                vals = []
                for c in cols:
                    v = row.get(c)
                    try:
                        if pd.isna(v):
                            v = None
                    except TypeError:
                        pass
                    if v is not None:
                        if c in {"id", "numero_residente", "numero_socio"}:
                            try:
                                v = int(float(v))
                            except (TypeError, ValueError):
                                v = None
                        else:
                            v = str(v).strip() or None
                    vals.append(v)
                conn.execute(sql, tuple(vals))
                count += 1
        return count
