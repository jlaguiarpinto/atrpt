# infrastructure/persistence/ponto/ausencia_ponto_repository.py

import sqlite3
from datetime import date
from pathlib import Path
from typing import List, Optional

from domain.ponto.ausencia_ponto import AusenciaPonto


class AusenciaPontoRepository:

    _DDL = """
    CREATE TABLE IF NOT EXISTS ausencias_ponto (
        id               INTEGER PRIMARY KEY AUTOINCREMENT,
        empregado_numero INTEGER NOT NULL,
        tipo             TEXT    NOT NULL,
        data_inicio      TEXT    NOT NULL,
        data_fim         TEXT    NOT NULL,
        obs              TEXT
    )
    """

    def __init__(self, db_path):
        self.db_path = Path(db_path)
        self._init_table()

    def _connect(self):
        return sqlite3.connect(self.db_path)

    def _init_table(self):
        with self._connect() as conn:
            conn.execute(self._DDL)

    # ── leitura ───────────────────────────────────────────────────────────────

    def listar_todos(self) -> List[AusenciaPonto]:
        sql = "SELECT id, empregado_numero, tipo, data_inicio, data_fim, obs FROM ausencias_ponto ORDER BY data_inicio, empregado_numero"
        with self._connect() as conn:
            rows = conn.execute(sql).fetchall()
        return [self._row(r) for r in rows]

    def listar_por_mes(self, ano: int, mes: int) -> List[AusenciaPonto]:
        """Ausências que interceptam o mês indicado."""
        inicio_mes = date(ano, mes, 1)
        import calendar
        ultimo_dia = calendar.monthrange(ano, mes)[1]
        fim_mes    = date(ano, mes, ultimo_dia)
        sql = """
            SELECT id, empregado_numero, tipo, data_inicio, data_fim, obs
            FROM ausencias_ponto
            WHERE data_inicio <= ? AND data_fim >= ?
            ORDER BY data_inicio, empregado_numero
        """
        with self._connect() as conn:
            rows = conn.execute(sql, (fim_mes.isoformat(), inicio_mes.isoformat())).fetchall()
        return [self._row(r) for r in rows]

    # ── escrita ───────────────────────────────────────────────────────────────

    def guardar(self, aus: AusenciaPonto) -> AusenciaPonto:
        if aus.id:
            sql = """UPDATE ausencias_ponto
                     SET empregado_numero=?, tipo=?, data_inicio=?, data_fim=?, obs=?
                     WHERE id=?"""
            with self._connect() as conn:
                conn.execute(sql, (aus.empregado_numero, aus.tipo,
                                   aus.data_inicio.isoformat(), aus.data_fim.isoformat(),
                                   aus.obs, aus.id))
        else:
            sql = """INSERT INTO ausencias_ponto (empregado_numero, tipo, data_inicio, data_fim, obs)
                     VALUES (?, ?, ?, ?, ?)"""
            with self._connect() as conn:
                cur = conn.execute(sql, (aus.empregado_numero, aus.tipo,
                                         aus.data_inicio.isoformat(), aus.data_fim.isoformat(),
                                         aus.obs))
                aus.id = cur.lastrowid
        return aus

    def remover(self, ausencia_id: int) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM ausencias_ponto WHERE id=?", (ausencia_id,))

    # ── aux ───────────────────────────────────────────────────────────────────

    @staticmethod
    def _row(row) -> AusenciaPonto:
        id_, numero, tipo, di, df, obs = row
        return AusenciaPonto(
            id               = id_,
            empregado_numero = numero,
            tipo             = tipo,
            data_inicio      = date.fromisoformat(di),
            data_fim         = date.fromisoformat(df),
            obs              = obs,
        )
