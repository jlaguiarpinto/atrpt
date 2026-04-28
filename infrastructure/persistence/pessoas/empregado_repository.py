# atrpt/infrastructure/persistence/empregado_repository.py

import pyodbc
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Optional, List

from domain.pessoas.empregado import Empregado


def _to_date(val) -> Optional[date]:
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.date()
    if isinstance(val, date):
        return val
    return None


def _str(val) -> Optional[str]:
    if val is None:
        return None
    s = str(val).strip()
    return s if s else None


class EmpregadoRepository:

    def __init__(self, accdb_path: Path):
        self.accdb_path = accdb_path
        self._conn_str = (
            r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
            f"DBQ={accdb_path};"
        )

    def _connect(self):
        return pyodbc.connect(self._conn_str)

    def list_all(self, apenas_ativos: bool = False) -> List[Empregado]:
        with self._connect() as conn:
            return self._query_todos(conn, apenas_ativos)

    def list_ativos(self) -> List[Empregado]:
        return self.list_all(apenas_ativos=True)

    def get_by_numero(self, numero: int) -> Optional[Empregado]:
        with self._connect() as conn:
            rows = self._query_todos(conn, apenas_ativos=False, numero=numero)
        return rows[0] if rows else None

    def pesquisar(self, texto: str, apenas_ativos: bool = True) -> List[Empregado]:
        todos = self.list_all(apenas_ativos=apenas_ativos)
        txt = texto.lower().strip()
        return [
            e for e in todos
            if txt in e.nome.lower()
            or txt in (e.sector or "").lower()
            or txt in (e.local or "").lower()
            or txt in (e.categoria_atual or "").lower()
            or str(e.numero) == txt
        ]

    def _query_todos(self, conn, apenas_ativos: bool = False,
                     numero: int = None) -> List[Empregado]:

        # Access ODBC não suporta AND nos JOINs nem subqueries correlacionadas
        # Vencimentos em query separada para evitar duplicados por histórico
        sql = """
            SELECT
                dp.[Numero do trabalhador],
                dp.[Nome do trabalhador],
                dp.[ativo],
                dp.[local],
                dp.[sector],
                dp.[NIF],
                dp.[NISS],
                dp.[Numero de Utente],
                dp.[CC],
                dp.[data validade CC],
                dp.[Data de nascimento],
                dp.[Estado civil],
                dp.[Género],
                dp.[Naturalidade],
                dp.[Nacionalidade],
                dp.[Morada],
                dp.[CP],
                dp.[Localidade CP],
                dp.[Telefone],
                dp.[Telemóvel],
                dp.[Endereço eletrónico],
                dp.[NIB],
                dp.[Notas],
                c.[tipo de contrato],
                c.[data de admissão],
                c.[data de cessação],
                c.[categoria de admissão],
                c.[antiguidade],
                cat.[categoria atual],
                d.[Diuturnidades],
                d.[Valor total]
            FROM (((
                [Dados Pessoais] dp
                LEFT JOIN (SELECT * FROM [Contratos] WHERE [activo] = 'A') AS c
                    ON dp.[Numero do trabalhador] = c.[numero do trabalhador]
                )
                LEFT JOIN (SELECT * FROM [Categorias] WHERE [activo] = 'A') AS cat
                    ON dp.[Numero do trabalhador] = cat.[Numero do trabalhador]
                )
                LEFT JOIN (SELECT * FROM [Diuturnidades] WHERE [ativo] = 'A') AS d
                    ON dp.[Numero do trabalhador] = d.[Numero do trabalhador]
            )
        """
        conditions = []
        params = []
        if apenas_ativos:
            conditions.append("dp.[ativo] = 'A'")
        if numero is not None:
            conditions.append("dp.[Numero do trabalhador] = ?")
            params.append(numero)
        if conditions:
            sql += " WHERE " + " AND ".join(conditions)
        sql += " ORDER BY dp.[Nome do trabalhador]"

        cursor = conn.cursor()
        if params:
            cursor.execute(sql, params)
        else:
            cursor.execute(sql)
        rows = cursor.fetchall()

        # vencimentos separados — um por trabalhador (mais recente por ano)
        cursor.execute(
            "SELECT [Numero do trabalhador], [vencimento] FROM [Vencimentos]"
            " ORDER BY [Numero do trabalhador], [ano] DESC, [desde mes] DESC"
        )
        vencimentos = {}
        for vr in cursor.fetchall():
            num = int(vr[0]) if vr[0] is not None else None
            if num is not None and num not in vencimentos:
                v = vr[1]
                vencimentos[num] = float(v) if v is not None else None

        return [self._row_to_empregado(r, vencimentos) for r in rows]

    def _row_to_empregado(self, r, vencimentos: dict = None) -> Empregado:
        num = r[0]
        vencimento = (vencimentos or {}).get(int(num)) if num is not None else None

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
            tipo_contrato      = _str(r[23]),
            data_admissao      = _to_date(r[24]),
            data_cessacao      = _to_date(r[25]),
            categoria_admissao = _str(r[26]),
            antiguidade        = r[27],
            categoria_atual    = _str(r[28]),
            vencimento         = vencimento,
            diuturnidades      = r[29],
            valor_diuturnidades= float(r[30]) if r[30] is not None else None,
        )

    def update(self, dados: dict) -> None:
        """
        Grava os campos editáveis de um empregado na tabela [Dados Pessoais].
        Recebe dict com: numero, telemovel, telefone, email,
                         morada, cp, localidade, nib, notas, ativo
        """
        numero = dados.get("numero")
        if not numero:
            raise ValueError("numero é obrigatório para update")

        # mapeamento campo Python → nome da coluna Access
        mapa = {
            "telemovel":  "Telemóvel",
            "telefone":   "Telefone",
            "email":      "Endereço eletrónico",
            "morada":     "Morada",
            "cp":         "CP",
            "localidade": "Localidade CP",
            "nib":        "NIB",
            "notas":      "Notas",
            "ativo":      "ativo",
        }

        sets   = []
        params = []
        for campo, coluna in mapa.items():
            if campo in dados:
                sets.append(f"[{coluna}] = ?")
                params.append(dados[campo])

        if not sets:
            return  # nada a actualizar

        params.append(numero)
        sql = (
            "UPDATE [Dados Pessoais] SET "
            + ", ".join(sets)
            + " WHERE [Numero do trabalhador] = ?"
        )

        with self._connect() as conn:
            conn.execute(sql, params)
            conn.commit()
