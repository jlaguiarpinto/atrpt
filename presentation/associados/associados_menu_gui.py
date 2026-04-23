# atrpt/presentation/associados_menu_gui.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG


class AssociadosMenuGUI(BG):

    def __init__(self, root, controller):
        self.current_frame = None
        BG.__init__(self, root, controller)
        self.root = root
        self.controller = controller
        self.build_ui()

    def build_ui(self):                                                             #Constrói o menu principal
        frame = self.abrir_work_area()
        self.current_frame = frame
        self.set_title("Associados")
        self.add_button(frame, "Enviar emails", self._abrir_envio)
        self.add_button(frame, "Processamento de Quotas", self.controller.processar_quotas)
        self.add_button(frame, "Relatórios", self.controller.relatorios)

    def _abrir_envio(self):

        # limpar área de trabalho
        frame = self.abrir_work_area()
        self.current_frame = frame

        self.set_title("Associados", "Enviar Emails")

        # -------------------------
        # BUTTON ROW
        # -------------------------
        buttons = [
            ("Preparar", self.controller.preparar_envio),
            ("Analisar", self.controller.analisar_mensagens),
            ("Enviar", self.controller.enviar),
            ("Voltar", self.build_ui)
        ]

        self.build_button_row(frame, buttons)

        def _build_logs(self, parent):

            self.log_text = tk.Text(parent, height=12, bg="black", fg="white")
            self.log_text.pack(fill="both", expand=True, padx=10, pady=10)


