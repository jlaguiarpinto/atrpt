#atrpt/domain/secretaria/ponto_processor.py


import pandas as pd


class PontoProcessor:

    COLUNAS = [
        "data", "nome", "e1", "s1", "e2", "s2",
        "presenca", "falta", "feriado", "ferias",
        "noturno", "baixa", "observacoes",
    ]

    def limpar_registos(self, df: pd.DataFrame) -> pd.DataFrame:
        df["Pot"] = ""
        df.columns = self.COLUNAS
        df.loc[:, "data"] = df["data"].astype("string").fillna("").str.strip()
        df.loc[:, "nome"] = df["nome"].astype("string")
        df = df[~df["data"].str.upper().eq("TOTAL")].copy()
        mask_sem_data = df["data"] == ""     
        df.loc[:, "nome"] = df["nome"].where(mask_sem_data, pd.NA)
        df.loc[:, "nome"] = df["nome"].ffill()       
        df = df[~mask_sem_data].copy()
        df.loc[:, "data"] =pd.to_datetime(
            df["data"],format="%Y-%m-%d %H:%M:%S",errors="coerce").dt.strftime('%Y-%m-%d')
        return df[self.COLUNAS]

    def merge_sem_duplicados(self, mensal: pd.DataFrame, novos: pd.DataFrame):
        if mensal is None:
            mensal = pd.DataFrame(columns=self.COLUNAS)
        chave_mensal = set(zip(mensal["nome"].astype(str), mensal["data"]))
        chave_novos = list(zip(novos["nome"].astype(str), novos["data"]))

        mask = [c not in chave_mensal for c in chave_novos]
        novos_novos = novos[mask]
        # alinhar colunas antes do concat para evitar FutureWarning e perda de colunas
        colunas = list(dict.fromkeys(list(mensal.columns) + list(novos_novos.columns)))
        mensal      = mensal.reindex(columns=colunas)
        novos_novos = novos_novos.reindex(columns=colunas)
        return pd.concat([mensal, novos_novos], ignore_index=True)