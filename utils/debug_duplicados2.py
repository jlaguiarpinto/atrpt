import pyodbc

DB = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\RH_ATRPT.accdb"
conn = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB};")
cursor = conn.cursor()

# total de linhas por tabela
for tabela, campo in [("Contratos","activo"), ("Categorias","activo"), ("Diuturnidades","ativo")]:
    cursor.execute(f"SELECT COUNT(*) FROM [{tabela}]")
    total = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM [{tabela}] WHERE [{campo}] = 'A'")
    ativos = cursor.fetchone()[0]
    cursor.execute(f"SELECT COUNT(*) FROM [{tabela}] WHERE [{campo}] IS NULL")
    nulos = cursor.fetchone()[0]
    print(f"{tabela}: total={total}  activos={ativos}  nulos={nulos}")

# contar linhas na query principal
print("\n=== Contagem na query JOIN ===")
cursor.execute("""
    SELECT COUNT(*)
    FROM ((
        [Dados Pessoais] dp
        LEFT JOIN (SELECT * FROM [Contratos] WHERE [activo] = 'A') AS c
            ON dp.[Numero do trabalhador] = c.[numero do trabalhador]
        )
        LEFT JOIN (SELECT * FROM [Categorias] WHERE [activo] = 'A') AS cat
            ON dp.[Numero do trabalhador] = cat.[Numero do trabalhador]
    )
""")
print(f"  com Contratos+Categorias: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM [Dados Pessoais]")
print(f"  Dados Pessoais sozinho:   {cursor.fetchone()[0]}")

conn.close()
