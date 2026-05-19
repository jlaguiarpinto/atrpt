# infrastructure/persistence/secretaria/contacorrente_sqlite_repository.py
#
# Substitui ContaCorrenteRepository (Excel) por SQLite.
# A tabela residentes_cc em atrpt.db espelha o Sheet1 do antigo Residentes_cc.xlsx.
# get_all_f3m() continua a ler Residentes_F3M.xlsx directamente (fonte de verdade F3M).

import sqlite3
from pathlib import Path

import pandas as pd

from domain.shared.strings import normalizar_colunas, simplificar_nome


_DDL = """
    CREATE TABLE IF NOT EXISTS residentes_cc (
        id               INTEGER,
        numero_residente INTEGER PRIMARY KEY,
        numero_socio     INTEGER,
        nome             TEXT,
        excepcao         TEXT,
        data_saida       TEXT,
        mensalidade      REAL,
        saldo            REAL,
        quota            REAL,
        pim              REAL,
        anterior         REAL,
        atual            REAL,
        activo           TEXT,
        atualizado_em    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

# Colunas na ordem da tabela (sem atualizado_em — gerida automaticamente)
_COLS_BD = [
    "id", "numero_residente", "numero_socio", "nome",
    "excepcao", "data_saida", "mensalidade", "saldo",
    "quota", "pim", "anterior", "atual", "activo",
]

_COLS_REAL = {"mensalidade", "saldo", "quota", "pim", "anterior", "atual"}


def _to_py(val, col: str = ""):
    """Converte valor pandas para tipo nativo Python, arredondando reais a 2 dec."""
    try:
        if pd.isna(val):
            return None
    except TypeError:
        pass
    if val is None:
        return None
    if col in _COLS_REAL:
        try:
            return round(float(val), 2)
        except (TypeError, ValueError):
            return None
    if col in {"id", "numero_residente", "numero_socio"}:
        try:
            return int(val)
        except (TypeError, ValueError):
            return None
    return str(val)


class ContaCorrenteSQLiteRepository:

    def __init__(self, db_path: str, f3m_path: str):
        self.db_path  = str(db_path)
        self.f3m_path = str(f3m_path)
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_DDL)
            existing = {r[1] for r in conn.execute("PRAGMA table_info(residentes_cc)").fetchall()}
            if "activo" not in existing:
                conn.execute("ALTER TABLE residentes_cc ADD COLUMN activo TEXT")

    # ------------------------------------------------------------------
    # Leitura — interface idêntica ao ContaCorrenteRepository (Excel)
    # ------------------------------------------------------------------

    def get_all(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql("SELECT * FROM residentes_cc", conn)

    def get_by_numero(self, numero: int) -> dict | None:
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                """SELECT excepcao, mensalidade, saldo, quota, pim, anterior, atual
                   FROM residentes_cc WHERE numero_residente = ?""",
                (int(numero),),
            ).fetchone()
        if row is None:
            return None
        return dict(zip(
            ["excecao", "mensalidade", "saldo", "quota", "pim", "anterior", "atual"],
            row,
        ))

    def get_activo_por_numero(self) -> dict:
        """Devolve {numero_residente: activo} lido directamente do F3M."""
        try:
            df = self.get_all_f3m()
            if "activo" not in df.columns:
                return {}
            return {
                int(nr): str(v).strip()
                for nr, v in zip(df["numero_residente"], df["activo"])
                if pd.notna(nr) and pd.notna(v)
            }
        except Exception:
            return {}

    def get_all_f3m(self) -> pd.DataFrame:
        """Lê Residentes_F3M.xlsx directamente e devolve DataFrame normalizado."""
        df = pd.read_excel(self.f3m_path, engine="openpyxl")
        df = normalizar_colunas(df)
        df = df.rename(columns={"contribuinte": "NIF", "codigoutente": "numero_residente"})
        df["nome"] = df["nome"].apply(simplificar_nome)
        return df

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def upsert_df(self, df: pd.DataFrame) -> int:
        """
        UPSERT de um DataFrame para residentes_cc.
        Aceita tanto 'excepcao' (normalizado do Excel) como 'excecao'.
        Devolve o número de linhas processadas.
        """
        df = df.copy()
        # normalizar nome de coluna vindo do Excel (excepção → excepcao)
        if "excepcao" not in df.columns and "excecao" in df.columns:
            df = df.rename(columns={"excecao": "excepcao"})

        cols = [c for c in _COLS_BD if c in df.columns]
        placeholders = ", ".join(["?"] * len(cols))
        updates = ", ".join(
            f"{c} = excluded.{c}" for c in cols if c != "numero_residente"
        )
        sql = (
            f"INSERT INTO residentes_cc ({', '.join(cols)}) VALUES ({placeholders}) "
            f"ON CONFLICT(numero_residente) DO UPDATE SET {updates}, "
            f"atualizado_em = CURRENT_TIMESTAMP"
        )
        count = 0
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df.iterrows():
                vals = tuple(_to_py(row.get(c), c) for c in cols)
                conn.execute(sql, vals)
                count += 1
        return count
