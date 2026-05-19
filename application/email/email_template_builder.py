#atrpt/application/email/email_template_builder.py

import re
from pathlib import Path

from application.email.word_template_loader import carregar_template_word
from application.email.template_utils import SafeDict


class EmailTemplateBuilder:

    def __init__(self, template_dir):
        self.template_dir = Path(template_dir)

    def build(self, template_name, data):
        name = Path(template_name)
        if not name.suffix:
            name = name.with_suffix('.docx')
        template_path = self.template_dir / name

        subject, body = carregar_template_word(template_path)

        # Se o template tiver blocos [TAG]...[/TAG] e os dados tiverem tipo_texto,
        # usa o bloco correspondente; caso contrário usa o corpo completo
        tipo = data.get("tipo_texto")
        if tipo:
            matches = re.findall(r"\[([A-Za-z_]+)\](.*?)\[/\1\]", body, re.DOTALL)
            blocos = {nome: conteudo.strip() for nome, conteudo in matches}
            corpo = blocos.get(tipo, body)
        else:
            corpo = body

        subject = subject.format_map(SafeDict(data))
        corpo_formatado = corpo.format_map(SafeDict(data))

        html = f"<html><body>{corpo_formatado}</body></html>"

        return subject, html
    
    def prepara_corpo_email(row, mes_pagamento, mes_faturacao):

        gender   = row.get("genero", "")
        relation = row.get("relacao", "")
        name     = row.get("petit_nom", row.get("nome", ""))
        especial = row.get("especial", "")
        anterior = row.get("anterior", 0)

        valor_mes = row.get("atual", 0)
        total     = row.get("total", 0)

        valor_mes = 0 if pd.isna(valor_mes) else float(valor_mes)
        total     = 0 if pd.isna(total) else float(total)
        
        if valor_mes == 0:

            html = f"""
            <p>O valor de <b>{total:.2f}€</b> correspondente a facturação de farmácia
            d{gender} {relation} {name}, encontra-se por liquidar.</p>

            <p>Agradecemos o urgente pagamento para o IBAN
            PT50 0035 0651 00454681830 96.</p>
            """

        elif especial == "lar":

            html = f"""
            <p>Em anexo a facturação de farmácia de {name},
            que totaliza <b>{total:.2f}€</b>.</p>

            <p>Pagamento até dia 15 de {mes_pagamento}.</p>
            """

        elif especial == "DD":

            html = f"""
            <p>Em anexo a facturação de farmácia d{gender} {relation} {name},
            que totaliza <b>{total:.2f}€</b>.</p>

            <p>Este pagamento será realizado por débito direto
            no dia 10 de {mes_pagamento}.</p>
            """

        elif anterior and anterior != 0:

            html = f"""
            <p>Em anexo a facturação de farmácia d{gender} {relation} {name},
            no valor de {valor_mes:.2f}€.</p>

            <p>O total de <b>{total:.2f}€</b>, que inclui saldo anterior,
            deve ser pago até ao dia 15 de {mes_pagamento}
            para o IBAN PT50 0035 0651 00454681830.</p>
            """

        else:

            html = f"""
            <p>Em anexo a facturação de farmácia d{gender} {relation} {name},
            que totaliza <b>{total:.2f}€</b>.</p>

            <p>O pagamento deve ser efetuado para o IBAN
            PT50 0035 0651 00454681830 96 até ao próximo dia 15 de
            {mes_pagamento}.</p>
            """

        return f"<html><body>{html}</body></html>"