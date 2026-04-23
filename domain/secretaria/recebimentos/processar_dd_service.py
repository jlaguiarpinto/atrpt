#atrpt/domain/secretaria/recebimentos/processar_dd_service.py
import pandas as pd
from domain.shared.strings import remover_separador

class ProcessarDDService:

    def __init__(self, inflow_repo, pim_repo, residentes_repo, email_service):
        self.inflow_repo = inflow_repo
        self.pim_repo = pim_repo
        self.residentes_repo = residentes_repo
        self.email_service = email_service


    def processar_dd(self, atualizar_pim=True, enviar_emails=True):

        # --- ler comprovativo ---
        inflow = self.inflow_repo.ler_comprovativodd()

        inflow = inflow.iloc[:, 1:5]
        inflow.columns = ["valor", "Nº", "nome, "Estado"]
        breakpoint()
        inflow["valor"] = inflow["valor"].apply(remover_separador).astype(float)

        s = inflow["Nº"].astype(str).str.replace("'", "").str.strip()
        inflow["Nº"] = pd.to_numeric(s, errors="coerce").astype("Int64")

        inflow["Estado"] = inflow["Estado"].astype(str).str.strip()

        inflow = inflow[inflow["Estado"] == "0000"]

        if inflow.empty:
            return 0

        # --- residentes conta corrente ---
        cc = self.residentes_repo.ler_residentes_cc()

        cc["Nº"] = pd.to_numeric(cc["Nº"], errors="coerce").astype("Int64")
        cc = cc[cc["excepção"] == "DD"]

        cc["Mensalidade"] = pd.to_numeric(cc["Mensalidade"], errors="coerce").fillna(0)

        # --- merge ---
        df = inflow.merge(cc, on="Nº", how="inner")

        df["PIM_pago"] = (df["valor"] - df["Mensalidade"]).round(2)

        df = df[df["PIM_pago"] > 0]

        if df.empty:
            return 0

        # --- atualizar PIM ---
        if atualizar_pim:
            self._atualizar_pim(df)

        # --- enviar emails ---
        if enviar_emails:
            self._enviar_emails(df)

        return len(df)