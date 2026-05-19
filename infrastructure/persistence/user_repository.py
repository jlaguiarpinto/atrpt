#atrpt /infrastructure/persistence/sqlite_user_repository.py
import sqlite3
from pathlib import Path
from datetime import datetime
from domain.users.users import user


class UserRepository:

    def __init__(self, db_path: Path):
        self.db_path = db_path
        self._init_db()

    def _connect(self):
        return sqlite3.connect(self.db_path, timeout=10)

    def _init_db(self):
        with self._connect() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    username TEXT PRIMARY KEY,
                    nome TEXT NOT NULL,
                    email TEXT NOT NULL,
                    nif TEXT,
                    ativo INTEGER NOT NULL DEFAULT 1,
                    criado_em TEXT NOT NULL,
                    perfil TEXT
                );
            """)
            # migração — adicionar coluna perfil se não existir
            try:
                conn.execute("ALTER TABLE users ADD COLUMN perfil TEXT")
            except Exception:
                pass

            conn.execute("""
                CREATE TABLE IF NOT EXISTS permissions (
                    username TEXT NOT NULL,
                    recurso TEXT NOT NULL
                );
            """)

    # ------------------------------------

    def get_by_username(self, username: str) -> user | None:

        with self._connect() as conn:
            cur = conn.execute(
                "SELECT username, nome, email, nif, ativo, perfil FROM users WHERE username = ?",
                (username,)
            )
            row = cur.fetchone()

            if not row:
                return None

            cur = conn.execute(
                "SELECT recurso FROM permissions WHERE username = ?",
                (username,)
            )
            permissions = [r[0] for r in cur.fetchall()]

        return user(
            username=row[0],
            nome=row[1],
            email=row[2],
            nif=row[3],
            ativo=bool(row[4]),
            permissions=permissions,
            perfil=row[5] if len(row) > 5 else None,
        )

    def create(self, username: str, nome: str, email: str,
               nif: str | None, perfil: str | None = None) -> user:

        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO users (username, nome, email, nif, ativo, criado_em, perfil)
                VALUES (?, ?, ?, ?, 1, ?, ?)
                """,
                (username, nome, email, nif, datetime.now().isoformat(), perfil)
            )

        return self.get_by_username(username)

    def update_perfil(self, username: str, perfil: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE users SET perfil = ? WHERE username = ?",
                (perfil, username)
            )

    def list_all(self) -> list[user]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, nome, email, nif, ativo, perfil FROM users ORDER BY nome"
            ).fetchall()
            result = []
            for r in rows:
                perms = [p[0] for p in conn.execute(
                    "SELECT recurso FROM permissions WHERE username=?", (r[0],)
                ).fetchall()]
                result.append(user(
                    username=r[0], nome=r[1], email=r[2],
                    nif=r[3], ativo=bool(r[4]),
                    permissions=perms,
                    perfil=r[5] if len(r) > 5 else None,
                ))
        return result

    def get_by_perfil(self, perfil: str) -> list[user]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT username, nome, email, nif, ativo, perfil FROM users WHERE perfil = ? AND ativo = 1 ORDER BY nome",
                (perfil,)
            ).fetchall()
            result = []
            for r in rows:
                perms = [p[0] for p in conn.execute(
                    "SELECT recurso FROM permissions WHERE username=?", (r[0],)
                ).fetchall()]
                result.append(user(
                    username=r[0], nome=r[1], email=r[2],
                    nif=r[3], ativo=bool(r[4]),
                    permissions=perms,
                    perfil=r[5] if len(r) > 5 else None,
                ))
        return result