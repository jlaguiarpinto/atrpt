# atrpt/presentation/aprovisionamento/pedido_pedir_aprovacao_gui.py

import os
import sys
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from presentation.shared.base_gui import BaseGui as BG
import logging

logger = logging.getLogger(__name__)


class PedirAprovacaoGUI(BG):
    """
    Vista embebida — submete pedido de 'criado' para 'pendente'.
    Fluxo:
      1. Escolher pedido em estado 'criado'
      2. Seleccionar proposta (auto se única)
      3. Anexar documento opcional
      4. Submeter → muda estado + envia email aos diretores
    """

    def __init__(self, parent, controller):
        super().__init__(parent, controller)
        self._pedido           = None
        self._proposta         = None
        self._proposta_validas = []
        self._anexo_path       = None

    def _post_init(self):
        self._build()

    # ── construção ────────────────────────────────────────────────────

    def _build(self):
        f = tk.Frame(self.frame, bg=BG.BG, padx=24, pady=16)
        f.pack(fill="both", expand=True)
        f.columnconfigure(1, weight=1)

        # título
        tk.Label(f, text="Pedir Aprovação", font=BG.FONT_TITLE,
                 fg=BG.FG, bg=BG.BG).grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        tk.Label(f,
                 text="Sinaliza a proposta preferida e submete para aprovação — os diretores podem adjudicar outra.",
                 font=BG.FONT_SUB, fg="#555", bg=BG.BG).grid(
            row=1, column=0, columnspan=2, sticky="w", pady=(0, 12))

        ttk.Separator(f).grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))

        # ── pedido ────────────────────────────────────────────────────
        tk.Label(f, text="Pedido:", bg=BG.BG, font=BG.FONT_SUB).grid(
            row=3, column=0, sticky="w", pady=6, padx=(0, 12))

        pedidos = self.controller.listar_pedidos("criado")
        self._pedidos_map = {p.numero: p for p in pedidos}

        self.cb_pedido = ttk.Combobox(
            f, values=list(self._pedidos_map), state="readonly", width=22)
        self.cb_pedido.grid(row=3, column=1, sticky="w", pady=6)
        self.cb_pedido.bind("<<ComboboxSelected>>", self._on_pedido)

        if not self._pedidos_map:
            self.cb_pedido.set("Sem pedidos em estado 'criado'")
            self.cb_pedido.config(state="disabled")

        self.lbl_desc = tk.Label(f, text="", fg="#555", bg=BG.BG, font=BG.FONT_SUB)
        self.lbl_desc.grid(row=4, column=0, columnspan=2, sticky="w", pady=(0, 8))

        # ── propostas ─────────────────────────────────────────────────
        frame_prop = ttk.LabelFrame(f, text="Proposta que recomenda para adjudicação", padding=8)
        frame_prop.grid(row=5, column=0, columnspan=2, sticky="ew", pady=6)
        frame_prop.columnconfigure(0, weight=1)

        cols = ("Fornecedor", "Valor (€)", "Documento")
        self.tree = ttk.Treeview(frame_prop, columns=cols, show="headings",
                                  height=4, selectmode="browse")
        self.tree.heading("Fornecedor", text="Fornecedor")
        self.tree.heading("Valor (€)",  text="Valor (€)")
        self.tree.heading("Documento",  text="Documento")
        self.tree.column("Fornecedor", width=200, anchor="w")
        self.tree.column("Valor (€)",  width=100, anchor="e")
        self.tree.column("Documento",  width=340, anchor="w")
        self.tree.tag_configure("com_doc", foreground="#1a6bbf")
        self.tree.tag_configure("sem_doc", foreground="gray")
        self.tree.pack(fill="x")
        self.tree.bind("<<TreeviewSelect>>", self._on_proposta)
        self.tree.bind("<Double-1>",         self._abrir_doc_proposta)

        self.lbl_prop = tk.Label(frame_prop, text="Seleccione um pedido.",
                                  fg="gray", bg="white")
        self.lbl_prop.pack(anchor="w", pady=(4, 0))

        # ── anexo ─────────────────────────────────────────────────────
        frame_anx = ttk.LabelFrame(f, text="Anexo", padding=8)
        frame_anx.grid(row=6, column=0, columnspan=2, sticky="ew", pady=6)
        frame_anx.columnconfigure(0, weight=1)

        self.lbl_anexo = tk.Label(frame_anx, text="Nenhum ficheiro seleccionado",
                                   fg="gray", bg="white", anchor="w")
        self.lbl_anexo.grid(row=0, column=0, sticky="ew")

        btn_anx = tk.Frame(frame_anx, bg="white")
        btn_anx.grid(row=1, column=0, sticky="w", pady=(6, 0))
        ttk.Button(btn_anx, text="Escolher ficheiro", command=self._escolher_anexo).pack(side="left", padx=(0, 6))
        ttk.Button(btn_anx, text="Remover",           command=self._remover_anexo).pack(side="left", padx=(0, 6))
        ttk.Button(btn_anx, text="Abrir",             command=self._abrir_anexo).pack(side="left")

        # ── diretores (informativo) ───────────────────────────────────
        frame_dir = ttk.LabelFrame(f, text="Email de autorização será enviado a", padding=8)
        frame_dir.grid(row=7, column=0, columnspan=2, sticky="ew", pady=6)
        frame_dir.columnconfigure(1, weight=1)

        tk.Label(frame_dir, text="Dir. Financeiro:", bg="white",
                 font=BG.FONT_SUB).grid(row=0, column=0, sticky="w", padx=(0, 10), pady=2)
        self.lbl_dir_fin = tk.Label(frame_dir, text="—", fg="gray", bg="white")
        self.lbl_dir_fin.grid(row=0, column=1, sticky="w", pady=2)

        tk.Label(frame_dir, text="2.º Diretor:", bg="white",
                 font=BG.FONT_SUB).grid(row=1, column=0, sticky="w", padx=(0, 10), pady=2)
        self._frame_dir2 = tk.Frame(frame_dir, bg="white")
        self._frame_dir2.grid(row=1, column=1, sticky="ew", pady=2)
        self.lbl_dir2 = tk.Label(self._frame_dir2, text="—", fg="gray", bg="white")
        self.lbl_dir2.pack(side="left")
        self.cb_dir2 = ttk.Combobox(self._frame_dir2, state="readonly", width=34)
        self.cb_dir2.bind("<<ComboboxSelected>>", self._on_dir2)

        # ── botões ────────────────────────────────────────────────────
        btn_row = tk.Frame(f, bg=BG.BG)
        btn_row.grid(row=8, column=0, columnspan=2, pady=18)

        self.btn_submeter = tk.Button(
            btn_row, text="Submeter para Aprovação",
            command=self._submeter, state="disabled",
            bg=BG.BTN_BG, font=BG.FONT_BUTTON)
        self.btn_submeter.pack(side="left", padx=8)

        tk.Button(btn_row, text="← Voltar",
                  command=self.go_back,
                  bg=BG.BTN_BG, font=BG.FONT_BUTTON).pack(side="left", padx=8)

        # carregar info de diretores
        self._dir_fin       = self.controller.get_diretor_financeiro()
        self._dirs_opcoes   = self.controller.get_diretores_para_segundo()
        self._dir2_escolhido = None
        self._mostrar_dir_fin()

    # ── diretores ─────────────────────────────────────────────────────

    def _mostrar_dir_fin(self):
        if self._dir_fin:
            self.lbl_dir_fin.config(
                text=f"{self._dir_fin.nome}  ({self._dir_fin.email})", fg="#1a1a1a")
        else:
            self.lbl_dir_fin.config(
                text="Nenhum utilizador com perfil DirFin", fg="red")

    def _actualizar_dir2(self, pedido):
        """Determina o 2.º diretor após seleccionar pedido."""
        self._dir2_escolhido = None
        for w in self._frame_dir2.winfo_children():
            w.pack_forget()

        from core.security import PERFIS_DIRECAO
        criador = self.controller.get_user_info(pedido.criado_por)

        if criador and criador.perfil in PERFIS_DIRECAO:
            # o criador é diretor — fica fixo
            self._dir2_escolhido = criador
            self.lbl_dir2.config(
                text=f"{criador.nome}  (criador do pedido)", fg="#1a6bbf")
            self.lbl_dir2.pack(side="left")
        elif self._dirs_opcoes:
            # dropdown de diretores disponíveis
            self.cb_dir2.config(values=[u.nome for u in self._dirs_opcoes])
            self.cb_dir2.set("")
            self.cb_dir2.pack(side="left")
        else:
            self.lbl_dir2.config(text="Nenhum diretor disponível", fg="red")
            self.lbl_dir2.pack(side="left")

        self._actualizar_btn()

    def _on_dir2(self, event=None):
        idx = self.cb_dir2.current()
        if 0 <= idx < len(self._dirs_opcoes):
            self._dir2_escolhido = self._dirs_opcoes[idx]
        self._actualizar_btn()

    # ── pedido / proposta ─────────────────────────────────────────────

    def _on_pedido(self, event=None):
        numero = self.cb_pedido.get().strip()
        pedido = self._pedidos_map.get(numero)
        if not pedido:
            return
        self._pedido   = pedido
        self._proposta = None
        self.lbl_desc.config(
            text=f"{pedido.descricao}  |  {pedido.centro_custo}  |  criado por: {pedido.criado_por}")

        mapa = self.controller.get_mapa_fornecedores()
        self.tree.delete(*self.tree.get_children())
        self._proposta_validas = pedido.propostas_validas() if hasattr(pedido, 'propostas_validas') else pedido.propostas

        for p in self._proposta_validas:
            nome  = mapa.get(str(p.fornecedor_id), str(p.fornecedor_id))
            valor = f"{p.valor:,.2f}" if p.valor is not None else "—"
            doc   = p.pdf_path or ""
            self.tree.insert("", "end",
                values=(nome, valor, doc or "— sem documento —"),
                tags=("com_doc" if doc else "sem_doc",))

        if len(self._proposta_validas) == 1:
            self.tree.selection_set(self.tree.get_children()[0])
            self._on_proposta()
        elif not self._proposta_validas:
            self.lbl_prop.config(text="Sem propostas válidas neste pedido.", fg="red")

        self._actualizar_dir2(pedido)

    def _on_proposta(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = self.tree.index(sel[0])
        if idx < len(self._proposta_validas):
            self._proposta = self._proposta_validas[idx]
            mapa = self.controller.get_mapa_fornecedores()
            nome = mapa.get(str(self._proposta.fornecedor_id), str(self._proposta.fornecedor_id))
            self.lbl_prop.config(
                text=f"Seleccionada: {nome}  |  {self._proposta.valor:,.2f} €",
                fg="#1a6bbf")
        self._actualizar_btn()

    def _abrir_doc_proposta(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        path = self.tree.item(sel[0], "values")[2]
        if path and not path.startswith("—"):
            self._abrir_path(path)

    # ── anexo ─────────────────────────────────────────────────────────

    def _escolher_anexo(self):
        path = filedialog.askopenfilename(
            title="Seleccionar Anexo",
            filetypes=[("Documentos", "*.pdf *.docx *.doc *.xlsx *.xls"),
                       ("Todos", "*.*")])
        if path:
            self._anexo_path = path
            self.lbl_anexo.config(text=os.path.basename(path), fg="#1a1a1a")

    def _remover_anexo(self):
        self._anexo_path = None
        self.lbl_anexo.config(text="Nenhum ficheiro seleccionado", fg="gray")

    def _abrir_anexo(self):
        if self._anexo_path:
            self._abrir_path(self._anexo_path)

    def _abrir_path(self, path: str):
        if not os.path.exists(path):
            messagebox.showerror("Ficheiro não encontrado", f"{path}", parent=self.root)
            return
        try:
            if sys.platform == "win32":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)

    # ── estado do botão ───────────────────────────────────────────────

    def _actualizar_btn(self):
        pode = (
            self._pedido is not None
            and self._proposta is not None
            and self._dir2_escolhido is not None
        )
        self.btn_submeter.config(state="normal" if pode else "disabled")

    # ── submeter ──────────────────────────────────────────────────────

    def _submeter(self):
        if not (self._pedido and self._proposta and self._dir2_escolhido):
            return

        mapa      = self.controller.get_mapa_fornecedores()
        nome_forn = mapa.get(str(self._proposta.fornecedor_id), str(self._proposta.fornecedor_id))

        if not messagebox.askyesno(
            "Confirmar",
            f"Pedido: {self._pedido.numero}\n"
            f"Proposta: {nome_forn}  |  {self._proposta.valor:,.2f} €\n\n"
            f"Email enviado a:\n"
            f"  • {self._dir_fin.nome}  (Dir. Financeiro)\n"
            f"  • {self._dir2_escolhido.nome}\n\n"
            "Confirma a submissão?",
            parent=self.root,
        ):
            return

        try:
            # registar anexo no pedido se indicado
            if self._anexo_path:
                self.controller.adicionar_anexo(self._pedido.numero, self._anexo_path)

            self.controller.pedir_aprovacao(
                numero             = self._pedido.numero,
                proposta           = self._proposta,
                diretor_financeiro = self._dir_fin,
                diretor2           = self._dir2_escolhido,
            )
            messagebox.showinfo(
                "Submetido",
                f"Pedido {self._pedido.numero} submetido.\n"
                f"Email enviado a {self._dir_fin.nome} e {self._dir2_escolhido.nome}.",
                parent=self.root,
            )
            self.go_back()
        except Exception as e:
            logger.error(f"Erro ao pedir aprovação: {e}", exc_info=True)
            messagebox.showerror("Erro", str(e), parent=self.root)
