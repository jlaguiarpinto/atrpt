# atrpt/infrastructure/email/emailer.py
#
# Responsabilidade: conversão EmailMessage (dataclass) → MIME (stdlib).
#
# O que faz:
#   build_mime()  — converte o dataclass em MimeMessage com HTML, anexos e inline images
#   send()        — constrói o MIME e delega no SmtpClient.send()
#
# O que NÃO faz (responsabilidade do EmailSender/send_batch):
#   modo teste               → EmailSender.send_one() redireciona antes de chegar aqui
#   BCC                      → já vem resolvido no EmailMessage.bcc
#   assinatura               → já incorporada no html_body pelo EmailSender
#   delays / lotes           → send_batch

from email.message import EmailMessage as MimeMessage
from pathlib import Path

from application.email.email_message import EmailMessage
from infrastructure.email.smtp_client import SmtpClient


class Emailer:

    def __init__(
        self,
        smtp_client: SmtpClient,
        *,
        from_addr: str | None = None,
        from_name: str | None = None,
    ):
        self.smtp      = smtp_client
        self.from_addr = from_addr
        self.from_name = from_name

        # Exposto para o EmailSender adicionar ao BCC automaticamente
        self.email_from = from_addr

    # --------------------------------------------------
    # Conversão dataclass → MIME
    # --------------------------------------------------

    def build_mime(self, message: EmailMessage) -> tuple[MimeMessage, list[str]]:
        """
        Constrói o MimeMessage e devolve (mime, recipients).

        recipients = message.to + message.bcc
        O modo teste, BCC e assinatura já foram resolvidos pelo EmailSender
        antes de chegar aqui — este método não os toca.
        """
        mime = MimeMessage()

        mime["From"] = (
            f"{self.from_name} <{self.from_addr}>"
            if self.from_name
            else (self.from_addr or self.smtp.user)
        )
        mime["To"]      = ", ".join(message.to)
        mime["Subject"] = message.subject

        # Parte HTML
        mime.add_alternative(message.html_body, subtype="html")

        # Imagens inline (CID)
        if message.inline_images:
            html_payload = mime.get_payload()[1]
            for cid, path in message.inline_images.items():
                path = Path(path)
                with open(path, "rb") as img:
                    html_payload.add_related(
                        img.read(),
                        maintype="image",
                        subtype=path.suffix.lstrip("."),
                        cid=f"<{cid}>",
                    )

        # Anexos
        if message.attachments:
            for path in message.attachments:
                path = Path(path)
                with open(path, "rb") as f:
                    mime.add_attachment(
                        f.read(),
                        maintype="application",
                        subtype="octet-stream",
                        filename=path.name,
                    )

        # Recipients SMTP = To + BCC (BCC não vai no cabeçalho MIME)
        recipients = list(message.to)
        if message.bcc:
            recipients += list(message.bcc)

        return mime, recipients

    # --------------------------------------------------
    # Envio
    # --------------------------------------------------

    def send(self, message: EmailMessage):
        """
        Constrói o MIME e envia via SmtpClient.

        Pré-condição: smtp_client.connect() já foi chamado pelo send_batch.
        """
        mime, recipients = self.build_mime(message)
        self.smtp.send(mime, recipients)
