# importar_iban.py — com fuzzy matching e confirmação linha a linha
import sqlite3
import pandas as pd
from difflib import SequenceMatcher

XLSX_PATH = r"G:\.shortcut-targets-by-id\135tiRYPmRcH1rSzL-zzmha63-TkrIKpj\Contabilidade\Tesouraria\Pagamentos Fornecedores\IBAN.xlsx"
DB_PATH   = r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\data\atrpt.db"

PREFIXOS_REMOVER = ["enf - ", "enf. - ", "enf.- "]

def limpar_nome(nome):
    n = nome.strip()
    for p in PREFIXOS_REMOVER:
        if n.lower().startswith(p):
            n = n[len(p):].strip()
            break
    return n

def similaridade(a, b):
    return SequenceMatcher(None, a.lower(), b.lower()).ratio()

def top_candidatos(nome, xlsx_disponivel, n=10):
    scored = [(nome_x, iban_x, tipo_x, similaridade(nome, nome_x)) for nome_x, iban_x, tipo_x in xlsx_disponivel]
    scored.sort(key=lambda x: x[3], reverse=True)
    return scored[:n]

# ── ler Excel ────────────────────────────────────────────────────────────────
df = pd.read_excel(XLSX_PATH, header=None)
df = df.iloc[:, [0, 1, 4]]
df.columns = ["nome_xlsx", "iban", "tipo"]
df["nome_xlsx"]       = df["nome_xlsx"].astype(str).str.strip()
df["nome_xlsx_limpo"] = df["nome_xlsx"].apply(limpar_nome)
df["iban"]            = df["iban"].astype(str).str.strip()
df["tipo"]            = df["tipo"].astype(str).str.strip().replace("nan", "")

# ── ler BD ───────────────────────────────────────────────────────────────────
conn = sqlite3.connect(DB_PATH)
bd_rows = conn.execute("SELECT id, nome, iban, tipo_fornecedor FROM fornecedores ORDER BY nome").fetchall()

# fornecedores a processar: sem IBAN e sem "taxi" no nome
bd_sem_iban = [
    (row[0], row[1].strip(), row[2], row[3])
    for row in bd_rows
    if not row[2] and "taxi" not in row[1].lower()
]

# ibans já existentes na BD (para excluir do xlsx disponível)
ibans_ja_na_bd = {row[2] for row in bd_rows if row[2]}

print(f"\n{'═'*60}")
print(f"  Fornecedores na BD sem IBAN (excl. Taxi): {len(bd_sem_iban)}")
print(f"  IBANs já gravados na BD                 : {len(ibans_ja_na_bd)}")

actualizados    = 0
ignorados       = 0
nao_encontrados = []

for fid, nome_bd, _, _ in bd_sem_iban:

    # xlsx disponível: exclui linhas cujo IBAN já está na BD
    xlsx_disponivel = [
        (row["nome_xlsx_limpo"], row["iban"], row["tipo"])
        for _, row in df.iterrows()
        if row["iban"] not in ibans_ja_na_bd
    ]

    print(f"\n{'═'*60}")
    print(f"  BD    : {nome_bd}")
    print("─" * 60)

    candidatos = top_candidatos(nome_bd, xlsx_disponivel, n=10)

    # verificar se o 1º é correspondência exacta
    if candidatos and candidatos[0][3] == 1.0:
        nome_c, iban_c, tipo_c, score = candidatos[0]
        print(f"  ✔ Correspondência exacta: {nome_c}")
        print(f"    IBAN : {iban_c}  |  Tipo : {tipo_c}")
        resposta = input("  Actualizar? [s/n]: ").strip().lower()
        if resposta == "s":
            conn.execute(
                "UPDATE fornecedores SET iban=?, tipo_fornecedor=? WHERE id=?",
                (iban_c or None, tipo_c or None, fid)
            )
            conn.commit()
            ibans_ja_na_bd.add(iban_c)
            actualizados += 1
            print("  ✅ Actualizado.")
        else:
            ignorados += 1
            print("  ⏭️  Ignorado.")
        continue

    # sem exacta → mostrar os 10 candidatos
    print("  Candidatos Excel mais próximos:")
    for i, (nome_c, iban_c, tipo_c, score) in enumerate(candidatos, 1):
        print(f"    [{i:2d}] {nome_c:<40} ({score:.0%})")
        print(f"          IBAN: {iban_c}  |  Tipo: {tipo_c}")
    print("    [ n] Ignorar")

    while True:
        resposta = input(f"  Escolha [1-{len(candidatos)}/n]: ").strip().lower()
        if resposta.isdigit() and 1 <= int(resposta) <= len(candidatos):
            idx = int(resposta) - 1
            nome_c, iban_c, tipo_c, _ = candidatos[idx]
            conn.execute(
                "UPDATE fornecedores SET iban=?, tipo_fornecedor=? WHERE id=?",
                (iban_c or None, tipo_c or None, fid)
            )
            conn.commit()
            ibans_ja_na_bd.add(iban_c)
            actualizados += 1
            print(f"  ✅ Actualizado com: {nome_c}")
            break
        elif resposta == "n":
            ignorados += 1
            nao_encontrados.append(nome_bd)
            print("  ⏭️  Ignorado.")
            break
        else:
            print(f"  ⚠️  Resposta inválida. Introduza 1-{len(candidatos)} ou n.")

conn.close()

print(f"\n{'═'*60}")
print(f"  ✅ Actualizados  : {actualizados}")
print(f"  ⏭️  Ignorados     : {ignorados}")
if nao_encontrados:
    print(f"  ⚠️  Sem match ({len(nao_encontrados)}):")
    for n in nao_encontrados:
        print(f"     - {n}")
