# atrpt/application/email/enviar_doc_usecase.py
"""
Use case genérico para envio de documentos por email (faturas, recibos, etc.).
Parametrizado pelo repositório, template e função de tipo de texto.

Exemplos de uso:
    # Faturas
    uc = EnviarDocUseCase(
        emailer            = emailer,
        ctx                = ctx,
        doc_repo           = faturacao_repo,
        envio_repo         = envio_faturas_repo,
        template_path      = ctx.template_email,  # caminho completo
        definir_tipo_texto = _tipo_fatura,
        modulo_log         = "secretaria_faturas",
        logger             = logger,
    )

    # Recibos PIM
    uc = EnviarDocUseCase(
        emailer            = emailer,
        ctx                = ctx,
        doc_repo           = recibos_repo,
        envio_repo         = envio_recibos_repo,
        template_path      = cfg.paths["template_recibo_pim"],  # caminho completo
        definir_tipo_texto = _tipo_recibo,
        modulo_log         = "pim_recibos",
        logger             = logger,
    )
"""

import ast
from pathlib import Path
from typing import Callable
import pandas as pd

from application.email.email_message import EmailMessage
from application.email.email_template_builder import EmailTemplateBuilder
from application.email.email_sender import EmailSender


class EnviarDocUseCase:

    def __init__(
        self,
        emailer,
        ctx,
        doc_repo,
        envio_repo,
        template_path: str | Path,  # caminho completo para o ficheiro .docx
        definir_tipo_texto: Callable[[pd.Series], str],
        modulo_log: str = "email",
        tamanho_lote: int = 25,
        pausa_entre_lotes: tuple = (60, 120),
        delay_envio: tuple = (3, 6),
        logger=None,
    ):
        self.email_sender       = EmailSender(emailer)
        self.ctx                = ctx
        self.doc_repo           = doc_repo
        self.envio_repo         = envio_repo
        self.template_path      = template_path  # caminho completo para o ficheiro .docx
        self.definir_tipo_texto = definir_tipo_texto
        self.modulo_log         = modulo_log
        self.tamanho_lote       = tamanho_lote
        self.pausa_entre_lotes  = pausa_entre_lotes
        self.delay_envio        = delay_envio
        self.logger             = logger

    # ── FASE 1 — Preparar ficheiro de envio ──────────────────────────────────

    def preparar(self, **kwargs) -> dict:
        """
        Lê doc_repo, filtra linhas com email e sem data_envio,
        constrói assunto + HTML para cada linha a partir do template Word,
        resolve nomes de anexos e guarda o ficheiro de envio via repositório.

        kwargs são acrescentados ao data do template (ex: mes_faturacao, mes_pagamento).
        Devolve {"ficheiro_envio": str(caminho), "total": int}.
        """
        self.logger.info(f"[{self.modulo_log}] A preparar emails...")

        df = self.doc_repo.ler()
        df = df[df["email"].notna() & df["data_envio"].isna()].copy()

        if df.empty:
            self.logger.info("Nenhuma linha elegível para envio.")
            return {"ficheiro_envio": str(self.envio_repo._path), "total": 0}

        # acrescentar kwargs ao df (ex: mes_pagamento, mes_faturacao)
        for k, v in kwargs.items():
            df[k] = v

        # template_path: caminho completo passado no construtor
        template_path = Path(self.template_path)
        builder       = EmailTemplateBuilder(template_dir=template_path.parent)
        template_name = template_path.name

        def build_row(row):
            data = row.to_dict()
            data["tipo_texto"] = self.definir_tipo_texto(row)
            return builder.build(template_name, data)

        resultados        = df.apply(build_row, axis=1)
        df["subject"]     = [r[0] for r in resultados]
        df["html_body"]   = [r[1] for r in resultados]
        df["attachments"] = df.get("filename", pd.Series("", index=df.index)).apply(
            self._build_attachments
        )

        self.envio_repo.guardar(df)
        self.logger.info(
            f"Ficheiro envio criado: {self.envio_repo._path} ({len(df)} registos)"
        )
        return {"ficheiro_envio": str(self.envio_repo._path), "total": len(df)}

    # ── FASE 2 — Enviar ───────────────────────────────────────────────────────

    def enviar(self, on_progress=None) -> dict:
        """
        Lê o ficheiro de envio, filtra pendentes (data_envio nula),
        constrói os EmailMessage e delega no EmailSender.send_batch.
        """
        df_completo  = self.envio_repo.ler()
        df_pendentes = df_completo[df_completo["data_envio"].isna()]

        if df_pendentes.empty:
            if on_progress:
                on_progress("✅ Nenhum email pendente para envio")
            return {"status": "ok", "enviados": 0, "erros": 0,
                    "mensagem": "Nenhum email pendente"}

        total_pendentes = len(df_pendentes)
        self.logger.info(f"Enviando {total_pendentes} emails pendentes")
        if on_progress:
            on_progress(f"📧 Enviando {total_pendentes} emails pendentes")

        indices_reais = df_pendentes.index.tolist()

        mensagens = [
            EmailMessage(
                to        = [row["email"]],
                subject   = row["subject"],
                html_body = row["html_body"],
                attachments = self._resolver_caminhos_attachments(row.get("attachments")),
                bcc       = [],
            )
            for _, row in df_pendentes.iterrows()
        ]

        resultado = self.email_sender.send_batch(
            mensagens         = mensagens,
            repo              = self.envio_repo,
            df                = df_completo,
            df_indices        = indices_reais,
            coluna_data_envio = "data_envio",
            coluna_status     = "status_envio",
            coluna_erro       = "erro_envio",
            tamanho_lote      = self.tamanho_lote,
            max_por_conexao   = 40,
            pausa_entre_lotes = self.pausa_entre_lotes,
            delay_envio       = self.delay_envio,
            modulo_log        = self.modulo_log,
            on_progress       = on_progress,
        )

        self.logger.info(
            f"Envio concluído → OK: {resultado['stats']['ok']} "
            f"| ERROS: {resultado['stats']['erro']}"
        )

        return {
            "status":          "ok",
            "enviados":        resultado["stats"]["ok"],
            "erros":           resultado["stats"]["erro"],
            "total_pendentes": total_pendentes,
            "interrompido":    resultado["stats"]["interrompido"],
        }

    # ── helpers privados ──────────────────────────────────────────────────────

    def _resolver_caminhos_attachments(self, value) -> list[Path]:
        return [
            p if p.is_absolute() else Path(self.ctx.pim_mensal_dir) / p
            for p in (Path(n) for n in self._parse_attachments(value))
        ]

    def _parse_attachments(self, value) -> list[str]:
        if value is None or (isinstance(value, float) and pd.isna(value)):
            return []
        if isinstance(value, list):
            return [str(v) for v in value]
        if isinstance(value, str):
            value = value.strip()
            if not value:
                return []
            if value.startswith("["):
                try:
                    parsed = ast.literal_eval(value)
                    if isinstance(parsed, list):
                        return [str(v) for v in parsed]
                except (ValueError, SyntaxError):
                    self.logger.warning(f"Não foi possível interpretar attachments: {value!r}")
            return [value]
        return [str(value)]

    def _build_attachments(self, value) -> list[str]:
        return [Path(n).name for n in self._parse_attachments(value)]


# ── Funções de tipo de texto prontas a usar ───────────────────────────────────

def tipo_fatura(row: pd.Series) -> str:
    """Para Envio_Faturas.docx — DD / TBsemdivida / TBcomdivida."""
    especial = str(row.get("especial", "") or "").strip()
    if especial == "DD":
        return "DD"
    try:
        anterior = float(row.get("anterior") or 0)
    except (ValueError, TypeError):
        anterior = 0.0
    return "TBsemdivida" if anterior == 0.0 else "TBcomdivida"


def tipo_recibo_pim(row: pd.Series) -> str:
    """Para Recibo_PIM.docx — COM_SALDO / SEM_SALDO."""
    try:
        saldo = float(row.get("saldo") or 0)
    except (ValueError, TypeError):
        saldo = 0.0
    return "COM_SALDO" if saldo != 0.0 else "SEM_SALDO"
