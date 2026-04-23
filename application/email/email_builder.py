# application/email/email_builder.py

from application.email.email_message import EmailMessage

    
def build_email(builder, template, data, to):
    """
    Helper para construir EmailMessage a partir de um template.
    """
    subject, html = builder.build(template, data)

    return EmailMessage(
        to=[to],
        subject=subject,
        html_body=html,
    )