# atrpt/domain/pessoas/empregado.py

from dataclasses import dataclass, field
from datetime import datetime, date
from typing import Optional


class SituacaoTrabalhador:
    ATIVO      = 'A'  # em funções
    INATIVO    = 'I'  # saiu da organização
    BAIXA      = 'B'  # baixa prolongada
    LICENCA    = 'L'  # licença sem vencimento
    SUSPENSAO  = 'S'  # suspensão de contrato
    PRE_REFORMA = 'P' # pré-reforma
    CANDIDATO  = 'C'  # candidato (ainda não admitido)

    TODOS = {'A', 'B', 'L', 'S', 'P', 'I', 'C'}
    # trabalhadores que contam como "em serviço" para efeitos de listagem
    EM_SERVICO = {'A', 'B', 'L', 'S', 'P'}


@dataclass
class Empregado:
    numero:             int
    nome:               str
    ativo:              str                    # ver SituacaoTrabalhador
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
    nome_conhecido:     Optional[str] = None

    # contacto de emergência
    emerg_nome:         Optional[str] = None
    emerg_relacao:      Optional[str] = None
    emerg_telemovel:    Optional[str] = None

    # documento de identificação (tipo explícito: CC, BI, Passaporte, …)
    doc_ident_tipo:     Optional[str] = None

    # financeiro
    nib:                Optional[str] = None
    banco:              Optional[str] = None

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
        # compatibilidade — verdadeiro apenas se estritamente ativo
        return self.ativo == SituacaoTrabalhador.ATIVO

    @property
    def em_servico(self) -> bool:
        # inclui baixa, licença, suspensão e pré-reforma
        return self.ativo in SituacaoTrabalhador.EM_SERVICO

    @property
    def nome_abreviado(self) -> str:
        partes = self.nome.split()
        if len(partes) <= 2:
            return self.nome
        return f"{partes[0]} {partes[-1]}"
