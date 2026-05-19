# atrpt/presentation/pessoas/empregado_edicao_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from datetime import date
from presentation.shared.base_gui import BaseGui as BG
import logging

logger = logging.getLogger(__name__)

_DOC_TIPOS        = ["CC", "BI", "Passaporte", "Título de Residência", "Outro"]
_ESTADO_CIVIL_NEUT = ["", "Solteiro/a", "Casado/a", "Divorciado/a",
                      "Viúvo/a", "União de Facto", "Separado/a"]
_ESTADO_CIVIL_MASC = ["", "Solteiro",   "Casado",   "Divorciado",
                      "Viúvo",   "União de Facto", "Separado"]
_ESTADO_CIVIL_FEM  = ["", "Solteira",   "Casada",   "Divorciada",
                      "Viúva",   "União de Facto", "Separada"]
_ESTADO_CIVIL = _ESTADO_CIVIL_NEUT   # alias para retrocompatibilidade
_GENERO        = ["", "Masculino", "Feminino", "Outro"]
_LOCAIS        = ["", "Sede", "CSAG"]
_SECTORES      = ["", "Cozinha", "Lavandaria", "Lar", "Centro de dia"]
_TIPOS_CONTRATO = ["", "Sem termo", "Com termo certo"]
_SITUACOES    = [
    ("Ativo",       "A"), ("Inativo",    "I"), ("Baixa",      "B"),
    ("Licença",     "L"), ("Suspensão",  "S"), ("Pré-reforma","P"),
    ("Candidato",   "C"),
]


# ── helpers de layout ────────────────────────────────────────────────────────

def _lbl(parent, texto, row):
    ttk.Label(parent, text=texto, anchor="w").grid(
        row=row, column=0, sticky="w", padx=(0, 8), pady=3)

def _ent(parent, row, width=28, value=""):
    v = tk.StringVar(value=value)
    ttk.Entry(parent, textvariable=v, width=width).grid(
        row=row, column=1, sticky="w", pady=3)
    return v

def _date_ent(parent, row, value=""):
    frm = ttk.Frame(parent)
    frm.grid(row=row, column=1, sticky="w", pady=3)
    v = tk.StringVar(value=value)
    ttk.Entry(frm, textvariable=v, width=12).pack(side="left")
    ttk.Label(frm, text="  AAAA-MM-DD", foreground="gray").pack(side="left")
    return v

def _combo(parent, row, values, value="", width=18):
    v = tk.StringVar(value=value)
    ttk.Combobox(parent, textvariable=v, values=values, width=width).grid(
        row=row, column=1, sticky="w", pady=3)
    return v

def _sep(parent, row):
    ttk.Separator(parent, orient="horizontal").grid(
        row=row, column=0, columnspan=2, sticky="ew", pady=5)


# ── validação ────────────────────────────────────────────────────────────────

def _str_date(label, s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        date.fromisoformat(s)
        return s
    except ValueError:
        raise ValueError(f"{label}: data inválida. Use o formato AAAA-MM-DD.")

def _str_float(label, s):
    s = (s or "").strip().replace(",", ".")
    if not s:
        return None
    try:
        return float(s)
    except ValueError:
        raise ValueError(f"{label}: deve ser um número (ex: 1250.50).")

def _str_int(label, s):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return int(s)
    except ValueError:
        raise ValueError(f"{label}: deve ser um número inteiro.")

def _str_digits(label, s):
    s = (s or "").strip()
    if s and not s.isdigit():
        raise ValueError(f"{label}: deve conter apenas dígitos.")
    return s or None


# ── formulário ───────────────────────────────────────────────────────────────

class EmpregadoEdicaoGUI(tk.Toplevel):

    def __init__(self, parent, controller, empregado, on_save=None):
        super().__init__(parent)
        self.controller = controller
        self.empregado  = empregado
        self._on_save   = on_save

        self.title(f"Ficha — {empregado.nome}")
        self.resizable(True, True)
        self.grab_set()

        self._build()
        self.update_idletasks()

        # centrar e limitar altura ao ecrã
        screen_h = self.winfo_screenheight()
        w = self.winfo_width()
        h = min(self.winfo_height(), screen_h - 80)
        px = parent.winfo_rootx() + parent.winfo_width()  // 2
        py = parent.winfo_rooty() + parent.winfo_height() // 2
        self.geometry(f"{w}x{h}+{px - w//2}+{max(0, py - h//2)}")

    # ------------------------------------------------------------------

    def _scrollable_tab(self, nb, title):
        """Cria um tab com scroll vertical; devolve o frame interior."""
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
        e  = self.empregado
        nb = ttk.Notebook(self)
        nb.pack(fill="both", expand=True, padx=10, pady=8)

        tab1 = self._scrollable_tab(nb, "Dados Pessoais")
        tab1.columnconfigure(0, minsize=195)
        self._build_pessoais(tab1, e)

        tab2 = self._scrollable_tab(nb, "Contrato e Remuneração")
        tab2.columnconfigure(0, minsize=195)
        self._build_contrato(tab2, e)

        bf = tk.Frame(self)
        bf.pack(fill="x", padx=10, pady=(0, 8))
        tk.Button(bf, text="Gravar e Fechar", command=self._guardar_e_fechar,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG).pack(side="right", padx=6)
        tk.Button(bf, text="Guardar", command=self._guardar,
                  font=BG.FONT_BUTTON, bg=BG.BTN_BG, width=10).pack(side="right", padx=2)
        self._lbl_status = tk.Label(bf, text="", fg="#2a7a2a",
                                    font=("Segoe UI", 8))
        self._lbl_status.pack(side="left", padx=8)

    def _build_pessoais(self, tab, e):
        def fd(d): return d.isoformat() if d else ""

        ttk.Label(tab, text=f"N.º {e.numero}",
                  font=("Segoe UI", 9, "bold")).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 6))

        _lbl(tab, "Nome:", 1)
        self._v_nome = _ent(tab, 1, 40, e.nome)

        _lbl(tab, "Data de nascimento:", 2)
        self._v_nasc = _date_ent(tab, 2, fd(e.data_nascimento))

        _lbl(tab, "Estado civil:", 3)
        self._v_ecivil = tk.StringVar(value=e.estado_civil or "")
        self._cb_ecivil = ttk.Combobox(tab, textvariable=self._v_ecivil,
                                       values=_ESTADO_CIVIL_NEUT, width=20)
        self._cb_ecivil.grid(row=3, column=1, sticky="w", pady=3)

        _lbl(tab, "Género:", 4)
        self._v_genero = _combo(tab, 4, _GENERO, e.genero or "", 14)
        self._v_genero.trace_add("write", self._on_genero_change)
        self._on_genero_change()

        _lbl(tab, "Nacionalidade:", 5)
        self._v_nacionalidade = _ent(tab, 5, 28, e.nacionalidade or "")

        _sep(tab, 6)

        _lbl(tab, "Tipo doc. identidade:", 7)
        self._v_doc_tipo = _combo(tab, 7, _DOC_TIPOS, e.doc_ident_tipo or "", 22)

        _lbl(tab, "N.º doc. identidade:", 8)
        self._v_cc = _ent(tab, 8, 24, e.cc or "")

        _lbl(tab, "Validade doc.:", 9)
        self._v_val_cc = _date_ent(tab, 9, fd(e.data_validade_cc))

        _lbl(tab, "NIF:", 10)
        self._v_nif = _ent(tab, 10, 14, e.nif or "")

        _lbl(tab, "NISS:", 11)
        self._v_niss = _ent(tab, 11, 16, e.niss or "")

        _sep(tab, 12)

        _lbl(tab, "Morada:", 13)
        self._v_morada = _ent(tab, 13, 40, e.morada or "")

        _lbl(tab, "Código Postal:", 14)
        self._v_cp = _ent(tab, 14, 14, e.cp or "")

        _lbl(tab, "Localidade:", 15)
        self._v_localidade = _ent(tab, 15, 28, e.localidade or "")

        _lbl(tab, "Telemóvel:", 16)
        self._v_telemovel = _ent(tab, 16, 16, e.telemovel or "")

        _lbl(tab, "Email:", 17)
        self._v_email = _ent(tab, 17, 36, e.email or "")

        _lbl(tab, "Nome conhecido:", 18)
        self._v_nome_conhecido = _ent(tab, 18, 28, e.nome_conhecido or "")

        _lbl(tab, "NIB/IBAN:", 19)
        self._v_nib = _ent(tab, 19, 36, e.nib or "")

        _lbl(tab, "Banco:", 20)
        self._v_banco = _ent(tab, 20, 28, e.banco or "")

        _sep(tab, 21)

        _lbl(tab, "Nome (emergência):", 22)
        self._v_emerg_nome = _ent(tab, 22, 36, e.emerg_nome or "")

        _lbl(tab, "Parentesco:", 23)
        self._v_emerg_relacao = _ent(tab, 23, 20, e.emerg_relacao or "")

        _lbl(tab, "Telm. emergência:", 24)
        self._v_emerg_telemovel = _ent(tab, 24, 16, e.emerg_telemovel or "")

        _sep(tab, 25)

        _lbl(tab, "Notas:", 26)
        self._txt_notas = tk.Text(tab, width=44, height=3, relief="solid", bd=1)
        self._txt_notas.insert("1.0", e.notas or "")
        self._txt_notas.grid(row=26, column=1, sticky="w", pady=3)

        _sep(tab, 27)

        _lbl(tab, "Situação:", 28)
        cur_lbl = next((lbl for lbl, k in _SITUACOES if k == e.ativo), "Inativo")
        self._v_sit = tk.StringVar(value=cur_lbl)
        ttk.Combobox(tab, textvariable=self._v_sit,
                     values=[lbl for lbl, _ in _SITUACOES],
                     state="readonly", width=16).grid(
            row=28, column=1, sticky="w", pady=3)

    def _on_genero_change(self, *_):
        g = self._v_genero.get()
        if g == "Feminino":
            opts = _ESTADO_CIVIL_FEM
        elif g == "Masculino":
            opts = _ESTADO_CIVIL_MASC
        else:
            opts = _ESTADO_CIVIL_NEUT
        self._cb_ecivil["values"] = opts

    def _build_contrato(self, tab, e):
        def fd(d): return d.isoformat() if d else ""

        cats = self.controller.get_categorias()

        _lbl(tab, "Local:", 0)
        self._v_local = _combo(tab, 0, _LOCAIS, e.local or "", 20)

        _lbl(tab, "Sector:", 1)
        self._v_sector = _combo(tab, 1, _SECTORES, e.sector or "", 24)

        _sep(tab, 2)

        _lbl(tab, "Tipo contrato:", 3)
        self._v_tipo_cont = _combo(tab, 3, _TIPOS_CONTRATO, e.tipo_contrato or "", 28)

        _lbl(tab, "Data admissão:", 4)
        self._v_admissao = _date_ent(tab, 4, fd(e.data_admissao))

        _lbl(tab, "Data cessação:", 5)
        self._v_cessacao = _date_ent(tab, 5, fd(e.data_cessacao))

        _lbl(tab, "Categoria admissão:", 6)
        self._v_cat_adm = _combo(tab, 6, cats, e.categoria_admissao or "", 54)

        _lbl(tab, "Categoria atual:", 7)
        self._v_cat_atual = _combo(tab, 7, cats, e.categoria_atual or "", 54)

        _sep(tab, 8)

        _lbl(tab, "Vencimento (€):", 9)
        self._v_vencimento = _ent(tab, 9, 14,
            f"{e.vencimento:.2f}" if e.vencimento else "")

        _lbl(tab, "Diuturnidades:", 10)
        self._v_diuturni = _ent(tab, 10, 8,
            str(e.diuturnidades) if e.diuturnidades is not None else "")

        _lbl(tab, "Valor diuturnidades (€):", 11)
        self._v_val_diuturni = _ent(tab, 11, 14,
            f"{e.valor_diuturnidades:.2f}" if e.valor_diuturnidades else "")

    # ------------------------------------------------------------------

    def _guardar(self):
        try:
            dados = self._collect()
        except ValueError as ex:
            messagebox.showwarning("Dados inválidos", str(ex), parent=self)
            return
        try:
            emp = self.controller.guardar_empregado(dados)
            if self._on_save and emp:
                self._on_save(emp)
            self._lbl_status.config(text="Guardado com sucesso.")
            self.after(3000, lambda: self._lbl_status.config(text=""))
        except Exception as ex:
            logger.exception("Erro ao guardar")
            messagebox.showerror("Erro", str(ex), parent=self)

    def _guardar_e_fechar(self):
        try:
            dados = self._collect()
        except ValueError as ex:
            messagebox.showwarning("Dados inválidos", str(ex), parent=self)
            return
        try:
            emp = self.controller.guardar_empregado(dados)
            if self._on_save and emp:
                self._on_save(emp)
            self.destroy()
        except Exception as ex:
            logger.exception("Erro ao guardar")
            messagebox.showerror("Erro", str(ex), parent=self)

    def _collect(self) -> dict:
        sit_key = next((k for lbl, k in _SITUACOES if lbl == self._v_sit.get()), "I")
        return {
            "numero":             self.empregado.numero,
            "nome":               self._v_nome.get().strip() or None,
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
            "ativo":              sit_key,
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
