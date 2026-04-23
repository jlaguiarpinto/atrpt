# atrpt/domain/fornecedores/fornecedor.py

from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Fornecedor:
    id: Optional[int] = None
    nome: str = ""
    email: Optional[str] = None
    nif: Optional[str] = None
    iban: Optional[str] = None
    tipo_fornecedor: Optional[str] = None
    tipo_relacao: Optional[str] = None
    setor: Optional[str] = None
    metodo_pagamento: Optional[str] = None   # TB | DD | MB | OU

    # contacto comercial
    comercial_nome: Optional[str] = None
    comercial_email: Optional[str] = None
    comercial_telemovel: Optional[str] = None

    # contacto administrativo
    administrativo_nome: Optional[str] = None
    administrativo_email: Optional[str] = None
    administrativo_telemovel: Optional[str] = None
