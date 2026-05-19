# presentation/secretaria/residentes_menu_view.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG


class ResidentesMenuView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)

    def _post_init(self):
        root = getattr(self, "_root_gui", self)
        self.build_menu_buttons([("← Menu", root.go_back)])
        frame = tk.Frame(self.frame_work, bg=self.BG)
        frame.pack(fill="both", expand=True, pady=20)
        opcoes = [
            ("Residentes Activos",      self.controller.abrir_residentes_ativos),
            ("Candidatos / Pendentes",  self.controller.abrir_candidatos),
        ]
        root.build_button_row(frame, opcoes)
