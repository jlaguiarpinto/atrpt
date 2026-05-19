# presentation/secretaria/pim_em_curso_view.py
#
# Vista do PIM em curso: lê pim_corrente (SQLite) via pim_repo.ler_pim().
# Sem selector de período — exibe sempre o ciclo activo.

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from pathlib import Path

from presentation.shared.base_gui import BaseGui as BG

_TREE_COLS = [
    ("numero_residente", "Nº",         50),
    ("nome",             "Nome",       200),
    ("especial",         "Especial",    56),
    ("anterior",         "Anterior",    80),
    ("atual",            "Atual",       80),
    ("total",            "Total",       80),
    ("recebido",         "Recebido",    80),
    ("saldo",            "Saldo",       80),
    ("data",             "Data Pag.",   90),
    ("data_envio_recibo","Envio Recibo",90),
]

_NUMERIC_COLS = {"anterior", "atual", "total", "recebido", "saldo"}


class PimEmCursoView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._dados: list[dict] = []
        self._ord_col = "nome"
        self._ord_asc = True

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame_work, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(2, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── barra de filtro ───────────────────────────────────────────
        ctrl = tk.LabelFrame(outer, text="Filtro", bg=self.BG,
                             fg=self.FG, font=("Segoe UI", 8, "bold"))
        ctrl.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        f = tk.Frame(ctrl, bg=self.BG)
        f.pack(fill="x", padx=6, pady=4)

        def lbl(txt):
            tk.Label(f, text=txt, bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 8)).pack(side="left")

        lbl("Nome:")
        self.ent_pesq = tk.Entry(f, width=28)
        self.ent_pesq.pack(side="left", padx=(3, 10))
        self.ent_pesq.bind("<Return>", lambda _: self._filtrar())

        tk.Button(f, text="Filtrar",   command=self._filtrar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="Limpar",    command=self._limpar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="Actualizar", command=self._carregar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=10).pack(side="left", padx=3)
        tk.Button(f, text="Importar PIM.xlsx", command=self._importar_pim,
                  font=("Segoe UI", 8), bg="#fff9c4", width=16).pack(side="left", padx=6)
        tk.Button(f, text="← Menu",   command=self._voltar_menu,
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
            self.tree.column(cid, width=w, anchor=anchor, minwidth=36)

        vsb = ttk.Scrollbar(frame_tree, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.tag_configure("alt",      background="#f5f0e8")
        self.tree.tag_configure("sem_mov",  foreground="#888888")

        # ── rodapé ────────────────────────────────────────────────────
        self.lbl_count = tk.Label(outer, text="", bg=self.BG,
                                  font=("Segoe UI", 8), anchor="w")
        self.lbl_count.grid(row=3, column=0, sticky="w", pady=(4, 0))

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self):
        try:
            df = self.controller.pim_repo.ler_pim()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler PIM:\n{e}",
                                 parent=self.root)
            return
        cols = [c for c, *_ in _TREE_COLS]
        for col in cols:
            if col not in df.columns:
                df[col] = None
        self._dados = df[cols].to_dict("records")
        self._filtrar()

    def _filtrar(self):
        pesq = self.ent_pesq.get().strip().lower()
        filtrado = [
            d for d in self._dados
            if not pesq or pesq in str(d.get("nome") or "").lower()
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
                f = float(v)
                return f"{f:.2f}" if f else ""
            except (TypeError, ValueError):
                return ""
        if col == "numero_residente":
            try:
                return str(int(v))
            except (TypeError, ValueError):
                return str(v)
        s = str(v).strip()
        return "" if s.lower() in ("nan", "none", "nat", "<na>") else s

    def _preencher_tree(self, dados: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for i, d in enumerate(dados):
            vals = tuple(self._fmt(d.get(cid), cid) for cid, *_ in _TREE_COLS)
            sem_mov = (
                d.get("saldo") in (None, 0, 0.0)
                and d.get("atual") in (None, 0, 0.0)
            )
            tag = "sem_mov" if sem_mov else ("alt" if i % 2 else "")
            self.tree.insert("", "end", values=vals, tags=(tag,))

        def _soma(col):
            total = 0.0
            for d in dados:
                v = d.get(col)
                try:
                    total += float(v)
                except (TypeError, ValueError):
                    pass
            return total

        try:
            self.lbl_totais.config(
                text=(
                    f"Anterior: {_soma('anterior'):.2f}   "
                    f"Atual: {_soma('atual'):.2f}   "
                    f"Recebido: {_soma('recebido'):.2f}   "
                    f"Saldo: {_soma('saldo'):.2f}"
                )
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

    def _importar_pim(self):
        """Importa PIM.xlsx para pim_corrente, substituindo os dados actuais."""
        import pandas as pd
        from domain.shared.strings import normalizar_colunas

        pim_path = None
        try:
            p = self.controller.cfg.paths.get("pim_file")
            if p and Path(p).exists():
                pim_path = Path(p)
        except Exception:
            pass

        if pim_path is None:
            chosen = filedialog.askopenfilename(
                title="Seleccionar PIM.xlsx",
                filetypes=[("Excel", "*.xlsx *.xls"), ("Todos", "*.*")],
                parent=self.root,
            )
            if not chosen:
                return
            pim_path = Path(chosen)

        try:
            df = pd.read_excel(pim_path, engine="openpyxl")
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível ler o ficheiro:\n{e}",
                                 parent=self.root)
            return

        df = normalizar_colunas(df)

        # garante que a coluna chave existe
        if "numero_residente" not in df.columns:
            messagebox.showerror(
                "Formato inválido",
                "O ficheiro não contém a coluna 'numero_residente'.",
                parent=self.root,
            )
            return

        try:
            self.controller.pim_repo.salvar_pim(df)
        except Exception as e:
            messagebox.showerror("Erro ao importar", str(e), parent=self.root)
            return

        messagebox.showinfo(
            "PIM importado",
            f"PIM actualizado a partir de:\n{pim_path}\n\n{len(df)} residente(s) importado(s).",
            parent=self.root,
        )
        self._carregar()

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _voltar_menu(self):
        getattr(self, '_root_gui', self).go_back()
