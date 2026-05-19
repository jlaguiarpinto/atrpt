# application/fornecedores/import_fornecedores_usecase.py

import openpyxl

from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository


class ImportFornecedoresFromExcelUseCase:

    def __init__(self, repository: FornecedorRepository):
        self.repository = repository

    def execute(self, excel_path: str) -> int:

        wb = openpyxl.load_workbook(excel_path, read_only=True, data_only=True)
        ws = wb.active

        rows = list(ws.iter_rows(values_only=True))
        if not rows:
            raise ValueError("Ficheiro Excel vazio.")

        headers = [str(h).strip() if h else "" for h in rows[0]]

        if "nome" not in [h.lower() for h in headers]:
            raise ValueError("Excel deve conter coluna 'nome'")

        # mapa case-insensitive: nome_lower -> índice
        col = {h.lower(): i for i, h in enumerate(headers)}

        def _get(row, key):
            idx = col.get(key.lower())
            if idx is None:
                return None
            v = row[idx]
            return str(v).strip() if v is not None else None

        count = 0
        for row in rows[1:]:
            nome = _get(row, "nome")
            if not nome:
                continue

            self.repository.save_from_dict({
                "nome":     nome,
                "nif":      _get(row, "nif"),
                "email":    _get(row, "email"),
                "iban":     _get(row, "iban"),
                "telefone": _get(row, "telefone"),
            })
            count += 1

        wb.close()
        return count
