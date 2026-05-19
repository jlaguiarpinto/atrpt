#atrpt/application/email/enviar_recibos_pim_usecase.py

from datetime import datetime
from pathlib import Path
import pandas as pd
from application.email.email_message import EmailMessage
from application.email.mass_email_sender import MassEmailSender


class EnviarRecibosPimUseCase:

    def __init__(self, emailer, paths, residentes, modo_teste=False):
        self.emailer = emailer
        self.paths = paths
        self.residentes = residentes
        self.modo_teste = modo_teste

    # --------------------------------------------------

    def executar(self, recibos_df, on_progress=None):

        if recibos_df.empty:
            return

        from infrastructure.persistence.secretaria.pim_sqlite_repository import PimSQLiteRepository
        pim_repo = PimSQLiteRepository(self.paths["atrpt_db"])
        pim_df = pim_repo.ler_pim()
        pim_df["numero_residente"] = pim_df["numero_residente"].astype(str)

        mensagens = []

        for _, row in recibos_df.iterrows():

            numero = int(row["numero_residente"])
            residente = self.residentes.get_by_numero(numero)

            if not residente:
                continue

            email = residente.get("email")
            if not email:
                continue

            html = f"""
            <p>Exmo(a). {residente.get("nome")},</p>
            <p>Confirmamos a receção de {row['valor_PIM']:.2f} €.</p>
            <p>saldo atual: {row['saldo atual']:.2f} €</p>
            """

            mensagens.append(
                EmailMessage(
                    to=[email],
                    subject="Recibo PIM",
                    html_body="""
                    <p>Segue recibo:</p>
                    <img src="cid:logo">
                    """,
                    inline_images={
                        "logo": Path("imgs/logo.png")
                    }
                            ))

        sender = MassEmailSender(
            self.emailer,
            modo_teste=self.modo_teste,
        )

        sender.send_batch(
            mensagens=mensagens,
            log_dir=Path.cwd() / "logs" / "pim_recibos",
            on_progress=on_progress,
        )

        # --------------------------------------------------
        # atualizar data_envio_recibo
        # --------------------------------------------------

        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        for _, row in recibos_df.iterrows():
            pim_df.loc[
                pim_df["numero_residente"] == str(row["numero_residente"]),
                "data_envio_recibo"
            ] = timestamp

        pim_repo.salvar_pim(pim_df)