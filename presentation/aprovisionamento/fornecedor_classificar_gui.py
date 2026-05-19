# atrpt/presentation/aprovisionamento/fornecedor_classificar_gui.py
"""
View de classificação e reclassificação de fornecedores.

Permite:
  - Ver todos os fornecedores numa treeview com filtro por tipo de relação
  - Seleccionar um ou vários (Ctrl/Shift+clique)
  - Mover os seleccionados para: Prestador | Avençado | Pontual | Suspenso
  - Editar individualmente com duplo clique
"""

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG

from domain.aprovisionamento.fornecedor import TIPOS_FORNECEDOR, TIPOS_RELACAO

# Categorias destino com cor de etiqueta na treeview
CATEGORIAS = {
    "Prestador":   "#1a6bbf",   # azul
    "Avençado":    "#2e7d32",   # verde
    "Pontual":     "#e65100",   # laranja
    "Suspenso":    "#b71c1c",   # vermelho
    "Contrato":    "#6a1b9a",   # roxo
    "Preferencial":"#00695c",   # verde-azulado
}


class FornecedorClassificarGUI(BG):
    """
    Sub-view integrada no sistema de navegação (show_view).
    Acedida via FornecedoresGUI → 'Classificar Fornecedores'.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._fornecedores = []          # lista completa em memória
        self._fornecedor_por_iid: dict[str, object] = {}

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar()

    # ── construção ────────────────────────────────────────────────────────────

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)

        # ── barra de filtros ──────────────────────────────────────────
        barra = tk.Frame(outer, bg=self.BG)
        barra.pack(fill="x", pady=(0, 4))

        tk.Label(barra, text="Filtrar por relação:", bg=self.BG, fg=self.FG).pack(side="left")

        self.cb_filtro = ttk.Combobox(
            barra,
            values=["Todos"] + TIPOS_RELACAO + ["Sem relação"],
            state="readonly", width=14,
        )
        self.cb_filtro.set("Todos")
        self.cb_filtro.pack(side="left", padx=(4, 16))
        self.cb_filtro.bind("<<ComboboxSelected>>", lambda e: self._aplicar_filtro())

        tk.Label(barra, text="Pesquisa:", bg=self.BG, fg=self.FG).pack(side="left")
        self.ent_pesquisa = ttk.Entry(barra, width=28)
        self.ent_pesquisa.pack(side="left", padx=(4, 8))
        self.ent_pesquisa.bind("<KeyRelease>", lambda e: self._aplicar_filtro())

        ttk.Button(barra, text="↺ Recarregar", command=self._carregar).pack(side="left", padx=(8, 0))

        # contador
        self.lbl_contador = tk.Label(barra, text="", bg=self.BG, fg=self.FG)
        self.lbl_contador.pack(side="right")

        # ── treeview ──────────────────────────────────────────────────
        tree_frame = tk.Frame(outer, bg=self.BG)
        tree_frame.pack(fill="both", expand=True)

        cols = ("nome", "nif", "tipo", "relacao", "email", "pagamento")
        self.tree = ttk.Treeview(
            tree_frame, columns=cols, show="headings",
            selectmode="extended",    # permite Ctrl+clique e Shift+clique
            height=18,
        )
        headers = {
            "nome":      ("Nome",        240),
            "nif":       ("NIF",          90),
            "tipo":      ("Tipo",        130),
            "relacao":   ("Relação",     100),
            "email":     ("Email",       180),
            "pagamento": ("Pagamento",    75),
        }
        for col, (label, width) in headers.items():
            self.tree.heading(col, text=label,
                              command=lambda c=col: self._ordenar(c))
            self.tree.column(col, width=width, anchor="w", minwidth=40)

        # tags de cor por tipo de relação
        for rel, cor in CATEGORIAS.items():
            self.tree.tag_configure(rel, foreground=cor)
        self.tree.tag_configure("sem_relacao", foreground="gray")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.bind("<Double-1>", self._on_dblclick)

        # ── painel de acções em lote ──────────────────────────────────
        acoes = tk.Frame(outer, bg=self.BG)
        acoes.pack(fill="x", pady=(6, 0))

        tk.Label(
            acoes,
            text="Mover seleccionados para →",
            bg=self.BG, fg=self.FG,
            font=self.FONT_SUB,
        ).pack(side="left", padx=(0, 8))

        for categoria, cor in CATEGORIAS.items():
            tk.Button(
                acoes,
                text=categoria,
                bg=self.BTN_BG, fg=cor,
                font=self.FONT_BUTTON,
                relief="raised",
                command=lambda c=categoria: self._mover_seleccionados(c),
            ).pack(side="left", padx=3)

        tk.Label(acoes, text="  |  Duplo clique para editar individualmente",
                 bg=self.BG, fg="gray", font=("Segoe UI", 8)).pack(side="left")

        # ordenação
        self._ord_col = "nome"
        self._ord_asc = True

    # ── dados ─────────────────────────────────────────────────────────────────

    def _carregar(self):
        self._fornecedores = self.controller.get_fornecedores() or []
        self._aplicar_filtro()

    def _aplicar_filtro(self):
        filtro_rel  = self.cb_filtro.get()
        pesquisa    = self.ent_pesquisa.get().strip().lower()

        visíveis = []
        for f in self._fornecedores:
            # filtro por relação
            rel = (f.tipo_relacao or "").strip()
            if filtro_rel == "Sem relação" and rel:
                continue
            if filtro_rel not in ("Todos", "Sem relação") and rel != filtro_rel:
                continue
            # pesquisa livre (nome ou NIF)
            if pesquisa:
                haystack = f"{f.nome} {f.nif or ''}".lower()
                if pesquisa not in haystack:
                    continue
            visíveis.append(f)

        # ordenar
        rev = not self._ord_asc
        visíveis.sort(
            key=lambda f: (getattr(f, self._ord_col.replace("relacao", "tipo_relacao")
                                              .replace("tipo", "tipo_fornecedor")
                                              .replace("pagamento", "metodo_pagamento"), "") or "").lower(),
            reverse=rev,
        )

        self._preencher_tree(visíveis)
        self.lbl_contador.config(
            text=f"{len(visíveis)} de {len(self._fornecedores)} fornecedores"
        )

    def _preencher_tree(self, fornecedores):
        self.tree.delete(*self.tree.get_children())
        self._fornecedor_por_iid.clear()
        for f in fornecedores:
            rel = (f.tipo_relacao or "").strip()
            tag = rel if rel in CATEGORIAS else "sem_relacao"
            iid = self.tree.insert("", "end", tags=(tag,), values=(
                f.nome,
                f.nif            or "",
                f.tipo_fornecedor or "",
                rel              or "—",
                f.email          or "",
                f.metodo_pagamento or "",
            ))
            self._fornecedor_por_iid[iid] = f

    # ── ordenação por coluna ──────────────────────────────────────────────────

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._aplicar_filtro()

    # ── acções ────────────────────────────────────────────────────────────────

    def _mover_seleccionados(self, nova_relacao: str):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning(
                "Sem selecção",
                "Seleccione pelo menos um fornecedor na lista.",
                parent=self.root,
            )
            return

        nomes = [self._fornecedor_por_iid[iid].nome for iid in sel]
        resumo = "\n".join(f"  • {n}" for n in nomes[:10])
        if len(nomes) > 10:
            resumo += f"\n  … e mais {len(nomes)-10}"

        if not messagebox.askyesno(
            "Confirmar",
            f"Mover {len(sel)} fornecedor(es) para '{nova_relacao}'?\n\n{resumo}",
            parent=self.root,
        ):
            return

        erros = []
        for iid in sel:
            f = self._fornecedor_por_iid[iid]
            try:
                self.controller.editar_fornecedor({
                    "id":          f.id,
                    "nome":        f.nome,
                    "nif":         f.nif,
                    "email":       f.email,
                    "iban":        f.iban,
                    "tipo_fornecedor":  f.tipo_fornecedor,
                    "tipo_relacao":     nova_relacao,
                    "metodo_pagamento": f.metodo_pagamento,
                    "setor":            f.setor,
                    "comercial_nome":          f.comercial_nome,
                    "comercial_email":         f.comercial_email,
                    "comercial_telemovel":     f.comercial_telemovel,
                    "administrativo_nome":     f.administrativo_nome,
                    "administrativo_email":    f.administrativo_email,
                    "administrativo_telemovel":f.administrativo_telemovel,
                })
                # actualizar objecto em memória
                f.tipo_relacao = nova_relacao
            except Exception as e:
                erros.append(f"{f.nome}: {e}")

        if erros:
            messagebox.showerror("Erros", "\n".join(erros), parent=self.root)

        self._aplicar_filtro()

        messagebox.showinfo(
            "Concluído",
            f"{len(sel) - len(erros)} fornecedor(es) movidos para '{nova_relacao}'.",
            parent=self.root,
        )

    # ── edição individual ─────────────────────────────────────────────────────

    def _on_dblclick(self, event):
        sel = self.tree.selection()
        if not sel:
            return
        f = self._fornecedor_por_iid[sel[0]]
        self._abrir_edicao(f)

    def _abrir_edicao(self, f):
        win = tk.Toplevel(self.root)
        win.title(f"Editar — {f.nome}")
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        def _lbl(row, texto):
            ttk.Label(frame, text=texto).grid(
                row=row, column=0, sticky="w", pady=3, padx=(0, 8))

        def _ent(row, valor, width=36):
            e = ttk.Entry(frame, width=width)
            e.insert(0, valor or "")
            e.grid(row=row, column=1, sticky="w", pady=3)
            return e

        def _sep(row, titulo=None):
            if titulo:
                ttk.Label(frame, text=titulo,
                          font=("Segoe UI", 9, "bold")).grid(
                    row=row, column=0, columnspan=2, sticky="w", pady=(6, 1))
                row += 1
            ttk.Separator(frame, orient="horizontal").grid(
                row=row, column=0, columnspan=2, sticky="ew", pady=(0, 4))
            return row + 1

        r = 0
        _lbl(r, "Nome:");         ent_nome  = _ent(r, f.nome);          r += 1
        _lbl(r, "NIF:");
        lbl_nif = tk.Label(frame, text=f.nif or "—",
                           relief="sunken", padx=4, anchor="w", width=14)
        lbl_nif.grid(row=r, column=1, sticky="w", pady=3);              r += 1
        _lbl(r, "Email:");        ent_email = _ent(r, f.email);          r += 1
        _lbl(r, "IBAN:");         ent_iban  = _ent(r, f.iban);           r += 1

        _lbl(r, "Tipo fornecedor:")
        cb_tipo = ttk.Combobox(frame, values=TIPOS_FORNECEDOR,
                               state="readonly", width=20)
        cb_tipo.set(f.tipo_fornecedor or "")
        cb_tipo.grid(row=r, column=1, sticky="w", pady=3);              r += 1

        _lbl(r, "Relação:")
        cb_rel = ttk.Combobox(frame, values=TIPOS_RELACAO,
                              state="readonly", width=14)
        cb_rel.set(f.tipo_relacao or "")
        cb_rel.grid(row=r, column=1, sticky="w", pady=3);              r += 1

        _lbl(r, "Pagamento:")
        cb_pag = ttk.Combobox(frame, values=["TB", "DD", "MB", "OU"],
                              state="readonly", width=8)
        cb_pag.set(f.metodo_pagamento or "")
        cb_pag.grid(row=r, column=1, sticky="w", pady=3);              r += 1

        _lbl(r, "Atividade:")
        ent_ativ = _ent(r, getattr(f, "atividade", "") or "");         r += 1

        r = _sep(r, "Contacto Comercial")
        _lbl(r, "Nome:");   ent_c1n = _ent(r, f.comercial_nome);       r += 1
        _lbl(r, "Email:");  ent_c1e = _ent(r, f.comercial_email);      r += 1
        _lbl(r, "Telm:");   ent_c1t = _ent(r, f.comercial_telemovel);  r += 1

        r = _sep(r, "Contacto Administrativo")
        _lbl(r, "Nome:");   ent_c2n = _ent(r, f.administrativo_nome);       r += 1
        _lbl(r, "Email:");  ent_c2e = _ent(r, f.administrativo_email);      r += 1
        _lbl(r, "Telm:");   ent_c2t = _ent(r, f.administrativo_telemovel);  r += 1

        ttk.Separator(frame, orient="horizontal").grid(
            row=r, column=0, columnspan=2, sticky="ew", pady=6);        r += 1

        def _gravar():
            nome = ent_nome.get().strip()
            if not nome:
                messagebox.showerror("Erro", "O nome é obrigatório.", parent=win)
                return
            dados = {
                "id":                      f.id,
                "nome":                    nome,
                "nif":                     f.nif,          # NIF imutável aqui
                "email":                   ent_email.get().strip() or None,
                "iban":                    ent_iban.get().strip()  or None,
                "tipo_fornecedor":         cb_tipo.get() or None,
                "tipo_relacao":            cb_rel.get()  or None,
                "metodo_pagamento":        cb_pag.get()  or None,
                "atividade":              ent_ativ.get().strip() or None,
                "setor":                   f.setor,
                "comercial_nome":          ent_c1n.get().strip() or None,
                "comercial_email":         ent_c1e.get().strip() or None,
                "comercial_telemovel":     ent_c1t.get().strip() or None,
                "administrativo_nome":     ent_c2n.get().strip() or None,
                "administrativo_email":    ent_c2e.get().strip() or None,
                "administrativo_telemovel":ent_c2t.get().strip() or None,
            }
            try:
                self.controller.editar_fornecedor(dados)
                # actualizar objecto em memória
                for campo, valor in dados.items():
                    if hasattr(f, campo):
                        setattr(f, campo, valor)
                self._aplicar_filtro()
                win.destroy()
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=win)

        bf = ttk.Frame(frame)
        bf.grid(row=r, column=0, columnspan=2, pady=8)
        ttk.Button(bf, text="Gravar",   command=_gravar).pack(side="left", padx=5)
        ttk.Button(bf, text="Cancelar", command=win.destroy).pack(side="left", padx=5)

        ent_nome.focus_set()
