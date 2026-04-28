# atrpt/presentation/secretaria/ponto_emparelhamento_dialog.py
"""
Diálogo modal que aparece quando um nome do ponto não é resolvido
nem na BD de pessoas nem na BD de fornecedores.
Mostra a lista de enfermeiros e pede ao utilizador para escolher
(ou ignorar) o emparelhamento.
"""

import tkinter as tk
from tkinter import ttk
import logging

from presentation.shared.base_gui import BaseGui as _BG

logger = logging.getLogger(__name__)

BG     = _BG.BG
FG     = _BG.FG
BTN_BG = _BG.BTN_BG
FONT_UI   = _BG.FONT_SUB
FONT_BOLD = _BG.FONT_SUB


class EmparelhamentoDialog(tk.Toplevel):
    """
    Parâmetros
    ----------
    parent        : janela pai
    nao_resolvidos: list de (numero, nome) do ponto sem correspondência
    enfermeiros   : list de Fornecedor com tipo_fornecedor == "Enfermeiro"
    on_save       : callable(numero, nome, fornecedor_id) → chamado por cada emparelhamento confirmado
    """

    def __init__(self, parent, nao_resolvidos: list, enfermeiros: list, on_save):
        super().__init__(parent)
        self.title("Emparelhamento — Nomes não resolvidos")
        self.configure(bg=BG)
        self.resizable(True, False)
        self.grab_set()

        self._nao_resolvidos = nao_resolvidos  # [(numero, nome), ...]
        self._enfermeiros    = enfermeiros
        self._on_save        = on_save
        self._idx            = 0
        self._total          = len(nao_resolvidos)

        self._build()
        self._mostrar_atual()

        self.update_idletasks()
        pw = parent.winfo_rootx() + parent.winfo_width()  // 2
        ph = parent.winfo_rooty() + parent.winfo_height() // 2
        w, h = self.winfo_width(), self.winfo_height()
        self.geometry(f"+{pw - w//2}+{ph - h//2}")
        self.wait_window()

    def _build(self):
        # cabeçalho
        hdr = tk.Frame(self, bg=BG, pady=8, padx=14)
        hdr.pack(fill="x")

        self._lbl_prog = tk.Label(hdr, text="", font=FONT_UI, bg=BG, fg=FG)
        self._lbl_prog.pack(anchor="w")

        self._lbl_nome = tk.Label(hdr, text="", font=FONT_BOLD, bg=BG, fg=FG,
                                   wraplength=500, justify="left")
        self._lbl_nome.pack(anchor="w", pady=(2, 0))

        ttk.Separator(self, orient="horizontal").pack(fill="x")

        # lista de enfermeiros
        body = tk.Frame(self, bg=BG, padx=14, pady=8)
        body.pack(fill="both", expand=True)

        tk.Label(body, text="Seleccione o enfermeiro correspondente:",
                 font=FONT_UI, bg=BG, fg=FG).pack(anchor="w", pady=(0, 4))

        # treeview com os enfermeiros
        cols = ("nome", "nif", "relacao")
        self._tree = ttk.Treeview(body, columns=cols, show="headings",
                                   height=10, selectmode="browse")
        self._tree.heading("nome",    text="Nome")
        self._tree.heading("nif",     text="NIF")
        self._tree.heading("relacao", text="Relação")
        self._tree.column("nome",    width=300)
        self._tree.column("nif",     width=100)
        self._tree.column("relacao", width=100)

        vsb = ttk.Scrollbar(body, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="left", fill="y")

        self._iid_map = {}
        for f in self._enfermeiros:
            iid = self._tree.insert("", "end", values=(
                f.nome,
                f.nif or "",
                f.tipo_relacao or "",
            ))
            self._iid_map[iid] = f

        # duplo clique selecciona e confirma
        self._tree.bind("<Double-1>", lambda e: self._confirmar())

        # botões
        bf = tk.Frame(self, bg=BG, pady=8)
        bf.pack(fill="x", padx=14)

        tk.Button(bf, text="Confirmar emparelhamento", command=self._confirmar,
                  bg=BTN_BG, fg=FG, font=FONT_BOLD,
                  relief="raised", padx=12, pady=3
                  ).pack(side="left")

        tk.Button(bf, text="Ignorar este", command=self._ignorar,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=3
                  ).pack(side="left", padx=(8, 0))

        tk.Button(bf, text="Ignorar restantes", command=self.destroy,
                  bg=BTN_BG, fg=FG, font=FONT_UI,
                  relief="raised", padx=10, pady=3
                  ).pack(side="right")

    def _mostrar_atual(self):
        if self._idx >= self._total:
            self.destroy()
            return
        numero, nome = self._nao_resolvidos[self._idx]
        self._lbl_prog.config(
            text=f"Não resolvido {self._idx + 1} de {self._total}"
        )
        self._lbl_nome.config(text=f"Ponto:  {numero} — {nome}")

        # tentar pré-seleccionar por similaridade de nome
        nome_up = nome.upper()
        melhor_iid = None
        melhor_score = 0
        for iid, f in self._iid_map.items():
            partes_f    = set(f.nome.upper().split())
            partes_nome = set(nome_up.split())
            score = len(partes_f & partes_nome)
            if score > melhor_score:
                melhor_score = score
                melhor_iid   = iid

        if melhor_iid and melhor_score > 0:
            self._tree.selection_set(melhor_iid)
            self._tree.see(melhor_iid)

    def _confirmar(self):
        sel = self._tree.selection()
        if not sel:
            return
        f = self._iid_map[sel[0]]
        numero, nome = self._nao_resolvidos[self._idx]
        try:
            self._on_save(numero, nome, f.id)
        except Exception as ex:
            logger.error(f"Erro ao guardar emparelhamento: {ex}", exc_info=True)
        self._idx += 1
        self._mostrar_atual()

    def _ignorar(self):
        self._idx += 1
        self._mostrar_atual()
