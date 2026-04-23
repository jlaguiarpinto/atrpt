#atrpt /domain/secretaria/recebimentos/enums.py
class TipoRecebimento(Enum):
    TRANSFERENCIA = "transferencia"
    DEBITO_DIRETO = "debito_direto"
    DINHEIRO = "dinheiro"
    ATM = "atm"

class EstadoRecebimento(Enum):
    IMPORTADO = "importado"
    IDENTIFICADO = "identificado"
    VALIDADO = "validado"
    APLICADO = "aplicado"
    REJEITADO = "rejeitado"