#atrpt/infrastructure/persistence/conta_corrente_excel_repository.py
import pandas as pd
from pathlib import Path
from domain.shared.strings import normalizar_colunas,  simplificar_nome



class ContaCorrenteRepository():

    def __init__(self, file_path: Path):
  
        self._df = pd.read_excel(file_path,dtype={
        "numero_residente": "string","nome": "string", },usecols=range(12),engine='openpyxl')
        self._df = normalizar_colunas(self._df)
        self._df3m = pd.read_excel(file_path,
                                   dtype={"ID": "Int64","Nome": "string","Contribuinte": "string","Saldo": "float64",
                                          "CodigoUtente": "string" },
                                   sheet_name="F3M",engine='openpyxl')
        self._df3m = normalizar_colunas(self._df3m)
        self._df3m = self._df3m.rename(columns={"contribuinte": "NIF", "codigoutente": "numero_residente"})
        self._df3m["nome"] = self._df3m["nome"].apply(simplificar_nome)

    def get_by_numero(self, numero: int):
        row = self._df[self._df["numero_residente"] == str(numero)]
        if row.empty:
            return None
        row = row.iloc[0]

        return {
            "excecao": row.get("excecao"),
            "mensalidade": row.get("mensalidade"),
            "saldo": row.get("saldo"),
            "quota": row.get("quota"),
            "pim": row.get("pim"),
            "anterior": row.get("anterior"),
            "atual": row.get("atual"),
        }
    
        
    def get_all(self):
        """
        Devolve todos os residentes como lista de dicionários.
        """
        return self._df.copy()
    
    def get_all_f3m(self):
        """
        Devolve todos os residentes como lista de dicionários.
        """
        return self._df3m.copy()
    
