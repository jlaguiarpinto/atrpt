#atrpt /infrastructure/persistence/associados_excel_repo.py
from pathlib import Path
import pandas as pd
from domain.shared.strings import simplificar_nome, normalizar_coluna


class AssociadosRepo:

    def __init__(self, associados_file: Path, saldos_file: Path):
        self.associados_file = associados_file
        self.saldos_file= saldos_file

    # variantes normalizadas → nome canónico esperado pelo código
    _ALIASES = {
        "e_mail":  "email",
        "mail":    "email",
        "ativo":   "activo",
        "nome_completo": "nome",
    }

    def ler_associados(self):
        df = pd.read_excel(self.associados_file, engine="openpyxl", header=1)
        df.columns = [normalizar_coluna(col) for col in df.columns]
        df = df.rename(columns={k: v for k, v in self._ALIASES.items() if k in df.columns})
        if "email" not in df.columns:
            disponiveis = ", ".join(df.columns.tolist())
            raise KeyError(
                f"Coluna 'email' não encontrada em {self.associados_file.name}. "
                f"Colunas disponíveis: {disponiveis}"
            )
        if "activo" in df.columns:
            df = df[df["activo"].fillna("").str.lower() == "sim"]
        df = df[df["email"].notna() & df["email"].str.contains("@", na=False)]
        df["nome"] = df["nome"].apply(simplificar_nome)
        return df
    
    def ler_saldos(self):
        df = pd.read_excel(self.saldos_file,sheet_name="Dados", engine="openpyxl")
        df.columns = [normalizar_coluna(col) for col in df.columns]
        return df
    
    def salvar_envio(self, df, assunto):

        assunto_limpo = "".join(
            c for c in assunto if c.isalnum() or c in (" ", "_")
        ).strip().replace(" ", "_")

        pasta = self.associados_file.parent
        pasta.mkdir(exist_ok=True)

        ficheiro = pasta / f"{assunto_limpo}_envio.xlsx"

        df.to_excel(ficheiro, index=False)

        return ficheiro