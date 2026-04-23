import pyodbc

DB = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\RH_ATRPT.accdb"
conn = pyodbc.connect(f"DRIVER={{Microsoft Access Driver (*.mdb, *.accdb)}};DBQ={DB};")
cursor = conn.cursor()

cursor.execute("SELECT COUNT(*) FROM [Dados Pessoais]")
print(f"Total linhas Dados Pessoais: {cursor.fetchone()[0]}")

cursor.execute("SELECT COUNT(*) FROM (SELECT DISTINCT [Numero do trabalhador] FROM [Dados Pessoais])")
print(f"Numeros únicos: {cursor.fetchone()[0]}")

# duplicados em Dados Pessoais
cursor.execute("""
    SELECT [Numero do trabalhador], COUNT(*) AS n
    FROM [Dados Pessoais]
    GROUP BY [Numero do trabalhador]
    HAVING COUNT(*) > 1
""")
rows = cursor.fetchall()
if rows:
    print("Duplicados em Dados Pessoais:")
    for r in rows:
        print(f"  numero {r[0]}: {r[1]} vezes")
else:
    print("Sem duplicados em Dados Pessoais")

conn.close()
