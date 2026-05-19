# application/secretaria/arquivar_pim_usecase.py
#
# Arquiva o ciclo mensal do PIM:
#   1. Grava/actualiza em pim_historico (SQLite) — idempotente via UPSERT.
#   2. Copia o PIM.xlsx para a pasta mensal (pim_mensal_file) — opcional.
#
# Schema por (ano, mes, numero_residente):
#   atual     — valor faturado no mês
#   recebido  — montante recebido
#   saldo     — saldo no fim do ciclo  (anterior[n] = saldo[n-1] → derivável)
#   data      — data do pagamento, normalizada para YYYY-MM-DD

import logging
import sqlite3
from datetime import datetime
from pathlib import Path

import pandas as pd

logger = logging.getLogger(__name__)

_DDL = """
    CREATE TABLE IF NOT EXISTS pim_historico (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        ano              INTEGER NOT NULL,
        mes              INTEGER NOT NULL,
        numero_residente INTEGER NOT NULL,
        atual            REAL,
        anterior         REAL,
        recebido         REAL,
        saldo            REAL,
        data             TEXT,
        arquivado_em     DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(ano, mes, numero_residente)
    )
"""

_COLUNAS_BD = ["ano", "mes", "numero_residente", "atual", "anterior", "recebido", "saldo", "data"]

_DATE_FMTS = [
    "%Y-%m-%d %H:%M:%S",
    "%Y-%m-%d",
    "%d/%m/%Y",
    "%d-%m-%Y",
    "%Y/%m/%d",
    "%d.%m.%Y",
]


def _normalizar_data(val) -> str | None:
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
    except TypeError:
        pass
    s = str(val).strip()
    if not s or s.lower() in ("nat", "none", "nan"):
        return None
    for fmt in _DATE_FMTS:
        try:
            return datetime.strptime(s, fmt).strftime("%Y-%m-%d")
        except ValueError:
            pass
    try:
        return pd.to_datetime(s, dayfirst=True).strftime("%Y-%m-%d")
    except Exception:
        return s  # devolve como está se não conseguir converter


_COLUNAS_REAL = {"atual", "anterior", "recebido", "saldo"}


def _val(v, col: str = ""):
    try:
        if pd.isna(v):
            return None
    except TypeError:
        pass
    if col in _COLUNAS_REAL:
        try:
            return round(float(v), 2)
        except (TypeError, ValueError):
            return None
    return v


class ArquivarPimUseCase:

    def __init__(self, db_path: str):
        self.db_path = str(db_path)
        self._setup_bd()

    def _setup_bd(self):
        with sqlite3.connect(self.db_path) as conn:
            cols = {r[1] for r in conn.execute(
                "PRAGMA table_info(pim_historico)"
            ).fetchall()}
            if cols and "saldo" not in cols:
                conn.execute("DROP TABLE pim_historico")
                cols = set()
                logger.info("pim_historico: schema antigo removido, a recriar.")
            conn.execute(_DDL)
            # migração incremental: adicionar coluna anterior se não existir
            if cols and "anterior" not in cols:
                conn.execute("ALTER TABLE pim_historico ADD COLUMN anterior REAL")
                logger.info("pim_historico: coluna 'anterior' adicionada.")

    def execute(
        self,
        pim_df: pd.DataFrame,
        ano: int,
        mes: int,
        pim_mensal_file: Path | None = None,
    ) -> dict:
        """
        Arquiva o PIM do ciclo (ano, mes).
        pim_mensal_file: se None, não grava cópia Excel.
        Devolve {"gravados": n, "excel": str | None}.
        """
        df = pim_df.copy()
        df["ano"] = int(ano)
        df["mes"] = int(mes)

        df["numero_residente"] = (
            pd.to_numeric(df["numero_residente"], errors="coerce")
            .astype("Int64")
        )
        df = df[df["numero_residente"].notna()].copy()

        # garantir colunas mínimas
        for col in _COLUNAS_BD:
            if col not in df.columns:
                df[col] = None

        # normalizar data
        df["data"] = df["data"].apply(_normalizar_data)

        gravados = 0
        with sqlite3.connect(self.db_path) as conn:
            for _, row in df[_COLUNAS_BD].iterrows():
                conn.execute(
                    """
                    INSERT INTO pim_historico
                        (ano, mes, numero_residente, atual, anterior, recebido, saldo, data)
                    VALUES (?,?,?,?,?,?,?,?)
                    ON CONFLICT(ano, mes, numero_residente) DO UPDATE SET
                        atual        = excluded.atual,
                        anterior     = excluded.anterior,
                        recebido     = excluded.recebido,
                        saldo        = excluded.saldo,
                        data         = excluded.data,
                        arquivado_em = CURRENT_TIMESTAMP
                    """,
                    tuple(_val(row[c], c) for c in _COLUNAS_BD),
                )
                gravados += 1

        logger.info("pim_historico: %d linhas gravadas (ano=%s mes=%s)", gravados, ano, mes)

        excel_path = None
        if pim_mensal_file is not None:
            pim_mensal_file = Path(pim_mensal_file)
            pim_mensal_file.parent.mkdir(parents=True, exist_ok=True)
            pim_df.to_excel(pim_mensal_file, index=False)
            excel_path = str(pim_mensal_file)
            logger.info("Excel mensal guardado: %s", pim_mensal_file)

        return {"gravados": gravados, "excel": excel_path}
