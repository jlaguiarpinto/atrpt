# presentation/secretaria/ponto_resumo_empregado_view.py
"""
Resumo mensal por empregado com filtro Todos | AAD | Enfermeiro.
AAD:        Dias Trab, Sub.Ref, Faltas, Baixas, Férias, Fer.h, Noturno h, Total h, Média/dia
Enfermeiro: Dias Trab, Diurno h, Noturno h, Dom/Fer h, Total h, Média/dia
"""

import logging
import tkinter as tk
from tkinter import ttk
import pandas as pd

from presentation.shared.base_gui import BaseGui as _BG

logger = logging.getLogger(__name__)

BG        = _BG.BG
FG        = _BG.FG
BTN_BG    = _BG.BTN_BG
FONT_UI   = _BG.FONT_SUB
FONT_BOLD = _BG.FONT_SUB
FONT_TITLE= _BG.FONT_TITLE

BG_HEADER   = "#b8cccb"
BG_TREEVIEW = "#ffffff"
SEL_BG      = "#a8c4c0"
FONT_MONO   = ("Courier New", 9)

# Colunas por modo de visualização
COLUNAS_TODOS = [
    ("numero",      "Num",        60,  "center"),
    ("nome",        "Nome",      260,  "w"),
    ("grupo",       "Grupo",      72,  "center"),
    ("tipo",        "Tipo",       80,  "w"),
    ("ativo_rh",    "Ativo RH",   58,  "center"),
    ("dias_trab",   "Dias",       52,  "e"),
    ("sub_ref",     "Sub.Ref.",   58,  "e"),
    ("faltas",      "Faltas",     48,  "e"),
    ("baixas",      "Baixas",     48,  "e"),
    ("ferias",      "Férias",     48,  "e"),
    ("feriado_h",   "Fer.h",      48,  "e"),
    ("diurno_h",    "Diurno h",   66,  "e"),
    ("noturno_h",   "Noturno h",  70,  "e"),
    ("domingo_h",   "Dom/Fer h",  72,  "e"),
    ("total_horas", "Total h",    66,  "e"),
    ("media_dia",   "Média/dia",  68,  "e"),
]

COLUNAS_AAD = [
    ("numero",      "Num",        60,  "center"),
    ("nome",        "Nome",      280,  "w"),
    ("tipo",        "Tipo",       90,  "w"),
    ("categoria",   "Categoria", 150,  "w"),
    ("ativo_rh",    "Ativo RH",   62,  "center"),
    ("dias_trab",   "Dias Trab.", 66,  "e"),
    ("sub_ref",     "Sub.Ref.",   62,  "e"),
    ("faltas",      "Faltas",     52,  "e"),
    ("baixas",      "Baixas",     52,  "e"),
    ("ferias",      "Férias",     52,  "e"),
    ("feriado_h",   "Fer.h",      52,  "e"),
    ("noturno_h",   "Noturno h",  72,  "e"),
    ("total_horas", "Total h",    66,  "e"),
    ("media_dia",   "Média/dia",  70,  "e"),
]

COLUNAS_ENF = [
    ("numero",      "Num",        60,  "center"),
    ("nome",        "Nome",      300,  "w"),
    ("tipo",        "Tipo",       90,  "w"),
    ("ativo_rh",    "Ativo RH",   62,  "center"),
    ("dias_trab",   "Dias Trab.", 66,  "e"),
    ("diurno_h",    "Diurno h",   70,  "e"),
    ("noturno_h",   "Noturno h",  74,  "e"),
    ("domingo_h",   "Dom/Fer h",  76,  "e"),
    ("total_horas", "Total h",    66,  "e"),
    ("media_dia",   "Média/dia",  70,  "e"),
]

_COLUNAS_MAP = {"Todos": COLUNAS_TODOS, "AAD": COLUNAS_AAD, "Enfermeiro": COLUNAS_ENF}

# Colunas numéricas para ordenação e totais (por modo)
_COLS_NUM = {
    "Todos":     {"dias_trab","sub_ref","faltas","baixas","ferias","feriado_h",
                  "diurno_h","noturno_h","domingo_h","total_horas","media_dia"},
    "AAD":       {"dias_trab","sub_ref","faltas","baixas","ferias","feriado_h",
                  "noturno_h","total_horas","media_dia"},
    "Enfermeiro":{"dias_trab","diurno_h","noturno_h","domingo_h","total_horas","media_dia"},
}


def _eh_enfermeiro(numero_str: str) -> bool:
    try:
        return int(str(numero_str).strip()) >= 500
    except (ValueError, TypeError):
        return False


def _agregar(df: pd.DataFrame) -> pd.DataFrame:
    """Agrega linhas diárias por empregado."""
    def _n(s):
        return pd.to_numeric(s, errors="coerce").fillna(0)

    linhas = df[df["data"].astype(str) != "TOTAL"].copy()
    if linhas.empty:
        return pd.DataFrame()

    rows = []
    for (numero, nome), g in linhas.groupby(["numero", "nome"], sort=True):
        presenca  = _n(g.get("presenca",          pd.Series(dtype=float)))
        sub_ref   = _n(g.get("subsidio_refeicao", pd.Series(dtype=float)))
        faltas    = _n(g.get("falta",             pd.Series(dtype=float)))
        baixas    = _n(g.get("baixa",             pd.Series(dtype=float)))
        ferias    = _n(g.get("ferias",            pd.Series(dtype=float)))
        feriado_h = _n(g.get("feriado",           pd.Series(dtype=float)))
        noturno   = _n(g.get("noturno_h" if "noturno_h" in g.columns else "noturno",
                              pd.Series(dtype=float)))
        diurno    = _n(g.get("diurno_h",  pd.Series(dtype=float)))
        domingo   = _n(g.get("domingo_h", pd.Series(dtype=float)))

        dias_trab   = int((presenca > 0).sum())
        total_horas = round(float(presenca.sum()), 2)
        media_dia   = round(total_horas / dias_trab, 2) if dias_trab else 0.0

        primeira  = g.iloc[0]
        categoria = str(primeira.get("categoria", "") or "")
        ativo_rh  = str(primeira.get("ativo_rh",  "") or "")
        tipo      = str(primeira.get("tipo", "Desconhecido") or "Desconhecido")

        if "grupo" in g.columns:
            grupo = str(primeira.get("grupo", "") or "")
        else:
            grupo = "Enfermeiro" if _eh_enfermeiro(numero) else "AAD"

        rows.append({
            "numero":      numero,
            "nome":        nome,
            "grupo":       grupo,
            "tipo":        tipo,
            "categoria":   categoria,
            "ativo_rh":    ativo_rh,
            "dias_trab":   dias_trab,
            "sub_ref":     int(sub_ref.sum()),
            "faltas":      int(faltas.sum()),
            "baixas":      int(baixas.sum()),
            "ferias":      int(ferias.sum()),
            "feriado_h":   round(float(feriado_h.sum()), 2),
            "diurno_h":    round(float(diurno.sum()), 2),
            "noturno_h":   round(float(noturno.sum()), 2),
            "domingo_h":   round(float(domingo.sum()), 2),
            "total_horas": total_horas,
            "media_dia":   media_dia,
        })

    return pd.DataFrame(rows)


class ResumoEmpregadoView(tk.Toplevel):

    _FILTROS = ["Todos", "AAD", "Enfermeiro"]

    def __init__(self, parent, df: pd.DataFrame, mes_label: str = ""):
        super().__init__(parent)
        self.title(f"Revisão do ponto — {mes_label}")
        self.configure(bg=BG)
        self.state("zoomed")
        self.resizable(True, True)

        self._resumo_completo = _agregar(df)
        self._mes_label       = mes_label
        self._filtro_ativo    = "Todos"
        self._resumo          = self._resumo_completo.copy()
        self._sort_col        = None
        self._sort_rev        = False
        self._colunas         = COLUNAS_TODOS

        self._build()
        self.grab_set()

    # ── construção da UI ──────────────────────────────────────────────────────
    def _build(self):
        # cabeçalho
        topo = tk.Frame(self, bg=BG_HEADER, pady=6)
        topo.pack(fill="x")
        tk.Label(topo, text=f"Revisão do ponto de {self._mes_label}",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG
                 ).pack(side="left", padx=16)

        # ── barra de filtro ───────────────────────────────────────────────────
        fbar = tk.Frame(self, bg=BG_HEADER, pady=5, relief="groove", bd=1)
        fbar.pack(fill="x")

        tk.Label(fbar, text="Mostrar:", font=FONT_UI, bg=BG_HEADER, fg=FG
                 ).pack(side="left", padx=(14, 8))

        self._filtro_btns = {}
        cores = {"Todos": "#c8dedd", "AAD": "#c8e8c8", "Enfermeiro": "#c8d0e8"}
        for f in self._FILTROS:
            btn = tk.Button(
                fbar, text=f, font=FONT_BOLD,
                bg=cores[f], fg=FG,
                relief="sunken" if f == "Todos" else "raised",
                padx=16, pady=3,
                command=lambda filt=f: self._aplicar_filtro(filt),
            )
            btn.pack(side="left", padx=4)
            self._filtro_btns[f] = btn

        self._lbl_cont = tk.Label(fbar, text="", font=FONT_UI, bg=BG_HEADER, fg=FG)
        self._lbl_cont.pack(side="left", padx=14)

        # ── barra de navegação empregado ──────────────────────────────────────
        ebar = tk.Frame(self, bg="#d6e6e4", pady=5, relief="groove", bd=1)
        ebar.pack(fill="x")

        tk.Button(ebar, text="◀ Anterior", command=self._anterior,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=2
                  ).pack(side="left", padx=(12, 6))
        tk.Button(ebar, text="Seguinte ▶", command=self._seguinte,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=2
                  ).pack(side="left", padx=(0, 18))

        self._emp_var = tk.StringVar(value="")
        tk.Label(ebar, textvariable=self._emp_var,
                 font=("Verdana", 12, "bold"),
                 bg="#d6e6e4", fg="#1a3a38", anchor="w"
                 ).pack(side="left", padx=8, fill="x", expand=True)

        # ── treeview ──────────────────────────────────────────────────────────
        self._tree_frame = tk.Frame(self, bg=BG)
        self._tree_frame.pack(fill="both", expand=True, padx=6, pady=(6, 0))
        self._tree_frame.rowconfigure(0, weight=1)
        self._tree_frame.columnconfigure(0, weight=1)

        self._tree = None
        self._vsb  = None
        self._hsb  = None
        self._construir_tree()

        # rodapé e toolbar
        self._frame_footer = tk.Frame(self, bg=BG_HEADER, pady=4,
                                       relief="groove", bd=1)
        self._frame_footer.pack(fill="x", padx=6, pady=(2, 0))

        bar = tk.Frame(self, bg=BG, pady=5)
        bar.pack(fill="x", padx=6, pady=(0, 4))
        tk.Button(bar, text="Fechar", command=self.destroy,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=12, pady=3
                  ).pack(side="right", padx=6)

        self._popular()

    def _construir_tree(self):
        """Cria (ou recria) o Treeview com as colunas do filtro activo."""
        if self._tree:
            self._tree.destroy()
        if self._vsb:
            self._vsb.destroy()
        if self._hsb:
            self._hsb.destroy()

        cols = [c[0] for c in self._colunas]
        self._tree = ttk.Treeview(self._tree_frame, columns=cols,
                                   show="headings", selectmode="browse")
        self._style_tree()

        for col_id, lbl, width, anchor in self._colunas:
            self._tree.heading(col_id, text=lbl,
                               command=lambda c=col_id: self._ordenar(c))
            self._tree.column(col_id, width=width, minwidth=28,
                               anchor=anchor, stretch=False)

        self._vsb = ttk.Scrollbar(self._tree_frame, orient="vertical",
                                   command=self._tree.yview)
        self._hsb = ttk.Scrollbar(self._tree_frame, orient="horizontal",
                                   command=self._tree.xview)
        self._tree.configure(yscrollcommand=self._vsb.set,
                             xscrollcommand=self._hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        self._vsb.grid(row=0, column=1, sticky="ns")
        self._hsb.grid(row=1, column=0, sticky="ew")
        self._tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("RES.Treeview",
                         background=BG_TREEVIEW, foreground="black",
                         fieldbackground=BG_TREEVIEW, rowheight=22,
                         font=FONT_MONO, borderwidth=0)
        style.configure("RES.Treeview.Heading",
                         background=BG_HEADER, foreground=FG,
                         font=FONT_BOLD, relief="groove")
        style.map("RES.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "black")])
        self._tree.configure(style="RES.Treeview")
        self._tree.tag_configure("desconhecido", foreground="#cc4400")
        self._tree.tag_configure("inativo",      foreground="gray")
        self._tree.tag_configure("aad",          background="#f4faf4")
        self._tree.tag_configure("enf",          background="#f4f6ff")

    # ── filtro ────────────────────────────────────────────────────────────────
    def _aplicar_filtro(self, filtro: str):
        self._filtro_ativo = filtro
        self._colunas = _COLUNAS_MAP[filtro]
        self._sort_col = None
        self._sort_rev = False

        # actualizar aparência dos botões
        for nome, btn in self._filtro_btns.items():
            btn.config(relief="sunken" if nome == filtro else "raised")

        if filtro == "Todos":
            self._resumo = self._resumo_completo.copy()
        else:
            self._resumo = self._resumo_completo[
                self._resumo_completo["grupo"] == filtro
            ].copy()

        self._construir_tree()
        self._popular()

    # ── popular treeview ──────────────────────────────────────────────────────
    def _popular(self):
        self._tree.delete(*self._tree.get_children())

        col_ids = [c[0] for c in self._colunas]
        int_cols = {"dias_trab", "sub_ref", "faltas", "baixas", "ferias"}
        flt_cols = {"feriado_h", "diurno_h", "noturno_h", "domingo_h",
                    "total_horas", "media_dia"}

        for _, row in self._resumo.iterrows():
            tags = []
            if row.get("tipo", "") == "Desconhecido":
                tags.append("desconhecido")
            if row.get("ativo_rh", "") == "Nao":
                tags.append("inativo")
            tags.append("enf" if row.get("grupo", "") == "Enfermeiro" else "aad")

            vals = []
            for col in col_ids:
                v = row.get(col, "")
                if col in int_cols:
                    try:
                        v = str(int(float(v)))
                    except Exception:
                        v = str(v)
                elif col in flt_cols:
                    try:
                        v = f"{float(v):.2f}"
                    except Exception:
                        v = str(v)
                else:
                    v = str(v)
                vals.append(v)

            self._tree.insert("", "end", tags=tuple(tags), values=vals)

        n = len(self._resumo)
        self._lbl_cont.config(text=f"{n} {'empregado' if n==1 else 'empregados'}")

        # selecção inicial
        children = self._tree.get_children()
        if children:
            self._tree.selection_set(children[0])
            self._tree.focus(children[0])
            self._on_select_iid(children[0])

        self._build_footer()

    # ── rodapé de totais ──────────────────────────────────────────────────────
    def _build_footer(self):
        for w in self._frame_footer.winfo_children():
            w.destroy()
        if self._resumo.empty:
            return

        r = self._resumo

        tk.Label(self._frame_footer, text="TOTAIS :", font=FONT_BOLD,
                 bg=BG_HEADER, fg=FG, width=10, anchor="w"
                 ).pack(side="left", padx=(10, 6))

        def _tot(lbl, val):
            grp = tk.Frame(self._frame_footer, bg=BG_HEADER, padx=8)
            grp.pack(side="left")
            tk.Label(grp, text=lbl,  font="Verdana 7",  bg=BG_HEADER, fg=FG).pack()
            tk.Label(grp, text=val,  font=FONT_BOLD,     bg=BG_HEADER, fg="black").pack()

        f = self._filtro_ativo
        _tot("Dias Trab.", str(int(r["dias_trab"].sum())))

        if f in ("Todos", "AAD"):
            _tot("Sub.Ref.",  str(int(r["sub_ref"].sum())))
            _tot("Faltas",    str(int(r["faltas"].sum())))
            _tot("Baixas",    str(int(r["baixas"].sum())))
            _tot("Férias",    str(int(r["ferias"].sum())))
            _tot("Fer.h",     f"{r['feriado_h'].sum():.2f}")

        if f in ("Todos", "Enfermeiro"):
            _tot("Diurno h",  f"{r['diurno_h'].sum():.2f}")

        _tot("Noturno h",     f"{r['noturno_h'].sum():.2f}")

        if f in ("Todos", "Enfermeiro"):
            _tot("Dom/Fer h", f"{r['domingo_h'].sum():.2f}")

        _tot("Total h",       f"{r['total_horas'].sum():.2f}")
        dt = r["dias_trab"].sum()
        media = round(r["total_horas"].sum() / dt, 2) if dt > 0 else 0.0
        _tot("Média/dia",     f"{media:.2f}")

    # ── navegação anterior / seguinte ─────────────────────────────────────────
    def _on_tree_select(self, _event=None):
        sel = self._tree.selection()
        if sel:
            self._on_select_iid(sel[0])

    def _on_select_iid(self, iid):
        col_ids = [c[0] for c in self._colunas]
        numero = self._tree.set(iid, "numero") if "numero" in col_ids else ""
        nome   = self._tree.set(iid, "nome")   if "nome"   in col_ids else ""
        self._emp_var.set(f"{numero}  —  {nome}")

    def _anterior(self):
        children = self._tree.get_children()
        if not children:
            return
        sel = self._tree.selection()
        idx = children.index(sel[0]) if sel else 1
        target = children[idx - 1] if idx > 0 else children[-1]
        self._tree.selection_set(target)
        self._tree.focus(target)
        self._tree.see(target)
        self._on_select_iid(target)

    def _seguinte(self):
        children = self._tree.get_children()
        if not children:
            return
        sel = self._tree.selection()
        idx = children.index(sel[0]) if sel else -1
        target = children[idx + 1] if idx < len(children) - 1 else children[0]
        self._tree.selection_set(target)
        self._tree.focus(target)
        self._tree.see(target)
        self._on_select_iid(target)

    # ── ordenação ─────────────────────────────────────────────────────────────
    def _ordenar(self, col):
        rev = not self._sort_rev if self._sort_col == col else False
        self._sort_col = col
        self._sort_rev = rev

        for c_id, lbl, _, _ in self._colunas:
            self._tree.heading(c_id, text=lbl)
        suf = " (D)" if rev else " (A)"
        lbl_col = next(c[1] for c in self._colunas if c[0] == col)
        self._tree.heading(col, text=lbl_col + suf)

        cols_num = _COLS_NUM.get(self._filtro_ativo, set())

        def _chave(iid):
            val = self._tree.set(iid, col)
            if col in cols_num:
                try:
                    return float(val)
                except Exception:
                    return 0.0
            return val.lower()

        itens = sorted(self._tree.get_children(), key=_chave, reverse=rev)
        for i, iid in enumerate(itens):
            self._tree.move(iid, "", i)
