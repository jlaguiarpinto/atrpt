#atrpt/infrastructure/persistence/envio_repository.py
from pathlib import Path
import pandas as pd
from datetime import datetime
import re


class EnvioRepository:

    def __init__(self, base_dir: Path):
        self.base_dir = base_dir

    # ------------------------------------------
    # GUARDAR
    # ------------------------------------------
    def guardar(self, df, nome_base: str) -> Path:
        self.base_dir.mkdir(parents=True, exist_ok=True)
        nome_base = re.sub(r"[^\w\-_.]", "_", nome_base)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M")
        filename = f"{nome_base}_{timestamp}.xlsx"
        full_path = self.base_dir / filename

        df.to_excel(full_path, index=False)

        return full_path

    # ------------------------------------------
    # LER
    # ------------------------------------------
    def ler(self, path: Path):
        return pd.read_excel(path)
