#atrpt/application/aprovisionamento/list_fornecedores_usecase.py
from infrastructure.persistence.aprovisionamento.fornecedor_repository import FornecedorRepository
from domain.aprovisionamento.fornecedor import Fornecedor
class ListFornecedoresUseCase:

    def __init__(self, repo: FornecedorRepository):
        self.repo = repo

    def execute(self) -> list[Fornecedor]:
        return self.repo.list_all()