# presentation/secretaria/ponto_controller.py

import logging
import threading
from core.month_context import build_month_context
from infrastructure.persistence.ponto.ponto_repository import PontoRepository

logger = logging.getLogger(__name__)


class PontoController:

    def __init__(self, root, cfg, usecase, user_context=None,
                 pessoas_repo=None, fornecedor_repo=None, mapa_repo=None):
        self.root           = root
        self.cfg            = cfg
        self.usecase        = usecase
        self.user           = user_context
        self.pessoas_repo   = pessoas_repo      # EmpregadoRepository
        self.fornecedor_repo= fornecedor_repo   # FornecedorRepositorySQL
        self.mapa_repo      = mapa_repo         # PontoMapaRepository
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

        from presentation.secretaria.ponto_resumo_empregado_view import ResumoEmpregadoView
        ResumoEmpregadoView(parent=self.root, df=df_enriquecido, mes_label=mes_label)

    # ── exportar inativos / não resolvidos ───────────────────────────────────
    def exportar_inativos(self):
        import pandas as pd
        from tkinter import filedialog

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
            self.gui.informuser("Sem dados",
                                "Nao existe resumo mensal para este mes.", "warning")
            return

        df_enriquecido = self._enriquecer_com_pessoas(df)

        # filtrar: inativos ou desconhecidos — uma linha por pessoa (numero+nome únicos)
        linhas = df_enriquecido[df_enriquecido["data"].astype(str) != "TOTAL"].copy()
        resultado = (
            linhas[
                (linhas["ativo_rh"] == "Nao") |
                (linhas["tipo"]     == "Desconhecido")
            ]
            .drop_duplicates(subset=["numero", "nome"])
            [["numero", "nome", "tipo", "categoria", "ativo_rh"]]
            .sort_values(["tipo", "nome"])
            .reset_index(drop=True)
        )

        if resultado.empty:
            self.gui.informuser("Sem registos",
                                "Nao existem pessoas inativas ou nao resolvidas.", "info")
            return

        # pedir caminho para guardar
        path = filedialog.asksaveasfilename(
            title="Guardar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=f"ponto_inativos_{mes}.xlsx",
        )
        if not path:
            return

        resultado.columns = ["Numero", "Nome", "Tipo", "Categoria", "Ativo RH"]
        resultado.to_excel(path, index=False)
        self._log(f"Exportado: {path} ({len(resultado)} registos)")
        self.gui.informuser("Exportado",
                            f"{len(resultado)} registos exportados para: {path}")

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
                for f in self.fornecedor_repo.list_by("tipo_fornecedor", "Enfermeiro"):
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
                tipo_f  = str(getattr(f, "tipo_fornecedor", "") or "").strip() or "Fornecedor"
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
                        tipo_f  = str(getattr(f, "tipo_fornecedor", "") or "").strip() or "Enfermeiro"
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

        # -- diálogo de emparelhamento manual para os restantes -------
        if verdadeiramente_nao_resolvidos and self.fornecedor_repo is not None:
            try:
                enfermeiros = self.fornecedor_repo.list_by("tipo_fornecedor", "Enfermeiro")
            except Exception:
                enfermeiros = []

            if enfermeiros:
                def _on_save_mapa(numero, nome, fornecedor_id):
                    if self.mapa_repo:
                        self.mapa_repo.save(numero, nome, fornecedor_id)
                    f = next((x for x in enfermeiros if x.id == fornecedor_id), None)
                    if f:
                        tipo_f  = str(getattr(f, "tipo_fornecedor", "") or "").strip() or "Enfermeiro"
                        ativo_f = str(getattr(f, "tipo_relacao",    "") or "").lower()
                        mask = (
                            df["numero"].astype(str).str.strip() == numero
                        ) & (
                            df["nome"].astype(str).str.strip().str.upper() == nome
                        )
                        df.loc[mask, "ativo_rh"]  = "Nao" if ativo_f == "suspenso" else "Sim"
                        df.loc[mask, "tipo"]      = tipo_f
                        df.loc[mask, "categoria"] = tipo_f

                from presentation.secretaria.ponto_emparelhamento_dialog import EmparelhamentoDialog
                EmparelhamentoDialog(
                    parent          = self.root,
                    nao_resolvidos  = verdadeiramente_nao_resolvidos,
                    enfermeiros     = enfermeiros,
                    on_save         = _on_save_mapa,
                )

        return df

    # ── helpers ───────────────────────────────────────────────────────────────
    def _log(self, msg):
        logger.info(msg)
        if self.gui:
            self.root.after(0, lambda m=msg: self.gui.log(m))
