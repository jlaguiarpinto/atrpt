# presentation/secretaria/pim_menu_view.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG


class PimMenuView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)

    def _post_init(self):
        root = getattr(self, '_root_gui', self)
        self.build_menu_buttons([("← Menu", root.go_back)])
        frame = tk.Frame(self.frame_work, bg=self.BG)
        frame.pack(fill="both", expand=True, pady=20)

        opcoes = [
            ("Processar PIM", self.controller.abrir_pim),
            ("PIM em curso",  self.controller.abrir_pim_em_curso),
            ("Histórico PIM", self.controller.abrir_saldos),
        ]
        root.build_button_row(frame, opcoes)
