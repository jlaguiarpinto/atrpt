# atrpt/application/aprovisionamento/add_proposta_usecase.py

from datetime import datetime
from typing import Optional
from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Proposta
from domain.aprovisionamento.enums import PedidoEstado


class AddPropostaUseCase:
    
    def __init__(self, repository: PedidoRepository):
        self.repository = repository
    
    def execute(
        self,
        numero: str,
        fornecedor_id: str,
        valor: float,
        documento: Optional[str] = None
    ) -> None:
        # Buscar pedido existente
        pedido = self.repository.get_by_numero(numero)
        
        if not pedido:
            raise ValueError(f"Pedido {numero} não encontrado")
        
        # Verificar se pedido ainda pode receber propostas
        if pedido.estado != "criado":
            raise ValueError(f"Não é possível adicionar proposta. Pedido está {pedido.estado.value}")
        
        # Criar nova proposta
        nova_proposta = Proposta(
            fornecedor_id=fornecedor_id,
            valor=valor,
            pdf_path=documento
        )
        
        # Adicionar ao pedido
        pedido.propostas.append(nova_proposta)
        
        # Salvar alterações
        self.repository.save(pedido)

    