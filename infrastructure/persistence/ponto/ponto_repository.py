# atrpt/infrastructure/persistence/ponto/ponto_repository.py

from pathlib import Path
import re
import pandas as pd


class PontoRepository:

    def __init__(self, pasta_mes, ficheiro_resumo):
        self.pasta_mes       = pasta_mes
        self.ficheiro_resumo = ficheiro_resumo

    def listar_ficheiros_diarios(self):
        pattern = re.compile(r"^\d{4}\.xlsx$")
        return sorted([
            f for f in self.pasta_mes.glob("*.xlsx")
            if pattern.match(f.name)
        ])

    def ler_ultimo_dia_mes_anterior(self) -> pd.DataFrame | None:
        nome_pasta = self.pasta_mes.name
        try:
            ano = int(nome_pasta[:4])
            mes = int(nome_pasta[4:])
        except ValueError:
            return None

        if mes == 1:
            ano_ant, mes_ant = ano - 1, 12
        else:
            ano_ant, mes_ant = ano, mes - 1

        pasta_ant = self.pasta_mes.parent / f"{ano_ant}{mes_ant:02d}"
        if not pasta_ant.exists():
            return None

        pattern = re.compile(r"^\d{4}\.xlsx$")
        ficheiros = sorted([
            f for f in pasta_ant.glob("*.xlsx")
            if pattern.match(f.name)
        ])
        if not ficheiros:
            return None

        try:
            return pd.read_excel(ficheiros[-1])
        except Exception:
            return None

    def ler_excel(self, path):
        return pd.read_excel(path)

    def ler_mensal(self):
        if self.ficheiro_resumo.exists():
            df = pd.read_excel(self.ficheiro_resumo)
            return self._normalizar_colunas(df)
        return None

    def guardar_mensal(self, df: pd.DataFrame):
        df = self._normalizar_colunas(df.copy())
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

    # ── normalização de colunas ───────────────────────────────────────────────
    @staticmethod
    def _normalizar_colunas(df: pd.DataFrame) -> pd.DataFrame:
        """
        Garante tipos e nomes correctos após leitura/antes de gravação:
        - hext50/75/100 : numérico (float), NaN → 0
        - observ        : texto, NaN → ""
        - observacoes_dl / observacoes_cs : migrados para observ se ainda existirem
        """
        # migração de campos antigos → observ (campo único, sem separador)
        if "observ" not in df.columns:
            # preferir observacoes_dl; se vazio usar observacoes_cs
            obs_dl = df.get("observacoes_dl", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
            obs_cs = df.get("observacoes_cs", pd.Series("", index=df.index)).fillna("").astype(str).str.strip()
            df["observ"] = obs_dl.where(obs_dl != "", obs_cs)
            # remover colunas antigas se existirem
            df = df.drop(columns=[c for c in ("observacoes_dl", "observacoes_cs")
                                   if c in df.columns], errors="ignore")

        # horas extra — numérico
        for col in ("hext50", "hext75", "hext100"):
            if col not in df.columns:
                df[col] = 0.0
            else:
                df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0.0)

        # observ — texto limpo
        df["observ"] = df["observ"].fillna("").astype(str).str.strip()

        return df
