# atrpt/reset_user.py
#
# Apaga o registo do utilizador actual da atrpt_db para testar o fluxo
# de novo utilizador em qualquer aplicação.
#
# Uso:  python reset_user.py
#       python reset_user.py --username outro_user   (forçar username)
#       python reset_user.py --dry-run               (mostrar sem apagar)

import argparse
import getpass
import sqlite3
from pathlib import Path
from core.config import load_config


def main():
    parser = argparse.ArgumentParser(description="Reset de utilizador para testes")
    parser.add_argument("--username", default=None, help="Username a apagar (default: utilizador actual do sistema)")
    parser.add_argument("--dry-run",  action="store_true", help="Mostrar o que seria apagado sem apagar")
    args = parser.parse_args()

    username = (args.username or getpass.getuser()).lower()

    cfg     = load_config(Path("app.ini"))
    db_path = cfg.paths_app["atrpt_db"]

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT username, nome, email, ativo FROM users WHERE username = ?",
            (username,)
        ).fetchone()

    if not row:
        print(f"Utilizador '{username}' não encontrado na BD — nada a fazer.")
        return

    print(f"\nUtilizador encontrado:")
    print(f"  username : {row[0]}")
    print(f"  nome     : {row[1]}")
    print(f"  email    : {row[2]}")
    print(f"  ativo    : {row[3]}")

    if args.dry_run:
        print("\n[dry-run] Nenhuma alteração efectuada.")
        return

    confirmar = input(f"\nApagar '{username}'? (s/N): ").strip().lower()
    if confirmar != "s":
        print("Cancelado.")
        return

    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM users WHERE username = ?", (username,))

    print(f"Utilizador '{username}' removido. Na próxima execução será tratado como novo utilizador.")


if __name__ == "__main__":
    main()
