#Atrpt / domain/secretaria/recebimentos/importar_extrato_usecase.py
from pathlib import Path
from datetime import datetime
import hashlib
import csv

from domain.secretaria.recebimentos.recebimento import Recebimento
from domain.secretaria.recebimentos.enums import TipoRecebimento


class ImportarExtratoUseCase:

    def __init__(self, recebimento_repository):
        self.repo = recebimento_repository

    # -----------------------------------------------------

    def execute(self, csv_path: Path):

        criados = 0
        ignorados = 0

        with open(csv_path, newline="", encoding="utf-8") as file:
            reader = csv.DictReader(file)

            for row in reader:

                data = datetime.strptime(row["data"], "%d-%m-%Y")
                valor = float(row["valor"].replace(",", "."))
                descricao = row["Descricao"]

                tipo = self._inferir_tipo(descricao)

                if self.repo.exists_movimento(data, valor, descricao):
                    ignorados += 1
                    continue

                recebimento_id = self._gerar_id(data, valor, descricao)

                recebimento = Recebimento(
                    id=recebimento_id,
                    data=data,
                    valor=valor,
                    tipo=tipo,
                    descricao_banco=descricao
                )

                self.repo.save(recebimento)
                criados += 1

        return {
            "criados": criados,
            "ignorados": ignorados
        }

    # -----------------------------------------------------

    def _gerar_id(self, data, valor, descricao):

        raw = f"{data.isoformat()}|{valor}|{descricao}"
        return hashlib.sha256(raw.encode()).hexdigest()

    # -----------------------------------------------------

    def _inferir_tipo(self, descricao: str) -> TipoRecebimento:

        desc = descricao.lower()

        if "debito direto" in desc:
            return TipoRecebimento.DEBITO_DIRETO

        if "atm" in desc:
            return TipoRecebimento.ATM

        return TipoRecebimento.TRANSFERENCIA