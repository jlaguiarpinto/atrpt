#atrpt /application/email/email_message.py
#Email message data class

from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable

@dataclass
class EmailMessage:
    to: list[str]
    subject: str
    html_body: str
    attachments: Iterable[Path] = field(default_factory=list)
    inline_images: dict[str, Path] = field(default_factory=list)
    bcc: list[str] = field(default_factory=list)

    def __post_init__(self):
        # Garantir que attachments é sempre uma lista
        if self.attachments is None:
            self.attachments = []
        elif isinstance(self.attachments, (str, Path)):
            # Se for um único Path ou string, converter para lista
            self.attachments = [self.attachments]
        elif not isinstance(self.attachments, list):
            # Se for outro iterável, converter para lista
            try:
                self.attachments = list(self.attachments)
            except TypeError:
                self.attachments = [self.attachments]
        
        # Garantir que bcc é lista
        if self.bcc is None:
            self.bcc = []
        elif not isinstance(self.bcc, list):
            self.bcc = list(self.bcc) if self.bcc else []