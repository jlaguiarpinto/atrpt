# presentation/ponto/ponto_controller.py

import logging
import threading
from core.month_context import build_month_context
from infrastructure.persistence.ponto.ponto_repository import PontoRepository

logger = logging.getLogger(__name__)


class PontoController:

    def __init__(self, root, cfg, usecase, user_context=None,
                 pessoas_repo=None, fornecedor_repo=None, mapa_repo=None,
                 ausencia_repo=None):
        self.root            = root
        self.cfg             = cfg
        self.usecase         = usecase
        self.user            = user_context
        self.pessoas_repo    = pessoas_repo      # EmpregadoRepository
        self.fornecedor_repo = fornecedor_repo   # FornecedorRepositorySQL
        self.mapa_repo       = mapa_repo         # PontoMapaRepository
        self.ausencia_repo   = ausencia_repo     # AusenciaPontoRepository
        self.gui     = None
        self.ctx     = None
        self.repo    = None

    def start(self, gui_host):
        from presentation.ponto.ponto_gui import PontoGUI
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

        # carregar ausências para o mês em processamento
        ausencias = []
        if self.ausencia_repo:
            try:
                nome_pasta = self.ctx.paths["pasta_mes"].name
                ano_proc   = int(nome_pasta[:4])
                mes_proc   = int(nome_pasta[4:])
                ausencias  = self.ausencia_repo.listar_por_mes(ano_proc, mes_proc)
                if ausencias:
                    self._log(f"📋 {len(ausencias)} ausências conhecidas carregadas")
            except Exception as ex:
                logger.warning(f"Nao foi possivel carregar ausencias: {ex}")

        def job():
            try:
                total, output = self.usecase.executar(
                    repo        = self.repo,
                    ctx         = self.ctx,
                    on_progress = self._log,
                    ausencias   = ausencias,
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

        # enriquecer com ativo_rh e grupo para filtro AAD/Enfermeiro funcionar
        df = self._enriquecer_com_pessoas(df)

        # capturar repo no closure para evitar que seja substituído por outra operação
        _repo_closure = self.repo

        def _on_save(df_editado):
            # remover colunas de enriquecimento antes de gravar
            cols_extra = [c for c in ("ativo_rh", "tipo", "categoria", "grupo")
                          if c in df_editado.columns]
            _repo_closure.guardar_mensal(df_editado.drop(columns=cols_extra, errors="ignore"))
            self._log(f"Resumo {mes_label} gravado apos edicao manual.")

        from presentation.ponto.ponto_resumo_mensal_view import ResumoMensalView
        ResumoMensalView(
            parent    = self.root,
            df        = df,
            on_save   = _on_save,
            mes_label = mes_label,
            username  = getattr(self.user, "username", "") if self.user else "",
        )

    # ── resumo por empregado ─────────────────────────────────────────────────
    def resumo_empregado(self):
        import pandas as pd

        mes = self.gui.perguntaMes()
        if not mes:
            return

        self.ctx  = build_month_context(self.cfg, "ponto", mes)
        self.repo = PontoRepository(
            pasta_mes       = self.ctx.paths["pasta_mes"],
            ficheiro_resumo = self.ctx.paths["ficheiro_resumo"],
        )

        df = self.repo.ler_mensal()
        if df is None or df.empty:
            self.gui.informuser(
                "Sem dados",
                f"Nao existe resumo mensal para {mes}. Processe primeiro o ponto do mes.",
                "warning",
            )
            return

        meses_pt = ["","Janeiro","Fevereiro","Marco","Abril","Maio","Junho",
                    "Julho","Agosto","Setembro","Outubro","Novembro","Dezembro"]
        try:
            ano = int(str(mes)[:4])
            m   = int(str(mes)[4:])
            mes_label = f"{meses_pt[m]} {ano}"
        except Exception:
            mes_label = str(mes)

        df_enriquecido = self._enriquecer_com_pessoas(df)

        from presentation.ponto.ponto_resumo_empregado_view import ResumoEmpregadoView
        ResumoEmpregadoView(parent=self.root, df=df_enriquecido, mes_label=mes_label)

    # ── erros de picagem ─────────────────────────────────────────────────────
    def ver_erros_picagem(self):
        mes = self.gui.perguntaMes()
        if not mes:
            return

        self.ctx  = build_month_context(self.cfg, "ponto", mes)
        self.repo = PontoRepository(
            pasta_mes       = self.ctx.paths["pasta_mes"],
            ficheiro_resumo = self.ctx.paths["ficheiro_resumo"],
        )

        df = self.repo.ler_mensal()
        if df is None or df.empty:
            self.gui.informuser(
                "Sem dados",
                f"Nao existe resumo mensal para {mes}. Processe primeiro o ponto do mes.",
                "warning",
            )
            return

        if "erros_picagem" not in df.columns:
            self.gui.informuser(
                "Sem erros",
                "O resumo mensal nao tem coluna de erros de picagem.",
                "info",
            )
            return

        meses_pt = ["", "Janeiro", "Fevereiro", "Marco", "Abril", "Maio", "Junho",
                    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
        try:
            ano = int(str(mes)[:4])
            m   = int(str(mes)[4:])
            mes_label = f"{meses_pt[m]} {ano}"
        except Exception:
            mes_label = str(mes)

        from presentation.ponto.ponto_erros_picagem_view import ErrosPicagemView
        ErrosPicagemView(parent=self.root, df=df, mes_label=mes_label)

    # ── cruzamento com pessoas / fornecedores ────────────────────────────────
    def _enriquecer_com_pessoas(self, df: "pd.DataFrame") -> "pd.DataFrame":
        """
        Acrescenta ao df as colunas:
          categoria  — categoria profissional (da BD de pessoas)
          ativo_rh   — "Sim"/"Nao" (da BD de pessoas)
          tipo       — "Empregado" | "Enfermeiro" | "Desconhecido"

        Cruzamento por número (parte antes de ' - ' no campo nome original,
        ou campo numero se já splitado).
        Quem não for encontrado em pessoas é cruzado com fornecedores
        pelo nome para identificar enfermeiros.
        """
        import pandas as pd

        df = df.copy()
        df["categoria"] = ""
        df["ativo_rh"]  = ""
        df["tipo"]      = "Desconhecido"

        # -- mapas da BD de pessoas -----------------------------------
        mapa_emp_num  = {}   # numero_str → Empregado
        mapa_emp_nome = {}   # nome_upper → Empregado  (fallback)
        if self.pessoas_repo is not None:
            try:
                empregados = self.pessoas_repo.list_all(apenas_ativos=False)
                for e in empregados:
                    mapa_emp_num[str(e.numero).strip()] = e
                    mapa_emp_nome[e.nome.strip().upper()] = e
            except Exception as ex:
                logger.warning(f"Nao foi possivel aceder a BD de pessoas: {ex}")

        # -- mapa nome_upper → fornecedor (apenas Enfermeiros) ------
        mapa_forn = {}
        if self.fornecedor_repo is not None:
            try:
                for f in self.fornecedor_repo.list_by("atividade", "Enfermeiro"):
                    mapa_forn[f.nome.strip().upper()] = f
            except Exception as ex:
                logger.warning(f"Nao foi possivel aceder a BD de fornecedores: {ex}")

        # -- garantir split numero/nome no df de entrada -------------
        # o Excel pode ter sido gravado antes do split estar no pipeline
        if "numero" not in df.columns:
            split = df["nome"].astype(str).str.split(r" - ", n=1, expand=True)
            if split.shape[1] == 2:
                df.insert(df.columns.get_loc("nome"), "numero", split[0].str.strip())
                df["nome"] = split[1].str.strip()
            else:
                df.insert(df.columns.get_loc("nome"), "numero", "")

        # -- cruzamento linha a linha --------------------------------
        nomes_nao_resolvidos = []

        for idx, row in df.iterrows():
            if str(row.get("data", "")) == "TOTAL":
                continue

            num  = str(row.get("numero", "")).strip()
            nome = str(row.get("nome",   "")).strip().upper()

            # 1ª tentativa — por número na BD pessoas
            e = mapa_emp_num.get(num)

            # 2ª tentativa — por nome na BD pessoas
            if e is None:
                e = mapa_emp_nome.get(nome)

            if e is not None:
                df.at[idx, "categoria"] = e.categoria_atual or ""
                df.at[idx, "ativo_rh"]  = "Sim" if e.ativo_bool else "Nao"
                df.at[idx, "tipo"]      = "Empregado"
                continue

            # 3ª tentativa — por nome na BD fornecedores
            if nome in mapa_forn:
                f       = mapa_forn[nome]
                tipo_f  = str(getattr(f, "atividade", "") or "").strip() or "Fornecedor"
                ativo_f = str(getattr(f, "tipo_relacao",    "") or "").lower()
                df.at[idx, "ativo_rh"]  = "Nao" if ativo_f == "suspenso" else "Sim"
                df.at[idx, "tipo"]      = tipo_f
                df.at[idx, "categoria"] = tipo_f
            else:
                nomes_nao_resolvidos.append((num, nome))

        # -- para os ainda não resolvidos: consultar mapa guardado ---
        verdadeiramente_nao_resolvidos = []
        for num, nome in sorted(set(nomes_nao_resolvidos)):
            fid = self.mapa_repo.get(num, nome) if self.mapa_repo else None
            if fid is not None and self.fornecedor_repo is not None:
                try:
                    f = self.fornecedor_repo.get_by_id(fid)
                    if f:
                        tipo_f  = str(getattr(f, "atividade", "") or "").strip() or "Enfermeiro"
                        ativo_f = str(getattr(f, "tipo_relacao",    "") or "").lower()
                        mask = (
                            df["numero"].astype(str).str.strip() == num
                        ) & (
                            df["nome"].astype(str).str.strip().str.upper() == nome
                        )
                        df.loc[mask, "ativo_rh"]  = "Nao" if ativo_f == "suspenso" else "Sim"
                        df.loc[mask, "tipo"]      = tipo_f
                        df.loc[mask, "categoria"] = tipo_f
                        continue
                except Exception:
                    pass
            verdadeiramente_nao_resolvidos.append((num, nome))
            logger.warning(f"Ponto — nao resolvido: '{num} - {nome}'")

        # pessoas não resolvidas — só logging, sem diálogo
        if verdadeiramente_nao_resolvidos:
            logger.info(
                f"Ponto — {len(verdadeiramente_nao_resolvidos)} pessoa(s) "
                f"nao resolvidas (nao encontradas em pessoas nem em fornecedores): "
                + ", ".join(f"{n} - {nm}" for n, nm in verdadeiramente_nao_resolvidos)
            )

        return df

    # ── ausências conhecidas ─────────────────────────────────────────────────
    def gerir_ausencias(self):
        from presentation.ponto.ausencias_ponto_gui import AusenciasPontoGUI
        self.gui.show_view(AusenciasPontoGUI, self)

    def listar_empregados_ativos(self):
        if not self.pessoas_repo:
            return []
        return self.pessoas_repo.list_all(apenas_ativos=False)

    def listar_ausencias(self):
        if not self.ausencia_repo:
            return []
        return self.ausencia_repo.listar_todos()

    def guardar_ausencia(self, aus):
        if not self.ausencia_repo:
            raise RuntimeError("Repositório de ausências não configurado.")
        return self.ausencia_repo.guardar(aus)

    def remover_ausencia(self, ausencia_id: int):
        if not self.ausencia_repo:
            raise RuntimeError("Repositório de ausências não configurado.")
        self.ausencia_repo.remover(ausencia_id)

    # ── helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg):
        logger.info(msg)
        if self.gui:
            self.root.after(0, lambda m=msg: self.gui.log(m))
