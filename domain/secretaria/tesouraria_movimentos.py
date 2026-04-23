#atrpt/domain/secretaria/tesouraria_movimentos.py
"""
Carrega o comprovativo diário ficando apenas com os NOVOS movimentos no "inflow_diario".
    (string) : Tabela com novos movimentos
"""

from pathlib import Path
import pandas as pd

from domain.shared.strings import remover_separador, simplificar_nome

paths = paths

inflow_diario = pd.read_csv(paths["comprovativo_file"],skiprows=14,header=0,sep=';',encoding='ISO-8859-1')
inflow_acumulado = pd.read_excel(paths["inflow_file"])
  
inflow_diario.columns = inflow_diario.columns.str.strip()
inflow_diario = inflow_diario[['data','descricao', 'valor']].copy()
inflow_diario['descricao'] = (inflow_diario['descricao'].str.rstrip()
.replace(r'\s*(TRF|TFI)\s*', '', regex=True)                                    # Remove patterns like "TRF" or "TFI"
.str.strip('="'))                                                               # Remove surrounding '=' and '"'
inflow_diario['valor'] = inflow_diario['valor'].apply(remover_separador)
inflow_diario['valor'] = inflow_diario['valor'].astype(float).round(2)
inflow_diario = inflow_diario[inflow_diario['valor'] > 0].copy()
# Prepara o acumulado para comparar -retira as colunas de identificação do movimento
inflow_comparavel=inflow_acumulado.iloc[:,0:3]
#retem em inflow_diario apenas os movimentos que não estão em inflow_acumulado
merged_df = pd.merge(inflow_diario, inflow_comparavel, how='left', indicator=True)
inflow_diario = merged_df[merged_df ['_merge']=='left_only'].drop(columns=['_merge'])
return inflow_diario