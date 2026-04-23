# atrpt/infrastructure/system/power_management.py

import sys
import platform

class PowerManagement:
    """Gerencia o estado de energia do sistema para evitar suspensão durante operações longas"""
    
    @staticmethod
    def prevent_sleep():
        """Impede o sistema de entrar em suspensão/hibernação durante a execução"""
        if platform.system() == 'Windows':
            try:
                import ctypes
                # ES_CONTINUOUS = 0x80000000
                # ES_SYSTEM_REQUIRED = 0x00000001
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000001)
                return True
            except Exception:
                return False
        elif platform.system() == 'Darwin':  # macOS
            try:
                import subprocess
                # Prevenir sleep (caffeinate -d impede display sleep)
                subprocess.run(['caffeinate', '-d', '-t', '1'], 
                             capture_output=True, timeout=0.1)
                return True
            except Exception:
                return False
        elif platform.system() == 'Linux':
            try:
                import subprocess
                # Prevenir sleep via systemd-inhibit
                subprocess.run(['systemd-inhibit', '--why=Envio de emails', 'sleep', '1'],
                             capture_output=True, timeout=0.1)
                return True
            except Exception:
                return False
        return False
    
    @staticmethod
    def allow_sleep():
        """Permite o sistema voltar a suspender normalmente"""
        if platform.system() == 'Windows':
            try:
                import ctypes
                # ES_CONTINUOUS = 0x80000000 (sem flags de prevenção)
                ctypes.windll.kernel32.SetThreadExecutionState(0x80000000)
                return True
            except Exception:
                return False
        # macOS e Linux: a prevenção termina automaticamente quando o processo termina
        return False
    
    @staticmethod
    def is_windows():
        return platform.system() == 'Windows'
    
    @staticmethod
    def is_macos():
        return platform.system() == 'Darwin'
    
    @staticmethod
    def is_linux():
        return platform.system() == 'Linux'


class PowerManagementContext:
    """Context manager para usar com 'with'"""
    
    def __init__(self, prevent: bool = True):
        self.prevent = prevent
    
    def __enter__(self):
        if self.prevent:
            PowerManagement.prevent_sleep()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.prevent:
            PowerManagement.allow_sleep()