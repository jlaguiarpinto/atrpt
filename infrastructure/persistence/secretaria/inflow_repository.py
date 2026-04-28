# infrastructure/persistence/inflow_repository.py

import pandas as pd
from pathlib import Path
from domain.shared.strings import remover_separador, normalizar


class InflowRepository:

    def __init__(self, comprovativo_path: Path, inflow_path: Path,
        comprovativodd_path: Path):
        self._comprovativo_path = comprovativo_path
        self._inflow_path = inflow_path
        self._comprovativodd_path = comprovativodd_path

    # --------------------------------------------
    # Extrato bruto do banco
    # --------------------------------------------

    def ler_extrato_diario(self) -> pd.DataFrame:
        df = pd.read_csv(
            self._comprovativo_path,
            skiprows=14,
            header=0,
            sep=";",
            encoding="ISO-8859-1",
        )    
        df.columns = [normalizar(c) for c in df.columns]                                 
        df.columns = df.columns.str.strip()
        col_desc = next(c for c in df.columns if "descri" in c.lower())
        df = df.rename(columns={
            "datavalor": "data",
            col_desc: "descricao",
            "montante": "valor",
        })
        df=df[["data","descricao","valor"]]
        df["descricao"] = (df["descricao"].str.rstrip().str.replace(r"\s*(TRF|TFI)\s*", "", regex=True).str.strip('="'))
        df["valor"] = (df["valor"].apply(remover_separador).astype(float).round(2))
        df = df[df["valor"] > 0].copy()
        df["data"] = (
        pd.to_datetime(df["data"], dayfirst=True, errors="coerce")
          .dt.strftime("%Y-%m-%d")
    )
        return df
    
    def ler_comprovativodd(self) -> pd.DataFrame:
        data=None
        with open(self._comprovativodd_path, encoding="ISO-8859-1") as f:
            for i, line in enumerate(f):
                if i > 14: break
                # procurar linha com "data"
                if data is None:
                    partes = line.strip().split(";")
                    if len(partes) > 1 and partes[0].strip().lower() == "data":
                        data = partes[1].strip()
                        break
        df = pd.read_csv(
            self._comprovativodd_path,
            skiprows=14,
            header=0,
            sep=";",
            encoding="ISO-8859-1",
        )
        # normalizar nomes das colunas
        df.columns = df.columns.str.strip().map(normalizar)
        df = df.rename(columns={"montante":"valor","noautorizacaodebito": "numero_residente"})
        cols = ["valor", "numero_residente", "estado"]
        df = df[cols]
        df["valor"] = df["valor"].apply(remover_separador).astype(float)

        return df, data
    
    # --------------------------------------------
    # Inflow acumulado interno
    # --------------------------------------------

    def ler_inflow_acumulado(self) -> pd.DataFrame:
        return pd.read_excel(self._inflow_path, dtype={'Num':'str'}, engine = 'openpyxl')


    # --------------------------------------------
    # NOVO MÉTODO: Salvar inflow acumulado
    # --------------------------------------------
    
    def salvar_inflow_acumulado(self, df: pd.DataFrame) -> None:
        """
        Salva o dataFrame no arquivo de inflow acumulado
        e atualiza o cache interno se necessário
        """
        df.to_excel(self._inflow_path, index=False)
        #df.to_parquet(self._inflow_pq_path, index=False)
        
    # Opcional: método que já lê e retorna o novo valor
    def atualizar_e_ler_inflow_acumulado(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Salva o novo dataFrame e retorna o valor atualizado
        """
        self.salvar_inflow_acumulado(df)
        return self.ler_inflow_acumulado()  # Lê o arquivo recém-salvo