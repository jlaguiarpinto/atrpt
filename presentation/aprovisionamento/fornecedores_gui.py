# atrpt/presentation/fornecedores_main_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG
from presentation.aprovisionamento.fornecedor_detalhe_gui import FornecedorDetalheGUI


TIPOS_FORNECEDOR = [
    "Serviços", "Material", "Equipamento", "Obras",
    "Médico", "Enfermeiro", "Psicólogo", "Fisioterapeuta",
    "Professor de Ginástica", "Maestro","Consumíveis"
    "Talho", "Peixaria", "Mercearia",
    "Energia", "Manutenção", "Outro",
]

TIPOS_RELACAO = [
    "Pontual", "Contrato", "Preferencial",
    "Avençado", "Prestador", "Suspenso",
]


class FornecedoresGUI(BG):
    """Sub-menu para gestão de Fornecedores"""

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        # _build chamado via _post_init pelo show_view, após injecção dos frames

    def _post_init(self):
        self._build()

    def _build(self):
        frame = self.abrir_work_area()
        opcoes = [
            ("Novo Fornecedor",       self._novo_fornecedor),
            ("Importar Fornecedores", self._importar_fornecedores),
            ("Procurar Fornecedor", self._procurar_fornecedor),
            ("Listar Todos",          self._listar_todos),
        ]
        self.build_menu_buttons(opcoes)


    def _novo_fornecedor(self):
        win = tk.Toplevel(self.root)
        BG.make_modal(win, self.root)
        from presentation.aprovisionamento.pedido_form_gui import form_fornecedor_dialog
        dados = form_fornecedor_dialog(win)
        if dados:
            self.controller.novo_fornecedor(dados)

    def _importar_fornecedores(self):
        path = self.ask_file(
            title="Selecionar ficheiro Excel",
            filetypes=[("Excel", "*.xlsx"), ("All files", "*.*")]
        )
        if path:
            self.controller.importar_fornecedores(path)

    def _listar_todos(self):
        fornecedores = self.controller.get_fornecedores()
        self._mostrar_lista_fornecedores(fornecedores)

    def _procurar_fornecedor(self):
        self.show_view(FornecedorDetalheGUI, self.controller)

    def _pesquisar_fornecedor(self):
        nome = self.pedirInput("Pesquisar", "Nome do fornecedor:")
        if nome:
            resultado = self.controller.pesquisar_fornecedor(nome)
            self._mostrar_lista_fornecedores(resultado)

    # ------------------------------------------------------------------
    # Lista com duplo clique para editar
    # ------------------------------------------------------------------

    def _mostrar_lista_fornecedores(self, fornecedores):
        if not fornecedores:
            self.informuser("Info", "Nenhum fornecedor encontrado.")
            return

        win = tk.Toplevel(self.root)
        win.title("Lista de Fornecedores")
        win.geometry("1400x600")
        win.resizable(True, True)

        cols = (
            "id", "nome", "nif", "email", "iban",
            "tipo_fornecedor", "tipo_relacao", "setor", "metodo_pagamento",
            "com_nome", "com_email", "com_telm",
            "adm_nome", "adm_email", "adm_telm",
        )
        headers = {
            "id":               ("ID",            50),
            "nome":             ("Nome",          220),
            "nif":              ("NIF",           100),
            "email":            ("Email",         180),
            "iban":             ("IBAN",          200),
            "tipo_fornecedor":  ("Tipo",          120),
            "tipo_relacao":     ("Relação",        90),
            "setor":            ("Setor",         100),
            "metodo_pagamento": ("Pagamento",      80),
            "com_nome":         ("Comercial",     140),
            "com_email":        ("Email Com.",    150),
            "com_telm":         ("Telm. Com.",     90),
            "adm_nome":         ("Administrativo",140),
            "adm_email":        ("Email Adm.",    150),
            "adm_telm":         ("Telm. Adm.",     90),
        }

        # ── frame principal com grid ──────────────────────────────────
        win.rowconfigure(0, weight=1)
        win.rowconfigure(1, weight=0)
        win.rowconfigure(2, weight=0)
        win.columnconfigure(0, weight=1)

        frame = ttk.Frame(win)
        frame.grid(row=0, column=0, sticky="nsew", padx=8, pady=8)
        frame.rowconfigure(0, weight=1)
        frame.columnconfigure(0, weight=1)

        tree = ttk.Treeview(frame, columns=cols, show="headings")
        for col in cols:
            label, width = headers[col]
            tree.heading(col, text=label)
            tree.column(col, width=width, anchor="w", minwidth=40)

        vsb = ttk.Scrollbar(frame, orient="vertical",   command=tree.yview)
        hsb = ttk.Scrollbar(frame, orient="horizontal", command=tree.xview)
        tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        # ── rodapé ───────────────────────────────────────────────────
        ttk.Label(win, text="Duplo clique para editar", foreground="gray").grid(
            row=1, column=0, sticky="w", padx=12, pady=(0, 2))
        ttk.Button(win, text="Fechar", command=win.destroy).grid(
            row=2, column=0, pady=(0, 8))

        # ── dados ─────────────────────────────────────────────────────
        fornecedor_por_iid = {}
        for f in fornecedores:
            iid = tree.insert("", "end", values=(
                f.id,
                f.nome,
                f.nif                        or "",
                f.email                      or "",
                f.iban                       or "",
                f.tipo_fornecedor            or "",
                f.tipo_relacao               or "",
                getattr(f, "setor", "")      or "",
                getattr(f, "metodo_pagamento", "") or "",
                getattr(f, "comercial_nome", "")   or "",
                getattr(f, "comercial_email", "")  or "",
                getattr(f, "comercial_telemovel", "") or "",
                getattr(f, "administrativo_nome", "") or "",
                getattr(f, "administrativo_email", "") or "",
                getattr(f, "administrativo_telemovel", "") or "",
            ))
            fornecedor_por_iid[iid] = f

        # ── duplo clique para editar ──────────────────────────────────
        def _on_dblclick(event):
            sel = tree.selection()
            if not sel:
                return
            self._editar_fornecedor(fornecedor_por_iid[sel[0]], tree, sel[0])

        tree.bind("<Double-1>", _on_dblclick)

    # ------------------------------------------------------------------
    # Formulário de edição completo
    # ------------------------------------------------------------------

    def _editar_fornecedor(self, fornecedor, tree, iid):
        win = tk.Toplevel(self.root)
        win.title(f"Editar — {fornecedor.nome}")
        win.grab_set()
        win.resizable(False, False)

        frame = ttk.Frame(win, padding=12)
        frame.pack(fill="both", expand=True)

        def _lbl(row, texto):
            ttk.Label(frame, text=texto).grid(row=row, column=0, sticky="w", pady=3, padx=(0, 8))

        def _entry(row, valor, width=38):
            e = ttk.Entry(frame, width=width)
            e.insert(0, valor or "")
            e.grid(row=row, column=1, columnspan=2, sticky="w", pady=3)
            return e

        def _sep(row):
            ttk.Separator(frame, orient="horizontal").grid(
                row=row, column=0, columnspan=3, sticky="ew", pady=6)

        # ── dados gerais ──────────────────────────────────────────────
        _lbl(0, "Nome:")
        ent_nome = _entry(0, fornecedor.nome)

        _lbl(1, "NIF:")
        ent_nif = _entry(1, fornecedor.nif)

        _lbl(2, "Email geral:")
        ent_email = _entry(2, fornecedor.email)

        _lbl(3, "IBAN:")
        ent_iban = _entry(3, fornecedor.iban)

        _lbl(4, "Tipo fornecedor:")
        cb_tipo_forn = ttk.Combobox(frame, values=TIPOS_FORNECEDOR, state="readonly", width=30)
        cb_tipo_forn.set(fornecedor.tipo_fornecedor or "")
        cb_tipo_forn.grid(row=4, column=1, sticky="w", pady=3)

        _lbl(5, "Tipo relação:")
        cb_tipo_rel = ttk.Combobox(frame, values=TIPOS_RELACAO, state="readonly", width=30)
        cb_tipo_rel.set(fornecedor.tipo_relacao or "")
        cb_tipo_rel.grid(row=5, column=1, sticky="w", pady=3)

        _lbl(6, "Método pagamento:")
        cb_pagamento = ttk.Combobox(frame, values=["TB", "DD", "MB", "OU"], state="readonly", width=10)
        cb_pagamento.set(getattr(fornecedor, "metodo_pagamento", "") or "")
        cb_pagamento.grid(row=6, column=1, sticky="w", pady=3)

        _sep(7)

        # contacto comercial
        ttk.Label(frame, text="Contacto Comercial", font=("Segoe UI", 9, "bold")).grid(
            row=8, column=0, columnspan=3, sticky="w", pady=(0, 2))
        _lbl(9, "Nome:")
        ent_com_nome = _entry(9, getattr(fornecedor, "comercial_nome", ""))
        _lbl(10, "Email:")
        ent_com_email = _entry(10, getattr(fornecedor, "comercial_email", ""))
        _lbl(11, "Telm:")
        ent_com_telm = _entry(11, getattr(fornecedor, "comercial_telemovel", ""))

        _sep(12)

        # contacto administrativo
        ttk.Label(frame, text="Contacto Administrativo", font=("Segoe UI", 9, "bold")).grid(
            row=13, column=0, columnspan=3, sticky="w", pady=(0, 2))
        _lbl(14, "Nome:")
        ent_adm_nome = _entry(14, getattr(fornecedor, "administrativo_nome", ""))
        _lbl(15, "Email:")
        ent_adm_email = _entry(15, getattr(fornecedor, "administrativo_email", ""))
        _lbl(16, "Telm:")
        ent_adm_telm = _entry(16, getattr(fornecedor, "administrativo_telemovel", ""))

        _sep(17)



        # ── botões ───────────────────────────────────────────────────
        def _gravar():
            dados = {
                "id":                      fornecedor.id,
                "nome":                    ent_nome.get().strip(),
                "nif":                     ent_nif.get().strip() or None,
                "email":                   ent_email.get().strip() or None,
                "iban":                    ent_iban.get().strip() or None,
                "tipo_fornecedor":         cb_tipo_forn.get() or None,
                "tipo_relacao":            cb_tipo_rel.get() or None,
                "metodo_pagamento":        cb_pagamento.get() or None,
                "setor":                   getattr(fornecedor, "setor", None),
                "comercial_nome":          ent_com_nome.get().strip() or None,
                "comercial_email":         ent_com_email.get().strip() or None,
                "comercial_telemovel":     ent_com_telm.get().strip() or None,
                "administrativo_nome":     ent_adm_nome.get().strip() or None,
                "administrativo_email":    ent_adm_email.get().strip() or None,
                "administrativo_telemovel": ent_adm_telm.get().strip() or None,

            }
            if not dados["nome"]:
                self.informuser("Erro", "O nome é obrigatório.")
                return
            try:
                self.controller.editar_fornecedor(dados)
                # actualizar linha visível na treeview
                tree.item(iid, values=(
                    dados["id"],
                    dados["nome"],
                    dados["nif"] or "",
                    dados["tipo_fornecedor"] or "",
                    dados["tipo_relacao"] or "",
                    dados["email"] or "",
                ))
                win.destroy()
            except Exception as e:
                self.informuser("Erro", str(e))

        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=18, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="Gravar",   command=_gravar).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="Cancelar", command=win.destroy).pack(side="left", padx=5)
