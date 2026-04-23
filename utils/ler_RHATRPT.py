import pyodbc

conn_str = (
    r"DRIVER={Microsoft Access Driver (*.mdb, *.accdb)};"
    r"DBQ=G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\RH_ATRPT.accdb;"
)
conn = pyodbc.connect(conn_str)
cursor = conn.cursor()

# listar tabelas
for row in cursor.tables(tableType="TABLE"):
    print(row.table_name)

# ver colunas de uma tabela
for row in cursor.columns(table="NomeDaTabela"):
    print(f"  {row.column_name:30} {row.type_name:15} nullable={row.nullable}")

# ver primeiras linhas
cursor.execute("SELECT TOP 10 * FROM NomeDaTabela")
for row in cursor.fetchall():
    print(row)

conn.close()