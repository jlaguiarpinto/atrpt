# atrpt/presentation/associados_menu_gui.py

import tkinter as tk
from presentation.shared.base_gui import BaseGui as BG


class AssociadosMenuGUI(BG):

    def __init__(self, root, controller):
        BG.__init__(self, root, controller)
        self.root = root
        self.controller = controller
        self._frame_resumo = None
        self._frame_acoes  = None
        self.build_ui()

    # --------------------------------------------------
    # Nível 0 — menu principal
    # --------------------------------------------------

    def build_ui(self):
        frame = self.abrir_work_area()
        self.set_title("Associados")
        self.add_button(frame, "Enviar emails",            self._abrir_envio)
        self.add_button(frame, "Processamento de Quotas",  self.controller.processar_quotas)
        self.add_button(frame, "Relatórios",               self.controller.relatorios)

    # --------------------------------------------------
    # Nível 1 — área de envio de emails
    # --------------------------------------------------

    def _abrir_envio(self):
        frame = self.abrir_work_area()
        self.set_title("Associados", "Enviar Emails")

        self._frame_resumo = tk.Frame(frame, bg=self.BG)
        self._frame_resumo.pack(fill="x", padx=20, pady=(10, 0))

        self._frame_acoes = tk.Frame(frame, bg=self.BG)
        self._frame_acoes.pack(fill="x", pady=6)

        self._botoes_preparar()

    # --------------------------------------------------
    # Troca de botões consoante o estado
    # --------------------------------------------------

    def _botoes_preparar(self):
        self._limpar(self._frame_resumo)
        self._limpar(self._frame_acoes)
        self.build_button_row(self._frame_acoes, [
            ("Preparar envio", self.controller.preparar_envio),
            ("Retomar envio",  self.controller.retomar_envio),
            ("Voltar",         self.build_ui),
        ])

    def mostrar_resumo_envio(self, resumo: str):
        """Chamado pelo controller após preparação + exclusões concluídas."""
        self._limpar(self._frame_resumo)
        self._limpar(self._frame_acoes)

        tk.Label(
            self._frame_resumo,
            text=resumo,
            font="Verdana 10",
            bg=self.BG,
            fg=self.FG,
            justify="left",
        ).pack(anchor="w", padx=10, pady=6)

        self.build_button_row(self._frame_acoes, [
            ("Analisar",   self.controller.analisar_mensagens),
            ("Enviar",     self.controller.enviar),
            ("Novo envio", self.controller.preparar_envio),
            ("Voltar",     self.build_ui),
        ])

    # --------------------------------------------------
    # Log — usa o txt_output herdado do BaseGui
    # --------------------------------------------------

    def log(self, mensagem):
        self.escreveOutput(mensagem)

    # --------------------------------------------------
    # Utilitário
    # --------------------------------------------------

    def _limpar(self, frame):
        if frame:
            for w in frame.winfo_children():
                w.destroy()
