import sqlite3

db_path = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"

with sqlite3.connect(db_path) as conn:
    cur = conn.execute("SELECT * FROM pedidos ORDER BY numero")
    cols = [d[0] for d in cur.description]
    rows = cur.fetchall()

if not rows:
    print("Sem pedidos.")
else:
    print(f"{'  '.join(cols)}")
    print("-" * 80)
    for row in rows:
        print("  ".join(str(v or "") for v in row))
    print(f"\nTotal: {len(rows)} pedido(s)")
