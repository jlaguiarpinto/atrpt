#atrpt/presentation/secretaria/farmacia_view.py

class FarmaciaView:

    def __init__(self, gui):
        self.gui = gui

    def render(self, controller):

        self.gui.set_title("PIM - Farmácia")

        frame = self.gui.abrir_work_area()

        self.gui.build_header(
            frame,
            "Módulo Farmácia",
            "Processamento PIM"
        )

        opcoes = [
            ("Ler Faturas", controller.processar_faturacao),
            ("Gerar novo PIM", controller.produzir_pim),
            ("Preparar Faturas", controller.preparar_faturas),
            ("Enviar Faturas", controller.enviar_faturas),
            ("Menu Inicial", lambda: controller.start()),
        ]

        self.gui.build_button_row(frame, opcoes)

        self.gui.log("Ecrã PIM carregado.")


