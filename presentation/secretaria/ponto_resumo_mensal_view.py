# presentation/secretaria/ponto_resumo_mensal_view.py
"""
View de revisão e edição do Resumo Mensal de Ponto.

Paleta idêntica ao BaseGui (BG #CADAD9 / FG #92332C / BTN_BG #F1E2CF).
Duplo-clique numa linha → editar campos numéricos e observações.
Rodapé com totais actualizados em tempo real.

Campos READ-ONLY  : data, dia_semana, feriado_desc, e1, s1, e2, s2, erros_picagem
Campos EDITÁVEIS  : presenca, falta, feriado, ferias, noturno, baixa,
                    subsidio_refeicao, observacoes_sc, observacoes_js
"""

import logging
import tkinter as tk
from tkinter import ttk, messagebox
import pandas as pd
from presentation.shared.base_gui import BaseGui as _BG

logger = logging.getLogger(__name__)

# ── Tema lido do BaseGui — sem redefinir ──────────────────────────────────────
BG          = _BG.BG
FG          = _BG.FG
BTN_BG      = _BG.BTN_BG
FONT_BUTTON = _BG.FONT_BUTTON
FONT_TITLE  = _BG.FONT_TITLE
FONT_UI     = _BG.FONT_SUB
FONT_BOLD   = _BG.FONT_SUB
FONT_TOTAL  = _BG.FONT_SUB

# Variações locais (não existem no BaseGui)
BG_TREEVIEW = "#ffffff"
BG_HEADER   = "#b8cccb"
BG_FOOTER   = "#d4e8d4"
BG_ENTRY    = "#f8f8f8"
SEL_BG      = "#a8c4c0"
SAB_BG      = "#e8e8e8"
DOM_BG      = "#f5dce0"
FER_FG      = "#8b0000"
ERR_FG      = "#cc4400"
EDIT_FG     = "#1a5c1a"
FONT_MONO   = ("Courier New", 9)
FONT_NAV    = "Verdana 10 bold"

COLUNAS = [
    ("data",              "Data",          82,  False),
    ("dia_semana",        "Dia",           68,  False),
    ("feriado_desc",      "Feriado",      118,  False),
    ("e1",                "E1",            70,  False),
    ("s1",                "S1",            70,  False),
    ("e2",                "E2",            70,  False),
    ("s2",                "S2",            70,  False),
    ("presenca",          "Presenca",      68,  True),
    ("falta",             "Falta",         46,  True),
    ("feriado",           "Fer.",          46,  True),
    ("ferias",            "Ferias",        46,  True),
    ("noturno",           "Noturno",       64,  True),
    ("baixa",             "Baixa",         46,  True),
    ("subsidio_refeicao", "S.Ref.",        52,  True),
    ("erros_picagem",     "Erros",        148,  False),
    ("observacoes_sc",    "Obs.SC",       118,  True),
    ("observacoes_js",    "Obs.JS",       118,  True),
]
COL_NUM    = {"presenca","falta","feriado","ferias","noturno","baixa","subsidio_refeicao"}
TOTAIS_NUM = ["presenca","falta","feriado","ferias","noturno","baixa","subsidio_refeicao"]


class _EditDialog(tk.Toplevel):

    def __init__(self, parent, row_data: dict, callback):
        super().__init__(parent)
        self.callback = callback
        self._vars    = {}
        self.title(f"Editar  {row_data.get('data','')}  -  {row_data.get('nome','')}")
        self.resizable(False, False)
        self.configure(bg=BG)
        self.grab_set()
        self._build(row_data)
        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{pw - w//2}+{ph - h//2}")
        self.wait_window()

    def _build(self, rd):
        pad = dict(padx=12, pady=3)

        hdr = tk.Frame(self, bg=BG_HEADER, pady=6, padx=12)
        hdr.pack(fill="x")
        info = (f"{rd.get('dia_semana','')}  |  "
                f"E1: {rd.get('e1','')}  S1: {rd.get('s1','')}  "
                f"E2: {rd.get('e2','')}  S2: {rd.get('s2','')}")
        if rd.get("feriado_desc"):
            info += f"  |  {rd['feriado_desc']}"
        tk.Label(hdr, text=info, font=FONT_MONO, bg=BG_HEADER, fg=FG).pack(anchor="w")
        erros = rd.get("erros_picagem", "")
        if erros:
            tk.Label(hdr, text=f"Atencao: {erros}", font=FONT_UI, bg=BG_HEADER,
                     fg=ERR_FG).pack(anchor="w")

        body = tk.Frame(self, bg=BG, padx=14, pady=8)
        body.pack(fill="both")

        campos_num = [
            ("presenca",          "Presenca (h)"),
            ("falta",             "Falta  (0/1)"),
            ("feriado",           "Feriado (h)"),
            ("ferias",            "Ferias  (0/1)"),
            ("noturno",           "Noturno (h)"),
            ("baixa",             "Baixa   (0/1)"),
            ("subsidio_refeicao", "Sub. Refeicao (0/1)"),
        ]
        campos_txt = [
            ("observacoes_sc", "Observacoes SC"),
            ("observacoes_js", "Observacoes JS"),
        ]
        for col, lbl in campos_num:
            self._add_field(body, lbl, col, rd, numeric=True, **pad)
        ttk.Separator(body, orient="horizontal").pack(fill="x", pady=6)
        for col, lbl in campos_txt:
            self._add_field(body, lbl, col, rd, numeric=False, **pad)

        bf = tk.Frame(self, bg=BG, pady=8)
        bf.pack(fill="x")
        tk.Button(bf, text="Guardar", command=self._save,
                  bg=BTN_BG, fg=FG, font=FONT_BOLD,
                  relief="raised", padx=16, pady=4
                  ).pack(side="right", padx=12)
        tk.Button(bf, text="Cancelar", command=self.destroy,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=12, pady=4
                  ).pack(side="right", padx=4)

    def _add_field(self, parent, label, col, rd, numeric, **kw):
        row = tk.Frame(parent, bg=BG)
        row.pack(fill="x", **kw)
        tk.Label(row, text=label, width=22, anchor="w",
                 font=FONT_UI, bg=BG, fg=FG).pack(side="left")
        var = tk.StringVar(value=str(rd.get(col, "") or ""))
        tk.Entry(row, textvariable=var, font=FONT_MONO,
                 bg=BG_ENTRY, fg="black", relief="solid", bd=1,
                 width=10 if numeric else 32).pack(side="left")
        self._vars[col] = (var, numeric)

    def _save(self):
        result = {}
        for col, (var, numeric) in self._vars.items():
            raw = var.get().strip()
            if numeric:
                try:
                    result[col] = float(raw) if "." in raw else int(raw)
                except ValueError:
                    messagebox.showerror("Valor invalido",
                                         f"'{raw}' nao e um numero valido para '{col}'.",
                                         parent=self)
                    return
            else:
                result[col] = raw
        self.callback(result)
        self.destroy()


class ResumoMensalView(tk.Toplevel):

    def __init__(self, parent, df: pd.DataFrame, on_save=None, mes_label: str = ""):
        super().__init__(parent)
        self.title(f"Revisao Mensal de Ponto - {mes_label}")
        self.configure(bg=BG)
        self.state("zoomed")
        self.resizable(True, True)

        self._on_save   = on_save
        self._mes_label = mes_label
        self._df        = df.copy()
        self._modified  = False

        self._empregados = self._listar_empregados()
        self._emp_idx    = 0

        self._build()
        self._mostrar_empregado()
        self.grab_set()

    # ── dados ─────────────────────────────────────────────────────────────────
    def _listar_empregados(self):
        df = self._df[self._df["data"] != "TOTAL"]
        if df.empty:
            return []
        return list(df.groupby(["numero", "nome"], sort=True).groups.keys())

    def _linhas_empregado(self, numero, nome):
        df = self._df
        mask = (
            (df["data"] != "TOTAL") &
            (df["numero"].astype(str) == str(numero)) &
            (df["nome"].astype(str)   == str(nome))
        )
        return df[mask].copy()

    def _calcular_totais(self, numero, nome):
        linhas = self._linhas_empregado(numero, nome)
        totais = {}
        for col in TOTAIS_NUM:
            if col in linhas.columns:
                totais[col] = round(
                    float(pd.to_numeric(linhas[col], errors="coerce").fillna(0).sum()), 2)
            else:
                totais[col] = 0.0
        return totais

    def _atualizar_linha_total_df(self, numero, nome):
        totais = self._calcular_totais(numero, nome)
        mask = (
            (self._df["data"] == "TOTAL") &
            (self._df["numero"].astype(str) == str(numero)) &
            (self._df["nome"].astype(str)   == str(nome))
        )
        if mask.any():
            idx = self._df[mask].index[0]
            for col, val in totais.items():
                self._df.at[idx, col] = val
        else:
            nova = {"data": "TOTAL", "numero": numero, "nome": nome}
            nova.update(totais)
            self._df = pd.concat([self._df, pd.DataFrame([nova])], ignore_index=True)
        return totais

    # ── UI ────────────────────────────────────────────────────────────────────
    def _build(self):
        topo = tk.Frame(self, bg=BG_HEADER, pady=6)
        topo.pack(fill="x")

        tk.Label(topo, text="REVISAO MENSAL DE PONTO",
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG).pack(side="left", padx=16)
        tk.Label(topo, text=self._mes_label,
                 font=FONT_TITLE, bg=BG_HEADER, fg=FG).pack(side="left")

        nav = tk.Frame(topo, bg=BG_HEADER)
        nav.pack(side="right", padx=16)

        self._btn_prev = tk.Button(nav, text="<  Anterior", command=self._prev_emp,
                                   font=FONT_NAV, bg=BTN_BG, fg=FG,
                                   relief="raised", padx=8, pady=2)
        self._btn_prev.pack(side="left")

        self._lbl_emp = tk.Label(nav, text="", font=FONT_NAV,
                                  bg=BG_HEADER, fg=FG, width=32, anchor="center")
        self._lbl_emp.pack(side="left", padx=10)

        self._btn_next = tk.Button(nav, text="Seguinte  >", command=self._next_emp,
                                   font=FONT_NAV, bg=BTN_BG, fg=FG,
                                   relief="raised", padx=8, pady=2)
        self._btn_next.pack(side="left")

        self._lbl_emp_n = tk.Label(nav, text="", font=FONT_UI,
                                    bg=BG_HEADER, fg=FG, width=10)
        self._lbl_emp_n.pack(side="left", padx=(12, 0))

        # Treeview
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=(4, 0))

        cols = [c[0] for c in COLUNAS]
        self._tree = ttk.Treeview(tree_frame, columns=cols, show="headings",
                                   selectmode="browse")
        self._style_tree()

        for col_id, col_lbl, col_w, _ in COLUNAS:
            self._tree.heading(col_id, text=col_lbl)
            anchor = "e" if col_id in COL_NUM else "w"
            self._tree.column(col_id, width=col_w, minwidth=30,
                               anchor=anchor, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal",  command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self._tree.bind("<Double-1>", self._on_double_click)

        self._build_footer()
        self._build_toolbar()

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("PMR.Treeview",
                         background=BG_TREEVIEW, foreground="black",
                         fieldbackground=BG_TREEVIEW, rowheight=22,
                         font=FONT_MONO, borderwidth=0)
        style.configure("PMR.Treeview.Heading",
                         background=BG_HEADER, foreground=FG,
                         font=FONT_BOLD, relief="groove")
        style.map("PMR.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "black")])
        self._tree.configure(style="PMR.Treeview")

        self._tree.tag_configure("sabado",  background=SAB_BG)
        self._tree.tag_configure("domingo", background=DOM_BG)
        self._tree.tag_configure("feriado", foreground=FER_FG)
        self._tree.tag_configure("erro",    foreground=ERR_FG)
        self._tree.tag_configure("editado", foreground=EDIT_FG)

    def _build_footer(self):
        foot = tk.Frame(self, bg=BG_FOOTER, pady=5, relief="groove", bd=1)
        foot.pack(fill="x", padx=6, pady=(2, 0))

        tk.Label(foot, text="TOTAL DO MES :", font=FONT_TOTAL,
                 bg=BG_FOOTER, fg=FG, width=16, anchor="w"
                 ).pack(side="left", padx=(10, 6))

        self._total_vars = {}
        for col, lbl in [
            ("presenca",          "Presenca"),
            ("falta",             "Faltas"),
            ("feriado",           "Feriados"),
            ("ferias",            "Ferias"),
            ("noturno",           "Noturno"),
            ("baixa",             "Baixas"),
            ("subsidio_refeicao", "Sub.Ref."),
        ]:
            grp = tk.Frame(foot, bg=BG_FOOTER, padx=10)
            grp.pack(side="left")
            tk.Label(grp, text=lbl, font="Verdana 7", bg=BG_FOOTER, fg=FG).pack()
            var = tk.StringVar(value="-")
            tk.Label(grp, textvariable=var, font=FONT_TOTAL,
                     bg=BG_FOOTER, fg="black").pack()
            self._total_vars[col] = var

    def _build_toolbar(self):
        bar = tk.Frame(self, bg=BG, pady=5)
        bar.pack(fill="x", padx=6, pady=(0, 4))

        tk.Label(bar, text="  Duplo-clique numa linha para editar os valores",
                 font=FONT_UI, bg=BG, fg=FG).pack(side="left")

        tk.Button(bar, text="Guardar Alteracoes", command=self._guardar,
                  bg=BTN_BG, fg=FG, font=FONT_BUTTON,
                  relief="raised", padx=16, pady=3
                  ).pack(side="right", padx=6)
        tk.Button(bar, text="Fechar sem guardar", command=self._fechar,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=3
                  ).pack(side="right", padx=4)

    # ── navegação ─────────────────────────────────────────────────────────────
    def _prev_emp(self):
        if self._emp_idx > 0:
            self._emp_idx -= 1
            self._mostrar_empregado()

    def _next_emp(self):
        if self._emp_idx < len(self._empregados) - 1:
            self._emp_idx += 1
            self._mostrar_empregado()

    def _mostrar_empregado(self):
        if not self._empregados:
            self._lbl_emp.config(text="(sem empregados)")
            return
        numero, nome = self._empregados[self._emp_idx]
        n = len(self._empregados)
        self._lbl_emp.config(text=f"{numero} - {nome}")
        self._lbl_emp_n.config(text=f"{self._emp_idx+1} / {n}")
        self._btn_prev.config(state="normal" if self._emp_idx > 0     else "disabled")
        self._btn_next.config(state="normal" if self._emp_idx < n - 1 else "disabled")
        self._preencher_tree(numero, nome)
        self._atualizar_totais_footer(numero, nome)

    # ── Treeview ──────────────────────────────────────────────────────────────
    def _preencher_tree(self, numero, nome):
        self._tree.delete(*self._tree.get_children())
        linhas = self._linhas_empregado(numero, nome)

        for _, row in linhas.iterrows():
            valores = []
            for col_id, *_ in COLUNAS:
                val = row.get(col_id, "")
                if pd.isna(val) or val is None:
                    val = ""
                elif col_id in COL_NUM:
                    try:
                        f = float(val)
                        if col_id in {"presenca", "noturno", "feriado"}:
                            val = f"{f:.2f}"
                        else:
                            val = str(int(f)) if f == int(f) else str(f)
                    except (ValueError, TypeError):
                        val = str(val)
                else:
                    val = str(val)
                valores.append(val)

            self._tree.insert("", "end", iid=str(row.name),
                               values=valores, tags=self._tags_linha(row))

    def _tags_linha(self, row):
        tags = []
        dia = str(row.get("dia_semana", ""))
        if dia == "Sabado":
            tags.append("sabado")
        elif dia == "Domingo":
            tags.append("domingo")
        if row.get("feriado_desc", ""):
            tags.append("feriado")
        if row.get("erros_picagem", ""):
            tags.append("erro")
        return tuple(tags)

    def _atualizar_totais_footer(self, numero, nome):
        totais = self._calcular_totais(numero, nome)
        for col, var in self._total_vars.items():
            val = totais.get(col, 0.0)
            if col in {"presenca", "noturno", "feriado"}:
                var.set(f"{val:.2f} h")
            else:
                var.set(str(int(val)))

    # ── edição ────────────────────────────────────────────────────────────────
    def _on_double_click(self, event):
        sel = self._tree.selection()
        if not sel:
            return
        iid = sel[0]
        try:
            idx = int(iid)
        except ValueError:
            return
        if idx not in self._df.index:
            return
        row = self._df.loc[idx]
        if str(row.get("data", "")) == "TOTAL":
            return
        row_data = {c: row.get(c, "") for c in self._df.columns}

        def _on_edit(result: dict):
            for col, val in result.items():
                self._df.at[idx, col] = val
            self._modified = True
            numero, nome = self._empregados[self._emp_idx]
            self._preencher_tree(numero, nome)
            try:
                self._tree.selection_set(iid)
                self._tree.see(iid)
            except Exception:
                pass
            self._atualizar_linha_total_df(numero, nome)
            self._atualizar_totais_footer(numero, nome)

        _EditDialog(self, row_data, _on_edit)

    # ── guardar / fechar ──────────────────────────────────────────────────────
    def _guardar(self):
        if self._on_save:
            try:
                self._on_save(self._df.copy())
                self._modified = False
                messagebox.showinfo("Guardado",
                                     "Resumo mensal actualizado com sucesso.",
                                     parent=self)
            except Exception as e:
                logger.error(f"Erro ao guardar resumo: {e}", exc_info=True)
                messagebox.showerror("Erro", f"Nao foi possivel guardar:\n{e}", parent=self)
        else:
            messagebox.showinfo("Info", "Sem handler de gravacao configurado.", parent=self)

    def _fechar(self):
        if self._modified:
            if not messagebox.askyesno(
                "Alteracoes nao gravadas",
                "Ha alteracoes nao gravadas. Fechar mesmo assim?",
                parent=self,
            ):
                return
        self.destroy()
