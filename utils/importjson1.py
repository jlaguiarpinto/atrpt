import json
import pandas as pd
from pathlib import Path
import os

print("RUNNING FILE:", os.path.abspath(__file__))

# --------------------------------------------------
# CONFIG (HARDCODED)
# --------------------------------------------------
excel_path = Path(r"G:\.shortcut-targets-by-id\1U63DGZ6urrQl6543DNHJZQR93oRmv-G2\Associados\jornalatrptmarco2026_envio.xlsx")
json_path = Path(r"G:\.shortcut-targets-by-id\1NsBCziGNFjlQ-f8QRcezPsKVP9QzGdp0\APPs\atrpt\logs\envio.json")

col_email = "email"
col_data = "data_envio"

# --------------------------------------------------
# 1. LER E VALIDAR JSON - VERSÃO COM TRATAMENTO DE ERRO
# --------------------------------------------------
print(f"Tentando ler JSON de: {json_path}")
print(f"Arquivo existe: {json_path.exists()}")

# Primeiro, vamos ler o arquivo como texto para inspecionar
try:
    with open(json_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    print(f"Tamanho do arquivo: {len(content)} caracteres")
    
    # Tentar encontrar o erro mostrando as linhas ao redor
    lines = content.split('\n')
    error_line = 1705  # linha do erro
    start_line = max(0, error_line - 5)
    end_line = min(len(lines), error_line + 5)
    
    print(f"\nLinhas {start_line+1} a {end_line} do arquivo:")
    for i in range(start_line, end_line):
        print(f"Linha {i+1}: {lines[i][:100]}")  # mostrar apenas os primeiros 100 caracteres
    
    # Tentar carregar o JSON
    data = json.loads(content)
    print("JSON válido!")
    
except json.JSONDecodeError as e:
    print(f"ERRO JSON: {e}")
    print(f"Posição do erro: {e.pos}")
    print(f"Linha: {e.lineno}, Coluna: {e.colno}")
    
    # Mostrar o caractere problemático
    if e.pos < len(content):
        context_start = max(0, e.pos - 20)
        context_end = min(len(content), e.pos + 20)
        print(f"\nContexto ao redor do erro:")
        print(content[context_start:context_end])
        print(" " * (e.pos - context_start) + "^")
    
    # Tentar corrigir automaticamente? (opcional)
    print("\nTentando corrigir JSON...")
    
    # Estratégia 1: Usar ast.literal_eval para strings Python (se for Python dict)
    try:
        import ast
        # Tentar interpretar como dicionário Python
        data = ast.literal_eval(content)
        print("✓ Conseguiu interpretar como Python dict")
        
        # Converter para JSON válido e salvar
        fixed_json_path = json_path.with_name(json_path.stem + "_fixed.json")
        with open(fixed_json_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"✓ Versão corrigida salva em: {fixed_json_path}")
        
    except:
        print("✗ Não foi possível corrigir automaticamente")
        exit(1)
        
except Exception as e:
    print(f"Erro inesperado: {e}")
    exit(1)

# --------------------------------------------------
# 2. EXTRAIR EMAILS OK + TIMESTAMP
# --------------------------------------------------
envios = data.get("envios", [])
envios_ok = []

for e in envios:
    if e.get("status") == "OK":
        destino = e.get("destino", [])
        timestamp = e.get("timestamp")

        if destino:
            email = destino[0].strip().lower()
            envios_ok.append((email, timestamp))

map_envios = dict(envios_ok)
print(f"\nEnvios OK encontrados: {len(map_envios)}")

# --------------------------------------------------
# 3. LER EXCEL
# --------------------------------------------------
try:
    df = pd.read_excel(excel_path)
    print(f"Excel carregado: {len(df)} linhas")
except Exception as e:
    print(f"Erro ao carregar Excel: {e}")
    exit(1)

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
# 5. GUARDAR (backup + overwrite)
# --------------------------------------------------
# Criar backup
backup_path = excel_path.with_name(excel_path.stem + "_backup" + excel_path.suffix)
df_original = pd.read_excel(excel_path)
df_original.to_excel(backup_path, index=False)
print(f"Backup criado: {backup_path}")

# Salvar atualizado
df.to_excel(excel_path, index=False)
print("✔ Ficheiro atualizado com sucesso")