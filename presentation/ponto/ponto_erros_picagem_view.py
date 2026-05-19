# presentation/ponto/ponto_erros_picagem_view.py

import logging
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import pandas as pd
from presentation.shared.base_gui import BaseGui as _BG

logger = logging.getLogger(__name__)

BG          = _BG.BG
FG          = _BG.FG
BTN_BG      = _BG.BTN_BG
FONT_BUTTON = _BG.FONT_BUTTON
FONT_TITLE  = _BG.FONT_TITLE
FONT_UI     = _BG.FONT_SUB

BG_TREEVIEW = "#ffffff"
BG_HEADER   = "#b8cccb"
SEL_BG      = "#a8c4c0"
ERR_FG      = "#cc4400"
FONT_MONO   = ("Courier New", 9)

COLUNAS = [
    ("numero",        "Nº",               52),
    ("nome",          "Nome",             200),
    ("data",          "Data",              88),
    ("dia_semana",    "Dia",               68),
    ("e1",            "E1",                52),
    ("s1",            "S1",                52),
    ("e2",            "E2",                52),
    ("s2",            "S2",                52),
    ("erros_picagem", "Erro de Picagem",  380),
]

_COL_CENTER = {"e1", "s1", "e2", "s2", "data", "numero"}

COL_MAP_XLSX = {
    "numero":        "Nº",
    "nome":          "Nome",
    "data":          "Data",
    "dia_semana":    "Dia Semana",
    "e1":            "E1",
    "s1":            "S1",
    "e2":            "E2",
    "s2":            "S2",
    "erros_picagem": "Erro de Picagem",
}


class ErrosPicagemView(tk.Toplevel):

    def __init__(self, parent, df: pd.DataFrame, mes_label: str = ""):
        super().__init__(parent)
        self._mes_label = mes_label
        titulo = f"Erros de Picagem — {mes_label}" if mes_label else "Erros de Picagem"
        self.title(titulo)
        self.configure(bg=BG)
        self.state("zoomed")
        self.resizable(True, True)

        self._df_erros = self._extrair_erros(df)
        self._build()
        self._preencher(self._df_erros)
        self.grab_set()

    # ── dados ─────────────────────────────────────────────────────────────────

    @staticmethod
    def _extrair_erros(df: pd.DataFrame) -> pd.DataFrame:
        if "erros_picagem" not in df.columns:
            return pd.DataFrame(columns=["numero", "nome", "data", "dia_semana",
                                         "e1", "s1", "e2", "s2", "erros_picagem"])
        mask = (
            (df["data"].astype(str) != "TOTAL") &
            df["erros_picagem"].notna() &
            (df["erros_picagem"].astype(str).str.strip() != "") &
            (~df["erros_picagem"].astype(str).str.strip().str.lower().isin(["nan", "none"]))
        )
        cols = [c for c in ["numero", "nome", "data", "dia_semana",
                             "e1", "s1", "e2", "s2", "erros_picagem"]
                if c in df.columns]
        return df[mask][cols].copy().reset_index(drop=True)

    # ── UI ────────────────────────────────────────────────────────────────────

    def _build(self):
        # cabeçalho
        topo = tk.Frame(self, bg=BG_HEADER, pady=6)
        topo.pack(fill="x")
        titulo = f"Erros de Picagem — {self._mes_label}" if self._mes_label else "Erros de Picagem"
        tk.Label(topo, text=titulo, font=FONT_TITLE, bg=BG_HEADER, fg=FG).pack(side="left", padx=16)

        # barra de filtro por trabalhador
        fbar = tk.Frame(self, bg=BG_HEADER, pady=4, relief="groove", bd=1)
        fbar.pack(fill="x")
        tk.Label(fbar, text="Trabalhador:", font=FONT_UI, bg=BG_HEADER, fg=FG
                 ).pack(side="left", padx=(14, 6))

        nomes = ["Todos"]
        if not self._df_erros.empty and "nome" in self._df_erros.columns:
            nomes += sorted(self._df_erros["nome"].astype(str).str.strip().unique().tolist())

        self._var_filtro = tk.StringVar(value="Todos")
        cb = ttk.Combobox(fbar, textvariable=self._var_filtro, values=nomes,
                          state="readonly", font=FONT_UI, width=34)
        cb.pack(side="left", padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _: self._aplicar_filtro())

        self._lbl_cont = tk.Label(fbar, text="", font=FONT_UI, bg=BG_HEADER, fg=FG)
        self._lbl_cont.pack(side="left", padx=14)

        # treeview
        tree_frame = tk.Frame(self, bg=BG)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=(4, 0))

        cols = [c[0] for c in COLUNAS]
        self._tree = ttk.Treeview(tree_frame, columns=cols,
                                   show="headings", selectmode="browse")
        self._style_tree()

        for col_id, col_lbl, col_w in COLUNAS:
            self._tree.heading(col_id, text=col_lbl)
            anchor = "center" if col_id in _COL_CENTER else "w"
            stretch = col_id == "erros_picagem"
            self._tree.column(col_id, width=col_w, minwidth=30,
                               anchor=anchor, stretch=stretch)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        # toolbar
        bar = tk.Frame(self, bg=BG, pady=5)
        bar.pack(fill="x", padx=6, pady=(2, 4))
        tk.Button(bar, text="Exportar para XLSX", command=self._exportar,
                  bg=BTN_BG, fg=FG, font=FONT_BUTTON,
                  relief="raised", padx=16, pady=3).pack(side="right", padx=6)
        tk.Button(bar, text="Fechar", command=self.destroy,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=3).pack(side="right", padx=4)

    def _style_tree(self):
        style = ttk.Style()
        style.theme_use("default")
        style.configure("ERR.Treeview",
                        background=BG_TREEVIEW, foreground="black",
                        fieldbackground=BG_TREEVIEW, rowheight=22,
                        font=FONT_MONO, borderwidth=0)
        style.configure("ERR.Treeview.Heading",
                        background=BG_HEADER, foreground=FG,
                        font=FONT_UI, relief="groove")
        style.map("ERR.Treeview",
                  background=[("selected", SEL_BG)],
                  foreground=[("selected", "black")])
        self._tree.configure(style="ERR.Treeview")
        self._tree.tag_configure("erro", foreground=ERR_FG)

    # ── preenchimento / filtro ────────────────────────────────────────────────

    def _preencher(self, df: pd.DataFrame):
        self._tree.delete(*self._tree.get_children())
        for _, row in df.iterrows():
            valores = []
            for col_id, *_ in COLUNAS:
                v = row.get(col_id, "")
                if v is None or (isinstance(v, float) and pd.isna(v)):
                    v = ""
                valores.append(str(v).strip())
            self._tree.insert("", "end", values=valores, tags=("erro",))
        n = len(df)
        self._lbl_cont.config(text=f"{n} {'erro' if n == 1 else 'erros'}")

    def _aplicar_filtro(self):
        nome = self._var_filtro.get().strip()
        if nome == "Todos":
            df = self._df_erros
        else:
            df = self._df_erros[
                self._df_erros["nome"].astype(str).str.strip() == nome
            ]
        self._preencher(df)

    def _df_visivel(self) -> pd.DataFrame:
        nome = self._var_filtro.get().strip()
        if nome == "Todos":
            return self._df_erros
        return self._df_erros[
            self._df_erros["nome"].astype(str).str.strip() == nome
        ]

    # ── exportação ────────────────────────────────────────────────────────────

    def _exportar(self):
        df = self._df_visivel()
        if df.empty:
            messagebox.showinfo("Sem dados", "Nao ha erros para exportar.", parent=self)
            return

        nome_filtro = self._var_filtro.get().strip()
        suf = "" if nome_filtro == "Todos" else f"_{nome_filtro.split()[0]}"
        mes_clean = self._mes_label.replace(" ", "_") if self._mes_label else ""
        initial = f"erros_picagem{suf}_{mes_clean}.xlsx" if mes_clean else f"erros_picagem{suf}.xlsx"

        path = filedialog.asksaveasfilename(
            title="Guardar Excel",
            defaultextension=".xlsx",
            filetypes=[("Excel", "*.xlsx")],
            initialfile=initial,
            parent=self,
        )
        if not path:
            return

        export_df = df.copy()
        export_df.columns = [COL_MAP_XLSX.get(c, c) for c in export_df.columns]

        try:
            export_df.to_excel(path, index=False)
            messagebox.showinfo(
                "Exportado",
                f"{len(export_df)} registo(s) exportado(s) para:\n{path}",
                parent=self,
            )
        except Exception as e:
            logger.error(f"Erro ao exportar erros de picagem: {e}", exc_info=True)
            messagebox.showerror("Erro", f"Nao foi possivel exportar:\n{e}", parent=self)
