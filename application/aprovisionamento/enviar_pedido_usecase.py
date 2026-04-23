# application/aprovisionamento/enviar_pedido_usecase.py

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Pedido
from application.email.email_message import EmailMessage

class EnviarPedidoUseCase:

    def __init__(self, pedido_repo, fornecedor_repo, emailer):
        self.pedido_repo = pedido_repo
        self.fornecedor_repo = fornecedor_repo
        self.emailer = emailer 

    def execute(self, numero: str):

        pedido = self.pedido_repo.get_by_numero(numero)
        if not pedido:
            raise ValueError("Pedido não encontrado")

        proposta = pedido.proposta_selecionada
        if not proposta:
            raise ValueError("Sem proposta selecionada")

        fornecedor = self.fornecedor_repo.get_by_id(proposta.fornecedor_id)
        if not fornecedor:
            raise ValueError("Fornecedor não encontrado")

        if not fornecedor.email:
            raise ValueError("Fornecedor sem email")

        # valida autorização
        valor = proposta.valor
        aut1 = pedido.autorizacao_1_por
        aut2 = pedido.autorizacao_2_por

        if valor > 200 and not (aut1 and aut2):
            raise ValueError("Faltam autorizações")
        if valor <= 200 and not aut1:
            raise ValueError("Falta autorização")

        # envio
        self.emailer.send(
            to=[fornecedor.email],
            subject=f"Pedido {pedido.numero}",
            html=f"""
            <p>Segue pedido {pedido.numero}</p>
            <p>{pedido.descricao}</p>
            """,
            attachments=[proposta.pdf_path]
        )

        pedido.marcar_enviado()
        self.pedido_repo.save(pedido)

        return pedido
    
    def _build_body(self, pedido: Pedido) -> str:

        proposta = pedido.proposta_selecionada

        return f"""
        <p>Exmos. Senhores,</p>

        <p>Segue pedido <strong>{pedido.numero}</strong>.</p>

        <ul>
            <li>Centro de custo: {pedido.centro_custo}</li>
            <li>Descricao: {pedido.descricao}</li>
            <li>valor: {proposta.valor if proposta else "-"}</li>
        </ul>

        <p>Com os melhores cumprimentos,</p>
        """
    
    def pode_encomendar(self, numero):

        pedido = self.repo.get_by_numero(numero)

        if pedido.estado == PedidoEstado.encomendado:
            return False

        valor = pedido.proposta_selecionada.valor if pedido.proposta_selecionada else 0

        aut1 = pedido.autorizacao_1_por
        aut2 = pedido.autorizacao_2_por

        if valor <= 200:
            return bool(aut1)

        return bool(aut1) and bool(aut2)
    
    def encomendar(self, numero):

        if not self.pode_encomendar(numero):
            raise ValueError("Pedido não autorizado")

        pedido = self.repo.get_by_numero(numero)

        pedido.estado = PedidoEstado.encomendado

        self.repo.update(pedido)

