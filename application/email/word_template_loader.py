# atrpt/application/email/word_template_loader.py

def carregar_template_word(path):
    """
    Suporta formatação básica do Word:
      bold, itálico, sublinhado, links, listas (• - *)
      blocos condicionais [TAG]...[/TAG]
    """
    from docx import Document
    import re

    doc = Document(path)

    subject     = None
    linhas_html = []
    lista_aberta = False

    for i, p in enumerate(doc.paragraphs):

        # 1ª linha = assunto
        if i == 0:
            subject = p.text.strip()
            continue

        texto_bruto = p.text.strip()

        if not texto_bruto:
            continue

        # ── tags de bloco: linha que é só [TAG] ou [/TAG] ─────────────────
        # emitir como marcador limpo, sem <p> à volta
        if re.fullmatch(r"\[/?[A-Za-z_]+\]", texto_bruto):
            linhas_html.append(texto_bruto)
            continue

        is_lista = texto_bruto.startswith(("•", "-", "*"))

        # ── construir texto com estilos ────────────────────────────────────
        partes = []
        for run in p.runs:
            txt = run.text
            if not txt:
                continue
            if "http://" in txt or "https://" in txt:
                txt = re.sub(r"(https?://[^\s]+)", r'<a href="\1">\1</a>', txt)
            if run.bold:
                txt = f"<b>{txt}</b>"
            if run.italic:
                txt = f"<i>{txt}</i>"
            if run.underline:
                txt = f"<u>{txt}</u>"
            partes.append(txt)

        linha = "".join(partes).strip()

        # ── listas ─────────────────────────────────────────────────────────
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

    return subject, body
