# migrar_fornecedores.py
import sqlite3

db_path = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"

colunas = [
    "ADD COLUMN iban TEXT",
    "ADD COLUMN contacto1_nome TEXT",
    "ADD COLUMN contacto1_telefone TEXT",
    "ADD COLUMN contacto1_email TEXT",
    "ADD COLUMN contacto2_nome TEXT",
    "ADD COLUMN contacto2_telefone TEXT",
    "ADD COLUMN contacto2_email TEXT",
    "ADD COLUMN tipo_fornecedor TEXT",
    "ADD COLUMN tipo_relacao TEXT",
]

with sqlite3.connect(db_path) as conn:
    for col in colunas:
        try:
            conn.execute(f"ALTER TABLE fornecedores {col}")
            print(f"OK: {col}")
        except Exception as e:
            print(f"IGNORADO (já existe?): {col} — {e}")
    conn.commit()

print("Migração concluída.")
