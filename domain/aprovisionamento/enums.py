# atrpt/ domain/aprovisionamento/enums.py

from enum import Enum

class PedidoEstado(Enum):
    criado = "criado"
    pendente = "pendente"
    autorizado = "autorizado"
    encomendado = "encomendado"
    concluido = "concluido"
    cancelado = "cancelado"