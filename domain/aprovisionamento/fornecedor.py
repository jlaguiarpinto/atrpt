# atrpt/domain/aprovisionamento/fornecedor.py

from dataclasses import dataclass, field
from typing import Optional

TIPOS_FORNECEDOR = [
    "Alimentação e Bebidas",
    "Higiene e Conforto",
    "Saúde e Bem Estar",
    "Lazer e Cultura",
    "Manutenção Imóveis",
    "Manutenção Equipamentos",
    "Deslocação e Transportes",
    "Comunicações",
    "Energia",
    "Outros",
]

TIPOS_RELACAO = [
    "Pontual", "Contrato", "Preferencial",
    "Avençado", "Prestador", "Suspenso",
]


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
    atividade: Optional[str] = None

    # contacto comercial
    comercial_nome: Optional[str] = None
    comercial_email: Optional[str] = None
    comercial_telemovel: Optional[str] = None

    # contacto administrativo
    administrativo_nome: Optional[str] = None
    administrativo_email: Optional[str] = None
    administrativo_telemovel: Optional[str] = None
