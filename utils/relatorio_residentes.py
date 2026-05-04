import pandas as pd
from pathlib import Path

# -------------------------
# LOAD
# -------------------------
gdrive_csag = r"G:\.shortcut-targets-by-id\1YUU7cpAVBqQ-XmuiuqVAzKPjw-UZdVg8\CSAG"
file_path = Path(gdrive_csag) / "Tabelas" / "Residentes_cc.xlsx"

df = pd.read_excel(
    file_path,
    sheet_name="F3M",
    usecols=["ID", "DataAdmissao", "DataFim", "Activo"]
)

# -------------------------
# LIMPEZA
# -------------------------
df["ID"] = pd.to_numeric(df["ID"], errors="coerce")
df = df[~df["ID"].isin([684, 767])]

# 🔴 parsing correto
df["DataAdmissao"] = pd.to_datetime(df["DataAdmissao"], dayfirst=True, errors="coerce")
df["DataFim"] = pd.to_datetime(df["DataFim"], dayfirst=True, errors="coerce")

df["Activo"] = (
    df["Activo"].astype(str)
    .str.strip().str.lower()
    .map({"sim": True, "não": False, "nao": False})
)

df = df[df["DataAdmissao"].notna()].copy()

# -------------------------
# ATIVOS ATUAIS
# -------------------------
ativos_hoje = df[df["Activo"]].shape[0]

# -------------------------
# DATA DE REFERÊNCIA = FIM DO ÚLTIMO MÊS
# -------------------------
max_data = max(
    df["DataAdmissao"].max(),
    df["DataFim"].dropna().max()
)

mes_ref = max_data.to_period("M")
data_ref = mes_ref.to_timestamp(how="end")

print("Data referência:", data_ref.date())

# -------------------------
# EVENTOS
# -------------------------
entradas = df.groupby(df["DataAdmissao"].dt.date).size()

saidas = (
    df[df["DataFim"].notna()]
    .groupby(df["DataFim"].dt.date)
    .size()
)

# -------------------------
# EIXO DIÁRIO
# -------------------------
inicio = df["DataAdmissao"].min().normalize()
datas = pd.date_range(inicio, data_ref, freq="D")[::-1]

# -------------------------
# SIMULAÇÃO
# -------------------------
current = ativos_hoje
registos = []

for d in datas:
    entradas_dia = entradas.get(d.date(), 0)
    saidas_dia = saidas.get(d.date(), 0)

    registos.append({"Data": d, "Ativos": current})

    current = current - entradas_dia + saidas_dia

df_diario = pd.DataFrame(registos)

# -------------------------
# MÉDIAS
# -------------------------
df_diario["Ano"] = df_diario["Data"].dt.year
df_diario["Mes"] = df_diario["Data"].dt.month

media_mensal = (
    df_diario.groupby(["Ano", "Mes"])["Ativos"]
    .mean()
    .reset_index(name="Media_Ativos")
    .sort_values(["Ano", "Mes"], ascending=False)
)

media_anual = (
    df_diario.groupby("Ano")["Ativos"]
    .mean()
    .reset_index(name="Media_Ativos")
    .sort_values("Ano", ascending=False)
)

print("\n--- Média Mensal ---")
print(media_mensal)

print("\n--- Média Anual ---")
print(media_anual)