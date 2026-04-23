#atrpt/application/aprovisionamento/list_fornecedores_usecase.py
from infrastructure.persistence.fornecedor_repository import FornecedorRepositorySQL
from domain.aprovisionamento.fornecedor import Fornecedor
class ListFornecedoresUseCase:

    def __init__(self, repo: FornecedorRepositorySQL):
        self.repo = repo

    def execute(self) -> list[Fornecedor]:
        return self.repo.list_all()