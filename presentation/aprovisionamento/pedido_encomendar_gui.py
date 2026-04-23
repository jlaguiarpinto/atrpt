# atrpt/presentation/pedido_encomendar_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG


class EncomendarGUI(BG):
    """
    Formulário para marcar pedido como encomendado
    """

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Encomendar")
        self._build()

    def _build(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # carregar pedidos autorizados
        pedidos = self.controller.listar_pedidos("autorizado")
        self._pedidos_map = {p.numero: p for p in pedidos}
        numeros = list(self._pedidos_map.keys())

        # Nº Pedido — combobox com pedidos autorizados
        ttk.Label(frame, text="Nº Pedido:").grid(row=0, column=0, sticky="w")
        self.cb_num = self.criar_combobox_autocomplete(
            frame, valores=numeros, largura=20,
            placeholder="Selecione o pedido..." if numeros else "Sem pedidos autorizados",
        )
        self.cb_num.grid(row=0, column=1, pady=5)
        self.cb_num.focus()
        self.cb_num.bind("<Return>", lambda e: self._encomendar())

        # descrição do pedido seleccionado
        self.lbl_desc = ttk.Label(frame, text="", foreground="gray")
        self.lbl_desc.grid(row=1, column=0, columnspan=2, sticky="w", pady=(0,4))
        self.cb_num.bind("<<ComboboxSelected>>", self._on_select)

        # Botões
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

        ttk.Button(btn_frame, text="Encomendar", command=self._encomendar)\
            .pack(side="left", padx=5)

        ttk.Button(btn_frame, text="Fechar", command=self.root.destroy)\
            .pack(side="left", padx=5)

    def _on_select(self, event=None):
        numero = self.cb_num.get().strip()
        pedido = self._pedidos_map.get(numero)
        if pedido:
            self.lbl_desc.config(text=f"{pedido.descricao}  |  {pedido.centro_custo}")

    def _encomendar(self):
        """Executa a marcação como encomendado"""
        numero = self.cb_num.get().strip()

        if not numero or numero not in self._pedidos_map:
            messagebox.showerror("Erro", "Selecione um pedido autorizado.", parent=self.root)
            return

        try:
            self.controller.encomendar(numero)
        except ValueError as e:
            messagebox.showwarning("Não permitido", str(e), parent=self.root)
            return
        except Exception as e:
            messagebox.showerror("Erro", str(e), parent=self.root)
            return

        messagebox.showinfo(
            "OK",
            "Pedido marcado como encomendado.",
            parent=self.root
        )

        self.root.destroy()