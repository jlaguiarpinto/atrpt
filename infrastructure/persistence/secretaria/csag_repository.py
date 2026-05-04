# infrastructure/persistence/secretaria/csag_repository.py

import pandas as pd
from pathlib import Path


class CsagRepository:
    """Lê o ficheiro CSAG.xlsx mensal.

    O caminho já vem resolvido pelo chamador via resolver_path_template().
    A 1.ª linha do ficheiro é ignorada; os nomes das colunas estão na 2.ª linha.
    A 1.ª coluna (vazia) é descartada.
    """

    def __init__(self, csag_file: Path):
        self._path = Path(csag_file)

    def ler(self) -> pd.DataFrame:
        if not self._path.exists():
            raise FileNotFoundError(f"CSAG não encontrado: {self._path}")
        df = pd.read_excel(self._path, header=1)
        if str(df.columns[0]).startswith("Unnamed"):
            df = df.iloc[:, 1:]
        return df
