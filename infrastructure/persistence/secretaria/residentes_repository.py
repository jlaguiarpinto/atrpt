#atrpt/infrastructure/persistence/residentes_repository.py
import pandas as pd
from pathlib import Path
from domain.shared.strings import normalizar_colunas, simplificar_nome


class ResidentesRepository():

    def __init__(self, residentes_path: Path):
        self.residentes = pd.read_excel(residentes_path,dtype="string")
        self.residentes = normalizar_colunas(self.residentes)
        self.residentes = self.residentes.loc[:, ~self.residentes.columns.duplicated()]
        self.residentes["nome"] = self.residentes["nome"].apply(simplificar_nome)
        self.path = residentes_path

    def get_by_numero(self, numero: int):
        row = self.residentes[self.residentes["numero_residente"] == str(numero)] 
        if row.empty:
            return None
        row = row.iloc[0]
        return {
            "numero_residente": row["numero_residente"],
            "nome": row.get("nome"),
            "email": row.get("email"),
            "genero": row.get("genero"),
            "relacao": row.get("relacao"),
            "petit_nom": row.get("petit nom"),
            "resp_gen": row.get("resp_gen"),
            "responsavel": row.get("responsavel"),
            "designacao bancaria": row.get("designacao bancaria"),
        }
    
    def get_all(self):
        """
        Devolve todos os residentes como lista de dicionários.
        """
        return self.residentes.to_dict(orient="records")
    
    def update_designacao(self, numero, novo_valor):

        mask = self.residentes["numero_residente"] == str(numero)

        if not mask.any():
            return False

        self.residentes.loc[mask, "designacao bancaria"] = str(novo_valor).strip()

        self.residentes.to_excel(self.path, index=False)

        return True

    def get_residentes_lookups(self) -> dict:   
        """
        Devolve vários dicionários úteis de residentes.
        """

        if self.residentes.empty:
            return {}

        required = {"numero_residente", "nome"}
        if not required.issubset(self.residentes.columns):
            raise ValueError("Tabela de residentes inválida.")

        df = self.residentes.copy()

        df["numero_residente"] = pd.to_numeric(
            df["numero_residente"],
            errors="coerce"
        )

        df = df.dropna(subset=["numero_residente"])
        df["numero_residente"] = df["numero_residente"].astype(int)

        lookups = {}

        lookups["numero_nome"] = dict(
            zip(df["numero_residente"], df["nome"])
        )

        if "NIF" in df.columns:
            lookups["numero_nif"] = dict(
                zip(df["numero_residente"], df["NIF"])
            )

        if "email" in df.columns:
            lookups["numero_email"] = dict(
                zip(df["numero_residente"], df["email"])
            )

        if "designacao bancaria" in df.columns:
            lookups["numero_designacao"] = dict(
                zip(df["numero_residente"], df["designacao bancaria"])
            )

        return lookups