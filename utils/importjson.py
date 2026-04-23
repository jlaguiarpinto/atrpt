import json
import pandas as pd
from pathlib import Path

import os

# --------------------------------------------------
# CONFIG (HARDCODED)
# --------------------------------------------------
excel_path = Path(r"G:\.shortcut-targets-by-id\1U63DGZ6urrQl6543DNHJZQR93oRmv-G2\Associados\jornalatrptmarco2026_envio.xlsx")
json_path = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs"
                 r"\atrpt\logs\envio.json")

col_email = "email"
col_data = "data_envio"



# --------------------------------------------------
# 1. LER JSON
# --------------------------------------------------
with open(json_path, "r", encoding="utf-8") as f:
    data = json.load(f)

envios = data.get("envios", [])
# --------------------------------------------------
# 2. EXTRAIR EMAILS OK + TIMESTAMP
# --------------------------------------------------
envios_ok = []

for e in envios:
    if e.get("status") == "OK":
        destino = e.get("destino", [])
        timestamp = e.get("timestamp")

        if destino:
            email = destino[0].strip().lower()
            envios_ok.append((email, timestamp))

# transformar em dict para lookup rápido
map_envios = dict(envios_ok)

print(f"Envios OK encontrados: {len(map_envios)}")

# --------------------------------------------------
# 3. LER EXCEL
# --------------------------------------------------
df = pd.read_excel(excel_path)

# normalizar emails
df[col_email] = df[col_email].astype(str).str.strip().str.lower()

# garantir coluna data_envio
if col_data not in df.columns:
    df[col_data] = None

# --------------------------------------------------
# 4. ATUALIZAR
# --------------------------------------------------
count = 0

for idx, row in df.iterrows():
    email = row[col_email]

    if email in map_envios:
        df.at[idx, col_data] = map_envios[email]
        count += 1

print(f"Atualizados: {count}")

# --------------------------------------------------
# 5. GUARDAR (overwrite)
# --------------------------------------------------
df.to_excel(excel_path, index=False)

print("✔ Ficheiro atualizado com sucesso")