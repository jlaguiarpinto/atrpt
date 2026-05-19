# atrpt/infrastructure/email/smtp_client.py
#
# Responsabilidade: executor SMTP puro.
#
# O que faz:
#   connect() / disconnect() — gestão explícita da ligação (chamados pelo send_batch)
#   send()                   — envia uma mensagem MIME já construída, com retries SMTP
#
# O que NÃO faz (responsabilidade do send_batch):
#   delays entre emails      → send_batch.delay_envio
#   pausas entre lotes       → send_batch.pausa_entre_lotes
#   reconexão por volume     → send_batch controla max_por_conexao
#   connect/disconnect auto  → send_batch chama connect()/disconnect() explicitamente

import smtplib
import time
import random
from email.message import EmailMessage as MimeMessage


class SmtpClient:

    def __init__(
        self,
        server: str,
        port: int,
        user: str,
        password: str,
        use_ssl: bool = False,
        retries: int = 3,
        debug=None,
    ):
        self.server  = server
        self.port    = port
        self.user    = user
        self.password = password
        self.use_ssl  = use_ssl
        self.retries  = retries
        self.debug    = debug

        # Exposto para o send_batch ler e gerir externamente

        self._smtp  = None
        self._sent  = 0          # contador gerido pelo send_batch via sent_count

    # --------------------------------------------------
    # Debug
    # --------------------------------------------------

    def _log(self, msg: str):
        if callable(self.debug):
            try:
                self.debug(msg)
            except Exception:
                pass

    # --------------------------------------------------
    # Ligação — públicos, chamados pelo send_batch
    # --------------------------------------------------

    def connect(self):
        """Abre ligação SMTP e autentica."""
        self._log(f"Ligação SMTP a {self.server}:{self.port}")
        if self.use_ssl:
            smtp = smtplib.SMTP_SSL(self.server, self.port, timeout=60)
        else:
            smtp = smtplib.SMTP(self.server, self.port, timeout=60)
            smtp.starttls()
        smtp.login(self.user, self.password)
        self._smtp = smtp
        self._sent = 0

    def disconnect(self):
        """Fecha a ligação SMTP de forma segura."""
        if self._smtp:
            try:
                self._smtp.quit()
            except Exception:
                pass
            self._smtp = None

    @property
    def connected(self) -> bool:
        return self._smtp is not None

    # --------------------------------------------------
    # Envio — puro, sem delays, sem connect automático
    # --------------------------------------------------

    def send(self, mime: MimeMessage, recipients: list[str]) -> bool:
        """
        Envia uma mensagem MIME já construída para a lista de recipients.

        Pré-condição: connect() já foi chamado pelo send_batch.
        Faz retries em caso de erros SMTP recuperáveis.

        Devolve True em caso de sucesso.
        Lança excepção se esgotar as tentativas.
        """
        if self._smtp is None:
            raise RuntimeError(
                "SmtpClient.send() chamado sem ligação activa. "
                "Chame connect() primeiro (responsabilidade do send_batch)."
            )

        for tentativa in range(self.retries):
            try:
                self._smtp.send_message(mime, to_addrs=recipients)
                self._sent += 1
                self._log(f"Enviado para {recipients} (total sessão: {self._sent})")
                return True

            except smtplib.SMTPServerDisconnected:
                self._log(f"Servidor desligou (tentativa {tentativa + 1}/{self.retries}) — a reconectar")
                self.disconnect()
                self.connect()

            except smtplib.SMTPDataError as exc:
                self._log(f"SMTPDataError: {exc} (tentativa {tentativa + 1}/{self.retries})")
                if exc.smtp_code >= 500:  # permanent failure — retrying won't help
                    raise
                if tentativa == self.retries - 1:
                    raise
                time.sleep(random.uniform(5, 12))

        # Nunca deve chegar aqui (o raise acima cobre o último retry)
        return False

    # --------------------------------------------------
    # Alias de compatibilidade
    # --------------------------------------------------

    def close(self):
        """Alias de disconnect() para compatibilidade."""
        self.disconnect()
