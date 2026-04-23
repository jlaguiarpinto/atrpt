#atrpt/infrastructure/persistence/ponto_repository.py
from pathlib import Path
import re
import pandas as pd


class PontoRepository:

    def __init__(self, pasta_mes, ficheiro_resumo):
        self.pasta_mes = pasta_mes
        self.ficheiro_resumo = ficheiro_resumo

    def listar_ficheiros_diarios(self):
        pattern = re.compile(r"^\d{4}\.xlsx$")
        return sorted([
            f for f in self.pasta_mes.glob("*.xlsx")
            if pattern.match(f.name)
        ])

    def ler_ultimo_dia_mes_anterior(self) -> pd.DataFrame | None:
        """
        Lê o ficheiro do último dia do mês anterior.
        A pasta do mês anterior é AAAAMM-1 — calculada a partir de pasta_mes.
        Devolve DataFrame ou None se não existir.
        """
        nome_pasta = self.pasta_mes.name  # ex: "202603"
        try:
            ano  = int(nome_pasta[:4])
            mes  = int(nome_pasta[4:])
        except ValueError:
            return None

        # calcular mês anterior
        if mes == 1:
            ano_ant, mes_ant = ano - 1, 12
        else:
            ano_ant, mes_ant = ano, mes - 1

        pasta_ant = self.pasta_mes.parent / f"{ano_ant}{mes_ant:02d}"
        if not pasta_ant.exists():
            return None

        # último ficheiro DDMM.xlsx da pasta anterior
        pattern = re.compile(r"^\d{4}\.xlsx$")
        ficheiros = sorted([
            f for f in pasta_ant.glob("*.xlsx")
            if pattern.match(f.name)
        ])
        if not ficheiros:
            return None

        ultimo = ficheiros[-1]
        try:
            return pd.read_excel(ultimo)
        except Exception:
            return None

    def ler_excel(self, path):
        return pd.read_excel(path)

    def ler_mensal(self):
        if self.ficheiro_resumo.exists():
            return pd.read_excel(self.ficheiro_resumo)
        return None

    def guardar_mensal(self, df):
        df.to_excel(self.ficheiro_resumo, index=False)

    def guardar_resumo_empregado(self, df: pd.DataFrame):
        if df is None or df.empty:
            return
        path = self.pasta_mes / f"{self.pasta_mes.name}_resumo_empregados.xlsx"
        df.to_excel(path, index=False)
        return path

    def guardar_erros(self, df_erros: pd.DataFrame):
        if df_erros is None or df_erros.empty:
            return
        path = self.pasta_mes / "erros_picagem.xlsx"
        df_erros.to_excel(path, index=False)
        return path