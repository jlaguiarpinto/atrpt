# atrpt/presentation/aprovisionamento/pedido_form_gui.py

import tkinter as tk
from tkinter import ttk, messagebox
from presentation.shared.base_gui import BaseGui as BG
from presentation.aprovisionamento.proposta_form_widget import PropostaFormWidget
import logging

logger = logging.getLogger(__name__)


class PedidoFormGUI(BG):
    """Formulário para criação de novo pedido."""

    def __init__(self, root, controller):
        super().__init__(root, controller)
        self.root.title("Novo Pedido")
        self.centros_custo = self.controller.get_centros_custo()
        self._propostas = []
        self._propostas_extra = []
        self.proposta_widgets = []
        self._build()

    def _build(self):
        frame = ttk.Frame(self.root, padding=10)
        frame.pack(fill="both", expand=True)

        # --- Centro de Custo ---
        ttk.Label(frame, text="Centro de Custo:").grid(row=0, column=0, sticky="w")
        self.cb_cc = ttk.Combobox(
            frame,
            values=self.centros_custo,
            state="readonly",
            width=30,
        )
        self.cb_cc.grid(row=0, column=1, columnspan=2, pady=5, sticky="w")

        # --- Descrição ---
        ttk.Label(frame, text="Descrição:").grid(row=1, column=0, sticky="nw")
        self.txt_desc = tk.Text(frame, width=40, height=4)
        self.txt_desc.grid(row=1, column=1, columnspan=2, pady=5)

        # --- Secção de Propostas ---
        propostas_label = ttk.LabelFrame(frame, text="Proposta (obrigatória)", padding=5)
        propostas_label.grid(row=2, column=0, columnspan=3, pady=10, sticky="ew")
        propostas_label.columnconfigure(0, weight=1)

        # formulário da proposta principal — sempre visível
        self.proposta_form_frame = ttk.Frame(propostas_label)
        self.proposta_form_frame.pack(fill="x")

        self._proposta_widget_principal = PropostaFormWidget(
            self.proposta_form_frame, self.controller, gui=self
        )
        self._proposta_widget_principal.build(
            parent_frame=self.proposta_form_frame, show_label_frame=False
        )

        # propostas adicionais
        ttk.Button(
            propostas_label,
            text="+ Adicionar outra proposta",
            command=self._adicionar_proposta,
        ).pack(anchor="w", pady=(4, 0))

        self.frame_extras = ttk.Frame(propostas_label)
        self.frame_extras.pack(fill="x")

        ttk.Label(propostas_label, text="Propostas adicionais confirmadas:",
                  foreground="gray").pack(anchor="w", pady=(6, 0))
        self.lista_propostas = tk.Listbox(propostas_label, height=3, width=60)
        self.lista_propostas.pack(fill="x", pady=2)

        # Botões principais
        btn_frame = ttk.Frame(frame)
        btn_frame.grid(row=3, column=0, columnspan=3, pady=10)

        ttk.Button(
            btn_frame, text="Gravar Pedido",
            command=self._gravar,
        ).pack(side="left", padx=5)

        ttk.Button(
            btn_frame, text="Fechar",
            command=self.root.destroy,
        ).pack(side="left", padx=5)

    def _adicionar_proposta(self):
        """Abre formulário para proposta adicional (opcional)."""
        extra_frame = ttk.Frame(self.frame_extras)
        extra_frame.pack(fill="x", pady=4)
        widget = PropostaFormWidget(extra_frame, self.controller, gui=self)
        widget.build(parent_frame=extra_frame, show_label_frame=False)
        btn_f = ttk.Frame(extra_frame)
        btn_f.pack(pady=4)
        ttk.Button(btn_f, text="Confirmar",
            command=lambda: self._confirmar_proposta_extra(widget, extra_frame)
        ).pack(side="left", padx=4)
        ttk.Button(btn_f, text="Cancelar",
            command=extra_frame.destroy
        ).pack(side="left", padx=4)
        self.proposta_widgets.append(widget)

    def _confirmar_proposta_extra(self, widget, frame):
        """Confirma proposta adicional e adiciona à listbox."""
        import os
        valido, fornecedor_id, valor, pdf_path = widget.validar(show_errors=True, parent=self.root)
        if not valido:
            return
        fornecedor_nome = next(
            (n for n, fid in widget.fornecedores_obj.items() if fid == fornecedor_id), fornecedor_id
        )
        self._propostas_extra.append({
            "fornecedor_id": fornecedor_id,
            "fornecedor_nome": fornecedor_nome,
            "valor": valor,
            "documento": pdf_path,
        })
        self.lista_propostas.insert(
            tk.END,
            f"{fornecedor_nome}  |  {valor:.2f} €  |  {os.path.basename(pdf_path) if pdf_path else 'Sem PDF'}"
        )
        frame.destroy()

    def _gravar(self):
        cc = self.cb_cc.get().strip()
        desc = self.txt_desc.get("1.0", "end").strip()

        if not cc or not desc:
            messagebox.showerror(
                "Erro", "Centro de Custo e Descrição são obrigatórios.",
                parent=self.root
            )
            return

        # validar proposta principal (obrigatória)
        valido, forn_id, valor, pdf = self._proposta_widget_principal.validar(
            show_errors=True, parent=self.root
        )
        if not valido:
            return

        import os
        forn_nome = next(
            (n for n, fid in self._proposta_widget_principal.fornecedores_obj.items()
             if fid == forn_id), forn_id
        )
        propostas = [{
            "fornecedor_id": forn_id,
            "fornecedor_nome": forn_nome,
            "valor": valor,
            "documento": pdf,
        }] + self._propostas_extra

        self.controller.criar_pedido(
            centro_custo=cc,
            descricao=desc,
            proposta=propostas,
        )

        messagebox.showinfo("OK", "Pedido criado com sucesso!", parent=self.root)
        self.root.destroy()