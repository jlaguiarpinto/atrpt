# atrpt/presentation/aprovisionamento/pedidos_gui.py

from presentation.shared.base_gui import BaseGui as BG


class EncomendasGUI(BG):
    """
    Sub-menu para listagem e gestão de aprovisionamento
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self.set_title("Encomendas", "Encomendas")
        self._build()

    def _build(self):
        """Constrói a interface do sub-menu de aprovisionamento"""
        frame = self.abrir_work_area()

        self.build_header(
            frame,
            "Encomendas Realizadas",
            "Consulta e acompanhamento de aprovisionamento"
        )

        # Botões no menu superior
        opcoes = [
            ("Listar Pendentes", self.controller.listar_aprovisionamento_pendentes),
            ("Listar Entregues", self.controller.listar_aprovisionamento_entregues),
            ("Acompanhar", self._acompanhar_encomenda),
            ("Marcar Entregue", self._marcar_entregue)
        ]

        self.build_menu_buttons(opcoes)

        # Botões adicionais na área de trabalho
        self.add_button(frame, "Consultar por Período", self.controller.consultar_por_periodo)
        self.add_button(frame, "Exportar Relatório", self.controller.exportar_relatorio_aprovisionamento)

        # Botão voltar
        self.add_button(frame, "← Voltar", self.go_back)

    def _acompanhar_encomenda(self):
        """Acompanha uma encomenda específica"""
        numero = self.pedirInput("Acompanhar", "Nº da Encomenda:")
        if numero:
            self.controller.acompanhar_encomenda(numero)

    def _marcar_entregue(self):
        """Marca uma encomenda como entregue"""
        numero = self.pedirInput("Marcar Entregue", "Nº da Encomenda:")
        if numero:
            confirm = self.confirm("Confirmar", f"Marcar encomenda {numero} como entregue?")
            if confirm:
                self.controller.marcar_entregue(numero)