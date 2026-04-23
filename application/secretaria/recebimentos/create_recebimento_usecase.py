# atrpt/application/secretaria/recebimentos/create_recebimento_usecase.py

from datetime import datetime
from domain.finance.recebimento import Recebimento

class CreateRecebimentoUseCase:

    def __init__(self, receb_repo, conta_repo,
                 mensalidade_handler,
                 pim_handler,
                 outros_handler):

        self.receb_repo = receb_repo
        self.conta_repo = conta_repo
        self.mensalidade_handler = mensalidade_handler
        self.pim_handler = pim_handler
        self.outros_handler = outros_handler

    def execute(self, data, origem, tipo,
                entidade_tipo, entidade_id,
                valor, referencia, user):

        # 1. Guardar recebimento
        receb_id = self.receb_repo.save(...)

        # 2. atualizar conta corrente
        self.conta_repo.registar_credito(...)

        # 3. Comportamento específico
        if tipo in ("mensalidade", "quota"):
            self.mensalidade_handler.processar(...)

        elif tipo == "pim":
            self.pim_handler.processar(...)

        else:
            self.outros_handler.processar(...)

        return receb_id