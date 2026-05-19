# infrastructure/persistence/aprovisionamento/faturacao_fornecedores_repository.py
#
# Acesso à tabela faturacao_documentos para faturas de fornecedores.

import sqlite3
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class FaturacaoFornecedoresRepository:

    def __init__(self, db_path: str | Path):
        self.db_path = str(db_path)

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        # Adiciona coluna data_vencimento se ainda não existir (migração silenciosa)
        try:
            conn.execute("ALTER TABLE faturacao_documentos ADD COLUMN data_vencimento TEXT")
            conn.commit()
        except Exception:
            pass
        return conn

    # ------------------------------------------------------------------

    def existe(self, numero_documento: str, nif_emitente: str) -> bool:
        """True se já existe um registo com o mesmo número e NIF."""
        with self._conn() as conn:
            row = conn.execute(
                "SELECT 1 FROM faturacao_documentos "
                "WHERE numero_documento = ? AND nif_emitente = ?",
                (numero_documento, nif_emitente),
            ).fetchone()
        return row is not None

    def inserir(self, record: dict) -> int:
        """Insere uma nova fatura e devolve o id gerado."""
        with self._conn() as conn:
            cur = conn.execute(
                """
                INSERT INTO faturacao_documentos
                    (fornecedor_id, nif_emitente, nome_emitente, numero_documento,
                     tipo, data_emissao, ano, mes,
                     base_tributavel, iva, total, data_vencimento, situacao)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    record.get("fornecedor_id"),
                    record["nif_emitente"],
                    record.get("nome_emitente"),
                    record["numero_documento"],
                    record.get("tipo"),
                    record.get("data_emissao"),
                    record.get("ano"),
                    record.get("mes"),
                    record.get("base_tributavel", 0),
                    record.get("iva", 0),
                    record.get("total", 0),
                    record.get("data_vencimento"),
                    record.get("situacao", "Registado"),
                ),
            )
        logger.info(
            "faturacao_documentos: inserido id=%d  doc=%s  nif=%s  total=%.2f",
            cur.lastrowid,
            record["numero_documento"],
            record["nif_emitente"],
            record.get("total", 0),
        )
        return cur.lastrowid

    def buscar_emitente_por_serie(self, numero_documento: str) -> tuple[str | None, str | None]:
        """
        Devolve (nif_emitente, nome_emitente) do registo mais recente cuja
        série de documento coincide com os primeiros caracteres de numero_documento.
        Útil como fallback quando o parser não extrai o NIF do PDF actual mas
        o fornecedor já foi registado em faturas anteriores da mesma série.
        """
        prefixo = numero_documento[:10]
        with self._conn() as conn:
            row = conn.execute(
                "SELECT nif_emitente, nome_emitente FROM faturacao_documentos "
                "WHERE numero_documento LIKE ? AND nif_emitente IS NOT NULL "
                "ORDER BY importado_em DESC LIMIT 1",
                (prefixo + "%",),
            ).fetchone()
        return (row[0], row[1]) if row else (None, None)
