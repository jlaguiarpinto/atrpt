import pyodbc

DB = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\RH_ATRPT.accdb"
conn = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB};")
cursor = conn.cursor()

# contratos activos por trabalhador — ver se há mais de 1
print("=== Contratos activos com mais de 1 linha por trabalhador ===")
cursor.execute("""
    SELECT [numero do trabalhador], COUNT(*) AS n
    FROM [Contratos]
    WHERE [activo] = 'A'
    GROUP BY [numero do trabalhador]
    HAVING COUNT(*) > 1
""")
for r in cursor.fetchall():
    print(f"  trabalhador {r[0]}: {r[1]} contratos activos")

# diuturnidades activas por trabalhador
print("\n=== Diuturnidades activas com mais de 1 linha ===")
cursor.execute("""
    SELECT [Numero do trabalhador], COUNT(*) AS n
    FROM [Diuturnidades]
    WHERE [ativo] = 'A'
    GROUP BY [Numero do trabalhador]
    HAVING COUNT(*) > 1
""")
for r in cursor.fetchall():
    print(f"  trabalhador {r[0]}: {r[1]} diuturnidades activas")

# categorias activas por trabalhador
print("\n=== Categorias activas com mais de 1 linha ===")
cursor.execute("""
    SELECT [Numero do trabalhador], COUNT(*) AS n
    FROM [Categorias]
    WHERE [activo] = 'A'
    GROUP BY [Numero do trabalhador]
    HAVING COUNT(*) > 1
""")
for r in cursor.fetchall():
    print(f"  trabalhador {r[0]}: {r[1]} categorias activas")

conn.close()
