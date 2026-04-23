#atrpt/infrastructure/system/timeout_logger.py

import logging
from functools import partial
import threading

class TimeoutLogger:
    """Logger que não bloqueia se o handler demorar"""
    
    def __init__(self, logger, timeout=0.1):
        self.logger = logger
        self.timeout = timeout
    
    def _log_with_timeout(self, level, msg, *args, **kwargs):
        def log():
            getattr(self.logger, level)(msg, *args, **kwargs)
        
        thread = threading.Thread(target=log, daemon=True)
        thread.start()
        thread.join(self.timeout)  # Espera no máximo timeout segundos
    
    def info(self, msg, *args, **kwargs):
        self._log_with_timeout('info', msg, *args, **kwargs)
    
    def error(self, msg, *args, **kwargs):
        self._log_with_timeout('error', msg, *args, **kwargs)
    
    def warning(self, msg, *args, **kwargs):
        self._log_with_timeout('warning', msg, *args, **kwargs)

