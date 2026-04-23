# atrpt/presentation/secretaria/debitodireto_gui.py

class DebitoDiretoGUI:

    def __init__(self, parent, controller):
        self.parent = parent
        self.controller = controller
        self.gui = controller.gui  # ← BaseGui

        self._build()

    # --------------------------------------------------

    def _build(self):

        # limpar área de trabalho corretamente
        frame = self.gui.abrir_work_area()

        # título
        self.gui.set_title("Débitos Diretos")

        # botões
        botoes = [
            ("Produzir Débitos Diretos", self._produzir_dd),
            ("Processar Débitos Diretos", self._processar_dd),
            ("Voltar", self._voltar),
        ]

        self.gui.build_button_row(frame, botoes)

    # --------------------------------------------------

    def _produzir_dd(self):

        try:
            path = self.controller.produzir_dd()
            self.gui.log_ok(f"DD produzido: {path}")

        except Exception as e:
            self.gui.log_error(str(e))

    # --------------------------------------------------

    def _processar_dd(self):

        try:
            n = self.controller.processar_dd()
            self.gui.log_ok(f"{n} movimentos processados")

        except Exception as e:
            self.gui.log_error(str(e))

    # --------------------------------------------------

    def _voltar(self):
        self.gui.go_back()