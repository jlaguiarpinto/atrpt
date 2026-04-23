#atrpt/domain/secretaria/ponto_context.py

from dataclasses import dataclass
from pathlib import Path

@dataclass
class PontoContext:
    ano: int
    mes: int
    ponto_dir: Path
    ponto_mensal_dir: Path