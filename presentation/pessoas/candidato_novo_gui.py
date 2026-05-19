# atrpt/presentation/pessoas/candidato_novo_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG
from presentation.pessoas.empregado_edicao_gui import (
    _lbl, _ent, _date_ent, _combo, _sep,
    _str_date, _str_float, _str_int, _str_digits,
    _DOC_TIPOS, _GENERO,
    _ESTADO_CIVIL_NEUT, _ESTADO_CIVIL_MASC, _ESTADO_CIVIL_FEM,
    _LOCAIS, _SECTORES, _TIPOS_CONTRATO,
)
import logging

logger = logging.getLogger(__name__)


class CandidatoNovoGUI(tk.Toplevel):
    """Formulário modal para introdução de dados de novo candidato."""

    def __init__(self, parent, controller, on_save=None):
        super().__init__(parent)
        self.controller = controller
        self._on_save   = on_save

        self.title("Novo Candidato")
        self.resizable(True, True)
        self.grab_set()

        self._build()
        self.update_idletasks()

        screen_h = self.winfo_screenheight()
        w = self.winfo_width()
        h = min(self.winfo_height(), screen_h - 80)
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w//2}+{max(0, py - h//2)}")

    # ------------------------------------------------------------------

    def _scrollable_tab(self, nb, title):
        outer = ttk.Frame(nb)
        nb.add(outer, text=title)

        canvas = tk.Canvas(outer, highlightthickness=0)
        vsb = ttk.Scrollbar(outer, orient="vertical", command=canvas.yview)
        canvas.configure(yscrollcommand=vsb.set)
        vsb.pack(side="right", fill="y")
        canvas.pack(side="left", fill="both", expand=True)

        inner = ttk.Frame(canvas, padding=10)
        cw = canvas.create_window((0, 0), window=inner, anchor="nw")

        inner.bind("<Configure>",
                   lambda e: canvas.configure(scrollregion=canvas.bbox("all")))
        canvas.bind("<Configure>",
                    lambda e: canvas.itemconfig(cw, width=e.width))

        def _wheel(e):
            canvas.yview_scroll(int(-1 * (e.delta / 120)), "units")
        canvas.bind("<Enter>", lambda _: canvas.bind_all("<MouseWheel>", _wheel))
        canvas.bind("<Leave>", lambda _: canvas.unbind_all("<MouseWheel>"))

        return inner

    def _build(self):
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        tab1 = self._scrollable_tab(nb, "Dados Pessoais")
        tab1.columnconfigure(0, minsize=195)
        self._build_pessoais(tab1)

        tab2 = self._scrollable_tab(nb, "Contrato e Remuneração")
        tab2.columnconfigure(0, minsize=195)
        self._build_contrato(tab2)

        bf = tk.Frame(self)
        bf.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bf, text="Gravar", command=self._gravar,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="right", padx=6)
        tk.Button(bf, text="Cancelar", command=self.destroy,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="right", padx=2)

    def _build_pessoais(self, tab):
        _lbl(tab, "Nome:", 0)
        self._v_nome = _ent(tab, 0, 40)
        # keep ref to first entry for focus
        tab.winfo_children()[-1].focus_set()

        _lbl(tab, "Data de nascimento:", 1)
        self._v_nasc = _date_ent(tab, 1)

        _lbl(tab, "Estado civil:", 2)
        self._v_ecivil = tk.StringVar()
        self._cb_ecivil = ttk.Combobox(tab, textvariable=self._v_ecivil,
                                       values=_ESTADO_CIVIL_NEUT, width=20)
        self._cb_ecivil.grid(row=2, column=1, sticky="w", pady=3)

        _lbl(tab, "Género:", 3)
        self._v_genero = _combo(tab, 3, _GENERO, "", 14)
        self._v_genero.trace_add("write", self._on_genero_change)
        self._on_genero_change()

        _lbl(tab, "Nacionalidade:", 4)
        self._v_nacionalidade = _ent(tab, 4, 28)

        _sep(tab, 5)

        _lbl(tab, "Tipo doc. identidade:", 6)
        self._v_doc_tipo = _combo(tab, 6, _DOC_TIPOS, _DOC_TIPOS[0], 22)

        _lbl(tab, "N.º doc. identidade:", 7)
        self._v_cc = _ent(tab, 7, 24)

        _lbl(tab, "Validade doc.:", 8)
        self._v_val_cc = _date_ent(tab, 8)

        _lbl(tab, "NIF:", 9)
        self._v_nif = _ent(tab, 9, 14)

        _lbl(tab, "NISS:", 10)
        self._v_niss = _ent(tab, 10, 16)

        _sep(tab, 11)

        _lbl(tab, "Morada:", 12)
        self._v_morada = _ent(tab, 12, 40)

        _lbl(tab, "Código Postal:", 13)
        self._v_cp = _ent(tab, 13, 14)

        _lbl(tab, "Localidade:", 14)
        self._v_localidade = _ent(tab, 14, 28)

        _lbl(tab, "Telemóvel:", 15)
        self._v_telemovel = _ent(tab, 15, 16)

        _lbl(tab, "Email:", 16)
        self._v_email = _ent(tab, 16, 36)

        _lbl(tab, "Nome conhecido:", 17)
        self._v_nome_conhecido = _ent(tab, 17, 28)

        _lbl(tab, "NIB/IBAN:", 18)
        self._v_nib = _ent(tab, 18, 36)

        _lbl(tab, "Banco:", 19)
        self._v_banco = _ent(tab, 19, 28)

        _sep(tab, 20)

        _lbl(tab, "Nome (emergência):", 21)
        self._v_emerg_nome = _ent(tab, 21, 36)

        _lbl(tab, "Parentesco:", 22)
        self._v_emerg_relacao = _ent(tab, 22, 20)

        _lbl(tab, "Telm. emergência:", 23)
        self._v_emerg_telemovel = _ent(tab, 23, 16)

        _sep(tab, 24)

        _lbl(tab, "Notas:", 25)
        self._txt_notas = tk.Text(tab, width=44, height=3, relief="solid", bd=1)
        self._txt_notas.grid(row=25, column=1, sticky="w", pady=3)

    def _on_genero_change(self, *_):
        g = self._v_genero.get()
        if g == "Feminino":
            opts = _ESTADO_CIVIL_FEM
        elif g == "Masculino":
            opts = _ESTADO_CIVIL_MASC
        else:
            opts = _ESTADO_CIVIL_NEUT
        self._cb_ecivil["values"] = opts

    def _build_contrato(self, tab):
        cats = self.controller.get_categorias()

        _lbl(tab, "Local:", 0)
        self._v_local = _combo(tab, 0, _LOCAIS, "", 20)

        _lbl(tab, "Sector:", 1)
        self._v_sector = _combo(tab, 1, _SECTORES, "", 24)

        _sep(tab, 2)

        _lbl(tab, "Tipo contrato:", 3)
        self._v_tipo_cont = _combo(tab, 3, _TIPOS_CONTRATO, "", 28)

        _lbl(tab, "Data admissão:", 4)
        self._v_admissao = _date_ent(tab, 4)

        _lbl(tab, "Data cessação:", 5)
        self._v_cessacao = _date_ent(tab, 5)

        _lbl(tab, "Categoria admissão:", 6)
        self._v_cat_adm = _combo(tab, 6, cats, "", 54)

        _lbl(tab, "Categoria atual:", 7)
        self._v_cat_atual = _combo(tab, 7, cats, "", 54)

        _sep(tab, 8)

        _lbl(tab, "Vencimento (€):", 9)
        self._v_vencimento = _ent(tab, 9, 14)

        _lbl(tab, "Diuturnidades:", 10)
        self._v_diuturni = _ent(tab, 10, 8)

        _lbl(tab, "Valor diuturnidades (€):", 11)
        self._v_val_diuturni = _ent(tab, 11, 14)

    # ------------------------------------------------------------------

    def _gravar(self):
        if not self._v_nome.get().strip():
            messagebox.showwarning("Atenção", "O nome é obrigatório.", parent=self)
            return
        try:
            dados = self._collect()
        except ValueError as ex:
            messagebox.showwarning("Dados inválidos", str(ex), parent=self)
            return
        try:
            candidato = self.controller.criar_candidato(dados)
            if self._on_save and candidato:
                self._on_save(candidato)
            messagebox.showinfo(
                "Candidato criado",
                f"Candidato registado com N.º {candidato.numero}.",
                parent=self,
            )
            self.destroy()
        except Exception as ex:
            logger.exception("Erro ao criar candidato")
            messagebox.showerror("Erro", str(ex), parent=self)

    def _collect(self) -> dict:
        return {
            "nome":               self._v_nome.get().strip(),
            "data_nascimento":    _str_date("Data de nascimento", self._v_nasc.get()),
            "estado_civil":       self._v_ecivil.get().strip() or None,
            "genero":             self._v_genero.get().strip() or None,
            "nacionalidade":      self._v_nacionalidade.get().strip() or None,
            "doc_ident_tipo":     self._v_doc_tipo.get().strip() or None,
            "cc":                 self._v_cc.get().strip() or None,
            "data_validade_cc":   _str_date("Validade doc.", self._v_val_cc.get()),
            "nif":                _str_digits("NIF", self._v_nif.get()),
            "niss":               _str_digits("NISS", self._v_niss.get()),
            "morada":             self._v_morada.get().strip() or None,
            "cp":                 self._v_cp.get().strip() or None,
            "localidade":         self._v_localidade.get().strip() or None,
            "telemovel":          self._v_telemovel.get().strip() or None,
            "email":              self._v_email.get().strip() or None,
            "nome_conhecido":     self._v_nome_conhecido.get().strip() or None,
            "emerg_nome":         self._v_emerg_nome.get().strip() or None,
            "emerg_relacao":      self._v_emerg_relacao.get().strip() or None,
            "emerg_telemovel":    self._v_emerg_telemovel.get().strip() or None,
            "nib":                self._v_nib.get().strip() or None,
            "banco":              self._v_banco.get().strip() or None,
            "notas":              self._txt_notas.get("1.0", "end").strip() or None,
            "local":              self._v_local.get().strip() or None,
            "sector":             self._v_sector.get().strip() or None,
            "tipo_contrato":      self._v_tipo_cont.get().strip() or None,
            "data_admissao":      _str_date("Data admissão", self._v_admissao.get()),
            "data_cessacao":      _str_date("Data cessação", self._v_cessacao.get()),
            "categoria_admissao": self._v_cat_adm.get().strip() or None,
            "categoria_atual":    self._v_cat_atual.get().strip() or None,
            "vencimento":         _str_float("Vencimento", self._v_vencimento.get()),
            "diuturnidades":      _str_int("Diuturnidades", self._v_diuturni.get()),
            "valor_diuturnidades":_str_float("Valor diuturnidades", self._v_val_diuturni.get()),
        }
