# presentation/fornecedores/analise_fornecedores_gui.py
#
# Vista de análise de fornecedores.
# Painel superior : lista de fornecedores com filtros e média anual de faturação.
# Painel inferior : histórico mensal do fornecedor seleccionado.

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG

MESES = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun",
         "Jul", "Ago", "Set", "Out", "Nov", "Dez"]

from domain.aprovisionamento.fornecedor import TIPOS_FORNECEDOR, TIPOS_RELACAO


class AnaliseFornecedoresGUI(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._dados: list[dict] = []
        self._ord_col = "nome"
        self._ord_asc = True

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._popular_filtros()
        self._filtrar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── barra de filtros ──────────────────────────────────────────
        filtros = tk.LabelFrame(outer, text="Filtros", bg=self.BG,
                                fg=self.FG, font=("Segoe UI", 8, "bold"))
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        f1 = tk.Frame(filtros, bg=self.BG)
        f1.pack(fill="x", padx=6, pady=4)

        def _lbl(txt):
            tk.Label(f1, text=txt, bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 8)).pack(side="left")

        _lbl("Tipo:")
        self.cb_tipo = ttk.Combobox(f1, state="readonly", width=22)
        self.cb_tipo.pack(side="left", padx=(3, 14))

        _lbl("Relação:")
        self.cb_relacao = ttk.Combobox(f1, state="readonly", width=18)
        self.cb_relacao.pack(side="left", padx=(3, 14))

        _lbl("Setor:")
        self.cb_setor = ttk.Combobox(f1, state="readonly", width=18)
        self.cb_setor.pack(side="left", padx=(3, 14))

        tk.Button(f1, text="Filtrar", command=self._filtrar,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left", padx=(0, 6))
        tk.Button(f1, text="Limpar", command=self._limpar_filtros,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left")

        self.lbl_contagem = tk.Label(f1, text="", bg=self.BG, fg=self.FG,
                                     font=("Segoe UI", 8))
        self.lbl_contagem.pack(side="right", padx=6)

        # ── painel duplo (vertical) ───────────────────────────────────
        pw = ttk.PanedWindow(outer, orient="vertical")
        pw.grid(row=1, column=0, sticky="nsew")

        # ── painel superior: tabela de fornecedores ───────────────────
        top = tk.Frame(pw, bg=self.BG)
        pw.add(top, weight=2)
        top.rowconfigure(0, weight=1)
        top.columnconfigure(0, weight=1)

        cols = ("nome", "nif", "tipo", "atividade", "relacao", "setor", "n_anos", "media_anual", "total")
        self.tree = ttk.Treeview(
            top, columns=cols, show="headings", selectmode="browse", height=12,
        )
        cfg = {
            "nome":        ("Fornecedor",      210, "w"),
            "nif":         ("NIF",              70, "center"),
            "tipo":        ("Tipo",            158, "w"),
            "atividade":   ("Atividade",       110, "w"),
            "relacao":     ("Relação",          82, "w"),
            "setor":       ("Setor",            82, "w"),
            "n_anos":      ("Anos",             44, "center"),
            "media_anual": ("Média Anual (€)", 110, "e"),
            "total":       ("Total (€)",       110, "e"),
        }
        for col, (lbl, w, anchor) in cfg.items():
            self.tree.heading(col, text=lbl,
                              command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=w, anchor=anchor, minwidth=40)

        self.tree.tag_configure("com_dados",  foreground="#1a3a5c")
        self.tree.tag_configure("sem_dados",  foreground="#999999")

        vsb_t = ttk.Scrollbar(top, orient="vertical",   command=self.tree.yview)
        hsb_t = ttk.Scrollbar(top, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb_t.set, xscrollcommand=hsb_t.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb_t.grid(row=0, column=1, sticky="ns")
        hsb_t.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<<TreeviewSelect>>", self._on_select)
        self.tree.bind("<Double-1>", self._on_double_click)

        # ── painel inferior: histórico do fornecedor seleccionado ─────
        bot = tk.Frame(pw, bg=self.BG)
        pw.add(bot, weight=1)
        bot.rowconfigure(1, weight=1)
        bot.columnconfigure(0, weight=1)

        self.lbl_historico_titulo = tk.Label(
            bot, text="Seleccione um fornecedor para ver o histórico",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 8, "bold"), anchor="w",
        )
        self.lbl_historico_titulo.grid(row=0, column=0, columnspan=2,
                                       sticky="ew", padx=4, pady=(4, 2))

        hist_frame = tk.Frame(bot, bg=self.BG)
        hist_frame.grid(row=1, column=0, sticky="nsew")
        hist_frame.rowconfigure(0, weight=1)
        hist_frame.columnconfigure(0, weight=1)

        hcols = ("ano", "mes", "n_docs", "base", "iva", "total_h")
        self.tree_hist = ttk.Treeview(
            hist_frame, columns=hcols, show="headings",
            selectmode="none", height=6,
        )
        hcfg = {
            "ano":     ("Ano",              65, "center"),
            "mes":     ("Mês",              65, "center"),
            "n_docs":  ("Docs",             50, "center"),
            "base":    ("Base Trib. (€)",  140, "e"),
            "iva":     ("IVA (€)",         110, "e"),
            "total_h": ("Total (€)",       120, "e"),
        }
        for col, (lbl, w, anchor) in hcfg.items():
            self.tree_hist.heading(col, text=lbl)
            self.tree_hist.column(col, width=w, anchor=anchor, minwidth=40)

        self.tree_hist.tag_configure("par",   background="#f5f5f5")
        self.tree_hist.tag_configure("impar", background="#ffffff")

        vsb_h = ttk.Scrollbar(hist_frame, orient="vertical", command=self.tree_hist.yview)
        self.tree_hist.configure(yscrollcommand=vsb_h.set)
        self.tree_hist.grid(row=0, column=0, sticky="nsew")
        vsb_h.grid(row=0, column=1, sticky="ns")

        vsb_h_col = ttk.Scrollbar(bot, orient="vertical", command=self.tree_hist.yview)
        vsb_h_col.grid(row=1, column=1, sticky="ns")
        self.tree_hist.configure(yscrollcommand=vsb_h_col.set)

        self.lbl_hist_totais = tk.Label(
            bot, text="", bg=self.BG, fg=self.FG,
            font=("Segoe UI", 8, "bold"), anchor="e",
        )
        self.lbl_hist_totais.grid(row=2, column=0, columnspan=2,
                                  sticky="ew", padx=4, pady=(2, 2))

    # ------------------------------------------------------------------
    # Filtros
    # ------------------------------------------------------------------

    def _popular_filtros(self):
        vals = self.controller.get_valores_filtro()
        for cb, key in (
            (self.cb_tipo,    "tipo_fornecedor"),
            (self.cb_relacao, "tipo_relacao"),
            (self.cb_setor,   "setor"),
        ):
            cb["values"] = ["Todos"] + vals.get(key, [])
            cb.current(0)

    def _limpar_filtros(self):
        for cb in (self.cb_tipo, self.cb_relacao, self.cb_setor):
            cb.current(0)
        self._filtrar()

    def _get_filtro(self, cb: ttk.Combobox) -> str | None:
        v = cb.get()
        return None if v == "Todos" else v

    def _filtrar(self):
        self._dados = self.controller.get_fornecedores_com_media_anual(
            tipo_fornecedor=self._get_filtro(self.cb_tipo),
            tipo_relacao=self._get_filtro(self.cb_relacao),
            setor=self._get_filtro(self.cb_setor),
        )
        self._preencher_tree()
        self._limpar_historico()

    # ------------------------------------------------------------------
    # Tabela de fornecedores
    # ------------------------------------------------------------------

    def _preencher_tree(self):
        self.tree.delete(*self.tree.get_children())

        col_key = {
            "nome":        "nome",
            "nif":         "nif",
            "tipo":        "tipo_fornecedor",
            "atividade":   "atividade",
            "relacao":     "tipo_relacao",
            "setor":       "setor",
            "n_anos":      "n_anos",
            "media_anual": "media_anual",
            "total":       "total_historico",
        }
        _num = {"n_anos", "media_anual", "total"}
        key_fn = (
            (lambda r: float(r.get(col_key[self._ord_col]) or 0))
            if self._ord_col in _num
            else (lambda r: (r.get(col_key[self._ord_col]) or "").lower())
        )
        dados = sorted(self._dados, key=key_fn, reverse=not self._ord_asc)

        for r in dados:
            tem = r["n_anos"] > 0
            tag = "com_dados" if tem else "sem_dados"
            self.tree.insert("", "end", iid=str(r["id"]), tags=(tag,), values=(
                r["nome"]            or "",
                r["nif"]             or "",
                r["tipo_fornecedor"] or "",
                r.get("atividade")   or "",
                r["tipo_relacao"]    or "",
                r["setor"]           or "",
                r["n_anos"]          or 0,
                f"{r['media_anual']:,.2f}" if tem else "—",
                f"{r['total_historico']:,.2f}" if tem else "—",
            ))

        n = len(dados)
        self.lbl_contagem.config(text=f"{n} fornecedor{'es' if n != 1 else ''}")

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._preencher_tree()

    # ------------------------------------------------------------------
    # Histórico do fornecedor seleccionado
    # ------------------------------------------------------------------

    def _on_select(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        forn_id = int(sel[0])
        forn = next((r for r in self._dados if r["id"] == forn_id), None)
        if not forn:
            return
        self._carregar_historico(forn_id, forn["nome"])

    def _carregar_historico(self, forn_id: int, nome: str):
        self.tree_hist.delete(*self.tree_hist.get_children())
        self.lbl_hist_totais.config(text="")
        self.lbl_historico_titulo.config(text=f"Histórico — {nome}")

        rows = self.controller.get_historico_faturacao(forn_id)
        if not rows:
            self.lbl_hist_totais.config(text="Sem histórico de faturação.")
            return

        rows = sorted(rows, key=lambda r: (r["ano"] or 0, r["mes"] or 0), reverse=True)

        tot_base = tot_iva = tot_total = 0.0
        anos_vistos: dict[int, int] = {}
        cor_idx = 0
        for r in rows:
            ano = r["ano"]
            if ano not in anos_vistos:
                anos_vistos[ano] = cor_idx % 2
                cor_idx += 1
            tag = "par" if anos_vistos[ano] == 0 else "impar"
            m = r["mes"]
            mes_nome = MESES[m - 1] if m and 1 <= m <= 12 else (str(m) if m else "—")
            self.tree_hist.insert("", "end", tags=(tag,), values=(
                ano or "—",
                mes_nome,
                r["n_documentos"],
                f"{r['base_tributavel']:,.2f}",
                f"{r['iva']:,.2f}",
                f"{r['total']:,.2f}",
            ))
            tot_base  += r["base_tributavel"]
            tot_iva   += r["iva"]
            tot_total += r["total"]

        n = len(rows)
        self.lbl_hist_totais.config(
            text=(
                f"{n} {'meses' if n != 1 else 'mês'}  |  "
                f"Base {tot_base:,.2f} €   "
                f"IVA {tot_iva:,.2f} €   "
                f"Total {tot_total:,.2f} €"
            )
        )

    def _on_double_click(self, event):
        item = self.tree.identify_row(event.y)
        if not item:
            return
        forn = next((r for r in self._dados if str(r["id"]) == item), None)
        if forn:
            self._editar_classificacao(forn)

    def _editar_classificacao(self, forn: dict):
        dlg = tk.Toplevel(self.frame)
        dlg.title(f"Classificar — {forn['nome']}")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.transient(self.frame)

        pad = {"padx": 10, "pady": 5}

        frm = tk.Frame(dlg, padx=16, pady=12)
        frm.pack(fill="both", expand=True)

        # helper
        def _row(frm, label, row):
            tk.Label(frm, text=label, anchor="w", width=10).grid(
                row=row, column=0, sticky="w", **pad)

        # Tipo
        _row(frm, "Tipo:", 0)
        cb_tipo = ttk.Combobox(frm, values=TIPOS_FORNECEDOR, width=28)
        cb_tipo.set(forn["tipo_fornecedor"] or "")
        cb_tipo.grid(row=0, column=1, sticky="w", **pad)

        # Atividade
        _row(frm, "Atividade:", 1)
        ent_atividade = ttk.Entry(frm, width=30)
        ent_atividade.insert(0, forn.get("atividade") or "")
        ent_atividade.grid(row=1, column=1, sticky="w", **pad)

        # Relação
        _row(frm, "Relação:", 2)
        cb_relacao = ttk.Combobox(frm, values=TIPOS_RELACAO, state="readonly", width=28)
        cb_relacao.set(forn["tipo_relacao"] or "")
        cb_relacao.grid(row=2, column=1, sticky="w", **pad)

        # Setor (combobox editável com valores existentes)
        _row(frm, "Setor:", 3)
        setores_bd = self.controller.get_valores_filtro().get("setor", [])
        cb_setor = ttk.Combobox(frm, values=setores_bd, width=28)
        cb_setor.set(forn["setor"] or "")
        cb_setor.grid(row=3, column=1, sticky="w", **pad)

        # botões
        btn_frm = tk.Frame(dlg)
        btn_frm.pack(fill="x", pady=(0, 10))

        resultado = {"ok": False, "tipo_fornecedor": None, "atividade": None,
                     "tipo_relacao": None, "setor": None}

        def _guardar():
            resultado["tipo_fornecedor"] = cb_tipo.get().strip()       or None
            resultado["atividade"]       = ent_atividade.get().strip() or None
            resultado["tipo_relacao"]    = cb_relacao.get().strip()    or None
            resultado["setor"]           = cb_setor.get().strip()      or None
            resultado["ok"] = True
            dlg.destroy()

        tk.Button(btn_frm, text="Guardar", width=10, command=_guardar,
                  default="active").pack(side="right", padx=(4, 12))
        tk.Button(btn_frm, text="Cancelar", width=10,
                  command=dlg.destroy).pack(side="right", padx=4)

        dlg.bind("<Return>", lambda _: _guardar())
        dlg.bind("<Escape>", lambda _: dlg.destroy())

        # centrar sobre a janela pai
        dlg.update_idletasks()
        px = self.frame.winfo_rootx() + (self.frame.winfo_width()  - dlg.winfo_width())  // 2
        py = self.frame.winfo_rooty() + (self.frame.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{px}+{py}")

        self.frame.wait_window(dlg)

        if not resultado["ok"]:
            return

        dados = {
            "id":              forn["id"],
            "tipo_fornecedor": resultado["tipo_fornecedor"],
            "atividade":       resultado["atividade"],
            "tipo_relacao":    resultado["tipo_relacao"],
            "setor":           resultado["setor"],
        }
        try:
            self.controller.editar_fornecedor(dados)
        except Exception as e:
            self.informuser("Erro", str(e), tipo="error")
            return

        # actualizar linha local sem recarregar tudo
        forn["tipo_fornecedor"] = dados["tipo_fornecedor"]
        forn["atividade"]       = dados["atividade"]
        forn["tipo_relacao"]    = dados["tipo_relacao"]
        forn["setor"]           = dados["setor"]
        self._preencher_tree()
        # manter selecção
        try:
            self.tree.selection_set(str(forn["id"]))
            self.tree.focus(str(forn["id"]))
        except Exception:
            pass

    def _limpar_historico(self):
        self.tree_hist.delete(*self.tree_hist.get_children())
        self.lbl_hist_totais.config(text="")
        self.lbl_historico_titulo.config(
            text="Seleccione um fornecedor para ver o histórico"
        )
