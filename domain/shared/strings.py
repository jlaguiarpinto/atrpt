#atrpt/BLLdomain/shared/strings.py
import unicodedata
import re
import pandas as pd

PARTICULAS = {
    "de", "da", "do", "das", "dos", "di", "du", "del", "della", "van", "von", "e"
}

def normalizar(txt: str) -> str:                    #remove acentos, lower, retita caracteres não alfanuméricos
    if not isinstance(txt, str) or not txt.strip():
        return ""
    txt = remover_acentos(txt)
    txt = txt.strip().lower()
    txt = limpar_string(txt)
    return txt
    
def custom_converter(value):                        # Remove aspas duplas no início e no fim de string
    if value.startswith('="') and value.endswith('"'):
        return value[2:-1]
    return value

def remover_separador(valor):                   # Remove o separador de milhar e substituir a vírgula por ponto
    if isinstance(valor, float):  return valor
    if isinstance(valor, str):    return float(valor.replace('.', '').replace(',', '.'))

def remover_acentos(texto):                     # Remove acentuação
    if isinstance(texto, str):      
        return ''.join(c for c in unicodedata.normalize('NFKD', texto) if not unicodedata.combining(c))
    return texto  # Retorna sem alterações se não for string
    
def limpar_string(texto):                       # Retira da string caracteres não alfanuméricos
    if isinstance(texto, str):
        return re.sub(r'[^a-zA-Z0-9]', '', texto)
    return texto

def captura_nome(nome):
    tokens = _tokens_relevantes(nome)

    if len(tokens) <= 1:
        return nome

    return " ".join(tokens[:-1])  # tudo menos último

def simplificar_nome(nome):

    tokens = _tokens_relevantes(nome)

    if not tokens:
        return nome

    if len(tokens) == 1:
        return tokens[0]

    # regra especial Maria (mantida mas controlada)
    if tokens[0].lower() == "maria" and len(tokens) > 2:
        primeiro = tokens[1]
    else:
        primeiro = tokens[0]

    ultimo = tokens[-1]

    return f"{primeiro} {ultimo}"

def _tokens_relevantes(nome):

    if pd.isna(nome) or not str(nome).strip():
        return []

    nome = str(nome)

    nome = re.sub(r'-\d+$', '', nome)
    nome = re.sub(r'\s+', ' ', nome).strip()

    tokens = nome.split()

    return [t for t in tokens if t.lower() not in PARTICULAS]

def normalizar_colunas(df):
    df = df.copy()
    df.columns = df.columns.map(normalizar_coluna)
    return df

def normalizar_coluna(c):
        c = remover_acentos(str(c))
        c = c.strip().lower()
        c = re.sub(r"[^a-z0-9]+", "_", c)
        c = re.sub(r"_+", "_", c)
        c = c.strip("_")
        return c


def normalizar_nome(s: str) -> str:
    if not isinstance(s, str):
        return ""

    # remover acentos
    s = "".join(
        c for c in unicodedata.normalize("NFKD", s)
        if unicodedata.category(c) != "Mn"
    )

    # minúsculas
    s = s.lower()

    # remover palavras pouco relevantes
    s = re.sub(r"\b(de|da|do|dos|das)\b", "", s)

    # remover tudo que não seja letra ou número
    s = re.sub(r"[^a-z0-9]", "", s)

    return s