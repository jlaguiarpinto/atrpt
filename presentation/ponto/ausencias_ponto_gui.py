# presentation/ponto/ausencias_ponto_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date, datetime

from presentation.shared.base_gui import BaseGui as BG
from domain.ponto.ausencia_ponto import AusenciaPonto, TIPOS_AUSENCIA


class AusenciasPontoGUI(BG):
    """
    Vista embebida para registar ausências conhecidas (férias, baixas, etc.)
    que o processamento do ponto deve classificar correctamente em vez de marcar
    como falta de picagem.
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)

    def _post_init(self):
        self._build()

    # ── construção ────────────────────────────────────────────────────────────

    def _build(self):
        f = tk.Frame(self.frame, bg=BG.BG, padx=16, pady=12)
        f.pack(fill="both", expand=True)
        f.columnconfigure(0, weight=1)

        tk.Label(f, text="Ausências Conhecidas", font=BG.FONT_TITLE,
                 fg=BG.FG, bg=BG.BG).pack(anchor="w", pady=(0, 2))
        tk.Label(f,
                 text="Registe férias e baixas antecipadamente para evitar erros de classificação no processamento do ponto.",
                 font=BG.FONT_SUB, fg="#555", bg=BG.BG).pack(anchor="w", pady=(0, 10))

        ttk.Separator(f).pack(fill="x", pady=(0, 10))

        # ── formulário de adição ──────────────────────────────────────────────
        frm = ttk.LabelFrame(f, text="Registar Ausência", padding=10)
        frm.pack(fill="x", pady=(0, 10))
        frm.columnconfigure(1, weight=1)
        frm.columnconfigure(3, weight=1)

        # linha 0: empregado
        ttk.Label(frm, text="Empregado:").grid(row=0, column=0, sticky="w", padx=(0, 8), pady=4)
        self._empregados = self._carregar_empregados()
        nomes = [f"{e.numero} — {e.nome}" for e in self._empregados]
        self.cb_emp = ttk.Combobox(frm, values=nomes, state="readonly", width=36)
        self.cb_emp.grid(row=0, column=1, columnspan=3, sticky="w", pady=4)

        # linha 1: tipo
        ttk.Label(frm, text="Tipo:").grid(row=1, column=0, sticky="w", padx=(0, 8), pady=4)
        self._tipo_var = tk.StringVar(value="ferias")
        tipo_frame = tk.Frame(frm, bg="white")
        tipo_frame.grid(row=1, column=1, columnspan=3, sticky="w", pady=4)
        for key, label in TIPOS_AUSENCIA.items():
            ttk.Radiobutton(tipo_frame, text=label, variable=self._tipo_var,
                            value=key).pack(side="left", padx=(0, 12))

        # linha 2: datas
        ttk.Label(frm, text="Data início:").grid(row=2, column=0, sticky="w", padx=(0, 8), pady=4)
        self.ent_inicio = ttk.Entry(frm, width=14)
        self.ent_inicio.insert(0, date.today().isoformat())
        self.ent_inicio.grid(row=2, column=1, sticky="w", pady=4)

        ttk.Label(frm, text="Data fim:").grid(row=2, column=2, sticky="w", padx=(12, 8), pady=4)
        self.ent_fim = ttk.Entry(frm, width=14)
        self.ent_fim.insert(0, date.today().isoformat())
        self.ent_fim.grid(row=2, column=3, sticky="w", pady=4)

        ttk.Label(frm, text="(formato AAAA-MM-DD)", foreground="gray").grid(
            row=3, column=1, columnspan=3, sticky="w")

        # linha 4: obs
        ttk.Label(frm, text="Observação:").grid(row=4, column=0, sticky="w", padx=(0, 8), pady=4)
        self.ent_obs = ttk.Entry(frm, width=50)
        self.ent_obs.grid(row=4, column=1, columnspan=3, sticky="ew", pady=4)

        # botão adicionar
        btn_row = tk.Frame(frm, bg="white")
        btn_row.grid(row=5, column=0, columnspan=4, pady=(8, 0), sticky="w")
        tk.Button(btn_row, text="Adicionar", command=self._adicionar,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="left")

        # ── lista de ausências ────────────────────────────────────────────────
        lst_frame = ttk.LabelFrame(f, text="Ausências Registadas", padding=6)
        lst_frame.pack(fill="both", expand=True)
        lst_frame.columnconfigure(0, weight=1)

        cols = ("Empregado", "Tipo", "Início", "Fim", "Observação")
        self.tree = ttk.Treeview(lst_frame, columns=cols, show="headings",
                                  height=10, selectmode="browse")
        self.tree.heading("Empregado",  text="Empregado")
        self.tree.heading("Tipo",       text="Tipo")
        self.tree.heading("Início",     text="Início")
        self.tree.heading("Fim",        text="Fim")
        self.tree.heading("Observação", text="Observação")
        self.tree.column("Empregado",  width=220, anchor="w")
        self.tree.column("Tipo",       width=110, anchor="w")
        self.tree.column("Início",     width=90,  anchor="center")
        self.tree.column("Fim",        width=90,  anchor="center")
        self.tree.column("Observação", width=260, anchor="w")

        vsb = ttk.Scrollbar(lst_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        btn_lst = tk.Frame(lst_frame, bg=BG.BG)
        btn_lst.grid(row=1, column=0, sticky="w", pady=(6, 0))
        tk.Button(btn_lst, text="Remover Selecionado", command=self._remover,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="left", padx=(0, 10))
        tk.Button(btn_lst, text="← Voltar", command=self.go_back,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="left")

        self._atualizar_lista()

    # ── auxiliares ────────────────────────────────────────────────────────────

    def _carregar_empregados(self):
        try:
            return self.controller.listar_empregados_ativos()
        except Exception:
            return []

    def _atualizar_lista(self):
        self.tree.delete(*self.tree.get_children())
        self._ausencias_map = {}
        try:
            ausencias = self.controller.listar_ausencias()
        except Exception:
            return
        mapa_emp = {e.numero: e.nome for e in self._empregados}
        for aus in ausencias:
            nome = mapa_emp.get(aus.empregado_numero, str(aus.empregado_numero))
            iid = self.tree.insert("", "end", values=(
                f"{aus.empregado_numero} — {nome}",
                aus.tipo_label,
                aus.data_inicio.isoformat(),
                aus.data_fim.isoformat(),
                aus.obs or "",
            ))
            self._ausencias_map[iid] = aus

    def _parse_data(self, txt: str, campo: str) -> date:
        txt = txt.strip()
        for fmt in ("%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y"):
            try:
                return datetime.strptime(txt, fmt).date()
            except ValueError:
                continue
        raise ValueError(f"{campo}: formato inválido '{txt}' (use AAAA-MM-DD)")

    # ── acções ────────────────────────────────────────────────────────────────

    def _adicionar(self):
        idx = self.cb_emp.current()
        if idx < 0:
            messagebox.showwarning("Aviso", "Selecione o empregado.", parent=self.root)
            return
        emp = self._empregados[idx]
        try:
            di = self._parse_data(self.ent_inicio.get(), "Data início")
            df = self._parse_data(self.ent_fim.get(), "Data fim")
        except ValueError as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return
        if df < di:
            messagebox.showerror("Erro", "A data de fim não pode ser anterior à data de início.",
                                  parent=self.root)
            return

        aus = AusenciaPonto(
            empregado_numero = emp.numero,
            tipo             = self._tipo_var.get(),
            data_inicio      = di,
            data_fim         = df,
            obs              = self.ent_obs.get().strip() or None,
        )
        try:
            self.controller.guardar_ausencia(aus)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return

        self.ent_obs.delete(0, "end")
        self._atualizar_lista()

    def _remover(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showwarning("Aviso", "Selecione uma ausência para remover.",
                                   parent=self.root)
            return
        aus = self._ausencias_map.get(sel[0])
        if not aus:
            return
        if not messagebox.askyesno("Confirmar", "Remover esta ausência?", parent=self.root):
            return
        try:
            self.controller.remover_ausencia(aus.id)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return
        self._atualizar_lista()
