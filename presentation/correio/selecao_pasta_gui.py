# presentation/correio/selecao_pasta_gui.py
#
# Passo de catalogação de emails de faturas numa pasta IMAP.
#
# Ao clicar «Catalogar Pasta»:
#   1. Varre a pasta selecionada
#   2. Identifica emails com anexo PDF (fatura/NC) e emails com link de fatura
#   3. Ignora recibos e emails sem relação com faturas
#   4. Grava XLSX automático em pasta_faturas

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG

_FATURA_KEYS = ("fatura", "factura", "invoice", "fact")

_COLS = [
    ("tipo",       "Tipo",        58, "center"),
    ("fornecedor", "Fornecedor", 150, "w"),
    ("de",         "De",         160, "w"),
    ("assunto",    "Assunto",    200, "w"),
    ("data",       "Data",        88, "center"),
    ("detalhe",    "Detalhe",    220, "w"),
    ("estado",     "Estado",      80, "center"),
]


class SelecaoPastaGUI(BG):

    def __init__(self, parent, controller):
        self._pastas_map: dict[str, str] = {}   # label listbox → nome IMAP real
        self._dados: dict = {}
        super().__init__(parent, controller)

    def _post_init(self):
        self.build_menu_buttons([("Catalogar Pasta", self._catalogar)])
        self._build()
        self._carregar_pastas()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=8)
        outer.rowconfigure(1, weight=3)
        outer.rowconfigure(4, weight=1)
        outer.columnconfigure(0, weight=1)

        # Destino XLSX
        destino = str(self.controller.pasta_faturas) if self.controller.pasta_faturas else "—"
        tk.Label(
            outer, text=f"Destino XLSX:  {destino}",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 9, "bold"), anchor="w",
        ).grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 4))

        # Treeview de resultados (ocupação principal)
        self.tree = ttk.Treeview(
            outer, columns=[c[0] for c in _COLS],
            show="headings", selectmode="browse",
        )
        for key, label, width, anchor in _COLS:
            self.tree.heading(key, text=label)
            self.tree.column(key, width=width, anchor=anchor, minwidth=30,
                             stretch=(key in ("de", "assunto", "detalhe")))

        self.tree.tag_configure("pdf_ok",     foreground="#1a7a1a")   # guardado
        self.tree.tag_configure("pdf_descon", foreground="#b05000")   # guardado sem fornecedor
        self.tree.tag_configure("link",       foreground="#4a6fa5")   # link

        sb_v = ttk.Scrollbar(outer, orient="vertical",   command=self.tree.yview)
        sb_h = ttk.Scrollbar(outer, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=sb_v.set, xscrollcommand=sb_h.set)
        self.tree.grid(row=1, column=0, sticky="nsew")
        sb_v.grid(row=1, column=1, sticky="ns")
        sb_h.grid(row=2, column=0, sticky="ew")

        # Listbox de pastas IMAP (em baixo, altura fixa)
        tk.Label(outer, text="Pasta IMAP:", bg=self.BG, fg=self.FG,
                 font=("Segoe UI", 9, "bold")).grid(
            row=3, column=0, sticky="w", pady=(8, 2))

        list_frame = tk.Frame(outer, bg=self.BG)
        list_frame.grid(row=4, column=0, columnspan=2, sticky="nsew")
        list_frame.rowconfigure(0, weight=1)
        list_frame.columnconfigure(0, weight=1)

        self.lst = tk.Listbox(
            list_frame, selectmode="single", font=("Segoe UI", 9),
            relief="flat", borderwidth=1, activestyle="dotbox", height=6,
        )
        sb2 = ttk.Scrollbar(list_frame, orient="vertical", command=self.lst.yview)
        self.lst.configure(yscrollcommand=sb2.set)
        self.lst.grid(row=0, column=0, sticky="nsew")
        sb2.grid(row=0, column=1, sticky="ns")

        # Status
        self.lbl_status = tk.Label(
            outer, text="Selecione uma pasta e prima «Catalogar Pasta».",
            bg=self.BG, fg=self.FG, font=("Segoe UI", 8), anchor="w",
        )
        self.lbl_status.grid(row=5, column=0, columnspan=2, sticky="ew", pady=(4, 0))

    # ------------------------------------------------------------------
    # Carregar pastas
    # ------------------------------------------------------------------

    def _carregar_pastas(self):
        self._set_status("A ligar…")
        self.frame.update_idletasks()

        if not self.controller.conectar_se_necessario():
            self._set_status("Erro: sem ligação ao servidor.")
            return

        pastas_com_n = self.controller.listar_pastas_com_contagem()
        self.lst.delete(0, "end")
        self._pastas_map.clear()
        ultimo_sel = None

        for pasta, n in sorted(pastas_com_n, key=lambda x: x[0].lower()):
            label = f"{pasta}  ({n})"
            self.lst.insert("end", label)
            self._pastas_map[label] = pasta
            if any(k in pasta.lower() for k in _FATURA_KEYS):
                self.lst.selection_set(self.lst.size() - 1)
                ultimo_sel = self.lst.size() - 1

        if ultimo_sel is not None:
            self.lst.see(ultimo_sel)

        sel = self.lst.curselection()
        pre = f"«{self.lst.get(sel[0])}»" if sel else "nenhuma"
        self._set_status(
            f"{len(pastas_com_n)} pasta(s) — {pre} pré-selecionada. "
            "Prima «Catalogar Pasta» para iniciar."
        )

    # ------------------------------------------------------------------
    # Catalogar
    # ------------------------------------------------------------------

    def _catalogar(self):
        sel = self.lst.curselection()
        if not sel:
            self.informuser("Sem seleção", "Selecione uma pasta da lista.", "warning")
            return

        pasta   = self._pastas_map[self.lst.get(sel[0])]
        destino = self.controller.pasta_faturas
        if not destino:
            self.informuser("Sem destino",
                            "pasta_faturas não configurada no controller.", "error")
            return

        self.tree.delete(*self.tree.get_children())
        self._dados = {}
        self._set_status(f"A varrer «{pasta}»…")
        self.frame.update_idletasks()

        def progresso(feitos, total):
            self._set_status(f"A analisar: {feitos}/{total} emails relevantes…")
            self.frame.update_idletasks()

        self._dados = self.controller.catalogar_e_guardar(
            pasta, destino, callback=progresso,
            on_nao_reconhecido=self._pedir_fornecedor,
        )

        # Preencher treeview
        for r in self._dados.get("com_pdf", []):
            forn = r.get("fornecedor", "—")
            tag  = "pdf_ok" if forn != "—" else "pdf_descon"
            nomes = ", ".join(p["nome"] for p in r.get("pdfs", []))
            self.tree.insert("", "end", tags=(tag,), values=(
                "PDF",
                forn,
                r.get("de",      ""),
                r.get("assunto", ""),
                r.get("data",    ""),
                nomes,
                "Guardado",
            ))
        for r in self._dados.get("com_link", []):
            self.tree.insert("", "end", tags=("link",), values=(
                "Link",
                r.get("fornecedor", "—"),
                r.get("de",      ""),
                r.get("assunto", ""),
                r.get("data",    ""),
                " | ".join(r.get("urls", [])),
                "—",
            ))

        n_pdf  = len(self._dados.get("com_pdf",  []))
        n_link = len(self._dados.get("com_link", []))
        n_ign  = self._dados.get("ignorados",        0)
        n_tot  = self._dados.get("total",            0)
        n_grd  = self._dados.get("guardados",        0)
        n_des  = self._dados.get("nao_reconhecidos", 0)
        xlsx   = self._dados.get("xlsx")

        partes = [
            f"{n_tot} analisado(s)",
            f"{n_pdf} com PDF ({n_grd} guardado(s))",
            f"{n_des} sem fornecedor",
            f"{n_link} com link",
            f"{n_ign} ignorado(s)",
        ]
        if xlsx:
            partes.append(f"XLSX: {xlsx.name}")
        self._set_status("  |  ".join(partes))

    # ------------------------------------------------------------------

    # ------------------------------------------------------------------
    # Diálogo de identificação manual
    # ------------------------------------------------------------------

    def _pedir_fornecedor(self, assunto: str, dominio: str):
        """
        Mostra diálogo modal quando o emissor não é reconhecido.
        Devolve o Fornecedor seleccionado ou None (DESCON).
        """
        repo = self.controller._fornecedor_repo
        fornecedores = sorted(repo.list_all(), key=lambda f: f.nome) if repo else []
        nomes = [f.nome for f in fornecedores]

        dlg = tk.Toplevel(self.frame)
        dlg.title("Emissor não reconhecido")
        dlg.resizable(False, False)
        dlg.grab_set()
        dlg.focus_set()

        pad = {"padx": 12, "pady": 4}

        tk.Label(dlg, text="Emissor não identificado automaticamente.",
                 font=("Segoe UI", 9, "bold")).pack(anchor="w", **pad)

        info = tk.Frame(dlg)
        info.pack(fill="x", **pad)
        tk.Label(info, text="Domínio:", font=("Segoe UI", 9, "bold"),
                 width=10, anchor="w").grid(row=0, column=0, sticky="w")
        tk.Label(info, text=f"@{dominio}" if dominio else "(desconhecido)",
                 font=("Segoe UI", 9)).grid(row=0, column=1, sticky="w")
        tk.Label(info, text="Assunto:", font=("Segoe UI", 9, "bold"),
                 width=10, anchor="w").grid(row=1, column=0, sticky="w")
        tk.Label(info, text=assunto[:90], font=("Segoe UI", 9),
                 wraplength=420, justify="left").grid(row=1, column=1, sticky="w")

        tk.Label(dlg, text="Fornecedor:", font=("Segoe UI", 9, "bold")).pack(
            anchor="w", padx=12, pady=(8, 2))

        var_nome = tk.StringVar()
        combo = ttk.Combobox(dlg, textvariable=var_nome, values=nomes,
                             width=50, state="normal")
        combo.pack(padx=12, pady=(0, 8))
        combo.focus_set()

        # Autocomplete: filtra a lista e completa o texto com o primeiro resultado
        _prev = [""]

        def _on_key(event=None):
            if event and event.keysym in ("Return", "Escape", "Down", "Up", "Tab"):
                return
            typed = combo.get()
            if not typed:
                combo["values"] = nomes
                _prev[0] = ""
                return
            filtrados = [n for n in nomes if typed.lower() in n.lower()]
            combo["values"] = filtrados if filtrados else nomes
            # Completar automaticamente quando há um prefixo único
            if filtrados and event and event.keysym not in ("BackSpace", "Delete"):
                primeiro = filtrados[0]
                if primeiro.lower().startswith(typed.lower()) and primeiro != _prev[0]:
                    combo.set(primeiro)
                    combo.icursor(len(typed))
                    combo.selection_range(len(typed), tk.END)
                    _prev[0] = primeiro

        combo.bind("<KeyRelease>", _on_key)
        # Ao ganhar foco, abrir com lista completa
        combo.bind("<FocusIn>", lambda _: combo.configure(values=nomes))

        resultado = [None]

        def _confirmar():
            nome = var_nome.get().strip()
            resultado[0] = next((f for f in fornecedores if f.nome == nome), None)
            dlg.destroy()

        def _ignorar():
            dlg.destroy()

        btns = tk.Frame(dlg)
        btns.pack(fill="x", padx=12, pady=(4, 12))
        tk.Button(btns, text="Definir fornecedor", command=_confirmar,
                  font=("Segoe UI", 9)).pack(side="left", padx=(0, 6))
        tk.Button(btns, text="Ignorar (DESCON)", command=_ignorar,
                  font=("Segoe UI", 9)).pack(side="left")

        dlg.bind("<Return>", lambda _: _confirmar())
        dlg.bind("<Escape>", lambda _: _ignorar())

        # Centrar sobre a janela principal
        dlg.update_idletasks()
        x = self.frame.winfo_rootx() + (self.frame.winfo_width()  - dlg.winfo_width())  // 2
        y = self.frame.winfo_rooty() + (self.frame.winfo_height() - dlg.winfo_height()) // 2
        dlg.geometry(f"+{x}+{y}")

        dlg.wait_window()
        return resultado[0]

    # ------------------------------------------------------------------

    def _set_status(self, msg: str):
        self.lbl_status.config(text=msg)
