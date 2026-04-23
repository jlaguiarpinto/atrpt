#atrpt/infrastructure/logging/log_handler_gui.py

import logging


class GuiLogHandler(logging.Handler):

    def __init__(self, root, gui):
        super().__init__()
        self.root = root
        self.gui = gui

    def emit(self, record):

        msg = self.format(record)

        try:
            # garantir execução no thread Tkinter
            self.root.after(0, lambda: self.gui.log(msg))
        except Exception:
            pass