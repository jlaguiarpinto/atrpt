# presentation/secretaria/ponto_controller.py

import logging
import threading
from core.month_context import build_month_context
from infrastructure.persistence.ponto_repository import PontoRepository

logger = logging.getLogger(__name__)


class PontoController:

    def __init__(self, root, cfg, usecase):
        self.root    = root
        self.cfg     = cfg
        self.usecase = usecase
        self.gui     = None
        self.ctx     = None
        self.repo    = None

    def start(self, gui_host):
        from presentation.secretaria.ponto_gui import PontoGUI
        self.gui = gui_host
        gui_host.show_view(PontoGUI, self)

    # ── processar ponto ───────────────────────────────────────────────────────
    def processar(self):
        mes = self.gui.perguntaMes()
        if not mes:
            return

        self.ctx  = build_month_context(self.cfg, "ponto", mes)
        self.repo = PontoRepository(
            pasta_mes        = self.ctx.paths["pasta_mes"],
            ficheiro_resumo  = self.ctx.paths["ficheiro_resumo"],
        )
        logger.info(f"Processar ponto — mes {mes}, pasta: {self.ctx.paths['pasta_mes']}")

        def job():
            try:
                total, output = self.usecase.executar(
                    repo        = self.repo,
                    ctx         = self.ctx,
                    on_progress = self._log,
                )
                logger.info(f"\n✔ {total} ficheiros processados")
                if output:
                    self._log(f"Output: {output}")
            except Exception as e:
                logger.error(f"Erro no processamento de ponto: {e}", exc_info=True)
                self._log(f"Erro: {e}")

        threading.Thread(target=job, daemon=True).start()

    # ── rever resumo ──────────────────────────────────────────────────────────
    def rever_resumo(self):
        import pandas as pd

        mes = self.gui.perguntaMes()
        if not mes:
            return

        self.ctx  = build_month_context(self.cfg, "ponto", mes)
        self.repo = PontoRepository(
            pasta_mes        = self.ctx.paths["pasta_mes"],
            ficheiro_resumo  = self.ctx.paths["ficheiro_resumo"],
        )

        df = self.repo.ler_mensal()
        if df is None or df.empty:
            self.gui.informuser(
                "Sem dados",
                f"Nao existe resumo mensal para {mes}.\n"
                "Processe primeiro o ponto do mes.",
                "warning",
            )
            return

        for col in ["numero", "nome", "data"]:
            if col not in df.columns:
                df[col] = ""

        meses_pt = ["", "Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
                    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        try:
            ano = int(str(mes)[:4])
            m   = int(str(mes)[4:])
            mes_label = f"{meses_pt[m]} {ano}"
        except Exception:
            mes_label = str(mes)

        def _on_save(df_editado):
            self.repo.guardar_mensal(df_editado)
            self._log(f"Resumo {mes_label} gravado apos edicao manual.")

        from presentation.secretaria.ponto_resumo_mensal_view import ResumoMensalView
        ResumoMensalView(
            parent    = self.root,
            df        = df,
            on_save   = _on_save,
            mes_label = mes_label,
        )

    # ── helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg):
        logger.info(msg)
        if self.gui:
            self.root.after(0, lambda m=msg: self.gui.log(m))
