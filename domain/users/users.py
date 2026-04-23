# atrpt/domain/users/users.py

from dataclasses import dataclass, field
from typing import Optional, List


@dataclass
class user:
    username:    str
    nome:        str
    email:       str
    nif:         Optional[str]
    ativo:       bool
    permissions: List[str] = field(default_factory=list)
    perfil:      Optional[str] = None   # Dir | DL | DCD | SG | RH | CS | Sec
