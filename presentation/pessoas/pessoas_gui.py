# atrpt/presentation/pessoas/pessoas_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG


class PessoasGUI(BG):
    """Menu principal do módulo Pessoas."""

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.set_title("Pessoas")
        self._build_main_menu()
        self._restore_root_menu = self._build_main_menu

    def _build_main_menu(self):
        self.abrir_work_area()
        opcoes = [
            ("Consultar Trabalhadores", self._consultar),
            ("Listar Trabalhadores",    self._listar),
            ("Novo Candidato",          self._novo_candidato),
            ("Gerar Documento",         self._gerar_documento),
        ]
        self.build_menu_buttons(opcoes)

    def _consultar(self):
        from presentation.pessoas.empregado_consulta_gui import EmpregadoConsultaGUI
        self.show_view(EmpregadoConsultaGUI, self.controller)

    def _listar(self):
        from presentation.pessoas.trabalhador_lista_gui import TrabalhadorListaGUI
        self.show_view(TrabalhadorListaGUI, self.controller)

    def _novo_candidato(self):
        from presentation.pessoas.candidato_novo_gui import CandidatoNovoGUI
        CandidatoNovoGUI(self.root, self.controller)

    def _gerar_documento(self):
        from presentation.pessoas.trabalhador_doc_gui import TrabalhadorDocGUI
        self.show_view(TrabalhadorDocGUI, self.controller)
