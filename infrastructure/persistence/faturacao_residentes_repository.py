# infrastructure/persistence/faturacao_residentes_repository.py

# infrastructure/persistence/faturacao_residentes_repository.py

import pandas as pd
from pathlib import Path


class FaturacaoResidentesRepository:

    def __init__(self, path: Path):
        self._path = path

    def ler(self) -> pd.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(f"Ficheiro não encontrado: {self._path}")

        df = pd.read_excel(self._path, dtype={"numero_residente": "Int64"})

        df.columns = [c.strip().lower() for c in df.columns]

        if "data_envio" not in df.columns:
            df["data_envio"] = None

        df["data_envio"] = pd.to_datetime(df["data_envio"], errors="coerce")

        return df

    def guardar(self, df: pd.DataFrame):
        df["data_envio"] = pd.to_datetime(df["data_envio"], errors="coerce")
        df["numero_residente"] = df["numero_residente"].astype("Int64")

        df.to_excel(self._path, index=False)