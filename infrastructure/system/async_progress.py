#atrpt/infrasyructure/system/async_progress.py

import threading
from queue import Queue

class AsyncProgress:
    def __init__(self, on_progress):
        self.on_progress = on_progress
        self.queue = Queue()
        self.running = True
        self.thread = threading.Thread(target=self._process, daemon=True)
        self.thread.start()
    
    def send(self, message):
        """Envia mensagem sem bloquear"""
        self.queue.put(message)
    
    def _process(self):
        while self.running:
            try:
                msg = self.queue.get(timeout=0.1)
                if self.on_progress:
                    self.on_progress(msg)
            except:
                pass
    
    def stop(self):
        self.running = False


