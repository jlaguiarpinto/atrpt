#atrpt/presentation/secretaria_gui.py

import tkinter as tk
from tkinter import ttk
from tkinter import messagebox
from presentation.shared.base_gui import BaseGui as BG


class SecretariaGUI(BG):

    OPCOES = {
        "Tesouraria":  "abrir_tesouraria",
        "PIM":         "abrir_menu_pim",
        "Ponto":       "abrir_ponto",
        "Residentes":  "abrir_residentes",
    }

    def __init__(self, root, controller):

        BG.__init__(self, root, controller)

        self.controller = controller

        self._build_ui()

    def _build_ui(self):
        self.set_title("Secretaria")
        self._restore_root_menu = self._show_home
        self._show_home()

    def _show_home(self):
        frame = self.abrir_work_area()
        opcoes = [
            (texto, getattr(self.controller, metodo))
            for texto, metodo in self.OPCOES.items()
        ]
        self.build_menu_buttons(opcoes)
        return frame

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
