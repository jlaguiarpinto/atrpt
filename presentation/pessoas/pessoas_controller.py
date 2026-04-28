# atrpt/presentation/pessoas/pessoas_controller.py

import logging
from pathlib import Path
from typing import Optional, List

from domain.pessoas.empregado import Empregado
from infrastructure.persistence.pessoas.empregado_repository import EmpregadoRepository

logger = logging.getLogger(__name__)


class PessoasController:

    def __init__(self, cfg, user_context, audit_log=None):
        self.cfg          = cfg
        self.user_context = user_context
        self.audit_log    = audit_log
        self.gui          = None

        accdb      = Path(cfg.paths.get("rh_accdb",
                         cfg.paths_app.get("rh_accdb", "")))
        self.repo  = EmpregadoRepository(accdb)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def get_empregados(self, apenas_ativos: bool = True) -> List[Empregado]:
        try:
            return self.repo.list_all(apenas_ativos=apenas_ativos)
        except Exception as e:
            logger.error(f"Erro ao listar empregados: {e}", exc_info=True)
            return []

    def get_empregado(self, numero: int) -> Optional[Empregado]:
        try:
            return self.repo.get_by_numero(numero)
        except Exception as e:
            logger.error(f"Erro ao obter empregado {numero}: {e}", exc_info=True)
            return None

    def pesquisar(self, texto: str, apenas_ativos: bool = True) -> List[Empregado]:
        try:
            return self.repo.pesquisar(texto, apenas_ativos=apenas_ativos)
        except Exception as e:
            logger.error(f"Erro ao pesquisar empregados: {e}", exc_info=True)
            return []

    def get_locais(self) -> List[str]:
        try:
            todos = self.repo.list_all(apenas_ativos=False)
            return sorted({e.local for e in todos if e.local})
        except Exception:
            return []

    def get_sectores(self) -> List[str]:
        try:
            todos = self.repo.list_all(apenas_ativos=False)
            return sorted({e.sector for e in todos if e.sector})
        except Exception:
            return []

    def guardar_empregado(self, dados: dict) -> Optional[Empregado]:
        """
        Grava alterações editáveis de um empregado (contactos, morada, notas, ativo).
        Devolve o empregado actualizado.
        """
        try:
            self.repo.update(dados)
            return self.repo.get_by_numero(dados["numero"])
        except Exception as e:
            logger.error(f"Erro ao guardar empregado {dados.get('numero')}: {e}", exc_info=True)
            raise
