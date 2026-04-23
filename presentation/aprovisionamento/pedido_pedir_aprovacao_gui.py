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
    Permite ao utilizador:
      - Seleccionar um pedido em estado 'criado'
      - Ver e seleccionar a proposta a adjudicar
      - Juntar anexos
      - Submeter para aprovação (estado → pendente) e enviar email
    """

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Pedir Aprovação")
        self._pedido_actual = None
        self._proposta_selecionada = None
        self._anexos = []          # lista de {"id": int|None, "path": str}
        self._build()

    def _build(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        # ── selecção do pedido ────────────────────────────────────────
        ttk.Label(frame, text="Pedido:").grid(row=0, column=0, sticky="w", pady=4)

        pedidos = self.controller.listar_pedidos("criado")
        self._pedidos_map = {p.numero: p for p in pedidos}
        numeros = list(self._pedidos_map.keys())

        self.cb_pedido = ttk.Combobox(frame, values=numeros, state="readonly", width=20)
        self.cb_pedido.grid(row=0, column=1, sticky="w", pady=4)
        self.cb_pedido.bind("<<ComboboxSelected>>", self._on_pedido_select)

        if not numeros:
            self.cb_pedido.set("Sem pedidos em estado 'criado'")
            self.cb_pedido.config(state="disabled")

        # ── descrição do pedido ───────────────────────────────────────
        self.lbl_desc = ttk.Label(frame, text="", foreground="gray")
        self.lbl_desc.grid(row=1, column=0, columnspan=2, sticky="w")

        # ── propostas ─────────────────────────────────────────────────
        frame_prop = ttk.LabelFrame(frame, text="Propostas — seleccione a proposta a adjudicar",
                                    padding=6)
        frame_prop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=8)
        frame_prop.columnconfigure(0, weight=1)

        cols = ("Fornecedor", "Valor (€)", "Documento")
        self.tree_prop = ttk.Treeview(frame_prop, columns=cols, show="headings",
                                      height=5, selectmode="browse")
        self.tree_prop.heading("Fornecedor", text="Fornecedor")
        self.tree_prop.heading("Valor (€)",  text="Valor (€)")
        self.tree_prop.heading("Documento",  text="Documento")
        self.tree_prop.column("Fornecedor", width=200)
        self.tree_prop.column("Valor (€)",  width=100, anchor="e")
        self.tree_prop.column("Documento",  width=380)
        self.tree_prop.tag_configure("com_doc", foreground="#1a6bbf")
        self.tree_prop.tag_configure("sem_doc", foreground="gray")
        self.tree_prop.pack(fill="x", expand=True)
        self.tree_prop.bind("<<TreeviewSelect>>", self._on_proposta_select)
        self.tree_prop.bind("<Double-1>", self._abrir_documento)

        self.lbl_proposta = ttk.Label(frame_prop, text="Nenhuma proposta seleccionada",
                                      foreground="gray")
        self.lbl_proposta.pack(anchor="w", pady=(4, 0))

        # ── anexos ────────────────────────────────────────────────────
        frame_anx = ttk.LabelFrame(frame, text="Anexos", padding=6)
        frame_anx.grid(row=3, column=0, columnspan=2, sticky="ew", pady=4)
        frame_anx.columnconfigure(0, weight=1)

        self.lst_anexos = tk.Listbox(frame_anx, height=4, selectmode="single")
        sb_anx = ttk.Scrollbar(frame_anx, orient="vertical", command=self.lst_anexos.yview)
        self.lst_anexos.configure(yscrollcommand=sb_anx.set)
        self.lst_anexos.grid(row=0, column=0, sticky="ew")
        sb_anx.grid(row=0, column=1, sticky="ns")

        btn_anx = ttk.Frame(frame_anx)
        btn_anx.grid(row=1, column=0, sticky="w", pady=(4, 0))
        ttk.Button(btn_anx, text="➕ Adicionar anexo",
                   command=self._adicionar_anexo).pack(side="left", padx=(0, 4))
        ttk.Button(btn_anx, text="🗑 Remover",
                   command=self._remover_anexo).pack(side="left", padx=(0, 4))
        ttk.Button(btn_anx, text="📂 Abrir",
                   command=self._abrir_anexo).pack(side="left")

        # ── observações ───────────────────────────────────────────────
        ttk.Label(frame, text="Observações:").grid(row=4, column=0, sticky="nw", pady=4)
        self.txt_obs = tk.Text(frame, width=50, height=3)
        self.txt_obs.grid(row=4, column=1, sticky="ew", pady=4)

        # ── botões ────────────────────────────────────────────────────
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=5, column=0, columnspan=2, pady=12)

        self.btn_submeter = ttk.Button(
            btn_frame, text="Submeter para Aprovação",
            command=self._submeter, state="disabled"
        )
        self.btn_submeter.pack(side="left", padx=6)

        ttk.Button(btn_frame, text="Fechar",
                   command=self.root.destroy).pack(side="left", padx=6)

    # ── callbacks ─────────────────────────────────────────────────────

    def _on_pedido_select(self, event=None):
        numero = self.cb_pedido.get().strip()
        pedido = self._pedidos_map.get(numero)
        if not pedido:
            return
        self._pedido_actual = pedido
        self._proposta_selecionada = None
        self.lbl_proposta.config(text="Nenhuma proposta seleccionada")
        self.btn_submeter.config(state="disabled")

        self.lbl_desc.config(
            text=f"{pedido.descricao}  |  {pedido.centro_custo}  |  {pedido.criado_por}"
        )

        # carregar propostas
        self.tree_prop.delete(*self.tree_prop.get_children())
        mapa = self.controller.get_mapa_fornecedores()
        for p in pedido.propostas:
            nome = mapa.get(str(p.fornecedor_id), p.fornecedor_id)
            valor = f"{p.valor:,.2f}" if p.valor is not None else "—"
            doc   = p.pdf_path or ""
            tag   = "com_doc" if doc else "sem_doc"
            self.tree_prop.insert("", "end",
                values=(nome, valor, doc if doc else "— sem documento —"),
                tags=(tag,)
            )

        # se só há uma proposta, seleccionar automaticamente
        children = self.tree_prop.get_children()
        if len(children) == 1:
            self.tree_prop.selection_set(children[0])
            self._on_proposta_select()

        # carregar anexos existentes
        self._carregar_anexos(numero)

    def _on_proposta_select(self, event=None):
        sel = self.tree_prop.selection()
        if not sel or not self._pedido_actual:
            return
        idx = self.tree_prop.index(sel[0])
        propostas = self._pedido_actual.propostas
        if idx < len(propostas):
            self._proposta_selecionada = propostas[idx]
            nome = self.controller.get_mapa_fornecedores().get(
                str(self._proposta_selecionada.fornecedor_id),
                self._proposta_selecionada.fornecedor_id
            )
            valor = self._proposta_selecionada.valor
            self.lbl_proposta.config(
                text=f"✔ Seleccionada: {nome}  |  {valor:,.2f} €",
                foreground="#1a6bbf"
            )
            self.btn_submeter.config(state="normal")

    def _abrir_documento(self, event=None):
        sel = self.tree_prop.selection()
        if not sel:
            return
        valores = self.tree_prop.item(sel[0], "values")
        path = valores[2] if valores else ""
        if not path or path.startswith("—"):
            return
        self._abrir_path(path)

    # ── anexos ────────────────────────────────────────────────────────

    def _carregar_anexos(self, pedido_numero: str):
        self._anexos.clear()
        self.lst_anexos.delete(0, tk.END)
        try:
            for anx in self.controller.listar_anexos(pedido_numero):
                self._anexos.append(anx)
                self.lst_anexos.insert(tk.END, anx["path"])
        except Exception:
            pass

    def _adicionar_anexo(self):
        if not self._pedido_actual:
            messagebox.showwarning("Aviso", "Seleccione primeiro um pedido.",
                                   parent=self.root)
            return
        path = filedialog.askopenfilename(
            title="Seleccionar Anexo",
            filetypes=[
                ("Documentos", "*.pdf *.xlsx *.xls *.docx *.doc"),
                ("PDF", "*.pdf"),
                ("Excel", "*.xlsx *.xls"),
                ("Word", "*.docx *.doc"),
                ("Todos", "*.*"),
            ]
        )
        if not path:
            return
        try:
            self.controller.adicionar_anexo(self._pedido_actual.numero, path)
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return
        self._anexos.append({"id": None, "path": path})
        self.lst_anexos.insert(tk.END, path)

    def _remover_anexo(self):
        sel = self.lst_anexos.curselection()
        if not sel:
            return
        idx = sel[0]
        anexo = self._anexos[idx]
        if not messagebox.askyesno("Confirmar", "Remover este anexo?",
                                   parent=self.root):
            return
        if anexo.get("id"):
            try:
                self.controller.remover_anexo(anexo["id"])
            except Exception as e:
                messagebox.showerror("Erro", str(e), parent=self.root)
                return
        self._anexos.pop(idx)
        self.lst_anexos.delete(idx)

    def _abrir_anexo(self):
        sel = self.lst_anexos.curselection()
        if not sel:
            return
        path = self._anexos[sel[0]]["path"]
        self._abrir_path(path)

    def _abrir_path(self, path: str):
        if not os.path.exists(path):
            messagebox.showerror("Ficheiro não encontrado",
                                 f"Não foi possível encontrar:\n{path}",
                                 parent=self.root)
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

    # ── submeter ──────────────────────────────────────────────────────

    def _submeter(self):
        if not self._pedido_actual:
            return
        if not self._proposta_selecionada:
            messagebox.showwarning("Aviso", "Seleccione a proposta a adjudicar.",
                                   parent=self.root)
            return

        mapa = self.controller.get_mapa_fornecedores()
        nome_forn = mapa.get(
            str(self._proposta_selecionada.fornecedor_id),
            self._proposta_selecionada.fornecedor_id
        )
        obs = self.txt_obs.get("1.0", "end").strip()

        if not messagebox.askyesno(
            "Confirmar Submissão",
            f"Pedido: {self._pedido_actual.numero}\n"
            f"Proposta seleccionada: {nome_forn}  |  {self._proposta_selecionada.valor:,.2f} €\n\n"
            "O pedido passará a estado 'pendente' e será enviado email para aprovação.\n\n"
            "Confirma?",
            parent=self.root
        ):
            return

        try:
            self.controller.pedir_aprovacao(
                numero=self._pedido_actual.numero,
                proposta=self._proposta_selecionada,
                observacoes=obs,
            )
            messagebox.showinfo(
                "Submetido",
                f"Pedido {self._pedido_actual.numero} submetido para aprovação.\n"
                "Email enviado aos aprovadores.",
                parent=self.root
            )
            self.root.destroy()
        except Exception as e:
            logger.error(f"Erro ao pedir aprovação: {e}", exc_info=True)
            messagebox.showerror("Erro", str(e), parent=self.root)
