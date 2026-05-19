# presentation/ponto/ponto_resumo_empregado_view.py
"""
Resumo de ponto por empregado.

Painel superior : lista de empregados com totais mensais.
Painel inferior : registo diário do empregado seleccionado.
"""

import tkinter as tk
from tkinter import ttk
import pandas as pd
from presentation.shared.base_gui import BaseGui as _BG

BG          = _BG.BG
FG          = _BG.FG
BTN_BG      = _BG.BTN_BG
FONT_BUTTON = _BG.FONT_BUTTON
FONT_TITLE  = _BG.FONT_TITLE
FONT_UI     = _BG.FONT_SUB
FONT_MONO   = ("Courier New", 9)
BG_HEADER   = "#b8cccb"
BG_FOOTER   = "#d4e8d4"
BG_TREE     = "#ffffff"
SEL_BG      = "#a8c4c0"
SAB_BG      = "#e8e8e8"
DOM_BG      = "#f5dce0"
FER_FG      = "#8b0000"
ERR_FG      = "#cc4400"

# ── colunas do painel superior (resumo por empregado) ─────────────────────────
_COLS_EMP = [
    ("numero",            "Nº",          42,  "center"),
    ("nome",              "Nome",        220, "w"),
    ("tipo",              "Tipo",         80, "w"),
    ("presenca",          "Presença",     64, "e"),
    ("falta",             "Faltas",       46, "e"),
    ("noturno",           "Noturno",      64, "e"),
    ("baixa",             "Baixas",       46, "e"),
    ("ferias",            "Férias",       46, "e"),
    ("feriado",           "Fer.(h)",      52, "e"),
    ("subsidio_refeicao", "S.Ref.",       46, "e"),
    ("hext50",            "HExt50",       58, "e"),
    ("hext75",            "HExt75",       58, "e"),
    ("hext100",           "HExt100",      62, "e"),
]
_TOTAIS_EMP = {"presenca", "falta", "noturno", "baixa", "ferias",
               "feriado", "subsidio_refeicao", "hext50", "hext75", "hext100"}

# ── colunas do painel inferior (detalhe diário) ───────────────────────────────
_COLS_DET = [
    ("data",              "Data",         82, "w"),
    ("dia_semana",        "Dia",          68, "w"),
    ("e1",                "E1",           52, "center"),
    ("s1",                "S1",           52, "center"),
    ("e2",                "E2",           52, "center"),
    ("s2",                "S2",           52, "center"),
    ("presenca",          "Presença",     64, "e"),
    ("falta",             "Falta",        46, "e"),
    ("noturno",           "Noturno",      64, "e"),
    ("baixa",             "Baixa",        46, "e"),
    ("ferias",            "Férias",       46, "e"),
    ("feriado",           "Fer.(h)",      52, "e"),
    ("subsidio_refeicao", "S.Ref.",       46, "e"),
    ("hext50",            "HExt50",       58, "e"),
    ("hext75",            "HExt75",       58, "e"),
    ("hext100",           "HExt100",      62, "e"),
    ("erros_picagem",     "Erros",       148, "w"),
    ("observ",            "Observ.",     160, "w"),
    ("feriado_desc",      "Feriado",      60, "w"),
]
_NUM_DET = {"presenca", "falta", "noturno", "baixa", "ferias", "feriado",
            "subsidio_refeicao", "hext50", "hext75", "hext100"}


class ResumoEmpregadoView(tk.Toplevel):

    def __init__(self, parent, df: pd.DataFrame, mes_label: str = ""):
        super().__init__(parent)
        self.title(f"Resumo por empregado — {mes_label}")
        self.configure(bg=BG)
        self.state("zoomed")
        self.resizable(True, True)

        self._mes_label   = mes_label
        self._df          = df.copy()
        self._filtro      = "Todos"
        self._resumos:    list[dict] = []

        self._garantir_colunas()
        self._build()
        self._popular_empregados()
        self.grab_set()

    # ── prep ──────────────────────────────────────────────────────────────────

    def _garantir_colunas(self):
        for col in ("tipo", "categoria", "ativo_rh", "grupo",
                    "observ", "erros_picagem", "feriado_desc",
                    "hext50", "hext75", "hext100"):
            if col not in self._df.columns:
                self._df[col] = "" if col not in ("hext50", "hext75", "hext100") else 0.0

    @staticmethod
    def _inferir_grupo(num_str: str) -> str:
        try:
            return "Enfermeiro" if int(str(num_str).strip()) >= 500 else "AAD"
        except (ValueError, TypeError):
            return "AAD"

    def _calcular_resumos(self) -> list[dict]:
        df = self._df[self._df["data"].astype(str) != "TOTAL"].copy()
        if df.empty:
            return []

        if "grupo" not in df.columns or df["grupo"].astype(str).str.strip().eq("").all():
            df["grupo"] = df["numero"].astype(str).apply(self._inferir_grupo)
        else:
            vazio = df["grupo"].astype(str).str.strip() == ""
            df.loc[vazio, "grupo"] = df.loc[vazio, "numero"].astype(str).apply(
                self._inferir_grupo)

        filtro = self._filtro
        if filtro != "Todos":
            df = df[df["grupo"].astype(str) == filtro]

        resultados = []
        for (numero, nome), grp in df.groupby(["numero", "nome"], sort=True):
            tipo = str(grp["tipo"].iloc[0] if "tipo" in grp.columns else "").strip() or \
                   str(grp["grupo"].iloc[0]).strip()
            rec = {"numero": numero, "nome": nome, "tipo": tipo}
            for col in _TOTAIS_EMP:
                if col in grp.columns:
                    rec[col] = round(
                        float(pd.to_numeric(grp[col], errors="coerce").fillna(0).sum()), 2)
                else:
                    rec[col] = 0.0
            resultados.append(rec)
        return resultados

    # ── layout ────────────────────────────────────────────────────────────────

    def _build(self):
        topo = tk.Frame(self, bg=BG_HEADER, pady=6)
        topo.pack(fill="x")
        tk.Label(topo, text=f"Resumo por empregado — {self._mes_label}",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG).pack(side="left", padx=16)
        tk.Button(topo, text="Fechar", command=self.destroy,
                  font=FONT_UI, bg=BTN_BG, fg=FG,
                  relief="raised", padx=10, pady=2).pack(side="right", padx=12)

        # ── barra de filtro ───────────────────────────────────────────────────
        fbar = tk.Frame(self, bg=BG_HEADER, pady=4, relief="groove", bd=1)
        fbar.pack(fill="x")
        tk.Label(fbar, text="Mostrar:", font=FONT_UI, bg=BG_HEADER, fg=FG
                 ).pack(side="left", padx=(14, 8))
        self._filtro_btns = {}
        _cores = {"Todos": "#c8dedd", "AAD": "#c8e8c8", "Enfermeiro": "#c8d0e8"}
        for f in ("Todos", "AAD", "Enfermeiro"):
            btn = tk.Button(
                fbar, text=f, font=FONT_UI,
                bg=_cores[f], fg=FG,
                relief="sunken" if f == "Todos" else "raised",
                padx=14, pady=2,
                command=lambda ff=f: self._aplicar_filtro(ff),
            )
            btn.pack(side="left", padx=3)
            self._filtro_btns[f] = btn
        self._lbl_cont = tk.Label(fbar, text="", font=FONT_UI, bg=BG_HEADER, fg=FG)
        self._lbl_cont.pack(side="left", padx=12)

        # ── PanedWindow vertical ──────────────────────────────────────────────
        pw = ttk.PanedWindow(self, orient="vertical")
        pw.pack(fill="both", expand=True, padx=6, pady=4)

        # painel superior — lista de empregados
        top = tk.Frame(pw, bg=BG)
        pw.add(top, weight=1)
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)
        self._tree_emp = self._criar_treeview(top, _COLS_EMP)
        self._tree_emp.bind("<<TreeviewSelect>>", self._on_selecionar)
        self._style_tree(self._tree_emp, "EMP")

        # painel inferior — detalhe diário
        bot = tk.Frame(pw, bg=BG)
        pw.add(bot, weight=2)
        bot.rowconfigure(1, weight=1)
        bot.columnconfigure(0, weight=1)

        self._lbl_detalhe = tk.Label(
            bot, text="Seleccione um empregado para ver o registo mensal.",
            bg=BG, fg="gray", font=FONT_UI, anchor="w",
        )
        self._lbl_detalhe.grid(row=0, column=0, columnspan=2,
                                sticky="ew", padx=4, pady=(4, 2))
        self._tree_det = self._criar_treeview(bot, _COLS_DET, row=1)
        self._style_tree(self._tree_det, "DET")

        # rodapé de totais
        self._lbl_totais = tk.Label(
            bot, text="", bg=BG_FOOTER, fg=FG,
            font=FONT_UI, anchor="e", relief="groove",
        )
        self._lbl_totais.grid(row=2, column=0, columnspan=2,
                               sticky="ew", padx=0, pady=(2, 0))

    def _criar_treeview(self, parent, cols, row=0) -> ttk.Treeview:
        tree = ttk.Treeview(parent, columns=[c[0] for c in cols],
                            show="headings", selectmode="browse")
        for col_id, lbl, w, anchor in cols:
            tree.heading(col_id, text=lbl)
            tree.column(col_id, width=w, minwidth=28, anchor=anchor, stretch=False)

        vsb = ttk.Scrollbar(parent, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(parent, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        tree.grid(row=row, column=0, sticky="nsew")
        vsb.grid(row=row, column=1, sticky="ns")
        hsb.grid(row=row + 1, column=0, sticky="ew")
        return tree

    def _style_tree(self, tree: ttk.Treeview, tag: str):
        s = ttk.Style()
        s.configure(f"{tag}.Treeview",
                    background=BG_TREE, foreground="black",
                    fieldbackground=BG_TREE, rowheight=22,
                    font=FONT_MONO, borderwidth=0)
        s.configure(f"{tag}.Treeview.Heading",
                    background=BG_HEADER, foreground=FG,
                    font=FONT_UI, relief="groove")
        s.map(f"{tag}.Treeview",
              background=[("selected", SEL_BG)],
              foreground=[("selected", "black")])
        tree.configure(style=f"{tag}.Treeview")
        tree.tag_configure("sabado",  background=SAB_BG)
        tree.tag_configure("domingo", background=DOM_BG)
        tree.tag_configure("feriado", foreground=FER_FG)
        tree.tag_configure("erro",    foreground=ERR_FG, background="#fff0e8")

    # ── dados ─────────────────────────────────────────────────────────────────

    def _aplicar_filtro(self, filtro: str):
        self._filtro = filtro
        for nome, btn in self._filtro_btns.items():
            btn.config(relief="sunken" if nome == filtro else "raised")
        self._popular_empregados()

    def _popular_empregados(self):
        self._resumos = self._calcular_resumos()
        self._tree_emp.delete(*self._tree_emp.get_children())
        n = len(self._resumos)
        self._lbl_cont.config(text=f"{n} {'empregado' if n == 1 else 'empregados'}")

        for r in self._resumos:
            vals = []
            for col_id, *_ in _COLS_EMP:
                v = r.get(col_id, "")
                if col_id in _TOTAIS_EMP:
                    try:
                        f = float(v)
                        if col_id in {"presenca", "noturno", "feriado",
                                      "hext50", "hext75", "hext100"}:
                            v = f"{f:.2f}" if f else "—"
                        else:
                            v = str(int(f)) if f else "—"
                    except (ValueError, TypeError):
                        v = str(v)
                vals.append(str(v))
            self._tree_emp.insert("", "end",
                                  iid=f"{r['numero']}||{r['nome']}",
                                  values=vals)

        # limpar detalhe
        self._tree_det.delete(*self._tree_det.get_children())
        self._lbl_detalhe.config(
            text="Seleccione um empregado para ver o registo mensal.",
            fg="gray")
        self._lbl_totais.config(text="")

    def _on_selecionar(self, _event=None):
        sel = self._tree_emp.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            numero, nome = iid.split("||", 1)
        except ValueError:
            return
        self._mostrar_detalhe(numero, nome)

    def _mostrar_detalhe(self, numero: str, nome: str):
        self._lbl_detalhe.config(
            text=f"Registo mensal:  {numero} — {nome}", fg=FG)

        df = self._df
        mask = (
            (df["data"].astype(str) != "TOTAL") &
            (df["numero"].astype(str) == str(numero)) &
            (df["nome"].astype(str)   == str(nome))
        )
        linhas = df[mask].copy()

        self._tree_det.delete(*self._tree_det.get_children())

        tot_presenca = tot_noturno = 0.0
        n_dias = 0

        for _, row in linhas.iterrows():
            vals = []
            for col_id, *_ in _COLS_DET:
                v = row.get(col_id, "")
                if pd.isna(v) or v is None:
                    v = ""
                elif col_id in _NUM_DET:
                    try:
                        f = float(v)
                        if col_id in {"presenca", "noturno", "feriado",
                                      "hext50", "hext75", "hext100"}:
                            v = f"{f:.2f}" if f else ""
                        else:
                            v = str(int(f)) if f else ""
                    except (ValueError, TypeError):
                        v = str(v)
                else:
                    v = str(v)
                vals.append(v)

            tags = self._tags_linha(row)
            self._tree_det.insert("", "end", values=vals, tags=tags)

            try:
                tot_presenca += float(row.get("presenca") or 0)
                tot_noturno  += float(row.get("noturno") or 0)
                n_dias       += 1
            except (ValueError, TypeError):
                pass

        # rodapé de totais do detalhe
        res = next((r for r in self._resumos
                    if str(r["numero"]) == str(numero) and r["nome"] == nome), {})
        partes = []
        for col, lbl in [
            ("presenca",  "Presença"),
            ("falta",     "Faltas"),
            ("noturno",   "Noturno"),
            ("baixa",     "Baixas"),
            ("ferias",    "Férias"),
            ("hext50",    "HExt50"),
            ("hext75",    "HExt75"),
            ("hext100",   "HExt100"),
        ]:
            v = res.get(col, 0.0)
            if v:
                if col in {"presenca", "noturno", "hext50", "hext75", "hext100"}:
                    partes.append(f"{lbl}: {v:.2f} h")
                else:
                    partes.append(f"{lbl}: {int(v)}")
        self._lbl_totais.config(
            text="   ".join(partes) if partes else "",
            bg=BG_FOOTER,
        )

    @staticmethod
    def _tags_linha(row) -> tuple:
        tags = []
        dia = str(row.get("dia_semana", ""))
        if dia in ("Sabado", "Sábado"):
            tags.append("sabado")
        elif dia == "Domingo":
            tags.append("domingo")
        if str(row.get("feriado_desc", "") or "").strip():
            tags.append("feriado")
        erro = row.get("erros_picagem", "")
        if erro and str(erro).strip():
            tags.append("erro")
        return tuple(tags)
