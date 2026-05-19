# utils/migrar_residentes_cc.py
#
# Migração única: carrega Residentes_cc.xlsx (Sheet1) para SQLite (tabela residentes_cc).
# Pode ser executado várias vezes — usa UPSERT idempotente.
#
# Uso:
#   python utils/migrar_residentes_cc.py

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd

from core.config import load_config, load_paths
from infrastructure.persistence.secretaria.contacorrente_sqlite_repository import (
    ContaCorrenteSQLiteRepository,
)

_APP_INI = _ROOT / "app.ini"

# mapeamento do nome de coluna normalizado do Excel → nome no SQLite
_RENAME = {
    "excepcao":   "excepcao",   # já normalizado (de excepção)
    "id":         "id",
    "data_de_saida": "data_saida",
    "pim":        "pim",        # coluna PIM normaliza para pim
}


def main():
    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_secretaria")

    cc_xlsx   = cfg.paths["residentes_cc_file"]
    f3m_xlsx  = cfg.paths["residentes_f3m_file"]
    db_path   = cfg.paths["atrpt_db"]

    print(f"Fonte:    {cc_xlsx}")
    print(f"Destino:  {db_path}  [tabela residentes_cc]")

    # ler Sheet1
    df = pd.read_excel(cc_xlsx, usecols=range(12), engine="openpyxl")

    # normalizar nomes de colunas (excepção → excepcao, PIM → pim, etc.)
    from domain.shared.strings import normalizar_colunas
    df = normalizar_colunas(df)

    # renomear coluna de data para o nome da BD
    if "data_de_saida" in df.columns:
        df = df.rename(columns={"data_de_saida": "data_saida"})

    # garantir que numero_residente é Int64
    df["numero_residente"] = (
        pd.to_numeric(df["numero_residente"], errors="coerce").astype("Int64")
    )
    df = df[df["numero_residente"].notna()].copy()

    print(f"Linhas a migrar: {len(df)}")
    print(f"Colunas encontradas: {list(df.columns)}")

    repo = ContaCorrenteSQLiteRepository(db_path=db_path, f3m_path=f3m_xlsx)
    n = repo.upsert_df(df)

    print(f"\nMigração concluída — {n} linhas gravadas em residentes_cc.")


if __name__ == "__main__":
    main()
