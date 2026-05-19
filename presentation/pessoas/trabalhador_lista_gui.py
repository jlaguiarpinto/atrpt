# atrpt/presentation/pessoas/trabalhador_lista_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG
import logging

logger = logging.getLogger(__name__)

_SITUACOES = [
    ("Em serviço",  "EM_SERVICO"),
    ("Ativos",      "A"),
    ("Candidatos",  "C"),
    ("Inativos",    "I"),
    ("Todos",       None),
]
_SIT_LABEL = {
    'A': 'Ativo', 'I': 'Inativo', 'B': 'Baixa',
    'L': 'Licença', 'S': 'Suspensão', 'P': 'Pré-reforma', 'C': 'Candidato',
}

_COLS = ("Num", "Nome", "Situação", "Local", "Sector",
         "Categoria Atual", "Admissão", "Antiguidade", "Vencimento")
_HEADERS = {
    "Num":             ("Nº",               50),
    "Nome":            ("Nome",            220),
    "Situação":        ("Situação",          90),
    "Local":           ("Local",             80),
    "Sector":          ("Sector",           140),
    "Categoria Atual": ("Categoria Atual",  200),
    "Admissão":        ("Admissão",          90),
    "Antiguidade":     ("Antiguidade",        80),
    "Vencimento":      ("Vencimento",         90),
}


class TrabalhadorListaGUI(BG):
    """Vista de listagem de trabalhadores com filtro por situação e edição."""

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._iid_map = {}

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()

    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.columnconfigure(0, weight=1)
        outer.rowconfigure(1, weight=1)

        # ── barra de controlo ─────────────────────────────────────────
        barra = tk.Frame(outer, bg=self.BG)
        barra.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        tk.Label(barra, text="Situação:", bg=self.BG, fg=self.FG).pack(side="left")
        self._var_sit = tk.StringVar(value=_SITUACOES[0][0])
        cb = ttk.Combobox(barra, textvariable=self._var_sit,
                          values=[s[0] for s in _SITUACOES],
                          state="readonly", width=14)
        cb.pack(side="left", padx=(4, 12))
        cb.bind("<<ComboboxSelected>>", lambda e: self._recarregar())

        self._btn_editar = tk.Button(barra, text="Editar ficha",
                                     command=self._editar_seleccionado,
                                     font=self.FONT_BUTTON, bg=self.BTN_BG,
                                     state="disabled")
        self._btn_editar.pack(side="right", padx=4)

        self._lbl_count = tk.Label(barra, text="", bg=self.BG, fg="gray")
        self._lbl_count.pack(side="right", padx=8)

        # ── treeview ──────────────────────────────────────────────────
        tree_frame = tk.Frame(outer, bg=self.BG)
        tree_frame.grid(row=1, column=0, sticky="nsew")
        tree_frame.columnconfigure(0, weight=1)
        tree_frame.rowconfigure(0, weight=1)

        self._tree = ttk.Treeview(tree_frame, columns=_COLS, show="headings")
        self._tree.tag_configure("inativo",   foreground="gray")
        self._tree.tag_configure("candidato", foreground="#1a6e99")

        for col in _COLS:
            lbl, width = _HEADERS[col]
            self._tree.heading(col, text=lbl)
            self._tree.column(col, width=width, anchor="w")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ordenação por coluna
        _col_num    = {"Num", "Antiguidade"}
        _sort_state = {"col": None, "rev": False}

        def _ordenar(col):
            rev = not _sort_state["rev"] if _sort_state["col"] == col else False
            _sort_state.update({"col": col, "rev": rev})
            for c in _COLS:
                lbl, _ = _HEADERS[c]
                self._tree.heading(c, text=lbl)
            lbl_col, _ = _HEADERS[col]
            self._tree.heading(col, text=lbl_col + (" ▲" if not rev else " ▼"))

            def _chave(iid):
                val = self._tree.set(iid, col)
                if col in _col_num:
                    try:
                        return int(val)
                    except Exception:
                        return 0
                if col == "Vencimento":
                    try:
                        return float(val.replace(",", "").replace(" ", ""))
                    except Exception:
                        return 0.0
                return val.lower()

            itens = sorted(self._tree.get_children(), key=_chave, reverse=rev)
            for i, iid in enumerate(itens):
                self._tree.move(iid, "", i)

        for col in _COLS:
            self._tree.heading(col, command=lambda c=col: _ordenar(c))

        self._tree.bind("<<TreeviewSelect>>", self._on_select)
        self._tree.bind("<Double-1>", lambda e: self._editar_seleccionado())

        # ── rodapé ────────────────────────────────────────────────────
        tk.Label(outer, text="Duplo-clique ou botão Editar ficha para abrir a ficha",
                 bg=self.BG, fg="gray").grid(row=2, column=0, sticky="w", pady=(2, 0))

        self._recarregar()

    # ------------------------------------------------------------------

    def _situacao_key(self):
        label = self._var_sit.get()
        for lbl, key in _SITUACOES:
            if lbl == label:
                return key
        return None

    def _recarregar(self):
        dados = self.controller.get_trabalhadores(situacao=self._situacao_key())
        self._popular(dados)

    def _popular(self, dados):
        self._tree.delete(*self._tree.get_children())
        self._iid_map.clear()
        self._btn_editar.config(state="disabled")
        for e in dados:
            sit = e.ativo
            tag = "inativo" if sit == 'I' else ("candidato" if sit == 'C' else "")
            iid = self._tree.insert("", "end", tags=(tag,), values=(
                e.numero,
                e.nome,
                _SIT_LABEL.get(sit, sit),
                e.local or "",
                e.sector or "",
                e.categoria_atual or "",
                e.data_admissao.strftime("%Y-%m-%d") if e.data_admissao else "",
                e.antiguidade if e.antiguidade is not None else "",
                f"{e.vencimento:,.2f}" if e.vencimento else "",
            ))
            self._iid_map[iid] = e
        n = len(dados)
        self._lbl_count.config(text=f"{n} trabalhador{'es' if n != 1 else ''}")

    def _on_select(self, event=None):
        sel = self._tree.selection()
        self._btn_editar.config(state="normal" if sel else "disabled")

    def _editar_seleccionado(self):
        sel = self._tree.selection()
        if not sel:
            return
        e = self._iid_map.get(sel[0])
        if not e:
            return
        from presentation.pessoas.empregado_edicao_gui import EmpregadoEdicaoGUI
        EmpregadoEdicaoGUI(
            self.root, self.controller, e,
            on_save=lambda updated: self._after_save(updated, sel[0]),
        )

    def _after_save(self, e, iid):
        self._iid_map[iid] = e
        sit = e.ativo
        tag = "inativo" if sit == 'I' else ("candidato" if sit == 'C' else "")
        self._tree.item(iid, tags=(tag,), values=(
            e.numero,
            e.nome,
            _SIT_LABEL.get(sit, sit),
            e.local or "",
            e.sector or "",
            e.categoria_atual or "",
            e.data_admissao.strftime("%Y-%m-%d") if e.data_admissao else "",
            e.antiguidade if e.antiguidade is not None else "",
            f"{e.vencimento:,.2f}" if e.vencimento else "",
        ))
