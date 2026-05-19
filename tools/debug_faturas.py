"""
tools/debug_faturas.py
======================
Lê PDFs de faturas, mostra os campos extraídos e permite confirmar ou corrigir
cada valor campo a campo. As correções são guardadas em tools/correcoes_faturas.json
para apoiar a melhoria do parser.

Uso:
    python tools/debug_faturas.py                        # 5 amostras de PASTA_FATURAS
    python tools/debug_faturas.py ficheiro.pdf           # PDF específico
    python tools/debug_faturas.py pasta/  [N|all]        # N PDFs da pasta (default=5)

Interação por fatura:
    Enter   — todos os campos estão corretos, passa à próxima
    r       — rever campo a campo (Enter=OK, ou digitar o valor correto)
    q       — sair
"""

import io
import json
import sys
from datetime import datetime
from pathlib import Path

# UTF-8 no stdout (Windows)
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

# Permite importar do projecto sem instalar
sys.path.insert(0, str(Path(__file__).parent.parent))
from infrastructure.email.fatura_parser import extrair_texto_pdf, parse_fatura

_PASTA_FATURAS = Path(
    r"G:\.shortcut-targets-by-id\1Qr9fyP5j561vVIXw8b6mKJvgTyhTQF14\Secretaria\Faturas"
)
_CORRECOES_JSON = Path(__file__).parent / "correcoes_faturas.json"

_SEP  = "─" * 64
_CAMPOS = [
    ("n_fatura",   "N.º Fatura"),
    ("nif",        "NIF"),
    ("data",       "Data"),
    ("vencimento", "Vencimento"),
    ("total",      "Total (€)"),
    ("iva",        "IVA (€)"),
]


# ------------------------------------------------------------------
# Persistência de correções
# ------------------------------------------------------------------

def _carregar_correcoes() -> list:
    if _CORRECOES_JSON.exists():
        try:
            return json.loads(_CORRECOES_JSON.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _guardar_correcao(pdf_nome: str, campo: str, extraido, correto: str) -> None:
    dados = _carregar_correcoes()
    dados.append({
        "pdf":       pdf_nome,
        "campo":     campo,
        "extraido":  str(extraido) if extraido is not None else None,
        "correto":   correto,
        "data":      datetime.now().isoformat(timespec="seconds"),
    })
    _CORRECOES_JSON.write_text(
        json.dumps(dados, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )


# ------------------------------------------------------------------
# Formatação
# ------------------------------------------------------------------

def _fmt(val) -> str:
    return str(val) if val is not None else "—"


def _ok(val) -> str:
    return "✓" if val is not None else "✗"


def _mostrar_campos(campos: dict) -> None:
    for chave, label in _CAMPOS:
        val = campos.get(chave)
        print(f"  {_ok(val)}  {label:<14}{_fmt(val)}")


# ------------------------------------------------------------------
# Revisão campo a campo
# ------------------------------------------------------------------

def _rever_campos(pdf_nome: str, campos: dict) -> dict:
    """
    Percorre cada campo interativamente.
    Enter = OK; qualquer outro texto = valor correto.
    Devolve dict com eventuais correções aplicadas.
    """
    resultado = dict(campos)
    corrigidos = []

    print()
    for chave, label in _CAMPOS:
        val = campos.get(chave)
        indicador = _ok(val)
        display   = _fmt(val)
        try:
            resp = input(f"  {indicador}  {label:<14}{display}  → ").strip()
        except EOFError:
            break
        if resp and resp != display and resp != "—":
            resultado[chave] = resp
            _guardar_correcao(pdf_nome, chave, val, resp)
            corrigidos.append((label, display, resp))

    if corrigidos:
        print()
        print("  Correções registadas:")
        for label, antes, depois in corrigidos:
            print(f"    {label:<14}{antes}  →  {depois}")

    return resultado


# ------------------------------------------------------------------
# Debug de um PDF
# ------------------------------------------------------------------

def debug_pdf(path: Path, restam: int) -> bool:
    """
    Processa um PDF e interage com o utilizador.
    Devolve False se o utilizador pedir para sair.
    """
    print(f"\n{_SEP}")
    print(f"  {path.name}  ({path.stat().st_size // 1024} KB)")
    print(_SEP)

    try:
        texto = extrair_texto_pdf(path.read_bytes())
    except Exception as exc:
        print(f"  ERRO ao ler PDF: {exc}")
    else:
        if not texto.strip():
            print("  (sem texto — provável PDF de imagem digitalizada)")
        else:
            campos = parse_fatura(texto)
            _mostrar_campos(campos)

            sufixo = f"[{restam} restante(s)]  " if restam > 0 else ""
            try:
                resp = input(
                    f"\n  {sufixo}Enter=OK  r=rever campos  q=sair : "
                ).strip().lower()
            except EOFError:
                return False

            if resp == "q":
                return False
            if resp == "r":
                _rever_campos(path.name, campos)

    return True


# ------------------------------------------------------------------
# Main
# ------------------------------------------------------------------

def main():
    args = sys.argv[1:]

    if not args:
        pasta = _PASTA_FATURAS
        if not pasta.exists():
            print(f"Pasta não encontrada: {pasta}")
            sys.exit(1)
        pdfs = sorted(pasta.glob("*.pdf"))
        # Uma amostra por fornecedor (prefixo antes de "_")
        vistos: set[str] = set()
        selecao = []
        for p in pdfs:
            prefixo = p.name.split("_")[0]
            if prefixo not in vistos:
                vistos.add(prefixo)
                selecao.append(p)
            if len(selecao) >= 5:
                break
        print(f"{len(pdfs)} PDFs na pasta — a mostrar {len(selecao)} amostras")
        for i, p in enumerate(selecao):
            if not debug_pdf(p, restam=len(selecao) - i - 1):
                break
        return

    alvo = Path(args[0])

    if alvo.is_file():
        debug_pdf(alvo, restam=0)
        return

    if alvo.is_dir():
        limite_raw = args[1] if len(args) > 1 else "5"
        pdfs = sorted(alvo.glob("*.pdf"))
        limite = len(pdfs) if limite_raw.lower() == "all" else int(limite_raw)
        print(f"{len(pdfs)} PDFs na pasta — a mostrar {limite}")
        for i, p in enumerate(pdfs[:limite]):
            if not debug_pdf(p, restam=limite - i - 1):
                break
        return

    print(f"Caminho não encontrado: {alvo}")
    sys.exit(1)


if __name__ == "__main__":
    main()
