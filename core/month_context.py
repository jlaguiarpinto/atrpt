#atrpt/core/month_context.py

from datetime import date


from dataclasses import dataclass
from pathlib import Path
from core.paths import resolver_path_template


@dataclass
class MonthContext:
    ano: int
    mes: int
    paths: dict[str, Path]

def build_month_context(cfg, modulo: str, mes: int):

    ano = resolver_ano(mes)

    if modulo == "ponto":

        base_dir = Path(cfg.paths["ponto_dir"])
        pasta_mes = base_dir / f"{ano}{int(mes):02}"
        pasta_mes.mkdir(parents=True, exist_ok=True)
        paths = {
            "pasta_mes": pasta_mes,
            "ficheiro_resumo": pasta_mes / f"{ano}{int(mes):02}_Resumo.xlsx"
        }
        return MonthContext(
            ano=ano,
            mes=mes,
            paths=paths
        )

def resolver_ano(mes: int) -> int:
    hoje = date.today()
    ano=hoje.year
    if int(mes) > hoje.month == 1:
        return ano - 1
    return ano

