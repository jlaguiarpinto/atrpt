# atrpt/application/secretaria/enviar_faturas_usecase.py

import ast
from datetime import datetime
from pathlib import Path
import pandas as pd

from application.email.email_message import EmailMessage
from application.email.email_template_builder import EmailTemplateBuilder
from application.email.email_sender import EmailSender


class EnviarFaturasPimUseCase:

    def __init__(self, emailer, ctx, faturacao_repo, envio_faturas_repo, logger=None):
        self.email_sender        = EmailSender(emailer)
        self.ctx                 = ctx
        self.faturacao_repo      = faturacao_repo
        self.envio_faturas_repo  = envio_faturas_repo
        self.logger              = logger

    # --------------------------------------------------
    # FASE 1 — Preparar ficheiro de envio
    # --------------------------------------------------

    def preparar(self, mes_faturacao: str, mes_pagamento: str) -> dict:
        """
        Lê faturacao_repo, filtra linhas com email e sem data_envio,
        constrói assunto + HTML para cada linha a partir do template Word,
        resolve nomes de anexos e guarda o ficheiro de envio via repositório.

        Devolve {"ficheiro_envio": str(caminho), "total": int}.
        """
        self.logger.info("A preparar emails para envio...")

        df = self.faturacao_repo.ler()
        df = df[df["email"].notna() & df["data_envio"].isna()].copy()

        if df.empty:
            self.logger.info("Nenhuma linha elegível para envio.")
            return {"ficheiro_envio": str(self.envio_faturas_repo._path), "total": 0}

        df["mes_faturacao"] = mes_faturacao
        df["mes_pagamento"]  = mes_pagamento

        template_path = Path(self.ctx.template_email)
        builder       = EmailTemplateBuilder(template_dir=template_path.parent)
        template_name = template_path.name

        def build_row(row):
            data = row.to_dict()
            data["tipo_texto"] = self._definir_tipo_texto(row)
            subject, html = builder.build(template_name, data)
            return subject, html

        resultados = df.apply(build_row, axis=1)
        df["subject"]     = [r[0] for r in resultados]
        df["html_body"]   = [r[1] for r in resultados]
        df["attachments"] = df["filename"].apply(self._build_attachments)

        self.envio_faturas_repo.guardar(df)

        self.logger.info(
            f"Ficheiro envio criado: {self.envio_faturas_repo._path} ({len(df)} registos)"
        )

        return {
            "ficheiro_envio": str(self.envio_faturas_repo._path),
            "total": len(df),
        }

    # --------------------------------------------------
    # FASE 2 — Enviar
    # --------------------------------------------------

    def enviar(self, on_progress=None) -> dict:
        """
        Lê o ficheiro de envio, filtra pendentes (data_envio nula),
        constrói os EmailMessage com caminhos absolutos para os PDFs
        e delega no EmailSender.send_batch.

        O send_batch recebe o repositório e chama repo.guardar(df)
        após cada lote e no finally — não é necessário guardar aqui.

        Devolve {"status", "enviados", "erros", "total_pendentes", "interrompido"}.
        """
        df_completo    = self.envio_faturas_repo.ler()
        mask_pendentes = df_completo["data_envio"].isna()
        df_pendentes   = df_completo[mask_pendentes]

        if df_pendentes.empty:
            if on_progress:
                on_progress("✅ Nenhum email pendente para envio")
            return {
                "status":   "ok",
                "enviados": 0,
                "erros":    0,
                "mensagem": "Nenhum email pendente",
            }

        total_pendentes = len(df_pendentes)
        self.logger.info(f"Enviando {total_pendentes} emails pendentes")
        if on_progress:
            on_progress(f"📧 Enviando {total_pendentes} emails pendentes")

        # Índices reais no df_completo para cada mensagem pendente
        indices_reais: list[int] = df_pendentes.index.tolist()

        # Construir mensagens
        mensagens: list[EmailMessage] = []
        for _, row in df_pendentes.iterrows():
            attachments = self._resolver_caminhos_attachments(row.get("attachments"))
            mensagens.append(
                EmailMessage(
                    to=[row["email"]],
                    subject=row["subject"],
                    html_body=row["html_body"],
                    attachments=attachments,
                    bcc=[],
                )
            )

        # Enviar — repo.guardar() é chamado pelo send_batch após cada lote e no finally
        resultado = self.email_sender.send_batch(
            mensagens=mensagens,
            repo=self.envio_faturas_repo,   # ← repositório gere a gravação
            df=df_completo,
            df_indices=indices_reais,
            coluna_data_envio="data_envio",
            coluna_status="status_envio",
            coluna_erro="erro_envio",
            tamanho_lote=25,
            max_por_conexao=40,
            pausa_entre_lotes=(60, 120),
            delay_envio=(3, 6),
            modulo_log="secretaria_faturas",
            on_progress=on_progress,
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

    # --------------------------------------------------
    # Helpers privados
    # --------------------------------------------------

    def _resolver_caminhos_attachments(self, attachments_value) -> list[Path]:
        nomes = self._parse_attachments(attachments_value)
        caminhos = []
        for nome in nomes:
            p = Path(nome)
            caminhos.append(p if p.is_absolute() else self.ctx.pim_mensal_dir / p)
        return caminhos

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
        nomes = self._parse_attachments(value)
        result = []
        for nome in nomes:
            try:
                result.append(Path(nome).name)
            except Exception:
                result.append(str(nome))
        return result

    def _definir_tipo_texto(self, row) -> str:
        especial = str(row.get("especial", "") or "").strip()
        if especial == "DD":
            return "DD"

        anterior = row.get("anterior")
        try:
            anterior = float(anterior) if anterior is not None else 0.0
        except (ValueError, TypeError):
            anterior = 0.0

        return "TBsemdivida" if anterior == 0.0 else "TBcomdivida"
