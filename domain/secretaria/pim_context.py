#atrpt/domain/secretaria/pim/pim_context.py
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

@dataclass
class PimContext:

    # período
    ano: str
    mes: str

    # execução
    modo_teste: bool
    email_teste: Optional[str]

    # ---------- ledger ----------
    pim_file: Path                # PIM.xlsx (estado corrente)

    # ---------- histórico ----------
    pim_mensal_file: Path        # PIM_2026_03.xlsx

    # ---------- inputs ----------
    pim_mensal_dir: Path          # diretório dos PDFs
    csag_file: Path               # resumo farmácia

    # ---------- datasets intermédios ----------
    pdf_faturas: Path                # todas as faturas (1 linha = 1 fatura)
    faturacao_residentes_file: Path          # agregação por residente (editável)
    envio_faturas_file: Path

    # ---------- outputs ----------
    diferencas_file: Path

    #------------templates-------------
    template_email: Optional[Path] = None 

