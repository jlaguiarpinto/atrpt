# atrpt/presentation/fornecedores/fornecedores_controller.py

import sqlite3
import logging
from core.logging_utils import audit

logger = logging.getLogger(__name__)


class FornecedoresController:
    """
    Controller para a app standalone de gestão de fornecedores.
    Expõe CRUD de fornecedores, importação de Excel e histórico de
    faturação mensal (E-Fatura AT) — sem dependência de aprovisionamento.
    """

    def __init__(
        self,
        gui,
        user_context,
        fornecedor_repo,
        audit_log,
        list_fornecedores_uc,
        import_fornecedores_uc=None,
        importar_efatura_uc=None,
    ):
        self.gui = gui
        self.user = user_context
        self.fornecedor_repo = fornecedor_repo
        self.audit_log = audit_log
        self.list_fornecedores_uc = list_fornecedores_uc
        self.import_fornecedores_uc = import_fornecedores_uc
        self.importar_efatura_uc = importar_efatura_uc

    # ------------------------------------------------------------------
    # Leitura
    # ------------------------------------------------------------------

    def get_fornecedores(self):
        try:
            return self.list_fornecedores_uc.execute()
        except Exception:
            logger.exception("Erro ao listar fornecedores")
            return []

    # ------------------------------------------------------------------
    # Criação
    # ------------------------------------------------------------------

    def novo_fornecedor(self, dados: dict):
        try:
            fornecedor = self.fornecedor_repo.save_from_dict(dados)
            audit(
                self.audit_log,
                utilizador=self.user.username,
                accao="novo_fornecedor",
                detalhe=f"nome={dados.get('nome', '')}",
            )
            if self.gui:
                self.gui.informuser("OK", "Fornecedor criado com sucesso.")
            return fornecedor
        except Exception:
            logger.exception("Erro ao criar fornecedor")
            raise

    # ------------------------------------------------------------------
    # Edição
    # ------------------------------------------------------------------

    def editar_fornecedor(self, dados: dict):
        """
        Actualiza o fornecedor. Não mostra diálogo de confirmação — as
        views chamadoras (FornecedorDetalheGUI, FornecedorClassificarGUI)
        já gerem o seu próprio feedback ao utilizador.
        """
        try:
            self.fornecedor_repo.update(dados)
            audit(
                self.audit_log,
                utilizador=self.user.username,
                accao="editar_fornecedor",
                detalhe=f"id={dados['id']} nome={dados.get('nome', '')}",
            )
        except Exception:
            logger.exception("Erro ao editar fornecedor")
            raise

    # ------------------------------------------------------------------
    # Importação
    # ------------------------------------------------------------------

    def importar_fornecedores(self, file_path: str):
        if not self.import_fornecedores_uc:
            if self.gui:
                self.gui.informuser("Erro", "Importação não configurada.", tipo="error")
            return
        try:
            total = self.import_fornecedores_uc.execute(file_path)
            if self.gui:
                self.gui.informuser(
                    "Importação concluída",
                    f"{total} fornecedor(es) importado(s).",
                )
        except Exception as e:
            logger.exception("Erro na importação de fornecedores")
            if self.gui:
                self.gui.informuser("Erro", str(e), tipo="error")

    # ------------------------------------------------------------------
    # E-Fatura AT — histórico mensal
    # ------------------------------------------------------------------

    def importar_efatura(self, file_path: str):
        if not self.importar_efatura_uc:
            if self.gui:
                self.gui.informuser("Erro", "Use case de E-Fatura não configurado.", tipo="error")
            return
        try:
            r = self.importar_efatura_uc.execute(file_path)
            if self.gui:
                msg = (
                    f"Documentos lidos      : {r['lidos']}\n"
                    f"Inseridos             : {r['inseridos']}\n"
                    f"Actualizados          : {r['actualizados']}\n"
                    f"Ignorados (sem nº)    : {r['ignorados']}\n"
                    f"Sem fornecedor na BD  : {r['sem_fornecedor']}"
                )
                self.gui.informuser("E-Fatura importada", msg)
        except Exception as e:
            logger.exception("Erro ao importar E-Fatura")
            if self.gui:
                self.gui.informuser("Erro", str(e), tipo="error")

    def get_historico_faturacao(self, fornecedor_id: int) -> list:
        """Agregados mensais de um fornecedor (via view faturacao_mensal)."""
        try:
            db = self.fornecedor_repo.db_path
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(
                    "SELECT ano, mes, n_documentos, base_tributavel, iva, total "
                    "FROM faturacao_mensal "
                    "WHERE fornecedor_id = ? "
                    "ORDER BY ano DESC, mes DESC",
                    (fornecedor_id,),
                ).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.exception("Erro ao obter histórico de faturação")
            return []

    def get_documentos_faturacao(
        self,
        fornecedor_id: int | None = None,
        ano: int | None = None,
        mes: int | None = None,
        tipo: str | None = None,
    ) -> list:
        """Documentos individuais da tabela faturacao_documentos, com filtros opcionais."""
        try:
            db = self.fornecedor_repo.db_path
            conds, params = ["1=1"], []
            if fornecedor_id is not None:
                conds.append("fd.fornecedor_id = ?");  params.append(fornecedor_id)
            if ano is not None:
                conds.append("fd.ano = ?");            params.append(ano)
            if mes is not None:
                conds.append("fd.mes = ?");            params.append(mes)
            if tipo:
                conds.append("fd.tipo = ?");           params.append(tipo)
            sql = (
                "SELECT fd.id, fd.data_emissao, fd.numero_documento, "
                "       fd.tipo, fd.situacao, "
                "       fd.base_tributavel, fd.iva, fd.total, "
                "       fd.nif_emitente, fd.nome_emitente, "
                "       COALESCE(f.nome, fd.nome_emitente) AS fornecedor_nome "
                "FROM   faturacao_documentos fd "
                "LEFT JOIN fornecedores f ON fd.fornecedor_id = f.id "
                f"WHERE  {' AND '.join(conds)} "
                "ORDER  BY fd.data_emissao DESC, fd.id DESC"
            )
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.exception("Erro ao obter documentos de faturação")
            return []

    def get_valores_filtro(self) -> dict:
        """Valores distintos para tipo_fornecedor, tipo_relacao e setor."""
        try:
            db = self.fornecedor_repo.db_path
            with sqlite3.connect(db) as conn:
                def _distinct(col):
                    rows = conn.execute(
                        f"SELECT DISTINCT {col} FROM fornecedores "
                        f"WHERE {col} IS NOT NULL AND {col} != '' ORDER BY {col}"
                    ).fetchall()
                    return [r[0] for r in rows]
                return {
                    "tipo_fornecedor": _distinct("tipo_fornecedor"),
                    "tipo_relacao":    _distinct("tipo_relacao"),
                    "setor":           _distinct("setor"),
                }
        except Exception:
            logger.exception("Erro ao obter valores de filtro")
            return {"tipo_fornecedor": [], "tipo_relacao": [], "setor": []}

    def get_fornecedores_com_media_anual(
        self,
        tipo_fornecedor: str | None = None,
        tipo_relacao:    str | None = None,
        setor:           str | None = None,
    ) -> list[dict]:
        """
        Lista todos os fornecedores com a média anual de faturação calculada.
        Inclui fornecedores sem histórico (média = 0).
        """
        try:
            db = self.fornecedor_repo.db_path
            conds, params = [], []
            if tipo_fornecedor:
                conds.append("f.tipo_fornecedor = ?"); params.append(tipo_fornecedor)
            if tipo_relacao:
                conds.append("f.tipo_relacao = ?");    params.append(tipo_relacao)
            if setor:
                conds.append("f.setor = ?");           params.append(setor)
            where = ("WHERE " + " AND ".join(conds)) if conds else ""
            sql = f"""
                SELECT
                    f.id,
                    f.nome,
                    f.nif,
                    f.tipo_fornecedor,
                    f.atividade,
                    f.tipo_relacao,
                    f.setor,
                    COUNT(DISTINCT fm.ano)                                   AS n_anos,
                    COALESCE(SUM(fm.total), 0)                              AS total_historico,
                    CASE WHEN COUNT(DISTINCT fm.ano) > 0
                         THEN SUM(fm.total) / COUNT(DISTINCT fm.ano)
                         ELSE 0 END                                         AS media_anual
                FROM fornecedores f
                LEFT JOIN faturacao_mensal fm ON fm.fornecedor_id = f.id
                {where}
                GROUP BY f.id, f.nome, f.nif, f.tipo_fornecedor, f.atividade,
                         f.tipo_relacao, f.setor
                ORDER BY f.nome
            """
            with sqlite3.connect(db) as conn:
                conn.row_factory = sqlite3.Row
                rows = conn.execute(sql, params).fetchall()
            return [dict(r) for r in rows]
        except Exception:
            logger.exception("Erro ao obter fornecedores com média anual")
            return []

    def limpar_sem_data(self) -> int:
        """Apaga todos os documentos de faturação sem data de emissão. Devolve o nº de linhas removidas."""
        try:
            db = self.fornecedor_repo.db_path
            with sqlite3.connect(db) as conn:
                cur = conn.execute(
                    "DELETE FROM faturacao_documentos WHERE data_emissao IS NULL"
                )
                removidos = cur.rowcount
            logger.info("limpar_sem_data: %d documentos removidos", removidos)
            return removidos
        except Exception:
            logger.exception("Erro ao apagar documentos sem data")
            raise

    def get_anos_faturacao(self) -> list[int]:
        try:
            db = self.fornecedor_repo.db_path
            with sqlite3.connect(db) as conn:
                rows = conn.execute(
                    "SELECT DISTINCT ano FROM faturacao_documentos "
                    "WHERE ano IS NOT NULL ORDER BY ano DESC"
                ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []

    def get_tipos_faturacao(self) -> list[str]:
        try:
            db = self.fornecedor_repo.db_path
            with sqlite3.connect(db) as conn:
                rows = conn.execute(
                    "SELECT DISTINCT tipo FROM faturacao_documentos "
                    "WHERE tipo IS NOT NULL ORDER BY tipo"
                ).fetchall()
            return [r[0] for r in rows]
        except Exception:
            return []
