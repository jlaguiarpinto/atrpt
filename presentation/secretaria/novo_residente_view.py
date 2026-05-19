# presentation/secretaria/novo_residente_view.py
#
# Formulário de registo de candidato a residente (estado: pendente ou espera).
# Guarda em residentes_candidatos — tabela independente de residentes.

import tkinter as tk
from tkinter import ttk, messagebox

from presentation.shared.base_gui import BaseGui as BG
from infrastructure.persistence.secretaria.candidatos_repository import ESTADOS

# (campo, label, obrigatorio, entry_width, max_len)
# campo=None  →  cabeçalho de secção
_CAMPOS = [
    # ── Utente ────────────────────────────────────────────────────────
    (None,                  "Utente",                           False,  0, None),
    ("nome",                "Nome",                             True,  46, None),
    ("data_nascimento",     "Dt. Nascimento",                   False, 13, None),
    ("genero",              "Género",                           False,  5,    4),
    ("nif",                 "Contribuinte (NIF)",               False, 14, None),
    ("id_tipo",             "Tipo doc. ID",                     False, 13, None),
    ("id_num",              "Nº doc. ID",                       False, 22, None),
    ("id_val",              "Validade doc. ID",                 False, 13, None),
    # ── Morada e Contacto ─────────────────────────────────────────────
    (None,                  "Morada e Contacto",                False,  0, None),
    ("morada",              "Morada",                           False, 46, None),
    ("cod_postal",          "Cód. Postal",                      False, 10, None),
    ("contato",             "Contacto",                         False, 16, None),
    # ── Responsável ────────────────────────────────────────────────────
    (None,                  "Responsável",                      False,  0, None),
    ("responsavel",         "Nome",                             False, 46, None),
    ("relacao",             "Relação",                          False,  5,    4),
    ("resp_gen",            "Tratamento",                       False, 10, None),
    ("resp_id_tipo",        "Tipo doc. resp.",                  False, 13, None),
    ("resp_id_num",         "Nº doc. resp.",                    False, 22, None),
    ("resp_id_val",         "Validade doc. resp.",              False, 13, None),
    ("resp_tlm",            "Contacto resp.",                   False, 16, None),
    ("email",               "Email",                            False, 30, None),
    # ── Financeiro ────────────────────────────────────────────────────
    (None,                  "Informação Financeira",            False,  0, None),
    ("mensalidade",         "Mensalidade",                      False, 10, None),
    ("caucao",              "Caução",                           False, 10, None),
    ("iban",                "IBAN",                             False, 30, None),
    ("data_iban",           "Data IBAN",                        False, 13, None),
    ("designacao_bancaria", "Designação bancária",              False, 30, None),
    ("data_admissao",       "Dt. Admissão",                     False, 13, None),
    # ── Administrativo ────────────────────────────────────────────────
    (None,                  "Administrativo",                   False,  0, None),
    ("copag",               "CoPag",                            False,  5,    4),
    ("numero_socio",        "Nº Sócio",                         False,  6, None),
    ("petit_nom",           "Petit nom",                        False, 22, None),
    ("data_fim",            "Dt. Fim",                          False, 13, None),
    ("notas",               "Notas",                            False, 46, None),
]

_FLOAT_CAMPOS = {"mensalidade", "caucao"}


class NovoResidenteView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._vars:  dict[str, tk.StringVar] = {}
        self._v_estado: tk.StringVar | None  = None

    def _post_init(self):
        root = getattr(self, "_root_gui", self)
        self.build_menu_buttons([("← Residentes", root.go_back)])
        self._build()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame_work, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(0, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── área scrollável ───────────────────────────────────────────
        canvas = tk.Canvas(outer, bg=self.BG, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        canvas.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        form = tk.Frame(canvas, bg=self.BG, padx=20, pady=10)
        win_id = canvas.create_window((0, 0), window=form, anchor="nw")

        def _on_configure(e):
            canvas.configure(scrollregion=canvas.bbox("all"))
            canvas.itemconfig(win_id, width=canvas.winfo_width())

        form.bind("<Configure>", _on_configure)
        canvas.bind("<Configure>", lambda e: canvas.itemconfig(win_id, width=e.width))
        canvas.bind_all("<MouseWheel>",
                        lambda e: canvas.yview_scroll(-1 * (e.delta // 120), "units"))

        pad = {"padx": 8, "pady": 2}

        def _ctx(entry):
            m = tk.Menu(entry, tearoff=0)
            m.add_command(label="Cortar",  command=lambda: entry.event_generate("<<Cut>>"))
            m.add_command(label="Copiar",  command=lambda: entry.event_generate("<<Copy>>"))
            m.add_command(label="Colar",   command=lambda: entry.event_generate("<<Paste>>"))
            m.add_separator()
            m.add_command(label="Seleccionar tudo",
                          command=lambda: entry.select_range(0, tk.END))
            return m

        # ── Estado (combobox no topo, fora da lista de campos) ────────
        row_i = 0
        tk.Label(form, text="Estado:", anchor="e", width=20,
                 bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9, "bold")).grid(row=row_i, column=0, sticky="e", **pad)
        self._v_estado = tk.StringVar(value="pendente")
        estados_display = [e for e in ESTADOS if e != "inscrito"]
        cb = ttk.Combobox(form, textvariable=self._v_estado,
                          values=estados_display, state="readonly", width=14)
        cb.grid(row=row_i, column=1, sticky="w", **pad)
        row_i += 1

        # ── Campos dinâmicos ──────────────────────────────────────────
        for (campo, label, obrig, width, max_len) in _CAMPOS:
            if campo is None:
                # cabeçalho de secção
                tk.Label(form, text=f"  {label}",
                         bg="#e8e8e8", fg="#444",
                         font=("Segoe UI", 8, "bold"),
                         anchor="w", relief="flat").grid(
                    row=row_i, column=0, columnspan=2,
                    sticky="ew", padx=4, pady=(10, 2))
                row_i += 1
                continue

            lbl_txt = label + (" *" if obrig else "") + ":"
            tk.Label(form, text=lbl_txt, anchor="e", width=20,
                     bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 9, "bold" if obrig else "normal")).grid(
                row=row_i, column=0, sticky="e", **pad)

            var = tk.StringVar()
            self._vars[campo] = var

            e = tk.Entry(form, textvariable=var, width=width or 20,
                         font=("Segoe UI", 9))
            e.grid(row=row_i, column=1, sticky="w", **pad)

            if max_len:
                var.trace_add("write",
                              lambda *_, v=var, ml=max_len:
                              v.set(v.get()[:ml]) if len(v.get()) > ml else None)

            m = _ctx(e)
            e.bind("<Button-3>", lambda ev, _m=m: _m.tk_popup(ev.x_root, ev.y_root))
            row_i += 1

        form.columnconfigure(1, weight=0)

        # ── rodapé fixo ───────────────────────────────────────────────
        rodape = tk.Frame(outer, bg=self.BG, pady=8)
        rodape.grid(row=1, column=0, columnspan=2, sticky="ew")

        tk.Label(rodape, text="* campo obrigatório",
                 bg=self.BG, fg="#666", font=("Segoe UI", 8)).pack(side="left", padx=12)

        tk.Button(rodape, text="Gravar e sair", command=self._gravar,
                  font=("Segoe UI", 10, "bold"), bg="#c8e6c9", width=16).pack(side="right", padx=6)
        tk.Button(rodape, text="Gerar Contrato", command=self._gravar_e_contrato,
                  font=("Segoe UI", 10, "bold"), bg="#fff9c4", width=16).pack(side="right", padx=4)
        tk.Button(rodape, text="Cancelar", command=self._cancelar,
                  font=("Segoe UI", 9), width=12).pack(side="right", padx=4)

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _validar_e_coletar(self) -> dict | None:
        erros = []
        for campo, label, obrig, *_ in _CAMPOS:
            if campo is None:
                continue
            if obrig and not self._vars[campo].get().strip():
                erros.append(label)
        if erros:
            messagebox.showwarning(
                "Campos obrigatórios",
                "Preencha os seguintes campos:\n  • " + "\n  • ".join(erros),
                parent=self.root,
            )
            return None

        dados = {"estado": self._v_estado.get()}
        for campo, *_ in _CAMPOS:
            if campo is None or campo not in self._vars:
                continue
            v = self._vars[campo].get().strip() or None
            if v is not None and campo in _FLOAT_CAMPOS:
                try:
                    v = str(round(float(v.replace(",", ".")), 2))
                except ValueError:
                    messagebox.showerror(
                        "Valor inválido",
                        f"O campo «{campo}» deve ser um valor numérico.",
                        parent=self.root,
                    )
                    return None
            dados[campo] = v
        return dados

    # ------------------------------------------------------------------
    # Acções
    # ------------------------------------------------------------------

    def _gravar(self):
        dados = self._validar_e_coletar()
        if dados is None:
            return
        try:
            self.controller.candidatos_repo.insert(dados)
        except Exception as exc:
            messagebox.showerror("Erro ao gravar", str(exc), parent=self.root)
            return
        messagebox.showinfo(
            "Gravado",
            f"Candidato «{dados.get('nome')}» registado (estado: {dados.get('estado')}).",
            parent=self.root,
        )
        getattr(self, "_root_gui", self).go_back()

    def _gravar_e_contrato(self):
        dados = self._validar_e_coletar()
        if dados is None:
            return
        try:
            cid = self.controller.candidatos_repo.insert(dados)
            candidato = self.controller.candidatos_repo.get_by_id(cid)
        except Exception as exc:
            messagebox.showerror("Erro ao gravar", str(exc), parent=self.root)
            return

        from presentation.secretaria.contrato_residente_view import ContratoResidenteView
        root = getattr(self, "_root_gui", self)
        root.show_view(ContratoResidenteView, self.controller, candidato=candidato)

    def _cancelar(self):
        getattr(self, "_root_gui", self).go_back()
