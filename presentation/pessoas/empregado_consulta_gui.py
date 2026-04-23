# atrpt/presentation/pessoas/empregado_consulta_gui.py

import tkinter as tk
from tkinter import ttk
from presentation.shared.base_gui import BaseGui as BG
import logging

logger = logging.getLogger(__name__)


class EmpregadoConsultaGUI(BG):
    """View de consulta de empregados com pesquisa e ficha de detalhe."""

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._empregado_actual = None

    def _post_init(self):
        self.build_menu_buttons([])
        self._build()

    def _build(self):
        outer = tk.Frame(self.frame, bg=self.BG)
        outer.pack(fill="both", expand=True, padx=10, pady=6)

        # ── barra de pesquisa ─────────────────────────────────────────
        barra = tk.Frame(outer, bg=self.BG)
        barra.pack(fill="x", pady=(0, 6))

        tk.Label(barra, text="Pesquisar:", bg=self.BG, fg=self.FG).pack(side="left")
        self.ent_pesquisa = ttk.Entry(barra, width=35)
        self.ent_pesquisa.pack(side="left", padx=(4, 8))
        self.ent_pesquisa.bind("<Return>", lambda e: self._pesquisar())

        self.var_ativos = tk.BooleanVar(value=True)
        ttk.Checkbutton(barra, text="Só activos",
                        variable=self.var_ativos).pack(side="left", padx=(0, 8))

        ttk.Button(barra, text="🔍 Pesquisar",
                   command=self._pesquisar).pack(side="left")
        ttk.Button(barra, text="Listar todos",
                   command=self._listar_todos).pack(side="left", padx=(4, 0))

        # ── lista de resultados ───────────────────────────────────────
        lista_frame = tk.Frame(outer, bg=self.BG)
        lista_frame.pack(fill="x", pady=4)

        cols = ("Nº", "Nome", "Local", "Sector", "Activo")
        self.tree = ttk.Treeview(lista_frame, columns=cols,
                                  show="headings", height=8, selectmode="browse")
        self.tree.heading("Nº",      text="Nº")
        self.tree.heading("Nome",    text="Nome")
        self.tree.heading("Local",   text="Local")
        self.tree.heading("Sector",  text="Sector")
        self.tree.heading("Activo",  text="Activo")
        self.tree.column("Nº",      width=50,  anchor="center")
        self.tree.column("Nome",    width=250)
        self.tree.column("Local",   width=80)
        self.tree.column("Sector",  width=160)
        self.tree.column("Activo",  width=60,  anchor="center")
        self.tree.tag_configure("inativo", foreground="gray")

        vsb = ttk.Scrollbar(lista_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.pack(side="left", fill="x", expand=True)
        vsb.pack(side="right", fill="y")
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        self.lbl_count = tk.Label(outer, text="", bg=self.BG, fg="gray")
        self.lbl_count.pack(anchor="w")

        # ── ficha de detalhe ──────────────────────────────────────────
        ttk.Separator(outer, orient="horizontal").pack(fill="x", pady=6)

        ficha = tk.Frame(outer, bg=self.BG)
        ficha.pack(fill="both", expand=True)

        # coluna esquerda — dados pessoais
        col_esq = tk.LabelFrame(ficha, text="Dados Pessoais",
                                 bg=self.BG, fg=self.FG)
        col_esq.pack(side="left", fill="both", expand=True, padx=(0, 6))

        # coluna direita — contrato e remuneração
        col_dir = tk.LabelFrame(ficha, text="Contrato e Remuneração",
                                 bg=self.BG, fg=self.FG)
        col_dir.pack(side="left", fill="both", expand=True)

        def _campo(parent, label, row, col=0):
            tk.Label(parent, text=label, bg=self.BG, fg=self.FG,
                     anchor="w", width=16).grid(row=row, column=col*2,
                     sticky="w", padx=(8, 2), pady=2)
            var = tk.StringVar()
            tk.Label(parent, textvariable=var, bg=self.BG, fg=self.FG,
                     anchor="w").grid(row=row, column=col*2+1,
                     sticky="w", padx=(0, 12), pady=2)
            return var

        # dados pessoais
        self._v_nome        = _campo(col_esq, "Nome:",          0)
        self._v_numero      = _campo(col_esq, "Nº Trabalhador:",1)
        self._v_nascimento  = _campo(col_esq, "Data Nasc.:",    2)
        self._v_genero      = _campo(col_esq, "Género:",        3)
        self._v_estado_civil= _campo(col_esq, "Estado Civil:",  4)
        self._v_nif         = _campo(col_esq, "NIF:",           5)
        self._v_niss        = _campo(col_esq, "NISS:",          6)
        self._v_cc          = _campo(col_esq, "CC:",            7)
        self._v_val_cc      = _campo(col_esq, "Validade CC:",   8)
        self._v_nib         = _campo(col_esq, "NIB/IBAN:",      9)
        self._v_telemovel   = _campo(col_esq, "Telemóvel:",     10)
        self._v_email       = _campo(col_esq, "Email:",         11)
        self._v_morada      = _campo(col_esq, "Morada:",        12)
        self._v_localidade  = _campo(col_esq, "Localidade:",    13)
        self._v_notas       = _campo(col_esq, "Notas:",         14)

        # contrato e remuneração
        self._v_local       = _campo(col_dir, "Local:",         0)
        self._v_sector      = _campo(col_dir, "Sector:",        1)
        self._v_tipo_cont   = _campo(col_dir, "Tipo Contrato:", 2)
        self._v_admissao    = _campo(col_dir, "Admissão:",      3)
        self._v_cessacao    = _campo(col_dir, "Cessação:",      4)
        self._v_antiguidade = _campo(col_dir, "Antiguidade:",   5)
        self._v_cat_admissao= _campo(col_dir, "Cat. Admissão:", 6)
        self._v_cat_atual   = _campo(col_dir, "Cat. Actual:",   7)
        self._v_vencimento  = _campo(col_dir, "Vencimento:",    8)
        self._v_diuturni    = _campo(col_dir, "Diuturnidades:", 9)
        self._v_val_diuturni= _campo(col_dir, "Valor Diuturni:",10)

    # ── pesquisa ──────────────────────────────────────────────────────

    def _pesquisar(self):
        texto = self.ent_pesquisa.get().strip()
        if not texto:
            self._listar_todos()
            return
        apenas_ativos = self.var_ativos.get()
        empregados = self.controller.pesquisar(texto, apenas_ativos=apenas_ativos)
        self._popular_tree(empregados)

    def _listar_todos(self):
        apenas_ativos = self.var_ativos.get()
        empregados = self.controller.get_empregados(apenas_ativos=apenas_ativos)
        self._popular_tree(empregados)

    def _popular_tree(self, empregados):
        self.tree.delete(*self.tree.get_children())
        self._iid_map = {}
        for e in empregados:
            tag = "" if e.ativo_bool else "inativo"
            iid = self.tree.insert("", "end", tags=(tag,), values=(
                e.numero,
                e.nome,
                e.local or "",
                e.sector or "",
                "✔" if e.ativo_bool else "✗",
            ))
            self._iid_map[iid] = e
        n = len(empregados)
        self.lbl_count.config(text=f"{n} empregado{'s' if n != 1 else ''}")
        self._limpar_ficha()

    def _on_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        e = self._iid_map.get(sel[0])
        if e:
            self._mostrar_ficha(e)

    # ── ficha ─────────────────────────────────────────────────────────

    def _mostrar_ficha(self, e):
        def _fmt_date(d):
            return d.strftime("%d-%m-%Y") if d else ""

        self._v_nome.set(e.nome)
        self._v_numero.set(str(e.numero))
        self._v_nascimento.set(_fmt_date(e.data_nascimento))
        self._v_genero.set(e.genero or "")
        self._v_estado_civil.set(e.estado_civil or "")
        self._v_nif.set(e.nif or "")
        self._v_niss.set(e.niss or "")
        self._v_cc.set(e.cc or "")
        self._v_val_cc.set(_fmt_date(e.data_validade_cc))
        self._v_nib.set(e.nib or "")
        self._v_telemovel.set(e.telemovel or "")
        self._v_email.set(e.email or "")
        self._v_morada.set(e.morada or "")
        self._v_localidade.set(
            f"{e.cp or ''}  {e.localidade or ''}".strip()
        )
        self._v_notas.set(e.notas or "")
        self._v_local.set(e.local or "")
        self._v_sector.set(e.sector or "")
        self._v_tipo_cont.set(e.tipo_contrato or "")
        self._v_admissao.set(_fmt_date(e.data_admissao))
        self._v_cessacao.set(_fmt_date(e.data_cessacao))
        self._v_antiguidade.set(
            f"{e.antiguidade} anos" if e.antiguidade else ""
        )
        self._v_cat_admissao.set(e.categoria_admissao or "")
        self._v_cat_atual.set(e.categoria_atual or "")
        self._v_vencimento.set(
            f"{e.vencimento:,.2f} €" if e.vencimento else ""
        )
        self._v_diuturni.set(str(e.diuturnidades) if e.diuturnidades is not None else "")
        self._v_val_diuturni.set(
            f"{e.valor_diuturnidades:,.2f} €" if e.valor_diuturnidades else ""
        )

    def _limpar_ficha(self):
        for v in [
            self._v_nome, self._v_numero, self._v_nascimento,
            self._v_genero, self._v_estado_civil, self._v_nif,
            self._v_niss, self._v_cc, self._v_val_cc, self._v_nib,
            self._v_telemovel, self._v_email, self._v_morada,
            self._v_localidade, self._v_notas, self._v_local,
            self._v_sector, self._v_tipo_cont, self._v_admissao,
            self._v_cessacao, self._v_antiguidade, self._v_cat_admissao,
            self._v_cat_atual, self._v_vencimento, self._v_diuturni,
            self._v_val_diuturni,
        ]:
            v.set("")
