# infrastructure/persistence/pim_repository.py

import pandas as pd
from pathlib import Path

class PimRepository:

    def __init__(self, pim_file, faturacao_residentes_file:Path|None=None):
        self._pim_path = pim_file
        self._faturacao_path = faturacao_residentes_file

    def ler_pim(self) -> pd.DataFrame:
        return pd.read_excel(
            self._pim_path,
            dtype={
                "numero_residente": "Int64",
                "anterior": "float64",
                "atual":"float64",
                "total":"float64",
                "recebido": "float64",
                "saldo": "float64",
                "data": "string",
            },)

    def salvar_pim(self, df: pd.DataFrame) -> None:
        """Salva o arquivo PIM"""
        df["numero_residente"]=(
            pd.to_numeric(df["numero_residente"], errors="coerce")
            .astype("Int64")
        )
        df.to_excel(self._pim_path, index=False)

    def guardar_recibos_pendentes(self, df: pd.DataFrame) -> None:
        """Salva o arquivo recibos"""
        df.to_excel(self._pim_path.parent/"recibos_pendentes.xlsx", index=False)

    def ler_recibos_pendentes(self) ->pd.DataFrame:
        """Salva o arquivo recibos"""
        return(pd.read_excel(self._pim_path.parent/"recibos_pendentes.xlsx"))
    



