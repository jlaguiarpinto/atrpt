# atrpt/application/email/email_service.py

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import pandas as pd

from application.email.email_message import EmailMessage
from infrastructure.email.smtp_client import SmtpClient

logger = logging.getLogger(__name__)


def filtrar_pendentes(
    df: pd.DataFrame, 
    coluna_data_envio: str = "data_envio"
) -> Tuple[List[int], pd.DataFrame]:
    """
    Retorna índices e dataFrame dos emails não enviados.
    
    Args:
        df: dataFrame com os dados
        coluna_data_envio: Nome da coluna que indica se já foi enviado
    
    Returns:
        Tuple com (lista de índices, dataFrame filtrado)
    """
    if coluna_data_envio not in df.columns:
        df[coluna_data_envio] = None
    
    pendentes = df[df[coluna_data_envio].isna()]
    return pendentes.index.tolist(), pendentes


def construir_email(
    destinatario: str,
    assunto: str,
    corpo: str,
    assinatura_html: str = None,
    bcc: List[str] = None,
    attachments: List[Path] = None,
    inline_images: Dict[str, Path] = None
) -> EmailMessage:
    """
    Constrói EmailMessage com assinatura já incorporada no corpo.
    
    Args:
        destinatario: Email do destinatário
        assunto: Assunto do email
        corpo: Corpo HTML do email
        assinatura_html: Assinatura HTML a adicionar ao final
        bcc: Lista de emails em BCC
        attachments: Lista de caminhos para anexos
        inline_images: Dicionário com imagens inline {cid: path}
    
    Returns:
        EmailMessage configurado
    """
    corpo_final = corpo
    if assinatura_html:
        corpo_final += f"<br><br>{assinatura_html}"
    
    return EmailMessage(
        to=[destinatario],
        subject=assunto,
        html_body=corpo_final,
        bcc=bcc or [],
        attachments=attachments or [],
        inline_images=inline_images or {}
    )


def obter_config_smtp(
    modulo_envio: str, 
    config_app: dict
) -> dict:
    """
    Obtém configuração SMTP para o módulo a partir do app.ini.
    
    Args:
        modulo_envio: "associados", "secretaria", etc.
        config_app: Dicionário com configurações do app.ini
    
    Returns:
        Dicionário com configuração SMTP
    """
    mapeamento = {
        "associados": "smtp_associados",
        "secretaria": "smtp_secretaria",
        "tesouraria": "smtp_tesouraria",
        "presidencia": "smtp_presidencia",
        "comunicacao": "smtp_comunicacao"
    }
    
    secao = mapeamento.get(modulo_envio, "smtp_default")
    
    return {
        "server": config_app.get(secao, "server"),
        "port": config_app.getint(secao, "port"),
        "user": config_app.get(secao, "user"),
        "password": config_app.get(secao, "password"),
        "use_ssl": config_app.getboolean(secao, "use_ssl", fallback=False),
        "min_delay": config_app.getfloat(secao, "min_delay", fallback=1.5),
        "max_delay": config_app.getfloat(secao, "max_delay", fallback=4.0),
        "max_per_connection": config_app.getint(secao, "max_per_connection", fallback=40),
        "retries": config_app.getint(secao, "retries", fallback=3)
    }


def criar_smtp_client(config: dict, debug_callback=None) -> SmtpClient:
    """
    Cria e retorna uma instância de SmtpClient com a configuração fornecida.
    
    Args:
        config: Dicionário com configuração SMTP
        debug_callback: Callback para debug
    
    Returns:
        SmtpClient configurado
    """
    return SmtpClient(
        server=config["server"],
        port=config["port"],
        user=config["user"],
        password=config["password"],
        use_ssl=config.get("use_ssl", False),
        min_delay=config.get("min_delay", 1.5),
        max_delay=config.get("max_delay", 4.0),
        max_per_connection=config.get("max_per_connection", 40),
        retries=config.get("retries", 3),
        debug=debug_callback
    )


def aplicar_modo_teste(
    mensagens: List[EmailMessage], 
    email_teste: str
) -> List[EmailMessage]:
    """
    Redireciona todos os emails para o endereço de teste.
    
    Args:
        mensagens: Lista de EmailMessage
        email_teste: Email para onde redirecionar
    
    Returns:
        Lista de EmailMessage modificada
    """
    for msg in mensagens:
        msg.to = [email_teste]
        msg.bcc = []
    return mensagens


def processar_resultados(resultado: dict) -> dict:
    """
    Calcula estatísticas a partir do resultado do send_batch.
    
    Args:
        resultado: Dicionário retornado por send_batch
    
    Returns:
        Dicionário com estatísticas
    """
    total = resultado["total"]
    stats = resultado["stats"]
    
    return {
        "total_pendentes": total,
        "sucesso": stats["ok"],
        "falhas": stats["erro"],
        "interrompido": stats["interrompido"],
        "taxa_sucesso": (stats["ok"] / total * 100) if total > 0 else 0,
        "ultimo_indice": resultado["ultimo_indice"],
        "processados": resultado["processados"]
    }


def gerar_relatorio(
    resultado: dict,
    modulo_envio: str,
    log_dir: Path,
    df_info: dict = None
) -> Path:
    """
    Gera relatório JSON com todos os detalhes do envio.
    
    Args:
        resultado: Dicionário retornado por send_batch
        modulo_envio: Nome do módulo que realizou o envio
        log_dir: Diretório onde salvar o relatório
        df_info: Informações adicionais do dataFrame (opcional)
    
    Returns:
        Caminho do arquivo de relatório gerado
    """
    from datetime import datetime
    
    log_dir.mkdir(parents=True, exist_ok=True)
    
    relatorio = {
        "modulo": modulo_envio,
        "data_envio": datetime.now().isoformat(),
        "total_previsto": resultado["total"],
        "processados": resultado["processados"],
        "sucesso": resultado["stats"]["ok"],
        "falhas": resultado["stats"]["erro"],
        "interrompido": resultado["stats"]["interrompido"],
        "resultados_individuals": resultado["resultados"]
    }
    
    if df_info:
        relatorio["df_info"] = df_info
    
    filename = f"relatorio_{modulo_envio}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    filepath = log_dir / filename
    
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(relatorio, f, indent=4, ensure_ascii=False, default=str)
    
    logger.info(f"Relatório gerado: {filepath}")
    return filepath


def registrar_envio_dataframe(
    df: pd.DataFrame,
    indices: List[int],
    resultado: dict,
    log_dir: Path = None
) -> Path:
    """
    Grava o dataFrame atualizado em disco (CSV).
    
    Args:
        df: dataFrame atualizado
        indices: Índices dos emails processados
        resultado: Resultado do send_batch (para informação)
        log_dir: Diretório para salvar (opcional)
    
    Returns:
        Caminho do arquivo gerado
    """
    from datetime import datetime
    
    if log_dir:
        log_dir.mkdir(parents=True, exist_ok=True)
        filename = f"envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        filepath = log_dir / filename
    else:
        filepath = Path(f"envios_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv")
    
    df.to_csv(filepath, index=False, encoding="utf-8-sig")
    logger.info(f"dataFrame salvo: {filepath}")
    
    return filepath