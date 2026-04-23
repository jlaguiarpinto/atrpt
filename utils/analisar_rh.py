import pyodbc

# ajustar path
DB_PATH = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\RH_ATRPT.accdb"

conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    f"DBQ={DB_PATH};"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

tabelas_interesse = [
    "Dados Pessoais", "Contratos", "Categorias",
    "Colocação", "Vencimentos", "Diuturnidades"
]

for tabela in tabelas_interesse:
    print(f"\n{'='*60}")
    print(f"TABELA: {tabela}")
    print(f"{'='*60}")
    try:
        # colunas
        for row in cursor.columns(table=tabela):
            print(f"  {row.column_name:35} {row.type_name:15} nullable={row.nullable}")
        # primeiras 3 linhas
        print(f"\n  -- primeiras 3 linhas --")
        cursor.execute(f"SELECT TOP 3 * FROM [{tabela}]")
        rows = cursor.fetchall()
        cols = [d[0] for d in cursor.description]
        print(f"  {cols}")
        for r in rows:
            print(f"  {list(r)}")
    except Exception as e:
        print(f"  ERRO: {e}")

conn.close()
