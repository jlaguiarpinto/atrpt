# atrpt/infrastructure/system/non_blocking_log_handler.py

import logging
import queue
import threading


class NonBlockingLogHandler(logging.Handler):
    """Handler que processa logs em thread separada — não bloqueia o thread principal."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.queue   = queue.Queue()
        self.running = True
        self.thread  = threading.Thread(target=self._process, daemon=True)
        self.thread.start()

    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            pass  # perde o registo se a fila estiver cheia

    def _process(self):
        while self.running:
            try:
                record = self.queue.get(timeout=0.5)
                super().emit(record)
            except Exception:
                pass

    def close(self):
        self.running = False
        super().close()


class NonBlockingFileHandler(logging.FileHandler):
    """FileHandler não-bloqueante — escreve em ficheiro num thread de fundo."""

    def __init__(self, filename, mode="a", encoding="utf-8", delay=False):
        super().__init__(filename, mode=mode, encoding=encoding, delay=delay)
        self.queue   = queue.Queue()
        self.running = True
        self.thread  = threading.Thread(target=self._process, daemon=True)
        self.thread.start()

    def emit(self, record):
        try:
            self.queue.put_nowait(record)
        except queue.Full:
            pass

    def _process(self):
        while self.running:
            try:
                record = self.queue.get(timeout=0.5)
                super().emit(record)
            except Exception:
                pass

    def close(self):
        self.running = False
        super().close()


# Handler de raiz — activo para toda a aplicação
_root_handler = NonBlockingLogHandler()
_root_handler.setFormatter(
    logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
)
logging.getLogger().addHandler(_root_handler)
