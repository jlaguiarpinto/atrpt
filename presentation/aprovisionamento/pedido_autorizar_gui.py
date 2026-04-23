# atrpt/presentation/aprovisionamento/pedido_autorizar_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG


class AutorizarGUI(BG):
    """
    Formulário para autorizar pedidos de compra.

    Fluxo:
      1. Combobox com pedidos em estado 'pendente'
      2. Ao seleccionar, mostra descrição e lista de propostas válidas
      3. Se só há uma proposta válida → seleccionada automaticamente
         Se há várias → utilizador escolhe na treeview antes de autorizar
    """

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Autorizar Pedido")
        self._pedidos_map   = {}
        self._mapa_forn     = {}
        self._proposta_sel  = None
        self._build()

    def _build(self):
        frame = ttk.Frame(self.root, padding=12)
        frame.pack(fill="both", expand=True)
        frame.columnconfigure(1, weight=1)

        # ── pedidos pendentes ──────────────────────────────────────────
        pedidos = self.controller.listar_pedidos("pendente")
        self._pedidos_map = {p.numero: p for p in pedidos}
        self._mapa_forn   = self.controller.get_mapa_fornecedores()
        numeros = list(self._pedidos_map.keys())

        ttk.Label(frame, text="Pedido:").grid(row=0, column=0, sticky="w", pady=4)
        self.cb_pedido = self.criar_combobox_autocomplete(
            frame, valores=numeros, largura=24,
            placeholder="Selecione o pedido..." if numeros else "Sem pedidos pendentes",
        )
        self.cb_pedido.grid(row=0, column=1, sticky="w", pady=4)
        self.cb_pedido.bind("<<ComboboxSelected>>", self._on_pedido_select)

        # descrição
        self.lbl_desc = ttk.Label(frame, text="", foreground="gray")
        self.lbl_desc.grid(row=1, column=0, columnspan=2, sticky="w")

        # ── propostas ─────────────────────────────────────────────────
        self.frame_prop = ttk.LabelFrame(frame, text="Propostas", padding=6)
        self.frame_prop.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.frame_prop.columnconfigure(0, weight=1)

        cols = ("Fornecedor", "Valor (€)", "PDF")
        self.tree = ttk.Treeview(
            self.frame_prop, columns=cols, show="headings",
            height=5, selectmode="browse",
        )
        self.tree.heading("Fornecedor", text="Fornecedor")
        self.tree.heading("Valor (€)",  text="Valor (€)")
        self.tree.heading("PDF",        text="PDF")
        self.tree.column("Fornecedor", width=220, anchor="w")
        self.tree.column("Valor (€)",  width=100, anchor="e")
        self.tree.column("PDF",        width=300, anchor="w")

        vsb = ttk.Scrollbar(self.frame_prop, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=vsb.set)
        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")

        self.lbl_sel = ttk.Label(self.frame_prop, text="", foreground="gray")
        self.lbl_sel.grid(row=1, column=0, columnspan=2, sticky="w", pady=(4, 0))

        self.tree.bind("<<TreeviewSelect>>", self._on_proposta_select)

        # ── botões ────────────────────────────────────────────────────
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=2, pady=12)

        self.btn_autorizar = ttk.Button(
            btn_frame, text="Autorizar", command=self._autorizar, state="disabled"
        )
        self.btn_autorizar.pack(side="left", padx=6)
        ttk.Button(btn_frame, text="Fechar", command=self.root.destroy).pack(side="left", padx=6)

    # ------------------------------------------------------------------

    def _on_pedido_select(self, event=None):
        numero = self.cb_pedido.get().strip()
        pedido = self._pedidos_map.get(numero)
        if not pedido:
            return

        self.lbl_desc.config(text=f"{pedido.descricao}  |  {pedido.centro_custo}")
        self._proposta_sel = None
        self.btn_autorizar.config(state="disabled")

        # popular treeview com propostas válidas
        self.tree.delete(*self.tree.get_children())
        validas = pedido.propostas_validas()

        if not validas:
            self.lbl_sel.config(
                text="⚠  Sem propostas válidas — adicione fornecedor e valor antes de autorizar.",
                foreground="red",
            )
            return

        for i, p in enumerate(validas):
            nome = self._mapa_forn.get(str(p.fornecedor_id), p.fornecedor_id)
            self.tree.insert("", "end", iid=str(i), values=(
                nome,
                f"{p.valor:,.2f}",
                p.pdf_path or "— sem documento —",
            ))

        if len(validas) == 1:
            # selecção automática
            self.tree.selection_set("0")
            self._proposta_sel = validas[0]
            self.lbl_sel.config(
                text="Proposta seleccionada automaticamente (única disponível).",
                foreground="gray",
            )
            self.btn_autorizar.config(state="normal")
        else:
            self.lbl_sel.config(
                text="Seleccione a proposta a adjudicar antes de autorizar.",
                foreground="gray",
            )

        # guardar referência às válidas para recuperar pelo índice
        self._validas = validas

    def _on_proposta_select(self, event=None):
        sel = self.tree.selection()
        if not sel:
            return
        idx = int(sel[0])
        self._proposta_sel = self._validas[idx]
        nome = self._mapa_forn.get(
            str(self._proposta_sel.fornecedor_id), self._proposta_sel.fornecedor_id
        )
        self.lbl_sel.config(
            text=f"Seleccionada: {nome}  —  {self._proposta_sel.valor:,.2f} €",
            foreground="navy",
        )
        self.btn_autorizar.config(state="normal")

    def _autorizar(self):
        numero = self.cb_pedido.get().strip()
        if not numero or numero not in self._pedidos_map:
            messagebox.showerror("Erro", "Selecione um pedido.", parent=self.root)
            return
        if self._proposta_sel is None:
            messagebox.showerror(
                "Erro", "Seleccione a proposta a adjudicar.", parent=self.root
            )
            return
        try:
            self.controller.autorizar_pedido(numero, self._proposta_sel)
        except ValueError as e:
            messagebox.showwarning("Não permitido", str(e), parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return

        messagebox.showinfo("OK", f"Pedido {numero} autorizado.", parent=self.root)
        self.root.destroy()
