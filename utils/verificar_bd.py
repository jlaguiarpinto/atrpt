# verificar_bd.py
import pandas as pd
import sqlite3
conn = sqlite3.connect(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db")
rows = conn.execute("SELECT tipo_relacao, COUNT(*) FROM fornecedores GROUP BY tipo_relacao").fetchall()
for r in rows:
    print(r)
sem_nif = conn.execute("SELECT COUNT(*) FROM fornecedores WHERE nif IS NULL OR nif=''").fetchone()[0]
print(f"Sem NIF: {sem_nif}")

DB_PATH   = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"
XLSX_PATH = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\E_Fatura.xls"

conn = sqlite3.connect(DB_PATH)
bd_nifs = [row[0] for row in conn.execute("SELECT nif FROM fornecedores WHERE nif IS NOT NULL").fetchall()]

df = pd.read_excel(XLSX_PATH, dtype=str)
df["Emitente"] = df["Emitente"].str.strip()
nifs_xlsx = set(df["Emitente"].str.split("-", n=1).str[0].str.strip().tolist())

# comparar 5 exemplos
print("BD NIFs (5 exemplos)   :", bd_nifs[:5])
print("XLSX NIFs (5 exemplos) :", list(nifs_xlsx)[:5])

# quantos da BD estão no xlsx
encontrados = sum(1 for n in bd_nifs if n in nifs_xlsx)
print(f"\nBD com NIF: {len(bd_nifs)} | Encontrados no xlsx: {encontrados} | Ausentes: {len(bd_nifs)-encontrados}")

# ── contagem por tipo_relacao ─────────────────────────────────────────────────
print("═" * 50)
print("  Fornecedores por tipo_relacao:")
rows = conn.execute("""
    SELECT COALESCE(tipo_relacao, '(sem tipo)'), COUNT(*)
    FROM fornecedores
    GROUP BY tipo_relacao
    ORDER BY COUNT(*) DESC
""").fetchall()
for tipo, count in rows:
    print(f"    {tipo:<20} : {count}")

# ── contagem por tipo_fornecedor ──────────────────────────────────────────────
print("─" * 50)
print("  Fornecedores por tipo_fornecedor:")
rows = conn.execute("""
    SELECT COALESCE(tipo_fornecedor, '(sem tipo)'), COUNT(*)
    FROM fornecedores
    GROUP BY tipo_fornecedor
    ORDER BY COUNT(*) DESC
""").fetchall()
for tipo, count in rows:
    print(f"    {tipo:<30} : {count}")

# ── comparação NIFs BD vs xlsx ────────────────────────────────────────────────
print("─" * 50)
bd_nifs = [row[0] for row in conn.execute("SELECT nif FROM fornecedores WHERE nif IS NOT NULL").fetchall()]

df = pd.read_excel(XLSX_PATH, dtype=str)
df["Emitente"] = df["Emitente"].str.strip()
nifs_xlsx = set(df["Emitente"].str.split("-", n=1).str[0].str.strip().tolist())

print("  BD NIFs (5 exemplos)   :", bd_nifs[:5])
print("  XLSX NIFs (5 exemplos) :", list(nifs_xlsx)[:5])

encontrados = sum(1 for n in bd_nifs if n in nifs_xlsx)
print(f"\n  BD com NIF : {len(bd_nifs)}")
print(f"  No xlsx    : {encontrados}")
print(f"  Ausentes   : {len(bd_nifs) - encontrados}")
print("═" * 50)