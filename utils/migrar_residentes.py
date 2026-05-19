# utils/migrar_residentes.py
#
# Migração única: carrega Tabela_Residentes.xlsx → SQLite (tabela residentes).
# Idempotente (UPSERT). Pode ser executado várias vezes.
#
# Uso:
#   python utils/migrar_residentes.py

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(_ROOT))

import pandas as pd
from domain.shared.strings import normalizar_colunas, simplificar_nome
from core.config import load_config, load_paths
from infrastructure.persistence.secretaria.residentes_sqlite_repository import (
    ResidentesSQLiteRepository,
)

_APP_INI = _ROOT / "app.ini"

# mapeamento de colunas Excel → nome canónico SQLite
_RENAME = {
    "nteiro":              "id",
    "designacao_bancaria_1": None,      # descartar duplicado
    "designacao bancaria":   None,      # descartar duplicado com espaço
    "petit nom":           "petit_nom", # normalizar espaço
    "designacao bancaria": None,
}


def main():
    cfg = load_config(_APP_INI)
    cfg.paths = load_paths(_APP_INI, "paths_comum", "paths_secretaria")

    xlsx_path = cfg.paths["residentes_file"]
    db_path   = cfg.paths["atrpt_db"]

    print(f"Fonte:   {xlsx_path}")
    print(f"Destino: {db_path}  [tabela residentes]")

    df = pd.read_excel(xlsx_path, dtype="string", engine="openpyxl")
    df = normalizar_colunas(df)
    df = df.loc[:, ~df.columns.duplicated()]

    # renomear e descartar
    rename_map = {}
    drop_cols  = []
    for old, new in _RENAME.items():
        if old in df.columns:
            if new is None:
                drop_cols.append(old)
            else:
                rename_map[old] = new

    df = df.rename(columns=rename_map)
    df = df.drop(columns=[c for c in drop_cols if c in df.columns])

    # normalizar nomes
    if "nome" in df.columns:
        df["nome"] = df["nome"].apply(simplificar_nome)

    # garantir numero_residente numérico
    df["numero_residente"] = pd.to_numeric(df["numero_residente"], errors="coerce")
    df = df[df["numero_residente"].notna()].copy()

    print(f"Linhas a migrar: {len(df)}")
    print(f"Colunas:         {list(df.columns)}")

    repo = ResidentesSQLiteRepository(db_path)
    n = repo.upsert_df(df)
    print(f"\nMigração concluída — {n} linhas gravadas em residentes.")


if __name__ == "__main__":
    main()
