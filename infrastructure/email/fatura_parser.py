# infrastructure/email/fatura_parser.py
#
# Extração de campos de fatura a partir de texto de PDF.
# Suporta os formatos mais comuns do software PT (PHC, Primavera, Moloni, etc.).
# Limitação: PDFs digitalizados como imagem requerem OCR externo.

import io
import re
import logging

logger = logging.getLogger(__name__)

# Regex para valores monetários em formato PT/EN, incluindo separador de milhares
# com ponto, vírgula, espaço ou NBSP: 1.234,56 | 1 234,56 | 1\xa0234,56 | 1234,56
_EUR_RE = r"((?:\d{1,3}[.,\xa0 ])*\d{1,3}(?:[,.]\d{1,2})?|\d+[,.]\d{1,2}|\d+\.\d{2})"


# ------------------------------------------------------------------
# NIF — validação de checksum
# ------------------------------------------------------------------

def _valido_nif(nif: str) -> bool:
    """Valida o dígito de controlo do NIF/NIPC português (9 dígitos)."""
    if not re.match(r"^\d{9}$", nif):
        return False
    if nif[0] not in "123456789":
        return False
    resto = sum(int(nif[i]) * (9 - i) for i in range(8)) % 11
    dv = 0 if resto < 2 else 11 - resto
    return dv == int(nif[8])


# ------------------------------------------------------------------
# Extracção de texto do PDF
# ------------------------------------------------------------------

def extrair_texto_pdf(dados: bytes) -> str:
    """Extrai texto de todas as páginas do PDF. Retorna '' em PDFs de imagem."""
    try:
        import fitz
        doc = fitz.open(stream=dados, filetype="pdf")
        linhas = []
        for page in doc:
            blocos = page.get_text("dict")["blocks"]
            blocos_linha = sorted(
                [b for b in blocos if "lines" in b], key=lambda b: b["bbox"][1]
            )
            for b in blocos_linha:
                txt = " ".join(
                    span["text"] for line in b["lines"] for span in line["spans"]
                ).strip()
                if txt:
                    linhas.append(txt)
        doc.close()
        return "\n".join(linhas)
    except Exception:
        logger.debug("Erro ao extrair texto do PDF", exc_info=True)
        return ""


# ------------------------------------------------------------------
# Parse principal
# ------------------------------------------------------------------

def parse_fatura(texto: str, nif_proprio: str | None = None) -> dict:
    total = _total(texto)
    iva   = _iva(texto)
    base  = _base_tributavel(texto)
    taxa  = _iva_taxa(texto)

    # Calcular IVA quando o PDF só mostra a percentagem (ex: "IVA 23%")
    if iva is None and base is not None and taxa is not None:
        iva = round(base * taxa / 100, 2)

    # Calcular total bruto quando não está explícito mas temos base + IVA
    if total is None:
        if base is not None and iva is not None:
            total = round(base + iva, 2)
        elif base is not None:
            total = base   # melhor estimativa disponível

    return {
        "n_fatura":   _n_fatura(texto),
        "data":       _data(texto),
        "vencimento": _vencimento(texto),
        "nif":        _nif(texto, nif_proprio),
        "total":      total,
        "iva":        iva,
    }


# ------------------------------------------------------------------
# Log estruturado por fatura
# ------------------------------------------------------------------

def log_fatura(nome_pdf: str, pasta: str, assunto: str, de: str, campos: dict) -> None:
    """Regista no log toda a informação extraída de uma fatura."""

    def _fmt_val(val) -> str:
        if val is None:
            return "NÃO IDENTIFICADO"
        if isinstance(val, float):
            # Formato PT: 1.234,56 €
            return f"{val:,.2f} €".replace(",", "X").replace(".", ",").replace("X", ".")
        return str(val)

    ok  = lambda v: "✓" if v is not None else "✗"

    logger.info("══════════════════════════════════════════════════════")
    logger.info("Fatura : %s", nome_pdf)
    logger.info("Pasta  : %s", pasta)
    logger.info("Email  : \"%s\"  —  %s", assunto, de)
    logger.info("──────────────────────────────────────────────────────")
    logger.info("N.º Fatura  : %s  %s", _fmt_val(campos.get("n_fatura")),   ok(campos.get("n_fatura")))
    logger.info("Data        : %s  %s", _fmt_val(campos.get("data")),       ok(campos.get("data")))
    logger.info("Vencimento  : %s  %s", _fmt_val(campos.get("vencimento")), ok(campos.get("vencimento")))
    logger.info("NIF Emissor : %s  %s", _fmt_val(campos.get("nif")),        ok(campos.get("nif")))
    logger.info("Total       : %s  %s", _fmt_val(campos.get("total")),      ok(campos.get("total")))
    logger.info("IVA         : %s  %s", _fmt_val(campos.get("iva")),        ok(campos.get("iva")))


# ------------------------------------------------------------------
# Data — conversão para ISO e extracção de ano/mês
# ------------------------------------------------------------------

_MESES_PT = {
    "janeiro": 1, "fevereiro": 2, "março": 3, "abril": 4,
    "maio": 5, "junho": 6, "julho": 7, "agosto": 8,
    "setembro": 9, "outubro": 10, "novembro": 11, "dezembro": 12,
}


def parse_date_iso(data_str: str) -> tuple[str | None, int | None, int | None]:
    """
    Converte data extraída do PDF para (iso_str, ano, mes).
    Aceita DD/MM/AAAA, DD-MM-AAAA, DD.MM.AAAA e "1 de Janeiro de 2024".
    Devolve (None, None, None) se não reconhecido.
    """
    if not data_str:
        return None, None, None
    # Já em formato ISO (YYYY-MM-DD / YYYY/MM/DD)
    m = re.match(r"(\d{4})[/\-\.](\d{2})[/\-\.](\d{2})", data_str)
    if m:
        y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}", y, mo
    m = re.match(r"(\d{1,2})[/\-\.](\d{1,2})[/\-\.](\d{4})", data_str)
    if m:
        d, mo, y = int(m.group(1)), int(m.group(2)), int(m.group(3))
        return f"{y:04d}-{mo:02d}-{d:02d}", y, mo
    m = re.search(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", data_str, re.IGNORECASE)
    if m:
        d, mes_nome, y = int(m.group(1)), m.group(2).lower(), int(m.group(3))
        mo = _MESES_PT.get(mes_nome)
        if mo:
            return f"{y:04d}-{mo:02d}-{d:02d}", y, mo
    return None, None, None


# ------------------------------------------------------------------
# Valor monetário — normalização
# ------------------------------------------------------------------

def _parse_valor(s: str) -> float | None:
    """Converte string de valor para float. Suporta formatos PT e EN."""
    s = re.sub(r"[€$£\s  ]", "", s).strip()
    if not s:
        return None
    if "," in s and "." in s:
        # Decide pelo último separador
        if s.rfind(",") > s.rfind("."):
            s = s.replace(".", "").replace(",", ".")   # PT: 1.234,56
        else:
            s = s.replace(",", "")                     # EN: 1,234.56
    elif "," in s:
        # PT 3-decimal: "230,000" → 230.0; guard count==1 to avoid "1,234,567"
        if re.search(r",\d{1,3}$", s) and s.count(",") == 1:
            s = s.replace(",", ".")
        else:
            s = s.replace(",", "")
    elif "." in s:
        if not re.search(r"\.\d{2}$", s):
            s = s.replace(".", "")
    try:
        v = float(s)
        return v if v >= 0 else None
    except Exception:
        return None


def _candidatos(texto: str, pat: str) -> list[float]:
    vals = []
    for m in re.finditer(pat, texto, re.IGNORECASE):
        v = _parse_valor(m.group(1))
        if v is not None and v > 0:
            vals.append(v)
    return vals


# ------------------------------------------------------------------
# N.º da fatura
# ------------------------------------------------------------------

def _n_fatura(texto: str) -> str | None:
    patterns = [
        # Código PT explícito com série/número (ex: FT ACGOV2026/379, FT A/1)
        r"\b((?:FT|FR|FS|FA|NC|ND|RC|RG|VD|ORC|GT|GR)\s+[A-Z0-9]{1,15}\/\d{1,8})\b",
        r"\b((?:FT|FR|FS|FA|NC|ND|RC|RG|VD|ORC|GT|GR)[A-Z0-9]{0,15}\/\d{1,8})\b",
        r"\b((?:FT|FR|FS|FA|NC|ND|RC|RG|VD|ORC|GT|GR)\s*[A-Z0-9]{0,15}[\-\.]\d{1,8})\b",
        # Prefixo flexível 1-3 chars (ex: Air Liquide "F2 B1B9/0350021802")
        r"\b([A-Z]{1,3}\d?\s+[A-Z0-9]{2,15}\/\d{4,12})\b",
        # Etiqueta explícita de número de fatura
        r"(?:N\.?[ºo]\.?\s+(?:de\s+)?(?:Fatura|Factura|Documento|Invoice)|"
        r"(?:Fatura|Factura|Invoice)\s+N\.?[ºo]\.?)\s*[:\s]+([A-Z0-9][A-Z0-9\s\-\/\.]{2,28})",
        # Número de Documento genérico
        r"(?:N\.?[ºo]\.?\s*Documento|Document\s+N[ou]mber|Invoice\s+N[ou]mber)"
        r"\s*[:\s]+([A-Z0-9][A-Z0-9\-\/\.]{2,24})",
    ]
    for pat in patterns:
        m = re.search(pat, texto, re.IGNORECASE | re.MULTILINE)
        if m:
            val = m.group(1).strip().rstrip(".")
            if 3 <= len(val) <= 35:
                return val
    return None


# ------------------------------------------------------------------
# Data
# ------------------------------------------------------------------

# ISO primeiro (YYYY-MM-DD) para evitar ambiguidade com DD/MM/YYYY
_DATE_RE = r"(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2}|\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{2,4})"


def _data(texto: str) -> str | None:
    # Etiqueta + data na mesma linha
    m = re.search(
        r"(?:Data\s*(?:de\s*)?(?:Emiss[aã]o|Fatura|Factura|Venda|Document[oe])?|Date)"
        r"\s*[:\-]?\s*" + _DATE_RE,
        texto, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Mesma linha com texto intermédio — captura a PRIMEIRA data ISO (ex: ACGOV)
    # "Data Vencimento ... 2026-03-03 2026-04-02" → 2026-03-03
    m = re.search(r"\bData\b[^\n]+?(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})", texto, re.IGNORECASE)
    if m:
        return m.group(1)
    # Etiqueta na linha anterior (com possível linha intermédia de outra etiqueta)
    # Cobre: "Data\n15/05" e "Data  Vencimento\n15/05  15/06"
    m = re.search(
        r"\bData\b[^\n]*\n(?:[^\n\d]*\n)?\s*" + _DATE_RE,
        texto, re.IGNORECASE,
    )
    if m:
        return m.group(1)
    # Data por extenso: "1 de Janeiro de 2024"
    m = re.search(r"\b(\d{1,2}\s+de\s+\w+\s+de\s+\d{4})\b", texto, re.IGNORECASE)
    if m:
        return m.group(1)
    # Fallback: primeira data DD/MM/AAAA no documento
    m = re.search(r"\b(\d{1,2}[\/\-\.]\d{1,2}[\/\-\.]\d{4})\b", texto)
    return m.group(1) if m else None


# ------------------------------------------------------------------
# NIF do emissor
# ------------------------------------------------------------------

def _nif(texto: str, nif_proprio: str | None = None) -> str | None:
    """
    Devolve o NIF do emissor.
    Estratégia: primeiro identifica NIFs marcados como do CLIENTE e exclui-os;
    depois devolve o primeiro NIF válido com etiqueta de emissor.
    nif_proprio — NIF da organização compradora, sempre excluído (lido de app.ini).
    """
    # Identificar NIFs do cliente para excluir (V/NIF, NIF do cliente, etc.)
    _cliente_pats = (
        r"V[/.]?\s*(?:NIF|Contribuinte)[^\d]{0,10}(\d{9})",
        r"(?:NIF|Contribuinte)\s+(?:do\s+)?[Cc]liente[^\d]{0,10}(\d{9})",
        r"(?:Seu|Vosso)\s+(?:NIF|Contribuinte)[^\d]{0,10}(\d{9})",
        r"Adquirente[^\d]{0,30}(\d{9})",
    )
    cliente_nipc: set[str] = {nif_proprio} if nif_proprio else set()
    for pat in _cliente_pats:
        for m in re.finditer(pat, texto, re.IGNORECASE):
            nif = m.group(1)
            if _valido_nif(nif):
                cliente_nipc.add(nif)

    # Padrões de emissor, do mais explícito ao menos (ordem de preferência)
    _emissor_pats = (
        r"[Mm]atric[uo]la\s*/?\s*NIPC\s+(\d{9})",
        r"N\.I\.P\.C\.\s+(\d[\d ]{6,8}\d)",
        r"(?:NIF|NIPC|Contribuinte|N\.I\.F\.?C?|C[oó]d\.?\s*Fiscal)\s*[:\s]+(?:PT)?\s*(\d{9})",
        r"(?:NIF|NIPC|Contribuinte)[^\d]{0,15}(\d{9})",
    )
    for pat in _emissor_pats:
        for m in re.finditer(pat, texto, re.IGNORECASE):
            nif = re.sub(r"\s", "", m.group(1))
            if _valido_nif(nif) and nif not in cliente_nipc:
                return nif

    return None


# ------------------------------------------------------------------
# Total da fatura
# ------------------------------------------------------------------

def _total(texto: str) -> float | None:
    """Total bruto (com IVA). Só padrões que indicam montante final a pagar."""
    patterns_hc = [
        r"Total\s+[Aa]\s+[Pp]agar\s*[:\s]*€?\s*" + _EUR_RE,
        r"(?:Valor\s+)?Total\s+(?:da\s+)?(?:Fatura|Factura)\s*[:\s]*€?\s*" + _EUR_RE,
        r"Total\s+(?:com|incl\.?\s*)IVA\s*[:\s]*€?\s*" + _EUR_RE,
        r"Total\s+(?:Geral|EUR|Incl\.?)\s*[:\s]*€?\s*" + _EUR_RE,
        r"Total\s*\(\s*EUR\s*\)\s*" + _EUR_RE,
        r"Montante\s+Total\s*[:\s]*€?\s*" + _EUR_RE,
        r"Grand\s+Total\s*[:\s]*€?\s*" + _EUR_RE,
        r"Valor\s+Total\s*[:\s]*€?\s*" + _EUR_RE,
        r"Importe\s+Total\s*[:\s]*€?\s*" + _EUR_RE,
    ]
    for pat in patterns_hc:
        vals = _candidatos(texto, pat)
        if vals:
            return vals[0]

    # "TOTAL" em maiúsculas — última ocorrência (total final)
    todas = list(re.finditer(r"TOTAL\s*[:\s]*€?\s*" + _EUR_RE, texto))
    if todas:
        v = _parse_valor(todas[-1].group(1))
        if v and v > 0:
            return v

    # "Total" genérico — última ocorrência
    todas = list(re.finditer(r"\bTotal\s*[:\s]*€?\s*" + _EUR_RE, texto, re.IGNORECASE))
    if todas:
        v = _parse_valor(todas[-1].group(1))
        if v and v > 0:
            return v

    return None


# ------------------------------------------------------------------
# Base tributável (total líquido antes de IVA)
# ------------------------------------------------------------------

def _base_tributavel(texto: str) -> float | None:
    """
    Captura o valor líquido/base tributável antes de IVA.
    Usado quando o PDF não mostra o total bruto directamente.
    """
    pats = [
        # "MERCADORIA/SERVIÇOS" seguido de valor (mesma linha ou linha seguinte)
        r"MERCADORIA[S]?[/\s]*SERVI[CÇ][OA]S?\s*[:\s]*\n?\s*" + _EUR_RE,
        r"Base\s+[Tt]ribut[áa]vel\s*[:\s]*€?\s*" + _EUR_RE,
        r"Base\s+[Ii]ncid[êe]ncia\s*[:\s]*€?\s*" + _EUR_RE,
        r"Valor\s+[Ll][íi]quido\s*[:\s]*€?\s*" + _EUR_RE,
        r"Total\s+[Ll][íi]quido\s*[:\s]*€?\s*" + _EUR_RE,
        r"Montante\s+[Ll][íi]quido\s*[:\s]*€?\s*" + _EUR_RE,
    ]
    for pat in pats:
        vals = _candidatos(texto, pat)
        if vals:
            return vals[0]
    return None


# ------------------------------------------------------------------
# Taxa de IVA (percentagem)
# ------------------------------------------------------------------

def _iva_taxa(texto: str) -> float | None:
    """Captura a taxa de IVA em % (ex: '23%' → 23.0). Ignora linhas com valor €."""
    for pat in (
        r"\bIVA\s*[:\s]*(\d{1,2}(?:[,.]\d{1,2})?)\s*%",
        r"Taxa\s+(?:de\s+)?IVA\s*[:\s]*(\d{1,2}(?:[,.]\d{1,2})?)\s*%",
        r"(\d{1,2}(?:[,.]\d{1,2})?)\s*%\s+IVA\b",
    ):
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            try:
                return float(m.group(1).replace(",", "."))
            except ValueError:
                pass
    return None


# ------------------------------------------------------------------
# Data de vencimento
# ------------------------------------------------------------------

def _vencimento(texto: str) -> str | None:
    pats = [
        # Etiqueta + data na mesma linha
        r"(?:Data\s+(?:de\s+)?)?[Vv]encimento\s*[:\-]?\s*" + _DATE_RE,
        r"[Pp]razo\s+(?:de\s+)?[Pp]agamento\s*[:\-]?\s*" + _DATE_RE,
        r"[Pp]ayment\s+[Dd]ue\s*[:\-]?\s*" + _DATE_RE,
        r"[Dd]ue\s+[Dd]ate\s*[:\-]?\s*" + _DATE_RE,
        # Mesma linha com texto intermédio — captura a ÚLTIMA data ISO (ex: ACGOV)
        # "Data Vencimento ... 2026-03-03 2026-04-02" → 2026-04-02
        r"\bVencimento\b[^\n]+(\d{4}[\/\-\.]\d{2}[\/\-\.]\d{2})",
        # Etiqueta na linha anterior; captura primeira data na linha seguinte
        r"\bVencimento\b[^\n]*\n\s*" + _DATE_RE,
    ]
    for pat in pats:
        m = re.search(pat, texto, re.IGNORECASE)
        if m:
            return m.group(1)
    return None


# ------------------------------------------------------------------
# IVA
# ------------------------------------------------------------------

def _iva(texto: str) -> float | None:
    # Linha de total IVA agregado
    for pat in (
        r"Total\s+IVA\s*[:\s]*€?\s*" + _EUR_RE,
        r"IVA\s+Total\s*[:\s]*€?\s*" + _EUR_RE,
        r"Total\s+(?:de\s+)?IVA\s*[:\s]*€?\s*" + _EUR_RE,
        r"IVA\s+(?:a\s+)?[Pp]agar\s*[:\s]*€?\s*" + _EUR_RE,
    ):
        vals = _candidatos(texto, pat)
        if vals:
            return vals[0]

    # IVA por taxa — "IVA 23% 230,00" — captura valor, exclui a percentagem
    patron_taxa = r"IVA\s+\d{1,2}\s*%\s+(?:[-–—]\s*)?€?\s*((?:\d{1,3}\.)*\d{1,3},\d{2}|\d+,\d{2})"
    vals = _candidatos(texto, patron_taxa)
    if vals:
        return round(sum(vals), 2)

    # Fallback: "IVA" seguido de valor monetário (ignora linhas com %)
    vals = []
    for m in re.finditer(r"\bIVA\s*[:\s]*€?\s*" + _EUR_RE, texto, re.IGNORECASE):
        after = texto[m.end():m.end() + 8]
        if "%" not in after:
            v = _parse_valor(m.group(1))
            if v is not None and v >= 0:
                vals.append(v)
    return round(sum(vals), 2) if vals else None
