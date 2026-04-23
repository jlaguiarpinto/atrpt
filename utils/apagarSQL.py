import sqlite3

conn = sqlite3.connect("data/atrpt.db")
cursor = conn.cursor()

cursor.execute("DROP TABLE IF EXISTS fornecedores")

cursor.execute("""
CREATE TABLE fornecedores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    nome TEXT NOT NULL,
    email TEXT,
    nif TEXT UNIQUE
)
""")

conn.commit()
conn.close()