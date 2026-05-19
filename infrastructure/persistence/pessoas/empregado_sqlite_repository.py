# atrpt/infrastructure/persistence/pessoas/empregado_sqlite_repository.py

import sqlite3
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

from domain.pessoas.empregado import Empregado, SituacaoTrabalhador


def _to_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    if isinstance(val, str):
        try:
            return date.fromisoformat(val)
        except ValueError:
            return None
    return None


def _str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


def _calcular_antiguidade(admissao: Optional[date], cessacao: Optional[date] = None) -> Optional[int]:
    if admissao is None:
        return None
    referencia = cessacao if cessacao else date.today()
    anos = referencia.year - admissao.year
    if (referencia.month, referencia.day) < (admissao.month, admissao.day):
        anos -= 1
    return max(0, anos)


class EmpregadoSQLiteRepository:
    """
    Repositório de empregados sobre SQLite (atrpt.db).
    Tabelas: rh_dados_pessoais, rh_contratos, rh_categorias,
             rh_diuturnidades, rh_vencimentos.
    Interface idêntica à do EmpregadoRepository (Access).
    """

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._ensure_schema()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _ensure_schema(self):
        with self._connect() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS rh_dados_pessoais (
                    numero          INTEGER PRIMARY KEY,
                    nome            TEXT    NOT NULL,
                    ativo           TEXT    NOT NULL DEFAULT 'I'
                                    CHECK (ativo IN ('A','I','B','L','S','P','C')),
                    local           TEXT,
                    sector          TEXT,
                    nif             TEXT,
                    niss            TEXT,
                    numero_utente   TEXT,
                    cc              TEXT,
                    data_validade_cc TEXT,
                    data_nascimento  TEXT,
                    estado_civil    TEXT,
                    genero          TEXT,
                    naturalidade    TEXT,
                    nacionalidade   TEXT,
                    morada          TEXT,
                    cp              TEXT,
                    localidade      TEXT,
                    telefone        TEXT,
                    telemovel       TEXT,
                    email           TEXT,
                    nib             TEXT,
                    notas           TEXT,
                    doc_ident_tipo  TEXT,
                    banco           TEXT
                );

                CREATE TABLE IF NOT EXISTS rh_contratos (
                    id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero             INTEGER NOT NULL,
                    ativo              TEXT    NOT NULL DEFAULT 'I',
                    tipo_contrato      TEXT,
                    data_admissao      TEXT,
                    data_cessacao      TEXT,
                    categoria_admissao TEXT,
                    FOREIGN KEY (numero) REFERENCES rh_dados_pessoais(numero)
                );

                CREATE TABLE IF NOT EXISTS rh_categorias (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero          INTEGER NOT NULL,
                    ativo           TEXT    NOT NULL DEFAULT 'I',
                    categoria_atual TEXT,
                    FOREIGN KEY (numero) REFERENCES rh_dados_pessoais(numero)
                );

                CREATE TABLE IF NOT EXISTS rh_diuturnidades (
                    id            INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero        INTEGER NOT NULL,
                    ativo         TEXT    NOT NULL DEFAULT 'I',
                    diuturnidades INTEGER,
                    valor_total   REAL,
                    FOREIGN KEY (numero) REFERENCES rh_dados_pessoais(numero)
                );

                CREATE TABLE IF NOT EXISTS rh_vencimentos (
                    id         INTEGER PRIMARY KEY AUTOINCREMENT,
                    numero     INTEGER NOT NULL,
                    vencimento REAL,
                    ano        INTEGER,
                    desde_mes  INTEGER,
                    FOREIGN KEY (numero) REFERENCES rh_dados_pessoais(numero)
                );
            """)
            conn.execute("""
                CREATE UNIQUE INDEX IF NOT EXISTS idx_rh_vencimentos_uniq
                ON rh_vencimentos(numero, ano, desde_mes)
            """)
            # renomear activo → ativo (tabelas legadas do Access)
            for tabela in ("rh_contratos", "rh_categorias"):
                try:
                    conn.execute(f"ALTER TABLE {tabela} RENAME COLUMN activo TO ativo")
                except Exception:
                    pass
            # remove coluna legada importada do Access
            try:
                conn.execute("ALTER TABLE rh_contratos DROP COLUMN antiguidade")
            except Exception:
                pass
            self._migrate_candidato(conn)
            # adicionar colunas novas em bases de dados existentes
            for col_sql in (
                "ALTER TABLE rh_dados_pessoais ADD COLUMN banco TEXT",
                "ALTER TABLE rh_dados_pessoais ADD COLUMN nome_conhecido TEXT",
                "ALTER TABLE rh_dados_pessoais ADD COLUMN emerg_nome TEXT",
                "ALTER TABLE rh_dados_pessoais ADD COLUMN emerg_relacao TEXT",
                "ALTER TABLE rh_dados_pessoais ADD COLUMN emerg_telemovel TEXT",
            ):
                try:
                    conn.execute(col_sql)
                except Exception:
                    pass

    def _migrate_candidato(self, conn) -> None:
        """Garante CHECK 'C' e colunas doc_ident_tipo/banco em bases de dados existentes."""
        cur = conn.execute("PRAGMA table_info(rh_dados_pessoais)")
        cols = {row[1] for row in cur.fetchall()}

        cur = conn.execute(
            "SELECT sql FROM sqlite_master WHERE name='rh_dados_pessoais' AND type='table'"
        )
        row = cur.fetchone()
        schema_sql = row[0] if row else ""

        needs_check_fix = "'C'" not in schema_sql and '"C"' not in schema_sql
        has_doc_col     = "doc_ident_tipo" in cols

        if needs_check_fix:
            null_or_col = "doc_ident_tipo" if has_doc_col else "NULL"
            conn.execute("PRAGMA foreign_keys=OFF")
            conn.executescript(f"""
                DROP TABLE IF EXISTS rh_dados_pessoais_v2;
                CREATE TABLE rh_dados_pessoais_v2 (
                    numero          INTEGER PRIMARY KEY,
                    nome            TEXT    NOT NULL,
                    ativo           TEXT    NOT NULL DEFAULT 'I'
                                    CHECK (ativo IN ('A','I','B','L','S','P','C')),
                    local           TEXT, sector TEXT,
                    nif             TEXT, niss TEXT, numero_utente TEXT,
                    cc              TEXT, data_validade_cc TEXT,
                    data_nascimento TEXT, estado_civil TEXT, genero TEXT,
                    naturalidade    TEXT, nacionalidade TEXT,
                    morada          TEXT, cp TEXT, localidade TEXT,
                    telefone        TEXT, telemovel TEXT, email TEXT,
                    nib             TEXT, notas TEXT, doc_ident_tipo TEXT,
                    banco           TEXT
                );
                INSERT INTO rh_dados_pessoais_v2
                    SELECT numero, nome, ativo, local, sector, nif, niss,
                           numero_utente, cc, data_validade_cc, data_nascimento,
                           estado_civil, genero, naturalidade, nacionalidade,
                           morada, cp, localidade, telefone, telemovel, email,
                           nib, notas, {null_or_col}, NULL
                    FROM rh_dados_pessoais;
                DROP TABLE rh_dados_pessoais;
                ALTER TABLE rh_dados_pessoais_v2 RENAME TO rh_dados_pessoais;
            """)
            conn.execute("PRAGMA foreign_keys=ON")
        elif not has_doc_col:
            conn.execute(
                "ALTER TABLE rh_dados_pessoais ADD COLUMN doc_ident_tipo TEXT"
            )

    # ------------------------------------------------------------------
    # Queries públicas
    # ------------------------------------------------------------------

    def get_categorias(self) -> list:
        """Devolve lista ordenada de categorias únicas registadas."""
        with self._connect() as conn:
            cur = conn.execute("""
                SELECT DISTINCT categoria_atual FROM rh_categorias
                    WHERE categoria_atual IS NOT NULL AND categoria_atual != ''
                UNION
                SELECT DISTINCT categoria_admissao FROM rh_contratos
                    WHERE categoria_admissao IS NOT NULL AND categoria_admissao != ''
                ORDER BY 1
            """)
            return [r[0] for r in cur.fetchall()]

    def list_all(self, apenas_ativos: bool = False,
                 situacao: str = None) -> List[Empregado]:
        with self._connect() as conn:
            return self._query_todos(conn, apenas_ativos=apenas_ativos,
                                     situacao=situacao)

    def list_ativos(self) -> List[Empregado]:
        return self.list_all(situacao='A')

    def get_by_numero(self, numero: int) -> Optional[Empregado]:
        with self._connect() as conn:
            rows = self._query_todos(conn, apenas_ativos=False, numero=numero)
        return rows[0] if rows else None

    def pesquisar(self, texto: str, apenas_ativos: bool = True,
                  situacao: str = None) -> List[Empregado]:
        todos = self.list_all(apenas_ativos=apenas_ativos, situacao=situacao)
        txt = texto.lower().strip()
        return [
            e for e in todos
            if txt in e.nome.lower()
            or txt in (e.sector or "").lower()
            or txt in (e.local or "").lower()
            or txt in (e.categoria_atual or "").lower()
            or str(e.numero) == txt
        ]

    # ------------------------------------------------------------------
    # Escrita
    # ------------------------------------------------------------------

    def insert(self, dados: dict) -> int:
        """Insere novo registo em rh_dados_pessoais e tabelas relacionadas; devolve o numero."""
        with self._connect() as conn:
            cur = conn.execute(
                """INSERT INTO rh_dados_pessoais
                   (nome, ativo, nif, niss, cc, data_validade_cc, doc_ident_tipo,
                    data_nascimento, estado_civil, genero, nacionalidade,
                    morada, cp, localidade, telemovel, email,
                    nome_conhecido, emerg_nome, emerg_relacao, emerg_telemovel,
                    nib, banco, notas, local, sector)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    dados.get("nome"),
                    dados.get("ativo", "C"),
                    dados.get("nif"),
                    dados.get("niss"),
                    dados.get("cc"),
                    dados.get("data_validade_cc"),
                    dados.get("doc_ident_tipo"),
                    dados.get("data_nascimento"),
                    dados.get("estado_civil"),
                    dados.get("genero"),
                    dados.get("nacionalidade"),
                    dados.get("morada"),
                    dados.get("cp"),
                    dados.get("localidade"),
                    dados.get("telemovel"),
                    dados.get("email"),
                    dados.get("nome_conhecido"),
                    dados.get("emerg_nome"),
                    dados.get("emerg_relacao"),
                    dados.get("emerg_telemovel"),
                    dados.get("nib"),
                    dados.get("banco"),
                    dados.get("notas"),
                    dados.get("local"),
                    dados.get("sector"),
                ),
            )
            numero = cur.lastrowid
            self._upsert_contrato(conn, numero, dados)
            self._upsert_categoria(conn, numero, dados)
            self._upsert_diuturnidades(conn, numero, dados)
            self._upsert_vencimento(conn, numero, dados)
            return numero

    def update(self, dados: dict) -> None:
        """Grava todos os campos editáveis de um trabalhador."""
        numero = dados.get("numero")
        if not numero:
            raise ValueError("numero é obrigatório para update")
        if "ativo" in dados and dados["ativo"] not in SituacaoTrabalhador.TODOS:
            raise ValueError(f"situação inválida: {dados['ativo']!r}")
        with self._connect() as conn:
            self._update_pessoais(conn, numero, dados)
            self._upsert_contrato(conn, numero, dados)
            self._upsert_categoria(conn, numero, dados)
            self._upsert_diuturnidades(conn, numero, dados)
            self._upsert_vencimento(conn, numero, dados)

    def _update_pessoais(self, conn, numero: int, dados: dict) -> None:
        _campos = [
            "nome", "data_nascimento", "estado_civil", "genero", "nacionalidade",
            "doc_ident_tipo", "cc", "data_validade_cc", "nif", "niss",
            "morada", "cp", "localidade", "telemovel", "email",
            "nome_conhecido", "emerg_nome", "emerg_relacao", "emerg_telemovel",
            "nib", "banco", "notas", "local", "sector", "ativo",
        ]
        sets   = [f"{c} = ?" for c in _campos if c in dados]
        params = [dados[c]   for c in _campos if c in dados]
        if sets:
            conn.execute(
                "UPDATE rh_dados_pessoais SET " + ", ".join(sets) + " WHERE numero = ?",
                params + [numero],
            )

    def _upsert_contrato(self, conn, numero: int, dados: dict) -> None:
        _map = {
            "tipo_contrato":      "tipo_contrato",
            "data_admissao":      "data_admissao",
            "data_cessacao":      "data_cessacao",
            "categoria_admissao": "categoria_admissao",
        }
        in_dados = {col: dados[k] for k, col in _map.items() if k in dados}
        if not in_dados:
            return
        cur = conn.execute(
            "SELECT id FROM rh_contratos WHERE numero=? AND ativo='A'", (numero,))
        row = cur.fetchone()
        if row:
            sets = [f"{c} = ?" for c in in_dados]
            conn.execute(
                "UPDATE rh_contratos SET " + ", ".join(sets) + " WHERE id=?",
                list(in_dados.values()) + [row[0]],
            )
        elif any(v is not None for v in in_dados.values()):
            conn.execute(
                """INSERT INTO rh_contratos
                   (numero, ativo, tipo_contrato, data_admissao, data_cessacao, categoria_admissao)
                   VALUES (?, 'A', ?, ?, ?, ?)""",
                (numero, dados.get("tipo_contrato"), dados.get("data_admissao"),
                 dados.get("data_cessacao"), dados.get("categoria_admissao")),
            )

    def _upsert_categoria(self, conn, numero: int, dados: dict) -> None:
        if "categoria_atual" not in dados:
            return
        val = dados["categoria_atual"]
        cur = conn.execute(
            "SELECT id FROM rh_categorias WHERE numero=? AND ativo='A'", (numero,))
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE rh_categorias SET categoria_atual=? WHERE id=?", (val, row[0]))
        elif val is not None:
            conn.execute(
                "INSERT INTO rh_categorias (numero, ativo, categoria_atual) VALUES (?, 'A', ?)",
                (numero, val),
            )

    def _upsert_diuturnidades(self, conn, numero: int, dados: dict) -> None:
        _map = {"diuturnidades": "diuturnidades", "valor_diuturnidades": "valor_total"}
        in_dados = {col: dados[k] for k, col in _map.items() if k in dados}
        if not in_dados:
            return
        cur = conn.execute(
            "SELECT id FROM rh_diuturnidades WHERE numero=? AND ativo='A'", (numero,))
        row = cur.fetchone()
        if row:
            sets = [f"{c} = ?" for c in in_dados]
            conn.execute(
                "UPDATE rh_diuturnidades SET " + ", ".join(sets) + " WHERE id=?",
                list(in_dados.values()) + [row[0]],
            )
        elif any(v is not None for v in in_dados.values()):
            conn.execute(
                "INSERT INTO rh_diuturnidades (numero, ativo, diuturnidades, valor_total) VALUES (?, 'A', ?, ?)",
                (numero, dados.get("diuturnidades"), dados.get("valor_diuturnidades")),
            )

    def _upsert_vencimento(self, conn, numero: int, dados: dict) -> None:
        if "vencimento" not in dados or dados["vencimento"] is None:
            return
        from datetime import date as _date
        hoje = _date.today()
        cur = conn.execute(
            "SELECT id FROM rh_vencimentos WHERE numero=? AND ano=? ORDER BY desde_mes DESC LIMIT 1",
            (numero, hoje.year),
        )
        row = cur.fetchone()
        if row:
            conn.execute(
                "UPDATE rh_vencimentos SET vencimento=? WHERE id=?",
                (dados["vencimento"], row[0]),
            )
        else:
            conn.execute(
                "INSERT INTO rh_vencimentos (numero, vencimento, ano, desde_mes) VALUES (?, ?, ?, ?)",
                (numero, dados["vencimento"], hoje.year, hoje.month),
            )

    # ------------------------------------------------------------------
    # Internos
    # ------------------------------------------------------------------

    def _query_todos(self, conn, apenas_ativos: bool = False,
                     numero: int = None, situacao: str = None) -> List[Empregado]:

        sql = """
            SELECT
                dp.numero, dp.nome, dp.ativo, dp.local, dp.sector,
                dp.nif, dp.niss, dp.numero_utente, dp.cc, dp.data_validade_cc,
                dp.data_nascimento, dp.estado_civil, dp.genero,
                dp.naturalidade, dp.nacionalidade,
                dp.morada, dp.cp, dp.localidade, dp.telefone, dp.telemovel,
                dp.email, dp.nib, dp.notas, dp.doc_ident_tipo,
                c.tipo_contrato, c.data_admissao, c.data_cessacao,
                c.categoria_admissao,
                cat.categoria_atual,
                d.diuturnidades, d.valor_total,
                dp.banco,
                dp.nome_conhecido, dp.emerg_nome, dp.emerg_relacao, dp.emerg_telemovel
            FROM rh_dados_pessoais dp
            LEFT JOIN rh_contratos c
                ON dp.numero = c.numero AND c.ativo = 'A'
            LEFT JOIN rh_categorias cat
                ON dp.numero = cat.numero AND cat.ativo = 'A'
            LEFT JOIN rh_diuturnidades d
                ON dp.numero = d.numero AND d.ativo = 'A'
        """

        conditions = []
        params = []
        if situacao == 'EM_SERVICO':
            conditions.append("dp.ativo IN ('A','B','L','S','P')")
        elif situacao:
            conditions.append("dp.ativo = ?")
            params.append(situacao)
        elif apenas_ativos:
            conditions.append("dp.ativo = 'A'")
        if numero is not None:
            conditions.append("dp.numero = ?")
            params.append(numero)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY dp.nome"

        cur = conn.execute(sql, params)
        rows = cur.fetchall()

        # vencimento mais recente por trabalhador
        cur = conn.execute(
            "SELECT numero, vencimento FROM rh_vencimentos"
            " ORDER BY numero, ano DESC, desde_mes DESC"
        )
        vencimentos: dict = {}
        for vr in cur.fetchall():
            num = vr[0]
            if num is not None and num not in vencimentos:
                vencimentos[num] = float(vr[1]) if vr[1] is not None else None

        return [self._row_to_empregado(r, vencimentos) for r in rows]

    def _row_to_empregado(self, r, vencimentos: dict = None) -> Empregado:
        num = r[0]
        vencimento = (vencimentos or {}).get(num) if num is not None else None

        return Empregado(
            numero             = num,
            nome               = _str(r[1]) or "",
            ativo              = _str(r[2]) or "I",
            local              = _str(r[3]),
            sector             = _str(r[4]),
            nif                = _str(r[5]),
            niss               = _str(r[6]),
            numero_utente      = _str(r[7]),
            cc                 = _str(r[8]),
            data_validade_cc   = _to_date(r[9]),
            data_nascimento    = _to_date(r[10]),
            estado_civil       = _str(r[11]),
            genero             = _str(r[12]),
            naturalidade       = _str(r[13]),
            nacionalidade      = _str(r[14]),
            morada             = _str(r[15]),
            cp                 = _str(r[16]),
            localidade         = _str(r[17]),
            telefone           = _str(r[18]),
            telemovel          = _str(r[19]),
            email              = _str(r[20]),
            nib                = _str(r[21]),
            notas              = _str(r[22]),
            doc_ident_tipo     = _str(r[23]),
            tipo_contrato      = _str(r[24]),
            data_admissao      = _to_date(r[25]),
            data_cessacao      = _to_date(r[26]),
            categoria_admissao = _str(r[27]),
            categoria_atual    = _str(r[28]),
            antiguidade        = _calcular_antiguidade(_to_date(r[25]), _to_date(r[26])),
            vencimento         = vencimento,
            diuturnidades      = r[29],
            valor_diuturnidades= float(r[30]) if r[30] is not None else None,
            banco              = _str(r[31]),
            nome_conhecido     = _str(r[32]),
            emerg_nome         = _str(r[33]),
            emerg_relacao      = _str(r[34]),
            emerg_telemovel    = _str(r[35]),
        )
