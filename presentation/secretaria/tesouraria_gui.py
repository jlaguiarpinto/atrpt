# atrpt/presentation/secretaria/tesouraria_gui.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG

class TesourariaGUI(BG):
    
    OPCOES_TESOURARIA = {
        "Processar Extrato": "processar_extrato",
        "Registar Movimentos": "registar_movimentos",
        "Enviar Recibos": "enviar_recibos",
        "Débitos Diretos": "abrir_dd",
        "Voltar": "voltar_menu"
    }

    def __init__(self, root, controller):
        BG.__init__(self, root, controller)
        self.controller = controller
        self._build_ui()

    def _build_ui(self):

        for w in self.frame_menu.winfo_children():
            w.destroy()
        
        frame_btns = tk.Frame(self.frame_work, bg=self.BG)
        frame_btns.pack(pady=40)
        
        btn_width = 25
        for texto, metodo in self.OPCOES_TESOURARIA.items():
            comando = getattr(self.controller, metodo, None)
            if comando:
                tk.Button(
                    frame_btns,
                    text=texto,
                    width=btn_width,
                    font=self.FONT_BUTTON,
                    bg=self.BTN_BG,
                    command=comando
                ).pack(side="left", padx=10)