# atrpt/application/email/email_sender.py
#
# Responsabilidade: orquestração do envio.
#
# _preparar()    — modo teste, BCC automático, assinatura (comum a ambos)
# _guardar_log() — log JSON incremental por sessão (após cada lote e no finally)
#
# send_one()     — uso independente (poucos emails)
#                  gere a própria ligação (connect/disconnect)
#                  chama _preparar() → emailer.build_mime() → smtp.send()
#
# send_batch()   — uso em massa
#                  gere ligação por lote, reconexão por volume, delays, pausas
#                  chama _preparar() → emailer.build_mime() → smtp.send()
#                  chama repo.guardar(df) após cada lote e no finally
#                  NÃO chama send_one()

import json
import random
import time
from datetime import datetime
from pathlib import Path
from typing import Callable, List, Dict

from .email_message import EmailMessage
import logging

from infrastructure.system.power_management import PowerManagement


class EmailSender:

    def __init__(
        self,
        emailer,
        *,
        modo_teste: bool = False,
        email_teste: str | None = None,
        assinatura_html: str | None = None,
        assinatura_imagem: Path | None = None,
        log_dir: Path | None = None,
        logger=None,
    ):
        self.emailer           = emailer
        self.smtp              = emailer.smtp
        self.modo_teste        = modo_teste
        self.email_teste       = email_teste
        self.assinatura_html   = assinatura_html
        self.assinatura_imagem = assinatura_imagem
        self.log_dir           = Path(log_dir) if log_dir else None
        self.logger            = logger or logging.getLogger(__name__)

        if self.modo_teste and not self.email_teste:
            raise ValueError("modo_teste exige email_teste")

    # --------------------------------------------------
    # Preparação — comum a send_one e send_batch
    # --------------------------------------------------

    def _preparar(self, message: EmailMessage) -> tuple[EmailMessage, list[str]]:
        """
        Aplica modo teste, BCC automático e assinatura.
        Devolve (EmailMessage pronto, destinatarios_originais).
        """
        msg = EmailMessage(
            to=list(message.to),
            subject=message.subject,
            html_body=message.html_body,
            attachments=list(message.attachments or []),
            inline_images=dict(message.inline_images or {}),
            bcc=list(message.bcc or []),
        )

        destino_original = list(msg.to)

        if self.modo_teste:
            msg.to      = [self.email_teste]
            msg.bcc     = []
            msg.subject = f"[TESTE] {msg.subject}"
        else:
            email_from = getattr(self.emailer, "email_from", None)
            if email_from and email_from not in msg.bcc:
                msg.bcc.append(email_from)

        if self.assinatura_html:
            msg.html_body += "<br><br>" + self.assinatura_html

        if self.assinatura_imagem:
            msg.inline_images["assinatura_img"] = self.assinatura_imagem

        return msg, destino_original

    # --------------------------------------------------
    # Gravação repositório — após cada lote e no finally
    # --------------------------------------------------

    def _guardar_repo(
        self,
        repo,
        df,
        contexto: str = "",
        on_progress: Callable | None = None,
    ):
        """
        Chama repo.guardar(df) de forma segura.
        Contexto usado apenas na mensagem de progresso ("lote 2", "final", etc.).
        """
        if repo is None or df is None:
            return
        try:
            repo.guardar(df)
            msg = f"💾 Guardado ({contexto})" if contexto else "💾 Guardado"
            self.logger.info(msg)
            if on_progress:
                on_progress(msg)
        except PermissionError:
            self.logger.warning("Ficheiro aberto por outra aplicação — não foi possível guardar")
        except Exception as exc:
            self.logger.error(f"Erro ao guardar: {exc}")

    # --------------------------------------------------
    # Gravação log JSON — após cada lote e no finally
    # --------------------------------------------------

    def _guardar_log(
        self,
        resultados: list[dict],
        stats: dict,
        modulo: str = "email",
        on_progress: Callable | None = None,
    ):
        """
        Grava log JSON incremental em self.log_dir.
        Ficheiro único por sessão: <modulo>_YYYYMMDD_HHMMSS.json
        Cada chamada acrescenta os resultados do lote ao mesmo ficheiro.
        """
        if not self.log_dir or not resultados:
            return

        self.log_dir.mkdir(parents=True, exist_ok=True)

        # Ficheiro único por sessão
        if not hasattr(self, "_log_ficheiro_sessao"):
            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            self._log_ficheiro_sessao = self.log_dir / f"{modulo}_{ts}.json"
            dados = {"modulo": modulo, "sessao": ts, "envios": [], "stats": {}}
        else:
            try:
                with open(self._log_ficheiro_sessao, encoding="utf-8") as f:
                    dados = json.load(f)
            except Exception:
                dados = {"modulo": modulo, "envios": [], "stats": {}}

        for r in resultados:
            entrada = dict(r)
            if isinstance(entrada.get("data_hora"), datetime):
                entrada["data_hora"] = entrada["data_hora"].isoformat()
            if isinstance(entrada.get("destinatarios"), list):
                entrada["destinatarios"] = ", ".join(entrada["destinatarios"])
            dados["envios"].append(entrada)

        dados["stats"] = stats
        dados["ultima_actualizacao"] = datetime.now().isoformat()

        try:
            with open(self._log_ficheiro_sessao, "w", encoding="utf-8") as f:
                json.dump(dados, f, indent=2, ensure_ascii=False, default=str)
            msg = f"📋 Log: {self._log_ficheiro_sessao.name}"
            self.logger.info(msg)
            if on_progress:
                on_progress(msg)
        except Exception as exc:
            self.logger.error(f"Erro ao guardar log: {exc}")

    # --------------------------------------------------
    # Envio individual — uso independente
    # --------------------------------------------------

    def send_one(
        self,
        message: EmailMessage,
        *,
        ask_confirm=None,
        on_progress: Callable | None = None,
        idx: int | None = None,
        total: int | None = None,
    ) -> tuple[str, list[str]]:
        """
        Envia um único email gerindo a sua própria ligação.

        Devolve (status, destinatarios_originais).
        status ∈ {"OK", "SKIPPED", "ERRO: <mensagem>"}
        """
        msg, destino_original = self._preparar(message)
        dest_str = ", ".join(destino_original)

        if self.modo_teste and ask_confirm:
            prefixo = f"[{idx}/{total}] " if idx is not None else ""
            if not ask_confirm(f"{prefixo}Enviar para {dest_str}?"):
                return "SKIPPED", destino_original

        self.smtp.connect()
        try:
            mime, recipients = self.emailer.build_mime(msg)
            self.smtp.send(mime, recipients)
            status = "OK"
        except Exception as exc:
            status = f"ERRO: {exc}"
        finally:
            self.smtp.disconnect()

        if on_progress:
            prefixo = f"[{idx}/{total}] " if idx is not None and total is not None else ""
            on_progress(f"{prefixo}{status} → {dest_str}")

        return status, destino_original

    # --------------------------------------------------
    # Envio em lote — uso em massa
    # --------------------------------------------------

    def send_batch(
        self,
        *,
        mensagens: List[EmailMessage],
        repo=None,
        df=None,
        df_indices: list | None = None,
        idx_inicio: int = 0,
        coluna_data_envio: str = "data_envio",
        coluna_status: str = "status_envio",
        coluna_erro: str = "erro_envio",
        tamanho_lote: int = 50,
        max_por_conexao: int = 40,
        pausa_entre_lotes: tuple = (80, 200),
        delay_envio: tuple = (3, 9),
        modulo_log: str = "email",
        on_progress: Callable[[str], None] | None = None,
        on_lote_concluido: Callable[[int, int], bool] | None = None,
    ) -> Dict:
        """
        Envia emails em lotes: _preparar() → build_mime() → smtp.send()

        Gravação garantida via repo.guardar(df):
          - após cada lote concluído
          - no finally (cobre interrupções e erros)

        df_indices : índices reais do df para cada mensagem.
                     Se None, assume correspondência 0..N.
        """
        total = len(mensagens)
        resultados: list[dict] = []
        resultados_lote_atual: list[dict] = []
        stats = {"ok": 0, "erro": 0, "interrompido": False}

        # Garantir colunas no df
        if df is not None:
            for col in [coluna_data_envio, coluna_status, coluna_erro]:
                if col not in df.columns:
                    df[col] = None if col == coluna_data_envio else ""

        indices_df = df_indices if df_indices is not None else list(range(total))

        if on_progress:
            on_progress(f"🚀 Iniciando envio de {total} emails")

        lotes = [
            (i, mensagens[i: i + tamanho_lote])
            for i in range(idx_inicio, total, tamanho_lote)
        ]
        total_lotes = len(lotes)

        power_mgmt = PowerManagement()
        power_mgmt.prevent_sleep()

        try:
            for lote_num, (offset_lote, lote) in enumerate(lotes, start=1):

                # Interrupção controlada entre lotes
                if on_lote_concluido and lote_num > 1:
                    if not on_lote_concluido(lote_num - 1, total_lotes):
                        self.logger.info(f"Envio interrompido após lote {lote_num - 1}")
                        if on_progress:
                            on_progress(f"⏸️ Envio interrompido após lote {lote_num - 1}")
                        stats["interrompido"] = True
                        break

                self.logger.info(f"LOTE {lote_num}/{total_lotes} — {len(lote)} emails")
                if on_progress:
                    on_progress(f"\n📦 LOTE {lote_num}/{total_lotes} — {len(lote)} emails")

                resultados_lote_atual = []

                self.smtp.connect()
                self.logger.info(f"SMTP conectado para lote {lote_num}")

                try:
                    for idx_rel, msg in enumerate(lote):
                        idx_lista = offset_lote + idx_rel
                        idx_df    = indices_df[idx_lista]
                        data_hora = None
                        erro      = ""
                        dest_str  = ", ".join(msg.to)

                        # Reconexão por volume a meio do lote
                        if self.smtp._sent >= max_por_conexao:
                            self.logger.info(
                                f"max_por_conexao ({max_por_conexao}) atingido — a reconectar"
                            )
                            if on_progress:
                                on_progress(f"🔄 Reconexão SMTP (limite de {max_por_conexao} por sessão)")
                            self.smtp.disconnect()
                            self.smtp.connect()

                        try:
                            msg_pronto, _ = self._preparar(msg)
                            mime, recipients = self.emailer.build_mime(msg_pronto)
                            self.smtp.send(mime, recipients)
                            status    = "OK"
                            data_hora = datetime.now()
                            stats["ok"] += 1
                            self.logger.info(f"[{idx_lista + 1}/{total}] OK → {dest_str}")
                            if on_progress:
                                on_progress(f"[{idx_lista + 1}/{total}] OK → {dest_str}")

                        except Exception as exc:
                            status = "ERRO"
                            erro   = str(exc)
                            stats["erro"] += 1
                            self.logger.exception(f"[{idx_lista + 1}/{total}] ERRO → {dest_str}")
                            if on_progress:
                                on_progress(f"❌ [{idx_lista + 1}/{total}] ERRO: {erro} → {dest_str}")

                        entrada = {
                            "indice_lista":  idx_lista,
                            "indice_df":     idx_df,
                            "destinatarios": msg.to,
                            "assunto":       msg.subject,
                            "status":        status,
                            "erro":          erro,
                            "data_hora":     data_hora,
                        }
                        resultados.append(entrada)
                        resultados_lote_atual.append(entrada)

                        # Actualizar df pelo índice real
                        if df is not None:
                            if data_hora:
                                df.at[idx_df, coluna_data_envio] = data_hora
                            df.at[idx_df, coluna_status] = status
                            df.at[idx_df, coluna_erro]   = erro[:500] if erro else ""

                        time.sleep(random.uniform(*delay_envio))

                finally:
                    self.smtp.disconnect()
                    self.logger.info(f"SMTP desconectado após lote {lote_num}")

                # Guardar após lote
                self._guardar_repo(repo, df, f"lote {lote_num}", on_progress)
                self._guardar_log(resultados_lote_atual, stats, modulo_log, on_progress)

                # Pausa entre lotes
                if lote_num < total_lotes and not stats["interrompido"]:
                    pausa = random.uniform(*pausa_entre_lotes)
                    self.logger.info(f"Pausa de {int(pausa)}s antes do lote {lote_num + 1}")
                    if on_progress:
                        on_progress(f"\n⏸️ Pausa de {int(pausa)}s antes do próximo lote...")
                    time.sleep(pausa)

            # Fim normal
            self.logger.info(f"Envio concluído. OK: {stats['ok']} | ERRO: {stats['erro']}")
            if on_progress:
                on_progress(f"\n✨ Envio concluído.")
                on_progress(f"📊 OK: {stats['ok']} | ERRO: {stats['erro']}")

        finally:
            # Gravação de segurança — cobre interrupções, erros e fim normal
            self._guardar_repo(repo, df, "final", on_progress)
            self._guardar_log(resultados_lote_atual, stats, modulo_log, on_progress)
            power_mgmt.allow_sleep()

        return {
            "resultados":    resultados,
            "stats":         stats,
            "total":         total,
            "processados":   len(resultados),
            "ultimo_indice": resultados[-1]["indice_lista"] if resultados else idx_inicio - 1,
        }
