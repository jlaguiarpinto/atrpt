# presentation/secretaria/candidatos_view.py
#
# Lista de candidatos a residentes com edição inline e criação de novos.

import tkinter as tk
from tkinter import ttk, messagebox

from presentation.shared.base_gui import BaseGui as BG
from infrastructure.persistence.secretaria.candidatos_repository import ESTADOS

_TREE_COLS = [
    ("id",            "ID",           42),
    ("estado",        "Estado",       70),
    ("nome",          "Nome",        200),
    ("data_admissao", "Dt. Admissão", 88),
    ("responsavel",   "Responsável", 150),
    ("resp_tlm",      "Contacto",     90),
    ("mensalidade",   "Mensalidade",  72),
    ("notas",         "Notas",       130),
]


class CandidatosView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._dados: list[dict] = []

    def _post_init(self):
        root = getattr(self, "_root_gui", self)
        self.build_menu_buttons([("← Residentes", root.go_back)])
        self._build()
        self._carregar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame_work, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── barra de filtros ──────────────────────────────────────────
        filtros = tk.LabelFrame(outer, text="Filtros", bg=self.BG,
                                fg=self.FG, font=("Segoe UI", 8, "bold"))
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 4))

        f = tk.Frame(filtros, bg=self.BG)
        f.pack(fill="x", padx=6, pady=4)

        tk.Label(f, text="Nome:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 8)).pack(side="left")
        self._v_pesq = tk.StringVar()
        ent = tk.Entry(f, textvariable=self._v_pesq, width=28)
        ent.pack(side="left", padx=(3, 12))
        ent.bind("<Return>", lambda _: self._filtrar())

        tk.Label(f, text="Estado:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 8)).pack(side="left")
        self._v_estado_f = tk.StringVar(value="(todos)")
        cb = ttk.Combobox(f, textvariable=self._v_estado_f, state="readonly",
                          width=10, values=["(todos)"] + list(ESTADOS))
        cb.pack(side="left", padx=(3, 10))
        cb.bind("<<ComboboxSelected>>", lambda _: self._filtrar())

        tk.Button(f, text="Filtrar", command=self._filtrar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)

        tk.Button(f, text="Gerar Contrato", command=self._gerar_contrato,
                  font=("Segoe UI", 8), bg="#fff9c4",
                  width=14).pack(side="right", padx=(0, 6))
        tk.Button(f, text="+ Novo candidato", command=self._novo,
                  font=("Segoe UI", 8, "bold"), bg="#c8e6c9",
                  width=16).pack(side="right", padx=6)

        # ── lista ─────────────────────────────────────────────────────
        ft = tk.Frame(outer, bg=self.BG)
        ft.grid(row=1, column=0, sticky="nsew")
        ft.rowconfigure(0, weight=1)
        ft.columnconfigure(0, weight=1)

        cols = [c for c, *_ in _TREE_COLS]
        self._tree = ttk.Treeview(ft, columns=cols,
                                  show="headings", selectmode="browse")
        for cid, label, w in _TREE_COLS:
            anc = "center" if cid in ("id", "estado") else (
                  "e" if cid == "mensalidade" else "w")
            self._tree.heading(cid, text=label)
            self._tree.column(cid, width=w, anchor=anc, minwidth=30)

        vsb = ttk.Scrollbar(ft, orient="vertical",   command=self._tree.yview)
        hsb = ttk.Scrollbar(ft, orient="horizontal", command=self._tree.xview)
        self._tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self._tree.bind("<Double-1>", self._on_double)
        self._tree.tag_configure("inscrito", foreground="#aaa")

        # ── rodapé ────────────────────────────────────────────────────
        rod = tk.Frame(outer, bg=self.BG, pady=3)
        rod.grid(row=2, column=0, sticky="ew")
        self._lbl_total = tk.Label(rod, text="", bg=self.BG, fg="#666",
                                   font=("Segoe UI", 8))
        self._lbl_total.pack(side="left", padx=8)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self):
        try:
            self._dados = self.controller.candidatos_repo.get_all()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar candidatos:\n{e}",
                                 parent=self.root)
            return
        self._filtrar()

    def _filtrar(self):
        txt    = self._v_pesq.get().strip().lower()
        estado = self._v_estado_f.get()
        result = [
            d for d in self._dados
            if (not txt or txt in (d.get("nome") or "").lower())
            and (estado == "(todos)" or d.get("estado") == estado)
        ]
        self._popular(result)

    def _popular(self, dados: list[dict]):
        self._tree.delete(*self._tree.get_children())
        for d in dados:
            est = d.get("estado") or ""
            tag = "inscrito" if est == "inscrito" else ""
            self._tree.insert("", "end", iid=str(d["id"]),
                              values=tuple(str(d.get(c) or "") for c, *_ in _TREE_COLS),
                              tags=(tag,))
        self._lbl_total.config(text=f"{len(dados)} registo(s)")

    # ------------------------------------------------------------------
    # Acções
    # ------------------------------------------------------------------

    def _novo(self):
        getattr(self, "_root_gui", self).show_view(
            __import__("presentation.secretaria.novo_residente_view",
                       fromlist=["NovoResidenteView"]).NovoResidenteView,
            self.controller,
        )

    def _on_double(self, _event=None):
        sel = self._tree.selection()
        if not sel:
            return
        cid = int(sel[0])
        d = next((x for x in self._dados if x.get("id") == cid), None)
        if d:
            self._editar(d)

    def _gerar_contrato(self):
        sel = self._tree.selection()
        if not sel:
            from tkinter import messagebox
            messagebox.showwarning("Atenção", "Seleccione um candidato.", parent=self.root)
            return
        cid = int(sel[0])
        d = next((x for x in self._dados if x.get("id") == cid), None)
        if d:
            self.controller.abrir_contrato_candidato(d)

    def _editar(self, record: dict):
        from presentation.secretaria.novo_residente_view import _CAMPOS, _FLOAT_CAMPOS

        win = tk.Toplevel(self.root)
        win.title(f"Editar — {record.get('nome', '')}")
        win.geometry("680x640")
        win.grab_set()
        win.resizable(True, True)

        outer = tk.Frame(win, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=6, pady=6)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        form = tk.Frame(canvas, bg=self.BG, padx=16, pady=8)
        win_id = canvas.create_window((0, 0), window=form, anchor="nw")

        def _on_conf(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        form.bind("<Configure>", _on_conf)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        pad = {"padx": 6, "pady": 2}
        vars_edit: dict[str, tk.StringVar] = {}

        # ── Estado ────────────────────────────────────────────────────
        row_i = 0
        tk.Label(form, text="Estado:", anchor="e", width=20,
                 bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9, "bold")).grid(row=row_i, column=0, sticky="e", **pad)
        v_estado = tk.StringVar(value=record.get("estado") or "pendente")
        ttk.Combobox(form, textvariable=v_estado, values=list(ESTADOS),
                     state="readonly", width=14).grid(row=row_i, column=1, sticky="w", **pad)
        row_i += 1

        # ── Campos ────────────────────────────────────────────────────
        for (campo, label, obrig, width, max_len) in _CAMPOS:
            if campo is None:
                tk.Label(form, text=f"  {label}",
                         bg="#e8e8e8", fg="#444",
                         font=("Segoe UI", 8, "bold"),
                         anchor="w", relief="flat").grid(
                    row=row_i, column=0, columnspan=2,
                    sticky="ew", padx=4, pady=(10, 2))
                row_i += 1
                continue

            tk.Label(form, text=label + ("  *" if obrig else "") + ":",
                     anchor="e", width=20, bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 9, "bold" if obrig else "normal")).grid(
                row=row_i, column=0, sticky="e", **pad)

            var = tk.StringVar(value=str(record.get(campo) or ""))
            vars_edit[campo] = var
            e = tk.Entry(form, textvariable=var, width=width or 20,
                         font=("Segoe UI", 9))
            e.grid(row=row_i, column=1, sticky="w", **pad)
            if max_len:
                var.trace_add("write",
                              lambda *_, v=var, ml=max_len:
                              v.set(v.get()[:ml]) if len(v.get()) > ml else None)
            row_i += 1

        form.columnconfigure(1, weight=0)

        # ── Rodapé ────────────────────────────────────────────────────
        rodape = tk.Frame(win, bg=self.BG, pady=6)
        rodape.pack(fill="x", side="bottom", padx=6)

        def _guardar():
            dados = {"estado": v_estado.get()}
            for campo, *_ in _CAMPOS:
                if campo is None or campo not in vars_edit:
                    continue
                v = vars_edit[campo].get().strip() or None
                if v is not None and campo in _FLOAT_CAMPOS:
                    try:
                        v = str(round(float(v.replace(",", ".")), 2))
                    except ValueError:
                        messagebox.showerror("Valor inválido",
                                             f"O campo «{campo}» deve ser numérico.",
                                             parent=win)
                        return
                dados[campo] = v
            try:
                self.controller.candidatos_repo.update(int(record["id"]), dados)
            except Exception as exc:
                messagebox.showerror("Erro", str(exc), parent=win)
                return
            messagebox.showinfo("Gravado", "Candidato actualizado.", parent=win)
            win.destroy()
            self._carregar()

        tk.Button(rodape, text="Gravar", command=_guardar,
                  font=("Segoe UI", 10, "bold"), bg="#c8e6c9",
                  width=14).pack(side="right", padx=6)
        tk.Button(rodape, text="Cancelar", command=win.destroy,
                  font=("Segoe UI", 9), width=10).pack(side="right", padx=4)

        win.bind("<Return>", lambda _: _guardar())
        win.bind("<Escape>", lambda _: win.destroy())
