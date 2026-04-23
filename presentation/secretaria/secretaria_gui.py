#atrpt/presentation/secretaria_gui.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from presentation.shared.base_gui import BaseGui as BG


class SecretariaGUI(BG):

    OPCOES = {
        "Tesouraria": "abrir_tesouraria",
        "PIM": "abrir_pim",
        "Ponto": "abrir_ponto",
        "Saldos": "abrir_saldos",
    }

    def __init__(self, root, controller):

        BG.__init__(self, root, controller)

        self.controller = controller

        self._build_ui()

    def _build_ui(self):

        # topo
        self.set_title("Secretaria")

        # área de trabalho
        frame = self.abrir_work_area()

        self.build_header(
            frame,
            "Módulo Secretaria",
            "Menu principal"
        )

        opcoes = [
            (texto, getattr(self.controller, metodo))
            for texto, metodo in self.OPCOES.items()
        ]

        self.build_menu_buttons(opcoes)

        # --------------------------------------------------
    def show_welcome(self, nome):
        if hasattr(self, 'lbl_welcome'):
            self.lbl_welcome.config(text=f"Bem-vindo, {nome}")

    def ask_yes_no(self, titulo, mensagem):
        #return messagebox.askyesno(titulo, mensagem)
        return self.confirm(titulo, mensagem)

    def inform_user(self, titulo, mensagem):
        #messagebox.showinfo(titulo, mensagem)
        self.informuser(titulo, mensagem, "info")
