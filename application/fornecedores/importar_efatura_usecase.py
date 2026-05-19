# application/fornecedores/importar_efatura_usecase.py
#
# Importa o ficheiro E_Fatura.xls exportado do portal AT/DGCI.
# Cada linha = um documento (fatura ou nota de crédito).
# O import é idempotente: documentos já existentes são actualizados.
#
# Tabela principal : faturacao_documentos  (1 linha = 1 documento)
# View de agregação: faturacao_mensal      (GROUP BY fornecedor × ano × mês)

import sqlite3
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

_DDL_DOCUMENTOS = """
    CREATE TABLE IF NOT EXISTS faturacao_documentos (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id    INTEGER,
        nif_emitente     TEXT    NOT NULL,
        nome_emitente    TEXT,
        numero_documento TEXT    NOT NULL,
        tipo             TEXT,
        data_emissao     DATE,
        ano              INTEGER,
        mes              INTEGER,
        base_tributavel  REAL    NOT NULL DEFAULT 0,
        iva              REAL    NOT NULL DEFAULT 0,
        total            REAL    NOT NULL DEFAULT 0,
        situacao         TEXT,
        importado_em     DATETIME DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(nif_emitente, numero_documento),
        FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
    )
"""

_DDL_VIEW = """
    CREATE VIEW IF NOT EXISTS faturacao_mensal AS
    SELECT
        fornecedor_id,
        ano,
        mes,
        COUNT(*)               AS n_documentos,
        SUM(base_tributavel)   AS base_tributavel,
        SUM(iva)               AS iva,
        SUM(total)             AS total
    FROM   faturacao_documentos
    WHERE  fornecedor_id IS NOT NULL
    GROUP  BY fornecedor_id, ano, mes
"""


def _parse_pt_float(value) -> float:
    """'23.370,00 €'  →  23370.0"""
    if value is None:
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace('€', '').replace('\xa0', '').replace(' ', '')
    s = s.replace('.', '').replace(',', '.')
    try:
        return float(s)
    except ValueError:
        return 0.0


class ImportarEFaturaUseCase:

    def __init__(self, db_path: str):
        self.db_path = db_path
        self._setup_bd()

    def _setup_bd(self):
        with sqlite3.connect(self.db_path) as conn:
            # migração: se ainda existir a tabela antiga de agregados, removê-la
            # (a view faturacao_mensal substitui-a com dados reais)
            tbls = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            )}
            views = {r[0] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='view'"
            )}
            if "faturacao_mensal" in tbls:
                conn.execute("DROP TABLE faturacao_mensal")
                logger.info("Migração: tabela faturacao_mensal (agregada) removida.")
            conn.execute(_DDL_DOCUMENTOS)
            if "faturacao_mensal" not in views:
                conn.execute(_DDL_VIEW)

    # ------------------------------------------------------------------

    def execute(self, xls_path: str) -> dict:
        """
        Lê o E_Fatura.xls e faz upsert em faturacao_documentos.
        Devolve {"lidos": n, "inseridos": n, "actualizados": n,
                 "ignorados": n, "sem_fornecedor": n}.
        """
        documentos = self._ler_xls(xls_path)

        # mapa NIF → fornecedor_id
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            nif_map = {
                row["nif"]: row["id"]
                for row in conn.execute(
                    "SELECT id, nif FROM fornecedores WHERE nif IS NOT NULL"
                )
            }

        inseridos = actualizados = ignorados = sem_fornecedor = 0

        with sqlite3.connect(self.db_path) as conn:
            for doc in documentos:
                if not doc["numero_documento"]:
                    ignorados += 1
                    continue

                fid = nif_map.get(doc["nif_emitente"])
                if fid is None:
                    sem_fornecedor += 1

                existe = conn.execute(
                    "SELECT id FROM faturacao_documentos "
                    "WHERE nif_emitente=? AND numero_documento=?",
                    (doc["nif_emitente"], doc["numero_documento"]),
                ).fetchone()

                if existe:
                    conn.execute(
                        "UPDATE faturacao_documentos SET "
                        "fornecedor_id=?, nome_emitente=?, tipo=?, "
                        "data_emissao=?, ano=?, mes=?, "
                        "base_tributavel=?, iva=?, total=?, situacao=? "
                        "WHERE id=?",
                        (
                            fid, doc["nome_emitente"], doc["tipo"],
                            doc["data_emissao"], doc["ano"], doc["mes"],
                            doc["base_tributavel"], doc["iva"], doc["total"],
                            doc["situacao"], existe[0],
                        ),
                    )
                    actualizados += 1
                else:
                    conn.execute(
                        "INSERT INTO faturacao_documentos "
                        "(fornecedor_id, nif_emitente, nome_emitente, "
                        " numero_documento, tipo, data_emissao, ano, mes, "
                        " base_tributavel, iva, total, situacao) "
                        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?)",
                        (
                            fid, doc["nif_emitente"], doc["nome_emitente"],
                            doc["numero_documento"], doc["tipo"],
                            doc["data_emissao"], doc["ano"], doc["mes"],
                            doc["base_tributavel"], doc["iva"], doc["total"],
                            doc["situacao"],
                        ),
                    )
                    inseridos += 1

        return {
            "lidos":          len(documentos),
            "inseridos":      inseridos,
            "actualizados":   actualizados,
            "ignorados":      ignorados,
            "sem_fornecedor": sem_fornecedor,
        }

    # ------------------------------------------------------------------

    def _ler_xls(self, path: str) -> list:
        try:
            import xlrd
        except ImportError:
            raise ImportError(
                "A biblioteca 'xlrd' é necessária para ler ficheiros .xls.\n"
                "Instale com:  pip install xlrd"
            )

        wb   = xlrd.open_workbook(path)
        ws   = wb.sheets()[0]
        hdrs = [str(ws.cell_value(0, c)).strip() for c in range(ws.ncols)]

        def _idx(*nomes):
            for nome in nomes:
                try:
                    return hdrs.index(nome)
                except ValueError:
                    pass
            return None

        c_emitente = _idx("Emitente")
        c_numero   = _idx("Nº Fatura / ATCUD", "Nº Fatura", "ATCUD")
        c_tipo     = _idx("Tipo")
        c_data     = _idx("Data Emissão", "Data de Emissão")
        c_total    = _idx("Total")
        c_iva      = _idx("IVA")
        c_base     = _idx("Base Tributável", "Base Trib.")
        c_situacao = _idx("Situação", "Situacao")

        if c_emitente is None:
            raise ValueError(
                f"Coluna 'Emitente' não encontrada.\nColunas: {hdrs}"
            )

        result = []
        for rx in range(1, ws.nrows):

            def _cell(c):
                if c is None:
                    return None
                ct = ws.cell_type(rx, c)
                cv = ws.cell_value(rx, c)
                if ct == xlrd.XL_CELL_TEXT:
                    return str(cv).strip() or None
                if ct == xlrd.XL_CELL_NUMBER:
                    return cv
                if ct == xlrd.XL_CELL_DATE:
                    return xlrd.xldate_as_datetime(cv, wb.datemode)
                return str(cv).strip() or None

            emitente = _cell(c_emitente)
            if not emitente:
                continue

            partes         = emitente.split("-", 1)
            nif_emitente   = partes[0].strip()
            nome_emitente  = partes[1].strip() if len(partes) > 1 else ""

            if not nif_emitente:
                continue

            # data
            ano = mes = data_iso = None
            d = _cell(c_data)
            if isinstance(d, datetime):
                ano, mes    = d.year, d.month
                data_iso    = d.date().isoformat()
            elif isinstance(d, str):
                for fmt in ("%d/%m/%Y", "%Y-%m-%d"):
                    try:
                        dt       = datetime.strptime(d, fmt)
                        ano, mes = dt.year, dt.month
                        data_iso = dt.date().isoformat()
                        break
                    except ValueError:
                        pass

            result.append({
                "nif_emitente":   nif_emitente,
                "nome_emitente":  nome_emitente,
                "numero_documento": str(_cell(c_numero) or "").strip() or None,
                "tipo":           str(_cell(c_tipo) or "").strip() or None,
                "data_emissao":   data_iso,
                "ano":            ano,
                "mes":            mes,
                "base_tributavel": _parse_pt_float(_cell(c_base)),
                "iva":            _parse_pt_float(_cell(c_iva)),
                "total":          _parse_pt_float(_cell(c_total)),
                "situacao":       str(_cell(c_situacao) or "").strip() or None,
            })

        return result
