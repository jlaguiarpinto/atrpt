# presentation/fornecedores/fornecedor_historico_gui.py
#
# Vista de histórico de faturação mensal por fornecedor.
# Lê a tabela faturacao_mensal (populada via importar_efatura_usecase).

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]


class FornecedorHistoricoGUI(BG):
    """Mostra o histórico de faturação mensal de um fornecedor."""

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._fornecedores = []

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar_fornecedores()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=10, pady=8)

        # ── barra de topo ─────────────────────────────────────────────
        barra = tk.Frame(outer, bg=self.BG)
        barra.pack(fill="x", pady=(0, 8))

        tk.Label(barra, text="Fornecedor:", bg=self.BG, fg=self.FG).pack(side="left")

        self.cb_forn = ttk.Combobox(barra, state="readonly", width=55)
        self.cb_forn.pack(side="left", padx=(4, 20))
        self.cb_forn.bind("<<ComboboxSelected>>", lambda e: self._carregar_historico())

        ttk.Button(barra, text="Importar E-Fatura…",
                   command=self._importar).pack(side="left", padx=4)
        ttk.Button(barra, text="↺ Atualizar",
                   command=self._carregar_historico).pack(side="left", padx=4)

        # ── tabela mensal ─────────────────────────────────────────────
        tree_frame = tk.Frame(outer, bg=self.BG)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = ("ano", "mes", "n_docs", "base", "iva", "total")
        self.tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="browse", height=20,
        )

        cfg = {
            "ano":    ("Ano",               70, "center"),
            "mes":    ("Mês",               70, "center"),
            "n_docs": ("Docs",              60, "center"),
            "base":   ("Base Tributável",  160, "e"),
            "iva":    ("IVA",              130, "e"),
            "total":  ("Total",            140, "e"),
        }
        for col, (label, width, anchor) in cfg.items():
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=width, anchor=anchor, minwidth=40)

        # cores alternadas por ano
        self.tree.tag_configure("par",   background="#f5f5f5")
        self.tree.tag_configure("impar", background="#ffffff")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        # ── rodapé com totais ─────────────────────────────────────────
        self.lbl_totais = tk.Label(
            outer, text="", bg=self.BG, fg=self.FG,
            font=("Segoe UI", 9, "bold"), anchor="e",
        )
        self.lbl_totais.pack(fill="x", pady=(6, 0))

        self._ord_col = "ano"
        self._ord_asc = False   # mais recente primeiro por omissão

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar_fornecedores(self):
        self._fornecedores = self.controller.get_fornecedores()
        self.cb_forn["values"] = [
            f"{f.nome}  [{f.nif or '—'}]"
            for f in self._fornecedores
        ]

    def _forn_actual(self):
        idx = self.cb_forn.current()
        return self._fornecedores[idx] if idx >= 0 else None

    def _carregar_historico(self):
        self.tree.delete(*self.tree.get_children())
        self.lbl_totais.config(text="")
        f = self._forn_actual()
        if not f:
            return

        rows = self.controller.get_historico_faturacao(f.id)
        if not rows:
            self.lbl_totais.config(text="Sem dados de faturação para este fornecedor.")
            return

        # ordenar
        col_map = {
            "ano":    lambda r: (r["ano"]  or 0, r["mes"] or 0),
            "mes":    lambda r: (r["mes"]  or 0, r["ano"] or 0),
            "n_docs": lambda r: r["n_documentos"]  or 0,
            "base":   lambda r: r["base_tributavel"] or 0,
            "iva":    lambda r: r["iva"]   or 0,
            "total":  lambda r: r["total"] or 0,
        }
        rows = sorted(rows, key=col_map[self._ord_col], reverse=not self._ord_asc)

        tot_base = tot_iva = tot_total = 0.0
        anos_vistos = {}
        cor_idx = 0
        for r in rows:
            ano = r["ano"]
            if ano not in anos_vistos:
                anos_vistos[ano] = cor_idx % 2
                cor_idx += 1
            tag = "par" if anos_vistos[ano] == 0 else "impar"
            m = r["mes"]
            mes_nome = MESES[m - 1] if m and 1 <= m <= 12 else (str(m) if m else "—")
            self.tree.insert("", "end", tags=(tag,), values=(
                ano,
                mes_nome,
                r["n_documentos"],
                f"{r['base_tributavel']:,.2f} €",
                f"{r['iva']:,.2f} €",
                f"{r['total']:,.2f} €",
            ))
            tot_base  += r["base_tributavel"]
            tot_iva   += r["iva"]
            tot_total += r["total"]

        self.lbl_totais.config(
            text=(
                f"{len(rows)} meses  |  "
                f"Base {tot_base:,.2f} €   "
                f"IVA {tot_iva:,.2f} €   "
                f"Total {tot_total:,.2f} €"
            )
        )

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._carregar_historico()

    # ------------------------------------------------------------------
    # Acções
    # ------------------------------------------------------------------

    def _importar(self):
        path = self.ask_file(
            title="Selecionar E_Fatura.xls",
            filetypes=[("Excel", "*.xls *.xlsx"), ("Todos os ficheiros", "*.*")],
        )
        if not path:
            return
        self.controller.importar_efatura(path)
        # recarregar a lista de fornecedores (pode ter novos NIFs?)
        self._carregar_fornecedores()
        self._carregar_historico()
