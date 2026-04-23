import sqlite3

db_path = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"  # ajusta o caminho
print(db_path)
with sqlite3.connect(db_path) as conn:
    conn.execute("DELETE FROM encomendas")
    conn.commit()
    print("Tabela pedidos limpa.")