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
            self.gui.escreveOutput(msg)
            self.root.update_idletasks()
        except Exception:
            pass