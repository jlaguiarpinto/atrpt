#atrpt/application/email/word_template_loader.py

def carregar_template_word(path):
    """   Suporta formatação básica do Word, incluindo:
    bold
    itálico
    <u>sublinhado</u>           Word (Ctrl+B, Ctrl+I, Ctrl+U)
    links clicáveis             Word (Ctrl+K) ou links automáticos (http/https)
    listas (• - *)              Word (Ctrl+Shift+L) ou manualmente com símbolos • Item 1
    parágrafos
    blocos [TAG]...[/TAG]       word (pode ser usado para criar blocos condicionais, por exemplo [DIVIDA]...[/DIVIDA])
    """


    from docx import Document
    import re

    doc = Document(path)

    subject = None
    linhas_html = []

    lista_aberta = False

    for i, p in enumerate(doc.paragraphs):

        # -------------------------
        # SUBJECT
        # -------------------------
        if i == 0:
            subject = p.text.strip()
            continue

        texto_bruto = p.text.strip()

        if not texto_bruto:
            continue

        # -------------------------
        # DETETAR LISTAS
        # -------------------------
        is_lista = texto_bruto.startswith(("•", "-", "*"))

        # -------------------------
        # CONSTRUIR TEXTO COM ESTILOS
        # -------------------------
        partes = []

        for run in p.runs:
            txt = run.text

            if not txt:
                continue

            # link automático (http/https)
            if "http://" in txt or "https://" in txt:
                txt = re.sub(
                    r"(https?://[^\s]+)",
                    r'<a href="\1">\1</a>',
                    txt
                )

            if run.bold:
                txt = f"<b>{txt}</b>"

            if run.italic:
                txt = f"<i>{txt}</i>"

            if run.underline:
                txt = f"<u>{txt}</u>"

            partes.append(txt)

        linha = "".join(partes).strip()

        # -------------------------
        # LISTAS
        # -------------------------
        if is_lista:

            if not lista_aberta:
                linhas_html.append("<ul>")
                lista_aberta = True

            linha = linha.lstrip("•-* ").strip()

            linhas_html.append(f"<li>{linha}</li>")

        else:

            if lista_aberta:
                linhas_html.append("</ul>")
                lista_aberta = False

            linhas_html.append(f"<p>{linha}</p>")

    if lista_aberta:
        linhas_html.append("</ul>")

    body = "\n".join(linhas_html)

    # -------------------------
    # EXTRAIR BLOCOS
    # -------------------------
    blocos = {}

    matches = re.findall(r"\[(\w+)\](.*?)\[/\1\]", body, re.DOTALL)

    for nome, conteudo in matches:
        blocos[nome] = conteudo.strip()

    return subject, blocos