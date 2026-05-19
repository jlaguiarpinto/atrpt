# atrpt/presentation/pessoas/pessoas_controller.py

import logging
from pathlib import Path
from typing import Optional, List

from domain.pessoas.empregado import Empregado
from infrastructure.persistence.pessoas.empregado_sqlite_repository import EmpregadoSQLiteRepository

logger = logging.getLogger(__name__)


class PessoasController:

    def __init__(self, cfg, user_context, audit_log=None):
        self.cfg          = cfg
        self.user_context = user_context
        self.audit_log    = audit_log
        self.gui          = None

        db_path    = cfg.paths.get("atrpt_db", cfg.paths_app.get("atrpt_db", ""))
        self.repo  = EmpregadoSQLiteRepository(Path(db_path))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def get_empregados(self, apenas_ativos: bool = True) -> List[Empregado]:
        try:
            return self.repo.list_all(apenas_ativos=apenas_ativos)
        except Exception as e:
            logger.error(f"Erro ao listar empregados: {e}", exc_info=True)
            return []

    def get_trabalhadores(self, situacao: str = None) -> List[Empregado]:
        """Lista trabalhadores filtrando por situação. None = todos."""
        try:
            return self.repo.list_all(situacao=situacao)
        except Exception as e:
            logger.error(f"Erro ao listar trabalhadores: {e}", exc_info=True)
            return []

    def get_empregado(self, numero: int) -> Optional[Empregado]:
        try:
            return self.repo.get_by_numero(numero)
        except Exception as e:
            logger.error(f"Erro ao obter empregado {numero}: {e}", exc_info=True)
            return None

    def pesquisar(self, texto: str, apenas_ativos: bool = True,
                  situacao: str = None) -> List[Empregado]:
        try:
            return self.repo.pesquisar(texto, apenas_ativos=apenas_ativos,
                                       situacao=situacao)
        except Exception as e:
            logger.error(f"Erro ao pesquisar trabalhadores: {e}", exc_info=True)
            return []

    def get_categorias(self) -> List[str]:
        try:
            return self.repo.get_categorias()
        except Exception:
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

    def criar_candidato(self, dados: dict) -> Optional[Empregado]:
        """Insere nova pessoa no estado candidato ('C'). Devolve o registo criado."""
        try:
            dados["ativo"] = "C"
            numero = self.repo.insert(dados)
            return self.repo.get_by_numero(numero)
        except Exception as e:
            logger.error(f"Erro ao criar candidato: {e}", exc_info=True)
            raise

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
