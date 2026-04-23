# atrpt/domain/pessoas/empregado.py

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


@dataclass
class Empregado:
    numero:             int
    nome:               str
    ativo:              str                    # 'A' | 'I'
    local:              Optional[str] = None
    sector:             Optional[str] = None

    # identificação
    nif:                Optional[str] = None
    niss:               Optional[str] = None
    numero_utente:      Optional[str] = None
    cc:                 Optional[str] = None
    data_validade_cc:   Optional[date] = None

    # dados pessoais
    data_nascimento:    Optional[date] = None
    estado_civil:       Optional[str] = None
    genero:             Optional[str] = None
    naturalidade:       Optional[str] = None
    nacionalidade:      Optional[str] = None

    # contacto
    morada:             Optional[str] = None
    cp:                 Optional[str] = None
    localidade:         Optional[str] = None
    telefone:           Optional[str] = None
    telemovel:          Optional[str] = None
    email:              Optional[str] = None

    # financeiro
    nib:                Optional[str] = None

    # contrato
    tipo_contrato:      Optional[str] = None
    data_admissao:      Optional[date] = None
    data_cessacao:      Optional[date] = None
    categoria_admissao: Optional[str] = None
    categoria_atual:    Optional[str] = None
    antiguidade:        Optional[int] = None

    # remuneração
    vencimento:         Optional[float] = None
    diuturnidades:      Optional[int] = None
    valor_diuturnidades: Optional[float] = None

    # outros
    notas:              Optional[str] = None

    @property
    def ativo_bool(self) -> bool:
        return self.ativo == 'A'

    @property
    def nome_abreviado(self) -> str:
        partes = self.nome.split()
        if len(partes) <= 2:
            return self.nome
        return f"{partes[0]} {partes[-1]}"
