# atrpt/presentation/aprovisionamento/fornecedor_detalhe_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG

TIPOS_FORNECEDOR = [
    "Serviços", "Material", "Equipamento", "Obras",
    "Médico", "Enfermeiro", "Psicólogo", "Fisioterapeuta",
    "Professor de Ginástica", "Maestro",
    "Talho", "Peixaria", "Mercearia",
    "Energia", "Manutenção", "Outro",
]

TIPOS_RELACAO = [
    "Pontual", "Contrato", "Preferencial",
    "Avençado", "Prestador", "Suspenso",
]


class FornecedorDetalheGUI(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._resultados = []
        self._idx        = 0

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=10, pady=6)

        # ── barra de pesquisa ─────────────────────────────────────────
        barra = tk.Frame(outer, bg=self.BG)
        barra.pack(fill="x", pady=(0, 4))

        tk.Label(barra, text="Critério:", bg=self.BG, fg=self.FG).pack(side="left")
        self.cb_criterio = ttk.Combobox(
            barra, values=["Nome", "Tipo", "Relação"], state="readonly", width=10
        )
        self.cb_criterio.set("Nome")
        self.cb_criterio.pack(side="left", padx=(4, 12))

        # campo de pesquisa com dropdown flutuante
        self.cb_pesquisa = ttk.Combobox(
            barra, values=self._valores_para_criterio("Nome"),
            state="readonly", width=40
        )
        self.cb_pesquisa.pack(side="left", padx=(0, 8))
        self.cb_pesquisa.bind("<<ComboboxSelected>>", lambda e: self._pesquisar())
        self.cb_pesquisa.bind("<Return>", lambda e: self._pesquisar())

        ttk.Button(barra, text="🔍 Pesquisar", command=self._pesquisar).pack(side="left")

        # quando o critério muda, recarregar os valores do combobox
        self.cb_criterio.bind("<<ComboboxSelected>>", self._on_criterio_change)

        # ── navegação ─────────────────────────────────────────────────
        nav = tk.Frame(outer, bg=self.BG)
        nav.pack(fill="x", pady=2)

        self.btn_ant = ttk.Button(nav, text="◀", command=self._anterior, state="disabled", width=3)
        self.btn_ant.pack(side="left", padx=(0, 2))

        self.lbl_nav = tk.Label(nav, text="", bg=self.BG, fg=self.FG, width=12)
        self.lbl_nav.pack(side="left")

        self.btn_prox = ttk.Button(nav, text="▶", command=self._proximo, state="disabled", width=3)
        self.btn_prox.pack(side="left", padx=(2, 0))

        # ── formulário compacto ───────────────────────────────────────
        self.form = tk.Frame(outer, bg=self.BG)
        self.form.pack(fill="x", pady=4)

        def _lbl(parent, texto):
            return tk.Label(parent, text=texto, bg=self.BG, fg=self.FG, anchor="w")

        def _entry(parent, width):
            return ttk.Entry(parent, width=width)

        def _row(pady=3):
            f = tk.Frame(self.form, bg=self.BG)
            f.pack(fill="x", pady=pady)
            return f

        def _sep(texto=None):
            if texto:
                tk.Label(self.form, text=texto, bg=self.BG, fg=self.FG,
                         font=("Segoe UI", 8, "bold")).pack(anchor="w", pady=(6, 1))
            ttk.Separator(self.form, orient="horizontal").pack(fill="x", pady=(0, 3))

        # ── linha 1: Nome + NIF (só leitura) ────────────────────────
        r1 = _row()
        _lbl(r1, "Nome:").pack(side="left")
        self.ent_nome = _entry(r1, 42)
        self.ent_nome.pack(side="left", padx=(4, 16))
        _lbl(r1, "NIF:").pack(side="left")
        self.lbl_nif = tk.Label(r1, text="", bg=self.BG, fg=self.FG, width=12, anchor="w",
                                relief="sunken", padx=4)
        self.lbl_nif.pack(side="left", padx=(4, 0))

        # ── linha 2: IBAN + Email + Pagamento ────────────────────────
        r2 = _row()
        _lbl(r2, "IBAN:").pack(side="left")
        self.ent_iban = _entry(r2, 29)
        self.ent_iban.pack(side="left", padx=(4, 16))
        _lbl(r2, "Email:").pack(side="left")
        self.ent_email = _entry(r2, 30)
        self.ent_email.pack(side="left", padx=(4, 16))
        _lbl(r2, "Pagamento:").pack(side="left")
        self.cb_pagamento = ttk.Combobox(r2, values=["TB", "DD", "MB", "OU"], state="readonly", width=6)
        self.cb_pagamento.pack(side="left", padx=(3, 0))
        # ── linha 3: Tipo fornecedor + Tipo relação + Setor ───────────
        r3 = _row()
        _lbl(r3, "Tipo:").pack(side="left")
        self.cb_tipo_forn = ttk.Combobox(r3, values=TIPOS_FORNECEDOR, state="readonly", width=18)
        self.cb_tipo_forn.pack(side="left", padx=(3, 12))
        _lbl(r3, "Relação:").pack(side="left")
        self.cb_tipo_rel = ttk.Combobox(r3, values=TIPOS_RELACAO, state="readonly", width=12)
        self.cb_tipo_rel.pack(side="left", padx=(3, 12))
        _lbl(r3, "Setor:").pack(side="left")
        self.lbl_setor = tk.Label(r3, text="", bg=self.BG, fg=self.FG, width=16, anchor="w")
        self.lbl_setor.pack(side="left", padx=(4, 0))


        # ── contactos ─────────────────────────────────────────────────
        _sep("Contactos")

        r4 = _row()
        _lbl(r4, "Comercial:").pack(side="left")
        self.ent_c1_nome = _entry(r4, 18)
        self.ent_c1_nome.pack(side="left", padx=(4, 12))
        _lbl(r4, "Tel:").pack(side="left")
        self.ent_c1_tel = _entry(r4, 12)
        self.ent_c1_tel.pack(side="left", padx=(4, 12))
        _lbl(r4, "Email:").pack(side="left")
        self.ent_c1_email = _entry(r4, 22)
        self.ent_c1_email.pack(side="left", padx=(4, 0))

        r5 = _row()
        _lbl(r5, "Administrativo:").pack(side="left")
        self.ent_c2_nome = _entry(r5, 18)
        self.ent_c2_nome.pack(side="left", padx=(4, 12))
        _lbl(r5, "Tel:").pack(side="left")
        self.ent_c2_tel = _entry(r5, 12)
        self.ent_c2_tel.pack(side="left", padx=(4, 12))
        _lbl(r5, "Email:").pack(side="left")
        self.ent_c2_email = _entry(r5, 22)
        self.ent_c2_email.pack(side="left", padx=(4, 0))

        # ── botões ────────────────────────────────────────────────────
        btn_frame = tk.Frame(outer, bg=self.BG)
        btn_frame.pack(pady=6)

        tk.Button(btn_frame, text="Gravar", command=self._gravar,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left", padx=6)
        tk.Button(btn_frame, text="Limpar", command=self._limpar_form,
                  font=self.FONT_BUTTON, bg=self.BTN_BG).pack(side="left", padx=6)

        self._limpar_form()

    # ── pesquisa ──────────────────────────────────────────────────────

    def _entry_pesquisa(self, parent, valores, largura=30):
        """Entry com dropdown Toplevel para pesquisa — mantém foco ao digitar."""
        placeholder = "Digite para pesquisar..."
        _dd = [None]
        _timer = [None]

        entry = tk.Entry(parent, width=largura)
        entry.insert(0, placeholder)
        entry.config(foreground="gray")
        entry._valores = list(valores)
        entry._cancel_timer = lambda: (
        entry.after_cancel(_timer[0]) if _timer[0] else None)

        def _focus_in(e):
            if entry.get() == placeholder:
                entry.delete(0, "end")
                entry.config(foreground="black")

        def _focus_out(e):
            # só esconder dropdown — não interferir com outros campos
            entry.after(150, _esconder)

        def _esconder():
            if _dd[0]:
                _dd[0].destroy()
                _dd[0] = None

        def _mostrar(filtrados):
            _esconder()
            if not filtrados:
                return
            win = tk.Toplevel(entry)
            win.wm_overrideredirect(True)
            lb = tk.Listbox(win, height=min(10, len(filtrados)),
                            selectmode="single", activestyle="dotbox")
            sb = tk.Scrollbar(win, orient="vertical", command=lb.yview)
            lb.configure(yscrollcommand=sb.set)
            lb.pack(side="left", fill="both", expand=True)
            sb.pack(side="right", fill="y")
            for v in filtrados:
                lb.insert("end", v)

            def _posicionar():
                entry.update_idletasks()
                x = entry.winfo_rootx()
                y = entry.winfo_rooty() + entry.winfo_height()
                w = max(entry.winfo_width(), 250)
                h = min(10, len(filtrados)) * 20 + 4
                win.geometry(f"{w}x{h}+{x}+{y}")
                win.lift()
                win.focus_set()
                lb.focus_set()

            win.after(10, _posicionar)
            _dd[0] = win

            def _select(e):
                sel = lb.curselection()
                if sel:
                    valor = lb.get(sel[0])
                    entry.delete(0, "end")
                    entry.insert(0, valor)
                    entry.config(foreground="black")
                    _esconder()
                    entry.focus_set()
                    self._pesquisar()
            lb.bind("<ButtonRelease-1>", _select)
            lb.bind("<Return>", _select)

        def _keyrelease(e):
            if e.keysym in ("Escape", "Tab", "Shift_L", "Shift_R",
                            "Control_L", "Control_R", "Alt_L", "Alt_R"):
                return
            if e.keysym in ("Return", "KP_Enter"):
                _esconder(); return
            texto = entry.get().strip()
            if texto == placeholder:
                return
            filtrados = [v for v in entry._valores if texto.lower() in v.lower()] if texto else entry._valores
            _mostrar(filtrados)

        entry.bind("<FocusIn>",    _focus_in)
        entry.bind("<FocusOut>",   _focus_out)
        entry.bind("<KeyRelease>", _keyrelease)
        entry.get_value = lambda: "" if entry.get() == placeholder else entry.get()
        entry._mostrar_todos = lambda: _mostrar(entry._valores)
        return entry

    def _valores_para_criterio(self, criterio):
        """Devolve lista de valores para alimentar o dropdown de pesquisa."""
        if criterio == "Tipo":
            return TIPOS_FORNECEDOR
        elif criterio == "Relação":
            return TIPOS_RELACAO
        # Nome — vai à BD
        try:
            todos = self.controller.get_fornecedores()
            return sorted({f.nome for f in todos if f.nome})
        except Exception:
            return []

    def _on_criterio_change(self, event=None):
        criterio = self.cb_criterio.get()
        valores  = self._valores_para_criterio(criterio)
        self.cb_pesquisa["values"] = valores
        self.cb_pesquisa.set("")
        self.cb_pesquisa.focus_set()
    def _pesquisar(self):
        criterio = self.cb_criterio.get()
        texto = self.cb_pesquisa.get().strip()

        if not texto:
            messagebox.showwarning("Pesquisa", "Introduza um valor para pesquisar.", parent=self.root)
            return

        texto_low = texto.lower()
        todos     = self.controller.get_fornecedores()

        if criterio == "Nome":
            self._resultados = [f for f in todos if texto_low in f.nome.lower()]
        elif criterio == "Tipo":
            self._resultados = [f for f in todos if texto_low in (f.tipo_fornecedor or "").lower()]
        elif criterio == "Relação":
            self._resultados = [f for f in todos if texto_low in (f.tipo_relacao or "").lower()]

        if not self._resultados:
            messagebox.showinfo("Pesquisa", "Nenhum fornecedor encontrado.", parent=self.root)
            self._limpar_form()
            return

        self._idx = 0
        self._mostrar_actual()

    # ── navegação ─────────────────────────────────────────────────────

    def _anterior(self):
        if self._idx > 0:
            self._idx -= 1
            self._mostrar_actual()

    def _proximo(self):
        if self._idx < len(self._resultados) - 1:
            self._idx += 1
            self._mostrar_actual()

    def _mostrar_actual(self):
        f     = self._resultados[self._idx]
        total = len(self._resultados)

        self.lbl_nav.config(text=f"{self._idx + 1} / {total}")
        self.btn_ant.config(state="normal"  if self._idx > 0         else "disabled")
        self.btn_prox.config(state="normal" if self._idx < total - 1 else "disabled")

        def _set(entry, valor):
            entry.delete(0, tk.END)
            entry.insert(0, valor or "")

        _set(self.ent_nome,     f.nome)
        self.lbl_nif.config(text=f.nif or "")
        _set(self.ent_email,    f.email)
        _set(self.ent_iban,     f.iban)
        _set(self.ent_c1_nome,  f.comercial_nome)
        _set(self.ent_c1_tel,   f.comercial_telemovel)
        _set(self.ent_c1_email, f.comercial_email)
        _set(self.ent_c2_nome,  f.administrativo_nome)
        _set(self.ent_c2_tel,   f.administrativo_telemovel)
        _set(self.ent_c2_email, f.administrativo_email)

        self.cb_tipo_forn.set(f.tipo_fornecedor or "")
        self.cb_tipo_rel.set(f.tipo_relacao or "")
        self.cb_pagamento.set(getattr(f, "metodo_pagamento", "") or "")
        self._setor_actual = getattr(f, "setor", None)
        self.lbl_setor.config(text=self._setor_actual or "")

    # ── gravar ────────────────────────────────────────────────────────

    def _gravar(self):
        if not self._resultados:
            messagebox.showwarning("Aviso", "Nenhum fornecedor seleccionado.", parent=self.root)
            return

        f = self._resultados[self._idx]
        dados = {
            "id":                 f.id,
            "nome":               self.ent_nome.get().strip(),
            "nif":                self.lbl_nif.cget("text") or None,
            "email":              self.ent_email.get().strip() or None,
            "iban":               self.ent_iban.get().strip() or None,
            "tipo_fornecedor":    self.cb_tipo_forn.get() or None,
            "tipo_relacao":       self.cb_tipo_rel.get() or None,
            "metodo_pagamento":   self.cb_pagamento.get() or None,
            "setor":              getattr(self, "_setor_actual", None),
            "comercial_nome":     self.ent_c1_nome.get().strip() or None,
            "comercial_telefone": self.ent_c1_tel.get().strip() or None,
            "comercial_email":    self.ent_c1_email.get().strip() or None,
            "administrativo_nome":     self.ent_c2_nome.get().strip() or None,
            "administrativo_telefone": self.ent_c2_tel.get().strip() or None,
            "administrativo_email":    self.ent_c2_email.get().strip() or None,
        }

        if not dados["nome"]:
            messagebox.showerror("Erro", "O nome é obrigatório.", parent=self.root)
            return

        try:
            self.controller.editar_fornecedor(dados)
            messagebox.showinfo("OK", "Fornecedor gravado com sucesso.", parent=self.root)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)

    # ── limpar ────────────────────────────────────────────────────────

    def _limpar_form(self):
        self._resultados = []
        self._idx = 0
        self.lbl_nav.config(text="")
        self.btn_ant.config(state="disabled")
        self.btn_prox.config(state="disabled")
        self.lbl_nif.config(text="")
        for e in [self.ent_nome, self.ent_email, self.ent_iban,
                  self.ent_c1_nome, self.ent_c1_tel, self.ent_c1_email,
                  self.ent_c2_nome, self.ent_c2_tel, self.ent_c2_email]:
            e.delete(0, tk.END)
        self.cb_tipo_forn.set("")
        self.cb_tipo_rel.set("")
        self.cb_pagamento.set("")
        self.lbl_setor.config(text="")
