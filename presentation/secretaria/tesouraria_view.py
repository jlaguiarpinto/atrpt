#atrpt/presentation/secretaria/tesouraria_view.py

class TesourariaView:

    def __init__(self, gui):
        self.gui = gui

    def render(self, controller):

        self.gui.set_title("Tesouraria")

        frame = self.gui.abrir_work_area()

        self.gui.build_header(
            frame,
            "Módulo Tesouraria",
            "Gestão financeira"
        )

        opcoes = [
            ("Processar Extrato", controller.processar_extrato),
            ("Registar Movimentos", controller.registar_movimentos),
            ("Débitos Diretos", controller.abrir_dd),
            ("Produzir DD", controller.produzir_dd),
            ("Enviar Recibos", controller.enviar_recibos),
            ("Menu Inicial", lambda: controller.start()),
        ]

        self.gui.build_button_row(frame, opcoes)

        self.gui.log("Ecrã Tesouraria carregado.")