# presentation/fornecedores/historico_faturacao_gui.py
#
# View principal do histórico de faturação (E-Fatura AT).
# Mostra documentos individuais (faturacao_documentos) com filtros
# por fornecedor, ano, mês e tipo de documento.

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG

MESES = {
    1: "Janeiro", 2: "Fevereiro", 3: "Março",    4: "Abril",
    5: "Maio",    6: "Junho",     7: "Julho",     8: "Agosto",
    9: "Setembro",10: "Outubro",  11: "Novembro", 12: "Dezembro",
}


class HistoricoFaturacaoGUI(BG):
    """
    Vista de histórico de faturação.
    Lista documentos individuais importados do E-Fatura AT,
    com filtros por fornecedor, ano, mês e tipo.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._fornecedores = []
        self._dados = []

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._popular_filtros()

    # ------------------------------------------------------------------
    # Construção
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=10, pady=6)

        # ── barra de filtros ──────────────────────────────────────────
        filtros = tk.LabelFrame(outer, text="Filtros", bg=self.BG,
                                fg=self.FG, font=("Segoe UI", 8, "bold"))
        filtros.pack(fill="x", pady=(0, 6))

        # linha 1 de filtros
        f1 = tk.Frame(filtros, bg=self.BG)
        f1.pack(fill="x", padx=6, pady=(4, 2))

        tk.Label(f1, text="Fornecedor:", bg=self.BG, fg=self.FG).pack(side="left")
        self.cb_forn = ttk.Combobox(f1, state="readonly", width=48)
        self.cb_forn.pack(side="left", padx=(3, 16))

        tk.Label(f1, text="Ano:", bg=self.BG, fg=self.FG).pack(side="left")
        self.cb_ano = ttk.Combobox(f1, state="readonly", width=7)
        self.cb_ano.pack(side="left", padx=(3, 16))

        tk.Label(f1, text="Mês:", bg=self.BG, fg=self.FG).pack(side="left")
        self.cb_mes = ttk.Combobox(f1, state="readonly", width=12)
        self.cb_mes.pack(side="left", padx=(3, 16))

        tk.Label(f1, text="Tipo:", bg=self.BG, fg=self.FG).pack(side="left")
        self.cb_tipo = ttk.Combobox(f1, state="readonly", width=18)
        self.cb_tipo.pack(side="left", padx=(3, 16))

        # linha 2: botões
        f2 = tk.Frame(filtros, bg=self.BG)
        f2.pack(fill="x", padx=6, pady=(2, 4))

        tk.Button(f2, text="Filtrar", command=self._filtrar,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left", padx=(0, 8))
        tk.Button(f2, text="Limpar filtros", command=self._limpar_filtros,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left", padx=(0, 24))
        tk.Button(f2, text="Importar E-Fatura…", command=self._importar,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left")
        tk.Button(f2, text="Apagar sem data", command=self._apagar_sem_data,
                  font=self.FONT_BUTTON, bg="#ffcccc").pack(side="left", padx=(8, 0))

        self.lbl_contagem = tk.Label(f2, text="", bg=self.BG, fg=self.FG,
                                     font=("Segoe UI", 8))
        self.lbl_contagem.pack(side="right", padx=8)

        # ── tabela de documentos ──────────────────────────────────────
        tree_frame = tk.Frame(outer, bg=self.BG)
        tree_frame.pack(fill="both", expand=True)
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        cols = ("data", "numero", "fornecedor", "tipo", "base", "iva", "total", "situacao")
        self.tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="browse", height=20,
        )

        cfg = {
            "data":       ("Data",            90, "center"),
            "numero":     ("Nº Documento",   160, "w"),
            "fornecedor": ("Fornecedor",      240, "w"),
            "tipo":       ("Tipo",            110, "w"),
            "base":       ("Base Trib.",      120, "e"),
            "iva":        ("IVA",              95, "e"),
            "total":      ("Total",           110, "e"),
            "situacao":   ("Situação",         90, "w"),
        }
        for col, (label, width, anchor) in cfg.items():
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=width, anchor=anchor, minwidth=40)

        self.tree.tag_configure("nota_credito", foreground="#b71c1c")
        self.tree.tag_configure("fatura",       foreground="#1a1a1a")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ── rodapé com totais ─────────────────────────────────────────
        rodape = tk.Frame(outer, bg=self.BG)
        rodape.pack(fill="x", pady=(4, 0))

        self.lbl_totais = tk.Label(
            rodape, text="", bg=self.BG, fg=self.FG,
            font=("Segoe UI", 9, "bold"), anchor="e",
        )
        self.lbl_totais.pack(fill="x")

        self._ord_col = "data"
        self._ord_asc = False

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _popular_filtros(self):
        self._fornecedores = self.controller.get_fornecedores()
        forn_vals = ["Todos"] + [
            f"{f.nome}  [{f.nif or '—'}]" for f in self._fornecedores
        ]
        self.cb_forn["values"] = forn_vals
        self.cb_forn.current(0)

        anos = ["Todos"] + [str(a) for a in self.controller.get_anos_faturacao()]
        self.cb_ano["values"] = anos
        self.cb_ano.current(0)

        mes_vals = ["Todos"] + [f"{m:02d} — {MESES[m]}" for m in range(1, 13)]
        self.cb_mes["values"] = mes_vals
        self.cb_mes.current(0)

        tipos = ["Todos"] + self.controller.get_tipos_faturacao()
        self.cb_tipo["values"] = tipos
        self.cb_tipo.current(0)

    def _limpar_filtros(self):
        self.cb_forn.current(0)
        self.cb_ano.current(0)
        self.cb_mes.current(0)
        self.cb_tipo.current(0)
        self._filtrar()

    def _filtrar(self):
        forn_idx = self.cb_forn.current()
        fid  = self._fornecedores[forn_idx - 1].id if forn_idx > 0 else None

        ano_str = self.cb_ano.get()
        ano  = int(ano_str) if ano_str != "Todos" else None

        mes_str = self.cb_mes.get()
        mes  = int(mes_str.split("—")[0].strip()) if mes_str != "Todos" else None

        tipo_str = self.cb_tipo.get()
        tipo = tipo_str if tipo_str != "Todos" else None

        self._dados = self.controller.get_documentos_faturacao(
            fornecedor_id=fid, ano=ano, mes=mes, tipo=tipo
        )
        self._preencher_tree()

    # ------------------------------------------------------------------
    # Treeview
    # ------------------------------------------------------------------

    def _preencher_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.lbl_totais.config(text="")
        self.lbl_contagem.config(text="")

        if not self._dados:
            self.lbl_totais.config(text="Sem documentos para os filtros seleccionados.")
            return

        col_key = {
            "data":       "data_emissao",
            "numero":     "numero_documento",
            "fornecedor": "fornecedor_nome",
            "tipo":       "tipo",
            "base":       "base_tributavel",
            "iva":        "iva",
            "total":      "total",
            "situacao":   "situacao",
        }
        _numeric = {"base", "iva", "total"}
        if self._ord_col in _numeric:
            _key = lambda r: float(r.get(col_key[self._ord_col]) or 0)
        else:
            _key = lambda r: str(r.get(col_key[self._ord_col]) or "")
        dados = sorted(self._dados, key=_key, reverse=not self._ord_asc)

        tot_base = tot_iva = tot_total = 0.0
        for r in dados:
            tipo = (r.get("tipo") or "").lower()
            tag  = "nota_credito" if "crédito" in tipo or "credito" in tipo else "fatura"
            self.tree.insert("", "end", tags=(tag,), values=(
                r.get("data_emissao") or "",
                r.get("numero_documento") or "",
                r.get("fornecedor_nome") or r.get("nome_emitente") or "",
                r.get("tipo") or "",
                f"{r.get('base_tributavel', 0):,.2f} €",
                f"{r.get('iva', 0):,.2f} €",
                f"{r.get('total', 0):,.2f} €",
                r.get("situacao") or "",
            ))
            tot_base  += r.get("base_tributavel", 0)
            tot_iva   += r.get("iva", 0)
            tot_total += r.get("total", 0)

        n = len(dados)
        self.lbl_contagem.config(text=f"{n} documento{'s' if n != 1 else ''}")
        self.lbl_totais.config(
            text=(
                f"Base tributável  {tot_base:,.2f} €     "
                f"IVA  {tot_iva:,.2f} €     "
                f"Total  {tot_total:,.2f} €"
            )
        )

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._preencher_tree()

    # ------------------------------------------------------------------
    # Importação
    # ------------------------------------------------------------------

    def _importar(self):
        path = self.ask_file(
            title="Selecionar E_Fatura.xls",
            filetypes=[("Excel", "*.xls *.xlsx"), ("Todos os ficheiros", "*.*")],
        )
        if not path:
            return
        self.controller.importar_efatura(path)
        self._popular_filtros()
        self._filtrar()

    def _apagar_sem_data(self):
        if not self.confirm("Apagar sem data",
                            "Apagar todos os documentos sem data de emissão?\n"
                            "Esta operação não pode ser desfeita."):
            return
        try:
            n = self.controller.limpar_sem_data()
            self.informuser("Concluído", f"{n} documento(s) sem data removido(s).")
            self._popular_filtros()
            self._filtrar()
        except Exception as e:
            self.informuser("Erro", str(e), tipo="error")
