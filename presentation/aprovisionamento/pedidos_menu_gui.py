# atrpt/presentation/pedidos_menu_gui.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG

class PedidosMenuGUI(BG):
    """
    Sub-menu para gestão de Pedidos de Compra
    """

    def __init__(self, parent, controller):
        self.controller = controller  # Guardar referência ao controller
        super().__init__(parent, controller)
        # O __init__ do BG provavelmente já guarda o controller,
        # mas vamos garantir definindo explicitamente
        if not hasattr(self, 'controller'):
            self.controller = controller
        
        self._build()

    def _build(self):
        """Constrói a interface do sub-menu de pedidos"""
        frame = self.abrir_work_area()

        # Botões no menu superior
        opcoes = [
            ("Criar Pedido", self._criar_pedido),
            ("Adicionar Proposta", self._adicionar_proposta),
            ("Listar Pedidos", lambda: self.controller.listar_pedidos()),
            ("Listar Pendentes", lambda: self.controller.listar_pendentes()),
            ("Autorizar", self._autorizar),
            ("Encomendar", self._encomendar),
        ]

        self.build_menu_buttons(opcoes)

        # Botões adicionais na área de trabalho
        self.add_button(frame, "Consultar Pedido", self._consultar_pedido)
        self.add_button(frame, "Histórico", lambda: self.controller.historico_pedidos)
        self.add_button(frame, "Exportar Pedidos", lambda: self.controller.exportar_pedidos)

        # Botão voltar
        self.add_button(frame, "← Voltar", self.go_back)

    def _criar_pedido(self):
        """Abre formulário para criar novo pedido"""
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        from presentation.aprovisionamento.pedido_form_gui import PedidoFormGUI
        PedidoFormGUI(win, self.controller)
        self.root.wait_window(win)

    def _adicionar_proposta(self):
        """Abre formulário para adicionar proposta a pedido existente"""
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        from presentation.aprovisionamento.pedido_proposta_gui import JuntarPropostaGUI
        JuntarPropostaGUI(win, self.controller)
        self.root.wait_window(win)

    def _autorizar(self):
        """Abre formulário para autorizar pedido"""
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        from presentation.aprovisionamento.pedido_autorizar_gui import AutorizarGUI
        AutorizarGUI(win, self.controller)
        self.root.wait_window(win)

    def _encomendar(self):
        """Abre formulário para marcar pedido como encomendado"""
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        from presentation.aprovisionamento.pedido_encomendar_gui import EncomendarGUI
        EncomendarGUI(win, self.controller)
        self.root.wait_window(win)

    def _consultar_pedido(self):
        """Consulta um pedido específico"""
        numero = self.pedirInput("Consultar Pedido", "Nº do Pedido:")
        if numero:
            self.controller.consultar_pedido(numero)
