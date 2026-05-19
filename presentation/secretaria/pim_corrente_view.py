# presentation/secretaria/pim_corrente_view.py
#
# Vista do PIM em curso: lê pim_historico (SQLite) e mostra por período.

import sqlite3
import tkinter as tk
from tkinter import ttk, messagebox

from presentation.shared.base_gui import BaseGui as BG

_MESES_PT = [
    "", "Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
    "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro",
]

_TREE_COLS = [
    ("numero_residente", "Nº",         50),
    ("nome",             "Nome",      200),
    ("atual",            "Atual",      80),
    ("anterior",         "Anterior",   80),
    ("recebido",         "Recebido",   80),
    ("saldo",            "Saldo",      80),
    ("data",             "Data Pag.",  90),
]

_NUMERIC_COLS = {"atual", "anterior", "recebido", "saldo"}

_SQL_PERIODOS = """
    SELECT DISTINCT ano, mes
    FROM pim_historico
    ORDER BY ano DESC, mes DESC
"""

_SQL_DADOS = """
    SELECT p.numero_residente,
           COALESCE(r.nome, '') AS nome,
           p.atual,
           p.anterior,
           p.recebido,
           p.saldo,
           p.data
    FROM pim_historico p
    LEFT JOIN residentes r ON r.numero_residente = p.numero_residente
    WHERE p.ano = ? AND p.mes = ?
    ORDER BY nome
"""


class PimCorrenteView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._dados: list[dict] = []
        self._ord_col = "nome"
        self._ord_asc = True

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar_periodos()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame_work, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── barra de controlo ─────────────────────────────────────────
        ctrl = tk.LabelFrame(outer, text="Período / Filtro", bg=self.BG,
                             fg=self.FG, font=("Segoe UI", 8, "bold"))
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        f = tk.Frame(ctrl, bg=self.BG)
        f.pack(fill="x", padx=6, pady=4)

        def lbl(txt):
            tk.Label(f, text=txt, bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 8)).pack(side="left")

        lbl("Período:")
        self.cb_periodo = ttk.Combobox(f, state="readonly", width=18)
        self.cb_periodo.pack(side="left", padx=(3, 16))
        self.cb_periodo.bind("<<ComboboxSelected>>", lambda _: self._carregar_dados())

        lbl("Nome:")
        self.ent_pesq = tk.Entry(f, width=24)
        self.ent_pesq.pack(side="left", padx=(3, 10))
        self.ent_pesq.bind("<Return>", lambda _: self._filtrar())

        tk.Button(f, text="Filtrar", command=self._filtrar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="Limpar",  command=self._limpar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="← Menu",  command=self._voltar_menu,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=10).pack(side="right", padx=6)

        # ── totais ────────────────────────────────────────────────────
        tots = tk.Frame(outer, bg=self.BG)
        tots.grid(row=1, column=0, sticky="ew", pady=(0, 4))

        self.lbl_totais = tk.Label(tots, text="", bg=self.BG, fg=self.FG,
                                   font=("Segoe UI", 8))
        self.lbl_totais.pack(side="left", padx=4)

        # ── lista ─────────────────────────────────────────────────────
        frame_tree = tk.Frame(outer, bg=self.BG)
        frame_tree.grid(row=2, column=0, sticky="nsew")
        frame_tree.rowconfigure(0, weight=1)
        frame_tree.columnconfigure(0, weight=1)

        cols = [c for c, *_ in _TREE_COLS]
        self.tree = ttk.Treeview(frame_tree, columns=cols,
                                  show="headings", selectmode="browse")
        for cid, label, w in _TREE_COLS:
            self.tree.heading(cid, text=label,
                              command=lambda c=cid: self._ordenar(c))
            anchor = "e" if cid in _NUMERIC_COLS else "w"
            self.tree.column(cid, width=w, anchor=anchor, minwidth=40)

        vsb = ttk.Scrollbar(frame_tree, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("alt", background="#f5f0e8")
        self.tree.tag_configure("sem_saldo", foreground="#888888")

        # ── rodapé com contagem ───────────────────────────────────────
        self.lbl_count = tk.Label(outer, text="", bg=self.BG,
                                  font=("Segoe UI", 8), anchor="w")
        self.lbl_count.grid(row=3, column=0, sticky="w", pady=(4, 0))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _db_path(self) -> str:
        return str(self.controller.cfg.paths["atrpt_db"])

    def _garantir_schema(self):
        """Adiciona coluna 'anterior' a pim_historico se ainda não existir."""
        try:
            with sqlite3.connect(self._db_path()) as conn:
                cols = {r[1] for r in conn.execute(
                    "PRAGMA table_info(pim_historico)"
                ).fetchall()}
                if cols and "anterior" not in cols:
                    conn.execute("ALTER TABLE pim_historico ADD COLUMN anterior REAL")
        except Exception:
            pass

    def _carregar_periodos(self):
        self._garantir_schema()
        try:
            with sqlite3.connect(self._db_path()) as conn:
                rows = conn.execute(_SQL_PERIODOS).fetchall()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler períodos:\n{e}",
                                 parent=self.root)
            return

        if not rows:
            self.cb_periodo["values"] = []
            self.lbl_count.config(text="Sem dados em pim_historico.")
            return

        labels = [f"{_MESES_PT[m]} {a}" for a, m in rows]
        self._periodos = rows   # [(ano, mes), ...]
        self.cb_periodo["values"] = labels
        self.cb_periodo.current(0)
        self._carregar_dados()

    def _carregar_dados(self):
        idx = self.cb_periodo.current()
        if idx < 0:
            return
        ano, mes = self._periodos[idx]
        try:
            with sqlite3.connect(self._db_path()) as conn:
                cur = conn.execute(_SQL_DADOS, (ano, mes))
                cols = [d[0] for d in cur.description]
                self._dados = [dict(zip(cols, row)) for row in cur.fetchall()]
        except Exception as e:
            messagebox.showerror("Erro", f"Erro ao ler PIM:\n{e}", parent=self.root)
            return
        self._filtrar()

    def _filtrar(self):
        pesq = self.ent_pesq.get().strip().lower()
        filtrado = [
            d for d in self._dados
            if not pesq or pesq in (d.get("nome") or "").lower()
        ]
        filtrado.sort(
            key=lambda d: str(d.get(self._ord_col) or "").lower(),
            reverse=not self._ord_asc,
        )
        self._preencher_tree(filtrado)

    def _limpar(self):
        self.ent_pesq.delete(0, "end")
        self._filtrar()

    @staticmethod
    def _fmt(v, col: str) -> str:
        if v is None:
            return ""
        if col in _NUMERIC_COLS:
            try:
                return f"{float(v):.2f}"
            except (TypeError, ValueError):
                return ""
        if col == "numero_residente":
            try:
                return str(int(v))
            except (TypeError, ValueError):
                return str(v)
        return str(v).strip()

    def _preencher_tree(self, dados: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for i, d in enumerate(dados):
            vals = tuple(self._fmt(d.get(cid), cid) for cid, *_ in _TREE_COLS)
            sem_saldo = d.get("saldo") in (None, 0, 0.0) and d.get("atual") in (None, 0, 0.0)
            tag = "sem_saldo" if sem_saldo else ("alt" if i % 2 else "")
            self.tree.insert("", "end", values=vals, tags=(tag,))

        # totais
        def _soma(col):
            return sum(
                float(d[col]) for d in dados
                if d.get(col) is not None
            )
        try:
            t_atual    = _soma("atual")
            t_recebido = _soma("recebido")
            t_saldo    = _soma("saldo")
            self.lbl_totais.config(
                text=(f"Atual: {t_atual:.2f}   "
                      f"Recebido: {t_recebido:.2f}   "
                      f"Saldo: {t_saldo:.2f}")
            )
        except Exception:
            self.lbl_totais.config(text="")

        self.lbl_count.config(text=f"{len(dados)} residente(s)")

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._filtrar()

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _voltar_menu(self):
        getattr(self, '_root_gui', self).go_back()
