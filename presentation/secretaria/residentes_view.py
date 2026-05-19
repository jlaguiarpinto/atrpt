# presentation/secretaria/residentes_view.py
#
# Vista de análise e edição de residentes.
# Lista filtrável + diálogo de edição por duplo-clique.

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from presentation.shared.base_gui import BaseGui as BG

_TREE_COLS = [
    ("id",               "ID",              36),
    ("numero_residente", "Nº\nUtente",      46),
    ("numero_socio",     "Nº\nAssoc.",      46),
    ("especial",         "Especial",        56),
    ("nome",             "Nome",           155),
    ("mensalidade",      "Mensal.",         62),
    ("saldo",            "Saldo",           66),
    ("atual",            "Atual",           62),
    ("pim",              "PIM",             58),
    ("anterior",         "Anterior",        62),
    ("quota",            "Quota",           54),
    ("idade",            "Idade",           40),
    ("permanencia",      "Perm.",           48),
    ("data_fim",         "Dt.\nSaída",      72),
    ("responsavel",      "Responsável",    140),
    ("email",            "Email",          150),
    ("copag",            "CoPag",           44),
]

# campos editáveis de residentes (nunca toca em residentes_cc aqui)
_EDIT_FIELDS = [
    # (campo,               label,                 readonly)
    ("numero_residente",    "Nº Residente",        True),
    ("numero_socio",        "Nº Sócio",            False),
    ("nome",                "Nome",                False),
    ("genero",              "Género",              False),
    ("relacao",             "Relação",             False),
    ("petit_nom",           "Petit nom",           False),
    ("resp_gen",            "Tratamento resp.",    False),
    ("responsavel",         "Responsável",         False),
    ("email",               "Email",               False),
    ("resp_tlm",            "Tlm. Responsável",    False),
    ("especial",            "Especial",            False),
    ("copag",               "CoPag",               False),
    ("nif",                 "Contribuinte",        False),
    ("iban",                "IBAN",                False),
    ("data_iban",           "Data IBAN",           False),
    ("designacao_bancaria", "Designação bancária", False),
    ("data_nascimento",     "Dt. Nascimento",      False),
    ("data_admissao",       "Dt. Admissão",        False),
    ("data_fim",            "Dt. Fim",             False),
]

# ordem personalizada da coluna Especial
_ESPECIAL_ORDEM = {
    "pendente": 0,
    "saido":    1,
    "saído":    1,
    "excecao":  2,
    "excepção": 2,
    "excepcao": 2,
    "lar":      3,
    "25":       4,
    "tf":       5,
    "":         5,
    "dd":       6,
    "cd":       7,
}

def _especial_key(d) -> tuple:
    v = str(d.get("especial") or "").strip().lower()
    return (_ESPECIAL_ORDEM.get(v, 99), v)


# campos de residentes_cc — mostrados no editor como só-leitura
_CC_FIELDS = [
    ("saldo",    "Saldo CC"),
    ("pim",      "PIM"),
    ("anterior", "Anterior"),
    ("quota",    "Quota"),
]

# formatos de data aceites (tenta por ordem)
_DATE_FMTS = ["%Y-%m-%d", "%d/%m/%Y", "%d-%m-%Y", "%Y/%m/%d", "%d.%m.%Y"]


def _parse_date(val) -> date | None:
    if not val:
        return None
    s = str(val).strip()[:10]
    if not s or s.lower() in ("nan", "none", "nat"):
        return None
    for fmt in _DATE_FMTS:
        try:
            from datetime import datetime
            return datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    return None


def _idade(dt_nasc: date | None, dt_ref: date) -> int | None:
    if dt_nasc is None:
        return None
    a = dt_ref.year - dt_nasc.year - ((dt_ref.month, dt_ref.day) < (dt_nasc.month, dt_nasc.day))
    return a if 0 <= a <= 130 else None


def _permanencia(dt_adm: date | None, dt_fim: date | None, hoje: date) -> str | None:
    if dt_adm is None:
        return None
    fim = dt_fim if dt_fim else hoje
    meses_total = (fim.year - dt_adm.year) * 12 + (fim.month - dt_adm.month)
    if meses_total < 0:
        return None
    anos, meses = divmod(meses_total, 12)
    return f"{anos}a {meses}m" if anos else f"{meses}m"


class ResidentesView(BG):

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._dados: list[dict] = []
        self._ord_col = "especial"
        self._ord_asc = True

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()
        self._carregar()

    # ------------------------------------------------------------------
    # Layout
    # ------------------------------------------------------------------

    def _build(self):
        # cabeçalhos de duas linhas funcionam no Tk 8.5+ nativamente
        style = ttk.Style()
        style.configure("Treeview.Heading", font=("Segoe UI", 8))

        outer = tk.Frame(self.frame_work, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=8, pady=6)
        outer.rowconfigure(1, weight=1)
        outer.columnconfigure(0, weight=1)

        # ── barra de filtros ──────────────────────────────────────────
        filtros = tk.LabelFrame(outer, text="Filtros", bg=self.BG,
                                fg=self.FG, font=("Segoe UI", 8, "bold"))
        filtros.grid(row=0, column=0, sticky="ew", pady=(0, 6))

        f = tk.Frame(filtros, bg=self.BG)
        f.pack(fill="x", padx=6, pady=4)

        def lbl(txt):
            tk.Label(f, text=txt, bg=self.BG, fg=self.FG,
                     font=("Segoe UI", 8)).pack(side="left")

        lbl("Nome:")
        self.ent_pesq = tk.Entry(f, width=28)
        self.ent_pesq.pack(side="left", padx=(3, 14))
        self.ent_pesq.bind("<Return>", lambda _: self._filtrar())

        lbl("Especial:")
        self.cb_especial = ttk.Combobox(f, state="readonly", width=10)
        self.cb_especial.pack(side="left", padx=(3, 10))

        lbl("CoPag:")
        self.cb_copag = ttk.Combobox(f, state="readonly", width=8)
        self.cb_copag.pack(side="left", padx=(3, 10))

        tk.Button(f, text="Filtrar", command=self._filtrar,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="Limpar",  command=self._limpar_filtros,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=8).pack(side="left", padx=3)
        tk.Button(f, text="← Menu",  command=self._voltar_menu,
                  font=("Segoe UI", 8), bg=self.BTN_BG, width=10).pack(side="right", padx=6)
        tk.Button(f, text="Contratos", command=self._abrir_contratos,
                  font=("Segoe UI", 8), bg="#fff9c4", width=10).pack(side="right", padx=4)
        tk.Button(f, text="+ Novo utente", command=self._novo_utente,
                  font=("Segoe UI", 8), bg="#c8e6c9", width=13).pack(side="right", padx=4)

        # ── lista ─────────────────────────────────────────────────────
        frame_tree = tk.Frame(outer, bg=self.BG)
        frame_tree.grid(row=1, column=0, sticky="nsew")
        frame_tree.rowconfigure(0, weight=1)
        frame_tree.columnconfigure(0, weight=1)

        cols = [c for c, *_ in _TREE_COLS]
        self.tree = ttk.Treeview(frame_tree, columns=cols,
                                 show="headings", selectmode="browse")
        for cid, label, w in _TREE_COLS:
            anchor = "e" if cid in self._NUMERIC_COLS or cid in self._INT_COLS else "w"
            self.tree.heading(cid, text=label,
                              command=lambda c=cid: self._ordenar(c))
            self.tree.column(cid, width=w, anchor=anchor, minwidth=30)

        vsb = ttk.Scrollbar(frame_tree, orient="vertical",   command=self.tree.yview)
        hsb = ttk.Scrollbar(frame_tree, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")

        self.tree.bind("<Double-1>", self._editar_seleccionado)
        self.tree.tag_configure("alt",     background="#f5f0e8")
        self.tree.tag_configure("inativo", foreground="#c62828")

        # ── rodapé ────────────────────────────────────────────────────
        rodape = tk.Frame(outer, bg=self.BG)
        rodape.grid(row=2, column=0, sticky="ew", pady=(4, 0))

        self.lbl_count = tk.Label(rodape, text="", bg=self.BG,
                                  font=("Segoe UI", 8), anchor="w")
        self.lbl_count.pack(side="left", padx=(0, 16))

        self.lbl_totais = tk.Label(rodape, text="", bg=self.BG,
                                   font=("Segoe UI", 8), fg="#333", anchor="w")
        self.lbl_totais.pack(side="left")

    # ------------------------------------------------------------------
    # Dados
    # ------------------------------------------------------------------

    def _carregar(self):
        try:
            self._dados = self.controller.residentes_repo.get_all_with_cc()
        except Exception as e:
            messagebox.showerror("Erro", f"Não foi possível carregar residentes:\n{e}", parent=self.root)
            return
        # activo vem sempre do F3M (fonte de verdade)
        try:
            activo_map = self.controller.cc_repo.get_activo_por_numero()
            for d in self._dados:
                nr = d.get("numero_residente")
                if nr is not None:
                    d["activo"] = activo_map.get(int(nr), d.get("activo"))
        except Exception:
            pass
        self._enriquecer_dados()
        self._popular_filtros()
        self._filtrar()

    def _enriquecer_dados(self):
        hoje = date.today()
        for d in self._dados:
            dt_nasc = _parse_date(d.get("data_nascimento"))
            dt_adm  = _parse_date(d.get("data_admissao"))
            dt_fim  = _parse_date(d.get("data_fim"))
            dt_ref  = dt_fim if dt_fim else hoje
            d["idade"]       = _idade(dt_nasc, dt_ref)
            d["permanencia"] = _permanencia(dt_adm, dt_fim, hoje)
            # normalizar data_fim para só mostrar a data (sem hora)
            if dt_fim:
                d["data_fim"] = dt_fim.strftime("%Y-%m-%d")

    def _popular_filtros(self):
        def vals(campo):
            vs = sorted({str(d.get(campo) or "").strip()
                         for d in self._dados if d.get(campo)})
            return ["(todos)"] + vs

        self.cb_especial["values"] = vals("especial")
        self.cb_copag["values"]    = vals("copag")
        self.cb_especial.set("(todos)")
        self.cb_copag.set("(todos)")

    def _filtrar(self):
        pesq     = self.ent_pesq.get().strip().lower()
        especial = self.cb_especial.get()
        copag    = self.cb_copag.get()

        def _tem_saldo(d):
            return any(
                d.get(c) not in (None, 0, 0.0)
                for c in self._NUMERIC_COLS
            )

        def ok(d):
            if d.get("activo") == "Não" and not _tem_saldo(d):
                return False
            if pesq and pesq not in (d.get("nome") or "").lower():
                return False
            if especial != "(todos)" and str(d.get("especial") or "").strip() != especial:
                return False
            if copag != "(todos)" and str(d.get("copag") or "").strip() != copag:
                return False
            return True

        filtrado = [d for d in self._dados if ok(d)]
        if self._ord_col == "especial":
            filtrado.sort(key=_especial_key, reverse=not self._ord_asc)
        else:
            filtrado.sort(
                key=lambda d: (d.get(self._ord_col) is None,
                               str(d.get(self._ord_col) or "").lower()),
                reverse=not self._ord_asc,
            )
        self._preencher_tree(filtrado)

    def _limpar_filtros(self):
        self.ent_pesq.delete(0, "end")
        self.cb_especial.set("(todos)")
        self.cb_copag.set("(todos)")
        self._filtrar()

    _NUMERIC_COLS = {"mensalidade", "saldo", "atual", "pim", "anterior", "quota"}
    _INT_COLS     = {"id", "numero_residente", "numero_socio", "idade"}
    _TOTAIS_COLS  = ("saldo", "atual", "pim", "quota")

    @staticmethod
    def _fmt(v, col: str) -> str:
        if v is None:
            return ""
        if col in ResidentesView._INT_COLS:
            try:
                return str(int(v))
            except (TypeError, ValueError):
                return str(v).strip()
        if col in ResidentesView._NUMERIC_COLS:
            try:
                f = float(v)
                return f"{f:.2f}" if f else ""
            except (TypeError, ValueError):
                return ""
        s = str(v).strip()
        return "" if s.lower() in ("nan", "none", "nat") else s

    def _preencher_tree(self, dados: list[dict]):
        self.tree.delete(*self.tree.get_children())
        for i, d in enumerate(dados):
            vals = tuple(self._fmt(d.get(cid), cid) for cid, *_ in _TREE_COLS)
            tag  = "inativo" if d.get("activo") == "Não" else ("alt" if i % 2 else "")
            raw_id = d.get("id")
            iid = str(int(raw_id)) if raw_id is not None else str(d["numero_residente"])
            self.tree.insert("", "end", iid=iid, values=vals, tags=(tag,))

        # totais
        def _soma(col):
            t = 0.0
            for d in dados:
                try:
                    t += float(d.get(col) or 0)
                except (TypeError, ValueError):
                    pass
            return t

        partes = "   ".join(
            f"{col.capitalize()}: {_soma(col):.2f}"
            for col in self._TOTAIS_COLS
        )
        self.lbl_count.config(text=f"{len(dados)} residente(s)")
        self.lbl_totais.config(text=partes)

    def _ordenar(self, col):
        if self._ord_col == col:
            self._ord_asc = not self._ord_asc
        else:
            self._ord_col = col
            self._ord_asc = True
        self._filtrar()

    # ------------------------------------------------------------------
    # Edição
    # ------------------------------------------------------------------

    def _editar_seleccionado(self, _event=None):
        sel = self.tree.selection()
        if not sel:
            return
        iid = sel[0]
        dados = next(
            (d for d in self._dados
             if d.get("id") is not None and str(int(d["id"])) == iid),
            None,
        )
        if dados is None:
            dados = next(
                (d for d in self._dados if str(d.get("numero_residente")) == iid),
                None,
            )
        if dados is None:
            return
        self._abrir_editor(dados)

    def _abrir_editor(self, dados: dict):
        win = tk.Toplevel(self.root)
        win.title(f"Editar — {dados.get('nome', '')}")
        win.transient(self.root)
        win.grab_set()
        win.resizable(False, True)

        pad = {"padx": 8, "pady": 3}
        frame = tk.Frame(win, padx=12, pady=10)
        frame.pack(fill="both", expand=True)

        entradas: dict[str, tk.StringVar] = {}

        def _menu_contexto(entry):
            menu = tk.Menu(entry, tearoff=0)
            menu.add_command(label="Cortar",  command=lambda: entry.event_generate("<<Cut>>"))
            menu.add_command(label="Copiar",  command=lambda: entry.event_generate("<<Copy>>"))
            menu.add_command(label="Colar",   command=lambda: entry.event_generate("<<Paste>>"))
            menu.add_separator()
            menu.add_command(label="Seleccionar tudo",
                             command=lambda: entry.select_range(0, tk.END))
            return menu

        for row_idx, (campo, label, readonly) in enumerate(_EDIT_FIELDS):
            tk.Label(frame, text=label + ":", anchor="e", width=18).grid(
                row=row_idx, column=0, sticky="e", **pad)
            var = tk.StringVar(value=str(dados.get(campo) or "").strip())
            entradas[campo] = var
            state = "readonly" if readonly else "normal"
            e = tk.Entry(frame, textvariable=var, state=state, width=46)
            e.grid(row=row_idx, column=1, sticky="ew", **pad)
            if not readonly:
                m = _menu_contexto(e)
                e.bind("<Button-3>", lambda ev, _m=m: _m.tk_popup(ev.x_root, ev.y_root))

        # separador + campos CC (só-leitura)
        n = len(_EDIT_FIELDS)
        ttk.Separator(frame, orient="horizontal").grid(
            row=n, column=0, columnspan=2, sticky="ew", pady=6)
        tk.Label(frame, text="Conta Corrente", font=("Segoe UI", 8, "bold"),
                 anchor="w").grid(row=n + 1, column=0, columnspan=2, sticky="w", padx=8)
        for i, (campo, label) in enumerate(_CC_FIELDS):
            r = n + 2 + i
            tk.Label(frame, text=label + ":", anchor="e", width=18).grid(
                row=r, column=0, sticky="e", **pad)
            v = dados.get(campo)
            txt = self._fmt(v, campo) or "—"
            tk.Label(frame, text=txt, anchor="w",
                     font=("Segoe UI", 9), fg="#444").grid(
                row=r, column=1, sticky="w", **pad)

        frame.columnconfigure(1, weight=1)

        # ── botões ────────────────────────────────────────────────────
        rodape = tk.Frame(win, pady=8)
        rodape.pack(fill="x")

        def _guardar():
            campos = {
                campo: var.get().strip() or None
                for campo, _, readonly in _EDIT_FIELDS
                if not readonly
            }
            try:
                ok = self.controller.residentes_repo.update(
                    int(dados["numero_residente"]), campos
                )
                if ok:
                    for d in self._dados:
                        if d.get("numero_residente") == dados["numero_residente"]:
                            d.update(campos)
                            # recalcular campos derivados após edição de datas
                            hoje = date.today()
                            dt_nasc = _parse_date(d.get("data_nascimento"))
                            dt_adm  = _parse_date(d.get("data_admissao"))
                            dt_fim  = _parse_date(d.get("data_fim"))
                            dt_ref  = dt_fim if dt_fim else hoje
                            d["idade"]       = _idade(dt_nasc, dt_ref)
                            d["permanencia"] = _permanencia(dt_adm, dt_fim, hoje)
                            break
                    self._filtrar()
                    win.destroy()
                else:
                    messagebox.showwarning("Aviso", "Nenhuma linha actualizada.", parent=win)
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=win)

        tk.Button(rodape, text="Guardar", command=_guardar,
                  bg="#c8e6c9", font=("Segoe UI", 9, "bold"), width=12).pack(side="left", padx=10)
        tk.Button(rodape, text="Cancelar", command=win.destroy,
                  width=10).pack(side="left")

        win.bind("<Return>", lambda _: _guardar())
        win.bind("<Escape>", lambda _: win.destroy())

    # ------------------------------------------------------------------
    # Navegação
    # ------------------------------------------------------------------

    def _novo_utente(self):
        getattr(self, '_root_gui', self).show_view(
            __import__('presentation.secretaria.novo_residente_view',
                        fromlist=['NovoResidenteView']).NovoResidenteView,
            self.controller,
        )

    def _abrir_contratos(self):
        getattr(self, '_root_gui', self).show_view(
            __import__('presentation.secretaria.contrato_residente_view',
                        fromlist=['ContratoResidenteView']).ContratoResidenteView,
            self.controller,
        )

    def _voltar_menu(self):
        getattr(self, '_root_gui', self).go_back()
