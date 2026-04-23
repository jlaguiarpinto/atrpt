# importar_efatura.py
import sqlite3
import pandas as pd

XLSX_PATH = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\E_Fatura.xls"
DB_PATH   = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"

# ── ler ficheiro E-Fatura ─────────────────────────────────────────────────────
df = pd.read_excel(XLSX_PATH, dtype=str)
df.columns = df.columns.str.strip()

if "Emitente" not in df.columns:
    print(f"❌ Colunas encontradas: {list(df.columns)}")
    raise SystemExit("Coluna 'Emitente' não encontrada.")

df["Emitente"]   = df["Emitente"].str.strip()
df["Setor"]      = df["Setor"].fillna("").str.strip()
df["Data Emissão"] = pd.to_datetime(df["Data Emissão"], errors="coerce", dayfirst=True)
df["Total"]      = pd.to_numeric(df["Total"].str.replace(",", "."), errors="coerce").fillna(0)
df["ano"]        = df["Data Emissão"].dt.year

def parse_emitente(valor):
    partes = valor.split("-", 1)
    if len(partes) == 2:
        return partes[0].strip(), partes[1].strip()
    return valor.strip(), ""

df[["nif", "nome"]] = df["Emitente"].apply(lambda x: pd.Series(parse_emitente(x)))

# ── preparar BD ───────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)

# garantir colunas e tabela
for col_sql in [
    "ALTER TABLE fornecedores ADD COLUMN setor TEXT",
    "ALTER TABLE fornecedores ADD COLUMN nif TEXT",
]:
    try:
        conn.execute(col_sql)
        conn.commit()
    except Exception:
        pass

conn.execute("""
    CREATE TABLE IF NOT EXISTS faturacao_anual (
        id             INTEGER PRIMARY KEY AUTOINCREMENT,
        fornecedor_id  INTEGER NOT NULL,
        ano            INTEGER NOT NULL,
        total          REAL    NOT NULL DEFAULT 0,
        UNIQUE(fornecedor_id, ano),
        FOREIGN KEY(fornecedor_id) REFERENCES fornecedores(id)
    )
""")
conn.commit()

bd_rows  = conn.execute("SELECT id, nome, nif, tipo_relacao FROM fornecedores").fetchall()
nifs_bd  = {row[2]: row[0] for row in bd_rows if row[2]}   # nif → id
nifs_xlsx = set(df["nif"].unique())

# ── 1. criar fornecedores novos ───────────────────────────────────────────────
novos = 0

df_uniq = df.drop_duplicates(subset=["nif"])
for _, row in df_uniq.iterrows():
    nif   = row["nif"]
    nome  = row["nome"]
    setor = row["Setor"] or None

for _, row in df_uniq.iterrows():
    nif   = row["nif"]
    nome  = row["nome"]
    setor = row["Setor"] or None

    if nif in nifs_bd:
        # actualizar setor mesmo que já exista
        if setor:
            conn.execute(
                "UPDATE fornecedores SET setor=? WHERE id=?",
                (setor, nifs_bd[nif])
            )
        continue

    conn.execute(
        "INSERT INTO fornecedores (nome, nif, setor) VALUES (?, ?, ?)",
        (nome, nif, setor)
    )
    fid = conn.execute("SELECT id FROM fornecedores WHERE nif=?", (nif,)).fetchone()[0]
    nifs_bd[nif] = fid
    novos += 1
    print(f"  ➕ {nif} — {nome}  [{setor or '—'}]")

    conn.execute(
        "INSERT INTO fornecedores (nome, nif, setor) VALUES (?, ?, ?)",
        (nome, nif, setor)
    )
    fid = conn.execute("SELECT id FROM fornecedores WHERE nif=?", (nif,)).fetchone()[0]
    nifs_bd[nif] = fid
    novos += 1
    print(f"  ➕ {nif} — {nome}  [{setor or '—'}]")

conn.commit()

# ── 2. suspensos ──────────────────────────────────────────────────────────────
suspensos = 0
for fid, nome_bd, nif_bd, tipo_relacao in bd_rows:
    if tipo_relacao == "Suspenso":
        continue
    if not nif_bd or nif_bd not in nifs_xlsx:
        conn.execute("UPDATE fornecedores SET tipo_relacao='Suspenso' WHERE id=?", (fid,))
        suspensos += 1
        print(f"  🔴 Suspenso: {nome_bd}")

conn.commit()

# ── 3. faturação acumulada por fornecedor e ano ───────────────────────────────
df_valido = df.dropna(subset=["ano"]).copy()
df_valido["fornecedor_id"] = df_valido["nif"].map(nifs_bd)
df_valido = df_valido.dropna(subset=["fornecedor_id"])
df_valido["fornecedor_id"] = df_valido["fornecedor_id"].astype(int)
df_valido["ano"] = df_valido["ano"].astype(int)

agg = df_valido.groupby(["fornecedor_id", "ano"])["Total"].sum().reset_index()

fat_inseridos  = 0
fat_actualizados = 0
for _, row in agg.iterrows():
    existente = conn.execute(
        "SELECT id, total FROM faturacao_anual WHERE fornecedor_id=? AND ano=?",
        (int(row["fornecedor_id"]), int(row["ano"]))
    ).fetchone()

    if existente:
        conn.execute(
            "UPDATE faturacao_anual SET total=? WHERE id=?",
            (round(row["Total"], 2), existente[0])
        )
        fat_actualizados += 1
    else:
        conn.execute(
            "INSERT INTO faturacao_anual (fornecedor_id, ano, total) VALUES (?, ?, ?)",
            (int(row["fornecedor_id"]), int(row["ano"]), round(row["Total"], 2))
        )
        fat_inseridos += 1

conn.commit()
conn.close()

print(f"\n{'═'*60}")
print(f"  ➕ Fornecedores novos         : {novos}")
print(f"  🔴 Marcados como suspensos   : {suspensos}")
print(f"  📊 Faturação inserida        : {fat_inseridos} registos")
print(f"  📊 Faturação actualizada     : {fat_actualizados} registos")
