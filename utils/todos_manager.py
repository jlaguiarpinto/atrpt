"""Gestor de ToDos: navega com setas, marca com Enter, move para DoNes.txt."""

import os
import sys
import msvcrt
from datetime import date, datetime

BASE_DIR = os.path.join(os.path.dirname(__file__), "..")
TODOS_FILE = os.path.join(BASE_DIR, "ToDos.txt")
DONES_FILE = os.path.join(BASE_DIR, "DoNes.txt")

# ANSI
RESET  = "\033[0m"
BOLD   = "\033[1m"
GREEN  = "\033[32m"
YELLOW = "\033[33m"
CYAN   = "\033[36m"
DIM    = "\033[2m"
CURSOR_UP   = "\033[{}A"
CLEAR_LINE  = "\033[2K"


def enable_ansi() -> None:
    import ctypes
    kernel = ctypes.windll.kernel32
    kernel.SetConsoleMode(kernel.GetStdHandle(-11), 7)


def load_lines(path: str) -> list[str]:
    if not os.path.exists(path):
        return []
    with open(path, encoding="utf-8") as f:
        return [ln.rstrip("\n") for ln in f.readlines() if ln.strip()]


def save_lines(path: str, lines: list[str]) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
        if lines:
            f.write("\n")


def append_done(text: str, done_date: date, comment: str = "") -> None:
    entry = f"[DONE {done_date.strftime('%Y-%m-%d')}] {text}"
    if comment:
        entry += f"  // {comment}"
    with open(DONES_FILE, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def ask_date() -> date:
    today = date.today()
    sys.stdout.write(f"  Data [{today}] (Enter=hoje, YYYY-MM-DD para outra): ")
    sys.stdout.flush()
    raw = input().strip()
    if not raw:
        return today
    try:
        return datetime.strptime(raw, "%Y-%m-%d").date()
    except ValueError:
        print("  Formato inválido — a usar hoje.")
        return today


def render(lines: list[str], cursor: int) -> None:
    print(f"\n{BOLD}=== ToDos ==={RESET}")
    print(f"{DIM}  ↑↓ navegar   Enter = marcar como feito   Q = sair{RESET}\n")
    for i, line in enumerate(lines):
        if i == cursor:
            print(f"  {CYAN}{BOLD}► {line}{RESET}")
        else:
            print(f"    {line}")
    print()


def read_key() -> str:
    ch = msvcrt.getch()
    if ch in (b"\xe0", b"\x00"):
        ch2 = msvcrt.getch()
        return {b"H": "UP", b"P": "DOWN"}.get(ch2, "")
    if ch == b"\r":
        return "ENTER"
    if ch in (b"q", b"Q", b"\x1b"):
        return "QUIT"
    return ""


def run() -> None:
    enable_ansi()
    cursor = 0

    while True:
        todos = load_lines(TODOS_FILE)

        if not todos:
            print(f"\n{GREEN}Nenhuma tarefa pendente.{RESET}\n")
            break

        cursor = min(cursor, len(todos) - 1)
        os.system("cls")
        render(todos, cursor)

        key = read_key()

        if key == "UP":
            cursor = max(0, cursor - 1)
        elif key == "DOWN":
            cursor = min(len(todos) - 1, cursor + 1)
        elif key == "ENTER":
            line = todos[cursor]
            print(f"\n  {YELLOW}A marcar:{RESET} {line}")
            done_date = ask_date()
            sys.stdout.write("  Comentário (opcional, Enter para ignorar): ")
            sys.stdout.flush()
            comment = input().strip()
            append_done(line, done_date, comment)
            todos.pop(cursor)
            save_lines(TODOS_FILE, todos)
            print(f"  {GREEN}Movido para DoNes.{RESET}")
            msvcrt.getch()  # pausa breve — qualquer tecla continua
            cursor = min(cursor, max(0, len(todos) - 1))
        elif key == "QUIT":
            break


if __name__ == "__main__":
    run()
