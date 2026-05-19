# infrastructure/persistence/secretaria/pim_sqlite_repository.py
#
# Substitui PimRepository (Excel) — usa SQLite como fonte de verdade.
# Mantém interface idêntica: ler_pim / salvar_pim / guardar_recibos_pendentes / ler_recibos_pendentes.
#
# Tabela pim_corrente: estado do PIM do ciclo em curso.
# A tabela pim_historico continua a ser o arquivo imutável por (ano, mes).

import logging
import sqlite3

import pandas as pd

logger = logging.getLogger(__name__)

_DDL = """
    CREATE TABLE IF NOT EXISTS pim_corrente (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        numero_residente INTEGER NOT NULL UNIQUE,
        ncli             TEXT,
        nome             TEXT,
        nfat             TEXT,
        especial         TEXT,
        anterior         REAL DEFAULT 0,
        atual            REAL DEFAULT 0,
        total            REAL DEFAULT 0,
        recebido         REAL DEFAULT 0,
        saldo            REAL DEFAULT 0,
        data             TEXT,
        user             TEXT,
        data_envio_recibo TEXT,
        atualizado_em    DATETIME DEFAULT CURRENT_TIMESTAMP
    )
"""

_STORE_COLS = [
    "numero_residente", "ncli", "nome", "nfat", "especial",
    "anterior", "atual", "total", "recebido", "saldo",
    "data", "user", "data_envio_recibo",
]

_NUMERIC_COLS = {"anterior", "atual", "total", "recebido", "saldo"}


class PimSQLiteRepository:

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._setup()

    def _setup(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(_DDL)
            count = conn.execute("SELECT COUNT(*) FROM pim_corrente").fetchone()[0]
            if count == 0:
                self._seed_from_historico(conn)

    def _seed_from_historico(self, conn):
        """Povoa pim_corrente com o período mais recente de pim_historico, se existir."""
        has_hist = conn.execute(
            "SELECT COUNT(*) FROM sqlite_master WHERE type='table' AND name='pim_historico'"
        ).fetchone()[0]
        if not has_hist:
            return
        hist_count = conn.execute("SELECT COUNT(*) FROM pim_historico").fetchone()[0]
        if not hist_count:
            return
        conn.execute("""
            INSERT OR IGNORE INTO pim_corrente
                (numero_residente, anterior, atual, total, recebido, saldo, data, nome, especial)
            SELECT
                p.numero_residente,
                p.anterior,
                p.atual,
                COALESCE(p.anterior, 0) + COALESCE(p.atual, 0),
                p.recebido,
                p.saldo,
                p.data,
                r.nome,
                r.especial
            FROM pim_historico p
            LEFT JOIN residentes r ON r.numero_residente = p.numero_residente
            WHERE (p.ano * 100 + p.mes) = (
                SELECT MAX(p2.ano * 100 + p2.mes) FROM pim_historico p2
            )
        """)
        logger.info("pim_corrente: semeado a partir de pim_historico.")

    # ------------------------------------------------------------------
    # Interface pública (compatível com PimRepository)
    # ------------------------------------------------------------------

    def ler_pim(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            df = pd.read_sql("SELECT * FROM pim_corrente ORDER BY numero_residente", conn)
        for col in _NUMERIC_COLS:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)
        if "numero_residente" in df.columns:
            df["numero_residente"] = pd.to_numeric(
                df["numero_residente"], errors="coerce"
            ).astype("Int64")
        return df

    def salvar_pim(self, df: pd.DataFrame) -> None:
        pim_df = df.copy()
        pim_df["numero_residente"] = pd.to_numeric(
            pim_df["numero_residente"], errors="coerce"
        ).astype("Int64")
        cols = [c for c in _STORE_COLS if c in pim_df.columns]
        pim_df = pim_df[cols]
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM pim_corrente")
            if not pim_df.empty:
                pim_df.to_sql("pim_corrente", conn, if_exists="append", index=False)

    def guardar_recibos_pendentes(self, df: pd.DataFrame) -> None:
        # estado já persistido em pim_corrente via salvar_pim — sem ficheiro auxiliar
        pass

    def ler_recibos_pendentes(self) -> pd.DataFrame:
        with sqlite3.connect(self.db_path) as conn:
            return pd.read_sql(
                """
                SELECT * FROM pim_corrente
                WHERE recebido > 0
                  AND (data_envio_recibo IS NULL OR data_envio_recibo = '')
                ORDER BY numero_residente
                """,
                conn,
            )
