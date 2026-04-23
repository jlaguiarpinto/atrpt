# atrpt/infrastructure/persistence/pedido_repository.py

import sqlite3
from pathlib import Path
from typing import Optional, List
from datetime import datetime

from domain.aprovisionamento.repository import PedidoRepository
from domain.aprovisionamento.entities import Proposta, Pedido
from domain.aprovisionamento.enums import PedidoEstado


class PedidoRepositorySQL(PedidoRepository):

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        conn.execute("PRAGMA foreign_keys = ON;")
        return conn

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS pedidos (
                    numero           TEXT PRIMARY KEY,
                    centro_custo     TEXT NOT NULL,
                    descricao        TEXT NOT NULL,
                    criado_por       TEXT NOT NULL,
                    data_criacao     TEXT NOT NULL,
                    estado           TEXT NOT NULL,
                    autorizacao_1_por TEXT,
                    autorizacao_1_em  TEXT,
                    autorizacao_2_por TEXT,
                    autorizacao_2_em  TEXT
                );
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS propostas (
                    id              INTEGER PRIMARY KEY AUTOINCREMENT,
                    pedido_numero   TEXT NOT NULL,
                    fornecedor_id   TEXT NOT NULL,
                    valor           REAL NOT NULL,
                    pdf_path        TEXT,
                    FOREIGN KEY (pedido_numero) REFERENCES pedidos(numero)
                );
            """)

    # --------------------------------------------------
    # Persistência
    # --------------------------------------------------

    def save(self, pedido: Pedido) -> None:
        with self._connect() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO pedidos (
                    numero, centro_custo, descricao, criado_por,
                    data_criacao, estado,
                    autorizacao_1_por, autorizacao_1_em,
                    autorizacao_2_por, autorizacao_2_em
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                pedido.numero,
                pedido.centro_custo,
                pedido.descricao,
                pedido.criado_por,
                pedido.data_criacao.isoformat(),
                pedido.estado.value,
                pedido.autorizacao_1_por,
                pedido.autorizacao_1_em.isoformat() if pedido.autorizacao_1_em else None,
                pedido.autorizacao_2_por,
                pedido.autorizacao_2_em.isoformat() if pedido.autorizacao_2_em else None,
            ))
            conn.execute(
                "DELETE FROM propostas WHERE pedido_numero = ?", (pedido.numero,)
            )
            for p in pedido.propostas:
                conn.execute("""
                    INSERT INTO propostas (pedido_numero, fornecedor_id, valor, pdf_path)
                    VALUES (?, ?, ?, ?)
                """, (pedido.numero, p.fornecedor_id, p.valor, p.pdf_path))

    # --------------------------------------------------
    # Anexos
    # --------------------------------------------------

    def adicionar_anexo(self, pedido_numero: str, path: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO pedido_anexos (pedido_numero, path) VALUES (?, ?)",
                (pedido_numero, path)
            )

    def remover_anexo(self, anexo_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM pedido_anexos WHERE id = ?", (anexo_id,))

    def listar_anexos(self, pedido_numero: str) -> list:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, path FROM pedido_anexos WHERE pedido_numero = ? ORDER BY id",
                (pedido_numero,)
            ).fetchall()
        return [{"id": r[0], "path": r[1]} for r in rows]

    # --------------------------------------------------
    # Leitura individual
    # --------------------------------------------------

    def get_by_numero(self, numero: str) -> Optional[Pedido]:
        with self._connect() as conn:
            cur = conn.execute("""
                SELECT numero, centro_custo, descricao, criado_por,
                       data_criacao, estado,
                       autorizacao_1_por, autorizacao_1_em,
                       autorizacao_2_por, autorizacao_2_em
                FROM pedidos WHERE numero = ?
            """, (numero,))
            row = cur.fetchone()
            if not row:
                return None
            propostas_rows = conn.execute(
                "SELECT fornecedor_id, valor, pdf_path FROM propostas WHERE pedido_numero = ?",
                (numero,)
            ).fetchall()
            anexos_rows = conn.execute(
                "SELECT path FROM pedido_anexos WHERE pedido_numero = ? ORDER BY id",
                (numero,)
            ).fetchall()

        return self._row_to_pedido(row, propostas_rows, [r[0] for r in anexos_rows])

    # --------------------------------------------------
    # Listagem por estado(s)
    # --------------------------------------------------

    def list_by_estado(self, *estados) -> List[Pedido]:
        """
        Sem argumentos  → devolve todos os pedidos.
        Com um ou mais  → filtra pelos estados indicados.

        Aceita enums ou strings:
            list_by_estado()
            list_by_estado("criado")
            list_by_estado("criado", "pendente")
        """
        with self._connect() as conn:
            if not estados:
                rows = conn.execute("""
                    SELECT p.numero, p.centro_custo, p.descricao, p.criado_por,
                           p.data_criacao, p.estado,
                           p.autorizacao_1_por, p.autorizacao_1_em,
                           p.autorizacao_2_por, p.autorizacao_2_em
                    FROM pedidos p
                    ORDER BY p.data_criacao DESC
                """).fetchall()
            else:
                valores = [
                    e.value if isinstance(e, PedidoEstado) else str(e).lower()
                    for e in estados
                ]
                placeholders = ",".join("?" * len(valores))
                rows = conn.execute(f"""
                    SELECT p.numero, p.centro_custo, p.descricao, p.criado_por,
                           p.data_criacao, p.estado,
                           p.autorizacao_1_por, p.autorizacao_1_em,
                           p.autorizacao_2_por, p.autorizacao_2_em
                    FROM pedidos p
                    WHERE p.estado IN ({placeholders})
                    ORDER BY p.data_criacao DESC
                """, valores).fetchall()

            # carregar propostas em batch (uma query em vez de N)
            numeros = [r[0] for r in rows]
            if not numeros:
                return []

            placeholders_n = ",".join("?" * len(numeros))
            prop_rows = conn.execute(f"""
                SELECT pedido_numero, fornecedor_id, valor, pdf_path
                FROM propostas
                WHERE pedido_numero IN ({placeholders_n})
            """, numeros).fetchall()

        # agrupar propostas por número de pedido
        props_por_pedido: dict[str, list] = {}
        for pr in prop_rows:
            props_por_pedido.setdefault(pr[0], []).append(pr[1:])

        return [
            self._row_to_pedido(row, props_por_pedido.get(row[0], []))
            for row in rows
        ]

    # --------------------------------------------------
    # Numeração automática
    # --------------------------------------------------

    def next_numero(self) -> str:
        ano = datetime.now().year
        with self._connect() as conn:
            cur = conn.execute(
                "SELECT COUNT(*) FROM pedidos WHERE numero LIKE ?",
                (f"{ano}/%",)
            )
            seq = cur.fetchone()[0] + 1
        return f"{ano}/{seq:02d}"

    # --------------------------------------------------
    # Construção de entidade — único ponto de montagem
    # --------------------------------------------------

    def _row_to_pedido(self, row: tuple, propostas_rows: list, anexos: list = None) -> Pedido:
        """
        row            : tuplo com as 10 colunas da tabela pedidos
        propostas_rows : lista de (fornecedor_id, valor, pdf_path)
        """
        (
            numero, centro_custo, descricao, criado_por,
            data_criacao, estado,
            aut1_por, aut1_em,
            aut2_por, aut2_em,
        ) = row

        propostas = [
            Proposta(fornecedor_id=r[0], valor=r[1], pdf_path=r[2])
            for r in propostas_rows
        ]

        return Pedido(
            numero=numero,
            centro_custo=centro_custo,
            descricao=descricao,
            criado_por=criado_por,
            data_criacao=datetime.fromisoformat(data_criacao),
            propostas=propostas,
            estado=PedidoEstado(estado),
            autorizacao_1_por=aut1_por,
            autorizacao_1_em=datetime.fromisoformat(aut1_em) if aut1_em else None,
            autorizacao_2_por=aut2_por,
            autorizacao_2_em=datetime.fromisoformat(aut2_em) if aut2_em else None,
            anexos=anexos or [],
        )
