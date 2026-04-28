# atrpt/presentation/pessoas/empregado_edicao_gui.py
"""
Formulário modal de edição de dados de um empregado.
Campos editáveis: os que podem ser alterados manualmente
(contactos, morada, notas, estado activo).
Campos calculados ou vindos de tabelas relacionadas
(categoria, vencimento, antiguidade) são mostrados em modo leitura.
"""

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG
import logging

logger = logging.getLogger(__name__)


class EmpregadoEdicaoGUI(tk.Toplevel):

    def __init__(self, parent, controller, empregado, on_save=None):
        super().__init__(parent)
        self.controller  = controller
        self.empregado   = empregado
        self._on_save    = on_save

        self.title(f"Editar — {empregado.nome}")
        self.resizable(False, False)
        self.grab_set()

        self._build()
        self.update_idletasks()
        # centrar sobre o pai
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{px - w//2}+{py - h//2}")

    # ------------------------------------------------------------------
    def _build(self):
        e = self.empregado

        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        # -- TAB 1: dados pessoais editaveis ---------------------------
        tab1 = ttk.Frame(nb, padding=10)
        nb.add(tab1, text="Dados Pessoais")

        def _lbl(parent, texto, row, col=0):
            ttk.Label(parent, text=texto, anchor="w", width=16).grid(
                row=row, column=col*2, sticky="w", padx=(0, 6), pady=3)

        def _ent(parent, valor, row, col=0, width=28):
            v = tk.StringVar(value=valor or "")
            ent = ttk.Entry(parent, textvariable=v, width=width)
            ent.grid(row=row, column=col*2+1, sticky="w", pady=3)
            return v

        def _ro(parent, valor, row, col=0, width=28):
            """Campo read-only (Label com relevo sunken)."""
            ttk.Label(parent, text=texto, anchor="w", width=16).grid(
                row=row, column=col*2, sticky="w", padx=(0, 6), pady=3)
            tk.Label(parent, text=valor or "", anchor="w", width=width,
                     relief="sunken", padx=4, bg="#f0f0f0").grid(
                row=row, column=col*2+1, sticky="w", pady=3)

        # identificacao (read-only)
        ttk.Label(tab1, text=f"N {e.numero}  |  {e.nome}",
                  font=("Segoe UI", 10, "bold")).grid(
            row=0, column=0, columnspan=4, sticky="w", pady=(0, 8))

        # contactos editaveis
        _lbl(tab1, "Telemovel:",  1)
        self._v_telemovel = _ent(tab1, e.telemovel, 1)

        _lbl(tab1, "Telefone:",   2)
        self._v_telefone  = _ent(tab1, getattr(e, "telefone", ""), 2)

        _lbl(tab1, "Email:",      3)
        self._v_email     = _ent(tab1, e.email, 3, width=36)

        ttk.Separator(tab1, orient="horizontal").grid(
            row=4, column=0, columnspan=4, sticky="ew", pady=6)

        _lbl(tab1, "Morada:",     5)
        self._v_morada    = _ent(tab1, e.morada, 5, width=40)

        _lbl(tab1, "CP:",         6)
        self._v_cp        = _ent(tab1, e.cp, 6, width=10)

        _lbl(tab1, "Localidade:", 7)
        self._v_localidade = _ent(tab1, e.localidade, 7, width=28)

        ttk.Separator(tab1, orient="horizontal").grid(
            row=8, column=0, columnspan=4, sticky="ew", pady=6)

        _lbl(tab1, "NIB/IBAN:",   9)
        self._v_nib       = _ent(tab1, e.nib, 9, width=34)

        ttk.Separator(tab1, orient="horizontal").grid(
            row=10, column=0, columnspan=4, sticky="ew", pady=6)

        _lbl(tab1, "Notas:",     11)
        self._txt_notas = tk.Text(tab1, width=44, height=3,
                                   relief="solid", bd=1)
        self._txt_notas.insert("1.0", e.notas or "")
        self._txt_notas.grid(row=11, column=1, columnspan=3,
                              sticky="w", pady=3)

        ttk.Separator(tab1, orient="horizontal").grid(
            row=12, column=0, columnspan=4, sticky="ew", pady=6)

        _lbl(tab1, "Activo:",    13)
        self._v_ativo = tk.BooleanVar(value=e.ativo_bool)
        ttk.Checkbutton(tab1, variable=self._v_ativo,
                        text="Trabalhador activo").grid(
            row=13, column=1, sticky="w", pady=3)

        # -- TAB 2: contrato e remuneracao (read-only) -----------------
        tab2 = ttk.Frame(nb, padding=10)
        nb.add(tab2, text="Contrato / Remuneracao")

        def _ro2(label, valor, row):
            ttk.Label(tab2, text=label, anchor="w", width=20).grid(
                row=row, column=0, sticky="w", padx=(0, 6), pady=3)
            tk.Label(tab2, text=str(valor or ""), anchor="w", width=30,
                     relief="sunken", padx=4, bg="#f0f0f0").grid(
                row=row, column=1, sticky="w", pady=3)

        def _fmt_date(d):
            return d.strftime("%d-%m-%Y") if d else ""

        _ro2("Tipo Contrato:",    e.tipo_contrato,        0)
        _ro2("Admissao:",         _fmt_date(e.data_admissao), 1)
        _ro2("Cessacao:",         _fmt_date(e.data_cessacao), 2)
        _ro2("Antiguidade:",
             f"{e.antiguidade} anos" if e.antiguidade else "", 3)
        _ro2("Cat. Admissao:",    e.categoria_admissao,   4)
        _ro2("Cat. Actual:",      e.categoria_atual,      5)
        _ro2("Vencimento:",
             f"{e.vencimento:,.2f} EUR" if e.vencimento else "", 6)
        _ro2("Diuturnidades:",
             str(e.diuturnidades) if e.diuturnidades is not None else "", 7)
        _ro2("Valor Diuturni.",
             f"{e.valor_diuturnidades:,.2f} EUR"
             if e.valor_diuturnidades else "", 8)
        _ro2("Local:",            e.local,                9)
        _ro2("Sector:",           e.sector,               10)

        # -- botoes ---------------------------------------------------
        bf = tk.Frame(self)
        bf.pack(fill="x", padx=10, pady=(0, 8))

        tk.Button(bf, text="Gravar", command=self._gravar,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="right", padx=6)
        tk.Button(bf, text="Cancelar", command=self.destroy,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="right", padx=2)

    # ------------------------------------------------------------------
    def _gravar(self):
        dados = {
            "numero":     self.empregado.numero,
            "telemovel":  self._v_telemovel.get().strip() or None,
            "telefone":   self._v_telefone.get().strip()  or None,
            "email":      self._v_email.get().strip()     or None,
            "morada":     self._v_morada.get().strip()    or None,
            "cp":         self._v_cp.get().strip()        or None,
            "localidade": self._v_localidade.get().strip() or None,
            "nib":        self._v_nib.get().strip()       or None,
            "notas":      self._txt_notas.get("1.0", "end").strip() or None,
            "ativo":      "A" if self._v_ativo.get() else "I",
        }
        try:
            empregado = self.controller.guardar_empregado(dados)
            if self._on_save and empregado:
                self._on_save(empregado)
            self.destroy()
        except Exception as ex:
            logger.exception("Erro ao gravar empregado")
            messagebox.showerror("Erro", str(ex), parent=self)
