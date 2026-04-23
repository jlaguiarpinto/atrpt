import sqlite3
from pathlib import Path

db_path = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db")  # ajusta aqui

conn = sqlite3.connect(db_path)
cur = conn.cursor()

print("\n--- TABELAS ---")
cur.execute("SELECT name FROM sqlite_master WHERE type='table'")
for row in cur.fetchall():
    print(row[0])

print("\n--- COLUNAS fornecedores ---")
cur.execute("PRAGMA table_info(fornecedores)")
for row in cur.fetchall():
    print(row)

conn.close()